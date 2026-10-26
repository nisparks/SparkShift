"""Bambu toolhead revision 30: compact fan side and closed P18 bores, rebuilt from revision 22.

Same clean sequence as revision 29 (inlet socket, restored front neck, filled corridors,
round fan bosses), with three changes driven by dock spacing and the user's review:

1. Fan pulled 1.65 mm toward the hotend. Its seat face is X9.80, leaving a 1.5 mm air gap
   to the heatsink fins. The shelf's fan-side face moves to X9.55. This also removes the
   1.25 mm strip behind the fan that extended to X15 and stopped 0.10 mm from the active
   carriage frame whenever a neighbour tool was parked on the carriage's -X side.
2. Lower P18 insert pockets end inside the flange (3.38 mm deep, 0.5 mm rear wall). A 4 mm
   insert cannot fit there: behind the flange the shelf top is only 1.98 mm above the bore
   axis, so the old bores broke through it. These two positions take M3 x 3 mm inserts.
3. Verification adds full-tool motion checks and minimum distances between the active
   carriage and parked neighbours, not only volume overlaps.

Run with --stage geometry for a fast build and static checks, or with no arguments for the
full motion, regression and export pass.
"""

import argparse
import json

import cadquery as cq
import trimesh

import fast_geometry
from audit_tool_owned_2510 import bounds, compound, overlaps
from build_bambu_clean_r29 import (
    APRON, BASE, FAN_AXES_Y, FAN_AXIS_Z, FLANGE_BOTTOM_Z, INLET_XY, P18_BOTTOM_Z, REFERENCES,
    SHELF_LOWER, SOURCE_ASSEMBLY, SOURCE_BODY, add, cone_x, cone_z, cyl_x, cyl_z, neck_stock,
    remove, sha, single)
from build_modular_toolhead import ROOT, STEP, STL, box, cylinder_y, load, primitives, volume
from build_refined_docking_review import translated_hits

NAME = "Bambu_Compact_Fan_Closed_Bores_R30_REVIEW"
REPORT = "verification_bambu_compact_r30.json"
FAN_DX = -1.65
FAN_SEAT_X = 11.45 + FAN_DX
SHELF_FACE_X = FAN_SEAT_X - 0.25
SHELF_TOP = -17.2794
FLANGE_REAR_Y = 32.05
P18_POCKET_START = 32.55
PITCH = 37.3
ZONES = (
    (-9.3, 11.9, 30.9, 38.9, -28.9, FLANGE_BOTTOM_Z + 0.01),
    (-13.6, 11.9, 11.0, 20.1, -28.9, -22.4),
    (-4.9, 4.9, 17.7, 27.7, -30.5, -25.9),
    (9.2, 22.1, 11.3, 38.9, -48.2, -22.4),
    (-8.4, -3.6, 30.9, 32.7, -21.6, -16.9),
    (3.6, 8.4, 30.9, 32.7, -21.6, -16.9),
)


def fan_parts():
    fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW").translate((FAN_DX, 0, 0))
    screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW").translate((FAN_DX, 0, 0))
    envelope = box(FAN_SEAT_X, FAN_SEAT_X + 10, 13, 38, -47.8, -22.8)
    return fan, screws, envelope


