"""Revision 34 review image: the rigid dock rack at first-layer height, before and after the bed change."""

import json

import cadquery as cq
from PIL import Image, ImageDraw

from audit_bed_front_edge_r34 import BED_FRONT_Y, FIRST_BAY_X, NOZZLE_LOCAL_Y, PITCH, REPORT, SHIFT, beds, frames, \
    source_bed, z_shift
from audit_low_z_bed_clearance import load_parked_variants
from audit_ten_tool_rack import world
from audit_tool_owned_2510 import compound
from build_fan_mounts_r33 import carriage
from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet

DOCK, TOOL, ACTIVE, GANTRY, RACK = ((0.75, 0.2, 0.7), (0.95, 0.67, 0.1), (0.2, 0.55, 0.9), (0.55, 0.6, 0.68),
                                    (0.25, 0.25, 0.28))
OLD_BED, NEW_BED, HIT, LIMIT = (0.9, 0.25, 0.2), (0.3, 0.75, 0.35), (0.85, 0.05, 0.05), (1.0, 0.45, 0.0)
SIZE = (900, 760)


def inside(shape, clip):
    a, b = shape.BoundingBox(), clip.BoundingBox()
    return (a.xmin >= b.xmin and a.xmax <= b.xmax and a.ymin >= b.ymin and a.ymax <= b.ymax
            and a.zmin >= b.zmin and a.zmax <= b.zmax)


def panel(items, clip, eye, target, up, title, zoom=1.0, peel=False):
    actors = []
    for shape, color, opacity in items:
        # Clipping a shape that already lies inside the box is an expensive no-op.
        part = shape if clip is None or inside(shape, clip) else shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, opacity, edge_vis=opacity > 0.99))
    path = primitives.WORK / "bed_front_edge_r34_panel.png"
    render_view(actors, eye, target, up, path, width=SIZE[0], height=SIZE[1], zoom=zoom, depth_peeling=peel)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((12, 12), title, fill=(10, 10, 10))
    path.unlink()
    return image


def main():
    report = json.loads((ROOT / REPORT).read_text())
    f = frames()
    variants = load_parked_variants()
    bed, _ = source_bed()
    options = beds(bed)
    dz = z_shift(variants["Bambu"], f, 0.2)
    bambu = variants["Bambu"]
    bay4 = FIRST_BAY_X + 4 * PITCH
    dock4 = world(bambu["dock"], bay4, f).translate((0, 0, dz))
    tool4 = world(bambu["tool"], bay4, f).translate((0, 0, dz))
    gap = report["print_area_and_probe"]["parked_to_bed_edge_y_gap_mm"]
    front = report["print_area_and_probe"]["front_print_limit_nozzle_y_mm"]
    side_clip = box(bay4 - 19, bay4 + 19, -45, 95, -22, 125)
    side_eye, side_target = (bay4 + 600, 25, 45), (bay4, 25, 45)
    collision = compound([s for s in (dock4.intersect(options["original"]), tool4.intersect(options["original"]))
                          if not s.isNull() and s.Solids()])
    panels = [
        panel([(dock4, DOCK, 1.0), (tool4, TOOL, 1.0), (options["original"], OLD_BED, 0.35), (collision, HIT, 1.0)],
              side_clip, side_eye, side_target, (0, 0, 1),
              "Revision 22: rigid rack at first-layer height (nozzle Z0.2), bed front edge at Y9: chute, pad and wiper "
              "buried in the bed", zoom=1.25, peel=True),
        panel([(dock4, DOCK, 1.0), (tool4, TOOL, 1.0), (options["front_edge_cut"], NEW_BED, 0.6)],
              side_clip, side_eye, side_target, (0, 0, 1),
              f"Revision 34: same rigid rack, bed front edge at Y{BED_FRONT_Y:g}: {gap:.2f} mm clear in Y at any "
              "gantry height", zoom=1.25, peel=True),
    ]
    parked = []
    for bay in range(10):
        x = FIRST_BAY_X + PITCH * bay
        v = variants["Bambu" if bay % 2 == 0 else "RedLizard"]
        parked += [(world(v["dock"], x, f).translate((0, 0, dz)), DOCK, 1.0)]
        if bay != 5:
            parked += [(world(v["tool"], x, f).translate((0, 0, dz)), TOOL, 1.0)]
    rig = compound([s for _, s in carriage()])
    to_front = front - (f["world_y_offset_mm"] - NOZZLE_LOCAL_Y)
    active = [(world(bambu["tool"], 175.0, f).translate((0, to_front, dz)), ACTIVE, 1.0),
              (world(rig, 175.0, f).translate((0, to_front, dz)), GANTRY, 1.0)]
    limit = (box(0, 350, front - 0.5, front + 0.5, 0.2, 1.2), LIMIT, 1.0)
    panels.append(panel(parked + active + [(options["original"], OLD_BED, 0.25), (options["front_edge_cut"], NEW_BED, 0.55),
                                           limit],
                        box(-70, 420, -45, 140, -30, 260), (175, 45, 1200), (175, 45, 0), (0, 1, 0),
                        f"Top view: old bed edge Y9 (red), required edge Y{BED_FRONT_Y:g} (green), front print limit "
                        f"nozzle Y{front:.2f} (orange): print area unchanged", zoom=1.0, peel=True))
    flying = cq.importers.importStep(str(primitives.WORK / "rack_audit_Flying_Gantry_world.step")).val()
    # Structural gantry bodies only: the overview does not need every screw, bearing and pulley.
    flying = compound([s for s in flying.Solids() if s.Volume() > 1500.0])
    crossbar = cq.importers.importStep(str(primitives.WORK / "rack_audit_crossbar_world.step")).val()
    square = [(flying.translate((0, 0, dz)), GANTRY, 1.0), (crossbar.translate((0, 0, dz)), RACK, 1.0)]
    square += [(load(n).translate((0, 0, dz)), (0.95, 0.55, 0.12), 1.0) for n in (
        "P29_Dock_Rack_Gantry_Mount_L", "P29_Dock_Rack_Gantry_Mount_R", "P30_Dock_Side_Spacer_L", "P30_Dock_Side_Spacer_R")]
    panels.append(panel(square + parked + [(options["shifted_back"], NEW_BED, 0.85)],
                        box(-90, 440, -45, 480, -30, 140), (-150, -380, 760), (175, 190, 0), (0, 0, 1),
                        f"Rigid square: crossbar closes the gantry U. Option B: stock bed moved back {SHIFT:g} mm "
                        f"(Y{BED_FRONT_Y:g}..{359 + SHIFT:g})", zoom=1.15, peel=True))
    out = ROOT / "images" / "63_bed_front_edge_r34_before_after.png"
    sheet(panels, 2, SIZE, out)
    print(out)


if __name__ == "__main__":
    main()
