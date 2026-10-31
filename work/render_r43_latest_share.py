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
import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import render_r43_public_comparison as V

names = ("r43_bambu_bed", "r43directC28clean_bambu_bed")
reference_file = CAD / "verification_swept_feed_cfd_r43.json"
latest_file = CAD / "verification_feed_cleanup_cfd_r43.json"
reference = json.loads(reference_file.read_text())["cases"][names[0]]
latest = json.loads(latest_file.read_text())["cases"][names[1]]
metrics = [
    {"pressure_pa": reference["pressure_at_180_pa"],
     "estimated_blower_lpm": reference["estimated_blower_lpm_1m_hose"],
     "rear_lpm": 0.,
     "speeds": reference["near_print_mean_speed_ms_at_estimated_blower"],
     "radial_r8_lpm": reference["near_print_net_radial_outflow_within_1mm_lpm_at_estimated_blower"]["r8_mm"],
     "sector_ratio": reference["coverage_at_estimated_blower"]["weakest_to_strongest_sector_mean_ratio"],
     "mesh": reference["mesh"]},
    {"pressure_pa": latest["inlet_pressure_pa_at_180"],
     "estimated_blower_lpm": latest["estimated_blower_lpm_1m_hose"],
     "rear_lpm": latest["rear_branch_at_180"]["lpm"],
     "speeds": latest["mean_speed_ms_at_estimated_blower"],
     "radial_r8_lpm": latest["net_radial_lpm_at_estimated_blower"]["r8_mm"],
     "sector_ratio": latest["coverage_at_estimated_blower"]["weakest_to_strongest_sector_mean_ratio"],
     "mesh": latest["mesh"]},
]
out = V.S / "swept_feed" / "optC28_clean"
grids = []
for name in names:
    assert P.mesh_stats(name)["mesh_ok"], name
    assert any(s["lpm"] == 180 and s["end"] == 1200 for s in P.stages(name)), name
    log = (C.results_dir(name) / "log.simpleFoam").read_text()
    assert "Time = 1200\n" in log and "\nEnd\n" in log, name
    grid = P.internal(name, 1200)
    tag = "share_r43" if name == names[0] else "share_clean_c28"
    V.render_streamline_view(grid, name, tag)
    grids.append(grid)


def plane_pair(axis, at, limits, filename):
    side = axis == "x"
    fig, axes = plt.subplots(1, 2, figsize=(14.6, 3.0 if side else 5.3))
    fig.patch.set_facecolor(V.PANEL)
    fig.subplots_adjust(left=.05, right=.98, bottom=.2 if side else .13, top=.88, wspace=.22)
    for ax, grid, title in zip(axes, grids, ("R43", "Latest C28 / cleaned feeds")):
        _, _, speed, _, _ = V.sample_map(grid, axis, at, limits, nx=420)
        ax.set_facecolor("#a9b5c3")
        ax.imshow(speed, origin="lower", extent=limits, vmin=0, vmax=65, cmap="turbo", aspect="equal")
        if side:
            ax.plot(22.7, -78.88, "w+", ms=8)
            ax.axhline(-79.08, color=V.AMBER, lw=1)
        else:
            ax.plot(0, 22.7, "w+", ms=8)
            for radius in (5, 10):
                ax.add_patch(Circle((0, 22.7), radius, fill=False, color="white",
                                    lw=1, ls="--", alpha=.7))
        ax.set_title(title, color=V.TEXT, fontsize=17, pad=10)
        ax.set_xlabel("Y (mm)" if side else "X (mm)", color=V.MUTED, fontsize=13)
        ax.set_ylabel("Z (mm)" if side else "Y (mm)", color=V.MUTED, fontsize=13)
        ax.tick_params(colors=V.MUTED, labelsize=12)
        for spine in ax.spines.values():
            spine.set_color(V.MUTED)
    path = out / filename
    fig.savefig(path, dpi=150, facecolor=V.PANEL)
    plt.close(fig)
    return path


plan = plane_pair("z", -78.78, (-14, 14, 8.7, 36.7), "share_r43_latest_plan.png")
side = plane_pair("x", 0, (-8, 36, -79.8, -63.8), "share_r43_latest_side.png")
grids.clear()
gc.collect()
fig, ax = plt.subplots(figsize=(14.6, .7))
fig.patch.set_facecolor(V.PANEL)
bar = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 65), cmap="turbo"),
                   cax=ax, orientation="horizontal", ticks=(0, 10, 20, 30, 40, 50, 60, 65), extend="max")
