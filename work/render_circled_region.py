"""Color-coded render of the carriage around the user's circled spot (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import numpy as np
from PIL import Image, ImageDraw

from build_modular_toolhead import box, load
from render_accessories_v26 import make_actor, render_view, shape_to_polydata

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
TMP = OUT / "tmp_circle.stl"
core = load("Core_With_Restrained_AHG_Lead_References_REVIEW").Solids()
p22 = load("P22_CPAP_Lower_Plenum")
fan = load("Bambu_Fan_2510_And_Screws_R30_REVIEW")
colors = {54: (0.55, 0.55, 0.6), 16: (0.3, 0.3, 0.8), 17: (0.8, 0.5, 0.2), 21: (0.8, 0.5, 0.2),
          20: (0.6, 0.2, 0.6), 24: (0.6, 0.2, 0.6), 19: (0.9, 0.9, 0.2), 23: (0.9, 0.9, 0.2), 18: (0.9, 0.9, 0.2),
          22: (0.9, 0.9, 0.2), 25: (0.9, 0.2, 0.2), 26: (0.9, 0.2, 0.2), 27: (0.9, 0.2, 0.2), 28: (0.9, 0.2, 0.2),
          29: (0.2, 0.7, 0.3), 30: (0.2, 0.7, 0.3), 31: (0.2, 0.7, 0.3)}
clip = box(-24.03, 24.07, -12.07, 24.07, -60.07, -40.07)
eye_dir = np.array([427.228 + 23.186, -133.663 - 6.568, -53.738 + 45.88])
eye_dir /= np.linalg.norm(eye_dir)
panels = []
for title, focus, dist_dir, items in (
        ("User's view direction: grey=P01, blue=rail block, purple=side plates, yellow=screws, red=nuts, teal=P22",
         (6, 6, -52), eye_dir, "all"),
        ("Same, P22 hidden", (6, 6, -52), eye_dir, "no_p22"),
        ("From directly behind (-Y), P22 hidden", (0, 0, -50), np.array([0, -1, 0.05]), "no_p22"),
        ("From below-front-right, fan + P22 + P01 bosses", (12, 14, -50), np.array([0.6, 0.6, -0.5]), "all")):
    actors = []
    for i, s in enumerate(core):
        if i in colors or i == 54:
            part = s.intersect(clip)
            if part.Solids():
                actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), colors.get(i, (0.5, 0.5, 0.5)), 1.0, edge_vis=True))
    if items == "all":
        actors.append(make_actor(shape_to_polydata(p22.intersect(clip).wrapped, TMP), (0.1, 0.6, 0.62), 1.0, edge_vis=True))
        actors.append(make_actor(shape_to_polydata(fan.intersect(clip).wrapped, TMP), (0.1, 0.1, 0.12), 1.0, edge_vis=True))
    path = OUT / "circle_tmp.png"
    eye = tuple(np.array(focus) + 300 * np.array(dist_dir) / np.linalg.norm(dist_dir))
    render_view(actors, eye, focus, (0, 0, 1), path, width=1000, height=800, zoom=1.0)
    img = Image.open(path).convert("RGB")
    ImageDraw.Draw(img).text((10, 10), title, fill=(0, 0, 0))
    panels.append(img)
    path.unlink()
sheet = Image.new("RGB", (2000, 1600), "white")
for i, p in enumerate(panels):
    sheet.paste(p, (1000 * (i % 2), 800 * (i // 2)))
sheet.save(OUT / "circled_region.png")
TMP.unlink(missing_ok=True)
print(OUT / "circled_region.png")
