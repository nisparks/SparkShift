"""Carriage revision 31: lower the P22-to-P01 front accessory mounts 1.5 mm for 2510-fan clearance.

Each tool's side 2510 fan ends at Z-47.8. Under it, the two lower front accessory bosses on
P01 (X+/-18, R4, top Z-48.78) leave 0.98 mm, and the P22 cheeks that bolt to them (top Z-49.0)
leave 1.20 mm. The own fan passes over them whenever a tool is picked up or parked, and the fan
of the tool parked one bay to the -X side passes over the -X pair whenever the active carriage
moves in or out of a bay.

This revision moves the two bosses, their M3 x 4 heat-sets and M3 screws, the P22 boss
clearances, screw holes and counterbores, and the P22 cheek tops down 1.5 mm. Nothing else changes.

1.5 mm is the practical limit. Lower, the P22 boss clearance would cut into the CPAP duct roof
below it: at 1.5 mm the remaining wall is about 1.4 mm, against the duct's existing 1.24 mm roof
wall. The boss keeps its R4 shape and 1.73 mm wall around the 4.54 mm insert pocket, so it now
hangs 1.0 mm below the P01 bottom face (Z-57.28) in front of the wall.

P01 is frozen v26j core geometry. This is a review proposal for the native model, not an edit of
it. The circled Z-53.079 cross-bore and nut slots on the P01 rear face already clamp the belt side
plates, so they are not reused.

Run with --stage geometry for the build and static checks only, or with no arguments for the
clearance, motion, regression and export pass.
"""

import argparse
import json

import cadquery as cq
import trimesh

import build_and_verify_accessories_v26 as acc
from audit_low_z_bed_clearance import load_parked_variants
from audit_tool_owned_2510 import bounds, compound, overlaps
from build_bambu_clean_r29 import add, remove, sha, single
from build_bambu_clean_r30 import PITCH, fan_parts
from build_modular_toolhead import ROOT, STEP, STL, box, cylinder_y, load, volume
from build_refined_docking_review import translated_hits

MOUNT_DZ = -1.5
OLD_Z = -52.78
NEW_Z = OLD_Z + MOUNT_DZ
BOSS_X = (-18.0, 18.0)
BOSS_Y = (11.4, 15.9)
BOSS_R = 4.0
POCKET_R = 2.27
P22_CLEAR_R = 4.02
CHEEK_TOP = -49.0 + MOUNT_DZ
FAN_BOTTOM_Z = -47.8
P01_BASE = "P01_Back_case_COTS_MR74"
CORE = "Core_With_Restrained_AHG_Lead_References_REVIEW"
CORE_P01 = 54
P22_BASE = "P22_CPAP_Lower_Plenum"
OTHER_CARRIAGE = ("P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
                  "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount")
SOURCE_COMPLETE = "30_Bambu_Compact_Complete_REVIEW"
NAMES = {
    "p01": "P01_Back_case_COTS_MR74_Lowered_Bosses_R31_REVIEW",
    "p22": "P22_CPAP_Lower_Plenum_Lowered_Mounts_R31_REVIEW",
    "hardware": "P22_P01_Mount_Hardware_R31_REVIEW",
    "core": "Core_With_Lowered_P01_Bosses_R31_REVIEW",
    "complete": "31_Carriage_Lowered_Mounts_Complete_REVIEW",
}
REPORT = "verification_carriage_lowered_mounts_r31.json"
# Every intended change lies inside these regions; anything else is a defect.
P01_ZONES = [(x - 4.1, x + 4.1, BOSS_Y[0] - 0.01, BOSS_Y[1] + 0.01, NEW_Z - 4.1, OLD_Z + 4.1) for x in BOSS_X]
P22_ZONES = [(-22.5, -13.4, 10.9, 21.1, NEW_Z - 4.2, -48.9), (13.4, 22.5, 10.9, 21.1, NEW_Z - 4.2, -48.9)]
DY = (0, -0.5, -1, -2, -3, -5, -10, -20, -40, -60)


