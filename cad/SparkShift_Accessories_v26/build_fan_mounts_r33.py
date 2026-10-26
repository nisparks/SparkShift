"""Toolhead revision 33: a third Bambu fan screw and a solid Red Lizard fan wall.

Bambu: the fan hung from its two upper holes; the lower edge was free. A third R3 boss on the
apron side face at the fan's lower-front hole (Y35.5, Z-45.3) takes a third fan-side M2.5 L4
heat-set insert and M2.5x14 screw, so the fan is held at three corners.

Red Lizard: the fan hung from a 4 x 5 mm column (X7.45..11.45, Y33..38) whose only joint to the
shelf was a 1.48 mm tab overlapping the shelf by 0.55 mm. The neck under P18 was missing, so
both lower P18 bores were half open at the bottom. Revision 33:
1. Restores the front neck under P18 as on the Bambu (revision 29), keeping the wire trough
   open, and recuts the lower P18 bores as closed M3 x 3 pockets as on the Bambu (revision 30).
2. Replaces the column with an 8.6 x 5.45 mm fan wall (X3.0..11.6, Y32.45..37.9) that runs up
   into the neck and seats the fan on its full height.
3. Moves both fan inserts from inner-entry L3 to fan-side M2.5 L4, like the Bambu.

The fan's rear holes cannot take a screw on the Red Lizard: an insert there would overlap the
heatsink top by about 2.8 mm.

Every check runs on fast_geometry, so the full pass takes minutes.
"""

import json
import time

import cadquery as cq
import trimesh

import fast_geometry
from audit_low_z_bed_clearance import load_parked_variants
from audit_tool_owned_2510 import bounds, compound, overlaps
from build_bambu_clean_r29 import (APRON, FAN_AXIS_Z, FLANGE_BOTTOM_Z, NECK_FRONT_Y, P18_BOTTOM_Z, add, cone_x,
                                   cyl_x, remove, sha, single)
from build_bambu_clean_r30 import FAN_SEAT_X, P18_POCKET_START, PITCH, fan_parts
from build_carriage_lowered_mounts_r31 import NAMES as R31, confined, labelled, nearest
from build_modular_toolhead import ROOT, STEP, STL, box, cylinder_y, load, volume
from build_refined_docking_review import translated_hits
from build_side_clearance_r32 import COMPLETE as R32_COMPLETE, VARIANTS as R32

FRONT_Y = 35.5
LOWER_Z = FAN_AXIS_Z - 20.0
RL_SEAT_X = 11.6
RL_SHELF_BOTTOM = -24.2794048
RL_WALL = (3.0, RL_SEAT_X, 32.45, APRON[3], -48.3, P18_BOTTOM_Z)
NAMES = {
    "bambu": "Bambu_Three_Screw_Fan_R33_REVIEW",
    "bambu_inserts": "Bambu_Fan_Side_M2p5_L4_Inserts_R33_REVIEW",
    "bambu_fan": "Bambu_Fan_2510_And_Three_Screws_R33_REVIEW",
    "bambu_toolhead": "33_Bambu_Three_Screw_Toolhead_REVIEW",
    "bambu_complete": "33_Bambu_Three_Screw_Complete_REVIEW",
    "redlizard": "RedLizard_Fan_Wall_R33_REVIEW",
    "redlizard_inserts": "RedLizard_Fan_Side_M2p5_L4_Inserts_R33_REVIEW",
    "redlizard_toolhead": "33_RedLizard_Fan_Wall_Toolhead_REVIEW",
}
REPORT = "verification_fan_mounts_r33.json"
CARRIAGE = (R31["core"], R31["p22"], R31["hardware"], "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
            "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount")
BAMBU_ZONES = [(5.0, 9.9, 32.3, 38.0, -48.0, -42.2)]
RL_ZONES = [(-9.3, 11.7, 32.0, 38.25, -48.4, -16.9)]
DY = (0, -1, -3, -10, -30)