def build_body(log):
    base = single(load(BASE), "revision-22 baseline")
    body = base
    # Legacy fan-seat stock outside the apron, as in revision 29.
    body = remove(body, box(APRON[1], 11.8, FLANGE_REAR_Y, 38.8, -28.8, P18_BOTTOM_Z),
                  "legacy front seat block outside apron", log)
    body = remove(body, box(APRON[1], 11.8, 31.0, FLANGE_REAR_Y, -28.8, -26.0),
                  "legacy front ring below shelf corner", log)
    body = remove(body, box(5.0, 11.8, 11.0, 20.0, -28.8, -26.0), "legacy rear ring below shelf", log)
    body = remove(body, box(5.0, APRON[1] + 0.05, APRON[3], 38.2, -28.8, -22.4),
                  "0.1 mm ring remnant proud of apron front face", log)
    # One flat fan-side face at X9.55 below the shelf's upper layer, full length. This also
    # removes the rear strip that reached X15 and the old 0.05 mm membrane.
    body = remove(body, box(SHELF_FACE_X, 22.0, 11.4, 38.8, -48.1, -22.5),
                  "fan-side face to X9.55 incl. rear strip", log)
    domain = box(*SHELF_LOWER).fuse(box(*APRON))
    for y in FAN_AXES_Y:
        corridor = cyl_x(y, FAN_AXIS_Z, -15.35, 7.45, 2.2)
        body = add(body, corridor.intersect(domain), f"restore shelf/apron through corridor Y{y}", log)
    body = add(body, neck_stock(), "restored P17 front neck", log)
    for x in (-6.0, 6.0):
        body = add(body, cylinder_y(x, -22.75, 31.1, 34.2, 3.2).intersect(box(*APRON)),
                   f"fill legacy counterbore crescent X{x:+.0f}", log)
    # Lower P18 insert pockets: close the old bore behind the flange (only up to the shelf
    # top, so nothing rises into the gap under the carriage), then recut inside the flange.
    for x in (-6.0, 6.0):
        slot = cylinder_y(x, -19.26, 31.0, FLANGE_REAR_Y + 0.05, 2.28).intersect(
            box(x - 3, x + 3, 30.9, FLANGE_REAR_Y + 0.1, -22.0, SHELF_TOP))
        body = add(body, slot, f"close bore slot under shelf top X{x:+.0f}", log)
        body = add(body, cylinder_y(x, -19.26, FLANGE_REAR_Y, P18_POCKET_START, 2.28),
                   f"pocket rear wall inside flange X{x:+.0f}", log)
        body = remove(body, cylinder_y(x, -19.26, P18_POCKET_START, 37.0, 2.28),
                      f"M3 x 3 mm insert pocket X{x:+.0f}", log)
    # Fan bosses: the fan seats on their faces. The front boss is bridged to the shelf face.
    body = add(body, box(APRON[1], SHELF_FACE_X, SHELF_LOWER[3], 35.5, SHELF_LOWER[4], P18_BOTTOM_Z),
               "shelf-to-front-boss bridge", log)
    inserts = []
    for y in FAN_AXES_Y:
        boss = cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.25, FAN_SEAT_X, 3.0).fuse(
            cone_x(y, FAN_AXIS_Z, FAN_SEAT_X - 5.75, 1.5, FAN_SEAT_X - 4.25, 3.0))
        boss = boss.intersect(box(FAN_SEAT_X - 6, FAN_SEAT_X, SHELF_LOWER[2], APRON[3], -28.3, P18_BOTTOM_Z))
        body = add(body, boss, f"fan boss Y{y}", log)
    for y in FAN_AXES_Y:
        body = remove(body, cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.5, FAN_SEAT_X + 0.01, 1.55),
                      f"L4 heat-set pilot Y{y}", log)
        body = remove(body, cone_x(y, FAN_AXIS_Z, FAN_SEAT_X - 0.3, 1.55, FAN_SEAT_X + 0.01, 1.86),
                      f"pilot entry chamfer Y{y}", log)
        inserts.append(cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.0, FAN_SEAT_X, 1.75).cut(
            cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.01, FAN_SEAT_X + 0.01, 1.05)))
    # Inlet socket sleeve, as revision 29.
    x0, y0 = INLET_XY
    sleeve = cyl_z(x0, y0, -29.9, -26.0, 4.0).fuse(cone_z(x0, y0, -30.4, 3.5, -29.9, 4.0)).fuse(
        cone_z(x0, y0, -26.8, 4.0, -26.0, 4.8))
    body = add(body, sleeve, "inlet socket sleeve", log)
    body = remove(body, cyl_z(x0, y0, -30.41, -29.28, 2.625), "socket around inlet tube", log)
    body = remove(body, cone_z(x0, y0, -30.41, 2.925, -30.11, 2.625), "socket entry chamfer", log)
    body = remove(body, cyl_z(x0, y0, -29.29, -27.0, 1.15), "2.3 mm filament guide", log)
    body = remove(body, cone_z(x0, y0, -27.0, 1.15, -26.0, 2.13), "funnel into existing guide bore", log)
    return base, body, compound(inserts)


def protected_parts():
    refs = {n: load(n) for n in REFERENCES}
    hardware = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW").Solids()
    _, screws, envelope = fan_parts()
    return dict(refs, Hotend=load("Tool2510_Reversed_Bambu_Reference_REVIEW"), Fan_Envelope=envelope,
                Fan_Screws=screws, Hotend_Screws=compound(hardware[i] for i in (1, 4, 7)),
                Hotend_Washers=compound(hardware[i] for i in (2, 5)))


