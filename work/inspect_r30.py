"""R29 vs R30 inspection from the user's rear view and the fan side (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
from PIL import Image, ImageDraw

from build_modular_toolhead import box, load
from render_accessories_v26 import make_actor, render_view, shape_to_polydata

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
TMP = OUT / "tmp_r30.stl"
PREVIEW = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\Bambu_Compact_Fan_Closed_Bores_R30_REVIEW_preview.step"


def panel(items, clip, eye, target, title):
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = OUT / "r30_tmp.png"
    render_view(actors, eye, target, (0, 0, 1), path, width=900, height=760, zoom=1.0)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


r29 = load("Bambu_Clean_Rebuild_R29_REVIEW")
r30 = cq.importers.importStep(PREVIEW).val()
hotend = (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.72, 0.72, 0.75))
p18 = (load("P18_Tool_docking_backplate_3010"), (0.8, 0.15, 0.75))
fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")
black = (0.1, 0.1, 0.12)
clip = box(-16.03, 23.07, 8.93, 40.07, -52.07, -9.93)
views = [
    ("rear view (yours), fan on", (10, -300, -20), (2, 25, -28)),
    ("-X side from below", (-250, -90, -120), (0, 25, -26)),
    ("fan side, fan removed", (300, 40, 30), (8, 25, -24)),
    ("front-right from below, fan removed", (220, 220, -120), (6, 30, -25)),
]
rows = []
for i, (title, eye, target) in enumerate(views):
    with_fan = i == 0
    before = [(r29, (0.95, 0.67, 0.1)), hotend, p18] + ([(fan, black), (screws, (0.4, 0.4, 0.42))] if with_fan else [])
    after = [(r30, (0.95, 0.67, 0.1)), hotend, p18] + ([(fan.translate((-1.65, 0, 0)), black),
                                                       (screws.translate((-1.65, 0, 0)), (0.4, 0.4, 0.42))] if with_fan else [])
    rows.append((panel(before, clip, eye, target, "R29: " + title), panel(after, clip, eye, target, "R30: " + title)))
sheet = Image.new("RGB", (1800, 760 * len(rows)), "white")
for i, (a, b) in enumerate(rows):
    sheet.paste(a, (0, 760 * i))
    sheet.paste(b, (900, 760 * i))
sheet.save(OUT / "r29_vs_r30.png")
TMP.unlink(missing_ok=True)
print(OUT / "r29_vs_r30.png")