def l4_insert(y, z, seat_x):
    return cyl_x(y, z, seat_x - 4.0, seat_x, 1.75).cut(cyl_x(y, z, seat_x - 4.01, seat_x + 0.01, 1.05))


def pilot(y, z, seat_x):
    return cyl_x(y, z, seat_x - 4.5, seat_x + 0.01, 1.55).fuse(cone_x(y, z, seat_x - 0.3, 1.55, seat_x + 0.01, 1.86))


def rl_neck():
    neck = box(-9.25, 9.25, 32.05, APRON[3], RL_SHELF_BOTTOM, P18_BOTTOM_Z).fuse(
        box(-9.0, 9.0, 32.05, NECK_FRONT_Y, P18_BOTTOM_Z, FLANGE_BOTTOM_Z))
    # The stem wire trough (X+/-2.55) stays open from below up into the stem.
    return neck.cut(box(-2.55, 2.55, 32.0, NECK_FRONT_Y, RL_SHELF_BOTTOM - 0.1, FLANGE_BOTTOM_Z + 0.1))


def red_lizard_parts():
    red = load_parked_variants()["RedLizard"]
    snap = red["tool"].Solids()
    if abs(volume(snap[0]) - 8352.19) > 0.5 or abs(bounds(snap[0])[5] - 48.74) > 0.01:
        raise ValueError("Red Lizard snapshot body is not solid 0")
    return {"hotend": compound(snap[1:14]), "fan": snap[14], "screws": compound(snap[15:17]),
            "old_inserts": compound(snap[17:19]), "p18": compound(snap[19:]), "dock": red["dock"],
            "removable": compound([*snap[1:9], snap[13]])}


def build_bambu(log):
    body = single(load(R32["Bambu"]["name"]), "revision-32 Bambu body")
    boss = cyl_x(FRONT_Y, LOWER_Z, APRON[1] - 0.5, FAN_SEAT_X, 3.0).intersect(
        box(APRON[1] - 0.6, FAN_SEAT_X, 31.0, APRON[3], -47.8, -42.0))
    body = add(body, boss, "lower-front fan boss on the apron side face", log)
    body = remove(body, pilot(FRONT_Y, LOWER_Z, FAN_SEAT_X), "L4 heat-set pilot and entry chamfer, lower front", log)
    fan, screws, _ = fan_parts()
    front = [s for s in screws.Solids() if bounds(s)[2] > 30]
    if len(front) != 1:
        raise ValueError("Could not identify the front fan screw")
    inserts = compound([*load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW").Solids(),
                        l4_insert(FRONT_Y, LOWER_Z, FAN_SEAT_X)])
    return body, inserts, compound([*screws.Solids(), front[0].translate((0, 0, LOWER_Z - FAN_AXIS_Z))])


def build_red_lizard(log):
    body = single(load(R32["RedLizard"]["name"]), "revision-32 Red Lizard body")
    body = remove(body, box(7.0, 11.7, APRON[3], 38.2, -48.5, -22.6), "old column front past the new front face", log)
    body = add(body, rl_neck(), "front neck under P18, wire trough open", log)
    body = add(body, box(*RL_WALL), "fan wall running into the neck", log)
    for x in (-6.0, 6.0):
        body = add(body, cylinder_y(x, -19.26, 32.05, P18_POCKET_START, 2.28), f"P18 pocket rear wall X{x:+.0f}", log)
        body = remove(body, cylinder_y(x, -19.26, P18_POCKET_START, 37.0, 2.28), f"M3 x 3 P18 pocket X{x:+.0f}", log)
    inserts = []
    for z in (FAN_AXIS_Z, LOWER_Z):
        body = remove(body, pilot(FRONT_Y, z, RL_SEAT_X), f"L4 heat-set pilot and chamfer Z{z}", log)
        inserts.append(l4_insert(FRONT_Y, z, RL_SEAT_X))
    return body, compound(inserts)