def zone_union(zones):
    shapes = [box(*z) for z in zones]
    return shapes[0].fuse(*shapes[1:]).clean()


def mass_properties(shape):
    c = shape.Center()
    return {"volume_mm3": volume(shape), "area_mm2": shape.Area(), "centroid_mm": [c.x, c.y, c.z]}


def same_properties(a, b, tolerance=1e-3):
    return (abs(a["volume_mm3"] - b["volume_mm3"]) < tolerance and abs(a["area_mm2"] - b["area_mm2"]) < tolerance
            and max(abs(p - q) for p, q in zip(a["centroid_mm"], b["centroid_mm"])) < tolerance)


def confined(new, old, zones):
    """Compare both parts with the edit zones removed.

    Differencing two nearly identical solids is unreliable in OCC (coincident faces everywhere),
    so the unchanged remainder is compared by volume, surface area and centroid instead.
    """
    outside_new = mass_properties(new.cut(zone_union(zones)))
    outside_old = mass_properties(old.cut(zone_union(zones)))
    inside_new = volume(new.copy().intersect(zone_union(zones)))
    inside_old = volume(old.copy().intersect(zone_union(zones)))
    return {"outside_zones_new": outside_new, "outside_zones_released": outside_old,
            "unchanged_outside_zones": same_properties(outside_new, outside_old),
            "inside_zones_mm3": {"new": inside_new, "released": inside_old}}


def hardware(dz):
    return [(name, cq.Shape.cast(shape)) for name, shape in acc.build_accessory_hardware(dz)
            if name.startswith("ACC_CASE_BOSS")]


def build_p01(log):
    body = single(load(P01_BASE), "released P01")
    old = compound([b.intersect(box(x - 4.6, x + 4.6, BOSS_Y[0], 16.5, -57.5, -48.0))
                    for x, b in ((x, load(P01_BASE)) for x in BOSS_X)])
    expected_boss = 3.141592653589793 * (BOSS_R ** 2 - POCKET_R ** 2) * (BOSS_Y[1] - BOSS_Y[0])
    if abs(volume(old) - 2 * expected_boss) > 1e-2:
        raise ValueError(f"P01 has material besides the two bosses in front of Y{BOSS_Y[0]}: {volume(old)}")
    cutter = box(BOSS_X[0] - 4.6, BOSS_X[0] + 4.6, BOSS_Y[0], 16.5, -57.5, -48.0).fuse(
        box(BOSS_X[1] - 4.6, BOSS_X[1] + 4.6, BOSS_Y[0], 16.5, -57.5, -48.0))
    body = remove(body, cutter, "remove the two lower front accessory bosses at Z-52.78", log)
    bosses = cylinder_y(BOSS_X[0], NEW_Z, *BOSS_Y, BOSS_R).fuse(cylinder_y(BOSS_X[1], NEW_Z, *BOSS_Y, BOSS_R))
    body = add(body, bosses, f"R4 bosses at Z{NEW_Z:.2f}", log)
    pockets = cylinder_y(BOSS_X[0], NEW_Z, BOSS_Y[0], 16.0, POCKET_R).fuse(
        cylinder_y(BOSS_X[1], NEW_Z, BOSS_Y[0], 16.0, POCKET_R))
    body = remove(body, pockets, "4.54 mm heat-set pockets, Y11.4..15.9", log)
    return body