def static_checks(base, body):
    failures = []
    if len(body.Shells()) != 1:
        failures.append({"check": "internal voids (extra shells)", "shells": len(body.Shells())})
    hits = overlaps(body, protected_parts())
    if hits:
        failures.append({"check": "protected-part interference", "hits": hits})
    changed = compound([*body.cut(base).Solids(), *base.cut(body).Solids()])
    zones = box(*ZONES[0])
    for z in ZONES[1:]:
        zones = zones.fuse(box(*z))
    zones = zones.clean()
    outside = sum(volume(s.cut(zones)) for s in changed.Solids())
    if outside > 1e-3:
        failures.append({"check": "change outside declared edit zones", "mm3": outside})
    x0, y0 = INLET_XY
    neck_gauge = neck_stock()
    for x in (-6.0, 6.0):
        neck_gauge = neck_gauge.cut(cylinder_y(x, -19.26, 30.0, 38.0, 2.3))
    neck_gauge = neck_gauge.cut(cyl_x(35.5, FAN_AXIS_Z, FAN_SEAT_X - 4.6, FAN_SEAT_X + 0.1, 1.9))
    gauges = {
        "front_neck_unfilled_mm3": volume(neck_gauge.cut(body)),
        "wire_trough_blocked_mm3": volume(box(-2.5, 2.5, 30.1, 35.9, -23.95, -19.5).intersect(body)),
        "wire_trough_bottom_entry_blocked_mm3": volume(box(-0.7, 0.7, 28.3, 31.0, -26.5, -24.1).intersect(body)),
        "fan_recess_membrane_mm3": volume(box(FAN_SEAT_X + 0.01, 15.1, 12.8, 32.0, -22.58, -22.505).intersect(body)),
        "rear_strip_remaining_mm3": volume(box(SHELF_FACE_X + 0.05, 15.1, 11.4, 12.45, -26.1, -22.51).intersect(body)),
        "socket_wall_missing_mm3": volume(cyl_z(x0, y0, -29.85, -26.1, 3.9).cut(
            cyl_z(x0, y0, -29.86, -26.09, 2.7)).cut(body)),
        "socket_blocked_mm3": volume(cyl_z(x0, y0, -30.39, -29.3, 2.6).intersect(body)),
        "filament_path_blocked_mm3": volume(cyl_z(x0, y0, -29.48, 48.0, 0.9).intersect(body)),
    }
    shelf_gauge = box(*SHELF_LOWER).cut(cyl_z(0, 22.68, -27, -22, 2.2)).cut(box(-2.6, 2.6, 28.1, 32.1, -27, -22))
    for y in FAN_AXES_Y:
        tag = f"{y:g}".replace(".", "p")
        # Stops short of the fan pilot, which now starts at X5.30 inside the old corridor line.
        corridor = cyl_x(y, FAN_AXIS_Z, -13.4, FAN_SEAT_X - 4.55, 2.19)
        gauges[f"corridor_{tag}_open_mm3"] = volume(corridor.intersect(shelf_gauge.fuse(box(*APRON))).cut(body))
        gauges[f"boss_{tag}_wall_missing_mm3"] = volume(cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.45, FAN_SEAT_X - 0.35, 2.3).cut(
            cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.46, FAN_SEAT_X, 1.76)).cut(body))
        gauges[f"pilot_{tag}_blocked_mm3"] = volume(cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.49, FAN_SEAT_X, 1.54).intersect(body))
    for x in (-6.0, 6.0):
        tag = f"x{x:+.0f}"
        gauges[f"p18_pocket_{tag}_wall_missing_mm3"] = volume(cylinder_y(x, -19.26, 32.6, 35.9, 2.9).cut(
            cylinder_y(x, -19.26, 32.5, 36.0, 2.29)).cut(body))
        gauges[f"p18_pocket_{tag}_blocked_mm3"] = volume(cylinder_y(x, -19.26, 32.56, 35.92, 2.27).intersect(body))
        gauges[f"p18_pocket_{tag}_rear_wall_missing_mm3"] = volume(
            cylinder_y(x, -19.26, FLANGE_REAR_Y + 0.01, P18_POCKET_START - 0.01, 2.27).cut(body))
        gauges[f"p18_old_slot_{tag}_open_mm3"] = volume(cylinder_y(x, -19.26, 31.0, FLANGE_REAR_Y - 0.01, 2.27).intersect(
            box(x - 3, x + 3, 30.9, 32.1, -22.0, SHELF_TOP - 0.01)).cut(body))
        gauges[f"p18_bump_above_shelf_{tag}_mm3"] = volume(box(x - 2.6, x + 2.6, 30.9, FLANGE_REAR_Y - 0.01,
                                                               SHELF_TOP + 0.01, -16.6).intersect(body))
    for key, value in gauges.items():
        if abs(value) > 1e-3:
            failures.append({"check": key, "mm3": value})
    b, bb = bounds(body), bounds(base)
    if not all(b[2 * i] >= bb[2 * i] - 1e-3 and b[2 * i + 1] <= bb[2 * i + 1] + 1e-3 for i in range(3)):
        failures.append({"check": "envelope grew", "body": b, "baseline": bb})
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    _, _, envelope = fan_parts()
    air = {"heatsink_fins": envelope.distance(hotend.Solids()[3]), "heating_assembly_plate": envelope.distance(hotend.Solids()[0]),
           "apron": envelope.distance(body.intersect(box(-10, 9.3, 31.0, 38.0, -48.0, -28.4))),
           "p18": envelope.distance(load("P18_Tool_docking_backplate_3010"))}
    return failures, gauges, hits, air