def insert_gauges(body, seat_x, axes, tag):
    gauges = {}
    for y, z in axes:
        key = f"{tag}_y{y:g}_z{z:g}".replace(".", "p").replace("-", "m")
        ring = cyl_x(y, z, seat_x - 4.45, seat_x - 0.35, 2.3).cut(cyl_x(y, z, seat_x - 4.46, seat_x, 1.76))
        gauges[f"{key}_insert_wall_missing_mm3"] = volume(ring.cut(body.copy()))
        gauges[f"{key}_pilot_blocked_mm3"] = volume(cyl_x(y, z, seat_x - 4.49, seat_x, 1.54).intersect(body.copy()))
    return gauges


def carriage():
    unchanged = []
    for name in CARRIAGE:
        solids = load(name).Solids()
        unchanged += [(name if len(solids) == 1 else f"{name}_{i}", s) for i, s in enumerate(solids)]
    return unchanged


def static_checks(bodies, hardware):
    failures, report = [], {}
    rl = red_lizard_parts()
    fan, _, envelope = fan_parts()
    hw = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW").Solids()
    stationary = {n: s for n, s in carriage()}
    stationary["P18"] = load("P18_Tool_docking_backplate_3010")
    # The apron's own heat-set inserts (hardware 0, 3, 6) sit in their pilots by design, as in revision 30.
    protected = {
        "Bambu": dict(stationary, Hotend=load("Tool2510_Reversed_Bambu_Reference_REVIEW"), Fan_Envelope=envelope,
                      Fan_Screws=hardware["Bambu"]["screws"], Hotend_Screws=compound(hw[i] for i in (1, 4, 7)),
                      Hotend_Washers=compound(hw[i] for i in (2, 5))),
        "RedLizard": dict({k: v for k, v in stationary.items() if k != "P18"}, Hotend=rl["hotend"],
                          Fan=rl["fan"], Fan_Screws=rl["screws"], P18_And_Magnets=rl["p18"]),
    }
    bases = {label: v["name"] for label, v in R32.items()}
    for label, body in bodies.items():
        r = {"volume_mm3": volume(body), "shells": len(body.Shells()), "valid": body.isValid(),
             "bounds_mm": bounds(body), "baseline": {"file": f"{bases[label]}.step", "sha256": sha(STEP / f"{bases[label]}.step")},
             "baseline_volume_mm3": volume(load(bases[label])), "baseline_bounds_mm": bounds(load(bases[label]))}
        if r["shells"] != 1 or not r["valid"]:
            failures.append(f"{label}: invalid body or internal void")
        # Only new contact counts: compare against the revision-32 body with the same references.
        r["intersections_mm3"] = overlaps(body, protected[label])
        r["baseline_intersections_mm3"] = overlaps(load(bases[label]), protected[label])
        new = {k: v for k, v in r["intersections_mm3"].items() if v - r["baseline_intersections_mm3"].get(k, 0.0) > 1e-3}
        if new:
            failures.append(f"{label}: new interference {new}")
        zones = BAMBU_ZONES if label == "Bambu" else RL_ZONES
        r["outside_edit_zones"] = confined(body.copy(), load(bases[label]), zones)
        if not r["outside_edit_zones"]["unchanged_outside_zones"]:
            failures.append(f"{label}: changed outside the edit zones")
        report[label] = r
    b = bodies["Bambu"]
    gauges = insert_gauges(b, FAN_SEAT_X, [(15.5, FAN_AXIS_Z), (FRONT_Y, FAN_AXIS_Z), (FRONT_Y, LOWER_Z)], "bambu")
    third = hardware["Bambu"]["inserts"].Solids()[2]
    gauges["bambu_third_insert_to_hotend_hardware_mm"] = min(third.distance(h) for h in hw)
    gauges["bambu_third_screw_in_fan_mm3"] = volume(hardware["Bambu"]["screws"].Solids()[2].intersect(fan))
    report["Bambu"]["gauges"] = gauges
    r = bodies["RedLizard"]
    pilots = pilot(FRONT_Y, FAN_AXIS_Z, RL_SEAT_X).fuse(pilot(FRONT_Y, LOWER_Z, RL_SEAT_X))
    pockets = cylinder_y(-6.0, -19.26, P18_POCKET_START, 37.0, 2.28).fuse(cylinder_y(6.0, -19.26, P18_POCKET_START, 37.0, 2.28))
    gauges = insert_gauges(r, RL_SEAT_X, [(FRONT_Y, FAN_AXIS_Z), (FRONT_Y, LOWER_Z)], "redlizard")
    gauges.update({
        "wall_unfilled_mm3": volume(box(*RL_WALL).cut(pilots).cut(r.copy())),
        "neck_unfilled_mm3": volume(rl_neck().cut(pockets).cut(pilots).cut(r.copy())),
        "wire_trough_blocked_mm3": volume(box(-2.5, 2.5, 32.1, 35.9, RL_SHELF_BOTTOM - 0.5, -19.4).intersect(r.copy())),
        "material_inside_fan_envelope_mm3": volume(box(RL_SEAT_X + 0.001, 21.6, 13.0, 38.0, -47.8, -22.8).intersect(r.copy())),
        "old_column_front_left_mm3": volume(box(7.0, 11.7, APRON[3] + 0.001, 38.2, -48.5, -22.6).intersect(r.copy())),
    })
    for x in (-6.0, 6.0):
        tag = f"p18_pocket_x{x:+.0f}"
        gauges[f"{tag}_blocked_mm3"] = volume(cylinder_y(x, -19.26, P18_POCKET_START + 0.01, NECK_FRONT_Y - 0.01, 2.27).intersect(r.copy()))
        gauges[f"{tag}_wall_missing_mm3"] = volume(cylinder_y(x, -19.26, P18_POCKET_START + 0.05, NECK_FRONT_Y - 0.03, 2.9).cut(
            cylinder_y(x, -19.26, P18_POCKET_START, NECK_FRONT_Y, 2.29)).cut(r.copy()))
        gauges[f"{tag}_rear_wall_missing_mm3"] = volume(cylinder_y(x, -19.26, 32.06, P18_POCKET_START - 0.01, 2.27).cut(r.copy()))
    report["RedLizard"]["gauges"] = gauges
    for label in ("Bambu", "RedLizard"):
        for key, value in report[label]["gauges"].items():
            if key.endswith("_mm3") and value > 1e-3:
                failures.append(f"{label} gauge {key}: {value}")
    if report["Bambu"]["gauges"]["bambu_third_insert_to_hotend_hardware_mm"] < 1.0:
        failures.append("Bambu third insert too close to the apron hotend hardware")
    return failures, report