def p01_checks(body):
    failures = []
    base_volume = volume(load(P01_BASE))
    released = mass_properties(load(P01_BASE))
    core = mass_properties(load(CORE).Solids()[CORE_P01])
    # The two exports of v26j P01 differ only by STEP representation (two seam edges, 0.006 mm3).
    same_as_core = same_properties(released, core, tolerance=0.01) and len(load(P01_BASE).Faces()) == len(
        load(CORE).Solids()[CORE_P01].Faces())
    if not same_as_core:
        failures.append("P01 COTS STEP differs from the core-reference P01")
    zones = confined(body.copy(), load(P01_BASE), P01_ZONES)
    result = {
        "volume_mm3": volume(body), "released_volume_mm3": base_volume,
        "net_change_mm3": volume(body) - base_volume, **zones,
        "faces": len(body.Faces()), "released_faces": len(load(P01_BASE).Faces()),
        "identical_to_core_reference_p01": same_as_core,
        "bounds_mm": bounds(body),
    }
    if abs(result["net_change_mm3"]) > 1e-3:
        failures.append("P01 boss move is not volume-neutral")
    if not zones["unchanged_outside_zones"]:
        failures.append("P01 changed outside the boss zones")
    for x in BOSS_X:
        local = body.copy().intersect(box(x - 4.6, x + 4.6, BOSS_Y[0], 16.5, -60.0, -46.0))
        b = bounds(local)
        result[f"boss_x{x:+.0f}_z_range_mm"] = [b[4], b[5]]
        if abs(b[5] - (NEW_Z + BOSS_R)) > 1e-3 or abs(b[4] - (NEW_Z - BOSS_R)) > 1e-3:
            failures.append(f"P01 boss X{x:+.0f} not at the lowered axis")
    return result, failures


def p22_checks(body, air):
    failures = []
    default_body, default_air = acc.build_p22_lower_plenum()
    default = cq.Shape.cast(default_body)
    released_air = cq.Shape.cast(default_air)
    reproduced = same_properties(mass_properties(default), mass_properties(load(P22_BASE)))
    if not reproduced:
        failures.append("Parameterised P22 builder does not reproduce the released P22 at mount_dz=0")
    zones = confined(body.copy(), load(P22_BASE), P22_ZONES)
    walls = {}
    for label, z, duct in (("released", OLD_Z, released_air), ("r31", NEW_Z, air)):
        walls[label] = min(duct.distance(cylinder_y(x, z, 11.0, 15.95, P22_CLEAR_R)) for x in BOSS_X)
    result = {
        "parameterised_builder_reproduces_released_p22": reproduced,
        "volume_mm3": volume(body), "released_volume_mm3": volume(load(P22_BASE)), **zones,
        "boss_clearance_to_cpap_duct_wall_mm": walls,
        "cheek_top_z_mm": {f"X{x:+.0f}": bounds(body.copy().intersect(box(x - 4.6, x + 4.6, 11.0, 21.0, -60.0, -46.0)))[5]
                           for x in BOSS_X},
        "air_volume_mm3": {"released": volume(released_air), "r31": volume(air)},
        "bounds_mm": bounds(body),
    }
    if not zones["unchanged_outside_zones"]:
        failures.append("P22 changed outside the cheek zones")
    if walls["r31"] < 1.24:
        failures.append(f"P22 boss clearance leaves {walls['r31']:.3f} mm to the duct (< 1.24 mm roof wall)")
    if abs(result["air_volume_mm3"]["r31"] - result["air_volume_mm3"]["released"]) > 1e-3:
        failures.append("CPAP air domain changed")
    if any(abs(z - CHEEK_TOP) > 1e-3 for z in result["cheek_top_z_mm"].values()):
        failures.append("P22 cheek tops not at the lowered height")
    return result, failures


def carriage_parts(p01, p22, hw):
    core = load(CORE).Solids()
    unchanged = [(f"core_{i}", s) for i, s in enumerate(core) if i != CORE_P01]
    for name in OTHER_CARRIAGE:
        solids = load(name).Solids()
        unchanged += [(name if len(solids) == 1 else f"{name}_{i}", s) for i, s in enumerate(solids)]
    changed = [("P01", p01), ("P22", p22)] + hw
    return unchanged, changed


