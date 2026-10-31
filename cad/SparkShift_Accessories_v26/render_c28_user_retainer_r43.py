"""Unbranded CAD cutaways and measured data for the C28 user-post retainer review.

Run audit_c28_user_retainer_r43.py, its motion and slicing audits, and (optionally)
cfd_direct_mount_r43.py --user-retainer first. Numbers are read from those reports.
"""
import json

import cadquery as cq
from PIL import Image, ImageDraw

import r43_c28_mechanical as M
import render_r43_public_comparison as V
from audit_c28_mechanical_r43 import ROOT, SOURCE
from audit_c28_user_retainer_r43 import OUTPUT
from render_c28_mechanical_r43 import COLORS, render

ADDED = {"p21": (1.0, .8, .28), "p22": (.45, .93, .82)}


def report(name):
    path = ROOT / name
    return json.loads(path.read_text()) if path.exists() else None


def panels():
    parts = {k: cq.Shape.importBrep(str(OUTPUT / f"{k}.brep")) for k in ("p01", "p21", "p22")}
    added = {k: cq.Shape.importBrep(str(OUTPUT / f"{k}_added.brep")) for k in ("p21", "p22")}
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    cable = cq.Shape.importBrep(str(SOURCE / next(p for n, p in manifest["carriage"] if n.startswith("Probe_Cable"))))
    hotend = cq.Shape.importBrep(str(SOURCE / dict(manifest["variants"]["Bambu"]["parts"])["hotend"]))
    hardware = M.hardware()
    metal = [(p, COLORS["brass" if "HEATSET" in n else "steel"]) for n, p in hardware]
    retainer_hw = [(p, COLORS["brass" if "HEATSET" in n else "steel"]) for n, p in hardware if "P21_P22" in n]

    cropped = M.box(-30, 30, -48, 34, -80, -40)
    items = [(p.intersect(cropped), COLORS[k]) for k, p in parts.items()]
    items += [(cable.intersect(cropped), COLORS["cable"]), (hotend, (.62, .65, .68))] + metal
    render(items, (0, -7, -59), (1, -.9, .35), 34, OUTPUT / "user_assembly.png")

    local = M.box(-10, 10, -43, -17, -74, -44)
    joint = [(parts["p21"].intersect(local), COLORS["p21"]), (parts["p22"].intersect(local), COLORS["p22"]),
             (cable.intersect(local), COLORS["cable"])] + retainer_hw
    render(joint, (0, -30.5, -58.5), (1, .15, .12), 17.5, OUTPUT / "user_retainer_section.png",
           M.box(-40, 0, -60, 40, -100, 0))

    original_p21 = cq.Shape.importBrep(str(SOURCE / next(p for n, p in manifest["carriage"] if n.startswith("P21_"))))
    post = [(original_p21.intersect(local), COLORS["p21"]),
            (added["p21"].intersect(local), ADDED["p21"]), (cable.intersect(local), COLORS["cable"])]
    post += [(p, COLORS["brass"]) for n, p in hardware if "P21_P22" in n and "HEATSET" in n]
    render(post, (0, -31, -56.5), (.75, -1, -.45), 15.5, OUTPUT / "user_post.png")

    seat = M.box(-14, 14, -46, -15, -74, -48)
    receiver = [(parts["p22"].intersect(seat).cut(added["p22"]), COLORS["p22"]),
                (added["p22"].intersect(seat), ADDED["p22"])]
    render(receiver, (0, -30, -60), (.55, -.75, .95), 17, OUTPUT / "user_receiver.png")