def tool_sets(bodies, hardware):
    fan, _, envelope = fan_parts()
    rl = red_lizard_parts()
    hw = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")
    return {
        "Bambu": {"parts": [("body", bodies["Bambu"]), ("fan inserts", hardware["Bambu"]["inserts"]), ("fan", fan),
                            ("fan screws", hardware["Bambu"]["screws"]),
                            ("hotend", load("Tool2510_Reversed_Bambu_Reference_REVIEW")),
                            ("hotend hardware", hw), ("P18", load("P18_Tool_docking_backplate_3010"))],
                  "changed": ("body", "fan inserts", "fan", "fan screws"), "fan": ("fan", "fan screws"),
                  "dock": load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW"),
                  # As revision 30: the hotend core drops 4 mm, then slides 40 mm to the rear.
                  "removable": compound(load("Tool2510_Reversed_Bambu_Reference_REVIEW").Solids()[3:5]),
                  "fixed": compound([bodies["Bambu"], hw, envelope, hardware["Bambu"]["screws"], hardware["Bambu"]["inserts"]]),
                  "service_path": [(0, 0, -i * 0.25) for i in range(17)] + [(0, -i, -4) for i in range(1, 41)]},
        # The Red Lizard drops straight out once its four vertical heatsink screws are removed.
        "RedLizard": {"parts": [("body", bodies["RedLizard"]), ("fan inserts", hardware["RedLizard"]["inserts"]),
                                ("fan", rl["fan"]), ("fan screws", rl["screws"]), ("hotend and hardware", rl["hotend"]),
                                ("P18 and magnets", rl["p18"])],
                      "changed": ("body", "fan inserts", "fan", "fan screws"), "fan": ("fan", "fan screws"),
                      "dock": rl["dock"], "removable": rl["removable"],
                      "fixed": compound([bodies["RedLizard"], box(RL_SEAT_X, RL_SEAT_X + 10, 13, 38, -47.8, -22.8),
                                         rl["screws"], hardware["RedLizard"]["inserts"], rl["p18"]]),
                      "service_path": [(0, 0, -i * 0.5) for i in range(91)]},
    }