def min_distance(a, b, cutoff=4.0):
    """Exact minimum distance over solid pairs whose boxes are within ``cutoff`` (None if none are)."""
    best = None
    for s in a.Solids():
        ia = fast_geometry.index_of(s)
        for t in b.Solids():
            ib = fast_geometry.index_of(t)
            gap = fast_geometry.axis_gap(ia, ib)
            if gap > cutoff or (best is not None and gap >= best):
                continue
            hit = fast_geometry.solid_distance(ia, ib, best=float("inf") if best is None else best)
            if hit is not None:
                best = hit[0]
    return best


def motion_checks(body, inserts):
    results = {}
    dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")
    carriage = compound([load(n) for n in REFERENCES if n != "P18_Tool_docking_backplate_3010"])
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    hardware = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")
    p18 = load("P18_Tool_docking_backplate_3010")
    fan, screws, envelope = fan_parts()
    changed = compound([body, fan, screws, inserts])
    tool = compound([body, hotend, hardware, fan, screws, inserts, p18])
    print("Dock approach/withdrawal and carriage retreat, 0.5 mm samples over 60 mm", flush=True)
    dock_hits, retreat_hits = [], []
    for step in range(121):
        dy = 0.5 * step
        hit = translated_hits(changed, {"Dock": dock}, (0, -dy, 0))
        if hit:
            dock_hits.append({"tool_y_mm": -dy, "hits": hit})
        hit = translated_hits(changed, {"Carriage": carriage}, (0, dy, 0))
        if hit:
            retreat_hits.append({"carriage_y_mm": -dy, "hits": hit})
    results.update(dock_samples=121, dock_hits=dock_hits, carriage_retreat_hits=retreat_hits)
    print("Removed-hotend service path", flush=True)
    removable = compound(hotend.Solids()[3:5])
    fixed = compound([body, hardware, envelope, screws, inserts])
    path = [(i * 0.25, 0) for i in range(17)] + [(4, i) for i in range(1, 41)]
    service_hits = []
    for down, rear in path:
        hit = translated_hits(removable, {"Fixed": fixed}, (0, -rear, -down))
        if hit:
            service_hits.append({"down_mm": down, "rear_mm": rear, "hits": hit})
    results.update(hotend_service_samples=len(path), hotend_service_hits=service_hits)
    print("Mixed parked neighbours at 37.3 mm pitch", flush=True)
    from audit_low_z_bed_clearance import load_parked_variants
    red = load_parked_variants()["RedLizard"]
    neighbour_checks = []
    for label, target in (("Bambu R30", compound([tool, dock])), ("RedLizard (R21 snapshot)", compound([red["tool"], red["dock"]]))):
        for dx in (-PITCH, PITCH):
            hits = []
            for sample in range(61):
                hit = translated_hits(tool, {"Neighbour": target.translate((dx, 0, 0))}, (0, -sample, 0))
                if hit:
                    hits.append({"withdrawal_mm": sample, "hits": hit})
            neighbour_checks.append({"variant": label, "offset_x_mm": dx, "samples": 61, "hits": hits})
    results["neighbour_checks"] = neighbour_checks
    print("Minimum distances: parked neighbours and the active carriage passing them", flush=True)
    distances = {
        "parked_bambu_to_bambu_mm": min_distance(tool, tool.translate((PITCH, 0, 0))),
        "parked_bambu_fan_side_to_redlizard_mm": min_distance(tool, red["tool"].translate((PITCH, 0, 0))),
        "parked_redlizard_fan_side_to_bambu_mm": min_distance(tool, red["tool"].translate((-PITCH, 0, 0))),
    }
    worst = None
    for dy in (0, -1, -3, -10, -30, -60):
        for dx in (-PITCH, PITCH):
            d = min_distance(carriage.translate((0, dy, 0)), tool.translate((dx, 0, 0)))
            if d is not None and (worst is None or d < worst["mm"]):
                worst = {"mm": d, "neighbour_dx_mm": dx, "carriage_dy_mm": dy}
    distances["active_carriage_to_parked_bambu_min"] = worst
    results["minimum_distances"] = distances
    failed = bool(dock_hits or retreat_hits or service_hits or any(c["hits"] for c in neighbour_checks)
                  or worst is None or worst["mm"] < 0.5)
    return results, failed


