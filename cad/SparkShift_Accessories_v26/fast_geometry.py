"""Fast, exact clearance helpers for the SparkShift CAD review scripts.

Why the review scripts were slow (measured on one carriage-vs-parked-tool sample):
- BRepExtrema_DistShapeShape on whole solids compares every face pair whose boxes are near.
  Complex solids (P03 has 904 faces, the dock 354) took up to 16 s per pair even when the
  answer was 26 mm, and one clearance sample cost about 100 s on one core.
- STEP parsing: the 30 MB core reference takes 7.4 s per load; OCC's native BREP takes 0.3 s.

This module keeps the results exact while doing far less work:
- ``load`` caches each STEP as BREP (keyed by file size and mtime) and returns a fresh shape
  on every call, so destructive OCC Booleans can never corrupt a cached object.
- ``FaceIndex`` stores every face of a solid with a tight bounding box. ``min_distance`` ranks
  face pairs by the distance between their boxes (a lower bound) and runs the exact OCC
  distance only on face pairs that can still beat the best answer so far.
- ``run_parallel`` spreads independent scenarios over worker processes.
"""

import os
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRep import BRep_Tool
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.Extrema import Extrema_ExtFlag_MIN
from OCP.gp import gp_Pnt, gp_Trsf, gp_Vec
from OCP.TopAbs import TopAbs_FACE, TopAbs_IN, TopAbs_VERTEX
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS

HERE = Path(__file__).resolve().parent
STEP = HERE / "step"
CACHE = HERE / ".cache" / "brep"


def load(name):
    """Same result as cq.importers.importStep(step/<name>.step).val(), via a BREP cache."""
    step = STEP / f"{name}.step"
    stat = step.stat()
    cached = CACHE / f"{name}.{stat.st_size}.{stat.st_mtime_ns}.brep"
    if cached.exists():
        return cq.Shape.importBrep(str(cached))
    shape = cq.importers.importStep(str(step)).val()
    CACHE.mkdir(parents=True, exist_ok=True)
    for old in CACHE.glob(f"{name}.*.brep"):
        old.unlink(missing_ok=True)
    tmp = cached.with_suffix(f".{os.getpid()}.tmp")
    shape.exportBrep(str(tmp))
    os.replace(tmp, cached)
    return shape


class FaceIndex:
    """Faces of one solid with tight, enclosing bounding boxes (computed once)."""

    def __init__(self, shape, label=None):
        self.label = label
        self.shape = shape.wrapped if hasattr(shape, "wrapped") else shape
        faces = []
        explorer = TopExp_Explorer(self.shape, TopAbs_FACE)
        while explorer.More():
            faces.append(explorer.Current())
            explorer.Next()
        self.faces = faces
        boxes = np.empty((len(faces), 6))
        for k, face in enumerate(faces):
            box = Bnd_Box()
            BRepBndLib.AddOptimal_s(face, box, False, False)
            boxes[k] = box.Get()
        self.lo, self.hi = boxes[:, :3], boxes[:, 3:]
        self.box_lo, self.box_hi = self.lo.min(axis=0), self.hi.max(axis=0)
        vertex = TopExp_Explorer(self.shape, TopAbs_VERTEX)
        p = BRep_Tool.Pnt_s(TopoDS.Vertex_s(vertex.Current()))
        self.point = np.array([p.X(), p.Y(), p.Z()])


_INDEX = OrderedDict()
_INDEX_LIMIT = 1024


def index_of(shape):
    """FaceIndex for a solid, built once per distinct shape (same TShape and location).

    The cache is bounded because callers often pass translated copies that are used only once.
    """
    wrapped = shape.wrapped if hasattr(shape, "wrapped") else shape
    key = hash(wrapped)
    bucket = _INDEX.get(key)
    if bucket is not None:
        _INDEX.move_to_end(key)
        for stored, index in bucket:
            if stored.IsSame(wrapped):
                return index
    index = FaceIndex(wrapped)
    _INDEX.setdefault(key, []).append((wrapped, index))
    while len(_INDEX) > _INDEX_LIMIT:
        _INDEX.popitem(last=False)
    return index


def _moved(face, offset):
    if not any(offset):
        return face
    trsf = gp_Trsf()
    trsf.SetTranslation(gp_Vec(*offset))
    return face.Moved(TopLoc_Location(trsf))


def _box_distance(alo, ahi, blo, bhi):
    gap = np.maximum(0.0, np.maximum(blo - ahi, alo - bhi))
    return np.sqrt((gap * gap).sum(axis=-1))