def motion_checks(bodies, hardware):
    sets = tool_sets(bodies, hardware)
    rig = compound([s for _, s in carriage()])
    results, failed = {}, False
    for label, t in sets.items():
        parts = dict(t["parts"])
        changed = compound([parts[n] for n in t["changed"]])
        tool = compound([s for _, s in t["parts"]])
        print(f"  {label}: dock approach/withdrawal and carriage retreat", flush=True)
        dock_hits, retreat_hits = [], []
        for step in range(121):
            dy = 0.5 * step
            hit = translated_hits(changed, {"Dock": t["dock"]}, (0, -dy, 0))
            if hit:
                dock_hits.append({"tool_y_mm": -dy, "hits": hit})
            hit = translated_hits(changed, {"Carriage": rig}, (0, dy, 0))
            if hit:
                retreat_hits.append({"carriage_y_mm": -dy, "hits": hit})
        print(f"  {label}: hotend service path", flush=True)
        service_hits = []
        for offset in t["service_path"]:
            hit = translated_hits(t["removable"], {"Fixed": t["fixed"]}, offset)
            if hit:
                service_hits.append({"offset_mm": offset, "hits": hit})
        print(f"  {label}: parked neighbours at +/-{PITCH}", flush=True)
        neighbours = []
        for other, o in sets.items():
            target = compound([s for _, s in o["parts"]] + [o["dock"]])
            for dx in (-PITCH, PITCH):
                moved = target.translate((dx, 0, 0))
                hits = []
                for sample in range(61):
                    hit = translated_hits(tool, {"Neighbour": moved}, (0, -sample, 0))
                    if hit:
                        hits.append({"withdrawal_mm": sample, "hits": hit})
                neighbours.append({"neighbour": other, "offset_x_mm": dx, "samples": 61, "hits": hits})
        results[label] = {"dock_samples": 121, "dock_hits": dock_hits, "carriage_retreat_hits": retreat_hits,
                          "hotend_service_samples": len(t["service_path"]), "hotend_service_hits": service_hits,
                          "neighbour_checks": neighbours}
        failed |= bool(dock_hits or retreat_hits or service_hits or any(n["hits"] for n in neighbours))
    return results, failed


def as_dict(found, **extra):
    return None if found is None else {"mm": found[0], "a": found[1], "b": found[2], **extra}


def clearances(bodies, hardware):
    rig = labelled(carriage())
    sets = tool_sets(bodies, hardware)
    out = {}
    for label, t in sets.items():
        parked = labelled(t["parts"] + [("dock", t["dock"])])
        for dx in (PITCH, -PITCH):
            worst = None
            for dy in DY:
                found = nearest(rig, parked, (0, dy, 0), (dx, 0, 0))
                if found and (worst is None or found[0] < worst["mm"]):
                    worst = as_dict(found, carriage_dy_mm=dy)
            out[f"active carriage | {label} parked at {dx:+.1f}"] = worst
        fan = labelled([(n, s) for n, s in t["parts"] if n in t["fan"]])
        out[f"own {label} fan | carriage"] = as_dict(nearest(rig, fan, (0, 0, 0), (0, 0, 0)))
    for la, ta in sets.items():
        for lb, tb in sets.items():
            out[f"parked {la} fan side | {lb} at +37.3"] = as_dict(
                nearest(labelled(ta["parts"]), labelled(tb["parts"]), (0, 0, 0), (PITCH, 0, 0), cutoff=8.0))
    return out


