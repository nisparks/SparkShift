"""Unbranded CAD views, plan section and measured data for the flow-neutral C28 user-post retainer (v5d).

Run audit_c28_flow_neutral_retainer_r43.py, the motion and slicing audits with --variant flow-neutral,
cfd_direct_mount_r43.py --user-retainer and --flow-neutral v5d first. Numbers are read from those reports.
"""
import io
import json

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from PIL import Image, ImageDraw

import r43_c28_mechanical as M
import r43_c28_user_joint as U
import render_r43_public_comparison as V
from audit_c28_mechanical_r43 import ROOT, SOURCE
from audit_c28_flow_neutral_retainer_r43 import OUTPUT
from audit_c28_user_retainer_r43 import USER_STEP
from render_c28_mechanical_r43 import COLORS, render

ADDED = {"p21": (1.0, .8, .28), "p22": (.45, .93, .82)}
PLAN_Z = -55.0
CLEAN, SEALED = "#8fa3b8", "#e0884a"


def report(name):
    path = ROOT / name
    return json.loads(path.read_text()) if path.exists() else None


def panels(parts, added, original_p21, cable):
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    hotend = cq.Shape.importBrep(str(SOURCE / dict(manifest["variants"]["Bambu"]["parts"])["hotend"]))
    hardware = M.hardware()
    metal = [(p, COLORS["brass" if "HEATSET" in n else "steel"]) for n, p in hardware]
    retainer_hw = [(p, COLORS["brass" if "HEATSET" in n else "steel"]) for n, p in hardware if "P21_P22" in n]

    cropped = M.box(-30, 30, -48, 34, -80, -40)
    items = [(p.intersect(cropped), COLORS[k]) for k, p in parts.items()]
    items += [(cable.intersect(cropped), COLORS["cable"]), (hotend, (.62, .65, .68))] + metal
    render(items, (0, -7, -59), (1, -.9, .35), 34, OUTPUT / "flow_neutral_assembly.png")

    local = M.box(-10, 10, -43, -17, -74, -44)
    joint = [(parts["p21"].intersect(local), COLORS["p21"]), (parts["p22"].intersect(local), COLORS["p22"]),
             (cable.intersect(local), COLORS["cable"])] + retainer_hw
    render(joint, (0, -30.5, -58.5), (1, .15, .12), 17.5, OUTPUT / "flow_neutral_section.png",
           M.box(-40, 0, -60, 40, -100, 0))

    post = [(original_p21.intersect(local), COLORS["p21"]),
            (added["p21"].intersect(local), ADDED["p21"]), (cable.intersect(local), COLORS["cable"])]
    post += [(p, COLORS["brass"]) for n, p in hardware if "P21_P22" in n and "HEATSET" in n]
    render(post, (0, -31, -56.5), (.75, -1, -.45), 15.5, OUTPUT / "flow_neutral_post.png")

    # Back wall and floor cropped away to look into the rear plenum at the skin and its faired keel.
    seat = M.box(-10, 10, -43.4, -15, -62, -48)
    receiver = [(parts["p22"].intersect(seat).cut(added["p22"]), COLORS["p22"]),
                (added["p22"].intersect(seat), ADDED["p22"]),
                (parts["p21"].intersect(M.box(-10, 10, -43.4, -15, -62, U.SEAL_Z)), COLORS["p21"]),
                (cable.intersect(seat), COLORS["cable"])]
    render(receiver, (0, -38.5, -55.5), (.5, -1, .5), 8.5, OUTPUT / "flow_neutral_receiver.png")


def plan_polys(shape, z=PLAN_Z):
    """Triangles of a solid's plan section at height z."""
    section = shape.intersect(M.box(-40, 40, -70, 60, z - .005, z + .005))
    tris = []
    for face in section.Faces():
        if abs(face.normalAt().z) > .99 and face.Center().z > z:
            vertices, triangles = face.tessellate(.01, .1)
            tris += [[(vertices[i].x, vertices[i].y) for i in t] for t in triangles]
    return tris


