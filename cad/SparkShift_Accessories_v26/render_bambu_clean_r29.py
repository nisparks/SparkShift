"""Before/after review images for the revision-29 clean Bambu rebuild."""

from PIL import Image, ImageDraw

from build_bambu_clean_r29 import BASE, NAME
from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata

TMP = primitives.WORK / "bambu_r29_render.stl"
YELLOW = (0.95, 0.67, 0.1)


def panel(items, clip, eye, target, title, size=(900, 760)):
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "bambu_r29_panel.png"
    render_view(actors, eye, target, (0, 0, 1), path, width=size[0], height=size[1], zoom=1.0)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


def sheet(panels, columns, size, path):
    rows = (len(panels) + columns - 1) // columns
    out = Image.new("RGB", (size[0] * columns, size[1] * rows), "white")
    for i, p in enumerate(panels):
        out.paste(p, (size[0] * (i % columns), size[1] * (i // columns)))
    out.save(path)
    return path


def main():
    before, after = load(BASE), load(NAME)
    hotend = (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.72, 0.72, 0.75))
    p18 = (load("P18_Tool_docking_backplate_3010"), (0.8, 0.15, 0.75))
    fan = (load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW"), (0.16, 0.18, 0.22))
    core = (load("Core_With_Restrained_AHG_Lead_References_REVIEW"), (0.45, 0.48, 0.52))
    # Clip planes are offset from model faces to avoid coincident-face Boolean failures.
    region = box(-16.03, 16.07, 8.93, 40.07, -34.07, -13.93)
    views = [
        ("fan side, fan removed", (300, 40, 30), (8, 25, -24)),
        ("-X side from below", (-250, -90, -120), (0, 25, -26)),
        ("front, below P18", (60, 300, -20), (0, 34, -24)),
        ("front-right from below", (220, 220, -120), (6, 30, -25)),
    ]
    panels = []
    for title, eye, target in views:
        panels.append(panel([(before, YELLOW), hotend, p18], region, eye, target, f"R22 (before): {title}"))
        panels.append(panel([(after, YELLOW), hotend, p18], region, eye, target, f"R29 (clean rebuild): {title}"))
    comparison = sheet(panels, 2, (900, 760), ROOT / "images" / "56_bambu_clean_r29_before_after.png")
    y = (after, YELLOW)
    details = [
        panel([y, hotend, p18], box(-0.03, 16.07, 23.97, 40.07, -32.07, -15.93), (220, 200, -60), (9, 33, -24),
              "Front corner: fan boss bridged to shelf, neck closes slot under P18", (1000, 820)),
        panel([y, hotend], box(-9.03, 9.07, 13.97, 31.07, -34.07, -19.93), (-160, -120, -60), (0, 22.7, -28),
              "Inlet socket encloses the hotend inlet tube (no exposed filament)", (1000, 820)),
        panel([y, hotend], box(-2.03, 16.07, 7.97, 26.07, -32.07, -17.93), (160, -160, -200), (8, 16, -26),
              "Rear fan boss and flat shelf underside", (1000, 820)),
        panel([y, hotend, p18, fan, core], box(-25.03, 25.07, -0.07, 48.07, -52.07, -7.93), (300, 30, 25),
              (10, 25, -25), "Fan installed: original red-circle areas", (1000, 820)),
    ]
    detail_path = sheet(details, 2, (1000, 820), ROOT / "images" / "57_bambu_clean_r29_details.png")
    TMP.unlink(missing_ok=True)
    print(comparison)
    print(detail_path)


if __name__ == "__main__":
    main()
