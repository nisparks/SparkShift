"""R43 study, round 2: variants of revision 41's P22 that keep its jets where they are, beside the nozzle
(session scratch, not committed).

low   : the floor under each jet lowered 0.4 mm (Z-76.65 -> -77.05, 0.8 mm left under it), from the slot face out to
        |X| 13.0 with a 45 degree ramp back up to the channel floor by |X| 13.4, over the jets' flat-floored length
        (Y19.0-28.2): the jets are 13 % taller and their bottom edge 0.4 mm nearer the print.
bell  : the bell-mouth round over each jet r 2.4 instead of 1.4: the wall's duct face carries a foot out to |X| 12.6
        for its bottom 2.4 mm (a 45 degree chamfer back to the 1.4 mm wall above), rounded r 2.4 from the slot-side edge.
combo : both.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
FILES = Path(__file__).parent
OUT = FILES / "r43" / "variants"
OUT.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))
import os  # noqa: E402
os.chdir(HERE)

import cadquery as cq  # noqa: E402

import r41_parts as R  # noqa: E402

a = R.a
SCENE = FILES / "r41_scene"
ROOF, WALL_X, FLOOR = R.ROOF, R.WALL_X, -76.65
LOW_FLOOR, LOW_X, LOW_RAMP, LOW_Y = -77.05, 13.0, 0.4, (19.0, 28.2)
BELL_R, BELL_Y = 2.4, (17.6, R.JET_LIP_Y[1])


def inside(z0, z1):
    return a.prism_xy_r(R.XY_INNER, R.XY_INNER_R, z0, z1)


def low_cut(side):
    """Floor pocket under the jet: flat at LOW_FLOOR out to LOW_X, then a 45 degree ramp up to FLOOR."""
    pts = [(WALL_X[0] - 0.05, LOW_FLOOR), (LOW_X, LOW_FLOOR), (LOW_X + LOW_RAMP, FLOOR + 0.01), (WALL_X[0] - 0.05, FLOOR + 0.01)]
    if side < 0:
        pts = [(-x, z) for x, z in pts][::-1]
    prof = R.shape(a.prism_xz_r(pts, [0, 0, 0, 0], LOW_Y[0], LOW_Y[1]))
    return R.common(prof, [inside(LOW_FLOOR - 1.0, FLOOR + 1.0)])


def bell_fill(side):
    """The whole corner under the wall, from its slot face out to |X| WALL_X[0] + BELL_R, for BELL_R over ROOF
    (chamfered back to the 1.4 mm wall above); bell_cut then rounds it."""
    x0, x1 = WALL_X[0], WALL_X[0] + BELL_R
    pts = [(x0, ROOF), (x1, ROOF), (x1, ROOF + BELL_R), (WALL_X[1], ROOF + BELL_R + (x1 - WALL_X[1])), (x0, ROOF + BELL_R + (x1 - WALL_X[1]))]
    if side < 0:
        pts = [(-x, z) for x, z in pts][::-1]
    prof = R.shape(a.prism_xz_r(pts, [0] * len(pts), *BELL_Y))
    return R.common(prof, [R.horn_in(-23.0, 23.0)])


def bell_cut(side):
    """As revision 41's round, on a larger radius: centred on the slot face, BELL_R over ROOF."""
    x = side * WALL_X[0]
    lo, hi = sorted((x, side * (WALL_X[0] + BELL_R + 0.3)))
    corner = R.shape(a.box(lo, hi, BELL_Y[0], BELL_Y[1], ROOF - 0.01, ROOF + BELL_R))
    corner = corner.cut(R.shape(a.cyl_y(x, ROOF + BELL_R, BELL_Y[0] - 0.1, BELL_Y[1] + 0.1, BELL_R)))
    return R.common(corner, [R.horn_in(lo - 1.0, hi + 1.0)])


def variant(kind, base):
    t = time.perf_counter()
    body = base
    if kind in ("bell", "combo"):
        body = R.fuse(body, *[bell_fill(s) for s in (-1, 1)])
        body = R.cut(body, [bell_cut(s) for s in (-1, 1)])
    if kind in ("low", "combo"):
        body = R.cut(body, [low_cut(s) for s in (-1, 1)])
    body = R.unify(body)
    print(f"{kind}: valid {body.isValid()}, solids {len(body.Solids())}, volume {body.Volume():.1f} mm3, "
          f"{time.perf_counter() - t:.0f} s", flush=True)
    return body


if __name__ == "__main__":
    m = json.loads((SCENE / "manifest.json").read_text())
    base = cq.Shape.importBrep(str(SCENE / dict(m["carriage"])[R.NAMES["p22"]]))
    print("R41 volume", round(base.Volume(), 1))
    for kind in sys.argv[1:] or ("low", "bell", "combo"):
        variant(kind, base).exportBrep(str(OUT / f"p22_{kind}.brep"))