def data_lines():
    geometry = report("verification_c28_user_retainer_geometry_r43.json")
    motion = report("verification_c28_user_retainer_motion_r43.json")
    slicing = report("verification_c28_user_retainer_slicing_r43.json")
    cfd = report("verification_user_retainer_cfd_r43.json")
    air = geometry["air_changes"]
    channel = air["new_material_in_clean_c28_channel_mm3"]
    lines = [
        ("DUCT SEAL", f"Closed. Duct air {air['duct_air_change_mm3']:+.0f} mm3 "
                      f"({100 * air['duct_air_change_mm3'] / air['duct_cavity_baseline_mm3']:+.1f}%); post + receiver "
                      f"take {channel['p21']:.0f} + {channel['p22']:.0f} mm3 of the clean C28 channel."),
        ("FIT", f"Cable gap: post {geometry['parts']['p21']['new_material_cable_gap_mm']:.2f} mm, receiver "
                f"{geometry['parts']['p22']['new_material_cable_gap_mm']:.2f} mm. P22 drops "
                f"{geometry['lower_duct_service']['downward_release_mm']} mm for service; P21 + EBB42 stay."),
    ]
    if motion:
        gantry = min(r["continuous_clearance_lower_bound_mm"] for r in motion["paths"])
        lines.append(("MOTION", f"{len(motion['paths'])} real-scene paths clear; smallest certified clearance "
                                f"{gantry:.2f} mm (rigid nominal CAD)."))
    if slicing:
        c = slicing["comparisons"]
        t = slicing["three_separate_parts_total"]["user_post_vs_original_pct"]
        lines.append(("PRINT", f"Support vs original C28: P21 "
                               f"{c['P21_top_down']['user_post_vs_original_pct']['support_deposition_volume_mm3']:+.0f}%, P22 "
                               f"{c['P22_back_down']['user_post_vs_original_pct']['support_deposition_volume_mm3']:+.1f}%, "
                               f"set {t['support_deposition_volume_mm3']:+.1f}%, time {t['total_estimated_time_s']:+.1f}%. "
                               f"Rear passage: {slicing['support_access']['rear_passage_support_mm3']:.0f} mm3."))
    if cfd:
        change = cfd["comparison_by_tool"]["Bambu"]
        speeds = change["mean_speed_pct"]
        lines.append(("CFD 180 L/MIN", f"Inlet pressure {change['pressure_pct']:+.1f}%, rear branch "
                                       f"{change['rear_branch_flow_pct']:+.1f}%, weakest near-print sector "
                                       f"{change['weakest_sector_speed_pct']:+.1f}%, mean speed r5 "
                                       f"{speeds.get('r5_mm', float('nan')):+.1f}%."))
    else:
        lines.append(("CFD", "Pending."))
    return lines


def main():
    panels()
    sheet = Image.new("RGB", (2800, 2900), V.BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((65, 35), "USER POST + MATCHED RECEIVER", fill=V.TEXT, font=V.font(62, True))
    draw.text((65, 125), "Bambu / C28. Orange: mid duct (gold = post + skirt). Teal: lower duct (mint = receiver). "
                         "Pink: cable.", fill=V.MUTED, font=V.font(34))
    tiles = [
        ("ASSEMBLED / ORIGINAL DATUMS", "user_assembly.png"),
        ("POST IN RECEIVER / CENTRE CUT, M3 FROM BELOW", "user_retainer_section.png"),
        ("USER POST + 45-DEGREE SEAL SKIRT", "user_post.png"),
        ("RECEIVER: OPEN FRONT, SLOT DAM, REAR KEEL", "user_receiver.png"),
    ]
    for i, (title, filename) in enumerate(tiles):
        x, y = 65 + (i % 2) * 1380, 230 + (i // 2) * 1060
        draw.text((x, y), title, fill=V.TEXT, font=V.font(37, True))
        sheet.paste(Image.open(OUTPUT / filename), (x, y + 60))
    y = 2370
    for label, text in data_lines():
        draw.text((65, y), label, fill=V.TEXT, font=V.font(32, True))
        draw.text((420, y), text, fill=V.MUTED, font=V.font(30))
        y += 82
    png = ROOT / "images" / "r43_c28_user_retainer_review.png"
    jpg = ROOT / "images" / "r43_c28_user_retainer_review_share.jpg"
    sheet = sheet.crop((0, 0, sheet.width, min(sheet.height, y + 40)))
    sheet.save(png, optimize=True)
    sheet.resize((1920, round(sheet.height * 1920 / sheet.width)), Image.Resampling.LANCZOS).save(
        jpg, quality=93, subsampling=0)
    print(png, jpg, sep="\n")


if __name__ == "__main__":
    main()
