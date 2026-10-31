"""v5: flow-neutral user-post retainer. Builds P21/P22, then screens fit, seal, airway intrusion and walls.

Usage: build_user_p21_receiver_v5.py [v5b|v5c|v5d]
v5c adds the print bevels (skin keel, socket bevels); v5d also fills all of P21's recess and removes all of
P22's notch boss, so nothing of P22 lies above the post when P22 drops off."""
import json
import os
import sys
import time
from pathlib import Path

CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import numpy as np

import r43_c28_mechanical as M
import r43_c28_user_joint as U
import r43_swept_feed as F
from audit_c28_mechanical_r43 import bounds, digest, mesh_check, quick_overlap

t0 = time.time()
VARIANT = sys.argv[1] if len(sys.argv) > 1 else "v5d"
assert VARIANT in ("v5b", "v5c", "v5d"), VARIANT
OUT = S / "swept_feed" / ("userP21_flow_neutral_v5" if VARIANT == "v5b" else f"userP21_flow_neutral_{VARIANT}")
OUT.mkdir(exist_ok=True)
scene = S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
read = lambda f: cq.Shape.importBrep(str(scene / f))
old21 = read(next(f for n, f in manifest["carriage"] if n.startswith("P21_")))
cable = read(next(f for n, f in manifest["carriage"] if n.startswith("Probe_Cable")))
user, exchange = U.load_user_p21(S / "swept_feed" / "userP21_20261030_193918" / "p21_user_snapshot.step")
clean22 = cq.Shape.importBrep(str(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep"))
angled = M.angled_p22(clean22)
corridor = F.main_channel_air()
# The true clean duct: inlet-connected air of P20 + released P21 + angled clean P22 (not the analytic corridor,
# which misses slivers beside the spine's rear corners).
scene41 = dict(json.loads((S / "r41_scene" / "manifest.json").read_text())["carriage"])
p20_ref = cq.Shape.importBrep(str(S / "r41_scene" / scene41["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))
air = U.clean_duct_air(p20_ref, old21, angled)
print("clean duct air", round(air.Volume(), 1), flush=True)

p21, p22, parts = U.flow_neutral_parts(user, old21, angled, air, print_bevels=VARIANT != "v5b",
                                         full_recess=VARIANT == "v5d")
print("built", round(time.time() - t0), "s", flush=True)
for key, body in {"p21": p21, "p22": p22, **{k: v for k, v in parts.items() if isinstance(v, cq.Shape)}}.items():
    body.exportBrep(str(OUT / f"{key}.brep"))


def duct_cavity(p21_body, p22_body):
    scene41 = dict(json.loads((S / "r41_scene" / "manifest.json").read_text())["carriage"])
    p20 = cq.Shape.importBrep(str(S / "r41_scene" / scene41["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))
    cap = cq.Solid.makeCylinder(8.2 + 2.5, 2.0, cq.Vector(0, -48.5, 29.0))
    space = M.box(-40, 40, -70, 60, -110, 45).cut(p20.fuse(p21_body).fuse(p22_body)).cut(cap).cut(
        M.box(-30, 30, -20, 50, -79.08, -45))
    cavity = next(s for s in space.Solids() if s.isInside(cq.Vector(0, -48.5, 20.0)))
    b = bounds(cavity)
    return {"volume_mm3": cavity.Volume(), "bounds_mm": b,
            "sealed": b[0] > -39 and b[1] < 39 and b[2] > -69 and b[5] < 44}


new21, new22 = p21.cut(old21), p22.cut(angled)
removed22 = angled.cut(p22)
air_clean = air
report = {
    "variant": OUT.name, "print_bevels": VARIANT != "v5b", "full_recess": VARIANT == "v5d",
    "parameters": {"skin_mm": U.SKIN, "slip_mm": U.SLIP, "plan_offset": "exact 2D arc offset",
                   "plan_section_z": U.SPINE_SECTION_Z},
    "exchange_repair": exchange,
    "p21": {"valid": p21.isValid(), "volume_mm3": p21.Volume(), "mesh": mesh_check(p21), "bounds_mm": bounds(p21),
            "added_vs_original_mm3": new21.Volume(), "removed_vs_original_mm3": old21.cut(p21).Volume()},
    "p22": {"valid": p22.isValid(), "volume_mm3": p22.Volume(), "mesh": mesh_check(p22), "bounds_mm": bounds(p22),
            "added_vs_clean_angled_mm3": new22.Volume(), "removed_vs_clean_angled_mm3": removed22.Volume()},
    "user_post_mm3": user.cut(old21).Volume(), "kept_post_mm3": parts["post"].Volume(),
    "discarded_post_fragments_mm3": parts["discarded_post_fragments_mm3"],
    "user_upper_kept_mm3": parts["user_upper_kept"].Volume(), "recess_fill_mm3": parts["recess_fill"].Volume(),
    "boss_shadow_skin_mm3": parts["boss_shadow_skin"].Volume(), "top_zone_z": U.TOP_ZONE_Z,
    "skin_keel_beyond_boss_wake_mm3": parts["skin_keel_beyond_boss_wake"].Volume() if VARIANT != "v5b" else 0.0,
    "p21_p22_overlap_mm3": quick_overlap(p21, p22), "p21_p22_gap_mm": p21.distance(p22),
    "cable_overlap_mm3": {"p21": quick_overlap(p21, cable), "p22": quick_overlap(p22, cable)},
    "new_material_cable_gap_mm": {"p21": new21.distance(cable), "p22": new22.distance(cable) if new22.Volume() > 1e-6 else None},
    "material_in_clean_c28_channel_air_mm3": {"p21": p21.intersect(air_clean).Volume(),
                                              "p22": p22.intersect(air_clean).Volume()},
    "socket_to_air_min_mm": parts["socket"].distance(air_clean),
    "post_to_air_min_mm": parts["post"].distance(air_clean),
    "hardware_overlaps_mm3": {n: {"p21": quick_overlap(p21, h), "p22": quick_overlap(p22, h)} for n, h in M.hardware()},
}
print(json.dumps({k: report[k] for k in ("p21_p22_overlap_mm3", "material_in_clean_c28_channel_air_mm3",
                                         "socket_to_air_min_mm", "post_to_air_min_mm", "new_material_cable_gap_mm")}),
      flush=True)
report["duct_cavity"] = duct_cavity(p21, p22)
report["baseline_duct_cavity_mm3"] = 27775.6
print("cavity", json.dumps(report["duct_cavity"]), flush=True)
# P22 drops 18 mm off the fixed P21 post for service (and assembles the reverse way).
release = []
for d in np.arange(.25, 18.01, .25):
    hit = quick_overlap(p22.translate((0, 0, -float(d))), p21)
    if hit > 1e-4:
        release.append({"lowering_mm": float(d), "overlap_mm3": hit})
report["release_collisions"] = release
print("release", "clear over 18 mm" if not release else json.dumps(release[:6]), flush=True)

# Insert wall and the thinnest post section in the cable zone.
ring = M.cylinder(0, M.RETAINER_Y, -64.95, -61.05, M.INSERT_R + 1.2).cut(
    M.cylinder(0, M.RETAINER_Y, -65, -61, M.INSERT_R))
report["insert_ring_1p2mm_fraction"] = ring.intersect(p21).Volume() / ring.Volume()
sections = {}
for z in (-51.6, -52.5, -54.0, -55.5, -57.0, -58.0, -60.0, -63.0):
    slab = M.box(-12, 12, -45, -15, z - .01, z + .01)
    piece = parts["post"].intersect(slab)
    sections[str(z)] = round(piece.Volume() / .02, 2)
report["post_plan_area_mm2"] = sections
# Thinnest wall: sample the post's plan section at several heights and measure the in-plane thickness.
from OCP.BRepClass3d import BRepClass3d_SolidClassifier
from OCP.gp import gp_Pnt
from OCP.TopAbs import TopAbs_IN
clf = BRepClass3d_SolidClassifier(parts["post"].wrapped)
thin = []
for z in (-51.8, -52.6, -53.6, -54.6, -55.6, -56.6, -57.6):
    for y in np.arange(-38.5, -27.0, .25):
        xs = np.arange(0, 6.0, .02)
        inside = []
        for x in xs:
            clf.Perform(gp_Pnt(float(x), float(y), z), 1e-7)
            inside.append(clf.State() == TopAbs_IN)
        runs, start = [], None
        for x, flag in zip(xs, inside + [False]):
            if flag and start is None:
                start = x
            if not flag and start is not None:
                runs.append((round(float(start), 2), round(float(x), 2)))
                start = None
        for a, b in runs:
            thin.append({"z": z, "y": round(float(y), 2), "x_from": a, "x_to": b, "width": round(b - a, 2)})
report["post_x_runs"] = thin
narrow = sorted((r for r in thin if r["x_from"] > .5), key=lambda r: r["width"])[:8]
back = []
for z in (-51.8, -52.6, -53.6, -54.6, -55.6, -56.6):
    for x in (0.0, 0.8, 1.6, 2.2):
        ys = np.arange(-39.5, -33.0, .02)
        flags = []
        for y in ys:
            clf.Perform(gp_Pnt(x, float(y), z), 1e-7)
            flags.append(clf.State() == TopAbs_IN)
        start = None
        for y, flag in zip(ys, flags + [False]):
            if flag and start is None:
                start = y
            if not flag and start is not None:
                back.append({"z": z, "x": x, "y_from": round(float(start), 2), "y_to": round(float(y), 2),
                             "depth": round(float(y - start), 2)})
                start = None
report["post_back_runs"] = back
report["thinnest_back_mm"] = sorted(back, key=lambda r: r["depth"])[:6]
print("back", json.dumps(report["thinnest_back_mm"]), flush=True)
report["narrowest_side_walls_mm"] = narrow
print("narrowest", json.dumps(narrow), flush=True)
report["seconds"] = round(time.time() - t0)
report["source_sha256"] = {"generator": digest(CAD / "r43_c28_user_joint.py")}
report["body_sha256"] = {k: digest(OUT / f"{k}.brep") for k in ("p21", "p22")}
(OUT / "initial_checks.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({k: v for k, v in report.items() if k not in ("post_x_runs", "post_back_runs", "exchange_repair")}, indent=1))
