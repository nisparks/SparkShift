"""Bambu toolhead revision 29: clean rebuild from revision 22.

Supersedes the revision 25-28 patch series, which accumulated boxes, wedges and
reliefs on top of each other. This starts again from the last coherent body
(revision 22) and applies only five deliberate changes:

1. A socket sleeve that encloses the hotend inlet tube, so the filament path has
   no exposed span between the printed guide and the hotend.
2. The original P17 front neck between the shelf, the front apron and P18, which
   the Bambu adaptation lost. It closes the through-slot at the front while
   keeping the stem wire trough and the two P18 insert bores open.
3. The cross-body fan-insert corridors are filled back to the original flat shelf
   underside and apron top, removing the open grooves and razor-thin skins.
4. Two closed round fan bosses with fan-side M2.5 L4 heat-set pilots. The fan
   seats on the boss faces at its modeled position.
5. The 0.05 mm membrane left over the fan recess is removed.

Run with --stage geometry for a fast build and static checks, or with no
arguments for the full motion, regression and export pass.
"""

import argparse
import hashlib
import json

import cadquery as cq
import trimesh

from audit_tool_owned_2510 import bounds, compound, overlaps
from build_modular_toolhead import ROOT, STEP, STL, box, cylinder_y, load, primitives, volume
from build_refined_docking_review import translated_hits

NAME = "Bambu_Clean_Rebuild_R29_REVIEW"
BASE = "Bambu_One_Piece_Shelf_Clearance_R22_REVIEW"
SOURCE_ASSEMBLY = "21_Bambu_Toolhead_And_Closed_Panel_Dock_REVIEW"
SOURCE_BODY = "Bambu_One_Piece_Docking_Audited_REVIEW"
INLET_XY = (0.0, 22.7)
FAN_AXES_Y = (15.5, 35.5)
FAN_AXIS_Z = -25.3
FAN_SEAT_X = 11.45
P18_BOTTOM_Z = -22.45
NECK_FRONT_Y = 35.93
FLANGE_BOTTOM_Z = -19.2794
APRON = (-9.25, 9.25, 31.1, 37.9, -65.93, -24.0)
SHELF_LOWER = (-13.5, 11.2, 11.5, 32.05, -26.0, -22.5)
REFERENCES = (
    "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
    "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
    "Core_With_Restrained_AHG_Lead_References_REVIEW",
)
# Every intended change lies inside one of these regions; anything else is a defect.
EDIT_ZONES = {
    "front_seat_and_neck": (-9.3, 11.8, 31.0, 38.8, -28.8, FLANGE_BOTTOM_Z + 0.01),
    "corridor_15p5": (-13.6, 11.8, 11.0, 20.0, -28.8, -22.4),
    "corridor_35p5_apron_top": (-9.3, 11.8, 32.0, 38.0, -28.8, -23.0),
    "inlet_socket": (-4.9, 4.9, 17.7, 27.7, -30.5, -25.9),
    "fan_recess_membrane": (11.19, 15.21, 12.7, 32.21, -22.61, -22.49),
}


def cyl_x(y, z, x0, x1, r):
    return cq.Solid.makeCylinder(r, x1 - x0, cq.Vector(x0, y, z), cq.Vector(1, 0, 0))


def cyl_z(x, y, z0, z1, r):
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))


def cone_x(y, z, x0, r0, x1, r1):
    return cq.Solid.makeCone(r0, r1, x1 - x0, cq.Vector(x0, y, z), cq.Vector(1, 0, 0))


