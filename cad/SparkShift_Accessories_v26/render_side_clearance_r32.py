"""Revision 30 vs 32 review images: flush -X side on both bodies and the Red Lizard fan-recess skin."""

import json

from PIL import Image, ImageDraw

from audit_low_z_bed_clearance import load_parked_variants
from audit_tool_owned_2510 import compound
from build_bambu_clean_r30 import PITCH
from build_carriage_lowered_mounts_r31 import CORE, CORE_P01, NAMES as R31
from build_modular_toolhead import ROOT, box, load, primitives
from build_side_clearance_r32 import REPORT, VARIANTS
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, YELLOW, sheet

GREY, CORE_BLUE, DARK, HOT = (0.47, 0.49, 0.54), (0.3, 0.33, 0.5), (0.12, 0.12, 0.14), (0.72, 0.72, 0.75)


def view(items, clip, eye, target, up, title, zoom=1.0, size=(900, 760)):
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "side_r32_panel.png"
    render_view(actors, eye, target, up, path, width=size[0], height=size[1], zoom=zoom)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


def main():
    report = json.loads((ROOT / REPORT).read_text())["clearances_mm"]
    skin = report["active carriage | RedLizard parked at -37.3"]
    core = load(CORE).Solids()
    carriage = [(load(R31["p01"]), GREY), (compound([s for i, s in enumerate(core) if i != CORE_P01]), CORE_BLUE)]
    bodies = {rev: {label: load(v["base"] if rev == 30 else v["name"]) for label, v in VARIANTS.items()}
              for rev in (30, 32)}
    red = load_parked_variants()["RedLizard"]["tool"].Solids()
    red_hot = compound(red[1:14])
    bambu_hot = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    panels = []
    for rev in (30, 32):
        gap = load(R31["p01"]).distance(bodies[rev]["Bambu"].translate((PITCH, 0, 0)))
        items = carriage + [(bodies[rev]["Bambu"].translate((PITCH, 0, 0)), YELLOW)]
        panels.append(view(items, box(10.03, 36.07, 5.07, 24.07, -26.03, -17.03), (23, 13, 300), (23, 13, -22),
                           (0, 1, 0), f"R{rev}: plan view, active carriage P01 (grey) to the Bambu body parked at "
                                      f"+37.3 (yellow): {gap:.2f} mm"))
    for rev in (30, 32):
        panels.append(view([(bodies[rev]["Bambu"], YELLOW), (bambu_hot, HOT)],
                           box(-16.03, 0.07, 8.07, 36.07, -32.07, -14.03), (-260, -150, -170), (-10, 22, -23),
                           (0, 0, 1), f"R{rev}: Bambu non-fan (-X) side from below-behind"))
    for rev in (30, 32):
        panels.append(view([(bodies[rev]["RedLizard"], YELLOW), (red_hot, HOT)],
                           box(-16.03, 0.07, 8.07, 36.07, -32.07, -14.03), (-260, -150, -170), (-10, 22, -23),
                           (0, 0, 1), f"R{rev}: Red Lizard non-fan (-X) side from below-behind"))
    for rev in (30, 32):
        gap = skin["r30_bodies" if rev == 30 else "r32_bodies"]["mm"]
        panels.append(view([(bodies[rev]["RedLizard"], YELLOW)],
                           box(4.03, 18.07, 8.07, 36.07, -26.07, -16.03), (220, -60, -260), (11, 22, -22.5),
                           (0, 0, 1), f"R{rev}: Red Lizard fan side from below, fan hidden. "
                                      f"Carriage to a Red Lizard parked at -37.3: {gap:.2f} mm"))
    path = sheet(panels, 2, (900, 760), ROOT / "images" / "61_side_clearance_r32_before_after.png")
    TMP.unlink(missing_ok=True)
    print(path)


if __name__ == "__main__":
    main()
