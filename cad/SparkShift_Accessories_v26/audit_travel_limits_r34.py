"""Revision 34: how far the active nozzle can travel in Y with ten parked tools on the gantry.

Front: the parked tools set the print limit (verification_ten_tool_closed_panel_dock.json); the dock
needs the nozzle at Y20.71. Rear: the X beam's Y-rail blocks, the Monolith rear motor mounts and
the carriage's rear parts (P20-P22 sit up to 82 mm behind the nozzle). The usable print depth then
depends on the revision-34 bed option, and the probe coil 19.5 mm behind the nozzle sets the mesh.

Contact is tested exactly (fast_geometry.touch_or_nest) every 0.5 mm along each path, then bisected
to 0.01 mm. Snapshot geometry is the session-folder Monolith gantry, as in the low-Z audits.
"""

import json
import time

import cadquery as cq
import numpy as np

import fast_geometry as fg
from audit_bed_front_edge_r34 import BED_FRONT_Y, COIL_LOCAL_Y, COIL_RADIUS, NOZZLE_LOCAL_Y, SHIFT, frames, sha
from audit_low_z_bed_clearance import load_parked_variants
from audit_ten_tool_rack import world
from audit_tool_owned_2510 import bounds
from build_fan_mounts_r33 import carriage
from build_modular_toolhead import ROOT, primitives

REPORT = "verification_travel_limits_r34.json"
RAILS = {"R1_GANTRY_Y_RAIL_left_400_NOMINAL", "R1_GANTRY_Y_RAIL_left_400_NOMINAL (1)"}
X_SAMPLES = (0.0, 25.0, 175.0, 325.0, 350.0)
REAR_END_NOZZLE_Y = 375.0
STEP, TOL = 0.5, 0.01
SOFT_MARGIN = 1.0           # soft limit kept this far inside the first hard contact
BED_REAR = {"A_bed_Y40_to_359": 359.0, "B_stock_bed_moved_back": 359.0 + SHIFT}


def snapshot(name):
    path = primitives.WORK / f"rack_audit_{name}_world.step"
    meta = json.loads(path.with_suffix(".json").read_text())
    shape = cq.importers.importStep(str(path)).val()
    if len(shape.Solids()) != len(meta):
        raise ValueError(f"Snapshot solid count changed: {name}")
    for solid, item in zip(shape.Solids(), meta):
        expected = [v for pair in zip(item["min_mm"], item["max_mm"]) for v in pair]
        if max(abs(a - b) for a, b in zip(bounds(solid), expected)) > 0.05:
            raise ValueError(f"Snapshot order/frame changed: {name}/{item['name']}")
    return shape, meta, {"file": str(path), "sha256": sha(path)}


def first_contact(pairs, offset):
    """Labels of a touching or overlapping (moving, fixed) solid pair at this offset, else None."""
    off = np.asarray(offset, float)
    for moving, fixed in pairs:
        alo = np.array([g.box_lo for g in moving]) + off
        ahi = np.array([g.box_hi for g in moving]) + off
        blo = np.array([g.box_lo for g in fixed])
        bhi = np.array([g.box_hi for g in fixed])
        near = fg._box_distance(alo[:, None], ahi[:, None], blo[None], bhi[None]) <= 1e-6
        for i, j in zip(*np.nonzero(near)):
            if fg.touch_or_nest(moving[i], fixed[j], off):
                return moving[i].label, fixed[j].label
    return None


def sweep(pairs, x, dys):
    """Walk the offsets in order; return the last clear dy and the first contact (bisected)."""
    last = None
    for dy in dys:
        if first_contact(pairs, (x, dy, 0)):
            if last is None:
                return {"last_clear_dy_mm": None, "contact_dy_mm": dy, "pair": first_contact(pairs, (x, dy, 0))}
            lo, hi = last, dy
            while abs(hi - lo) > TOL:
                mid = 0.5 * (lo + hi)
                lo, hi = (lo, mid) if first_contact(pairs, (x, mid, 0)) else (mid, hi)
            return {"last_clear_dy_mm": lo, "contact_dy_mm": hi, "pair": first_contact(pairs, (x, hi, 0))}
        last = dy
    return {"last_clear_dy_mm": last, "contact_dy_mm": None, "pair": None}