bar.ax.set_xticklabels(("0", "10", "20", "30", "40", "50", "60", "65+"))
bar.ax.tick_params(colors=V.TEXT, labelsize=13)
fig.tight_layout(pad=.4)
scale = out / "share_r43_latest_scale.png"
fig.savefig(scale, dpi=150, facecolor=V.PANEL)
plt.close(fig)

image = Image.new("RGB", (2400, 3960), V.BG)
draw = ImageDraw.Draw(image)


def text(x, y, value, size=30, colour=V.TEXT, bold=False):
    draw.text((x, y), value, font=V.font(size, bold), fill=colour)


def asset(path, box, crop=None):
    pic = Image.open(path).convert("RGB")
    if crop:
        pic = pic.crop(crop)
    factor = min((box[2]-box[0])/pic.width, (box[3]-box[1])/pic.height)
    pic = pic.resize((round(pic.width*factor), round(pic.height*factor)), Image.Resampling.LANCZOS)
    xy = (box[0]+(box[2]-box[0]-pic.width)//2, box[1]+(box[3]-box[1]-pic.height)//2)
    image.paste(pic, xy)
    return xy, pic.size


text(70, 40, "R43  vs.  LATEST REAR-FEED", 66, bold=True)
text(72, 130, "Bambu hotend  |  Same 180 L/min CFD flow  |  Current candidate: cleaned C28", 30, V.MUTED)
text(75, 210, "R43", 48, bold=True)
text(1270, 210, "LATEST C28", 48, V.BLUE, True)
text(75, 280, "Two side outlets", 28, V.MUTED)
text(1270, 280, "Side + rear outlets  /  28 deg  /  0.9 mm rear slot", 28, V.MUTED)
cad_boxes = ((70, 350, 1140, 890), (1260, 350, 2330, 890))
for index, (box, tag) in enumerate(zip(cad_boxes, ("r43", "candidate_a"))):
    if index == 0:
        pos, size = asset(V.ASSETS / "ports_closeup_r43.png", box)
    else:
        pos, size = asset(V.S / "swept_feed" / "optC28_conformal" / "aim_outlets_1.png",
                          box, (760, 660, 2640, 1600))
    points = json.loads((V.ASSETS / f"ports_{tag}.json").read_text())
    if index:
        px, py = points["rear"]
        point = (pos[0] + (px*2-760)*size[0]/1880, pos[1] + (py*2-660)*size[1]/940)
        text(box[0]+20, 894, "Curved rear slot", 26, V.AMBER, True)
        draw.line(((box[0]+120, 886), point), fill=V.AMBER, width=3)
    px, py = points["left"]
    point = (pos[0] + (px*2-760)*size[0]/1880, pos[1] + (py*2-660)*size[1]/940)
    text(box[2]-230, 894, "Side outlet", 26, V.BLUE, True)
    draw.line(((box[2]-140, 886), point), fill=V.BLUE, width=3)
text(75, 948, "CAD detail: heater block hidden only here; nozzle tip retained. CFD includes the hotend and sock.", 25, V.MUTED)

text(75, 1015, "3D AIRFLOW", 38, bold=True)
for tag, x in (("share_r43", 70), ("share_clean_c28", 1260)):
    asset(V.ASSETS / f"streamlines_{tag}.png", (x, 1090, x+1070, 1770))
text(75, 1790, "Same 128 upstream seeds. Line density is not flow volume. Ghosted walls / bed hidden for visibility.", 25, V.MUTED)
asset(scale, (180, 1845, 2220, 1940))
text(75, 1950, "Air speed (m/s)  |  Shared 0-65+ scale for every CFD visual", 28, V.MUTED)

text(75, 2020, "0.3 mm ABOVE THE BED", 38, bold=True)
text(1390, 2030, "+ nozzle  /  dashed radii: 5 and 10 mm", 26, V.MUTED)
asset(plan, (70, 2090, 2330, 2860))
text(75, 2890, "CENTRE PLANE / JET AIM", 36, bold=True)
asset(side, (70, 2950, 2330, 3380))

# The data strip replaces prose; the complete source values remain in the sidecar.
a, b = metrics
percent = lambda v0, v1: f"{100*(v1/v0-1):+.1f}%"
rows = [
    ("Pressure at 180 L/min", f"{a['pressure_pa']:,.0f} Pa", f"{b['pressure_pa']:,.0f} Pa",
     percent(a["pressure_pa"], b["pressure_pa"])),
    ("Estimated total flow / 1 m hose", f"{a['estimated_blower_lpm']:.1f} L/min",
     f"{b['estimated_blower_lpm']:.1f} L/min", percent(a["estimated_blower_lpm"], b["estimated_blower_lpm"])),
    ("Rear branch at 180 L/min", "None", f"{b['rear_lpm']:.1f} L/min", "New branch"),
]
for radius in (5, 10, 14):
    key=f"r{radius}_mm"
    rows.append((f"Mean speed / radius 1-{radius} mm", f"{a['speeds'][key]:.1f} m/s",
                 f"{b['speeds'][key]:.1f} m/s", percent(a["speeds"][key], b["speeds"][key])))
rows.extend([
    ("Weakest / strongest sector ratio", f"{a['sector_ratio']:.3f}", f"{b['sector_ratio']:.3f}",
     f"{b['sector_ratio']-a['sector_ratio']:+.3f}"),
    ("Net radial flow / radius 8 mm", f"{a['radial_r8_lpm']:.1f} L/min", f"{b['radial_r8_lpm']:.1f} L/min",
     percent(a["radial_r8_lpm"], b["radial_r8_lpm"])),
])
# Expand the lower canvas rather than shrink imagery or make data unreadable.
canvas = Image.new("RGB", (2400, 4260), V.BG)
canvas.paste(image, (0, 0))
image = canvas
draw = ImageDraw.Draw(image)
for x, label in ((80, "AIRFLOW DATA"), (1230, "R43"), (1690, "LATEST C28"), (2150, "CHANGE")):
    text(x, 3410, label, 28, V.MUTED, True)
for i, row in enumerate(rows):
    y=3470+i*62
    if i%2==0:
        draw.rectangle((70,y,2330,y+60),fill=V.PANEL)
    for x,value,colour in zip((85,1230,1690,2150),row,(V.TEXT,V.TEXT,V.BLUE,V.AMBER)):
        text(x,y+8,value,28,colour)
text(75, 4000, "Speed / sector / radial rows at estimated blower operation. Radial = signed net flow in first 1 mm above bed.", 24, V.MUTED)
text(75, 4040, "Both meshes pass: R43 1.64M cells; C28 2.48M. Local refinement/decomposition differ; not mesh-independent.", 24, V.MUTED)
text(75, 4080, "Steady SST RANS; iteration-1200 fields; pressure averaged over last 100. Oscillating residuals remain.", 24, V.MUTED)
text(75, 4140, "AIRFLOW COMPARISON, NOT THERMAL VALIDATION", 34, V.AMBER, True)
text(75, 4200, "Latest candidate is not a proven cooling winner. No temperature field, deposited bead or physical print test.", 24, V.MUTED)
png=CAD/"images"/"r43_vs_latest_c28.png"
jpg=CAD/"images"/"r43_vs_latest_c28_share.jpg"
image.save(png,optimize=True)
image.resize((1920,3408),Image.Resampling.LANCZOS).save(jpg,quality=94,subsampling=0)
sidecar={
    "cases":list(names),"metrics":dict(zip(names,metrics)),
    "latest_geometry":"optC28_clean; full-height feed clearance, 28 degrees, 0.9 mm slot",
    "visuals_flow_lpm":180,"iteration":1200,"speed_range_ms":[0,65],"contains_branding":False,
    "comparison_limitations":"Accepted but different local meshes/decomposition; geometry-specific mounts. "
                             "Steady snapshots, not mesh-independent or thermally validated.",
    "sources_sha256":{str(p.relative_to(CAD)):hashlib.sha256(p.read_bytes()).hexdigest()
                      for p in (reference_file,latest_file)},
    "geometry_sha256":{
        "r43":hashlib.sha256((C.CFD/"p22_r43.brep").read_bytes()).hexdigest(),
        "latest":hashlib.sha256((out/"p22_swept_beacon.brep").read_bytes()).hexdigest()},
    "outputs":{str(p.relative_to(CAD)):{"sha256":hashlib.sha256(p.read_bytes()).hexdigest(),
                                      "bytes":p.stat().st_size,"dimensions":Image.open(p).size} for p in (png,jpg)},
}
(CAD/"verification_r43_vs_latest_graphic_r43.json").write_text(json.dumps(sidecar,indent=2)+"\n")
print(json.dumps({"outputs":sidecar["outputs"],"data":rows},indent=2))
