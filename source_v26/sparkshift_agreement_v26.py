"""v26 agreement audit: every place where faces, edges or neighbouring parts do not agree.

Per printed part (assembly coordinates, captured pose):
  kink       adjacent faces meeting at 0.05-20 degrees (should be one face or a clear corner)
  knife      convex edge whose faces fold back past 150 degrees (a sharp spike of material)
  crevice    concave edge past 150 degrees (a needle-thin slot)
  tip        face boundary corner under 12 degrees (spike tip or needle slit in a face)
  short      edge shorter than 0.5 mm
  narrow     face narrower than 0.35 mm (2 * area / perimeter)
  step       parallel same-facing planes 0-0.6 mm apart within 1 mm of each other
  skew       same-facing planes 0.005-3 degrees apart within 1 mm of each other
  thin_wall  opposed planes enclosing material thinner than 0.8 mm
  crack      opposed planes facing each other across a gap under 0.3 mm
  bands      coaxial cylinders differing by under 0.6 mm, or near-coaxial arcs
Across parts:
  near_flush same-facing planes of two parts 0-0.8 mm apart and side by side
"""

import json
import math
import sys
from contextlib import contextmanager
from pathlib import Path

import adsk.core
import adsk.fusion


OUT = Path(__file__).resolve().parent / "sparkshift_agreement_v26"
P01 = "PRINT_motor_mount"
P02 = "PRINT_REAR_MOTOR_SERVO_SPACER"
P03 = "PRINT_000_outer_shell_of_extruder_1"
P04R = "PRINT_carrier_box_left"
P04F = "PRINT_arm_front_half"
STATE = {}


def g22():
    return sys.modules["sparkshift_blue_half_v22"]


def front():
    return sys.modules["sparkshift_front_half_only_v21"]


def tools():
    return sys.modules["sparkshift_open_frame_v19"]


def geometry():
    return tools().geometry()


def write(name, value):
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(value, indent=1, default=str) + "\n", encoding="utf-8")


def world_of(name):
    s, _ = geometry()
    if name in STATE.get("candidates", {}):
        shape = s.tbm().copy(STATE["candidates"][name])
        if not s.tbm().transform(shape, STATE["matrices"][name]):
            raise RuntimeError("Candidate placement failed: " + name)
        return shape
    return STATE["world"][name]


@contextmanager
def bound(placement=False):
    module = g22()
    saved = (module.STATE, module.OUT, module.world_of)
    module.STATE, module.OUT = STATE, OUT
    if placement:
        module.world_of = world_of
    try:
        yield module
    finally:
        module.STATE, module.OUT, module.world_of = saved


def capture(app, ui):
    with bound() as module:
        report = module.capture(app, ui, "USER_live_input_v26")
    STATE["candidates"] = {}
    return report


def prints():
    return sorted(n for n in STATE["world"] if n.startswith("PRINT_"))


# ---------------------------------------------------------------- vector helpers (mm)
def V(*c):
    return adsk.core.Vector3D.create(*c)


def mm(p):
    return [p.x * 10, p.y * 10, p.z * 10]


def sub(a, b):
    return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def unit(v):
    n = math.sqrt(dot(v, v))
    return [c / n for c in v] if n > 1e-12 else None


def angle(a, b):
    return math.degrees(math.acos(max(-1.0, min(1.0, dot(a, b)))))


def box(entity):
    b = entity.boundingBox
    return [b.minPoint.x * 10, b.minPoint.y * 10, b.minPoint.z * 10], \
        [b.maxPoint.x * 10, b.maxPoint.y * 10, b.maxPoint.z * 10]


def centre(entity):
    lo, hi = box(entity)
    return [(lo[i] + hi[i]) / 2 for i in range(3)]


def near(a, b, gap):
    return all(a[0][k] <= b[1][k] + gap and b[0][k] <= a[1][k] + gap for k in range(3))


def polyline(edge, tol=0.0003):
    ev = edge.evaluator
    ok, a, b = ev.getParameterExtents()
    if not ok:
        return []
    ok, pts = ev.getStrokes(a, b, tol)
    return [mm(p) for p in pts] if ok else []


def lead(pts, min_len=0.004):
    for q in pts[1:]:
        d = sub(q, pts[0])
        if math.sqrt(dot(d, d)) >= min_len:
            return unit(d)
    return unit(sub(pts[-1], pts[0])) if len(pts) > 1 else None


def outward(face, point):
    ok, n = face.evaluator.getNormalAtPoint(point)
    return [n.x, n.y, n.z] if ok else None


def face_samples(face, grid=7):
    """Points on the face from a parameter grid (mm), always including pointOnFace."""
    ev = face.evaluator
    out = [mm(face.pointOnFace)]
    try:
        r = ev.parametricRange()
        for i in range(grid):
            for j in range(grid):
                u = r.minPoint.x + (r.maxPoint.x - r.minPoint.x) * (i + 0.5) / grid
                v = r.minPoint.y + (r.maxPoint.y - r.minPoint.y) * (j + 0.5) / grid
                prm = adsk.core.Point2D.create(u, v)
                if ev.isParameterOnFace(prm):
                    ok, p = ev.getPointAtParameter(prm)
                    if ok:
                        out.append(mm(p))
    except Exception:
        pass
    return out


def on_face(face, point_mm, tol=0.002):
    p = adsk.core.Point3D.create(*(c / 10 for c in point_mm))
    ev = face.evaluator
    ok, prm = ev.getParameterAtPoint(p)
    if not ok or not ev.isParameterOnFace(prm):
        return False
    ok, q = ev.getPointAtParameter(prm)
    return ok and math.dist(mm(q), point_mm) < tol


