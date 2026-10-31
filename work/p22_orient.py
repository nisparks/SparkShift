"""P22 print-orientation study (session scratch): overhang area for every orientation, and where it is."""
import sys, os, json, math
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
from pathlib import Path
import numpy as np
import cadquery as cq
import trimesh

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\fdm")
OUT.mkdir(parents=True, exist_ok=True)
s = cq.Shape.importBrep(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\variants\p22_r43_lowbell_taper.brep")
stl = OUT / "p22.stl"
cq.exporters.export(s, str(stl), tolerance=0.02, angularTolerance=0.1)
m = trimesh.load_mesh(str(stl))
print("mesh", len(m.faces), "faces, area", round(m.area, 1), "volume", round(m.volume, 1), "bounds", np.round(m.bounds, 2).tolist())
N, A, C = m.face_normals, m.area_faces, m.triangles_center


def stats(up, thr_deg=(30.0, 45.0)):
    up = np.asarray(up, float) / np.linalg.norm(up)
    h = C @ up
    vz = m.vertices @ up
    z0 = vz.min()
    bed = (N @ up < -0.999) & (h - z0 < 0.02)
    out = {"bed_mm2": round(float(A[bed].sum()), 1), "height_mm": round(float(vz.max() - z0), 1)}
    for t in thr_deg:
        down = (N @ up < -math.sin(math.radians(90 - t))) & ~bed
        out[f"over{int(t)}_mm2"] = round(float(A[down].sum()), 1)
    return out, bed


def classify(up, thr=30.0):
    """Overhang facets that a support from the plate could reach (a ray straight down misses the part) and those over
    the part itself (inside the duct or the slot, or over another face)."""
    up = np.asarray(up, float) / np.linalg.norm(up)
    _, bed = stats(up)
    down = (N @ up < -math.sin(math.radians(90 - thr))) & ~bed
    idx = np.nonzero(down)[0]
    origins = C[idx] - up * 0.02
    hit = m.ray.intersects_any(origins, np.tile(-up, (len(idx), 1)))
    return idx, hit


# the current orientation: back face down (asm +Y up)
cur = (0.0, 1.0, 0.0)
st, _ = stats(cur)
idx, hit = classify(cur)
print("current (back face down):", st, "| over the part:", round(float(A[idx[hit]].sum()), 1), "mm2, reachable from the plate:",
      round(float(A[idx[~hit]].sum()), 1), "mm2")

# where it is: cluster the overhang facets
def clusters(idx, label):
    if not len(idx):
        return []
    sub = m.submesh([idx], append=True)
    parts = sub.split(only_watertight=False)
    rows = []
    for p in parts:
        b = p.bounds
        rows.append({"area_mm2": round(float(p.area), 1), "centre": np.round(p.centroid, 1).tolist(),
                     "x": np.round(b[:, 0], 1).tolist(), "y": np.round(b[:, 1], 1).tolist(), "z": np.round(b[:, 2], 1).tolist()})
    rows.sort(key=lambda r: -r["area_mm2"])
    print(f"  {label}: {len(rows)} patches")
    for r in rows[:14]:
        print("   ", r)
    return rows

clusters(idx[hit], "over the part")
clusters(idx[~hit], "reachable from the plate")

# sweep: Fibonacci sphere of 'up' directions
n = 1200
k = np.arange(n) + 0.5
phi = np.arccos(1 - 2 * k / n)
th = math.pi * (1 + 5 ** 0.5) * k
dirs = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
rows = []
for d in dirs:
    st, _ = stats(d)
    rows.append((st["over30_mm2"], st["over45_mm2"], st["bed_mm2"], st["height_mm"], d))
rows.sort(key=lambda r: r[0])
print("\nbest by 30-degree overhang (asm 'up' vector):")
for r in rows[:12]:
    print("  over30 %7.1f  over45 %7.1f  bed %6.1f  h %5.1f  up %s" % (r[0], r[1], r[2], r[3], np.round(r[4], 3).tolist()))
rows45 = sorted(rows, key=lambda r: r[1])
print("best by 45-degree overhang:")
for r in rows45[:8]:
    print("  over30 %7.1f  over45 %7.1f  bed %6.1f  h %5.1f  up %s" % (r[0], r[1], r[2], r[3], np.round(r[4], 3).tolist()))
for name, up in (("+X up (side)", (1, 0, 0)), ("-X up", (-1, 0, 0)), ("+Y up (back down)", (0, 1, 0)), ("-Y up (front down)", (0, -1, 0)),
                 ("+Z up (as installed)", (0, 0, 1)), ("-Z up (upside down)", (0, 0, -1))):
    st, _ = stats(up)
    i2, h2 = classify(up)
    print(f"{name:22s} {st} over the part {A[i2[h2]].sum():7.1f} reachable {A[i2[~h2]].sum():7.1f}")
json.dump({"current": stats(cur)[0]}, open(OUT / "orient.json", "w"))
