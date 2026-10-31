"""Close-up before/after renders of the Bambu shelf region (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
from PIL import Image, ImageDraw

from build_modular_toolhead import box, load
from render_accessories_v26 import make_actor, render_view, shape_to_polydata

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
TMP = OUT / "tmp_closeup.stl"
REFS = [
    ("Tool2510_Reversed_Bambu_Reference_REVIEW", (0.72, 0.72, 0.75)),
    ("P18_Tool_docking_backplate_3010", (0.8, 0.15, 0.75)),
]


def load_any(name):
    return cq.importers.importStep(name).val() if name.lower().endswith(".step") else load(name)


def panel(body, clip, eye, target, title, extra=()):
    actors = []
    for shape, color in [(body, (0.95, 0.67, 0.1))] + [(load(n), c) for n, c in REFS] + list(extra):
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = OUT / "closeup_tmp.png"
    render_view(actors, eye, target, (0, 0, 1), path, width=900, height=760, zoom=1.0)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


if __name__ == "__main__":
    before, after, tag = load_any(sys.argv[1]), load_any(sys.argv[2]), sys.argv[3]
    region = box(-16, 16, 9, 40, -34, -14)
    views = [
        ("+X fan side (fan removed)", (300, 40, 30), (8, 25, -24)),
        ("-X from below (your wedge view)", (-250, -90, -120), (0, 25, -26)),
        ("Underside, looking up", (-60, -40, -300), (0, 25, -26)),
        ("Front (+Y), below P18", (60, 300, -20), (0, 34, -24)),
        ("Front-right (+X+Y) from below", (220, 220, -120), (6, 30, -25)),
    ]
    rows = []
    for title, eye, target in views:
        rows.append((panel(before, region, eye, target, f"BEFORE (R22): {title}"),
                     panel(after, region, eye, target, f"AFTER (R29): {title}")))
    sheet = Image.new("RGB", (1800, 760 * len(rows)), "white")
    for i, (a, b) in enumerate(rows):
        sheet.paste(a, (0, 760 * i))
        sheet.paste(b, (900, 760 * i))
    sheet.save(OUT / f"{tag}_closeups.png")
    print(OUT / f"{tag}_closeups.png")
