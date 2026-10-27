"""Revision 36 review image: the chute arm chamfer and the side clearance it buys."""

import cadquery as cq
from PIL import Image, ImageDraw, ImageFont

import fast_geometry
from build_chute_chamfer_rack_r36 import NAMES, OLD_CHUTE, PITCH, build_chute, scene
from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet

ORANGE, GREY, RED, GREEN, YELLOW, CHUTE, BLUE = ((0.95, 0.55, 0.12), (0.62, 0.64, 0.68), (0.9, 0.05, 0.05),
                                                 (0.22, 0.4, 0.32), (0.9, 0.7, 0.15), (0.75, 0.2, 0.2),
                                                 (0.15, 0.35, 0.85))
SIZE = (900, 760)


def gap_bar(a, b, radius=0.07):
    a, b = cq.Vector(*a), cq.Vector(*b)
    return cq.Solid.makeCylinder(radius, (b - a).Length, a, (b - a).normalized())


def view(items, clip, eye, target, title, zoom=1.0):
    actors = []
    for shape, color in items:
        part = shape if clip is None else shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "chute_chamfer_r36_panel.png"
    render_view(actors, eye, target, (0, 0, 1), path, width=SIZE[0], height=SIZE[1], zoom=zoom)
    image = Image.open(path).convert("RGB")
    draw, font = ImageDraw.Draw(image), ImageFont.truetype("arial.ttf", 17)
    lines, line = [], ""
    for word in title.split():
        if draw.textlength(f"{line} {word}", font=font) > SIZE[0] - 30:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    draw.rectangle((0, 0, SIZE[0], 14 + 22 * len(lines)), fill=(255, 255, 255))
    for i, text in enumerate(lines):
        draw.text((12, 8 + 22 * i), text, fill=(10, 10, 10), font=font)
    path.unlink()
    return image


def main():
    _, chute_report, _ = build_chute()
    s = scene()
    parts = dict(s["carriage_parts"])
    from build_carriage_lowered_mounts_r31 import NAMES as R31
    p22, core = parts[R31["p22"]], parts[R31["core"]]
    old_chute, new_chute = load(OLD_CHUTE), load(NAMES["chute"])
    bambu = s["variants"]["Bambu"]
    body = dict(bambu["parts"])["body"]
    rig = fast_geometry.index_group([("P22", p22), ("Core", core)])
    pair = {}
    for tag, chute in (("r21", old_chute), ("r36", new_chute)):
        hit = fast_geometry.min_distance(rig, fast_geometry.index_group([("P26", chute)]), (0, 0, 0), (PITCH, 0, 0), 6.0)
        pair[tag] = hit
    limit = fast_geometry.min_distance(rig, fast_geometry.index_group([("Body", body)]), (0, 0, 0), (PITCH, 0, 0), 6.0)
    y = pair["r21"][3][1]
    dock = bambu["dock_solids"]
    section = box(4, 40, y, y + 40, -92, -62)
    eye, target = (21.5, y - 400, -78.0), (21.5, y, -78.0)

    def neighbour(chute):
        return [(dock[0].translate((PITCH, 0, 0)), GREEN), (chute.translate((PITCH, 0, 0)), CHUTE),
                (body.translate((PITCH, 0, 0)), YELLOW)]

    base = [(core, GREY), (p22, ORANGE)]
    panels = [
        view(base + neighbour(old_chute) + [(gap_bar(pair["r21"][3], pair["r21"][4]), BLUE)], section, eye, target,
             f"Revision 21, section at Y{y:.1f} looking toward the dock: the active carriage's P22 (orange) passes "
             f"the sharp top edge of the neighbouring chute's arm (red) at {pair['r21'][0]:.2f} mm (blue bar)", zoom=1.9),
        view(base + neighbour(new_chute) + [(gap_bar(pair["r36"][3], pair["r36"][4]), BLUE)], section, eye, target,
             f"Revision 36: the 1.5 mm chamfer opens that gap to {pair['r36'][0]:.2f} mm. The side limit becomes P01 "
             f"to the neighbour's printed body higher up, {limit[0]:.2f} mm", zoom=1.9),
        view([(new_chute, CHUTE), (old_chute.cut(new_chute), BLUE)], None, (95, -70, -20), (0, 27, -84),
             f"Revision-36 P26: both arm top outer edges chamfered 1.5 mm x 45 deg (removed "
             f"{chute_report['removed_mm3']:.1f} mm3, blue); {min(chute_report['wall_to_m3_head_channel_mm'].values()):.2f} mm "
             f"left to the M3 head channels", zoom=1.4),
        view(base + neighbour(new_chute) + [(gap_bar(pair["r36"][3], pair["r36"][4], 0.35), BLUE),
                                            (gap_bar(limit[3], limit[4], 0.35), RED)],
             box(0, 46, -60, 60, -96, -14), (23, -400, -55), (23, 20, -55),
             "Looking toward the dock with the neighbour at +37.3 mm: chute gap (blue, 2.79 mm) and the new side "
             f"limit, P01 to the neighbour's body (red, {limit[0]:.2f} mm)", zoom=1.25),
    ]
    out = ROOT / "images" / "66_chute_chamfer_r36_before_after.png"
    sheet(panels, 2, SIZE, out)
    print(out, {k: round(v[0], 3) for k, v in pair.items()}, round(limit[0], 3), f"y={y:.2f}",
          "limit points", [round(v, 2) for v in limit[3]], [round(v, 2) for v in limit[4]])


if __name__ == "__main__":
    main()