def cone_z(x, y, z0, r0, z1, r1):
    return cq.Solid.makeCone(r0, r1, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def single(shape, label):
    solids = shape.Solids()
    if len(solids) != 1 or not solids[0].isValid():
        raise ValueError(f"{label}: expected one valid solid, got {len(solids)}")
    return solids[0]


def add(body, stock, label, log):
    before = volume(body)
    result = single(body.fuse(stock).clean(), label)
    gained = volume(result) - before
    if gained < -1e-3 or gained > volume(stock) + 1e-3:
        raise ValueError(f"{label}: nonphysical union gain {gained}")
    log.append({"operation": label, "added_mm3": round(gained, 4)})
    return result


def remove(body, cutter, label, log):
    before = volume(body)
    result = single(body.cut(cutter).clean(), label)
    removed = before - volume(result)
    if removed < -1e-3 or removed > volume(cutter) + 1e-3:
        raise ValueError(f"{label}: nonphysical cut {removed}")
    log.append({"operation": label, "removed_mm3": round(removed, 4)})
    return result


def neck_stock():
    neck = box(-9.25, 9.25, 32.05, APRON[3], APRON[5], P18_BOTTOM_Z).fuse(
        box(-9.0, 9.0, 32.05, NECK_FRONT_Y, P18_BOTTOM_Z, FLANGE_BOTTOM_Z))
    # The P17 stem wire trough (X+/-2.55) stays open from the apron top upward.
    return neck.cut(box(-2.55, 2.55, 32.0, NECK_FRONT_Y, APRON[5], FLANGE_BOTTOM_Z + 0.1))


def build_body(log):
    base = single(load(BASE), "revision-22 baseline")
    body = base
    # 1. Clear legacy fan-seat stock outside the shelf and apron; clean bosses replace it.
    body = remove(body, box(9.25, 11.8, 32.05, 38.8, -28.8, P18_BOTTOM_Z),
                  "legacy front seat block and ring outside apron", log)
    body = remove(body, box(9.25, 11.8, 31.0, 32.05, -28.8, -26.0),
                  "legacy front ring below shelf corner", log)
    body = remove(body, box(5.0, 11.8, 11.0, 20.0, -28.8, -26.0),
                  "legacy rear ring below shelf", log)
    body = remove(body, box(11.2, 15.2, 12.75, 32.2, -22.6, -22.5),
                  "0.05 mm membrane over fan recess", log)
    body = remove(body, box(5.0, APRON[1] + 0.05, APRON[3], 38.2, -28.8, -22.4),
                  "0.1 mm legacy ring remnant proud of apron front face", log)
    # 2. Restore the flat shelf underside and apron top through the old insert corridors.
    domain = box(*SHELF_LOWER).fuse(box(*APRON))
    for y in FAN_AXES_Y:
        corridor = cyl_x(y, FAN_AXIS_Z, -15.35, 7.45, 2.2)
        body = add(body, corridor.intersect(domain), f"restore shelf/apron through corridor Y{y}", log)
    # 3. Restore the P17 front neck; recut the two P18 insert bores as full round holes.
    body = add(body, neck_stock(), "restored P17 front neck", log)
    # Old hotend-clamp counterbores (r3, X+/-6, Z-22.75) left crescents in the apron top that the
    # neck would otherwise seal in as internal voids.
    for x in (-6.0, 6.0):
        body = add(body, cylinder_y(x, -22.75, 31.1, 34.2, 3.2).intersect(box(*APRON)),
                   f"fill legacy counterbore crescent X{x:+.0f}", log)
    for x in (-6.0, 6.0):
        body = remove(body, cylinder_y(x, -19.26, 31.0, 37.0, 2.28), f"P18 insert bore X{x:+.0f}", log)
    # 4. Closed fan bosses; the fan seats on their faces at X11.45. The front boss is bridged
    #    to the shelf corner so the fan-side face runs continuously from the shelf to the boss.
    body = add(body, box(APRON[1], SHELF_LOWER[1], SHELF_LOWER[3], 35.5, SHELF_LOWER[4], P18_BOTTOM_Z),
               "shelf-to-front-boss bridge", log)
    inserts = []
    for y in FAN_AXES_Y:
        boss = cyl_x(y, FAN_AXIS_Z, 7.2, FAN_SEAT_X, 3.0).fuse(
            cone_x(y, FAN_AXIS_Z, 5.7, 1.5, 7.2, 3.0))
        boss = boss.intersect(box(5.0, FAN_SEAT_X, SHELF_LOWER[2], APRON[3], -28.3, P18_BOTTOM_Z))
        body = add(body, boss, f"fan boss Y{y}", log)
    for y in FAN_AXES_Y:
        body = remove(body, cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.5, FAN_SEAT_X + 0.01, 1.55),
                      f"L4 heat-set pilot Y{y}", log)
        body = remove(body, cone_x(y, FAN_AXIS_Z, FAN_SEAT_X - 0.3, 1.55, FAN_SEAT_X + 0.01, 1.86),
                      f"pilot entry chamfer Y{y}", log)
        inserts.append(cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.0, FAN_SEAT_X, 1.75).cut(
            cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.01, FAN_SEAT_X + 0.01, 1.05)))
    # 5. Inlet socket sleeve with a 45-degree root blend and a chamfered lower edge.
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
    return dict(
        refs, Hotend=load("Tool2510_Reversed_Bambu_Reference_REVIEW"),
        Fan_Envelope=box(11.45, 21.45, 13, 38, -47.8, -22.8),
        Fan_Screws=load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW"),
        Hotend_Screws=compound(hardware[i] for i in (1, 4, 7)),
        Hotend_Washers=compound(hardware[i] for i in (2, 5)))


