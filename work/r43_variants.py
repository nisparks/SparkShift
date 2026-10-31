"""R43 study: P22 outlet variants with longer jet windows (session scratch, not committed).

long : the heel drops vertically just in front of P23, so the channel floor stays at Z-76.65 back to Y13.05 and
       each jet runs full height from Y13.05 to the front wall (R41: full height only from Y19.6).
rear : as long, with the front 4 mm of each window closed, so the jets meet behind the nozzle.
"""
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

P23_FRONT = 11.55                     # both P23s' front face (Z-74.6..-70.8)
Y_HO = P23_FRONT + 0.30               # the new heel's outer face
WALL = 1.2
Y_HI = Y_HO + WALL                    # the heel's inner face: the jets start here
FLOOR, UNDER = -76.65, -77.85
WALL_X = R.WALL_X                     # (10.2, 11.6)
ROOF = R.ROOF
TRIM_H = 2.0                          # the duct-to-slot wall is made a plain 1.4 mm slab this far above ROOF

HORN_IN_NEW = R.HORN_IN[:11] + [(Y_HI, FLOOR), (Y_HI, -68.90)]
HORN_IN_NEW_R = R.HORN_IN_R[:11] + [0.5, 0.5]
HORN_OUT_NEW = R.HORN_OUT[:11] + [(Y_HO, UNDER), (Y_HO, -70.80)]
HORN_OUT_NEW_R = R.HORN_OUT_R[:11] + [0.5, 0.0]


def horn_in_new(x0, x1):
    return a.prism_yz_r(HORN_IN_NEW, HORN_IN_NEW_R, x0, x1)


def xy_outer(z0, z1, offset=WALL):
    from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
    from OCP.gp import gp_Vec
    w = cq.Wire(a.rounded_polygon_wire_2d(R.XY_INNER, R.XY_INNER_R)).offset2D(offset, "arc")[0]
    face = cq.Face.makeFromWires(w).translate(cq.Vector(0, 0, z0))
    return R.shape(BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(0, 0, z1 - z0)).Shape())


def heel_fill():
    """P22's new heel: everything under the R41 heel, out to the side wall, in front of Y_HO; on the slot side only
    below ROOF (the slot's rounded back corner above it is left as it is)."""
    region = R.common(a.box(-23.0, 23.0, Y_HO, 22.6, UNDER, -70.0),
                      [a.prism_yz_r(HORN_OUT_NEW, HORN_OUT_NEW_R, -23.0, 23.0), xy_outer(UNDER - 1.0, -69.0)])
    return R.cut(region, [a.box(-WALL_X[0], WALL_X[0], 0.0, 40.0, -90.0, -50.0),
                          a.box(-WALL_X[1], WALL_X[1], 0.0, 40.0, ROOF, -50.0)])


def corner_fill(side):
    """The slot's rounded back corner, squared off for TRIM_H above ROOF, so the wall over the jet is a plain slab."""
    lo, hi = sorted((side * WALL_X[0], side * WALL_X[1]))
    return a.box(lo, hi, Y_HI, 17.6, ROOF, ROOF + TRIM_H)


def new_air():
    return R.common(a.box(-22.0, 22.0, Y_HI - 0.01, 23.0, FLOOR - 0.01, -66.0),
                    [horn_in_new(-22.0, 22.0), R.p22_air_xy(-78.0, -60.0)])


def window_cut(side, y1=28.2):
    lo, hi = sorted((side * (WALL_X[0] - 0.05), side * 12.9))
    inside = a.prism_xy_r(R.XY_INNER, R.XY_INNER_R, FLOOR - 1.0, ROOF + 1.0)
    return R.common(a.box(lo, hi, Y_HI, y1, FLOOR - 0.01, ROOF), [horn_in_new(lo - 1.0, hi + 1.0), inside])


def wall_trim(side):
    """The thicker wall behind Y17.6 (out to |X| 12.85) cut back to the slab's duct face for TRIM_H above ROOF."""
    lo, hi = sorted((side * WALL_X[1], side * 13.0))
    inside = a.prism_xy_r(R.XY_INNER, R.XY_INNER_R, ROOF - 1.0, ROOF + TRIM_H + 1.0)
    return R.common(a.box(lo, hi, Y_HI, 17.6, ROOF - 0.01, ROOF + TRIM_H), [horn_in_new(lo - 1.0, hi + 1.0), inside])


def bell_mouth(side, y0=Y_HI, y1=R.JET_LIP_Y[1]):
    x = side * WALL_X[1]
    r = R.JET_LIP_R
    lo, hi = sorted((x - side * r, side * R.JET_LIP_X_OUT))
    corner = R.shape(a.box(lo, hi, y0, y1, ROOF - 0.01, ROOF + r))
    corner = corner.cut(R.shape(a.cyl_y(x - side * r, ROOF + r, y0 - 0.1, y1 + 0.1, r)))
    return R.common(corner, [horn_in_new(lo - 1.0, hi + 1.0)])


def blocker(side, y0):
    """Close the window in front of y0: the wall down to the floor, as a plain 1.4 mm slab."""
    lo, hi = sorted((side * WALL_X[0], side * WALL_X[1]))
    inside = a.prism_xy_r(R.XY_INNER, R.XY_INNER_R, FLOOR - 1.0, ROOF + 3.0)
    return R.common(a.box(lo, hi, y0, 28.3, FLOOR - 0.01, ROOF + R.JET_LIP_R + 0.01), [inside])


def variant(kind, base):
    t = time.perf_counter()
    body = R.fuse(base, heel_fill(), *[corner_fill(s) for s in (-1, 1)])
    cutters = [new_air()] + [c for s in (-1, 1) for c in (window_cut(s), wall_trim(s), bell_mouth(s))]
    body = R.cut(body, cutters)
    if kind == "rear":
        body = R.fuse(body, *[blocker(s, 24.2) for s in (-1, 1)])
    body = R.unify(body)
    print(f"{kind}: valid {body.isValid()}, solids {len(body.Solids())}, volume {body.Volume():.1f} mm3, "
          f"{time.perf_counter() - t:.0f} s", flush=True)
    return body


if __name__ == "__main__":
    import json
    m = json.loads((SCENE / "manifest.json").read_text())
    base = cq.Shape.importBrep(str(SCENE / dict(m["carriage"])[R.NAMES["p22"]]))
    print("R41 volume", round(base.Volume(), 1))
    for kind in sys.argv[1:] or ("long", "rear"):
        v = variant(kind, base)
        v.exportBrep(str(OUT / f"p22_{kind}.brep"))
