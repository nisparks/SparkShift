import gc
import hashlib
import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
from PIL import Image, ImageDraw
import cfd_cpap_r41_post as P
import render_r43_public_comparison as V

S = V.S
out = S / "swept_feed" / "optC28_clean"
source = CAD / "verification_direct_aim_cfd_r43.json"
report = json.loads(source.read_text())
names = ("r43directAq_bambu_bed", "r43directC28q_bambu_bed")
old, new = (report["cases"][name] for name in names)
assert all(row["mesh"]["mesh_ok"] for row in (old, new))
assert report["comparison_by_tool"]["Bambu"]["controls"]["matched_refinement"]

fig, axes = plt.subplots(1, 2, figsize=(14.6, 5.4))
fig.patch.set_facecolor(V.PANEL)
fig.subplots_adjust(left=.06, right=.88, bottom=.14, top=.9, wspace=.27)
for ax, name, title in zip(axes, names, ("32 deg / earlier aim", "28 deg / selected study aim")):
    grid = P.internal(name, 1200)
    limits = (-14, 14, 8.7, 36.7)
    _, _, speed, _, _ = V.sample_map(grid, "z", -78.78, limits, nx=380)
    ax.set_facecolor("#a9b5c3")
    field = ax.imshow(speed, origin="lower", extent=limits, cmap="turbo", vmin=0, vmax=65)
    ax.plot(0, 22.7, "w+", ms=9, mew=1.6)
    ax.add_patch(Circle((0, 22.7), 5, fill=False, edgecolor="white", linewidth=1.2, linestyle="--"))
    ax.set_title(title, color=V.TEXT, fontsize=18, pad=12)
    ax.set_xlabel("X (mm)", color=V.MUTED, fontsize=14)
    ax.set_ylabel("Y (mm)", color=V.MUTED, fontsize=14)
    ax.tick_params(colors=V.MUTED, labelsize=13)
    for spine in ax.spines.values():
        spine.set_edgecolor(V.MUTED)
    del grid
    gc.collect()
bar = fig.colorbar(field, cax=fig.add_axes((.91, .18, .019, .67)), extend="max")
bar.set_label("Air speed (m/s) at 180 L/min", color=V.TEXT, fontsize=14)
bar.ax.tick_params(colors=V.TEXT, labelsize=12)
maps = out / "share_aim_maps.png"
fig.savefig(maps, dpi=150, facecolor=V.PANEL)
plt.close(fig)

image = Image.new("RGB", (2400, 3420), V.BG)
draw = ImageDraw.Draw(image)


def text(x, y, value, size=30, colour=V.TEXT, bold=False):
    draw.text((x, y), value, font=V.font(size, bold), fill=colour)


