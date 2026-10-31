import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import r43_c28_mechanical as M
import r43_swept_feed as F
from r43_c28_user_joint import load_user_p21
from audit_c28_mechanical_r43 import bounds, mesh_check, quick_overlap, digest

OUT = S / "swept_feed" / "userP21_20261030_193918"
OLD = S / "swept_feed" / "optC28_mechanical"
SCENE = S / "r43_scene"
snapshot = json.loads((OUT / "snapshot.json").read_text())
scene = json.loads((SCENE / "manifest.json").read_text())
read = lambda file: cq.Shape.importBrep(str(SCENE / file))
parts = {}
exchange = {}
for key, meta in snapshot["parts"].items():
    assert digest(meta["file"]) == meta["sha256"]
    if key == "p21":
        body, exchange[key] = load_user_p21(meta["file"])
    else:
        # Fusion omits hidden components even when they are the STEP export target.
        # The user changed P21; use the explicit, already-checked mating-part inputs.
        body = cq.Shape.importBrep(str(OLD / f"{key}.brep"))
        exchange[key] = {"reference": str(OLD / f"{key}.brep"),
                         "sha256": digest(OLD / f"{key}.brep"),
                         "native_step_omitted_hidden_component": True}
    assert body.isValid() and len(body.Solids()) == len(body.Shells()) == 1, key
    parts[key] = body.Solids()[0]
    parts[key].exportBrep(str(OUT / f"{key}.brep"))
new = parts["p21"]
old = cq.Shape.importBrep(str(OLD / "p21.brep"))
added, removed = new.cut(old, tol=1e-5), old.cut(new, tol=1e-5)
assert added.isValid() and removed.isValid()
added.exportBrep(str(OUT / "p21_added_from_fork.brep"))
removed.exportBrep(str(OUT / "p21_removed_from_fork.brep"))
cable = read(next(f for n, f in scene["carriage"] if n.startswith("Probe_Cable")))
air = F.main_channel_air().cut(parts["p22"])
report = {
    "status": "RAW_USER_SNAPSHOT_SCREEN_NOT_YET_MATED",
    "source_sha256": snapshot["parts"]["p21"]["sha256"],
    "exchange": exchange,
    "parts": {k: {"volume_mm3": p.Volume(), "faces": len(p.Faces()), "bounds_mm": bounds(p)}
              for k, p in parts.items()},
    "p21_mesh": mesh_check(new),
    "added_vs_previous_fork_mm3": added.Volume(),
    "removed_vs_previous_fork_mm3": removed.Volume(),
    "added_bounds_mm": bounds(added), "removed_bounds_mm": bounds(removed),
    "p21_cable_overlap_mm3": quick_overlap(new, cable),
    "new_material_cable_gap_mm": added.distance(cable),
    "p21_overlap_with_checked_mates_mm3": {k: quick_overlap(new, parts[k]) for k in ("p01", "p22")},
    "added_in_actual_lower_channel_air_mm3": added.intersect(air).Volume(),
    "upper_p20_p24_interface_change_mm3": sum(
        p.intersect(M.box(-24, 24, -47, 2, -25, -17)).Volume() for p in (added, removed)),
    "hardware_overlap_mm3": {n: quick_overlap(new, h) for n, h in M.hardware()},
}
interference = new.intersect(parts["p22"])
if interference.Volume() > 1e-4:
    interference.exportBrep(str(OUT / "p21_p22_interference.brep"))
    report["p21_p22_overlap_bounds_mm"] = bounds(interference)
frame = scene["frames"]
gantry = read(scene["fixed"]["xgantry"]).translate((0, frame["x_gantry_y_shift_to_dock_mm"], 0))
gantry = gantry.rotate((0, 0, 0), (0, 0, 1), 180)
report["gantry"] = {}
for center in (0, 175, 350):
    local = gantry.translate((center, frame["world_y_offset_mm"], -frame["world_z_offset_mm"]))
    report["gantry"][str(center)] = {
        "p21_overlap_mm3": quick_overlap(new, local), "new_material_gap_mm": added.distance(local)}
report["bambu_overlaps_mm3"] = {
    n: quick_overlap(new, read(p)) for n, p in scene["variants"]["Bambu"]["parts"]}
report["root_sections_mm2"] = []
for y in (-33, -32.5, -32, -31.5, -31, -30.5, -30):
    slab = M.box(-7, 7, y-.01, y+.01, -66, -43)
    report["root_sections_mm2"].append({
        "y_mm": y, "previous_fork": old.intersect(slab).Volume()/.02,
        "user_shape": new.intersect(slab).Volume()/.02})
(OUT / "initial_screen.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2), flush=True)