def nearest(moving, fixed, offset, cutoff=40.0):
    hit = fg.min_distance(moving, fixed, offset_a=offset, cutoff=cutoff)
    return None if hit is None else {"mm": hit[0], "moving": hit[1], "fixed": hit[2]}


def print_depth(front, soft):
    """Printable nozzle Y and the bed band the probe can mesh, for each revision-34 bed option.

    The mesh is measured at probe positions (bed coordinates). The probe trails the nozzle by the coil
    offset, so it reaches bed Y from front + offset back to the bed edge less COIL_RADIUS, or as far
    as the nozzle's rear soft limit allows. Print positions outside that band use the nearest mesh row.
    """
    coil = [NOZZLE_LOCAL_Y - y for y in COIL_LOCAL_Y.values()]
    out = {}
    for option, bed_rear in BED_REAR.items():
        rear = min(bed_rear, soft)
        mesh = (front + max(coil), min(bed_rear - COIL_RADIUS, soft + min(coil)))
        out[option] = {"bed_y_mm": (BED_FRONT_Y, bed_rear), "nozzle_y_range_mm": (front, rear),
                       "depth_mm": rear - front, "width_mm": 350.0, "probe_mesh_bed_y_range_mm": mesh,
                       "unmeshed_front_strip_mm": max(0.0, mesh[0] - front),
                       "unmeshed_rear_strip_mm": max(0.0, rear - mesh[1])}
    return out


