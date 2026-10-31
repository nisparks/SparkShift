import argparse
import json
import os
import sys
import time
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
OUT = S / "swept_feed"
parser = argparse.ArgumentParser()
parser.add_argument("--roof-raise", type=float, default=0.0)
parser.add_argument("--mouth-height", type=float, default=1.3)
parser.add_argument("--angle", type=float, default=32.0)
parser.add_argument("--tag")
parser.add_argument("--clean-direct-mount", action="store_true")
parser.add_argument("--conformal-outlet", action="store_true")
parser.add_argument("--clear-feed-intrusions", action="store_true")
parser.add_argument("--mouth-floor-reference", type=float)
parser.add_argument("--printable-c28", action="store_true")
parser.add_argument("--bambu-only", action="store_true")
args = parser.parse_args()
if args.printable_c28 and (args.roof_raise, args.mouth_height, args.angle) != (3.0, .9, 28.0):
    parser.error("The printability variant is defined only for cleaned C28: roof 3, slot 0.9, angle 28")
if args.printable_c28 and not (args.clean_direct_mount and args.conformal_outlet and args.clear_feed_intrusions):
    parser.error("The printability variant requires all cleaned-C28 options")
RAISE, HEIGHT, ANGLE = args.roof_raise, args.mouth_height, args.angle
if args.tag:
    OUT = OUT / args.tag
elif RAISE:
    OUT = OUT / f"roof{RAISE:g}"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(CAD))
os.chdir(CAD)
import cadquery as cq
import numpy as np
import trimesh
import fast_geometry as fg
import r43_swept_feed as R
import r37_parts as P37
import r42_parts as R42
import build_and_verify_accessories_v26 as acc
from audit_tool_owned_2510 import bounds, compound

start = time.time()
base = cq.Shape.importBrep(str(S / "cfd" / "p22_r43.brep"))
part = R.p22(base, roof_raise=RAISE, mouth_height=HEIGHT, angle_deg=ANGLE,
             conformal_outlet=args.conformal_outlet, clear_feed_intrusions=args.clear_feed_intrusions,
             floor_reference_height=args.mouth_floor_reference)
if args.clean_direct_mount:
    part = R.clean_direct_mount(part)
if args.printable_c28:
    import r43_swept_printable as DFM
    part = DFM.p22(part, "Beacon")
part.exportBrep(str(OUT / "p22_swept_beacon.brep"))
carto_part = R.p22(base, "Cartographer", roof_raise=RAISE, mouth_height=HEIGHT, angle_deg=ANGLE,
                   conformal_outlet=args.conformal_outlet, clear_feed_intrusions=args.clear_feed_intrusions,
                   floor_reference_height=args.mouth_floor_reference)
if args.clean_direct_mount:
    carto_part = R.clean_direct_mount(carto_part)
if args.printable_c28:
    carto_part = DFM.p22(carto_part, "Cartographer")
carto_part.exportBrep(str(OUT / "p22_swept_cartographer.brep"))
air = R.air(RAISE, HEIGHT, ANGLE, args.mouth_floor_reference)
air.exportBrep(str(OUT / "swept_air.brep"))
print("Built", round(time.time() - start, 1), flush=True)

def mesh(s):
    vertices, triangles = s.tessellate(0.005, 0.05)
    return trimesh.Trimesh(np.array([v.toTuple() for v in vertices]), np.array(triangles), process=True)

def gap(a, b):
    hit = fg.min_distance([fg.index_of(s) for s in a.Solids()],
                          [fg.index_of(s) for s in b.Solids()], cutoff=15)
    return round(hit[0], 4) if hit else None

def overlap(a, b):
    total = 0.0
    for sa in a.Solids():
        for sb in b.Solids():
            if fg.touch_or_nest(fg.index_of(sa), fg.index_of(sb)):
                total += sa.intersect(sb).Volume()
    return round(total, 5)

def intersects_bounds(a, b, pad=0):
    return all(a[2*i] < b[2*i+1] + pad and a[2*i+1] > b[2*i] - pad for i in range(3))

result = {
    "label": "R43 swept-island routing study, not print-qualified or CFD-validated",
    "valid": part.isValid(), "solids": len(part.Solids()), "shells": len(part.Shells()),
    "volume_mm3": part.Volume(),
    "cartographer_valid": carto_part.isValid(), "cartographer_solids": len(carto_part.Solids()),
    "cartographer_shells": len(carto_part.Shells()),
    "connected_air_solids": len(air.Solids()), "air_cut_obstruction_mm3": overlap(part, air),
    "nominal_wall_mm": R.WALL, "mouth_height_mm": HEIGHT,
    "roof_raise_mm": RAISE,
    "mouth_span_mm": R.HALF_WIDTH * 2, "outlet_angle_deg": ANGLE,
    "obsolete_rear_mounts_removed": args.clean_direct_mount,
    "conformal_outlet_wall": args.conformal_outlet,
    "full_height_feed_clearance": args.clear_feed_intrusions,
    "mouth_floor_reference_height_mm": args.mouth_floor_reference,
    "printable_c28_variant": args.printable_c28,
    "hotend_scope": "Bambu only" if args.bambu_only else "Bambu and Red Lizard",
}
scene = acc.WORK / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
br = lambda f: cq.Shape.importBrep(str(scene / f))
checks = {}
for name, p, probe, hardware in (
    ("Beacon", part, compound(P37.beacon()[2:5]), P37.probe_hardware()),
    ("Cartographer", carto_part, R42.cartographer(), R42.hardware()),
):
    checks[name] = {"probe_overlap_mm3": overlap(p, probe), "probe_gap_mm": gap(p, probe)}
    bottom = P37.beacon()[0] if name == "Beacon" else R42.keepouts()["bottom"]
    top = P37.beacon()[1] if name == "Beacon" else R42.keepouts()["top"]
    checks[name]["bottom_sensing_keepout_overlap_mm3"] = overlap(p, bottom)
    checks[name]["metal_in_top_keepout_mm3"] = 0.0
    for n, s in hardware:
        if "REAR" not in n:
            checks[name][n + "_overlap_mm3"] = overlap(p, s)
            checks[name]["metal_in_top_keepout_mm3"] += overlap(s, top)
    print(name, checks[name], flush=True)
