"""Revision 29 vs 30 review images: compact fan side, closed P18 bores, carriage clearance."""

from PIL import Image, ImageDraw

from build_bambu_clean_r30 import FAN_DX, NAME, PITCH
from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, YELLOW, panel, sheet


def top_panel(items, clip, center, title):
    """Plan view looking down -Z with +Y up, so the docking direction reads vertically."""
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "bambu_r30_top.png"
    render_view(actors, (center[0], center[1], 300), center, (0, 1, 0), path, width=900, height=760, zoom=1.0)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


def main():
    r29, r30 = load("Bambu_Clean_Rebuild_R29_REVIEW"), load(NAME)
    hotend = (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.72, 0.72, 0.75))
    p18 = (load("P18_Tool_docking_backplate_3010"), (0.8, 0.15, 0.75))
    fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
    screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")
    black, grey = (0.1, 0.1, 0.12), (0.4, 0.4, 0.42)
    fans = {29: [(fan, black), (screws, grey)],
            30: [(fan.translate((FAN_DX, 0, 0)), black), (screws.translate((FAN_DX, 0, 0)), grey)]}
    region = box(-16.03, 23.07, 8.93, 40.07, -52.07, -9.93)
    views = [
        ("rear view, fan fitted", (10, -300, -20), (2, 25, -28), True),
        ("fan side, fan removed", (300, 40, 30), (8, 25, -24), False),
        ("-X side from below", (-250, -90, -120), (0, 25, -26), False),
        ("front-right from below, fan removed", (220, 220, -120), (6, 30, -25), False),
    ]
    panels = []
    for title, eye, target, with_fan in views:
        for rev, body in ((29, r29), (30, r30)):
            items = [(body, YELLOW), hotend, p18] + (fans[rev] if with_fan else [])
            panels.append(panel(items, region, eye, target, f"R{rev}: {title}"))
    comparison = sheet(panels, 2, (900, 760), ROOT / "images" / "58_bambu_compact_r30_before_after.png")
    # Close-ups: the closed P18 bore ends, and the strip that crowded the active carriage.
    core = load("Core_With_Restrained_AHG_Lead_References_REVIEW")
    junction = box(-10.53, 10.57, 24.93, 40.07, -22.07, -11.93)
    plan = box(-30.03, -16.97, 6.07, 20.07, -26.07, -22.53)
    details = []
    for rev, body in ((29, r29), (30, r30)):
        details.append(panel([(body, YELLOW), p18], junction, (0, -150, 160), (0, 31.5, -17.5),
                             f"R{rev}: P18 insert bores behind the flange (from above-behind)"))
    for rev, body in ((29, r29), (30, r30)):
        details.append(top_panel([(body.translate((-PITCH, 0, 0)), YELLOW), (core, (0.36, 0.39, 0.43))], plan,
                                 (-23.5, 13.0, -24.0),
                                 f"R{rev}: top view, +Y up. Parked neighbour (yellow) vs active carriage frame (grey)"))
    detail_path = sheet(details, 2, (900, 760), ROOT / "images" / "59_bambu_compact_r30_details.png")
    TMP.unlink(missing_ok=True)
    print(comparison)
    print(detail_path)


if __name__ == "__main__":
    main()