# ---------------------------------------------------------------- per-part detectors
def edge_findings(body):
    OUT_ = adsk.fusion.PointContainment.PointOutsidePointContainment
    IN_ = adsk.fusion.PointContainment.PointInsidePointContainment
    rows = []
    for i, e in enumerate(body.edges):
        length = e.length * 10
        mid = None
        try:
            pts = polyline(e)
            mid = pts[len(pts) // 2] if pts else None
        except Exception:
            pass
        if length < 0.5:
            rows.append({"kind": "short", "edge": i, "length_mm": length, "at": mid})
        faces = list(e.faces)
        if len(faces) != 2 or faces[0] == faces[1]:
            continue
        ev = e.evaluator
        ok, a, b = ev.getParameterExtents()
        thetas, convex = [], []
        for t in (0.2, 0.5, 0.8):
            ok, p = ev.getPointAtParameter(a + (b - a) * t)
            if not ok:
                continue
            n1, n2 = outward(faces[0], p), outward(faces[1], p)
            if n1 is None or n2 is None:
                continue
            thetas.append(angle(n1, n2))
            d = unit(sub(n1, n2))
            if d:
                q = adsk.core.Point3D.create(p.x + d[0] * 5e-4, p.y + d[1] * 5e-4, p.z + d[2] * 5e-4)
                c = body.pointContainment(q)
                if c == OUT_:
                    convex.append(True)
                elif c == IN_:
                    convex.append(False)
        if not thetas:
            continue
        th = max(thetas)
        cv = (sum(convex) > len(convex) / 2) if convex else None
        kind = None
        if 0.05 < th < 20.0:
            kind = "kink"
        elif th > 150.0:
            kind = "knife" if cv else "crevice"
        if kind:
            rows.append({"kind": kind, "edge": i, "theta_deg": th, "theta_all": thetas, "convex": cv,
                         "length_mm": length, "at": mid,
                         "faces": [type(f.geometry).__name__ for f in faces]})
    return rows


def tip_findings(body, limit=12.0):
    rows = []
    for fi, f in enumerate(body.faces):
        for loop in f.loops:
            polys = []
            for ce in loop.coEdges:
                pts = polyline(ce.edge)
                if ce.isOpposedToEdge:
                    pts = pts[::-1]
                if len(pts) >= 2:
                    polys.append((pts, ce.edge))
            if len(polys) < 2:
                continue
            for j in range(len(polys)):
                pin, ein = polys[j]
                pout, eout = polys[(j + 1) % len(polys)]
                if math.dist(pin[-1], pout[0]) > 0.01:
                    continue
                back, fwd = lead(pin[::-1]), lead(pout)
                if back is None or fwd is None:
                    continue
                ang = angle(back, fwd)
                if ang < limit:
                    rows.append({"kind": "tip", "face": fi, "angle_deg": ang, "at": pout[0],
                                 "face_type": type(f.geometry).__name__, "face_area_mm2": f.area * 100,
                                 "edge_lengths_mm": [ein.length * 10, eout.length * 10]})
    return rows


def narrow_findings(body, limit=0.35):
    rows = []
    for fi, f in enumerate(body.faces):
        perimeter = sum(ce.edge.length for loop in f.loops for ce in loop.coEdges) * 10
        area = f.area * 100
        width = 2 * area / perimeter if perimeter > 0 else 0.0
        if width < limit:
            rows.append({"kind": "narrow", "face": fi, "width_mm": width, "area_mm2": area,
                         "face_type": type(f.geometry).__name__, "at": centre(f)})
    return rows


def planes_of(body):
    rows = []
    for fi, f in enumerate(body.faces):
        if not isinstance(f.geometry, adsk.core.Plane):
            continue
        p = f.pointOnFace
        n = outward(f, p)
        if n:
            rows.append({"face": fi, "obj": f, "n": n, "p": mm(p), "box": box(f), "area": f.area * 100})
    return rows


def plane_findings(body, step=0.6, wall=0.8, crack=0.3, gap=1.0):
    planes = planes_of(body)
    rows = []
    cos_par = math.cos(math.radians(3.0))
    for i in range(len(planes)):
        a = planes[i]
        for j in range(i + 1, len(planes)):
            b = planes[j]
            c = dot(a["n"], b["n"])
            if abs(c) < cos_par or not near(a["box"], b["box"], gap):
                continue
            ang = angle(a["n"], b["n"]) if c > 0 else 180 - angle(a["n"], b["n"])
            off = dot(a["n"], sub(b["p"], a["p"]))
            if c > 0:
                if ang > 0.005:
                    rows.append({"kind": "skew", "faces": [a["face"], b["face"]], "angle_deg": ang,
                                 "offset_mm": off, "at": a["p"], "at2": b["p"]})
                elif 1e-4 < abs(off) < step:
                    rows.append({"kind": "step", "faces": [a["face"], b["face"]], "offset_mm": off,
                                 "at": a["p"], "at2": b["p"], "areas": [a["area"], b["area"]]})
                continue
            if ang > 0.5 or abs(off) > max(wall, crack):
                continue
            kind = "thin_wall" if off < 0 and -off < wall else "crack" if 0 < off < crack else None
            if not kind:
                continue
            hits = []
            for q in face_samples(a["obj"], 6):
                proj = [q[k] + a["n"][k] * off for k in range(3)]
                if on_face(b["obj"], proj):
                    hits.append(q)
            if hits:
                rows.append({"kind": kind, "faces": [a["face"], b["face"]], "gap_mm": abs(off),
                             "at": hits[len(hits) // 2], "overlap_samples": len(hits)})
    return rows


def cylinder_findings(body, dr=0.6):
    cyl = []
    for fi, f in enumerate(body.faces):
        g = f.geometry
        if isinstance(g, adsk.core.Cylinder):
            cyl.append((fi, mm(g.origin), [g.axis.x, g.axis.y, g.axis.z], g.radius * 10, box(f)))
    rows = []
    for i in range(len(cyl)):
        fa, oa, aa, ra, ba = cyl[i]
        for j in range(i + 1, len(cyl)):
            fb, ob, ab, rb, bb = cyl[j]
            if abs(dot(aa, ab)) < math.cos(math.radians(0.05)) or not near(ba, bb, 0.5):
                continue
            d = sub(ob, oa)
            along = dot(d, aa)
            lateral = math.sqrt(max(0.0, dot(d, d) - along * along))
            if lateral < 0.002 and 1e-4 < abs(ra - rb) < dr:
                rows.append({"kind": "bands", "faces": [fa, fb], "radii_mm": [ra, rb], "axis_offset_mm": lateral,
                             "at": centre(body.faces.item(fa))})
            elif 0.002 <= lateral < 0.3 and abs(ra - rb) < 0.3:
                rows.append({"kind": "bands", "faces": [fa, fb], "radii_mm": [ra, rb], "axis_offset_mm": lateral,
                             "near_coaxial": True, "at": centre(body.faces.item(fa))})
    return rows


def loops_of(face, tol=0.0005):
    return [polyline(ce.edge, tol) for loop in face.loops for ce in loop.coEdges]


def decorate(body, rows):
    """Attach red overlay polylines and a viewing normal to each finding."""
    edges, faces = list(body.edges), list(body.faces)
    for r in rows:
        poly, normal = [], None
        try:
            if "edge" in r:
                e = edges[r["edge"]]
                poly = [polyline(e, 0.0003)]
                ns = []
                for f in e.faces:
                    n = outward(f, adsk.core.Point3D.create(*(c / 10 for c in r["at"]))) if r.get("at") else None
                    if n:
                        ns.append(n)
                if ns:
                    normal = unit([sum(n[k] for n in ns) for k in range(3)]) or ns[0]
            elif "face" in r:
                f = faces[r["face"]]
                poly = loops_of(f)
                normal = outward(f, f.pointOnFace)
            elif "faces" in r and isinstance(r["faces"][0], int):
                for fi in r["faces"]:
                    poly += loops_of(faces[fi])
                f = faces[r["faces"][0]]
                normal = outward(f, f.pointOnFace)
                if r["kind"] == "bands":
                    normal = None
        except Exception as error:
            r["decorate_error"] = str(error)[:200]
        r["poly"] = [[[round(c, 4) for c in p] for p in pl] for pl in poly if len(pl) > 1]
        r["n"] = normal
    return rows


def seam_findings(body):
    """Edges between two faces that lie on the same surface (an unnecessary split line)."""
    rows = []
    for i, e in enumerate(body.edges):
        fs = list(e.faces)
        if len(fs) != 2 or fs[0] == fs[1]:
            continue
        g1, g2 = fs[0].geometry, fs[1].geometry
        same = False
        if isinstance(g1, adsk.core.Plane) and isinstance(g2, adsk.core.Plane):
            same = g1.isCoPlanarTo(g2)
        elif isinstance(g1, adsk.core.Cylinder) and isinstance(g2, adsk.core.Cylinder):
            if abs(g1.radius - g2.radius) < 1e-7 and g1.axis.isParallelTo(g2.axis):
                d = sub(mm(g2.origin), mm(g1.origin))
                a = [g1.axis.x, g1.axis.y, g1.axis.z]
                along = dot(d, a)
                same = math.sqrt(max(0.0, dot(d, d) - along * along)) < 1e-5
        if same:
            pts = polyline(e)
            rows.append({"kind": "seam", "edge": i, "length_mm": e.length * 10,
                         "at": pts[len(pts) // 2] if pts else None,
                         "areas": [fs[0].area * 100, fs[1].area * 100]})
    return rows


def auto_plan(part, step_max=0.25, narrow_max=0.15, kink_max=1.0, band_max=0.12):
    """DeleteFace steps for unambiguous artifacts, computed on the native body."""
    body = STATE["definitions"][part]
    faces, edges = list(body.faces), list(body.edges)
    index = {f.tempId: i for i, f in enumerate(faces)}
    steps, used = [], set()

    def neighbours(fi):
        out = set()
        for e in faces[fi].edges:
            for f in e.faces:
                if index[f.tempId] != fi:
                    out.add(index[f.tempId])
        return out

    def add(kind, ids, dv, why):
        ids = sorted(set(ids))
        if any(i in used for i in ids):
            return
        used.update(ids)
        steps.append({"kind": "delete", "faces": [signature(faces[i]) for i in ids], "max_dv": dv,
                      "label": "V26 %s %s" % (kind, why), "auto": kind, "ids": ids,
                      "at": centre(faces[ids[0]])})

    for r in plane_findings(body, step=step_max):
        if r["kind"] not in ("step", "skew"):
            continue
        if r["kind"] == "skew" and r["angle_deg"] > kink_max:
            continue
        a, b = r["faces"]
        minor, major = (a, b) if faces[a].area < faces[b].area else (b, a)
        risers = [i for i in neighbours(minor) & neighbours(major)
                  if i not in (minor, major) and faces[i].area * 100 < 3.0]
        if r["kind"] == "skew":
            if major not in neighbours(minor):
                continue
            risers = []
        elif not risers:
            continue
        dv = faces[minor].area * 100 * (abs(r.get("offset_mm", 0.1)) + 0.05) + 0.05
        add("step", [minor] + risers, dv, "snap %.3f mm %s at (%.1f, %.1f, %.1f)" %
            (abs(r.get("offset_mm", 0.0)), r["kind"], *centre(faces[minor])))
    for r in edge_findings(body):
        if r["kind"] != "kink" or r["theta_deg"] > kink_max:
            continue
        e = edges[r["edge"]]
        fs = [index[f.tempId] for f in e.faces]
        if not all(isinstance(faces[i].geometry, adsk.core.Plane) for i in fs):
            continue
        minor = min(fs, key=lambda i: faces[i].area)
        add("kink", [minor], faces[minor].area * 100 * 0.2 + 0.05,
            "flatten %.2f deg kink at (%.1f, %.1f, %.1f)" % (r["theta_deg"], *(r["at"] or (0, 0, 0))))
    for r in cylinder_findings(body):
        if r.get("near_coaxial") or abs(r["radii_mm"][0] - r["radii_mm"][1]) > band_max:
            continue
        a, b = r["faces"]
        minor = a if faces[a].area < faces[b].area else b
        major = b if minor == a else a
        ring = [i for i in neighbours(minor) & neighbours(major) if i not in (minor, major)]
        if not ring:
            continue
        add("band", [minor] + ring, faces[minor].area * 100 * 0.2 + 0.05,
            "merge R%.3f into R%.3f at (%.1f, %.1f, %.1f)" % (r["radii_mm"][0], r["radii_mm"][1], *r["at"]))
    for r in seam_findings(body):
        e = edges[r["edge"]]
        fs = sorted((index[f.tempId] for f in e.faces), key=lambda i: faces[i].area)
        add("seam", [fs[0]], 0.02, "merge split face at (%.1f, %.1f, %.1f)" % tuple(r["at"] or (0, 0, 0)))
    for r in narrow_findings(body, narrow_max):
        add("sliver", [r["face"]], r["area_mm2"] * 0.6 + 0.02,
            "remove %.3f mm sliver at (%.1f, %.1f, %.1f)" % (r["width_mm"], *r["at"]))
    write("%s_auto_plan.json" % part, [{k: v for k, v in s.items() if k != "faces"} for s in steps])
    return steps


def face_card(face, i):
    g = face.geometry
    lo, hi = box(face)
    s = "f%d %s A=%.3f x[%.3f,%.3f] y[%.3f,%.3f] z[%.3f,%.3f]" % (
        i, type(g).__name__[:3], face.area * 100, lo[0], hi[0], lo[1], hi[1], lo[2], hi[2])
    n = outward(face, face.pointOnFace)
    if isinstance(g, adsk.core.Plane):
        s += " n(%.4f,%.4f,%.4f) d=%.4f" % (n[0], n[1], n[2], dot(n, mm(face.pointOnFace)))
    elif isinstance(g, adsk.core.Cylinder):
        o = mm(g.origin)
        s += " R=%.4f c(%.3f,%.3f,%.3f) ax(%.3f,%.3f,%.3f) %s" % (
            g.radius * 10, o[0], o[1], o[2], g.axis.x, g.axis.y, g.axis.z,
            "out" if dot(n, sub(mm(face.pointOnFace), o)) > 0 else "in")
    elif isinstance(g, adsk.core.Cone):
        s += " cone half=%.2f" % math.degrees(g.halfAngle)
    elif isinstance(g, adsk.core.Torus):
        s += " torus R=%.3f r=%.3f" % (g.majorRadius * 10, g.minorRadius * 10)
    return s


def cards(name, clusters_json, ids=None):
    """Text cards: faces involved in each cluster plus their immediate neighbours."""
    body = world_of(name)
    faces, edges = list(body.faces), list(body.edges)
    index = {f.tempId: i for i, f in enumerate(faces)}
    meta = json.loads((OUT / clusters_json).read_text(encoding="utf-8"))
    lines = []
    for c in meta:
        if ids is not None and c["id"] not in ids:
            continue
        involved = set()
        for mbr in c["members"]:
            if "edge" in mbr:
                involved |= {index[f.tempId] for f in edges[mbr["edge"]].faces}
            if "face" in mbr:
                involved.add(mbr["face"])
            if isinstance(mbr.get("faces"), list) and mbr["faces"] and isinstance(mbr["faces"][0], int):
                involved |= set(mbr["faces"])
        lines.append("#%d %s %s | %s" % (c["id"], c["centre"], c["kinds"], c["detail"]))
        for i in sorted(involved, key=lambda k: faces[k].area):
            lines.append("   " + face_card(faces[i], i))
    path = OUT / ("cards_%s.txt" % name[:14])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def mating_map(part, limit=0.35):
    """For each face of the part (world pose): nearest other body within `limit` mm, fixed or moving."""
    module = g22()
    measure = adsk.core.Application.get().measureManager
    body = STATE["world"][part]
    faces = list(body.faces)
    shapes = []
    for n, b in STATE["world"].items():
        if n == part or n.startswith("REFERENCE_"):
            continue
        if STATE["paths"][n][:2] in module.MOVING:
            continue
        shapes.append((n, b))
    with bound(placement=True):
        for angle in (0.0, 87.5, 175.0):
            arm, frame_map = module.frames(angle)
            for n, path in STATE["paths"].items():
                if path[:2] in module.MOVING and n != part and not n.startswith("REFERENCE_"):
                    shapes.append(("%s@%g" % (n, angle), module.place(n, module.world_of(n), frame_map)))
    boxes = [(n, b, box(b)) for n, b in shapes]
    s, _ = geometry()
    out = {}
    for i, f in enumerate(faces):
        fb = box(f)
        sheet = None
        best = None
        for n, b, bb in boxes:
            if not near(fb, bb, limit):
                continue
            if sheet is None:
                sheet = s.tbm().copy(f)
            d = measure.measureMinimumDistance(sheet, b).value * 10
            if d < limit and (best is None or d < best[1]):
                best = (n, d)
        if best:
            out[i] = best
    STATE.setdefault("mating", {})[part] = out
    write("mating_%s.json" % part[:14], {str(k): v for k, v in out.items()})
    return len(out)


def plane_sheet(point, normal, size=300.0):
    """A large planar sheet (one face) on the plane through `point` with `normal` (mm)."""
    s, _ = geometry()
    n = unit(list(normal))
    helper = [0, 1, 0] if abs(n[1]) < 0.9 else [1, 0, 0]
    a = unit([n[1] * helper[2] - n[2] * helper[1], n[2] * helper[0] - n[0] * helper[2],
              n[0] * helper[1] - n[1] * helper[0]])
    b = [n[1] * a[2] - n[2] * a[1], n[2] * a[0] - n[0] * a[2], n[0] * a[1] - n[1] * a[0]]
    t = 1.0
    c = [point[k] - n[k] * t / 2 for k in range(3)]
    shape = s.tbm().createBox(adsk.core.OrientedBoundingBox3D.create(
        adsk.core.Point3D.create(*(v / 10 for v in c)), V(*a), V(*b), size / 10, size / 10, t / 10))
    best = max(shape.faces, key=lambda f: dot(outward(f, f.pointOnFace) or [0, 0, 0], n))
    return s.tbm().copy(best)


def cyl_sheet(cx, cz, y0, y1, r):
    s, _ = geometry()
    shape = s.cyl(cx, cz, y0, y1, r)
    return s.tbm().copy(next(f for f in shape.faces if isinstance(f.geometry, adsk.core.Cylinder)))


def tube(cx, cz, y0, y1, r_in, r_out):
    s, _ = geometry()
    t = s.cyl(cx, cz, y0, y1, r_out)
    s.op(t, s.cyl(cx, cz, y0 - 1.0, y1 + 1.0, r_in), "cut")
    return t


def face_index(part, i):
    return signature(STATE["definitions"][part].faces.item(i))


TOP = 62.22059521522819  # P01 top = cam axis + 11.5; P02 must agree exactly


def plan_p01_batch1():
    P = lambda i: face_index(P01, i)
    nx, nz = -(TOP - 48.7), 14.0
    L = math.hypot(nx, nz)
    steps = [
        {"kind": "replace", "faces": [P(10)], "guide": plane_sheet((-22.5, 5.0, 48.7), (nx / L, 0, nz / L)),
         "label": "P01 chamfer starts exactly at the side-wall corner (no 0.69 mm ledge)", "max_dv": 50.0},
        {"kind": "replace", "faces": [P(233)], "guide": cyl_sheet(21.0, TOP - 1.5, -2.0, 14.0, 1.5),
         "label": "P01 top-right R1.5 round tangent to top and side", "max_dv": 0.05},
        {"kind": "delete", "faces": [P(186)], "max_dv": 0.05, "label": "P01 remove 5 um R3.78 sliver at motor flange"},
        {"kind": "replace", "faces": [P(227)], "guide": plane_sheet((-2.25, 3.0, -14.5), (1, 0, 0)), "max_dv": 0.3,
         "label": "P01 Hall-slot wedge made coplanar with the X-2.25 wall"},
        {"kind": "combine", "op": "join", "shape": tube(-18.0, -52.78, 15.3, 15.9, 2.27, 2.6), "max_dv": 1.5,
         "label": "P01 left hole: remove the 0.15 mm counterbore ring"},
        {"kind": "combine", "op": "join", "shape": tube(18.0, -52.78, 15.3, 15.9, 2.27, 2.6), "max_dv": 1.5,
         "label": "P01 right hole: remove the 0.15 mm counterbore ring"},
        {"kind": "delete", "faces": [P(50), P(51)], "max_dv": 0.2, "label": "P01 gear cavity micro faces at X17.7"},
        {"kind": "delete", "faces": [P(153)], "max_dv": 1.0, "label": "P01 0.2 mm sliver at the R5.5 boss"},
        {"kind": "replace", "faces": [P(173)], "guide": plane_sheet((3.8, 11.0, 26.4406), (0, 0, -1)),
         "label": "P01 tiny tilted ceiling made level at Z26.4406", "max_dv": 0.05},
        {"kind": "delete", "faces": [P(123)], "max_dv": 2.0,
         "label": "P01 close the 0.2 mm crack between the ledge and the X20.5 wall"},
    ]
    for st in auto_plan(P01):
        if st["auto"] == "step":
            steps.append(st)
    return steps


def plan_p02_batch1():
    P = lambda i: face_index(P02, i)
    return [
        {"kind": "delete", "faces": [P(43)], "max_dv": 3.6,
         "label": "P02 top-left corner square - agrees with P03 and the P01 side wall"},
        {"kind": "replace", "faces": [P(8)], "guide": plane_sheet((10.0, -3.0, TOP), (0, 0, 1)),
         "label": "P02 top exactly level with the P01 top", "max_dv": 0.2},
        {"kind": "delete", "faces": [P(60)], "max_dv": 3.5,
         "label": "P02 top-right corner reset before the tangent round"},
        {"kind": "fillet", "edges": [{"at": [22.5, -3.2, TOP], "dir": [0, 1, 0]}], "radius": 1.5, "max_dv": 3.5,
         "label": "P02 top-right R1.5 round tangent to top and side (matches P01)"},
    ]


def plan_p03_batch1():
    P = lambda i: face_index(P03, i)
    bridge, _ = STATE["p03_slit_tools"]
    sweep = STATE["definitions"][P03].faces.item(67).geometry
    so, sr = mm(sweep.origin), sweep.radius * 10
    return [
        {"kind": "combine", "op": "join", "shape": bridge, "max_dv": 5.6,
         "label": "P03 close the see-through slit between the magnet pocket and the arm pocket"},
        {"kind": "delete", "faces": [P(61), P(55)], "max_dv": 1.5, "label": "P03 rib lower end runs cleanly into the R7 wall"},
        {"kind": "delete", "faces": [P(63), P(58)], "max_dv": 1.5, "label": "P03 rib upper end runs cleanly into the R7 wall"},
        {"kind": "delete", "faces": [P(69), P(70)], "max_dv": 3.0,
         "label": "P03 remove the R4.35 pocket remnant (0.3 mm spike) between the R7 and slanted walls"},
        {"kind": "replace", "faces": [P(2)], "guide": cyl_sheet(so[0], so[2], 20.0, 35.0, sr),
         "max_dv": 1.0, "label": "P03 arm-tip sweep one radius (R26.582 band merged into R26.635)"},
        {"kind": "delete", "faces": [P(222)], "max_dv": 0.5, "label": "P03 remove the 0.1 mm ledge strip at X-3.2"},
        {"kind": "delete", "faces": [P(133)], "max_dv": 0.05, "label": "P03 remove the 4 um micro step at X-3.2"},
    ]


def circle_fit(points):
    """Kasa least-squares circle through XZ points; returns (cx, cz, r_fit, r_max)."""
    sx = sz = sxx = szz = sxz = sb = sxb = szb = 0.0
    n = len(points)
    for x, z in points:
        b = x * x + z * z
        sx += x; sz += z; sxx += x * x; szz += z * z; sxz += x * z; sb += b; sxb += x * b; szb += z * b
    a = [[2 * sxx, 2 * sxz, sx], [2 * sxz, 2 * szz, sz], [2 * sx, 2 * sz, n]]
    y = [sxb, szb, sb]
    for i in range(3):
        p = max(range(i, 3), key=lambda r: abs(a[r][i]))
        a[i], a[p], y[i], y[p] = a[p], a[i], y[p], y[i]
        for r in range(i + 1, 3):
            f = a[r][i] / a[i][i]
            for c in range(i, 3):
                a[r][c] -= f * a[i][c]
            y[r] -= f * y[i]
    sol = [0.0] * 3
    for i in (2, 1, 0):
        sol[i] = (y[i] - sum(a[i][c] * sol[c] for c in range(i + 1, 3))) / a[i][i]
    cx, cz, k = sol
    r = math.sqrt(k + cx * cx + cz * cz)
    return cx, cz, r, max(math.hypot(x - cx, z - cz) for x, z in points)


def facet_bands(part, keys):
    b = STATE["definitions"][part]
    out = {}
    for i, f in enumerate(b.faces):
        if not isinstance(f.geometry, adsk.core.Plane):
            continue
        n = outward(f, f.pointOnFace)
        if n is None or abs(n[1]) > 0.01:
            continue
        lo, hi = box(f)
        if math.hypot(hi[0] - lo[0], hi[2] - lo[2]) >= 0.6:
            continue
        key = "%.3f..%.3f" % (lo[1], hi[1])
        if key in keys:
            pts = []
            for e in f.edges:
                for v in (e.startVertex, e.endVertex):
                    p = mm(v.geometry)
                    pts.append((p[0], p[2]))
            row = out.setdefault(key, {"faces": [], "pts": [], "y": (lo[1], hi[1])})
            row["faces"].append(i)
            row["pts"] += pts
    return out


def plan_p04r_batch1():
    keys = ("9.200..9.350", "7.000..9.200", "4.850..9.200", "4.700..4.850")
    bands = facet_bands(P04R, keys)
    steps = []
    for key in keys:
        row = bands[key]
        cx, cz, r, rmax = circle_fit(row["pts"])
        sigs = [face_index(P04R, i) for i in row["faces"]]
        steps.append({"kind": "replace", "faces": sigs, "guide": cyl_sheet(cx, cz, row["y"][0] - 2, row["y"][1] + 2, rmax + 0.0005),
                      "max_dv": 1.5, "fit": [cx, cz, r, rmax, len(row["faces"])],
                      "label": "P04R cam clearance Y%s: %d facets -> one R%.3f cylinder" % (key, len(row["faces"]), rmax + 0.0005)})
    return steps


def find_edge(body, spec, tol=0.003):
    """Edge passing through spec['at'] (mm), optionally a line along spec['dir']."""
    p = adsk.core.Point3D.create(*(c / 10 for c in spec["at"]))
    hits = []
    for e in body.edges:
        ev = e.evaluator
        ok, a, b = ev.getParameterExtents()
        ok2, t = ev.getParameterAtPoint(p)
        if not (ok and ok2) or t < min(a, b) - 1e-9 or t > max(a, b) + 1e-9:
            continue
        ok3, q = ev.getPointAtParameter(t)
        if not ok3 or q.distanceTo(p) * 10 > tol:
            continue
        if "dir" in spec:
            g = e.geometry
            if not isinstance(g, adsk.core.Line3D):
                continue
            d = unit(sub(mm(g.endPoint), mm(g.startPoint)))
            if abs(dot(d, unit(spec["dir"]))) < 0.9999:
                continue
        hits.append(e)
    if len(hits) != 1:
        raise RuntimeError("Edge spec %s matched %d edges" % (spec, len(hits)))
    return hits[0]


def audit_part(name, tag=""):
    body = world_of(name)
    rows = []
    for fn in (edge_findings, tip_findings, narrow_findings, plane_findings, cylinder_findings, seam_findings):
        try:
            rows += fn(body)
        except Exception as error:
            rows.append({"kind": "detector_error", "detector": fn.__name__, "error": str(error)[:300]})
    decorate(body, rows)
    for r in rows:
        r["part"] = name
    STATE.setdefault("findings", {})[name + tag] = rows
    write("findings_%s%s.json" % (name, tag), rows)
    counts = {}
    for r in rows:
        counts[r["kind"]] = counts.get(r["kind"], 0) + 1
    return counts


# ---------------------------------------------------------------- fix plans (native coordinates)
def signature(face):
    """Re-findable description of a face: sample points with normals, surface type, area."""
    rows = []
    for p in face_samples(face, 4)[:6]:
        n = outward(face, adsk.core.Point3D.create(*(c / 10 for c in p)))
        if n:
            rows.append({"p": p, "n": n})
    return {"type": type(face.geometry).__name__, "samples": rows, "area": face.area * 100}


def find_face(body, sig, tol=0.002):
    hits = []
    for f in body.faces:
        if type(f.geometry).__name__ != sig["type"]:
            continue
        for row in sig["samples"]:
            if on_face(f, row["p"], tol):
                n = outward(f, adsk.core.Point3D.create(*(c / 10 for c in row["p"])))
                if n and dot(n, row["n"]) > 0.9999:
                    hits.append(f)
                    break
    if len(hits) != 1:
        raise RuntimeError("Face signature matched %d faces (%s, area %.4f)" % (len(hits), sig["type"], sig["area"]))
    return hits[0]


def add_body(component, shape, label):
    s, _ = geometry()
    feature = component.features.baseFeatures.add()
    feature.name = label
    if not feature.startEdit():
        raise RuntimeError("Could not start " + label)
    try:
        component.bRepBodies.add(s.tbm().copy(shape), feature)
    finally:
        if not feature.finishEdit():
            raise RuntimeError("Could not finish " + label)
    return feature.bodies.item(0), feature


def collection(items):
    c = adsk.core.ObjectCollection.create()
    for item in items:
        c.add(item)
    return c


def healthy(feature, label):
    ok = adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState
    if feature is None or feature.healthState != ok:
        raise RuntimeError(label + ": " + (feature.errorOrWarningMessage if feature else "not created"))


def run_steps(component, part, steps, strict=True):
    """Apply combine/delete/replace steps to one body; non-strict mode skips and reports failures."""
    names, failures = [], []
    J, C = adsk.fusion.FeatureOperations.JoinFeatureOperation, adsk.fusion.FeatureOperations.CutFeatureOperation
    for step in steps:
        label = step["label"]
        body = component.bRepBodies.itemByName(part)
        before_volume = body.volume * 1000
        created = []
        try:
            if step["kind"] == "combine":
                tool, base = add_body(component, step["shape"], "V26 TOOL " + label)
                created.append(base)
                inp = component.features.combineFeatures.createInput(body, collection([tool]))
                inp.operation = J if step["op"] == "join" else C
                inp.isKeepToolBodies = False
                feature = component.features.combineFeatures.add(inp)
                created.append(feature)
                healthy(feature, label)
            elif step["kind"] == "delete":
                faces = [find_face(body, sg) for sg in step["faces"]]
                feature = component.features.deleteFaceFeatures.add(collection(faces))
                created.append(feature)
                healthy(feature, label)
            elif step["kind"] == "replace":
                faces = [find_face(body, sg) for sg in step["faces"]]
                guide, base = add_body(component, step["guide"], "V26 GUIDE " + label)
                created.append(base)
                inp = component.features.replaceFaceFeatures.createInput(collection(faces), False, collection([guide]))
                feature = component.features.replaceFaceFeatures.add(inp)
                created.append(feature)
                healthy(feature, label)
                removal = component.features.removeFeatures.add(base.bodies.item(0))
                created.append(removal)
                removal.name = "Remove V26 guide " + label[:40]
            elif step["kind"] == "fillet":
                edges = [find_edge(body, sp) for sp in step["edges"]]
                inp = component.features.filletFeatures.createInput()
                radius = adsk.core.ValueInput.createByReal(step["radius"] / 10)
                try:
                    inp.edgeSetInputs.addConstantRadiusEdgeSet(collection(edges), radius, False)
                except AttributeError:
                    inp.addConstantRadiusEdgeSet(collection(edges), radius, False)
                feature = component.features.filletFeatures.add(inp)
                created.append(feature)
                healthy(feature, label)
            else:
                raise RuntimeError("Unknown step kind " + step["kind"])
            feature.name = label
            body = component.bRepBodies.itemByName(part)
            if body is None or body.lumps.count != 1 or not body.isSolid:
                raise RuntimeError(label + ": result is not one solid")
            change = abs(body.volume * 1000 - before_volume)
            if "max_dv" in step and change > step["max_dv"]:
                raise RuntimeError("%s: volume change %.4f mm3 exceeds %.4f" % (label, change, step["max_dv"]))
            STATE.setdefault("step_dv", {})[label] = body.volume * 1000 - before_volume
            STATE.setdefault("applied_steps", []).append(step)
            names.append(label)
        except Exception as error:
            if strict:
                raise
            for f in reversed(created):
                try:
                    if f.isValid:
                        f.deleteMe()
                except Exception:
                    pass
            failures.append({"label": label, "error": str(error)[:300]})
    body = component.bRepBodies.itemByName(part)
    tools().one_solid(body, "Revised " + part)
    return body, names, failures


def prototype(app, part, steps, strict=False):
    """Run a plan in a temporary document; the native result becomes the candidate."""
    s, _ = geometry()
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "TEMP - v26 %s prototype" % part
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        component = design.rootComponent
        base = component.features.baseFeatures.add()
        if not base.startEdit():
            raise RuntimeError("Could not start the prototype input")
        try:
            component.bRepBodies.add(s.tbm().copy(STATE["definitions"][part]), base)
        finally:
            if not base.finishEdit():
                raise RuntimeError("Could not finish the prototype input")
        base.bodies.item(0).name = part
        STATE["applied_steps"] = []
        body, names, failures = run_steps(component, part, steps, strict)
        applied_steps = list(STATE["applied_steps"])
        native = s.tbm().copy(body)
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the prototype document")
        source.activate()
    STATE["candidates"][part] = native
    STATE.setdefault("plans", {})[part] = applied_steps
    report = {"applied": names, "failed": failures, "before": tools().stats(STATE["definitions"][part]),
              "candidate": tools().stats(native)}
    write("%s_prototype.json" % part, report)
    return report


def apply_live(app, ui, part):
    g22().require_idle(ui, allow_view=False)
    design = adsk.fusion.Design.cast(app.activeProduct)
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the captured live assembly")
    if design.timeline.count != STATE["timeline_count"]:
        raise RuntimeError("The live timeline changed since capture/last apply; recapture first")
    by, _ = front().inventory(design)
    body = by[part].nativeObject
    if front().exact(STATE["definitions"][part], body, "live %s before v26" % part):
        raise RuntimeError("The live %s changed after capture" % part)
    result, names, failures = run_steps(body.parentComponent, part, STATE["plans"][part], strict=True)
    delta = front().exact(STATE["candidates"][part], result, "applied %s v26" % part)
    if delta:
        raise RuntimeError("The live %s differs from the reviewed candidate: %.6f mm3" % (part, delta))
    s, _ = geometry()
    STATE["timeline_count"] = design.timeline.count
    STATE["definitions"][part] = s.tbm().copy(STATE["candidates"][part])
    STATE["world"][part] = world_of(part)
    del STATE["candidates"][part]
    applied = STATE.setdefault("applied", [])
    applied.append({"part": part, "features": names, "timeline_after": design.timeline.count})
    write("live_application.json", applied)
    return applied[-1]


def flush_findings(names, gap=0.8, adjacency=0.6):
    planes = {n: planes_of(world_of(n)) for n in names}
    rows = []
    cos_par = math.cos(math.radians(1.0))
    for i, na in enumerate(names):
        for nb in names[i + 1:]:
            for a in planes[na]:
                for b in planes[nb]:
                    if dot(a["n"], b["n"]) < cos_par or not near(a["box"], b["box"], adjacency):
                        continue
                    off = dot(a["n"], sub(b["p"], a["p"]))
                    ang = angle(a["n"], b["n"])
                    if (1e-4 < abs(off) < gap) or (0.005 < ang and abs(off) < gap):
                        rows.append({"kind": "near_flush", "parts": [na, nb], "faces": [a["face"], b["face"]],
                                     "offset_mm": off, "angle_deg": ang, "normal": a["n"],
                                     "at": a["p"], "at2": b["p"], "areas": [a["area"], b["area"]]})
    STATE["flush"] = rows
    write("findings_cross_part_flush.json", rows)
    return len(rows)


# ---------------------------------------------------------------- export for offline rendering
def export_scene(names, filename, tolerance=0.002, edge_tol=0.0005, bodies=None):
    """Write world-space meshes and BRep edge polylines (mm) for the offline VTK renderer."""
    scene = {}
    for name in names:
        body = (bodies or {}).get(name) or world_of(name)
        calc = body.meshManager.createMeshCalculator()
        calc.surfaceTolerance = tolerance
        calc.maxNormalDeviation = math.radians(8)
        mesh = calc.calculate()
        nodes = [round(v * 10, 5) for v in mesh.nodeCoordinatesAsDouble]
        edges = []
        for e in body.edges:
            try:
                pts = polyline(e, edge_tol)
            except Exception:
                pts = []
            if len(pts) > 1:
                edges.append([[round(c, 5) for c in p] for p in pts])
        scene[name] = {"nodes": nodes, "tris": list(mesh.nodeIndices), "edges": edges}
    (OUT / "scene").mkdir(parents=True, exist_ok=True)
    (OUT / "scene" / filename).write_text(json.dumps(scene), encoding="utf-8")
    return {n: {"tris": len(v["tris"]) // 3, "edges": len(v["edges"])} for n, v in scene.items()}


def sections(names, step=0.5):
    """Y sections of each part (polylines in XZ, mm) for silhouette agreement checks."""
    s, _ = geometry()
    T = s.tbm()
    out = {}
    for name in names:
        body = world_of(name)
        lo, hi = box(body)
        levels = []
        y = math.floor(lo[1] / step) * step + step / 2
        while y < hi[1]:
            levels.append(round(y, 4))
            y += step
        rows = {}
        for y in levels:
            wire = None
            for nudge in (0.0, 0.0013, -0.0021):
                try:
                    wire = T.planeIntersection(T.copy(body), adsk.core.Plane.create(
                        adsk.core.Point3D.create(0, (y + nudge) / 10, 0), V(0, 1, 0)))
                    break
                except Exception:
                    wire = None
            if wire is None:
                continue
            lines = []
            for e in wire.edges:
                pts = polyline(e, 0.0005)
                if len(pts) > 1:
                    lines.append([[round(p[0], 4), round(p[2], 4)] for p in pts])
            rows[str(y)] = lines
        out[name] = rows
    write("sections_y.json", out)
    return {n: len(v) for n, v in out.items()}

# ---------------------------------------------------------------- audits / release (v25 machinery, v26 state)
def v25():
    return sys.modules["sparkshift_cleanup_v25"]


@contextmanager
def as_v25():
    mod = v25()
    saved = (mod.STATE, mod.OUT, mod.world_of)
    mod.STATE, mod.OUT, mod.world_of = STATE, OUT, world_of
    try:
        yield mod
    finally:
        mod.STATE, mod.OUT, mod.world_of = saved


def audit_static(part):
    with as_v25() as mod:
        return mod.audit_static(part)


def audit_motion(part, angles, label):
    with as_v25() as mod:
        return mod.audit_motion(part, angles, label)


def audit_tool(parts, label):
    with as_v25() as mod:
        return mod.audit_tool(parts, label)


def audit_feed(parts, label):
    with as_v25() as mod:
        return mod.audit_feed(parts, label)


def added_clearance(part, label, arm_samples=33, cam_samples=73):
    with as_v25() as mod:
        return mod.added_clearance(part, label, arm_samples, cam_samples)


def freeze(app, label="SparkShift_v26_agreement_audit_WIP"):
    with as_v25() as mod:
        return mod.freeze(app, label)


def readback(app, count=200):
    with as_v25() as mod:
        return mod.readback(app, count)


def close_readback(app):
    with as_v25() as mod:
        return mod.close_readback(app)


def export_prints(app, mapping):
    with bound() as module:
        saved = module.PRINTS
        module.PRINTS = mapping
        try:
            return module.export_meshes(app)
        finally:
            module.PRINTS = saved


def xz_slice(body, y, xr, zr):
    """XZ section polylines of `body` at Y=y (mm), clipped to a box."""
    pl = adsk.core.Plane.create(adsk.core.Point3D.create(0, y / 10, 0), V(0, 1, 0))
    wire = adsk.fusion.TemporaryBRepManager.get().planeIntersection(body, pl)
    segs = []
    if wire:
        for e in wire.edges:
            pts = polyline(e, 0.0003)
            if any(xr[0] <= p[0] <= xr[1] and zr[0] <= p[2] <= zr[1] for p in pts):
                segs.append([[round(p[0], 4), round(p[2], 4)] for p in pts])
    return segs


def prism_xz(points, y0, y1):
    """Solid prism from an XZ polygon (mm) extruded over Y [y0, y1]."""
    tbm = adsk.fusion.TemporaryBRepManager.get()
    curves = []
    n = len(points)
    for i in range(n):
        a, b = points[i], points[(i + 1) % n]
        curves.append(adsk.core.Line3D.create(adsk.core.Point3D.create(a[0] / 10, y0 / 10, a[1] / 10),
                                              adsk.core.Point3D.create(b[0] / 10, y0 / 10, b[1] / 10)))
    wire, _ = tbm.createWireFromCurves(curves)
    face = tbm.createFaceFromPlanarWires([wire])
    if face is None:
        raise RuntimeError("Prism profile failed")
    shape = face
    s, _ = geometry()
    # sweep the planar face along +Y by thickening is not exposed; use a ruled loft-free route:
    return tools().extrude_face(face, (y1 - y0)) if hasattr(tools(), "extrude_face") else None


def moving_added_check(part, step=2.5, near_mm=1.0):
    """Added material of a moving part, carried with it over the motion, versus every other body."""
    s, _ = geometry()
    measure = adsk.core.Application.get().measureManager
    added = s.tbm().copy(STATE["candidates"][part])
    s.op(added, s.tbm().copy(STATE["definitions"][part]), "cut")
    if added.volume * 1000 < 1e-6:
        return {"added_mm3": 0.0, "closest": []}
    if not s.tbm().transform(added, STATE["matrices"][part]):
        raise RuntimeError("Placement failed")
    best, overlaps = {}, {}
    with bound(placement=True) as mod:
        for k in range(int(175.0 / step) + 1):
            ang = k * step
            arm, fm = mod.frames(ang)
            piece = mod.place(part, added, fm)
            pb = box(piece)
            for n, path in STATE["paths"].items():
                if n == part or n.startswith("REFERENCE_"):
                    continue
                other = mod.place(n, mod.world_of(n), fm) if path[:2] in mod.MOVING else STATE["world"][n]
                if not near(pb, box(other), near_mm):
                    continue
                d = measure.measureMinimumDistance(piece, other).value * 10
                if d < 1e-6:
                    v, _ = s.common_volume(piece, other)
                    if v > 1e-6:
                        overlaps[n] = max(overlaps.get(n, 0.0), v)
                if n not in best or d < best[n][0]:
                    best[n] = (round(d, 4), ang)
    report = {"added_mm3": added.volume * 1000, "overlaps": overlaps,
              "closest": sorted(best.items(), key=lambda kv: kv[1][0])[:10]}
    write("%s_moving_added_check.json" % part, report)
    return report


def profile_prisms(app, profiles, y0, y1):
    """Exact prisms (TBM) from closed XZ profiles; each profile = list of ("line", p0, p1) / ("arc", p0, pm, p1) in mm."""
    s, _ = geometry()
    tbm = s.tbm()
    source = app.activeDocument
    document = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    document.name = "TEMP - v26 profile prisms"
    out = []
    try:
        design = adsk.fusion.Design.cast(document.products.itemByProductType("DesignProductType"))
        design.designType = adsk.fusion.DesignTypes.ParametricDesignType
        root = design.rootComponent
        for prof in profiles:
            sketch = root.sketches.add(root.xZConstructionPlane)
            P = lambda q: sketch.modelToSketchSpace(adsk.core.Point3D.create(q[0] / 10, 0, q[1] / 10))
            sketch.isComputeDeferred = True
            first = prev = None
            try:
                for k, seg in enumerate(prof):
                    start = prev if prev is not None else P(seg[1])
                    end_pt = first if (k == len(prof) - 1 and first is not None) else P(seg[-1])
                    if seg[0] == "line":
                        c = sketch.sketchCurves.sketchLines.addByTwoPoints(start, end_pt)
                    else:
                        c = sketch.sketchCurves.sketchArcs.addByThreePoints(start, P(seg[2]), end_pt)
                    sp, ep = c.startSketchPoint, c.endSketchPoint
                    if first is None:
                        first = sp if sp.geometry.distanceTo(P(seg[1])) < 1e-7 else ep
                    prev = ep if ep.geometry.distanceTo(P(seg[-1])) < 1e-7 else sp
            finally:
                sketch.isComputeDeferred = False
            if sketch.profiles.count != 1:
                raise RuntimeError("Profile did not close into one region (%d)" % sketch.profiles.count)
            ext = root.features.extrudeFeatures.addSimple(sketch.profiles.item(0), adsk.core.ValueInput.createByReal((y1 - y0) / 10),
                                                         adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
            body = tbm.copy(ext.bodies.item(0))
            bb = body.boundingBox
            mtx = adsk.core.Matrix3D.create()
            mtx.translation = adsk.core.Vector3D.create(0, y0 / 10 - bb.minPoint.y, 0)
            if not tbm.transform(body, mtx):
                raise RuntimeError("Prism placement failed")
            out.append(body)
    finally:
        if not document.close(False):
            raise RuntimeError("Could not close the profile document")
        source.activate()
    return out


def stack_tool(cx, cz, rows):
    """Union of coaxial Y cylinders: rows = [(y0, y1, r), ...]."""
    s, _ = geometry()
    tool = None
    for y0, y1, r in rows:
        c = s.cyl(cx, cz, y0, y1, r)
        if tool is None:
            tool = c
        else:
            s.op(tool, c, "join")
    return tool