def plan_figure(parts, added, user_post, cable, clean_air):
    fig, ax = plt.subplots(figsize=(13, 9.2), dpi=100)
    fig.patch.set_facecolor("#112136")
    ax.set_facecolor("#112136")
    layers = [
        (clean_air, "#3c5f86", "clean C28 duct air"),
        (parts["p22"].cut(added["p22"]), "#1fa6c2", "P22 (unchanged)"),
        (added["p22"], "#73edd1", "P22 skin + 45\u00b0 keel (new)"),
        (parts["p21"], "#f08c2e", "P21 post as built"),
        (cable, "#c95fa3", "probe cable"),
    ]
    for shape, color, label in layers:
        tris = plan_polys(shape)
        ax.add_collection(PolyCollection(tris, facecolors=color, edgecolors=color, linewidths=.2, label=label))
    user_edges = user_post.intersect(M.box(-40, 40, -70, 60, PLAN_Z - .005, PLAN_Z + .005))
    for face in user_edges.Faces():
        if abs(face.normalAt().z) > .99 and face.Center().z > PLAN_Z:
            for edge in face.Edges():
                pts = [edge.positionAt(t) for t in [i / 24 for i in range(25)]]
                ax.plot([p.x for p in pts], [p.y for p in pts], color="#ff5a5a", lw=2.2, ls=(0, (4, 2)))
    ax.plot([], [], color="#ff5a5a", lw=2.2, ls=(0, (4, 2)), label="user post as drawn")
    ax.set_xlim(-9, 9)
    ax.set_ylim(-44, -27)
    ax.set_aspect("equal")
    ax.tick_params(colors="#c9d6e3", labelsize=13)
    for spine in ax.spines.values():
        spine.set_color("#5d7590")
    ax.set_xlabel("X (mm)", color="#c9d6e3", fontsize=14)
    ax.set_ylabel("Y (mm), rear down", color="#c9d6e3", fontsize=14)
    ax.legend(loc="upper right", fontsize=12, facecolor="#1b2f47", edgecolor="#5d7590", labelcolor="#e6eef6")
    ax.set_title(f"Plan section Z = {PLAN_Z:g} mm", color="#e6eef6", fontsize=17, loc="left")
    return to_image(fig)


