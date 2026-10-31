"""Investigation renders of Bambu bodies with distinct reference colors (not a repo artifact)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

from PIL import Image, ImageDraw

import cadquery as _cq
from build_modular_toolhead import box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
OUT.mkdir(exist_ok=True)
TMP = OUT / "tmp_mesh.stl"

REFS = {
    "hotend": ("Tool2510_Reversed_Bambu_Reference_REVIEW", (0.72, 0.72, 0.75), 1.0),
    "fan": ("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW", (0.15, 0.3, 0.85), 1.0),
    "p18": ("P18_Tool_docking_backplate_3010", (0.8, 0.15, 0.75), 1.0),
    "core": ("Core_With_Restrained_AHG_Lead_References_REVIEW", (0.42, 0.45, 0.48), 1.0),
    "cpap": ("P22_CPAP_Lower_Plenum", (0.1, 0.65, 0.65), 1.0),
}


def load_any(name):
    return _cq.importers.importStep(name).val() if name.lower().endswith('.step') else load(name)


def actors_for(body_name, clip, include):
    items = [(load_any(body_name), (0.95, 0.67, 0.1), 1.0)]
    for key in include:
        name, color, opacity = REFS[key]
        items.append((load(name), color, opacity))
    actors = []
    for shape, color, opacity in items:
        clipped = shape.intersect(clip)
        if clipped.isNull() or not clipped.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(clipped.wrapped, TMP), color, opacity, edge_vis=True))
    return actors


def sheet(body_name, views, filename, size=(900, 800)):
    panels = []
    for title, eye, target, clip, include in views:
        path = OUT / f"panel_{len(panels)}.png"
        render_view(actors_for(body_name, clip, include), eye, target, (0, 0, 1), path,
                    width=size[0], height=size[1], zoom=1.0)
        image = Image.open(path).convert("RGB")
        ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
        panels.append(image)
        path.unlink()
    cols = 2
    rows = (len(panels) + 1) // 2
    out = Image.new("RGB", (size[0] * cols, size[1] * rows), "white")
    for i, panel in enumerate(panels):
        out.paste(panel, (size[0] * (i % cols), size[1] * (i // cols)))
    out.save(OUT / filename)
    print(OUT / filename)


if __name__ == "__main__":
    body = sys.argv[1]
    tag = sys.argv[2]
    local = box(-20, 25, 5, 48, -52, -8)
    upper = box(-20, 25, 5, 48, -34, -10)
    views = [
        ("+X side, fan hidden: upper fan seats, front junction", (200, 30, -20), (10, 25, -25), upper, ["hotend", "p18", "core"]),
        ("+X side with blue fan", (200, 30, -20), (10, 25, -25), local, ["hotend", "fan", "p18", "core"]),
        ("-X side from below (wedge/scallop view)", (-200, -60, -80), (0, 25, -26), local, ["hotend", "p18"]),
        ("Underside looking up, core hidden", (-60, -40, -200), (0, 25, -26), local, ["hotend", "p18"]),
        ("Front (+Y) upper junction, P18 magenta", (40, 200, 10), (0, 30, -20), upper, ["hotend", "p18", "core"]),
        ("Rear (-Y) upper junction", (40, -200, 10), (0, 20, -20), upper, ["hotend", "core"]),
    ]
    sheet(body, views, f"{tag}_views.png")