def export_print(name, shape):
    step, stl = STEP / f"{name}.step", STL / f"{name}.stl"
    cq.exporters.export(shape, str(step))
    cq.exporters.export(shape, str(stl), tolerance=0.03, angularTolerance=0.1)
    back = single(cq.importers.importStep(str(step)).val(), f"{name} STEP readback")
    mesh = trimesh.load_mesh(stl)
    if abs(volume(back) - volume(shape)) > 1e-3 or not (
            mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split(only_watertight=False)) == 1):
        raise ValueError(f"{name} export readback failed")
    return [step, stl]


def export_assembly(name, parts, expected):
    path = STEP / f"{name}.step"
    assembly = cq.Assembly(name=name.replace("_", " "))
    for part, label, color in parts:
        assembly.add(part, name=label, color=cq.Color(*color))
    assembly.export(str(path))
    if len(cq.importers.importStep(str(path)).val().Solids()) != expected:
        raise ValueError(f"{name} readback solid count changed")
    return path


def export_all(bodies, hardware, report):
    exports = export_print(NAMES["bambu"], bodies["Bambu"]) + export_print(NAMES["redlizard"], bodies["RedLizard"])
    for key, shape in (("bambu_inserts", hardware["Bambu"]["inserts"]), ("redlizard_inserts", hardware["RedLizard"]["inserts"])):
        path = STEP / f"{NAMES[key]}.step"
        cq.exporters.export(shape, str(path))
        exports.append(path)
    fan, _, _ = fan_parts()
    path = STEP / f"{NAMES['bambu_fan']}.step"
    cq.exporters.export(compound([fan, *hardware["Bambu"]["screws"].Solids()]), str(path))
    exports.append(path)
    yellow, steel, brass, grey = (0.95, 0.67, 0.1), (0.35, 0.35, 0.38), (0.8, 0.55, 0.2), (0.72, 0.72, 0.75)
    exports.append(export_assembly(NAMES["bambu_toolhead"], [
        (bodies["Bambu"], "R33_Bambu_Print", yellow), (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), "Bambu_Hotend", grey),
        (load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"), "Hotend_M2p5_Hardware", (0.2, 0.7, 0.3)),
        (fan, "Fan_2510", (0.16, 0.18, 0.22)), (hardware["Bambu"]["screws"], "Fan_M2p5x14_Screws", steel),
        (hardware["Bambu"]["inserts"], "Fan_M2p5_L4_Inserts", brass)], 22))
    rl = red_lizard_parts()
    exports.append(export_assembly(NAMES["redlizard_toolhead"], [
        (bodies["RedLizard"], "R33_RedLizard_Print", (0.95, 0.5, 0.15)), (rl["hotend"], "RedLizard_Hotend_And_Hardware", grey),
        (rl["fan"], "Fan_2510", (0.16, 0.18, 0.22)), (rl["screws"], "Fan_M2p5x14_Screws", steel),
        (hardware["RedLizard"]["inserts"], "Fan_M2p5_L4_Inserts", brass), (rl["p18"], "P18_And_Magnets", (0.8, 0.15, 0.75))], 24))
    # Complete Bambu assembly: the revision-32 complete with the print, fan inserts and fan screws replaced.
    source = load(R32_COMPLETE).Solids()
    same = lambda a, b: max(abs(p - q) for p, q in zip(bounds(a), bounds(b))) < 1e-3
    _, old_screws, _ = fan_parts()
    old = {"print": [load(R32["Bambu"]["name"])], "inserts": load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW").Solids(),
           "screws": old_screws.Solids()}
    replaced = {k: [i for i, s in enumerate(source) if any(same(s, v) for v in vs)] for k, vs in old.items()}
    if [len(replaced[k]) for k in ("print", "inserts", "screws")] != [1, 2, 2]:
        raise ValueError(f"Ambiguous replacement in the revision-32 complete assembly: {replaced}")
    skip = {i for v in replaced.values() for i in v}
    before = compound([source[i] for i in sorted(skip)])
    after = compound([bodies["Bambu"], hardware["Bambu"]["inserts"], hardware["Bambu"]["screws"]])
    worst = 0.0
    for i, s in enumerate(source):
        if i in skip:
            continue
        increase = sum(overlaps(after, {"S": s}).values()) - sum(overlaps(before, {"S": s}).values())
        worst = max(worst, increase)
        if increase > 1e-3:
            raise ValueError(f"New intersection with complete-assembly solid {i}: {increase}")
    parts = [(bodies["Bambu"], "R33_Bambu_Print", yellow), (hardware["Bambu"]["inserts"], "Fan_M2p5_L4_Inserts", brass),
             (hardware["Bambu"]["screws"], "Fan_M2p5x14_Screws", steel)]
    parts += [(s, f"Reference_{i}", (0.55, 0.57, 0.6)) for i, s in enumerate(source) if i not in skip]
    exports.append(export_assembly(NAMES["bambu_complete"], parts, len(source) - len(skip) + 7))
    report["complete_assembly"] = {"source": f"{R32_COMPLETE}.step", "solids": len(source) - len(skip) + 7,
                                   "regression_checks": len(source) - len(skip), "max_increase_mm3": worst}
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in exports]


