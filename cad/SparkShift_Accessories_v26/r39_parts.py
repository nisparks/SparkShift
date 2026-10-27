"""Revision 39 geometry: the dock-coupling dowel pins move from the tool (P18) into the dock (P25).

Revision 38 found that the two Ø5x12 mm dowel pins sticking 5.5 mm out of every tool's P18 set the front
print limit: the active tool's pins reach into a parked tool's open rear, around its filament stem. With the
pins pressed into the dock and the bushings pressed into P18, nothing on the tool sticks out past its magnet
bar, and P18's flat plate becomes the limit everywhere.

Same hardware per tool/dock pair (2 dowel pins, 2 bushings, 2 + 2 magnets), same straight-Y docking, and the
same 4.59 mm pin insertion and 0.04 mm radial clearance, mirrored. A 7 mm bushing is wider than the Ø5 pin, so
the two pin bosses become one bar across P18's existing width (X+/-9.8, like the magnet bar). To keep at
least 1.48 mm of wall around the bushings, the axes move from X+/-6, Z22 to X+/-4.8, Z21. The bar's top stays
at Z26.2, so the clearances to the dock's entry lip (0.2 mm) and upper snap jaw (1.27 mm) are unchanged. The
magnets do not move.

Imported by build_dock_pins_r39.py and render_dock_pins_r39.py, so every consumer uses the same parts.
"""

import cadquery as cq
from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain

import build_and_verify_accessories_v26 as acc
from audit_tool_owned_2510 import bounds, compound
from build_bambu_clean_r29 import single
from build_modular_toolhead import load
from build_refined_docking_review import DOCK_NAMES

OLD_AXES = ((-6.0, 22.0), (6.0, 22.0))      # released pin/bushing axes (X, Z); left (-X) first, as in the dock
AXES = ((-4.8, 21.0), (4.8, 21.0))          # revision-39 axes
BOSS_FACE_Y = 45.0                           # P18 pin-boss face; unchanged
BAR = {"x": 9.8, "y": (37.0, BOSS_FACE_Y), "z": (16.0, 26.2), "r": 1.5}
SEAT_R, SEAT_DEPTH = 3.52, 5.5               # the dock's released bushing seat, now cut into P18
BUSHING = {"r_out": 3.5, "r_in": 2.52, "length": 5.45}                      # 5 x 7 x 5.5 mm, as modelled before
PIN = {"r": 2.48, "length": 12.0, "nose": 5.5, "cone": 2.0, "tip_r": 1.0}   # Ø5 x 12 mm rounded dowel, as before
PIN_BORE_R = 2.49                            # P18's released press-fit bore, now cut into P25
OLD_COUNTERBORE = (3.52, 5.5)                # P25's released bushing seat (radius, depth from the face)
OLD_CLEARANCE = (2.58, 12.0)                 # P25's released pin-clearance bore
LEFT, RIGHT = 10, 11                          # dock solid indices of the released bushings, now the pins
NAMES = {
    "p18": "P18_Docking_Backplate_Bushing_Seats_R39_REVIEW",
    "p25": "P25_Dock_Pin_Seats_R39_REVIEW",
    "dock": "39_Dock_Complete_REVIEW",
    "tool_hardware": "P18_Bushings_And_Magnets_R39_REVIEW",
    "review": "39_Dock_Pins_And_P18_Bushings_REVIEW",
}
DOCK_NAMES_R39 = tuple("Left_5x12_Dowel_Pin" if i == LEFT else "Right_5x12_Dowel_Pin" if i == RIGHT else n
                       for i, n in enumerate(DOCK_NAMES))


def unify(shape):
    u = ShapeUpgrade_UnifySameDomain(shape.wrapped if hasattr(shape, "wrapped") else shape, True, True, True)
    u.Build()
    return cq.Shape.cast(u.Shape())


