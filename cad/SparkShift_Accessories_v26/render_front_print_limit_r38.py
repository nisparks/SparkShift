"""Revision 38 review image and world-frame review assembly: the front print limit from exact 3D contact."""

import argparse
import json
import os
import re

import build_and_verify_accessories_v26 as acc

os.environ.setdefault("SPARKSHIFT_SCENE", str(acc.WORK / "r37_scene"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
from audit_bed_front_edge_r34 import BED_FRONT_Y, beds, source_bed  # noqa: E402
from audit_front_print_limit_r38 import REPORT  # noqa: E402
from audit_tool_owned_2510 import compound  # noqa: E402
from build_modular_toolhead import ROOT, box, primitives  # noqa: E402
from render_accessories_v26 import make_actor, render_view, shape_to_polydata  # noqa: E402
from render_bambu_clean_r29 import TMP, sheet  # noqa: E402

DOCK, TOOL, ACTIVE, RIG = (0.75, 0.2, 0.7), (0.95, 0.67, 0.1), (0.2, 0.55, 0.9), (0.55, 0.6, 0.68)
BED, AREA, GAIN, OLD, NEW = (0.62, 0.62, 0.62), (0.55, 0.72, 0.95), (0.1, 0.8, 0.25), (1.0, 0.45, 0.0), (0.1, 0.6, 0.2)
SIZE = (900, 760)
TIP_LOCAL_Z = -78.8794
REVIEW = "38_Front_Print_Limit_REVIEW"


def clipped(shape, clip):
    """Clip solid by solid: Booleans on compounds of overlapping solids can come back empty."""
    out = []
    for s in shape.Solids():
        a, b = s.BoundingBox(), clip.BoundingBox()
        if a.xmax < b.xmin or a.xmin > b.xmax or a.ymax < b.ymin or a.ymin > b.ymax or a.zmax < b.zmin or a.zmin > b.zmax:
            continue
        inside = (a.xmin >= b.xmin and a.xmax <= b.xmax and a.ymin >= b.ymin and a.ymax <= b.ymax
                  and a.zmin >= b.zmin and a.zmax <= b.zmax)
        part = s if inside else s.intersect(clip)
        if not part.isNull() and part.Solids():
            out += list(part.Solids())
    return compound(out) if out else None


def panel(items, clip, eye, target, up, title, zoom=1.0):
    actors = []
    for shape, color, opacity in items:
        part = clipped(shape, clip)
        if part is not None:
            actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, opacity, edge_vis=opacity > 0.99))
    path = primitives.WORK / "front_print_limit_r38_panel.png"
    render_view(actors, eye, target, up, path, width=SIZE[0], height=SIZE[1], zoom=zoom, depth_peeling=True)
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(title.split("\n")):
        draw.text((12, 12 + 16 * i), line, fill=(10, 10, 10))
    path.unlink()
    return image


def chart(report):
    old, new = report["revision_34_front_print_limit_nozzle_y_mm"], report["front_print_limit_nozzle_y_mm"]
    worst = report["worst_first_contact"]["first_contact_nozzle_y_mm"]
    fig, ax = plt.subplots(figsize=(SIZE[0] / 100, SIZE[1] / 100), dpi=100)
    ax.axhspan(new, 72, color=(0.85, 0.93, 1.0), zorder=0)
    ax.axhspan(new, old, color=(0.8, 0.95, 0.8), zorder=1)
    for label, style in (("Bambu", "-"), ("RedLizard", "--")):
        rows = sorted((r["x_mm"], r["y_mm"]) for r in report["profile"] if r["active"] == label and r["y_mm"])
        ax.plot([x for x, _ in rows], [y for _, y in rows], style, color=(0.75, 0.1, 0.1) if label == "Bambu"
                else (0.3, 0.3, 0.3), lw=1.4, label=f"First contact, {label} active", zorder=3)
    ax.axhline(old, color=OLD, lw=2.0, ls=":", label=f"Revision 34 limit Y{old:.2f} (whole envelope)")
    ax.axhline(new, color=NEW, lw=2.2, label=f"Revision 38 limit Y{new:.2f} (worst contact + 1 mm)")
    for x in r36.CENTERS:
        ax.axvline(x, color=(0.6, 0.6, 0.6), lw=0.6, zorder=2)
    ax.text(r36.CENTERS[4] + 0.6, 45.6, "bay centres", fontsize=8, color=(0.4, 0.4, 0.4))
    ax.text(178, (new + old) / 2 - 0.4, f"gained {old - new:.2f} mm across the full width", fontsize=10,
            color=(0.05, 0.4, 0.1), ha="center")
    ax.text(178, 70.2, "printable", fontsize=10, color=(0.15, 0.3, 0.6), ha="center")
    ax.set_xlim(0, 350)
    ax.set_ylim(44, 72)
    ax.set_xlabel("Nozzle X (mm)")
    ax.set_ylabel("Nozzle Y (mm, world CAD)")
    ax.set_title(f"First contact with the parked rack at every nozzle X (worst Y{worst:.2f}): coupling pins/magnets\n"
                 f"peak 4-7 mm either side of each bay centre, P18 dock plate elsewhere (Y~47.25)", fontsize=10)
    ax.legend(loc="lower right", fontsize=8)
    fig.tight_layout()
    path = primitives.WORK / "front_print_limit_r38_chart.png"
    fig.savefig(path)
    plt.close(fig)
    image = Image.open(path).convert("RGB").resize(SIZE)
    path.unlink()
    return image