def main():
    started = time.perf_counter()
    log = {"Bambu": [], "RedLizard": []}
    print("Building", flush=True)
    bambu, bambu_inserts, bambu_screws = build_bambu(log["Bambu"])
    red, red_inserts = build_red_lizard(log["RedLizard"])
    bodies = {"Bambu": bambu, "RedLizard": red}
    hardware = {"Bambu": {"inserts": bambu_inserts, "screws": bambu_screws}, "RedLizard": {"inserts": red_inserts}}
    print("Static checks", flush=True)
    failures, report = static_checks({k: v.copy() for k, v in bodies.items()}, hardware)
    report = {"status": "LOCAL_CAD_REVIEW_NOT_PRINT_OR_MACHINE_QUALIFICATION", "operations": log, **report,
              "static_failures": failures}
    if failures:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        raise ValueError(f"Static check failures: {failures}")
    print("Motion checks", flush=True)
    report["motion"], failed = motion_checks({k: v.copy() for k, v in bodies.items()}, hardware)
    if failed:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        raise ValueError(f"Motion failures; see {REPORT}")
    print("Clearances", flush=True)
    before = clearances({label: load(v["name"]) for label, v in R32.items()},
                        {"Bambu": {"inserts": load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW"), "screws": fan_parts()[1]},
                         "RedLizard": {"inserts": red_lizard_parts()["old_inserts"]}})
    after = clearances({k: v.copy() for k, v in bodies.items()}, hardware)
    report["clearances_mm"] = {k: {"r32": before[k], "r33": after[k]} for k in after}
    print("Exports", flush=True)
    export_all(bodies, hardware, report)
    report["hardware"] = {
        "Bambu": "Three M2.5 L4 OD3.5 fan-side heat-set inserts and three M2.5x14 low-head screws (one more of each).",
        "RedLizard": "Two M2.5 L4 OD3.5 fan-side heat-set inserts replace the two inner-entry M2.5 L3 inserts; the two "
                     "M2.5x14 low-head screws are unchanged. Lower P18 screws take M3 x 3 mm inserts in closed pockets.",
    }
    report["runtime_s"] = time.perf_counter() - started
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("operations", "motion")}, indent=1, default=str))


if __name__ == "__main__":
    main()
