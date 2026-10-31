"""How does Bambu Studio print the skin over P22's window (revision 43)? The skin is the 1.8 mm of P22's underside left
under the window notch for P23 to bear on: in print, a flat ceiling at height 40.0 mm spanning the window's 22.9 mm,
1.8 mm deep (plate x 163.55-186.45, y 165.58-167.38). Read the CLI slice of the print-oriented STL with the user's
preset (bs_p22_boss_test.py) around that height: features, speeds and fan, and plot the toolpaths per layer over the
mesh's cross-section."""
import re
import sys
import zipfile
from pathlib import Path

import matplotlib
import numpy as np
import trimesh

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

HERE = Path(__file__).parent
SLICE = HERE / "bs_r43_boss" / (sys.argv[1] if len(sys.argv) > 1 else "preset_as_is") / "sliced.3mf"
MESH = HERE / "bs_r43" / "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW_PRINT_ORIENTED.stl"
OUT = HERE / "r43" / "fdm" / "p22_window_bridge_gcode.png"
SKIN = dict(x=(163.55, 186.45), y=(165.58, 167.38), z=40.0)
LAYERS = (39.8, 40.0, 40.2, 40.4, 40.6, 41.0)
BOX = (158.0, 192.0, 150.0, 172.0)


def moves(path):
    z = zipfile.ZipFile(path)
    g = z.read(next(n for n in z.namelist() if n.endswith(".gcode"))).decode(errors="replace")
    feat, zz, x, y, f, fan = None, 0.0, 0.0, 0.0, 0.0, 0
    out = []
    for line in g.splitlines():
        if line.startswith("; FEATURE:"):
            feat = line[10:].strip()
        elif line.startswith("; Z_HEIGHT:"):
            zz = round(float(line.split(":")[1]), 2)
        elif line.startswith("M106") and " P" not in line or line.startswith("M106 P0") or line.startswith("M106 P1 "):
            s = re.search(r"S([\d.]+)", line)
            fan = float(s.group(1)) if s else fan
        elif line.startswith("M107"):
            fan = 0
        elif line[:3] in ("G0 ", "G1 ", "G2 ", "G3 "):
            mx, my, mf = re.search(r"X([-\d.]+)", line), re.search(r"Y([-\d.]+)", line), re.search(r"F([\d.]+)", line)
            f = float(mf.group(1)) if mf else f
            nx = float(mx.group(1)) if mx else x
            ny = float(my.group(1)) if my else y
            me = re.search(r"E([-\d.]+)", line)
            if me and float(me.group(1)) > 0 and (nx, ny) != (x, y):
                out.append((zz, feat, x, y, nx, ny, f / 60.0, fan, float(me.group(1))))
            x, y = nx, ny
    return out


def main():
    mv = moves(SLICE)
    m = trimesh.load_mesh(str(MESH))
    lo, hi = m.bounds
    shift = np.array([175.0 - (lo[0] + hi[0]) / 2, 160.0 - (lo[1] + hi[1]) / 2, -lo[2]])
    m.apply_translation(shift)
    sx, sy = SKIN["x"], SKIN["y"]
    print(f"{SLICE.parent.name}: {len(mv)} extrusion moves")
    for L in LAYERS:
        rows = [r for r in mv if r[0] == L and BOX[0] < (r[2] + r[4]) / 2 < BOX[1] and BOX[2] < (r[3] + r[5]) / 2 < BOX[3]]
        over = [r for r in rows if sx[0] + 0.3 < (r[2] + r[4]) / 2 < sx[1] - 0.3 and sy[0] - 0.4 < (r[3] + r[5]) / 2 < sy[1] + 0.4]
        summary = {}
        for r in over:
            s = summary.setdefault(r[1], [0, 0.0, set(), set()])
            s[0] += 1
            s[1] += float(np.hypot(r[4] - r[2], r[5] - r[3]))
            s[2].add(round(r[6]))
            s[3].add(round(r[7]))
        print(f"  layer {L:5.2f}: over the window's span:",
              {k: f"{v[0]} moves, {v[1]:.0f} mm, speed {sorted(v[2])} mm/s, fan {sorted(v[3])}" for k, v in summary.items()}
              or "nothing")
    feats = sorted({r[1] for r in mv if r[0] in LAYERS})
    cmap = plt.get_cmap("tab10")
    colour = {k: cmap(i % 10) for i, k in enumerate(feats)}
    fig, axes = plt.subplots(2, 3, figsize=(18, 10.5))
    for ax, L in zip(axes.flat, LAYERS):
        sec = m.section(plane_origin=[0, 0, L - 0.1], plane_normal=[0, 0, 1])
        if sec is not None:
            for d in sec.discrete:
                ax.fill(d[:, 0], d[:, 1], color="0.9", zorder=0)
                ax.plot(d[:, 0], d[:, 1], color="0.55", lw=0.8, zorder=1)
        seen = set()
        for r in mv:
            if r[0] != L:
                continue
            cx, cy = (r[2] + r[4]) / 2, (r[3] + r[5]) / 2
            if not (BOX[0] < cx < BOX[1] and BOX[2] < cy < BOX[3]):
                continue
            ax.plot([r[2], r[4]], [r[3], r[5]], color=colour[r[1]], lw=1.6, solid_capstyle="butt", zorder=2,
                    label=r[1] if r[1] not in seen else None)
            seen.add(r[1])
        ax.add_patch(plt.Rectangle((sx[0], sy[0]), sx[1] - sx[0], sy[1] - sy[0], fill=False, ec="red", lw=1.0, ls="--",
                                   zorder=3))
        ax.set_xlim(BOX[0], BOX[1])
        ax.set_ylim(BOX[2], BOX[3])
        ax.set_aspect("equal")
        ax.set_title(f"layer printed at {L:.2f} mm (section at {L - 0.1:.2f})")
        ax.legend(fontsize=8, loc="lower left")
    fig.suptitle("P22 (revision 43) as Bambu Studio slices it near the window's ceiling. Grey: P22's cross-section; "
                 "red dashes: the skin over the window (P23's bearing face)", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.96))
    fig.savefig(OUT, dpi=80)
    print(OUT)


if __name__ == "__main__":
    main()