def asset(path, box, crop=None):
    pic = Image.open(path).convert("RGB")
    if crop:
        pic = pic.crop(crop)
    scale = min((box[2] - box[0]) / pic.width, (box[3] - box[1]) / pic.height)
    pic = pic.resize((round(pic.width * scale), round(pic.height * scale)), Image.Resampling.LANCZOS)
    pos = (box[0] + (box[2] - box[0] - pic.width) // 2,
           box[1] + (box[3] - box[1] - pic.height) // 2)
    image.paste(pic, pos)
    return pos, pic.size


text(70, 48, "SPARKSHIFT", 82, bold=True)
text(760, 83, "REAR-FEED CPAP / DESIGN REVIEW", 43, V.BLUE, True)
text(75, 167, "Bambu Lab toolhead  |  Direct-mount Beacon / Cartographer  |  Community feedback wanted", 31, V.MUTED)
draw.line((70, 245, 2330, 245), fill="#29415c", width=3)
text(70, 275, "01  THE DESIGN", 40, bold=True)
text(1610, 275, "INTERNAL CLEANUP", 35, bold=True)

hero = S / "swept_feed" / "optC28_conformal" / "aim_outlets_1.png"
pos, size = asset(hero, (70, 365, 1520, 1090), (760, 660, 2640, 1600))
landmarks = json.loads((V.ASSETS / "ports_candidate_a.json").read_text())
for key, label, x, colour in (("rear", "Curved rear slot", 110, V.AMBER),
                              ("left", "Side outlet", 1110, V.BLUE)):
    px, py = landmarks[key]
    point = (pos[0] + (px * 2 - 760) * size[0] / 1880,
             pos[1] + (py * 2 - 660) * size[1] / 940)
    text(x, 1085, label, 30, colour, True)
    draw.line(((x + 95, 1080), point), fill=colour, width=3)
    draw.ellipse((point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5), outline=colour, width=3)
for i, title in enumerate(("Before", "Cleaned")):
    box = (1600 + 370*i, 355, 1950 + 370*i, 660)
    asset(out / f"cleanup_{i}_detail.png", box, (125, 70, 1260, 760))
    text(box[0] + 25, 675, title, 30, V.AMBER if i == 0 else V.BLUE, True)
text(1605, 755, "Unneeded feed roofs removed", 32, bold=True)
text(1605, 815, "78.84 -> 85.07 mm2 per side", 32, V.BLUE, True)
text(1605, 870, "+7.9% local channel area", 29, V.MUTED)
text(1605, 925, "Final outlet size unchanged", 29, V.MUTED)
text(1605, 1010, "Area recovery is not a cooling %.", 26, V.AMBER)
text(75, 1165, "CAD: latest cleaned C28. Outlet detail is unchanged by cleanup; heater block omitted there only, nozzle tip retained.", 25, V.MUTED)

cards = [
    ("LARGER SUPPLY PASSAGE", ["Roof raised 3 mm to ease routing.", "Keep the floor above the probe."]),
    ("CONTROLLED REAR JET", ["18 x 0.9 mm slot, aimed 28 deg down.", "Two side jets remain in place."]),
    ("PRESERVED INTERFACES", ["Direct probe mounts; old ears removed.", "Mount datums and keepouts retained."]),
]
for i, (heading, lines) in enumerate(cards):
    x = 70 + i * 775
    draw.rounded_rectangle((x, 1240, x + 740, 1450), radius=16, fill=V.PANEL)
    text(x + 25, 1260, heading, 29, V.BLUE, True)
    for j, line in enumerate(lines):
        text(x + 25, 1320 + 45*j, line, 27, V.TEXT)

text(70, 1500, "02  COMPLETED CFD: 32 DEG -> 28 DEG", 40, bold=True)
draw.rounded_rectangle((70, 1570, 2330, 1633), radius=10, fill="#493824")
text(92, 1580, "PRE-INLET-CLEANUP GEOMETRIES.  The latest internal cleanup is not represented by these CFD results.", 29, V.AMBER, True)
asset(maps, (70, 1660, 2330, 2440))
text(85, 2450, "Velocity 0.3 mm above the bed at 180 L/min.  + = nozzle; dashed circle = 5 mm radius.  Common scale.", 27, V.MUTED)

text(80, 2520, "AIRFLOW DIAGNOSTIC", 29, V.MUTED, True)
text(1310, 2520, "32 DEG", 29, V.MUTED, True)
text(1760, 2520, "28 DEG", 29, V.BLUE, True)
text(2130, 2520, "CHANGE", 29, V.MUTED, True)
rows = [
    ("Inlet total pressure at 180 L/min", "1,451 Pa", "1,461 Pa", "+0.7%"),
    ("Estimated blower flow / 1 m hose", "229.7 L/min", "229.4 L/min", "-0.1%"),
    ("Mean speed, radius 1-5 mm", "22.3 m/s", "24.2 m/s", "+8.5%"),
    ("Weakest / strongest sector speed ratio", "0.640", "0.883", "More even"),
    ("Net radial flow at radius 8 mm", "37.6 L/min", "33.1 L/min", "-12.0%"),
]
for i, row in enumerate(rows):
    y = 2580 + 68*i
    if i % 2 == 0:
        draw.rectangle((70, y, 2330, y + 64), fill=V.PANEL)
    for x, value, colour in zip((85, 1310, 1760, 2130), row, (V.TEXT, V.TEXT, V.BLUE, V.AMBER)):
        text(x, y + 10, value, 29, colour)
text(80, 2950, "Speed, sector ratio and radial flow scale to each design's estimated blower flow; not measured blower performance.", 25, V.MUTED)
text(80, 2990, "Radial flow is signed net flow in the first 1 mm above bed, not fresh-air delivery or a heat-removal measurement.", 25, V.MUTED)
draw.line((70, 3060, 2330, 3060), fill="#29415c", width=3)
text(75, 3100, "MORE EVEN AIRFLOW, NOT A PROVEN THERMAL WINNER", 39, V.AMBER, True)
text(75, 3165, "Feedback focus: outlet aim, rear/side balance, printability and service clearances.", 33, V.TEXT)
text(75, 3235, "OpenFOAM steady SST RANS; ~2.48M cells; 1,200-iteration snapshots; matched settings and accepted meshes.", 26, V.MUTED)
text(75, 3280, "Residuals still oscillate. Local mesh sensitivity remains. No temperature field, printed bead or physical cooling test.", 26, V.MUTED)
text(75, 3330, "Study variant only. Released R43 is unchanged. New-angle CFD shown here uses Bambu + Beacon geometry.", 26, V.MUTED)

png = CAD / "images" / "sparkshift_c28_design_review.png"
jpg = CAD / "images" / "sparkshift_c28_design_review_share.jpg"
image.save(png, optimize=True)
image.resize((1920, 2736), Image.Resampling.LANCZOS).save(jpg, quality=94, subsampling=0)
manifest = {
    "description": "Current cleaned C28 design views with explicitly labelled pre-cleanup 32/28 aim CFD.",
    "cfd_report_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
    "cfd_cases": list(names), "not_cleaned_geometry_cfd": True,
    "renderer_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    "outputs": {str(p.relative_to(CAD)): {"sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                                       "dimensions": Image.open(p).size, "bytes": p.stat().st_size}
                for p in (png, jpg)},
}
(CAD / "verification_c28_share_graphic_r43.json").write_text(json.dumps(manifest, indent=2) + "\n")
print(json.dumps(manifest["outputs"], indent=2))