def interference(p01, p22, hw):
    failures = []
    unchanged, _ = carriage_parts(p01, p22, hw)
    old_hw = hardware(0.0)
    hits = {}
    for label, shape in [("P01", p01), ("P22", p22)] + hw:
        others = {n: s for n, s in unchanged}
        others.update({n: s for n, s in [("P01", p01), ("P22", p22)] + hw if n != label})
        if label.startswith("ACC_CASE_BOSS"):
            others = {n: s for n, s in others.items() if not n.startswith("ACC_CASE_BOSS")}
        found = overlaps(shape, others)
        if found:
            hits[label] = found
    # Pre-existing contact (if any) between the released parts and the same neighbours is not a regression.
    released = {"P01": load(P01_BASE), "P22": load(P22_BASE)}
    released.update(dict(old_hw))
    baseline = {}
    for label, shape in released.items():
        others = {n: s for n, s in unchanged}
        others.update({n: s for n, s in released.items() if n != label})
        if label.startswith("ACC_CASE_BOSS"):
            others = {n: s for n, s in others.items() if not n.startswith("ACC_CASE_BOSS")}
        found = overlaps(shape, others)
        if found:
            baseline[label] = found
    new = {f"{a}|{b}": v for a, d in hits.items() for b, v in d.items()}
    old = {f"{a}|{b}": v for a, d in baseline.items() for b, v in d.items()}
    worse = {k: v for k, v in new.items() if v - old.get(k, 0.0) > 1e-3}
    if worse:
        failures.append(f"New intersections: {worse}")
    boss = lambda part, x: part.copy().intersect(box(x - 4.6, x + 4.6, BOSS_Y[0], 16.5, -60.0, -46.0))
    gaps = {
        "p01_boss_to_p22_mm": {"released": min(boss(load(P01_BASE), x).distance(load(P22_BASE)) for x in BOSS_X),
                               "r31": min(boss(p01, x).distance(p22) for x in BOSS_X)},
        "heatset_to_p01_overlap_mm3": sum(volume(s.intersect(p01)) for n, s in hw if "HEATSET" in n),
        "screw_to_p22_overlap_mm3": sum(volume(s.intersect(p22)) for n, s in hw if "M3x10" in n),
    }
    if gaps["heatset_to_p01_overlap_mm3"] > 1e-3 or gaps["screw_to_p22_overlap_mm3"] > 1e-3:
        failures.append("Mount hardware intersects P01 or P22")
    return {"released_intersections_mm3": old, "r31_intersections_mm3": new, **gaps}, failures