def dock_face_y(dock37):
    """P25's rear face at the coupling: where the released bushings sit flush."""
    y = bounds(dock37[LEFT])[2]
    if abs(y - 45.910082) > 1e-4 or abs(bounds(dock37[RIGHT])[2] - y) > 1e-6:
        raise ValueError("Unexpected released dock bushings")
    return y


def bar():
    x, (y0, y1), (z0, z1), r = BAR["x"], BAR["y"], BAR["z"], BAR["r"]
    return cq.Shape.cast(acc.prism_xz_r([(-x, z0), (x, z0), (x, z1), (-x, z1)], [r] * 4, y0, y1))


def p18():
    """Released P18 with its two pin bosses grown into one bar, the pin bores filled, two bushing seats cut."""
    old = single(load("P18_Tool_docking_backplate_3010"), "released P18")
    seats = [acc.cyl_y(x, z, BOSS_FACE_Y - SEAT_DEPTH, BOSS_FACE_Y + 0.5, SEAT_R) for x, z in AXES]
    return single(unify(acc.cut_all(acc.fuse_all([old.wrapped, bar().wrapped]), seats)), "revision-39 P18")


def p25(old, yf):
    """Released P25 with its bushing seats and pin-clearance bores filled and two press-fit pin bores cut."""
    fill = [acc.cyl_y(x, z, yf, yf + OLD_COUNTERBORE[1], OLD_COUNTERBORE[0]) for x, z in OLD_AXES]
    fill += [acc.cyl_y(x, z, yf, yf + OLD_CLEARANCE[1], OLD_CLEARANCE[0]) for x, z in OLD_AXES]
    bores = [acc.cyl_y(x, z, yf - 0.5, yf + PIN["length"] - PIN["nose"], PIN_BORE_R) for x, z in AXES]
    return single(unify(acc.cut_all(acc.fuse_all([old.wrapped] + fill), bores)), "revision-39 P25")


def bushings():
    y1 = BOSS_FACE_Y
    y0 = y1 - BUSHING["length"]
    return [cq.Shape.cast(acc.cut_all(acc.cyl_y(x, z, y0, y1, BUSHING["r_out"]),
                                      [acc.cyl_y(x, z, y0 - 0.5, y1 + 0.5, BUSHING["r_in"])])) for x, z in AXES]


def pins(yf):
    """Pressed 6.5 mm into P25, rounded nose 5.5 mm proud of its face, pointing at the tool."""
    tip = yf - PIN["nose"]
    base, back = tip + PIN["cone"], tip + PIN["length"]
    return [cq.Shape.cast(acc.fuse_all([acc.cyl_y(x, z, base, back, PIN["r"]),
                                        acc.cone_y(x, z, tip, base, PIN["tip_r"], PIN["r"])])) for x, z in AXES]


def tool_magnets():
    """The released Ø6x4 mm tool magnets in P18's magnet bar (unchanged)."""
    mags = [acc.cyl_y(x, -2.0, 41.70, 45.70, 3.00) for x in (-6.0, 6.0)]
    return [cq.Shape.cast(m) for m in mags]


def dock(dock37, yf):
    out = list(dock37)
    out[0] = p25(dock37[0], yf)
    out[LEFT], out[RIGHT] = pins(yf)
    return out


def tools(tools37, p18_new):
    """Revision-37 tool sets with P18 and its coupling hardware replaced (the same P18 on both hotends)."""
    hardware = compound([*bushings(), *tool_magnets()])
    out = {}
    for label, v in tools37.items():
        drop = {"P18", "coupling pins and magnets", "P18 and magnets"}
        parts = [(n, s) for n, s in v["parts"] if n not in drop]
        if len(v["parts"]) - len(parts) != (2 if label == "Bambu" else 1):
            raise ValueError(f"Unexpected revision-37 {label} parts: {[n for n, _ in v['parts']]}")
        out[label] = dict(v, parts=parts + [("P18", p18_new), ("bushings and magnets", hardware)])
    return out