def main():
    started = time.perf_counter()
    f = frames()
    dock_y = f["world_y_offset_mm"] - NOZZLE_LOCAL_Y
    flying, fm, flying_src = snapshot("Flying_Gantry")
    beam, xm, beam_src = snapshot("X_Gantry")
    beam = beam.translate((0, f["x_gantry_y_shift_to_dock_mm"], 0))
    fixed_all = fg.index_group([(m["name"], s) for s, m in zip(flying.Solids(), fm)])
    fixed_norail = [g for g in fixed_all if g.label not in RAILS]
    riders = fg.index_group([(m["name"], s) for s, m in zip(beam.Solids(), xm) if m["name"].startswith("_MGN9H")])
    others = fg.index_group([(m["name"], s) for s, m in zip(beam.Solids(), xm) if not m["name"].startswith("_MGN9H")])
    beam_pairs = [(others, fixed_all), (riders, fixed_norail)]
    if first_contact(beam_pairs, (0, 0, 0)):
        raise ValueError("X beam touches the gantry at the dock position outside its rail blocks")
    rails = [m for m in fm if m["name"] in RAILS]
    rail_y = (max(m["min_mm"][1] for m in rails), min(m["max_mm"][1] for m in rails))
    blocks = [bounds(s) for s, m in zip(beam.Solids(), xm) if m["name"] in
              {"_MGN9H (10)", "_MGN9H (11)", "_MGN9H (12)", "_MGN9H (13)"}]
    block_y = (min(b[2] for b in blocks), max(b[3] for b in blocks))
    rack = json.loads((ROOT / "verification_ten_tool_closed_panel_dock.json").read_text())
    strip = rack["full_ten_tool_rack"]["front_service_strip"]
    front = strip["conservative_nozzle_y_for_whole_envelope_separation_mm"]
    report = {
        "status": "PENDING",
        "frame": "World CAD coordinates: bed X0..350; revision-34 bed front edge Y40; nozzle positions.",
        "sources": {"flying_gantry": flying_src, "x_gantry": beam_src,
                    "ten_tool_rack": {"file": "verification_ten_tool_closed_panel_dock.json",
                                      "sha256": sha(ROOT / "verification_ten_tool_closed_panel_dock.json")}},
        "front": {"dock_nozzle_y_mm": dock_y, "front_print_limit_nozzle_y_mm": front,
                  "x_traverse_corridor_nozzle_y_mm": strip["audited_x_corridor_nozzle_y_mm"],
                  "note": "Forward of the print limit the nozzle may only move in straight Y inside its own empty "
                          "bay; Klipper soft limits cannot express this, so the toolchange macros must."},
        "rails": {"y_rail_extent_mm": rail_y, "x_beam_block_y_at_dock_mm": block_y,
                  "nozzle_y_range_by_rail_length_mm": (dock_y - (block_y[0] - rail_y[0]),
                                                       dock_y + rail_y[1] - block_y[1])},
    }
    print("X beam, front and rear", flush=True)
    front_dys = [-STEP * i for i in range(0, 61)]
    rear_dys = [front - dock_y + STEP * i for i in range(int((REAR_END_NOZZLE_Y - front) / STEP) + 1)]
    b_front = sweep(beam_pairs, 0.0, front_dys)
    b_rear = sweep(beam_pairs, 0.0, rear_dys)
    report["x_beam"] = {
        "front": dict(b_front, last_clear_nozzle_y_mm=None if b_front["last_clear_dy_mm"] is None
                      else dock_y + b_front["last_clear_dy_mm"]),
        "rear": dict(b_rear, last_clear_nozzle_y_mm=None if b_rear["last_clear_dy_mm"] is None
                     else dock_y + b_rear["last_clear_dy_mm"]),
    }
    variants = load_parked_variants()
    rig = [(n, world(s, 0.0, f)) for n, s in carriage()]
    report["carriage_rear"] = []
    for label, v in variants.items():
        moving = fg.index_group(rig + [(f"{label}_tool", world(v["tool"], 0.0, f))])
        for x in X_SAMPLES:
            print(f"Carriage rear, {label} at X{x:g}", flush=True)
            found = sweep([(moving, fixed_all)], x, rear_dys)
            report["carriage_rear"].append(dict(
                found, variant=label, nozzle_x_mm=x,
                last_clear_nozzle_y_mm=None if found["last_clear_dy_mm"] is None else dock_y + found["last_clear_dy_mm"],
                clearance_at_nozzle_y359=nearest(moving, fixed_all, (x, 359.0 - dock_y, 0))))
    report["x_beam"]["clearance_at_nozzle_y359"] = min(
        (h for h in (nearest(others, fixed_all, (0, 359.0 - dock_y, 0)),
                     nearest(riders, fixed_norail, (0, 359.0 - dock_y, 0))) if h), key=lambda h: h["mm"])
    stops = {"rail_end": report["rails"]["nozzle_y_range_by_rail_length_mm"][1],
             "x_beam": report["x_beam"]["rear"]["last_clear_nozzle_y_mm"],
             "carriage": min(c["last_clear_nozzle_y_mm"] for c in report["carriage_rear"])}
    hard = min(v for v in stops.values() if v is not None)
    soft = hard - SOFT_MARGIN
    report["rear"] = {"first_contact_nozzle_y_mm": stops, "hard_stop_nozzle_y_mm": hard,
                      "recommended_soft_limit_nozzle_y_mm": soft, "soft_limit_margin_mm": SOFT_MARGIN}
    report["print_depth"] = print_depth(front, soft)
    report["probe_coil_behind_nozzle_mm"] = {k: NOZZLE_LOCAL_Y - y for k, y in COIL_LOCAL_Y.items()}
    clear = all(c["last_clear_nozzle_y_mm"] and c["last_clear_nozzle_y_mm"] > 359.0 for c in report["carriage_rear"])
    report["status"] = ("TRAVEL_LIMITS_MEASURED_NOT_COMMISSIONED" if clear and b_rear["last_clear_dy_mm"]
                        and b_front["pair"] is not None else "CHECK_RESULTS")
    report["limitations"] = [
        "Nominal 400 mm Y rails and the session Monolith snapshot; belts, cable chains and umbilicals are not modeled.",
        "X travel is sampled at nozzle X0, 25, 175, 325 and 350 only; the X-rail ends were not checked.",
        "The front print limit is the conservative whole-envelope separation from the ten-tool rack audit.",
        "Klipper endstop positions and soft limits must be commissioned on the machine.",
    ]
    report["runtime_s"] = time.perf_counter() - started
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "rails", "rear", "print_depth")}, indent=1, default=str))
    print("x_beam front:", report["x_beam"]["front"])


if __name__ == "__main__":
    main()