def to_image(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", facecolor=fig.get_facecolor())
    plt.close(fig)
    buffer.seek(0)
    return Image.open(buffer).convert("RGB").resize((1300, 920), Image.Resampling.LANCZOS)


def metrics():
    geometry = report("verification_c28_flow_neutral_retainer_geometry_r43.json")
    sealed_geometry = report("verification_c28_user_retainer_geometry_r43.json")
    slicing = report("verification_c28_flow_neutral_retainer_slicing_r43.json")
    sealed_cfd = report("verification_user_retainer_cfd_r43.json")
    cfd = report("verification_flow_neutral_retainer_v5d_cfd_r43.json")
    back = slicing["comparisons"]["P22_back_down"]
    access = slicing["support_access"]
    rows = {
        "Duct air change (mm\u00b3)": {
            "v4 sealed": sealed_geometry["air_changes"]["duct_air_change_mm3"],
            "v5d": geometry["air_changes"]["duct_air_change_mm3"]},
        "P22 support, back down (mm\u00b3)": {
            "clean": back["original"]["support_deposition_volume_mm3"],
            "v4 sealed": back["sealed_user_post"]["support_deposition_volume_mm3"],
            "v5d": back["flow_neutral"]["support_deposition_volume_mm3"]},
        "Support in duct near post (mm\u00b3)": {
            "clean": access["channel_air_near_receiver_support_mm3"].get("original"),
            "v4 sealed": access["channel_air_near_receiver_support_mm3"]["sealed_user_post"],
            "v5d": access["channel_air_near_receiver_support_mm3"]["flow_neutral"]},
        "Post plan section, Z -51.6 (mm\u00b2)": {
            "v4 sealed": geometry["user_post_plan_section_mm2"]["-51.6"],
            "v5d": geometry["post_plan_section_mm2"]["-51.6"]},
    }
    for cases, change in ((sealed_cfd, "v4 sealed"), (cfd, "v5d")):
        if cases is None:
            continue
        pair = cases["comparison_by_tool"]["Bambu"]
        before, after = (cases["cases"][pair[k]] for k in ("before", "after"))
        weakest = lambda c: min(c["coverage_at_estimated_blower"]["sector_area_mean_speed_ms"].values())
        rows.setdefault("Duct pressure, 180 L/min (Pa)", {})["clean"] = before["inlet_pressure_pa_at_180"]
        rows["Duct pressure, 180 L/min (Pa)"][change] = after["inlet_pressure_pa_at_180"]
        rows.setdefault("Weakest near-print sector (m/s)", {})["clean"] = weakest(before)
        rows["Weakest near-print sector (m/s)"][change] = weakest(after)
    return rows


def chart_figure(rows):
    order = ["Duct pressure, 180 L/min (Pa)", "Weakest near-print sector (m/s)", "Duct air change (mm\u00b3)",
             "P22 support, back down (mm\u00b3)", "Support in duct near post (mm\u00b3)",
             "Post plan section, Z -51.6 (mm\u00b2)"]
    colors = {"clean": CLEAN, "v4 sealed": SEALED, "v5d": "#73edd1"}
    fig, axes = plt.subplots(2, 3, figsize=(13, 9.2), dpi=100)
    fig.patch.set_facecolor("#112136")
    for ax, title in zip(axes.ravel(), order):
        ax.set_facecolor("#112136")
        values = {k: v for k, v in rows.get(title, {}).items() if v is not None}
        labels = [k for k in ("clean", "v4 sealed", "v5d") if k in values]
        bars = ax.bar(labels, [values[k] for k in labels], color=[colors[k] for k in labels], width=.62)
        for bar, k in zip(bars, labels):
            v = values[k]
            text = f"{v:,.0f}" if abs(v) >= 100 else f"{v:,.1f}"
            ax.annotate(text, (bar.get_x() + bar.get_width() / 2, v), ha="center",
                        va="bottom" if v >= 0 else "top", color="#e6eef6", fontsize=12,
                        xytext=(0, 4 if v >= 0 else -4), textcoords="offset points")
        low, high = min(0, *values.values()), max(0, *values.values())
        pad = .18 * (high - low or 1)
        ax.set_ylim(low - (pad if low < 0 else 0), high + pad)
        ax.set_title(title, color="#e6eef6", fontsize=13)
        ax.tick_params(colors="#c9d6e3", labelsize=11)
        for spine in ax.spines.values():
            spine.set_color("#5d7590")
        ax.axhline(0, color="#5d7590", lw=.8)
    fig.tight_layout(pad=1.4)
    return to_image(fig)


def data_lines():
    geometry = report("verification_c28_flow_neutral_retainer_geometry_r43.json")
    motion = report("verification_c28_flow_neutral_retainer_motion_r43.json")
    slicing = report("verification_c28_flow_neutral_retainer_slicing_r43.json")
    cfd = report("verification_flow_neutral_retainer_v5d_cfd_r43.json")
    air = geometry["air_changes"]
    lines = [("DUCT", f"Sealed. Air {air['duct_air_change_mm3']:+.0f} mm3 "
                      f"({100 * air['duct_air_change_mm3'] / air['duct_cavity_baseline_mm3']:+.2f}%): skin under the "
                      f"P21 boss wake + {air['p22_skin_keel_beyond_boss_wake_mm3']:.0f} mm3 faired 45\u00b0 keel.")]
    if motion:
        sampled = min(r["minimum_sample"]["mm"] for r in motion["paths"])
        lines.append(("FIT / MOTION", f"Cable gap {geometry['parts']['p21']['new_material_cable_gap_mm']:.2f} mm; "
                                      f"{len(motion['paths'])} motion paths clear (>= {sampled:.2f} mm sampled); "
                                      f"P22 drops {geometry['lower_duct_service']['downward_release_mm']} mm."))
    if slicing:
        t = slicing["three_separate_parts_total"]["flow_neutral_vs_original_pct"]
        a = slicing["support_access"]
        lines.append(("PRINT", f"Set support {t['support_deposition_volume_mm3']:+.1f}%, time "
                               f"{t['total_estimated_time_s']:+.1f}% vs original; socket "
                               f"{a['receiver_socket_support_mm3']['flow_neutral']:.1f} mm3, rear passage "
                               f"{a['rear_passage_support_mm3']:.0f} mm3."))
    if cfd:
        change = cfd["comparison_by_tool"]["Bambu"]
        lines.append(("CFD 180 L/MIN", f"Pressure {change['pressure_pct']:+.1f}%, rear branch "
                                       f"{change['rear_branch_flow_pct']:+.1f}%, weakest sector "
                                       f"{change['weakest_sector_speed_pct']:+.1f}% vs clean C28."))
    return lines


def main():
    parts = {k: cq.Shape.importBrep(str(OUTPUT / f"{k}.brep")) for k in ("p01", "p21", "p22")}
    added = {k: cq.Shape.importBrep(str(OUTPUT / f"{k}_added.brep")) for k in ("p21", "p22")}
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    read = lambda prefix: cq.Shape.importBrep(str(SOURCE / next(p for n, p in manifest["carriage"]
                                                               if n.startswith(prefix))))
    original_p21, cable = read("P21_"), read("Probe_Cable")
    user, _ = U.load_user_p21(USER_STEP)
    clean_air = cq.Shape.importBrep(str(OUTPUT / "clean_duct_air.brep"))
    panels(parts, added, original_p21, cable)
    plan = plan_figure(parts, added, user.cut(original_p21), cable, clean_air)
    chart = chart_figure(metrics())

    sheet = Image.new("RGB", (2800, 3800), V.BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((65, 35), "FLOW-NEUTRAL USER POST (v5d)", fill=V.TEXT, font=V.font(62, True))
    draw.text((65, 125), "Bambu / C28. Orange: mid duct (gold = post). Teal: lower duct (mint = skin + keel). "
                         "Pink: cable.", fill=V.MUTED, font=V.font(34))
    tiles = [
        ("ASSEMBLED / ORIGINAL DATUMS", Image.open(OUTPUT / "flow_neutral_assembly.png")),
        ("POST IN SOCKET / CENTRE CUT, M3 FROM BELOW", Image.open(OUTPUT / "flow_neutral_section.png")),
        ("USER POST, TRIMMED TO THE SPINE", Image.open(OUTPUT / "flow_neutral_post.png")),
        ("P22 SKIN + FAIRED 45\u00b0 KEEL (BACK WALL CUT AWAY)", Image.open(OUTPUT / "flow_neutral_receiver.png")),
        ("WHERE THE POST SITS IN THE AIRWAY", plan),
        ("CLEAN C28 / SEALED v4 / FLOW-NEUTRAL v5d", chart),
    ]
    for i, (title, image) in enumerate(tiles):
        x, y = 65 + (i % 2) * 1380, 230 + (i // 2) * 1040
        draw.text((x, y), title, fill=V.TEXT, font=V.font(37, True))
        sheet.paste(image, (x, y + 60))
    y = 230 + 3 * 1040 + 20
    for label, text in data_lines():
        draw.text((65, y), label, fill=V.TEXT, font=V.font(32, True))
        draw.text((470, y), text, fill=V.MUTED, font=V.font(30))
        y += 82
    png = ROOT / "images" / "r43_c28_flow_neutral_retainer_review.png"
    jpg = ROOT / "images" / "r43_c28_flow_neutral_retainer_review_share.jpg"
    sheet = sheet.crop((0, 0, sheet.width, min(sheet.height, y + 40)))
    sheet.save(png, optimize=True)
    sheet.resize((1920, round(sheet.height * 1920 / sheet.width)), Image.Resampling.LANCZOS).save(
        jpg, quality=93, subsampling=0)
    print(png, jpg, sep="\n")


if __name__ == "__main__":
    main()
