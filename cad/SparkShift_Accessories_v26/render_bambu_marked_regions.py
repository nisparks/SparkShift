"""Color-separate the saved Bambu geometry for marked-region inspection."""

from PIL import Image, ImageDraw

from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata


def main():
    items = (
        ("Print", "Bambu_One_Piece_Docking_Audited_REVIEW", (0.95, 0.67, 0.1)),
        ("Hotend", "Tool2510_Reversed_Bambu_Reference_REVIEW", (0.7, 0.7, 0.72)),
        ("Fan", "Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW", (0.15, 0.3, 0.8)),
        ("Core", "Core_With_Restrained_AHG_Lead_References_REVIEW", (0.45, 0.48, 0.5)),
        ("Backplate", "P18_Tool_docking_backplate_3010", (0.8, 0.15, 0.75)),
        ("CPAP", "P22_CPAP_Lower_Plenum", (0.1, 0.65, 0.65)),
    )
    tmp = primitives.WORK / "marked_bambu_render_mesh.stl"
    actors = {}
    for label, name, color in items:
        shape = load(name).intersect(box(-60, 60, -60, 65, -58, -10))
        actors[label] = make_actor(
            shape_to_polydata(shape.wrapped, tmp), color, edge_vis=True)
    panels = []
    for labels, title in (
        (tuple(actors), "SECTIONED VIEW: blue fan, gray core, magenta backplate"),
        (("Print", "Hotend"), "SECTIONED VIEW: yellow print and gray hotend only"),
    ):
        path = primitives.WORK / f"bambu_region_panel_{len(panels)}.png"
        render_view([actors[k] for k in labels], (180, -65, 10), (0, 25, -30),
                    (0, 0, 1), path, width=1000, height=1200, zoom=1.1)
        panel = Image.open(path).convert("RGB")
        ImageDraw.Draw(panel).text((18, 18), title, fill=(20, 20, 20))
        panels.append(panel)
        path.unlink()
    output = Image.new("RGB", (2000, 1200), "white")
    for i, panel in enumerate(panels):
        output.paste(panel, (i * 1000, 0))
    path = ROOT / "images" / "46_bambu_marked_region_identity.png"
    output.save(path)
    tmp.unlink()
    print(path)


if __name__ == "__main__":
    main()
