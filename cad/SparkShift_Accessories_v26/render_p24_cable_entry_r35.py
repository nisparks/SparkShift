"""Revision 35 review image: the probe cable entering the wiring bay through P24, before and after."""

import json

import cadquery as cq
from PIL import Image, ImageDraw

import build_and_verify_accessories_v26 as acc
from build_carriage_lowered_mounts_r31 import NAMES as R31
from build_modular_toolhead import ROOT, box, load, primitives
from build_p24_cable_entry_r35 import CABLE_R, NAMES, REPORT, Y_BACK, Z_RUN, cable_route
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet

ORANGE, GREY, BLUE, RED, GREEN, TAN = ((0.95, 0.55, 0.12), (0.62, 0.64, 0.68), (0.15, 0.35, 0.85),
                                       (0.85, 0.05, 0.05), (0.25, 0.65, 0.3), (0.8, 0.72, 0.55))
SIZE = (900, 760)


def view(items, clip, eye, target, title, zoom=1.0):
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "p24_cable_entry_r35_panel.png"
    render_view(actors, eye, target, (0, 0, 1), path, width=SIZE[0], height=SIZE[1], zoom=zoom)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


def main():
    report = json.loads((ROOT / REPORT).read_text())
    old, new = load("P24_EBB42_Controller_Mount"), load(NAMES["p24"])
    old_cable = cq.Shape.cast(acc.make_cable_pipe(CABLE_R, Z_RUN, y_back=Y_BACK))
    cable = cable_route()
    clash = old_cable.intersect(old)
    p20, p21 = load("P20_CPAP_Hose_Inlet"), load("P21_CPAP_Gantry_Bridge")
    core = load(R31["core"])
    context = [(p21, TAN), (p20, GREEN)]
    low = box(-26, 26, -42, 2, -26, -9)
    half = box(-26, 0, -42, 2, -26, 26)
    above = ((70, 10, 90), (0, -22, -15))
    side = ((300, -22, -2), (0, -22, -2))
    panels = [
        view(context + [(old, ORANGE), (old_cable, BLUE), (clash, RED)], low, *above,
             f"Released P24 from above, cut below the board: the cable's forward run ends inside P24's bottom "
             f"({report['revision_21_cable']['overlap_with_released_p24_mm3']:.1f} mm3, red)", zoom=1.7),
        view(context + [(new, ORANGE), (cable, BLUE)], low, *above,
             "Revision 35: 3.8 mm slot at X0, 0.4 mm clear each side; the cable turns up into the bay", zoom=1.7),
        view(context + [(core, GREY), (old, ORANGE), (old_cable, BLUE), (clash, RED)], half, *side,
             "Section at X0, released: the cable runs into P24's bottom under the board", zoom=1.5),
        view(context + [(core, GREY), (new, ORANGE), (cable, BLUE)], half, *side,
             f"Section at X0, revision 35: R5 turn up, {report['cable']['vertical_run_to_board_standoff_plane_mm']:.1f} mm "
             f"to the board standoffs, {report['cable']['vertical_run_to_motor_rear_mm']:.1f} mm to the motor", zoom=1.5),
    ]
    out = ROOT / "images" / "65_p24_cable_entry_r35_before_after.png"
    sheet(panels, 2, SIZE, out)
    print(out)


if __name__ == "__main__":
    main()