def pair_distance(a, b, offset_a=(0, 0, 0), offset_b=(0, 0, 0), best=np.inf):
    """Exact minimum distance between two indexed solids, or None if it is not below ``best``."""
    oa, ob = np.asarray(offset_a, float), np.asarray(offset_b, float)
    if _box_distance(a.box_lo + oa, a.box_hi + oa, b.box_lo + ob, b.box_hi + ob) >= best:
        return None
    # Faces of each solid near the other solid's box, then all candidate pairs between them.
    ia = np.nonzero(_box_distance(a.lo + oa, a.hi + oa, b.box_lo + ob, b.box_hi + ob) < best)[0]
    ib = np.nonzero(_box_distance(b.lo + ob, b.hi + ob, a.box_lo + oa, a.box_hi + oa) < best)[0]
    if not len(ia) or not len(ib):
        return None
    lower = _box_distance((a.lo[ia] + oa)[:, None], (a.hi[ia] + oa)[:, None], (b.lo[ib] + ob)[None], (b.hi[ib] + ob)[None])
    order = np.argsort(lower, axis=None)
    result = None
    for flat in order:
        i, j = divmod(int(flat), len(ib))
        if lower[i, j] >= best:
            break
        ext = BRepExtrema_DistShapeShape(_moved(a.faces[ia[i]], offset_a), _moved(b.faces[ib[j]], offset_b),
                                         Extrema_ExtFlag_MIN)
        if not ext.IsDone() or ext.NbSolution() == 0:
            raise RuntimeError("BRepExtrema failed on a face pair")
        value = ext.Value()
        if value < best:
            p, q = ext.PointOnShape1(1), ext.PointOnShape2(1)
            best = value
            result = (value, (p.X(), p.Y(), p.Z()), (q.X(), q.Y(), q.Z()))
    return result


def _inside(index, point):
    return BRepClass3d_SolidClassifier(index.shape, gp_Pnt(*point), 1e-7).State() == TopAbs_IN


def nested(a, b, offset_a=(0, 0, 0), offset_b=(0, 0, 0)):
    """True if one solid lies wholly inside the other. Only meaningful when their surfaces do not meet."""
    oa, ob = np.asarray(offset_a, float), np.asarray(offset_b, float)
    return _inside(b, a.point + oa - ob) or _inside(a, b.point + ob - oa)


def solid_distance(a, b, offset_a=(0, 0, 0), offset_b=(0, 0, 0), best=np.inf):
    """Like BRepExtrema on the two solids: 0 when one contains the other, else the surface distance.

    Returns (mm, point_a, point_b), or None when the distance is not below ``best``.
    """
    oa, ob = np.asarray(offset_a, float), np.asarray(offset_b, float)
    if _box_distance(a.box_lo + oa, a.box_hi + oa, b.box_lo + ob, b.box_hi + ob) == 0 and nested(a, b, oa, ob):
        p = tuple(a.point + oa)
        return 0.0, p, p
    return pair_distance(a, b, offset_a, offset_b, best)


def touch_or_nest(a, b, offset_a=(0, 0, 0), offset_b=(0, 0, 0), tol=1e-6):
    """Exact screen for Booleans: False guarantees the two solids share no volume."""
    oa, ob = np.asarray(offset_a, float), np.asarray(offset_b, float)
    if _box_distance(a.box_lo + oa, a.box_hi + oa, b.box_lo + ob, b.box_hi + ob) > tol:
        return False
    if pair_distance(a, b, offset_a, offset_b, tol) is not None:
        return True
    return nested(a, b, oa, ob)


def min_distance(group_a, group_b, offset_a=(0, 0, 0), offset_b=(0, 0, 0), cutoff=5.0):
    """Exact minimum distance between two lists of FaceIndex (or None if nothing is within cutoff).

    Returns (mm, label_a, label_b, point_a, point_b). Solid pairs are tried nearest-box first, and
    every later pair is skipped as soon as its box distance cannot beat the running minimum.
    """
    oa, ob = np.asarray(offset_a, float), np.asarray(offset_b, float)
    pairs = []
    for a in group_a:
        for b in group_b:
            d = _box_distance(a.box_lo + oa, a.box_hi + oa, b.box_lo + ob, b.box_hi + ob)
            if d < cutoff:
                pairs.append((float(d), a, b))
    pairs.sort(key=lambda t: t[0])
    best, found = cutoff, None
    for box, a, b in pairs:
        if box >= best:
            break
        hit = solid_distance(a, b, offset_a, offset_b, best)
        if hit is not None:
            best = hit[0]
            found = (hit[0], a.label, b.label, hit[1], hit[2])
    return found


def axis_gap(a, b, offset_a=(0, 0, 0), offset_b=(0, 0, 0)):
    """Largest per-axis gap between the solids' boxes (the screen the original scripts used)."""
    oa, ob = np.asarray(offset_a, float), np.asarray(offset_b, float)
    return float(max(0.0, np.max(np.maximum(b.box_lo + ob - a.box_hi - oa, a.box_lo + oa - b.box_hi - ob))))


def index_group(parts):
    """[(label, shape)] -> [FaceIndex], one per solid."""
    return [FaceIndex(s, label) for label, shape in parts for s in shape.Solids()]


def run_parallel(func, tasks, workers=None):
    """Map ``func`` over picklable ``tasks`` in worker processes (Windows-safe, spawn)."""
    workers = workers or max(1, min(len(tasks), (os.cpu_count() or 2) // 2))
    if workers == 1:
        return [func(t) for t in tasks]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(func, tasks))
