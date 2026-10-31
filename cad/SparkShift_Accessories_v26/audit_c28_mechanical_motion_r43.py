"""Incremental real-scene movement checks for the separate C28 mechanical review."""
import json
import math

import cadquery as cq
import numpy as np

import fast_geometry as fg
import r43_c28_mechanical as M
from audit_c28_mechanical_r43 import OUTPUT, ROOT, SOURCE, bounds, digest
from build_chute_chamfer_rack_r36 import CENTERS, PITCH, world
from build_inlet_screws_r40 import DOCK_NOZZLE_Y, GANTRY_CENTERS, REAR_LIMITS


def check_path(label, moving, targets, start, end, step):
    a, b = fg.index_group(moving), fg.index_group(targets)
    start, end = np.asarray(start, float), np.asarray(end, float)
    delta = end - start
    length = float(np.linalg.norm(delta))
    cache = {}
    cap = step + .1
    certified = []

    def sample(t):
        if t not in cache:
            offset = tuple(start + delta * t)
            hit = fg.min_distance(a, b, offset_a=offset, cutoff=cap)
            distance = hit[0] if hit else cap
            assert distance > 1e-6, (label, offset, hit)
            cache[t] = {"mm": distance, "offset_mm": offset, "capped": hit is None,
                        "moving_part": hit[1] if hit else None, "obstacle": hit[2] if hit else None}
        return cache[t]["mm"]

    def interval(t0, t1, depth=0):
        d0, d1 = sample(t0), sample(t1)
        lower = min(d0, d1) - length * (t1 - t0) / 2
        if lower > 1e-5:
            certified.append(lower)
            return
        assert depth < 16, (label, t0, t1, d0, d1, "Cannot certify positive clearance")
        middle = (t0 + t1) / 2
        interval(t0, middle, depth + 1)
        interval(middle, t1, depth + 1)

    count = max(1, math.ceil(length / step))
    for i in range(count):
        interval(i / count, (i + 1) / count)
    nearest = min(cache.values(), key=lambda row: row["mm"])
    row = {
        "label": label, "start_offset_mm": start.tolist(), "end_offset_mm": end.tolist(),
        "initial_step_mm": step, "exact_distance_samples": len(cache),
        "minimum_sample": nearest, "continuous_clearance_lower_bound_mm": min(certified),
        "method": "Exact BREP face distances, adaptively refined. Distance is 1-Lipschitz under translation: "
                  "the smaller endpoint distance minus half the interval length bounds every point in it. "
                  "Capped readings are conservative lower bounds, not reported exact distances.",
    }
    print(label, json.dumps(row), flush=True)
    return row


def main():
    build_file = OUTPUT / "build_manifest.json"
    geometry = json.loads(build_file.read_text())
    assert geometry["generator_sha256"] == digest(ROOT / "r43_c28_mechanical.py")
    assert all(digest(OUTPUT / filename) == sha for filename, sha in geometry["body_sha256"].items())
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    assert geometry["frozen_scene_manifest_sha256"] == digest(SOURCE / "manifest.json")
    read = lambda p: cq.Shape.importBrep(str(SOURCE / p))
    added = [(key, cq.Shape.importBrep(str(OUTPUT / f"{key}_added.brep")))
             for key in ("p01", "p21", "p22")]
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
    full_lower = cq.Shape.importBrep(str(OUTPUT / "p22.brep"))
    report = {
        "status": "INCREMENTAL_RIGID_TRANSLATION_PATHS_CLEAR",
        "source_build_manifest_sha256": digest(build_file),
        "audit_sha256": digest(__file__),
        "scope": "All added material and every new fastener against the actual frozen Monolith/Bambu scene. "
                 "Unchanged material inherits the previous qualification; removals cannot create a collision. "
                 "This is not a new certification of the original rack, rail reach, or firmware limits.",
        "paths": rows, "bed_gap_of_new_material_and_hardware_mm": bed_gaps,
        "complete_p22_to_bed_mm_at_nozzle_0p2": bounds(full_lower)[4] - bed,
        "limitations": "Rigid nominal CAD only; no cable dynamics, printed deflection, thermal growth or machine test.",
    }
    (ROOT / "verification_c28_mechanical_motion_r43.json").write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)


if __name__ == "__main__":
    main()