def tools():
    """Bambu R30 and Red Lizard (R21 parked snapshot with the R30 strip-trimmed body)."""
    fan, screws, _ = fan_parts()
    bambu = [("R30 body", load("Bambu_Compact_Fan_Closed_Bores_R30_REVIEW")),
             ("fan inserts", load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW")),
             ("fan", fan), ("fan screws", screws),
             ("hotend", load("Tool2510_Reversed_Bambu_Reference_REVIEW")),
             ("hotend hardware", load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")),
             ("P18", load("P18_Tool_docking_backplate_3010"))]
    red = load_parked_variants()["RedLizard"]
    snap = red["tool"].Solids()
    if abs(volume(snap[0]) - 8352.19) > 0.5 or abs(bounds(snap[0])[5] - 48.74) > 0.01:
        raise ValueError("Red Lizard snapshot body is not solid 0")
    redlizard = [("R30 trimmed body", load("RedLizard_Side2510_Strip_Trim_R30_REVIEW")),
                 ("fan", snap[14]), ("fan screws/inserts", compound(snap[15:19])),
                 ("hotend and hardware", compound(snap[1:14])), ("P18 and magnets", compound(snap[19:]))]
    return {
        "Bambu R30": {"parts": bambu, "moving": ("R30 body", "fan inserts", "fan", "fan screws"),
                      "fan": ("fan", "fan screws"),
                      "dock": load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")},
        "RedLizard R30": {"parts": redlizard, "moving": ("R30 trimmed body", "fan", "fan screws/inserts"),
                          "fan": ("fan", "fan screws/inserts"), "dock": red["dock"]},
    }


def labelled(parts):
    names, solids = [], []
    for name, shape in parts:
        for s in shape.Solids():
            names.append(name)
            solids.append(s)
    return names, solids


def nearest(a, b, offset_a, offset_b, cutoff=5.0):
    """Minimum distance between two labelled solid lists, with the closest pair."""
    best = None
    moved_a = [(n, s.translate(offset_a)) for n, s in zip(*a)]
    moved_b = [(n, s.translate(offset_b)) for n, s in zip(*b)]
    for na, s in moved_a:
        sb = bounds(s)
        for nb, t in moved_b:
            tb = bounds(t)
            gap = max(tb[0] - sb[1], sb[0] - tb[1], tb[2] - sb[3], sb[2] - tb[3], tb[4] - sb[5], sb[4] - tb[5], 0)
            if gap > cutoff or (best is not None and gap >= best[0]):
                continue
            d = s.distance(t)
            if best is None or d < best[0]:
                best = (d, na, nb)
    return best


def clearances(p01, p22, hw):
    unchanged, changed = carriage_parts(p01, p22, hw)
    groups = {
        "unchanged": labelled(unchanged),
        "released": labelled([("P01", load(P01_BASE)), ("P22", load(P22_BASE))] + hardware(0.0)),
        "r31": labelled(changed),
    }
    results = {}
    for tool_label, tool in tools().items():
        parts = dict(tool["parts"])
        parked = labelled(tool["parts"] + [("dock", tool["dock"])])
        fan = labelled([(n, parts[n]) for n in tool["fan"]])
        scenarios = [("own fan, carriage retreating", fan, 0.0)]
        scenarios += [(f"parked neighbour at X{dx:+.1f}", parked, dx) for dx in (-PITCH, PITCH)]
        for scenario, target, dx in scenarios:
            print(f"Clearance: {tool_label}, {scenario}", flush=True)
            worst = {}
            for dy in DY:
                found = {g: nearest(groups[g], target, (0, dy, 0), (dx, 0, 0)) for g in groups}
                for state, members in (("released", ("unchanged", "released")), ("r31", ("unchanged", "r31"))):
                    cands = [found[g] for g in members if found[g] is not None]
                    if not cands:
                        continue
                    d, carriage_part, tool_part = min(cands)
                    if state not in worst or d < worst[state]["mm"]:
                        worst[state] = {"mm": d, "carriage_part": carriage_part, "tool_part": tool_part,
                                        "carriage_dy_mm": dy}
            results[f"{tool_label} | {scenario}"] = worst
    vertical = {}
    for label, (b01, b22) in (("released", (load(P01_BASE), load(P22_BASE))), ("r31", (p01, p22))):
        tops = []
        for s in (b01, b22):
            for x0, x1 in ((9.8, 20.6), (-22.6, -16.7)):
                under = s.copy().intersect(box(x0, x1, 13.0, 40.0, -70.0, FAN_BOTTOM_Z))
                if under.Solids():
                    tops.append(bounds(under)[5])
        vertical[label] = FAN_BOTTOM_Z - max(tops)
    results["vertical_gap_fan_bottom_to_p01_p22_under_fan_mm"] = vertical
    return results


def motion(p01, p22, hw):
    moving = compound([p01, p22] + [s for _, s in hw])
    hits = []
    for tool_label, tool in tools().items():
        parts = dict(tool["parts"])
        own = compound([parts[n] for n in tool["moving"]])
        parked = compound([s for _, s in tool["parts"]] + [tool["dock"]])
        print(f"Motion sweeps: {tool_label}", flush=True)
        for step in range(121):
            dy = -0.5 * step
            hit = translated_hits(moving, {"own tool": own}, (0, dy, 0))
            if hit:
                hits.append({"tool": tool_label, "carriage_dy_mm": dy, "hits": hit})
        for dx in (-PITCH, PITCH):
            target = parked.translate((dx, 0, 0))
            for step in range(61):
                hit = translated_hits(moving, {"parked neighbour": target}, (0, -step, 0))
                if hit:
                    hits.append({"tool": tool_label, "neighbour_dx_mm": dx, "carriage_dy_mm": -step, "hits": hit})
    return {"own_tool_samples": 121, "neighbour_samples": 61, "hits": hits}


def export_all(p01, p22, hw, report):
    exports = []
    for key, shape in (("p01", p01), ("p22", p22)):
        step, stl = STEP / f"{NAMES[key]}.step", STL / f"{NAMES[key]}.stl"
        cq.exporters.export(shape, str(step))
        cq.exporters.export(shape, str(stl), tolerance=0.03, angularTolerance=0.1)
        back = single(cq.importers.importStep(str(step)).val(), f"{key} STEP readback")
        mesh = trimesh.load_mesh(stl)
        if abs(volume(back) - volume(shape)) > 1e-3 or not (
                mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split(only_watertight=False)) == 1):
            raise ValueError(f"{key} export readback failed")
        exports += [step, stl]
    hw_path = STEP / f"{NAMES['hardware']}.step"
    cq.exporters.export(compound([s for _, s in hw]), str(hw_path))
    if len(cq.importers.importStep(str(hw_path)).val().Solids()) != len(hw):
        raise ValueError("Hardware STEP readback solid count changed")
    core = load(CORE).Solids()
    core_path = STEP / f"{NAMES['core']}.step"
    cq.exporters.export(compound([p01 if i == CORE_P01 else s for i, s in enumerate(core)]), str(core_path))
    if len(cq.importers.importStep(str(core_path)).val().Solids()) != len(core):
        raise ValueError("Core STEP readback solid count changed")
    # Complete assembly: the revision-30 carriage/dock/toolhead with P01 and P22 replaced and the
    # four mount fasteners added (the released complete assembly carries no accessory fasteners).
    source = load(SOURCE_COMPLETE).Solids()
    same = lambda a, b: max(abs(p - q) for p, q in zip(bounds(a), bounds(b))) < 1e-3
    replaced = {k: [i for i, s in enumerate(source) if same(s, v)]
                for k, v in (("P01", load(P01_BASE)), ("P22", load(P22_BASE)))}
    if [len(v) for v in replaced.values()] != [1, 1]:
        raise ValueError(f"Ambiguous replacement in the complete assembly: {replaced}")
    skip = {i for v in replaced.values() for i in v}
    print("Regression against unchanged complete-assembly solids", flush=True)
    before_parts = compound([source[i] for i in sorted(skip)] + [s for _, s in hardware(0.0)])
    after_parts = compound([p01, p22] + [s for _, s in hw])
    worst = 0.0
    for i, s in enumerate(source):
        if i in skip:
            continue
        increase = sum(overlaps(after_parts, {"S": s}).values()) - sum(overlaps(before_parts, {"S": s}).values())
        worst = max(worst, increase)
        if increase > 1e-3:
            raise ValueError(f"New intersection with complete-assembly solid {i}: {increase}")
    full = cq.Assembly(name="31 Carriage lowered P22 mounts - complete carriage, Bambu toolhead and dock")
    full.add(p01, name="R31_P01_Lowered_Bosses", color=cq.Color(0.45, 0.47, 0.52))
    full.add(p22, name="R31_P22_Lowered_Mounts", color=cq.Color(0.1, 0.65, 0.65))
    full.add(compound([s for _, s in hw]), name="R31_P22_P01_M3_Screws_And_Heatsets", color=cq.Color(0.8, 0.55, 0.2))
    for i, s in enumerate(source):
        if i not in skip:
            full.add(s, name=f"Unchanged_Reference_{i}", color=cq.Color(0.55, 0.57, 0.6))
    full_path = STEP / f"{NAMES['complete']}.step"
    full.export(str(full_path))
    expected = len(source) + len(hw)
    if len(cq.importers.importStep(str(full_path)).val().Solids()) != expected:
        raise ValueError("Complete assembly readback solid count changed")
    report["complete_assembly"] = {"solids": expected, "regression_checks": len(source) - len(skip),
                                   "max_increase_mm3": worst}
    exports += [hw_path, core_path, full_path]
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in exports]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=("geometry", "full"), default="full")
    args = parser.parse_args()
    log = []
    print(f"Building P01 with bosses at Z{NEW_Z:.2f}", flush=True)
    p01 = build_p01(log)
    print("Building P22 and mount hardware", flush=True)
    p22_body, p22_air = acc.build_p22_lower_plenum(MOUNT_DZ)
    p22 = single(cq.Shape.cast(p22_body), "R31 P22")
    air = cq.Shape.cast(p22_air)
    hw = hardware(MOUNT_DZ)
    built = {"p01": volume(p01), "p22": volume(p22)}
    # Checks work on copies: OCC Booleans may modify their arguments, and these shapes are exported.
    copies = lambda: (p01.copy(), p22.copy(), [(n, s.copy()) for n, s in hw])
    print("Static checks", flush=True)
    p01_report, failures = p01_checks(p01.copy())
    p22_report, p22_failures = p22_checks(p22.copy(), air)
    fit_report, fit_failures = interference(*copies())
    failures += p22_failures + fit_failures
    report = {
        "status": "LOCAL_CAD_REVIEW_NOT_PRINT_OR_MACHINE_QUALIFICATION",
        "change": f"P22-to-P01 front accessory mounts lowered {abs(MOUNT_DZ)} mm (axis Z{OLD_Z} -> Z{NEW_Z:.2f})",
        "sources": {n: {"file": f"{n}.step", "sha256": sha(STEP / f"{n}.step")}
                    for n in (P01_BASE, P22_BASE, CORE, SOURCE_COMPLETE)},
        "operations": log, "p01": p01_report, "p22": p22_report, "fit": fit_report,
        "static_failures": failures,
    }
    if args.stage == "geometry" or failures:
        print(json.dumps({k: v for k, v in report.items() if k not in ("operations", "sources")}, indent=1))
        if failures:
            raise ValueError(f"Static check failures: {failures}")
        return
    report["clearances"] = clearances(*copies())
    report["motion"] = motion(*copies())
    if report["motion"]["hits"]:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2) + "\n")
        raise ValueError(f"Motion sweep intersections; see {REPORT}")
    if abs(volume(p01) - built["p01"]) > 1e-6 or abs(volume(p22) - built["p22"]) > 1e-6:
        raise ValueError("Export shapes changed during checks")
    export_all(p01, p22, hw, report)
    report["design"] = {
        "boss_axis_z_mm": NEW_Z, "boss_top_z_mm": NEW_Z + BOSS_R, "boss_bottom_z_mm": NEW_Z - BOSS_R,
        "p01_bottom_face_z_mm": -57.279,
        "boss_wall_around_pocket_mm": BOSS_R - POCKET_R,
        "p22_cheek_top_z_mm": CHEEK_TOP, "p22_material_above_counterbore_mm": CHEEK_TOP - (NEW_Z + 3.0),
        "hardware": "Unchanged parts: 2x M3x4x4.6 heat-sets (Y11.9..15.9) and 2x M3 screws, moved with the bosses.",
    }
    report["limitations"] = [
        "P01 is frozen v26j geometry; the native model needs the same boss move before printing this pair.",
        "Each boss hangs 1.0 mm below the P01 bottom face in front of the wall; in the rear-face-down print "
        "orientation this is a 1.0 mm unsupported crescent at the start of each boss.",
        "Insert pull-out, printed strength and probe stiffness through the lowered mounts are unqualified.",
    ]
    (ROOT / REPORT).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("operations", "sources")}, indent=1))


if __name__ == "__main__":
    main()
