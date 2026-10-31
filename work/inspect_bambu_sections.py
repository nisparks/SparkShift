"""Cut-away section renders around the Bambu shelf/front junction (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

from PIL import Image, ImageDraw

import cadquery as _cq
from build_modular_toolhead import box, load
from render_accessories_v26 import make_actor, render_view, shape_to_polydata

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
OUT.mkdir(exist_ok=True)
TMP = OUT / "tmp_section.stl"

PARTS = [
    ("Tool2510_Reversed_Bambu_Reference_REVIEW", (0.75, 0.75, 0.78)),
    ("P18_Tool_docking_backplate_3010", (0.8, 0.15, 0.75)),
    ("Core_With_Restrained_AHG_Lead_References_REVIEW", (0.40, 0.43, 0.46)),
    ("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW", (0.15, 0.75, 0.25)),
    ("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW", (0.15, 0.3, 0.85)),
]


def load_any(name):
    return _cq.importers.importStep(name).val() if name.lower().endswith('.step') else load(name)


def render(body_name, keep, eye, target, title, path, extra=()):
    actors = []
    for name, color in [(body_name, (0.95, 0.67, 0.1))] + PARTS + list(extra):
        shape = load_any(name).intersect(keep)
        if shape.isNull() or not shape.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(shape.wrapped, TMP), color, 1.0, edge_vis=True))
    render_view(actors, eye, target, (0, 0, 1), path, width=900, height=800, zoom=1.0)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    return image


if __name__ == "__main__":
    body = sys.argv[1]
    tag = sys.argv[2]
    cuts = [
        ("Section Y=33.5 looking -Y (keep Y<33.5)", box(-16, 23, 10, 33.5, -34, -8), (0, 300, 0), (0, 20, -22)),
        ("Section Y=35.5 (front fan screw axis), keep Y<35.5", box(-16, 23, 10, 35.5, -34, -8), (0, 300, 0), (0, 20, -22)),
        ("Section Y=37.0, keep Y<37", box(-16, 23, 10, 37.0, -34, -8), (0, 300, 0), (0, 20, -22)),
        ("Section X=0 (hotend axis), keep X>0, from -X", box(0, 23, 8, 48, -34, -8), (-300, 0, 0), (0, 28, -22)),
        ("Section X=6 (P18/hotend screw), keep X>6, from -X", box(6, 23, 8, 48, -34, -8), (-300, 0, 0), (6, 28, -22)),
        ("Section X=9.5 (fan seats), keep X>9.5, from -X", box(9.5, 23, 8, 48, -34, -8), (-300, 0, 0), (9.5, 28, -22)),
    ]
    panels = []
    for i, (title, keep, eye, target) in enumerate(cuts):
        panels.append(render(body, keep, eye, target, title, OUT / f"sec_{i}.png"))
        (OUT / f"sec_{i}.png").unlink()
    out = Image.new("RGB", (1800, 2400), "white")
    for i, panel in enumerate(panels):
        out.paste(panel, (900 * (i % 2), 800 * (i // 2)))
    out.save(OUT / f"{tag}_sections.png")
    print(OUT / f"{tag}_sections.png")