def inside(b, zone, tol=0.002):
    return (b[0] >= zone[0] - tol and b[1] <= zone[1] + tol and b[2] >= zone[2] - tol and
            b[3] <= zone[3] + tol and b[4] >= zone[4] - tol and b[5] <= zone[5] + tol)


def static_checks(base, body):
    failures = []
    if len(body.Shells()) != 1:
        failures.append({"check": "internal voids (extra shells)", "shells": len(body.Shells())})
    hits = overlaps(body, protected_parts())
    if hits:
        failures.append({"check": "protected-part interference", "hits": hits})
    unexplained = []
    for kind, diff in (("added", body.cut(base)), ("removed", base.cut(body))):
        for s in diff.Solids():
            if volume(s) < 1e-4:
                continue
            b = bounds(s)
            if not any(inside(b, z) for z in EDIT_ZONES.values()):
                unexplained.append({"kind": kind, "mm3": volume(s), "bounds": b})
    if unexplained:
        failures.append({"check": "change outside declared edit zones", "solids": unexplained})
    x0, y0 = INLET_XY
    neck_gauge = neck_stock()
    for x in (-6.0, 6.0):
        neck_gauge = neck_gauge.cut(cylinder_y(x, -19.26, 30.0, 38.0, 2.3))
    # The front fan pilot legitimately breaks into the bottom 0.25 mm of the neck.
    neck_gauge = neck_gauge.cut(cyl_x(35.5, FAN_AXIS_Z, FAN_SEAT_X - 4.6, FAN_SEAT_X + 0.1, 1.9))
    gauges = {
        "front_neck_unfilled_mm3": volume(neck_gauge.cut(body)),
        "wire_trough_blocked_mm3": volume(box(-2.5, 2.5, 30.1, 35.9, -23.95, -19.5).intersect(body)),
        "wire_trough_bottom_entry_blocked_mm3": volume(box(-0.7, 0.7, 28.3, 31.0, -26.5, -24.1).intersect(body)),
        "membrane_remaining_mm3": volume(box(FAN_SEAT_X + 0.01, 15.1, 12.8, 32.0, -22.58, -22.505).intersect(body)),
        "socket_wall_missing_mm3": volume(cyl_z(x0, y0, -29.85, -26.1, 3.9).cut(
            cyl_z(x0, y0, -29.86, -26.09, 2.7)).cut(body)),
        "socket_blocked_mm3": volume(cyl_z(x0, y0, -30.39, -29.3, 2.6).intersect(body)),
        "filament_path_blocked_mm3": volume(cyl_z(x0, y0, -29.48, 48.0, 0.9).intersect(body)),
    }
    shelf_gauge = box(*SHELF_LOWER).cut(cyl_z(0, 22.68, -27, -22, 2.2)).cut(
        box(-2.6, 2.6, 28.1, 32.1, -27, -22))
    for y in FAN_AXES_Y:
        tag = f"{y:g}".replace(".", "p")
        corridor = cyl_x(y, FAN_AXIS_Z, -13.4, 6.9, 2.19)
        gauges[f"corridor_{tag}_open_mm3"] = volume(corridor.intersect(
            shelf_gauge.fuse(box(*APRON))).cut(body))
        gauges[f"boss_{tag}_wall_missing_mm3"] = volume(cyl_x(y, FAN_AXIS_Z, 7.0, FAN_SEAT_X - 0.35, 2.3).cut(
            cyl_x(y, FAN_AXIS_Z, 6.99, FAN_SEAT_X, 1.76)).cut(body))
        gauges[f"pilot_{tag}_blocked_mm3"] = volume(
            cyl_x(y, FAN_AXIS_Z, FAN_SEAT_X - 4.49, FAN_SEAT_X, 1.54).intersect(body))
    for x in (-6.0, 6.0):
        gauges[f"p18_bore_x{x:+.0f}_wall_missing_mm3"] = volume(cylinder_y(x, -19.26, 32.1, 35.9, 2.9).cut(
            cylinder_y(x, -19.26, 32.0, 36.0, 2.29)).cut(body))
        gauges[f"p18_bore_x{x:+.0f}_blocked_mm3"] = volume(
            cylinder_y(x, -19.26, 31.01, 35.9, 2.27).intersect(body))
    for key, value in gauges.items():
        if abs(value) > 1e-3:
            failures.append({"check": key, "mm3": value})
    b, bb = bounds(body), bounds(base)
    if not inside(b, bb, 0.001):
        failures.append({"check": "envelope grew", "body": b, "baseline": bb})
    return failures, gauges, hits