def export_review(s, report, show_x, bay, dz, bed_a):
    """World-frame review: bed A, the binding parked Bambu with Red Lizard neighbours, the active Bambu on the
    revision-37 carriage at the worst-case X on the new limit, and both limit lines on the bed."""
    from build_fan_mounts_r33 import export_assembly
    from build_refined_docking_review import DOCK_NAMES
    f = s["frames"]
    old, new = report["revision_34_front_print_limit_nozzle_y_mm"], report["front_print_limit_nozzle_y_mm"]
    items = [(bed_a, "Bed_A_Y40_to_359", (0.55, 0.55, 0.58)),
             (box(0, 350, old - 1.0, old + 1.0, 0.0, 0.3), "Front_limit_R34_whole_envelope", OLD),
             (box(0, 350, new - 1.0, new + 1.0, 0.0, 0.3), "Front_limit_R38_exact_contact", NEW)]
    for i in (bay - 1, bay, bay + 1):
        label = "Bambu" if i == bay else "RedLizard"
        v = s["variants"][label]
        items += [(r36.world(p, r36.CENTERS[i], f).translate((0, 0, dz)), f"T{i}_{label}_{n.replace(' ', '_')}",
                   TOOL if n == "body" else (0.62, 0.62, 0.65)) for n, p in v["parts"]]
        items += [(r36.world(d, r36.CENTERS[i], f).translate((0, 0, dz)), f"T{i}_Dock_{n}", DOCK)
                  for n, d in zip(DOCK_NAMES, v["dock_solids"])]
    move = (0, new - report["dock_nozzle_y_mm"], dz)
    items += [(r36.world(p, show_x, f).translate(move), f"Active_Bambu_{n.replace(' ', '_')}",
               ACTIVE if n == "body" else (0.45, 0.6, 0.85)) for n, p in s["variants"]["Bambu"]["parts"]]
    items += [(r36.world(p, show_x, f).translate(move), f"Carriage_{n}", RIG) for n, p in s["carriage_parts"]]
    path = export_assembly(REVIEW, items, sum(len(p.Solids()) for p, _, _ in items))
    print(path, sum(len(p.Solids()) for p, _, _ in items), "solids")
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--review", action=argparse.BooleanOptionalAction, default=True)
    args = parser.parse_args()
    report = json.loads((ROOT / REPORT).read_text())
    s = r36.scene()
    f = s["frames"]
    dock_y = report["dock_nozzle_y_mm"]
    old, new = report["revision_34_front_print_limit_nozzle_y_mm"], report["front_print_limit_nozzle_y_mm"]
    worst = report["by_active_tool"]["Bambu"]["worst"]
    contact = report["by_active_tool"]["Bambu"]["contact_at_worst"]
    dz = 0.2 - (f["world_z_offset_mm"] + TIP_LOCAL_Z)
    bed_a = beds(source_bed()[0])["front_edge_cut"]
    # The profile repeats every bay: show the worst case on the bay nearest mid-bed, with the active tool's own bay
    # (left empty in the rack) away from it.
    pitch = r36.CENTERS[1] - r36.CENTERS[0]
    k = round((175.0 - worst["x_mm"]) / pitch)
    show_x = worst["x_mm"] + k * pitch
    bay = int(re.search(r"parked T(\d)", contact["fixed"]).group(1)) + k
    if args.review:
        export_review(s, report, show_x, bay, dz, bed_a)
    if not args.image:
        return
    empty = 8
    parked = []
    for i, center in enumerate(r36.CENTERS):
        v = s["variants"]["Bambu" if i % 2 == 0 else "RedLizard"]
        parked.append((r36.world(v["dock"], center, f).translate((0, 0, dz)), DOCK, 1.0))
        if i != empty:
            parked.append((r36.world(v["tool"], center, f).translate((0, 0, dz)), TOOL, 1.0))
    bambu = s["variants"]["Bambu"]

    def active(x, nozzle_y, z=dz):
        move = (0, nozzle_y - dock_y, z)
        return [(r36.world(bambu["tool"], x, f).translate(move), ACTIVE, 1.0),
                (r36.world(s["carriage"], x, f).translate(move), RIG, 1.0)]

    top_clip = box(-25, 375, -45, 150, -30, 260)
    eye, target = (175, 52, 1200), (175, 52, 0)
    area_old = (box(0, 350, old, 150, 0.0, 0.4), AREA, 0.45)
    area_new = [(box(0, 350, new, old, 0.0, 0.4), GAIN, 0.75), area_old]
    line_old = (box(0, 350, old - 1.0, old + 1.0, 0.4, 1.4), OLD, 1.0)
    line_new = (box(0, 350, new - 1.0, new + 1.0, 0.4, 1.4), NEW, 1.0)
    old_d, new_d = report["print_depth_revision_34"], report["print_depth"]
    panels = [
        panel(parked + active(show_x, old) + [(bed_a, BED, 0.35), area_old, line_old], top_clip, eye, target,
              (0, 1, 0),
              f"Revision 34 (before): whole-envelope rule, front print limit nozzle Y{old:.2f} (orange line).\n"
              f"Print depth {old_d['A_bed_Y40_to_359']['depth_mm']:.1f} mm (bed A) / "
              f"{old_d['B_stock_bed_moved_back']['depth_mm']:.1f} mm (bed B). Bed front edge Y{BED_FRONT_Y:g}; "
              f"bay T{empty} is the active tool's.", zoom=1.3),
        panel(parked + active(show_x, new) + [(bed_a, BED, 0.35), line_old, line_new] + area_new, top_clip,
              eye, target, (0, 1, 0),
              f"Revision 38 (after): exact 3D contact, front print limit nozzle Y{new:.2f} (green line), gained "
              f"strip in green.\nActive tool at a worst-case X{show_x:g}. Print depth "
              f"{new_d['A_bed_Y40_to_359']['depth_mm']:.1f} / {new_d['B_stock_bed_moved_back']['depth_mm']:.1f} mm. "
              "No part changes.", zoom=1.3),
        chart(report),
    ]
    px, py, pz = contact["fixed_point_world_mm"]
    px += k * pitch
    first = worst["first_contact_nozzle_y_mm"]
    v = s["variants"]["RedLizard" if "RedLizard" in contact["fixed"] else "Bambu"]
    near = [(r36.world(v["dock"], r36.CENTERS[bay], f), DOCK, 1.0), (r36.world(v["tool"], r36.CENTERS[bay], f), TOOL, 1.0)]
    near += [(r36.world(bambu["tool"], show_x, f).translate((0, new - dock_y, 0)), ACTIVE, 1.0),
             (r36.world(s["carriage"], show_x, f).translate((0, new - dock_y, 0)), RIG, 1.0),
             (box(px - 6, px + 6, py + 0.25, py + 0.75, pz - 4, pz + 4), (0.9, 0.05, 0.05), 1.0)]
    clip = box(px - 6, px + 6, py - 60, py + 45, pz - 70, pz + 40)
    gap = report["by_active_tool"]["Bambu"]["clearance_at_print_limit"]["mm"]
    panels.append(panel(near, clip, (px + 600, py - 7, pz - 15), (px, py - 7, pz - 15), (0, 0, 1),
                        f"Section X{px - 6:.1f}..{px + 6:.1f} at the print limit: the active tool's front coupling pin "
                        f"(blue) is {gap:.2f} mm\nfrom the parked T{bay} body (yellow), red marker in the gap; they "
                        f"touch at nozzle Y{first:.2f}. Dock purple, carriage grey.", zoom=1.0))
    out = ROOT / "images" / "71_front_print_limit_r38_before_after.png"
    sheet(panels, 2, SIZE, out)
    print(out)


if __name__ == "__main__":
    main()
