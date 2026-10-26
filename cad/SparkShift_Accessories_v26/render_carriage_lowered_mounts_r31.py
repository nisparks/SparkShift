"""Revision 30 vs 31 carriage review images: P22-to-P01 front mounts lowered 1.5 mm under the 2510 fans."""

import json

from PIL import Image, ImageDraw

from audit_tool_owned_2510 import compound
from build_bambu_clean_r30 import PITCH, fan_parts
from build_carriage_lowered_mounts_r31 import CORE, CORE_P01, NAMES, P01_BASE, P22_BASE, REPORT, hardware
from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, YELLOW, sheet

GREY, TEAL, BRASS, STEEL, DARK = (0.47, 0.49, 0.54), (0.1, 0.65, 0.65), (0.85, 0.6, 0.15), (0.3, 0.3, 0.33), (0.12, 0.12, 0.14)


def panel(items, clip, eye, target, title, zoom=1.0, size=(900, 760)):
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "carriage_r31_panel.png"
    render_view(actors, eye, target, (0, 0, 1), path, width=size[0], height=size[1], zoom=zoom)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


def fasteners(shape):
    """Screws (about 86 mm3) in steel, heat-set inserts (about 35 mm3) in brass."""
    solids = shape.Solids()
    return [(compound([s for s in solids if s.Volume() > 60]), STEEL),
            (compound([s for s in solids if s.Volume() <= 60]), BRASS)]


def main():
    report = json.loads((ROOT / REPORT).read_text())
    gap = report["clearances"]["vertical_gap_fan_bottom_to_p01_p22_under_fan_mm"]
    core = load(CORE).Solids()
    others = compound([s for i, s in enumerate(core) if i != CORE_P01])
    fan, screws, _ = fan_parts()
    tool = [(load("Bambu_Compact_Fan_Closed_Bores_R30_REVIEW"), YELLOW),
            (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.72, 0.72, 0.75)),
            (load("P18_Tool_docking_backplate_3010"), (0.8, 0.15, 0.75)),
            (fan, DARK), (screws, (0.4, 0.4, 0.42)),
            (load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW"), BRASS)]
    neighbour = [(s.translate((-PITCH, 0, 0)), c) for s, c in tool]
    carriages = {
        30: [(load(P01_BASE), GREY), (load(P22_BASE), TEAL)] + fasteners(compound([s for _, s in hardware(0.0)])),
        31: [(load(NAMES["p01"]), GREY), (load(NAMES["p22"]), TEAL)] + fasteners(load(NAMES["hardware"])),
    }
    common = [(others, (0.3, 0.33, 0.5)), (load("P21_CPAP_Gantry_Bridge"), (0.2, 0.55, 0.35))]
    label = {30: f"R30 (released): {gap['released']:.2f} mm fan-to-mount gap",
             31: f"R31: mounts 1.5 mm lower, {gap['r31']:.2f} mm gap"}
    views = [
        ("own fan side, as in Fusion", tool, box(-24.03, 24.07, -11.93, 40.07, -62.07, -18.93),
         (430, -134, -54), (4, 14, -46), 1.0),
        ("section X=+18 through the +X mount, own fan above", tool, box(-24.03, 18.03, -2.07, 40.07, -64.07, -18.93),
         (300, 18, -42), (10, 18, -48), 1.0),
        ("section X=-18 through the -X mount, parked neighbour's fan above", neighbour,
         box(-18.03, 24.07, -2.07, 40.07, -64.07, -18.93), (-300, 18, -42), (-10, 18, -48), 1.0),
        ("close-up, section X=+18: fan (black), P01 boss (grey), P22 cheek (teal), M3 screw (steel), insert (brass)",
         tool, box(-24.03, 18.03, 6.07, 24.07, -61.07, -43.93), (300, 15, -52), (10, 15, -52), 2.3),
    ]
    panels = []
    for title, toolset, clip, eye, target, zoom in views:
        for rev in (30, 31):
            panels.append(panel(common + carriages[rev] + toolset, clip, eye, target, f"{label[rev]} | {title}", zoom))
    path = sheet(panels, 2, (900, 760), ROOT / "images" / "60_carriage_lowered_mounts_r31_before_after.png")
    TMP.unlink(missing_ok=True)
    print(path)


if __name__ == "__main__":
    main()