def motion_checks(body, inserts):
    results = {}
    dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")
    carriage = compound([load(n) for n in REFERENCES if n != "P18_Tool_docking_backplate_3010"])
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    hardware = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")
    fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
    screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")
    fan_box = box(11.45, 21.45, 13, 38, -47.8, -22.8)
    print("Dock approach/withdrawal and carriage retreat, 0.5 mm samples over 60 mm", flush=True)
    dock_hits, retreat_hits = [], []
    for step in range(121):
        dy = 0.5 * step
        hit = translated_hits(body, {"Dock": dock}, (0, -dy, 0))
        if hit:
            dock_hits.append({"tool_y_mm": -dy, "hits": hit})
        # Carriage moving -Y away from the parked tool == tool moving +Y relative to it.
        hit = translated_hits(body, {"Carriage": carriage}, (0, dy, 0))
        if hit:
            retreat_hits.append({"carriage_y_mm": -dy, "hits": hit})
    results["dock_samples"] = 121
    results["dock_hits"] = dock_hits
    results["carriage_retreat_hits"] = retreat_hits
    print("Removed-hotend service path", flush=True)
    removable = compound(hotend.Solids()[3:5])
    fixed = compound([body, hardware, fan_box, screws, inserts])
    service_hits = []
    path = [(i * 0.25, 0) for i in range(17)] + [(4, i) for i in range(1, 41)]
    for down, rear in path:
        hit = translated_hits(removable, {"Fixed": fixed}, (0, -rear, -down))
        if hit:
            service_hits.append({"down_mm": down, "rear_mm": rear, "hits": hit})
    results["hotend_service_samples"] = len(path)
    results["hotend_service_hits"] = service_hits
    print("Mixed parked neighbours at 37.3 mm pitch", flush=True)
    from audit_low_z_bed_clearance import load_parked_variants
    neighbours = load_parked_variants()
    tool = compound([body, hotend, hardware, fan, screws, inserts])
    neighbour_checks = []
    for label, target in (
            ("Bambu", compound([tool, dock])),
            ("RedLizard", compound([neighbours["RedLizard"]["tool"], neighbours["RedLizard"]["dock"]]))):
        for dx in (-37.3, 37.3):
            hits = []
            for sample in range(61):
                hit = translated_hits(tool, {"Neighbour": target.translate((dx, 0, 0))}, (0, -sample, 0))
                if hit:
                    hits.append({"withdrawal_mm": sample, "hits": hit})
            neighbour_checks.append({"variant": label, "offset_x_mm": dx, "samples": 61, "hits": hits})
    results["neighbour_checks"] = neighbour_checks
    failed = (dock_hits or retreat_hits or service_hits or any(c["hits"] for c in neighbour_checks))
    return results, bool(failed)


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
    insert_path = STEP / "Bambu_Fan_Side_M2p5_L4_Inserts_R29_REVIEW.step"
    cq.exporters.export(inserts, str(insert_path))
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    hardware = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")
    fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
    screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")
    tool_path = STEP / "29_Bambu_Clean_Toolhead_REVIEW.step"
    tool = cq.Assembly(name="29 Bambu clean toolhead")
    for part, label, color in (
            (body, "R29_Bambu_Print", (0.95, 0.67, 0.1)), (hotend, "Bambu_Hotend", (0.72, 0.72, 0.75)),
            (hardware, "Hotend_M2p5_Hardware", (0.2, 0.7, 0.3)), (fan, "Fan_2510", (0.16, 0.18, 0.22)),
            (screws, "Fan_M2p5x14_Screws", (0.35, 0.35, 0.38)), (inserts, "Fan_M2p5_L4_Inserts", (0.8, 0.55, 0.2))):
        tool.add(part, name=label, color=cq.Color(*color))
    tool.export(str(tool_path))
    if len(cq.importers.importStep(str(tool_path)).val().Solids()) != 20:
        raise ValueError("Toolhead STEP readback does not contain 20 solids")
    # Complete carriage/dock assembly: replace the revision-21 print and its two L3 inserts.
    source = load(SOURCE_ASSEMBLY)
    source_body = load(SOURCE_BODY)
    old_inserts = load("Tool2510_Two_Inner_Entry_L3_Heatsets_REVIEW").Solids()
    same = lambda a, b: max(abs(p - q) for p, q in zip(bounds(a), bounds(b))) < 1e-3
    replace_body = [i for i, s in enumerate(source.Solids()) if same(s, source_body)]
    replace_inserts = [i for i, s in enumerate(source.Solids()) if any(same(s, v) for v in old_inserts)]
    if len(replace_body) != 1 or len(replace_inserts) != 2:
        raise ValueError("Ambiguous print/insert replacement in the complete assembly")
    skip = set(replace_body + replace_inserts)
    regression = []
    print("Regression against unchanged complete-assembly solids", flush=True)
    for i, s in enumerate(source.Solids()):
        if i in skip:
            continue
        before = sum(overlaps(source_body, {"S": s}).values())
        after = sum(overlaps(body, {"S": s}).values())
        regression.append({"solid_index": i, "increase_mm3": after - before})
        if after - before > 1e-3:
            raise ValueError(f"New intersection with complete-assembly solid {i}: {after - before}")
    full_path = STEP / "29_Bambu_Clean_Complete_REVIEW.step"
    full = cq.Assembly(name="29 Bambu clean rebuild - complete carriage and dock")
    full.add(body, name="R29_Bambu_Print", color=cq.Color(0.95, 0.67, 0.1))
    full.add(inserts, name="Fan_M2p5_L4_Inserts", color=cq.Color(0.8, 0.55, 0.2))
    for i, s in enumerate(source.Solids()):
        if i not in skip:
            full.add(s, name=f"Unchanged_Reference_{i}", color=cq.Color(0.55, 0.57, 0.6))
    full.export(str(full_path))
    if len(cq.importers.importStep(str(full_path)).val().Solids()) != len(source.Solids()):
        raise ValueError("Complete assembly readback solid count changed")
    report["complete_assembly"] = {"solids": len(source.Solids()), "regression_checks": len(regression),
                                   "max_increase_mm3": max(r["increase_mm3"] for r in regression)}
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)}
                         for p in (step, stl, insert_path, tool_path, full_path)]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("geometry", "full"), default="full")
    args = parser.parse_args()
    log = []
    print("Building revision 29 from revision 22", flush=True)
    base, body, inserts = build_body(log)
    print("Static checks", flush=True)
    failures, gauges, hits = static_checks(base, body)
    report = {
        "status": "LOCAL_CAD_REVIEW_NOT_PRINT_THERMAL_OR_MACHINE_QUALIFICATION",
        "supersedes": "Revisions 25-28 (patch series rejected on visual review)",
        "baseline": {"file": f"{BASE}.step", "sha256": sha(STEP / f"{BASE}.step")},
        "operations": log, "feature_gauges_mm3": gauges, "protected_intersections_mm3": hits,
        "bounds_mm": bounds(body), "baseline_bounds_mm": bounds(base),
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
        (ROOT / "verification_bambu_clean_r29.json").write_text(json.dumps(report, indent=2) + "\n")
        raise ValueError("Motion check failures; see verification_bambu_clean_r29.json")
    export_all(body, inserts, report)
    report["design"] = {
        "fan_center_mm": [16.45, 25.5, -35.3],
        "fan_seat_x_mm": FAN_SEAT_X,
        "fan_inserts": "M2.5 L4 OD3.5, installed from the fan side before fitting the fan; 3.1 mm pilots 4.5 mm deep with 0.3 mm entry chamfer; existing M2.5x14 low-head screws engage 4 mm.",
        "front_insert_wall_mm": 0.65,
        "inlet_socket": "8 mm OD sleeve, 5.25 mm socket over the 4.75 mm inlet tube (0.25 mm radial, 0.20 mm axial clearance), 0.92 mm overlap below the inlet top; 2.3 mm guide with 45-degree funnel into the existing 4.2 mm bore.",
        "front_neck": "Restored P17 front neck: X+/-9.25 from the apron top to the P18 underside plane, X+/-9 up to the coupling flange; stem wire trough X+/-2.55 kept open; P18 insert bores now fully enclosed.",
    }
    report["limitations"] = [
        "Fixed-rack low-Z bed collision and inherited probe-cable entry issue remain unresolved.",
        "Front fan insert has a 0.65 mm wall to the apron front face, as in the inherited design.",
        "Insert pullout, printed strength, thermal behaviour at the inlet socket and fan cooling are unqualified.",
    ]
    (ROOT / "verification_bambu_clean_r29.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("operations", "motion")}, indent=1))


if __name__ == "__main__":
    main()
