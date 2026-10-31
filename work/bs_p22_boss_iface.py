"""Which overhangs of revision 43's P22 gain support when 'Remove small overhangs' is off? Diff the support-interface
extrusion (where support touches P22) of two slices from bs_p22_boss_test.py, cluster it, and name the face above each
cluster in P22's own coordinates (print: X' = X, Y' = -Z, Z' = Y + 45.4; placed at x 175, y 160)."""
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from bs_p22_boss_diff import MESH, OUT, points  # noqa: E402

CELL = 0.6


def main(a="preset_as_is", b="remove_small_off"):
    pa, pb = points(OUT / a / "sliced.3mf"), points(OUT / b / "sliced.3mf")
    m = trimesh.load_mesh(str(MESH))
    lo3, hi3 = m.bounds
    cx, cy = (lo3[0] + hi3[0]) / 2, (lo3[1] + hi3[1]) / 2
    for tag, p in ((a, pa), (b, pb)):
        i = p[p[:, 3] > 0]
        print(f"{tag}: interface points {len(i)}")
    ia = {tuple(v) for v in np.floor(pa[pa[:, 3] > 0, :3] / CELL).astype(int)}
    ib_pts = pb[pb[:, 3] > 0, :3]
    keys = np.floor(ib_pts / CELL).astype(int)
    newmask = np.array([tuple(k) not in ia and not any((k[0] + dx, k[1] + dy, k[2]) in ia for dx in (-1, 0, 1)
                                                      for dy in (-1, 0, 1)) for k in keys])
    new = ib_pts[newmask]
    print(f"interface points in {b} but not near any in {a}: {len(new)}")
    if not len(new):
        return
    kk = np.floor(new / CELL).astype(int)
    lo = kk.min(axis=0)
    grid = np.zeros(kk.max(axis=0) - lo + 1, bool)
    grid[tuple((kk - lo).T)] = True
    lab, n = ndimage.label(grid, structure=np.ones((3, 3, 3)))
    which = lab[tuple((kk - lo).T)]
    rows = []
    for k in range(1, n + 1):
        q = new[which == k]
        # the face each interface point holds up: straight up from it
        loc, ray, tri = m.ray.intersects_location(q, np.tile([0, 0, 1.0], (len(q), 1)), multiple_hits=False)
        nz = m.face_normals[tri][:, 2] if len(tri) else np.array([])
        gap = loc[:, 2] - q[ray, 2] if len(tri) else np.array([])
        top = loc[np.argmin(gap)] if len(tri) else q.mean(axis=0)
        model = (top[0] - cx, top[2] - 45.4, -(top[1] - cy) - 63.42)   # X, Y, Z in P22's assembly frame
        area = len(np.unique(np.floor(q[:, :2] / 0.5).astype(int), axis=0)) * 0.25
        rows.append((area, q.min(axis=0), q.max(axis=0), model, np.median(nz) if len(nz) else np.nan,
                     np.median(gap) if len(gap) else np.nan))
    rows.sort(key=lambda r: -r[0])
    print(f"{n} new contact patches (plan area ~ mm2 | plate box | face above: model X, Y, Z | its n_z | gap):")
    for area, mn, mx, model, nz, gap in rows[:20]:
        print(f"  {area:6.1f}  x {mn[0]:6.1f}-{mx[0]:6.1f} y {mn[1]:6.1f}-{mx[1]:6.1f} z {mn[2]:5.1f}-{mx[2]:5.1f}"
              f"  | X {model[0]:6.1f} Y {model[1]:6.1f} Z {model[2]:6.1f} | n_z {nz:5.2f} | gap {gap:4.2f}")


if __name__ == "__main__":
    main(*sys.argv[1:])
