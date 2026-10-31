"""Incremental real-scene movement checks for the Bambu C28 user-post retainer reviews.

Same paths and method as audit_c28_mechanical_motion_r43.py, applied to a user-post build: the sealed
receiver in WORK/swept_feed/optC28_user_retainer (audit_c28_user_retainer_r43.py) or, with
--variant flow-neutral, WORK/swept_feed/optC28_flow_neutral_retainer
(audit_c28_flow_neutral_retainer_r43.py). Adds the Cartographer receiver's new material.
"""
import argparse
import json

import cadquery as cq

import r43_c28_mechanical as M
from audit_c28_mechanical_motion_r43 import check_path
from audit_c28_mechanical_r43 import BASELINE, ROOT, SOURCE, acc, bounds, digest
from build_chute_chamfer_rack_r36 import CENTERS, PITCH, world
from build_inlet_screws_r40 import DOCK_NOZZLE_Y, GANTRY_CENTERS, REAR_LIMITS

VARIANTS = {
    "sealed": ("optC28_user_retainer", "verification_c28_user_retainer_motion_r43.json"),
    "flow-neutral": ("optC28_flow_neutral_retainer", "verification_c28_flow_neutral_retainer_motion_r43.json"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="sealed")
    variant = parser.parse_args().variant
    OUTPUT = acc.WORK / "swept_feed" / VARIANTS[variant][0]
    REPORT = ROOT / VARIANTS[variant][1]
    build_file = OUTPUT / "build_manifest.json"
    geometry = json.loads(build_file.read_text())
    assert geometry["generator_sha256"] == digest(ROOT / "r43_c28_user_joint.py")
    assert geometry["mechanical_generator_sha256"] == digest(ROOT / "r43_c28_mechanical.py")
    assert all(digest(OUTPUT / filename) == sha for filename, sha in geometry["body_sha256"].items())
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    assert geometry["frozen_scene_manifest_sha256"] == digest(SOURCE / "manifest.json")
    read = lambda p: cq.Shape.importBrep(str(SOURCE / p))
    cartographer = cq.Shape.importBrep(str(OUTPUT / "p22_cartographer.brep"))
    cartographer_added = cartographer.cut(cq.Shape.importBrep(str(BASELINE / "p22_swept_cartographer.brep")))
    assert cartographer_added.isValid()
    added = [(key, cq.Shape.importBrep(str(OUTPUT / f"{key}_added.brep"))) for key in ("p01", "p21", "p22")]
    added.append(("p22_cartographer", cartographer_added))
    changed = added + M.hardware()
    f = manifest["frames"]
    tool = [(f"Bambu_{n}", read(p)) for n, p in manifest["variants"]["Bambu"]["parts"]]
    dock = read(manifest["variants"]["Bambu"]["dock_r36"])
    local_obstacles = tool + [("Dock", dock)]
    rows = []
    rows.append(check_path("Own Bambu tool and dock: carriage withdrawal", changed, local_obstacles,
                           (0, 0, 0), (0, -60, 0), .5))
    for side in (-1, 1):
        neighbour = [(n, p.translate((side * PITCH, 0, 0))) for n, p in local_obstacles]
        rows.append(check_path(f"Adjacent Bambu bay at X {side * PITCH:g}", changed, neighbour,
                               (0, 0, 0), (0, -60, 0), 1))

    moving = [(n, world(s, 0, f)) for n, s in changed]
    xgantry = read(manifest["fixed"]["xgantry"]).translate((0, f["x_gantry_y_shift_to_dock_mm"], 0))
    rows.append(check_path("X travel against actual X gantry", moving, [("X_Gantry", xgantry)],
                           (GANTRY_CENTERS[0], 0, 0), (GANTRY_CENTERS[-1], 0, 0), 1))
    flying = read(manifest["fixed"]["flying"])
    for rear in REAR_LIMITS:
        dy = rear - DOCK_NOZZLE_Y
        rows.append(check_path(f"Rear nozzle Y {rear:g}: full X travel", moving, [("Flying_Gantry", flying)],
                               (GANTRY_CENTERS[0], dy, 0), (GANTRY_CENTERS[-1], dy, 0), 2))
    fixed = [(k, read(manifest["fixed"][k])) for k in ("hardware", "crossbar", "flying")]
    for i, center in enumerate(CENTERS):
        rows.append(check_path(f"Bay {i}: fixed gantry/rack approach", moving, fixed,
                               (center, 0, 0), (center, 60, 0), 2))
    for x in GANTRY_CENTERS:
        rows.append(check_path(f"Y travel at X {x:g}", moving, [("Flying_Gantry", flying)],
                               (x, 0, 0), (x, REAR_LIMITS[-1] - DOCK_NOZZLE_Y, 0), 2))
    bed = -79.08
    bed_gaps = {n: bounds(s)[4] - bed for n, s in changed}
    assert min(bed_gaps.values()) > 1
    lower = {"beacon": cq.Shape.importBrep(str(OUTPUT / "p22.brep")), "cartographer": cartographer}
    report = {
        "status": "INCREMENTAL_RIGID_TRANSLATION_PATHS_CLEAR",
        "source_build_manifest_sha256": digest(build_file),
        "audit_sha256": digest(__file__),
        "variant": variant,
        "scope": "All material added to P21 (post and recess fill, or post and seal skirt), both matched P22 "
                 "receivers and the angled mounts, plus every fastener, against the actual frozen Monolith/Bambu "
                 "scene. Unchanged material inherits the previous qualification; removals cannot create a "
                 "collision. This is not a new certification of the original rack, rail reach, or firmware limits.",
        "added_material_mm3": {n: s.Volume() for n, s in added},
        "paths": rows, "bed_gap_of_new_material_and_hardware_mm": bed_gaps,
        "complete_p22_to_bed_mm_at_nozzle_0p2": {k: bounds(s)[4] - bed for k, s in lower.items()},
        "limitations": "Rigid nominal CAD only; no cable dynamics, printed deflection, thermal growth or machine test.",
    }
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    main()
