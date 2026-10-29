"""Revision 42 review image: the Cartographer's own P23, and its keepout.

87: the Beacon on revision 37's P23 and the Cartographer on revision 42's, each cut at X0 through the coil and the
    nozzle; the Cartographer's keepout column (its model's own) with the metal that reaches into it; a close-up of
    the Monolith core's nuts in the top of the column.

Run after build_cartographer_mount_r42.py: python render_cartographer_mount_r42.py
"""
import json
import os

from PIL import Image, ImageDraw

import build_and_verify_accessories_v26 as acc
import r37_parts as P37
import r41_parts as R41
import r42_parts as R
from build_cartographer_mount_r42 import REPORT
from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet
from render_carriage_fixes_r41 import SIZE, v26_parts

os.environ["SPARKSHIFT_SCENE"] = str(acc.WORK / "r42_scene")

import build_chute_chamfer_rack_r36 as r36  # noqa: E402

TEAL, LIME, BOARD, GREY = (0.0, 0.64, 0.61), (0.55, 0.85, 0.2), (0.12, 0.12, 0.14), (0.7, 0.7, 0.72)
STEEL, RED, PINK, DARK = (0.45, 0.45, 0.5), (0.9, 0.12, 0.12), (0.95, 0.6, 0.7), (0.3, 0.3, 0.33)
NUTS = ("MONOC_M3_NUT_left_41.8", "MONOC_M3_NUT_right_41.8", "MONOC_M3x16_DRAW_left_41.8", "MONOC_M3x16_DRAW_right_41.8")


def view(items, clip, eye, target, title, zoom=1.0, up=(0, 0, 1)):
    """As revision 41's panels, with a white box behind the caption so it reads over dark parts."""
    actors = []
    for shape, color, *rest in items:
        part = shape.intersect(clip) if clip is not None else shape
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, rest[0] if rest else 1.0, edge_vis=True))
    path = primitives.WORK / "cartographer_mount_r42_panel.png"
    render_view(actors, eye, target, up, path, width=SIZE[0], height=SIZE[1], zoom=zoom)
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image, "RGBA")
    lines = title.split("\n")
    draw.rectangle((6, 6, 18 + max(draw.textlength(line) for line in lines), 16 + 14 * len(lines)),
                   fill=(255, 255, 255, 220))
    for i, line in enumerate(lines):
        draw.text((12, 12 + 14 * i), line, fill=(10, 10, 10))
    path.unlink()
    return image


def image_87(report):
    h, k = report["probe_heights"], report["keepouts"]
    p22, p23, p23c = load(R41.NAMES["p22"]), load(P37.NAMES["p23"]), load(R.NAMES["p23"])
    b, carto = P37.beacon(), R.cartographer()
    hotend = r36.scene()["variants"]["RedLizard"]["hotend"]
    core = v26_parts()
    nuts = [core[n] for n in NUTS]
    zones = R.keepouts()
    beacon_hw = [s for _, s in P37.probe_hardware()]
    carto_hw = [s for _, s in R.hardware()]
    cut = box(-40.0, 0.0, -40.0, 40.0, -90.0, -40.0)
    side = ((300.0, 4.0, -71.0), (0.0, 4.0, -71.0))
    tip = P37.tip_datum()
    datum = [(box(-40.0, 0.0, -24.0, 32.0, tip - 0.05, tip + 0.05), RED)]      # the nozzle tip's height, as a line
    # Clip solid by solid: OCC returns nothing for some reference compounds with overlapping solids.
    hot = [(s, GREY) for s in hotend.Solids()]
    beacon = [(s, BOARD) for s in b[2:5]]
    probe = [(s, BOARD) for s in carto.Solids()]
    top = k["cartographer_on_r42_p23_2p81"]["top"]
    nut = top["core_metal"]["MONOC_M3_NUT_left_41.8"]
    screw = top["core_metal"]["MONOC_M3x16_DRAW_left_41.8"]
    sink = top["tool_metal"]["RedLizard_hotend"]
    panels = [
        view([(p22, TEAL), (p23, LIME)] + beacon + hot + datum + [(s, STEEL) for s in beacon_hw],
             cut, *side,
             f"Beacon RevH on revision 37's P23 ({P37.Z_TOP - P37.Z_SEAT:.2f} mm), cut at X0 through the coil and the "
             f"Red Lizard nozzle (the line under it is the tip's height):\ncoil {h['Beacon_RevH_on_r37_P23']['above_tip_mm']:.2f} mm above the tip "
             f"(Beacon: nominally 2.6). The Cartographer on this P23 sits at "
             f"{h['Cartographer_V3_on_r37_P23']['above_tip_mm']:.2f} mm", zoom=2.7),
        view([(p22, TEAL), (p23c, LIME)] + probe + hot + datum + [(s, STEEL) for s in carto_hw],
             cut, *side,
             f"Cartographer V3 on revision 42's P23 ({P37.Z_TOP - R.SEAT:.2f} mm, 0.2 mm thinner), cut at X0:\n"
             f"coil {h['Cartographer_V3_on_r42_P23']['above_tip_mm']:.2f} mm above the tip (Cartographer: 2.6 to 3.0). "
             f"M3x5 probe screws; P22 unchanged", zoom=2.7),
        view([(zones["top"], RED, 0.3), (zones["bottom"], PINK, 0.45), (p23c, LIME, 0.6)] + probe + hot
             + [(s, DARK) for s in nuts], None, (260.0, -170.0, -40.0), (0.0, 0.0, -64.0),
             f"The Cartographer's keepout, from its own model: no metal in the red column over the coil "
             f"(22.5 x 22.5 mm, 20 mm tall).\nThe Monolith core's two lower M3 nuts reach "
             f"{20 - nut['above_board_mm'][0]:.1f} mm into its top ({nut['mm3']:.1f} mm3 each) and its draw screws' "
             f"ends {20 - screw['above_board_mm'][0]:.2f} mm; the Red Lizard\nheater block {sink['bounds_mm'][3] - sink['bounds_mm'][2]:.2f} "
             f"mm into its front ({sink['mm3']:.2f} mm3). None of it is ours to move; none of our metal is in either zone",
             zoom=1.6),
        view([(zones["top"], RED, 0.3), (p23c, LIME, 0.6)] + probe + [(s, DARK) for s in nuts],
             box(-30.0, 30.0, -30.0, 30.0, -80.0, -50.0), (-120.0, 160.0, -20.0), (0.0, 4.0, -57.0),
             f"Close-up from the front: the nuts (and the screw ends between them) in the top of the column, "
             f"{nut['above_board_mm'][0]:.1f}-20 mm above the board,\n{abs(nut['bounds_mm'][0]):.1f}-"
             f"{abs(nut['bounds_mm'][1]):.1f} mm either side of the coil's axis", zoom=3.2),
    ]
    out = ROOT / "images" / "87_cartographer_mount_keepout_r42.png"
    sheet(panels, 2, SIZE, out)
    return out


def main():
    report = json.loads((ROOT / REPORT).read_text())
    print(image_87(report))


if __name__ == "__main__":
    main()
