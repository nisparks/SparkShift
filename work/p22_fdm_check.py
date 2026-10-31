import sys, os, json, math
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
os.chdir(sys.path[0])
from pathlib import Path
import numpy as np
import cadquery as cq
import trimesh
import r41_parts as R41
import r43_parts as R
import print_audit_brep as AU

FILES = Path(__file__).resolve().parent
OUT = FILES / "r43" / "fdm"
SC = FILES / "r43_scene"
prev = cq.Shape.importBrep(str(FILES / "r43" / "variants" / "p22_r43_lowbell_taper.brep"))
new = R.p22()
new.exportBrep(str(FILES / "r43" / "variants" / "p22_r43_printable.brep"))
print("valid", new.isValid(), "solids", len(new.Solids()), "volume", round(new.Volume(), 2), "prev", round(prev.Volume(), 2),
      "added", round(new.cut(prev).Volume(), 2), "removed", round(prev.cut(new).Volume(), 2), "faces", len(new.Faces()), flush=True)

def mesh_of(s, name):
    p = OUT / f"{name}.stl"
    cq.exporters.export(s, str(p), tolerance=0.02, angularTolerance=0.1)
    return trimesh.load_mesh(str(p))

def overhangs(m, label):
    up = np.array([0.0, 1.0, 0.0])
    N, A, C = m.face_normals, m.area_faces, m.triangles_center
    h = C @ up
    bed = (N @ up < -0.999) & (h - h.min() < 0.02)
    d30 = (N @ up < -math.sin(math.radians(60))) & ~bed
    d45 = (N @ up < -math.sin(math.radians(45))) & ~bed
    idx = np.nonzero(d30)[0]
    hit = m.ray.intersects_any(C[idx] - up * 0.02, np.tile(-up, (len(idx), 1)))
    print(f"{label}: bed {A[bed].sum():.1f} mm2, overhang <30deg {A[d30].sum():.1f} (over the part {A[idx[hit]].sum():.1f}, "
          f"reachable {A[idx[~hit]].sum():.1f}), <45deg {A[d45].sum():.1f}", flush=True)
    sub = m.submesh([idx], append=True)
    rows = []
    for p in sub.split(only_watertight=False):
        b = p.bounds
        rows.append((round(float(p.area), 1), np.round(p.centroid, 1).tolist(), np.round(b[:, 0], 1).tolist(),
                     np.round(b[:, 1], 1).tolist(), np.round(b[:, 2], 1).tolist()))
    rows.sort(key=lambda r: -r[0])
    for r in rows[:12]:
        print("    %6.1f mm2 at %s  x %s y %s z %s" % r)

overhangs(mesh_of(prev, "prev"), "before (lower floor + bell-mouth)")
overhangs(mesh_of(new, "printable"), "after (printable)")

# fit against every part in the scene
m = json.loads((SC / "manifest.json").read_text())
parts = {n: cq.Shape.importBrep(str(SC / f)) for n, f in m["carriage"] if not n.startswith("P22_")}
parts["cartographer"] = cq.Shape.importBrep(str(SC / m["cartographer"]))
for label, v in m["variants"].items():
    for n, f in v["parts"]:
        parts[f"{label}:{n}"] = cq.Shape.importBrep(str(SC / f))
changed = new.cut(prev).fuse(prev.cut(new))
cb = changed.BoundingBox()
print("changed region bounds", [round(v, 2) for v in (cb.xmin, cb.xmax, cb.ymin, cb.ymax, cb.zmin, cb.zmax)])
rows = []
for n, s in parts.items():
    bb = s.BoundingBox()
    if bb.xmax < cb.xmin - 2 or bb.xmin > cb.xmax + 2 or bb.ymax < cb.ymin - 2 or bb.ymin > cb.ymax + 2 or bb.zmax < cb.zmin - 2 or bb.zmin > cb.zmax + 2:
        continue
    dn, dp = new.distance(s), prev.distance(s)
    if min(dn, dp) < 2.0:
        ov_n = new.intersect(s).Volume() if dn < 1e-6 else 0.0
        ov_p = prev.intersect(s).Volume() if dp < 1e-6 else 0.0
        rows.append((round(dn, 3), round(dp, 3), round(ov_n, 4), round(ov_p, 4), n))
rows.sort()
print("parts within 2 mm (gap new, gap before, overlap new, overlap before):")
for r in rows:
    flag = "  <-- CHANGED" if abs(r[0] - r[1]) > 1e-3 or abs(r[2] - r[3]) > 1e-4 else ""
    print("   %7.3f %7.3f %9.4f %9.4f  %s%s" % (*r, flag))

# P23's bearing on P22's underside: area of P22's faces at Z-70.8 over P23's top
p23 = parts["P23_Probe_Mount_Raised_Rear_Ears_R37_REVIEW"]
slab = cq.Shape.cast(R.a.box(-23, 23, -30, 12, -70.81, -70.79))
for tag, s in (("before", prev), ("after", new)):
    a = s.intersect(slab).intersect(p23.BoundingBox() and cq.Shape.cast(R.a.box(-23, 23, -30, 12, -70.82, -70.78))).Volume() / 0.02
    print(f"P22 solid in the 0.02 mm slab at its underside (Y-30..12), {tag}: {a:.1f} mm2")

nf, of = AU.face_rows(new), AU.face_rows(R41.p22())
ns, nc, _ = AU.edge_rows(new)
os_, oc, _ = AU.edge_rows(R41.p22())
for k, rows2, olds in (("small_or_thin_faces", nf, of), ("short_edges", ns, os_), ("shallow_creases", nc, oc)):
    rows2 = AU.tag(rows2, olds)
    fresh = [x for x in rows2 if not x["inherited"]]
    print(k, len(rows2), "new:", len(fresh), json.dumps([{kk: x[kk] for kk in x if kk in ("area_mm2", "width_mm", "length_mm", "angle_deg", "centre", "mid")} for x in fresh]))
