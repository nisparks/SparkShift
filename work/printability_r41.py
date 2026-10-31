"""Printability with build-plate-only supports: which overhangs the slicer will leave unsupported, per orientation.

Bambu Studio (support threshold angle 30 deg) supports faces flatter than 30 deg from horizontal. With
support_on_build_plate_only, a face whose column down to the bed meets the part gets no support at all.
Those faces, inside the ducts and out, must hold up on their own (short bridges are fine).
"""
import json
import math
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

import r37_parts as P37  # noqa: E402
import r41_parts as R  # noqa: E402
import r42_parts as R42  # noqa: E402
from build_modular_toolhead import load  # noqa: E402

FILES = Path(__file__).resolve().parent
THRESHOLD_DEG = 30.0                     # Bambu Studio default support threshold (slope from horizontal)
ROUGH_DEG = 45.0                         # flatter than this from horizontal prints rough without support
ROT = {"back face down (-Y)": ((1, 0, 0), 90), "front down (+Y)": ((1, 0, 0), -90),
       "top down (+Z)": ((1, 0, 0), 180), "bottom down (-Z)": ((1, 0, 0), 0),
       "left side down (-X)": ((0, 1, 0), -90), "right side down (+X)": ((0, 1, 0), 90)}
PARTS = {"P20": R.NAMES["p20"], "P21": R.NAMES["p21"], "P22": R.NAMES["p22"],
         "P23_Cartographer": R42.NAMES["p23"], "P23_Beacon": P37.NAMES["p23"]}


def rotation(axis, deg):
    a = np.radians(deg)
    x, y, z = axis
    c, s = math.cos(a), math.sin(a)
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


def mesh_of(shape, name):
    path = FILES / f"_pp_{name}.stl"
    cq.exporters.export(shape, str(path), tolerance=0.02, angularTolerance=0.1)
    m = trimesh.load_mesh(str(path))
    path.unlink()
    return m


def clusters(mesh, mask):
    idx = np.nonzero(mask)[0]
    if not len(idx):
        return []
    sub = set(idx.tolist())
    adj = mesh.face_adjacency
    keep = np.array([a in sub and b in sub for a, b in adj]) if len(adj) else np.array([], bool)
    pairs = adj[keep] if len(adj) else adj
    parent = {i: i for i in idx}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    groups = {}
    for i in idx:
        groups.setdefault(find(i), []).append(i)
    return list(groups.values())


def analyse(mesh_asm, rot):
    Rm = rotation(*rot)
    v = mesh_asm.vertices @ Rm.T
    shift = -v.min(axis=0)
    shift[0] = shift[1] = 0.0
    m = trimesh.Trimesh(v + shift, mesh_asm.faces, process=False)
    n, area, cen = m.face_normals, m.area_faces, m.triangles_center
    slope = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))          # 0 = flat ceiling facing down
    down = n[:, 2] < 0
    bed = down & (cen[:, 2] < 0.02) & (slope < 1.0)
    need = down & ~bed & (slope < THRESHOLD_DEG)
    rough = down & ~bed & (slope >= THRESHOLD_DEG) & (slope < ROUGH_DEG)
    blocked = np.zeros(len(m.faces), bool)
    pick = np.nonzero(need | rough)[0]
    if len(pick):
        origins = cen[pick] - np.array([0, 0, 0.01])
        hit = m.ray.intersects_any(origins, np.tile([0, 0, -1.0], (len(pick), 1)))
        blocked[pick] = hit
    out = {"bed_contact_mm2": round(float(area[bed].sum()), 1),
           "height_mm": round(float(m.bounds[1][2]), 1),
           "needs_support_mm2": round(float(area[need].sum()), 1),
           "needs_support_from_plate_mm2": round(float(area[need & ~blocked].sum()), 1),
           "unsupported_mm2": round(float(area[need & blocked].sum()), 1),
           "rough_unsupported_mm2": round(float(area[rough & blocked].sum()), 1)}
    regions = []
    inv = Rm.T
    for g in clusters(m, need & blocked):
        g = np.array(g)
        a = float(area[g].sum())
        if a < 0.5:
            continue
        pts = m.triangles[g].reshape(-1, 3)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        c = (cen[g] * area[g, None]).sum(axis=0) / a
        asm = inv @ (c - shift)
        regions.append({"area_mm2": round(a, 2), "print_z_mm": round(float(c[2]), 2),
                        "print_span_xy_mm": [round(float(hi[0] - lo[0]), 2), round(float(hi[1] - lo[1]), 2)],
                        "flattest_deg": round(float(slope[g].min()), 1),
                        "assembly_centre": [round(float(x), 2) for x in asm]})
    out["unsupported_regions"] = sorted(regions, key=lambda r: -r["area_mm2"])
    return out


def fit_axes(shape):
    """Cylindrical faces of the joints and spigot (r >= 5 mm): their axes, in assembly coordinates."""
    rows = {}
    for f in shape.Faces():
        if f.geomType() != "CYLINDER":
            continue
        cyl = f._geomAdaptor().Cylinder()
        rad = cyl.Radius()
        if rad < 5.0 or f.Area() < 20.0:
            continue
        d = cyl.Axis().Direction()
        k = tuple(round(abs(c), 2) for c in (d.X(), d.Y(), d.Z()))
        rows.setdefault(str(k), 0.0)
        rows[str(k)] += f.Area()
    return {k: round(v, 1) for k, v in rows.items()}


def main():
    report = {}
    for name, step in PARTS.items():
        shape = load(step)
        m = mesh_of(shape, name)
        report[name] = {"fit_cylinders_by_axis_mm2": fit_axes(shape),
                        "orientations": {label: analyse(m, rot) for label, rot in ROT.items()}}
        print(name, "cylinders r>=5 by axis:", report[name]["fit_cylinders_by_axis_mm2"], flush=True)
        for label, o in report[name]["orientations"].items():
            print(f"   {label:22s} bed {o['bed_contact_mm2']:7.1f}  h {o['height_mm']:5.1f}  needs {o['needs_support_mm2']:7.1f}"
                  f"  plate {o['needs_support_from_plate_mm2']:7.1f}  UNSUPPORTED {o['unsupported_mm2']:7.1f}"
                  f"  rough-unsup {o['rough_unsupported_mm2']:7.1f}  regions {len(o['unsupported_regions'])}", flush=True)
    (FILES / "printability_r41.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
