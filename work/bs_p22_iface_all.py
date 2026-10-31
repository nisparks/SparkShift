"""Every place one slice from bs_p22_boss_test.py touches revision 43's P22 with support interface, clustered, with the
face above each patch in P22's own frame, and whether the trunk under it stands on the plate."""
import sys
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).parent))
from bs_p22_boss_diff import MESH, OUT, points  # noqa: E402


def main(name="preset_as_is"):
    p = points(OUT / name / "sliced.3mf")
    m = trimesh.load_mesh(str(MESH))
    lo3, hi3 = m.bounds
    cx, cy = (lo3[0] + hi3[0]) / 2, (lo3[1] + hi3[1]) / 2
    q_all = p[p[:, 3] > 0, :3]
    kk = np.floor(q_all / 0.6).astype(int)
    lo = kk.min(axis=0)
    grid = np.zeros(kk.max(axis=0) - lo + 1, bool)
    grid[tuple((kk - lo).T)] = True
    lab, n = ndimage.label(grid, structure=np.ones((3, 3, 3)))
    which = lab[tuple((kk - lo).T)]
    rows = []
    for k in range(1, n + 1):
        q = q_all[which == k]
        loc, ray, tri = m.ray.intersects_location(q, np.tile([0, 0, 1.0], (len(q), 1)), multiple_hits=False)
        gap = loc[:, 2] - q[ray, 2] if len(tri) else np.array([])
        top = loc[np.argmin(gap)] if len(tri) else q.mean(axis=0)
        model = (top[0] - cx, top[2] - 45.4, -(top[1] - cy) - 63.42)
        # does the support under this patch stand on P22? cast down from the patch centre
        down = m.ray.intersects_any([q.mean(axis=0) - [0, 0, 0.3]], [[0, 0, -1.0]])[0]
        area = len(np.unique(np.floor(q[:, :2] / 0.5).astype(int), axis=0)) * 0.25
        rows.append((area, q.min(axis=0), q.max(axis=0), model, np.median(m.face_normals[tri][:, 2]) if len(tri) else np.nan,
                     down))
    rows.sort(key=lambda r: -r[0])
    print(f"{name}: {n} interface patches (plan area ~mm2 | plate box | face above in P22's frame | its n_z | P22 below)")
    for area, mn, mx, model, nz, down in rows:
        if area < 0.5:
            continue
        print(f"  {area:6.1f}  x {mn[0]:6.1f}-{mx[0]:6.1f} y {mn[1]:6.1f}-{mx[1]:6.1f} z {mn[2]:5.1f}-{mx[2]:5.1f}"
              f"  | X {model[0]:6.1f} Y {model[1]:6.1f} Z {model[2]:6.1f} | n_z {nz:5.2f} | {'P22' if down else 'plate'}")


if __name__ == "__main__":
    for a in sys.argv[1:] or ["preset_as_is", "plate_only_off"]:
        main(a)
