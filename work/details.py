"""High-magnification review panels of one Bambu body (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
from PIL import Image, ImageDraw

from build_modular_toolhead import box, load
from render_accessories_v26 import make_actor, render_view, shape_to_polydata

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
TMP = OUT / "tmp_detail.stl"


def load_any(name):
    return cq.importers.importStep(name).val() if name.lower().endswith(".step") else load(name)


def panel(items, clip, eye, target, title):
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = OUT / "detail_tmp.png"
    render_view(actors, eye, target, (0, 0, 1), path, width=1000, height=820, zoom=1.0)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


if __name__ == "__main__":
    body, tag = load_any(sys.argv[1]), sys.argv[2]
    hotend = (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.72, 0.72, 0.75))
    p18 = (load("P18_Tool_docking_backplate_3010"), (0.8, 0.15, 0.75))
    fan = (load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW"), (0.16, 0.18, 0.22))
    core = (load("Core_With_Restrained_AHG_Lead_References_REVIEW"), (0.45, 0.48, 0.52))
    yellow = (body, (0.95, 0.67, 0.1))
    views = [
        ("Front-right corner: fan boss, bridge, neck under P18", [yellow, hotend, p18],
         box(0, 16, 24, 40, -32, -16), (220, 200, -60), (9, 33, -24)),
        ("Inlet socket sleeve (hotend gray)", [yellow, hotend],
         box(-9, 9, 14, 31, -34, -20), (-160, -120, -60), (0, 22.7, -28)),
        ("Rear fan boss from below", [yellow, hotend],
         box(-2, 16, 8, 26, -32, -18), (160, -160, -200), (8, 16, -26)),
        ("Your original +X view, fan installed (cf. red circles)", [yellow, hotend, p18, fan, core],
         box(-25, 25, 0, 48, -52, -8), (300, 30, 25), (10, 25, -25)),
    ]
    panels = [panel(items, clip, eye, target, title) for title, items, clip, eye, target in views]
    sheet = Image.new("RGB", (2000, 1640), "white")
    for i, p in enumerate(panels):
        sheet.paste(p, (1000 * (i % 2), 820 * (i // 2)))
    sheet.save(OUT / f"{tag}_details.png")
    print(OUT / f"{tag}_details.png")
