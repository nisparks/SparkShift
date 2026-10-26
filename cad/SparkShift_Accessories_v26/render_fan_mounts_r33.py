"""Revision 32 vs 33 review images: third Bambu fan screw and the Red Lizard fan wall."""

from PIL import Image, ImageDraw

from audit_tool_owned_2510 import compound
from build_bambu_clean_r30 import fan_parts
from build_fan_mounts_r33 import NAMES, red_lizard_parts
from build_modular_toolhead import ROOT, box, load, primitives
from build_side_clearance_r32 import VARIANTS as R32
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet

ORANGE, GREY, DARK, BRASS, STEEL, P18 = ((0.95, 0.55, 0.12), (0.72, 0.72, 0.75), (0.13, 0.13, 0.15),
                                        (0.85, 0.62, 0.18), (0.45, 0.45, 0.5), (0.75, 0.2, 0.7))


def view(items, clip, eye, target, title, up=(0, 0, 1), zoom=1.0):
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "fan_mounts_r33_panel.png"
    render_view(actors, eye, target, up, path, width=900, height=760, zoom=zoom)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


def main():
    fan, screws2, _ = fan_parts()
    rl = red_lizard_parts()
    bambu = {32: (load(R32["Bambu"]["name"]), load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW"), screws2),
             33: (load(NAMES["bambu"]), load(NAMES["bambu_inserts"]), compound(
                 [s for s in load(NAMES["bambu_fan"]).Solids() if s.Volume() < 300]))}
    red = {32: (load(R32["RedLizard"]["name"]), rl["old_inserts"]), 33: (load(NAMES["redlizard"]), load(NAMES["redlizard_inserts"]))}
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    p18 = load("P18_Tool_docking_backplate_3010")
    low = box(-30.03, 30.07, 0.07, 50.07, -80.03, -14.97)
    panels = []
    for rev in (32, 33):
        body, inserts, screws = bambu[rev]
        panels.append(view([(body, ORANGE), (hotend, GREY), (fan, DARK), (screws, STEEL), (p18, P18)], low,
                           (230, 330, -20), (9, 28, -40), f"R{rev} Bambu: front, fan side ({len(screws.Solids())} fan screws)"))
    for rev in (32, 33):
        body, inserts, screws = bambu[rev]
        panels.append(view([(body, ORANGE), (inserts, BRASS)], low, (260, 120, -170), (8, 30, -40),
                           f"R{rev} Bambu body and fan inserts, fan removed, from below the fan side"))
    for rev in (32, 33):
        body, inserts = red[rev]
        panels.append(view([(body, ORANGE), (rl["hotend"], GREY), (rl["fan"], DARK), (rl["screws"], STEEL), (rl["p18"], P18)],
                           low, (230, 330, -20), (9, 28, -38), f"R{rev} Red Lizard: front, fan side"))
    for rev in (32, 33):
        body, inserts = red[rev]
        panels.append(view([(body, ORANGE), (inserts, BRASS)], low, (-200, 250, -170), (5, 30, -32),
                           f"R{rev} Red Lizard body and fan inserts from the front, below"))
    for rev in (32, 33):
        body, inserts = red[rev]
        panels.append(view([(body, ORANGE), (inserts, BRASS), (rl["hotend"], GREY), (rl["fan"], DARK), (rl["p18"], P18)],
                           box(-14.03, 24.07, 33.93, 50.07, -52.03, -14.97), (2, -300, -33), (4, 34, -33),
                           f"R{rev} Red Lizard section at Y=33.9, looking forward (P18 bores, neck, fan wall)"))
    path = sheet(panels, 2, (900, 760), ROOT / "images" / "62_fan_mounts_r33_before_after.png")
    TMP.unlink(missing_ok=True)
    print(path)


if __name__ == "__main__":
    main()
