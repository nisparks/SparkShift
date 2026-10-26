"""Full-rack checks using world-frame Fusion snapshots and current side-fan tools."""

import hashlib
import json
import math

import cadquery as cq

from audit_tool_owned_2510 import bounds, compound, boxes_overlap
from build_modular_toolhead import ROOT, STEP, load, primitives
from build_refined_docking_review import DOCK_STANDOFF_MM, REVIEW_REVISION, translated_hits, require_clear


def world(shape, center, frames):
    return shape.rotate((0, 0, 0), (0, 0, 1), 180).translate(
        (center, frames["world_y_offset_mm"], frames["world_z_offset_mm"]))


def snapshot(name, evidence):
    path = primitives.WORK / f"rack_audit_{name}_world.step"
    shape = cq.importers.importStep(str(path)).val()
    evidence[name] = {"file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "solids": len(shape.Solids()), "bounds_mm": bounds(shape)}
    if name != "crossbar":
        meta = json.loads(path.with_suffix(".json").read_text())
        if len(meta) != len(shape.Solids()):
            raise ValueError(f"Snapshot solid count changed: {name}")
        for solid, item in zip(shape.Solids(), meta):
            expected = [v for pair in zip(item["min_mm"], item["max_mm"]) for v in pair]
            if max(abs(a - b) for a, b in zip(bounds(solid), expected)) > 0.05:
                raise ValueError(f"Snapshot order/frame changed: {name}/{item['name']}")
    return shape


def parked_intake_review(variants):
    checks = []
    for label, active in variants.items():
        outer_x = bounds(active["envelope"])[1]
        origin = cq.Vector(outer_x, 25.5, -35.3)
        direction = cq.Vector(1, 0, 0)
        corridor = cq.Solid.makeCylinder(11, 20, origin, direction).cut(
            cq.Solid.makeCylinder(4, 20, origin, direction))
        for neighbor_label, neighbor in variants.items():
            target = compound([neighbor["tool"], neighbor["dock"]]).translate((37.3, 0, 0))
            candidates = [s for s in target.Solids() if boxes_overlap(bounds(s), bounds(corridor))]
            obstructions = [s.intersect(corridor) for s in candidates]
            obstruction_bounds = [bounds(s) for s in obstructions if s.Solids()]
            check = {
                "tool": label, "neighbor": neighbor_label,
                "gauge_limit_mm": 20,
                "nearest_annular_intake_obstruction_mm": (
                    min(b[0] for b in obstruction_bounds) - outer_x if obstruction_bounds else None),
                "slab_obstruction_samples": []}
            for gap in (2, 5, 10):
                slab = corridor.intersect(cq.Solid.makeCylinder(
                    11, 0.1, origin + direction * gap, direction))
                pieces = [s.intersect(slab) for s in candidates]
                pieces = [s for s in pieces if s.Solids()]
                if len(pieces) > 1:
                    occupied = pieces[0].fuse(*pieces[1:])
                else:
                    occupied = pieces[0] if pieces else None
                area = occupied.Volume() / 0.1 if occupied is not None else 0
                port_area = math.pi * (11 ** 2 - 4 ** 2)
                nearest = check["nearest_annular_intake_obstruction_mm"]
                if area < -0.001 or area > port_area + 0.001:
                    raise ValueError("Invalid parked intake section area")
                if area > 0.001 and (nearest is None or nearest > gap + 0.101):
                    raise ValueError("Parked intake distance and section disagree")
                check["slab_obstruction_samples"].append({
                    "gap_mm": gap, "slab_thickness_mm": 0.1,
                    "mean_obstruction_area_mm2": area,
                    "fraction_of_nominal_annular_port": area / port_area})
            checks.append(check)
    return {
        "nominal_port_outer_inner_radius_mm": [11, 4],
        "checks": checks,
        "qualification": "Geometric space gauges for the generic fan reference, not CFD or "
                         "a certified airflow gap. Neighbor tools partially obstruct the intake "
                         "corridor. Confirm selected fan orientation, hot-soak cooling and actual "
                         "wire exits with all parked fans powered."}


def audit_rack(variants, carriage, electronics, report):
    print("Auditing all ten bays against actual rack and Monolith end hardware", flush=True)
    frames = json.loads((primitives.WORK / "rack_audit_frames.json").read_text())
    if abs(frames["world_y_offset_mm"] - 36.91) > 0.001 or abs(
            frames["world_z_offset_mm"] - 191.2794) > 0.001:
        raise ValueError("Unexpected dock world frame")
    frames["original_world_y_offset_mm"] = frames["world_y_offset_mm"]
    frames["world_y_offset_mm"] += DOCK_STANDOFF_MM
    frames["x_gantry_y_shift_to_dock_mm"] += DOCK_STANDOFF_MM
    frames["dock_standoff_mm"] = DOCK_STANDOFF_MM
    rr = report["full_ten_tool_rack"] = {
        "frames": frames, "sources": {}, "bay_checks": [], "stationary_checks": [],
        "crossbeam_motion_hits": [], "lateral_motion_screens": [], "full_x_traverse": [],
        "pitch_mm": 37.3, "centers_x_mm": [7 + i * 37.3 for i in range(10)]}
    rr["parked_fan_intake_review"] = parked_intake_review(variants)
    flying = snapshot("Flying_Gantry", rr["sources"])
    xgantry = snapshot("X_Gantry", rr["sources"]).translate(
        (0, frames["x_gantry_y_shift_to_dock_mm"], 0))
    crossbar = snapshot("crossbar", rr["sources"])
    hardware = load("P29_Rack_Hardware_Complete")
    fixed = {"P29_P30_Hardware": hardware, "Crossbar": crossbar, "Flying_Gantry": flying}
    rr["spacer_stack_mm"] = [23.35, 373.0, 23.65]
    rr["rack_inner_span_mm"] = 420.0
    rr["minimum_parked_tool_x_gap_mm"] = min(
        37.3 + bounds(a["tool"])[0] - bounds(b["tool"])[1]
        for a in variants.values() for b in variants.values())
    rr["minimum_parked_gap_target_mm"] = 1.3
    if rr["minimum_parked_tool_x_gap_mm"] < rr["minimum_parked_gap_target_mm"]:
        report["failures"].append({"check": "Parked tool gap below 1.3mm nominal audit threshold"})
    rr["software_x_range_mm"] = [0, 350]
    rr["end_center_software_margin_mm"] = [7, 7.3]
    meta = json.loads((primitives.WORK / "rack_audit_X_Gantry_world.json").read_text())
    flying_meta = json.loads((primitives.WORK / "rack_audit_Flying_Gantry_world.json").read_text())
    bearing_ids = {i for i, m in enumerate(meta) if m["name"] in (
        "_MGN9H (10)", "_MGN9H (11)", "_MGN9H (12)", "_MGN9H (13)")}
    rail_ids = {i for i, m in enumerate(flying_meta) if m["name"] in (
        "R1_GANTRY_Y_RAIL_left_400_NOMINAL", "R1_GANTRY_Y_RAIL_left_400_NOMINAL (1)")}
    if len(bearing_ids) != 4 or len(rail_ids) != 2:
        raise ValueError("Unexpected inherited bearing/rail reference components")
    x_without_bearings = compound(s for i, s in enumerate(xgantry.Solids()) if i not in bearing_ids)
    flying_without_rails = compound(s for i, s in enumerate(flying.Solids()) if i not in rail_ids)
    flying_rails = compound(s for i, s in enumerate(flying.Solids()) if i in rail_ids)
    bearing_refs = compound(s for i, s in enumerate(xgantry.Solids()) if i in bearing_ids)
    rr["inherited_bearing_rail_contacts"] = {
        "at_dock_mm3": translated_hits(bearing_refs, {"Y_Rails": flying_rails}, (0, 0, 0)),
        "at_withdrawal_mm3": translated_hits(bearing_refs, {"Y_Rails": flying_rails}, (0, 60, 0)),
        "classification": "Inherited MGN9H/rail CAD overlaps, reported separately; no new rigid dock collision or physical bearing qualification."}
    rail = next(item for item in meta if item["name"] == "R1_GANTRY_X_RAIL_400_NOMINAL")
    rail_min, rail_max = rail["min_mm"][0], rail["max_mm"][0]
    rr["rail_x_bounds_mm"] = [rail_min, rail_max]
    rr["carriage_block_length_mm"] = 45.4
    rr["physical_rail_center_stroke_mm"] = [rail_min + 22.7, rail_max - 22.7]
    rr["end_rail_margins_mm"] = [7 - (rail_min + 22.7), (rail_max - 22.7) - 342.7]
    if min(rr["end_rail_margins_mm"]) <= 0:
        report["failures"].append({"check": "End bay outside physical rail stroke"})
    parked = {}
    docks = {}
    for i, center in enumerate(rr["centers_x_mm"]):
        for label, v in variants.items():
            key = f"T{i}_{label}"
            parked[key] = world(v["tool"], center, frames)
            docks[key] = world(v["dock"], center, frames)
            hits = require_clear(f"{key} parked tool to rack", parked[key], fixed, report)
            dock_hits = require_clear(f"{key} dock to rack", docks[key], fixed, report)
            rr["stationary_checks"].append({"bay": i, "variant": label,
                                             "tool_hits": hits, "dock_hits": dock_hits})
            active = world(compound([v["tool"], carriage]), center, frames)
            retreating = world(carriage, center, frames)
            check = {"bay": i, "variant": label, "samples": 121,
                     "approach_hits": [], "carriage_retreat_hits": [],
                     "carriage_is_subset_of_active_assembly": True}
            for step in range(121):
                offset = (0, step * 0.5, 0)
                hits = translated_hits(active, fixed, offset)
                if hits:
                    check["approach_hits"].append({"retreat_y_mm": offset[1], "hits": hits})
                    subset_hits = translated_hits(retreating, fixed, offset)
                    if subset_hits:
                        check["carriage_retreat_hits"].append({"retreat_y_mm": offset[1], "hits": subset_hits})
            if check["approach_hits"] or check["carriage_retreat_hits"]:
                report["failures"].append({"check": "Ten-bay rack/end approach", "result": check})
            rr["bay_checks"].append(check)
        print(f"Full rack: bay {i} static and straight motion complete", flush=True)
    parked_bounds = bounds(compound([*parked.values(), *docks.values()]))
    moving_rear = max(bounds(carriage)[3], *(bounds(v["tool"])[3] for v in variants.values()))
    conservative_front_strip = parked_bounds[3] + moving_rear - 22.7
    bed_path = primitives.WORK / "rack_audit_Bed_world.json"
    bed = json.loads(bed_path.read_text())
    if bed["body"] != "R1_BED_350_NOMINAL" or any(
            abs(bed["max_mm"][i] - bed["min_mm"][i] - 350) > 0.001 for i in (0, 1)):
        raise ValueError("Unexpected modeled bed envelope")
    rr["sources"]["Bed_envelope"] = {
        "file": str(bed_path), "sha256": hashlib.sha256(bed_path.read_bytes()).hexdigest(),
        **bed}
    rr["front_service_strip"] = {
        "parked_tool_dock_world_bounds_mm": parked_bounds,
        "conservative_nozzle_y_for_whole_envelope_separation_mm": conservative_front_strip,
        "boundary_offset_from_modeled_bed_front_mm": conservative_front_strip - bed["min_mm"][1],
        "coordinate_note": "Source-world bed datums, not commissioned Klipper coordinates.",
        "audited_x_corridor_nozzle_y_mm": frames["world_y_offset_mm"] + 60 - 22.7,
        "qualification": "Conservative bounding-envelope separation, not a certified printable-volume boundary. Reserve the front rack/service strip; full 350x350 printing is not established."}
    # Farther-than-adjacent tools cannot touch even during arbitrary Y translations.
    # Adjacent mixed cases are checked by the main generator at every sampled Y.
    rr["nonadjacent_broadphase_candidates"] = []
    for i in range(10):
        for j in range(i + 2, 10):
            for a in variants:
                for b in variants:
                    ba, bb = bounds(parked[f"T{i}_{a}"]), bounds(parked[f"T{j}_{b}"])
                    if ba[1] > bb[0]:
                        rr["nonadjacent_broadphase_candidates"].append([i, j, a, b])
    if rr["nonadjacent_broadphase_candidates"]:
        report["failures"].append({"check": "Nonadjacent tool X envelope overlap"})
    all_stationary = dict(fixed, **parked, **{f"Dock_{k}": s for k, s in docks.items()})
    del all_stationary["Flying_Gantry"]
    all_stationary["Flying_Except_Y_Rails"] = flying_without_rails
    for step in range(121):
        hits = translated_hits(xgantry, all_stationary, (0, step * 0.5, 0))
        hits.update(translated_hits(x_without_bearings, {"Flying_Y_Rails": flying_rails},
                                    (0, step * 0.5, 0)))
        if hits:
            rr["crossbeam_motion_hits"].append({"retreat_y_mm": step * 0.5, "hits": hits})
        if step % 40 == 0:
            print(f"Full rack: crossbeam sample {step}/120", flush=True)
    if rr["crossbeam_motion_hits"]:
        report["failures"].append({"check": "X gantry to full parked rack",
                                   "hits": rr["crossbeam_motion_hits"]})
    traverse_targets = dict(all_stationary, Flying_Y_Rails=flying_rails,
                           X_Gantry=xgantry.translate((0, 60, 0)))
    for label, v in variants.items():
        active = world(compound([v["tool"], carriage]), 0, frames).translate((0, 60, 0))
        check = {"variant": label, "retreat_y_mm": 60, "x_range_mm": [0, 350],
                 "step_mm": 1, "hits": []}
        for x in range(351):
            hits = translated_hits(active, traverse_targets, (x, 0, 0))
            if hits:
                check["hits"].append({"x_mm": x, "hits": hits})
        rr["full_x_traverse"].append(check)
        print(f"Full rack: {label} X0..350 traverse complete", flush=True)
        if check["hits"]:
            report["failures"].append({"check": "Full X traverse outside rack", "result": check})
    # Historical lateral scrub/peel motions are screened, not silently inherited.
    for label, v in variants.items():
        active = compound([v["tool"], carriage])
        for neighbor_label, neighbor in variants.items():
            targets = {f"Neighbor_{dx}": compound([neighbor["tool"], neighbor["dock"]]).translate((dx, 0, 0))
                       for dx in (-37.3, 37.3)}
            for retreat in (0, 12.7, 60):
                for lateral in (-6.5, -1.5, 1.5, 6.5):
                    hits = translated_hits(active, targets, (lateral, -retreat, 0))
                    rr["lateral_motion_screens"].append({
                        "tool": label, "neighbor": neighbor_label, "local_x_mm": lateral,
                        "retreat_mm": retreat, "hits": hits})
                    if retreat == 60 and hits:
                        report["failures"].append({"check": "Lateral move still obstructed after withdrawal",
                                                   "tool": label, "neighbor": neighbor_label, "hits": hits})
    rr["docking_path_constraint"] = (
        "Approach/withdraw along Y at fixed bay X. No inherited lateral peel or X-wiper scrub "
        "is approved inside the rack. Lateral tests are diagnostic, not an implemented machine sequence.")
    rr["sample_scope"] = (
        "20 tool/bay cases against crossbar, P29/P30 hardware and flying gantry; complete X-gantry "
        "sweep against all 20 possible parked tool/dock cases, Y0..60 every 0.5mm. "
        "All 8 mixed immediate-neighbor cases checked separately; farther bays separated in X.")
    rack = cq.Assembly(name=f"{REVIEW_REVISION} Ten side-fan toolheads and closed-panel docks")
    for i, center in enumerate(rr["centers_x_mm"]):
        label = "Bambu" if i % 2 == 0 else "RedLizard"
        v = variants[label]
        rack.add(world(v["tool"], center, frames), name=f"T{i}_{label}",
                 color=cq.Color(0.9, 0.65, 0.1) if label == "Bambu" else cq.Color(0.85, 0.3, 0.12))
        rack.add(world(v["dock"], center, frames), name=f"D{i}_{label}", color=cq.Color(0.22, 0.4, 0.32))
    rack.add(hardware, name="Unchanged_P29_P30_Hardware", color=cq.Color(0.3, 0.35, 0.4))
    rack.add(crossbar, name="Existing_2020_Crossbar", color=cq.Color(0.65, 0.65, 0.68))
    rack.add(xgantry, name="Monolith_X_Gantry_At_Dock", color=cq.Color(0.55, 0.55, 0.58))
    rack.add(world(carriage, 7, frames), name="Carriage_At_T0", color=cq.Color(0.5, 0.52, 0.55))
    output = STEP / f"{REVIEW_REVISION}_Ten_Tool_Side2510_Rack_REVIEW.step"
    rack.export(str(output))
    imported = cq.importers.importStep(str(output)).val()
    expected = sum(len(s.Solids()) for s in (
        hardware, crossbar, xgantry, carriage)) + sum(
            len(variants["Bambu" if i % 2 == 0 else "RedLizard"]["tool"].Solids()) +
            len(variants["Bambu" if i % 2 == 0 else "RedLizard"]["dock"].Solids()) for i in range(10))
    rr["export"] = {"file": output.name, "solids": len(imported.Solids()),
                    "expected_solids": expected, "valid": imported.isValid(),
                    "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
    if not imported.isValid() or len(imported.Solids()) != expected:
        report["failures"].append({"check": "Full ten-tool rack STEP reimport"})