def export_all(body, inserts, report):
    step = STEP / f"{NAME}.step"
    stl = STL / f"{NAME}.stl"
    cq.exporters.export(body, str(step))
    cq.exporters.export(body, str(stl), tolerance=0.03, angularTolerance=0.1)
    back = single(cq.importers.importStep(str(step)).val(), "print STEP readback")
    if abs(volume(back) - volume(body)) > 1e-3:
        raise ValueError("Print STEP readback volume mismatch")
    mesh = trimesh.load_mesh(stl)
    if not (mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split(only_watertight=False)) == 1):
        raise ValueError("Print STL is not one watertight, consistently wound shell")
    fan, screws, _ = fan_parts()
    insert_path = STEP / "Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW.step"
    cq.exporters.export(inserts, str(insert_path))
    fan_path = STEP / "Bambu_Fan_2510_And_Screws_R30_REVIEW.step"
    cq.exporters.export(compound([fan, screws]), str(fan_path))
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    hardware = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")
    tool_path = STEP / "30_Bambu_Compact_Toolhead_REVIEW.step"
    tool = cq.Assembly(name="30 Bambu compact toolhead")
    for part, label, color in (
            (body, "R30_Bambu_Print", (0.95, 0.67, 0.1)), (hotend, "Bambu_Hotend", (0.72, 0.72, 0.75)),
            (hardware, "Hotend_M2p5_Hardware", (0.2, 0.7, 0.3)), (fan, "Fan_2510", (0.16, 0.18, 0.22)),
            (screws, "Fan_M2p5x14_Screws", (0.35, 0.35, 0.38)), (inserts, "Fan_M2p5_L4_Inserts", (0.8, 0.55, 0.2))):
        tool.add(part, name=label, color=cq.Color(*color))
    tool.export(str(tool_path))
    if len(cq.importers.importStep(str(tool_path)).val().Solids()) != 20:
        raise ValueError("Toolhead STEP readback does not contain 20 solids")
    # Complete carriage/dock assembly: replace the revision-21 print, its two L3 fan inserts,
    # the fan and the two fan screws; everything else is reused unchanged.
    source = load(SOURCE_ASSEMBLY)
    same = lambda a, b: max(abs(p - q) for p, q in zip(bounds(a), bounds(b))) < 1e-3
    old = {
        "print": [load(SOURCE_BODY)],
        "inserts": load("Tool2510_Two_Inner_Entry_L3_Heatsets_REVIEW").Solids(),
        "fan": load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW").Solids(),
        "screws": load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW").Solids(),
    }
    replaced = {k: [i for i, s in enumerate(source.Solids()) if any(same(s, v) for v in vs)] for k, vs in old.items()}
    if [len(replaced[k]) for k in ("print", "inserts", "fan", "screws")] != [1, 2, 1, 2]:
        raise ValueError(f"Ambiguous replacement in the complete assembly: {replaced}")
    skip = {i for v in replaced.values() for i in v}
    before_parts = compound([source.Solids()[i] for i in sorted(skip)])
    after_parts = compound([body, inserts, fan, screws])
    print("Regression against unchanged complete-assembly solids", flush=True)
    regression = []
    for i, s in enumerate(source.Solids()):
        if i in skip:
            continue
        before = sum(overlaps(before_parts, {"S": s}).values())
        after = sum(overlaps(after_parts, {"S": s}).values())
        regression.append({"solid_index": i, "increase_mm3": after - before})
        if after - before > 1e-3:
            raise ValueError(f"New intersection with complete-assembly solid {i}: {after - before}")
    full_path = STEP / "30_Bambu_Compact_Complete_REVIEW.step"
    full = cq.Assembly(name="30 Bambu compact toolhead - complete carriage and dock")
    for part, label, color in ((body, "R30_Bambu_Print", (0.95, 0.67, 0.1)),
                               (inserts, "Fan_M2p5_L4_Inserts", (0.8, 0.55, 0.2)),
                               (fan, "Fan_2510", (0.16, 0.18, 0.22)), (screws, "Fan_M2p5x14_Screws", (0.35, 0.35, 0.38))):
        full.add(part, name=label, color=cq.Color(*color))
    for i, s in enumerate(source.Solids()):
        if i not in skip:
            full.add(s, name=f"Unchanged_Reference_{i}", color=cq.Color(0.55, 0.57, 0.6))
    full.export(str(full_path))
    if len(cq.importers.importStep(str(full_path)).val().Solids()) != len(source.Solids()):
        raise ValueError("Complete assembly readback solid count changed")
    report["complete_assembly"] = {"solids": len(source.Solids()), "regression_checks": len(regression),
                                   "max_increase_mm3": max(r["increase_mm3"] for r in regression)}
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)}
                         for p in (step, stl, insert_path, fan_path, tool_path, full_path)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("geometry", "full"), default="full")
    args = parser.parse_args()
    log = []
    print("Building revision 30 from revision 22", flush=True)
    base, body, inserts = build_body(log)
    print("Static checks", flush=True)
    failures, gauges, hits, air = static_checks(base, body)
    report = {
        "status": "LOCAL_CAD_REVIEW_NOT_PRINT_THERMAL_OR_MACHINE_QUALIFICATION",
        "supersedes": "Revision 29 (fan 1.65 mm further out, rear shelf strip near the carriage, open P18 bore slots)",
        "baseline": {"file": f"{BASE}.step", "sha256": sha(STEP / f"{BASE}.step")},
        "operations": log, "feature_gauges_mm3": gauges, "protected_intersections_mm3": hits,
        "fan_air_gaps_mm": air, "bounds_mm": bounds(body), "baseline_bounds_mm": bounds(base),
        "body_volume_mm3": volume(body), "net_change_vs_r22_mm3": volume(body) - volume(base),
        "static_failures": failures,
    }
    if args.stage == "geometry":
        preview = primitives.WORK / f"{NAME}_preview.step"
        cq.exporters.export(body, str(preview))
        print(json.dumps({k: v for k, v in report.items() if k != "operations"}, indent=1))
        print("Preview:", preview)
        return
    if failures:
        raise ValueError(f"Static check failures: {failures}")
    motion, failed = motion_checks(body, inserts)
    report["motion"] = motion
    if failed:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2) + "\n")
        raise ValueError(f"Motion/clearance failures; see {REPORT}")
    export_all(body, inserts, report)
    report["design"] = {
        "fan_center_mm": [16.45 + FAN_DX, 25.5, -35.3],
        "fan_seat_x_mm": FAN_SEAT_X, "shelf_fan_face_x_mm": SHELF_FACE_X,
        "fan_air_gap_to_heatsink_fins_mm": air["heatsink_fins"],
        "fan_screw_head_outer_x_mm": bounds(fan_parts()[1])[1],
        "fan_inserts": "M2.5 L4 OD3.5, installed from the fan side before fitting the fan; 3.1 mm pilots 4.5 mm deep with 0.3 mm entry chamfer; existing M2.5x14 low-head screws engage 4 mm.",
        "lower_p18_inserts": "M3 x 3 mm heat-set inserts in 4.56 mm pockets 3.38 mm deep, closed by a 0.5 mm rear wall inside the flange. The upper P18 pair is unchanged.",
        "inlet_socket": "8 mm OD sleeve, 5.25 mm socket over the 4.75 mm inlet tube (0.25 mm radial, 0.20 mm axial clearance), 0.92 mm overlap below the inlet top; 2.3 mm guide with 45-degree funnel into the existing 4.2 mm bore.",
        "front_neck": "Restored P17 front neck under P18; stem wire trough kept open.",
    }
    report["limitations"] = [
        "Fixed-rack low-Z bed collision and inherited probe-cable entry issue remain unresolved.",
        "Front fan insert keeps a 0.65 mm wall to the apron front face (fan hole 2.5 mm from the fan edge).",
        "Red Lizard neighbour checks use the revision-21 parked snapshot; the Red Lizard shelf strip is removed separately (verification_redlizard_strip_trim_r30.json).",
        "Insert pullout, printed strength, thermal behaviour at the inlet socket and fan cooling at the 1.5 mm gap are unqualified.",
    ]
    (ROOT / REPORT).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("operations",)}, indent=1))


if __name__ == "__main__":
    main()

