"""Expose both faces and the underside of the revised fan mounting region."""

from PIL import Image, ImageDraw

from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata


def render_comparison(before, after, before_label, after_label, filename):
    temp = primitives.WORK / f"{filename}_mesh.stl"
    clip = box(-40, 40, 0, 50, -58, -10)
    panels = []
    for name, eye, title in (
        (before, (-160, -45, -35), before_label),
        (after, (-160, -45, -35), after_label),
        (after, (160, -45, -15), "Fan-side L4 heatset pilot entries"),
        (after, (-80, -70, -130), "Underside, inlet sleeve and mounting webs"),
    ):
        actors = []
        for shape, color in (
            (load(name), (0.95, 0.67, 0.1)),
            (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.65, 0.65, 0.68)),
            (load("P18_Tool_docking_backplate_3010"), (0.65, 0.2, 0.65)),
        ):
            actors.append(make_actor(
                shape_to_polydata(shape.intersect(clip).wrapped, temp), color, edge_vis=True))
        path = primitives.WORK / f"{filename}_panel_{len(panels)}.png"
        render_view(actors, eye, (0, 25, -30), (0, 0, 1), path,
                    width=900, height=950, zoom=1.05)
        image = Image.open(path).convert("RGB")
        ImageDraw.Draw(image).text((15, 15), title, fill=(20, 20, 20))
        panels.append(image)
        path.unlink()
    output = Image.new("RGB", (1800, 1900), "white")
    for i, panel in enumerate(panels):
        output.paste(panel, (900 * (i % 2), 950 * (i // 2)))
    result = ROOT / "images" / f"{filename}.png"
    output.save(result)
    temp.unlink()
    print(result)


if __name__ == "__main__":
    render_comparison(
        "Bambu_Continuous_Guide_Clean_Fan_Mount_R25_REVIEW",
        "Bambu_Closed_Fan_Seats_Continuous_Junction_R26_REVIEW",
        "R25 REJECTED: open inner access scallops",
        "R26: closed inner face and continuous upper transition",
        "49_bambu_closed_mounts_r26_four_views")
