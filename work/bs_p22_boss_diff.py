"""Where does turning off 'Remove small overhangs' add support on revision 43's P22 (besides the bosses)? Compare the
support extrusion of two slices from bs_p22_boss_test.py voxel by voxel, cluster what's new, and say whether each
cluster is enclosed by P22 (inside the duct or a pocket) or open to the outside."""
import re
import sys
import zipfile
from pathlib import Path

import numpy as np
import trimesh
from scipy import ndimage

HERE = Path(__file__).parent
OUT = HERE / "bs_r43_boss"
MESH = HERE / "bs_r43" / "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW_PRINT_ORIENTED.stl"
CELL = 1.0


def points(path):
    z = zipfile.ZipFile(path)
    g = z.read(next(n for n in z.namelist() if n.endswith(".gcode"))).decode(errors="replace")
    feat, zz, x, y, pts = None, 0.0, 0.0, 0.0, []
    for line in g.splitlines():
        if line.startswith("; FEATURE:"):
            feat = line[10:].strip()
        elif line.startswith("; Z_HEIGHT:"):
            zz = float(line.split(":")[1])
        elif line[:3] in ("G0 ", "G1 ", "G2 ", "G3 "):
            mx, my = re.search(r"X([-\d.]+)", line), re.search(r"Y([-\d.]+)", line)
            nx = float(mx.group(1)) if mx else x
            ny = float(my.group(1)) if my else y
            if feat and "upport" in feat and re.search(r"E[\d.]", line):
                n = max(1, int(np.hypot(nx - x, ny - y) / 0.5))
                for t in np.linspace(0, 1, n + 1):
                    pts.append((x + (nx - x) * t, y + (ny - y) * t, zz, "nterface" in feat))
            x, y = nx, ny
    return np.array(pts)


def vox(p):
    return {tuple(v) for v in np.floor(p[:, :3] / CELL).astype(int)}


def main(a="preset_as_is", b=None):
    b = b or "remove_small_off"
    pa, pb = points(OUT / a / "sliced.3mf"), points(OUT / b / "sliced.3mf")
    va, vb = vox(pa), vox(pb)
    new = np.array(sorted(vb - va))
    print(f"{a}: {len(va)} support voxels; {b}: {len(vb)}; new in {b}: {len(new)}")
    if not len(new):
        return
    lo = new.min(axis=0)
    grid = np.zeros(new.max(axis=0) - lo + 1, bool)
    grid[tuple((new - lo).T)] = True
    lab, n = ndimage.label(grid, structure=np.ones((3, 3, 3)))
    m = trimesh.load_mesh(str(MESH))
    print("P22 bounds", np.round(m.bounds, 2).tolist())
    dirs = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1]], float)
    iface = {tuple(v) for v in np.floor(pb[pb[:, 3] > 0, :3] / CELL).astype(int)}
    rows = []
    for k in range(1, n + 1):
        cells = np.argwhere(lab == k) + lo
        c = (cells + 0.5) * CELL
        bb = np.r_[c.min(axis=0) - 0.5, c.max(axis=0) + 0.5]
        # enclosure: share of (cell, direction) rays that hit P22
        o = np.repeat(c, len(dirs), axis=0)
        d = np.tile(dirs, (len(c), 1))
        hit = m.ray.intersects_any(o, d)
        top = c[c[:, 2] == c[:, 2].max()].mean(axis=0)
        n_if = sum(tuple(v) in iface for v in cells)
        rows.append((len(cells), bb, hit.mean(), top, n_if))
    rows.sort(key=lambda r: -r[0])
    for size, bb, enc, top, n_if in rows[:25]:
        print(f"  {size:5d} cells  x {bb[0]:6.1f}-{bb[3]:6.1f}  y {bb[1]:6.1f}-{bb[4]:6.1f}  z {bb[2]:5.1f}-{bb[5]:5.1f}"
              f"  top at ({top[0]:.1f}, {top[1]:.1f}, {top[2]:.1f})  rays hitting P22 {enc:4.0%}  interface cells {n_if}")
    print(f"  ({n} clusters)")


if __name__ == "__main__":
    main(*sys.argv[1:])