for n, f in manifest["carriage"]:
    if n.startswith(("P20_", "P21_", "P22_", "P23_", "Beacon_", "R37_PROBE_", "R37_REAR_")):
        continue
    s = br(f)
    if intersects_bounds(bounds(part), bounds(s), 0.5):
        v = overlap(part, s)
        old = overlap(base, s)
        if v > 0.001 or n.startswith("Probe_Cable"):
            checks[n] = {"overlap_mm3": v, "baseline_overlap_mm3": old, "gap_mm": gap(part, s)}
result["assembly"] = checks
print("Carriage checked", round(time.time() - start, 1), flush=True)
tools = {}
for tool in (("Bambu",) if args.bambu_only else ("Bambu", "RedLizard")):
    tools[tool] = [(n, br(f)) for n, f in manifest["variants"][tool]["parts"]]
    for n, s in tools[tool]:
        if bounds(s)[4] < -60:
            checks[f"{tool}:{n}"] = {"overlap_mm3": overlap(part, s), "gap_mm": gap(part, s)}
            if tool == "Bambu" and n == "hotend":
                checks["Bambu:silicone_sock"] = {"gap_mm": gap(part, s.Solids()[4]),
                                               "overlap_mm3": overlap(part, s.Solids()[4])}
    print(tool, {n: v for n, v in checks.items() if n.startswith(tool + ":")}, flush=True)

m = mesh(part)
ma = mesh(air)
result["mesh_watertight"] = m.is_watertight
centres, normals = ma.triangles_center, ma.face_normals
# The original channels are allowed entrances; the short extension beyond the intended
# mouth is an outlet, not a missing wall.
channel = mesh(R.main_channel_air() if args.clear_feed_intrusions else R.RJ.duct_air())
sample = centres + normals * 0.75
ends = np.array([R.mouth(float(np.clip(p[0], -10, 10))).toTuple() for p in centres])
outlet = np.einsum("ij,j->i", centres - ends, R.outlet_axes(ANGLE)[0].toTuple()) > -0.02
keep = R.mouth_keep(ANGLE)
eligible = (~outlet & mesh(keep).contains(sample)
            & ~channel.contains(sample) & ~ma.contains(sample))
solid = m.contains(sample[eligible])
mesh_bad = sample[eligible][~solid]
# Resolve triangulation disagreements at the curved open lip against the actual BREP.
bad = np.array([p for p in mesh_bad
                if any(s.isInside(cq.Vector(*p), 1e-6) for s in keep.Solids())
                and not any(s.isInside(cq.Vector(*p), 1e-6) for s in part.Solids())])
result["sampled_wall_check"] = {
    "normal_offset_mm": 0.75, "samples": int(eligible.sum()), "outside_solid": int(len(bad)),
    "triangulated_outside_solid": int(len(mesh_bad)),
    "classification": "Failed triangle-mesh samples reclassified with exact BREP solids; "
                      "points outside the intended mouth trim are an open outlet, not missing walls.",
    "failed_points_mm": bad[::max(1, len(bad)//30)].tolist()[:30],
}
print("Walls", result["sampled_wall_check"], flush=True)
result["new_outlet_lowest_mm"] = bounds(R.nozzle(
    True, RAISE, HEIGHT, ANGLE, conformal_outlet=args.conformal_outlet,
    floor_reference_height=args.mouth_floor_reference))[4]
result["outlet_underside_above_bed_mm"] = result["new_outlet_lowest_mm"] + 79.08
(OUT / "checks.json").write_text(json.dumps(result, indent=2))

green, orange, purple = cq.Color(0.1, 0.6, 0.3), cq.Color(1, 0.5, 0.05), cq.Color(0.45, 0.25, 0.65)
assembly = cq.Assembly(name="swept_island_routing_study")
region = cq.Solid.makeBox(60, 85, 40, cq.Vector(-30, -48, -80))
half = cq.Solid.makeBox(35, 85, 40, cq.Vector(-35, -48, -80))
for tag, dx, p, sensor, tool, keep in (
    ("Bambu_Beacon", 0, part, compound(P37.beacon()[2:5]), "Bambu", region),
    ("Bambu_Cartographer" if args.bambu_only else "RedLizard_Carto",
     65, carto_part, R42.cartographer(), "Bambu" if args.bambu_only else "RedLizard", region),
    ("Air_route", 130, part, compound(P37.beacon()[2:5]), "Bambu", half),
):
    assembly.add(p.intersect(keep).translate((dx, 0, 0)), name=tag+"_P22", color=green)
    assembly.add(sensor.translate((dx, 0, 0)), name=tag+"_probe", color=purple)
    for i, (n, s) in enumerate(tools[tool]):
        if n in ("hotend", "hotend and hardware"):
            assembly.add(s.intersect(region).translate((dx, 0, 0)), name=f"{tag}_hotend_{i}",
                         color=cq.Color(0.2, 0.45, 0.9) if tool == "Bambu" else cq.Color(0.85, 0.2, 0.2))
    if tag == "Air_route":
        assembly.add(air.translate((dx, 0, 0)), name=tag+"_internal_air_NOT_material", color=orange)
assembly.save(str(OUT / "swept_island_review.step"), exportType="STEP")
print("Saved", OUT, "elapsed", round(time.time() - start, 1), flush=True)
