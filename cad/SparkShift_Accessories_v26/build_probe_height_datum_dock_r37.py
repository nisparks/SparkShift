"""Revision 37: probe at the makers' 2.6 mm height, P23 screws off the Beacon, Bambu tip at the datum, one dock.

1. Probe height. The Beacon coil sat 2.27 mm above the nozzle tip (Cartographer 2.28 mm); both makers give
   2.6 mm nominal. P23 is 0.33 mm thinner, so both probes sit 0.33 mm higher.
2. P23 to P22. Checking the hardware against the probes (no earlier audit did) found the two rear
   P23-to-P22 screw heads, recessed into P23's underside at (+/-15.8, -11.5), sitting 25.5 mm3 each inside
   the Beacon model's 1.1 mm top-side component block. With a 0.33 mm thinner P23 the front pair would keep
   only a 0.65 mm web. Revision 37 drops the four hidden screws and the probe's captive nuts:
   - the probe's own two M3 screws now clamp the probe and P23 together into heat-set inserts in P22;
   - P23 grows two rear ears behind the probe board, where two button-head screws hold it to P22 when the
     probe is off. No fastener sits between P23 and the probe board.
   P22's four spigot bosses move to match (0.4 mm longer, for 3 mm inserts).
3. Bambu tip. The synthetic Bambu nozzle's cone was drawn with a 1.1 mm tip face at the datum, but its 2 mm
   bore was cut straight through, leaving a knife edge 0.75 mm higher. Revision 37 restores the tip at the
   datum (the Red Lizard tip height) with a 0.4 mm orifice.
4. One dock. With both tips at the datum, every bay uses the revision-36 dock with the datum-height pad and
   wiper; the raised Bambu pad and wiper are retired.
5. P28's probe feeler goes from 2.27 to 2.60 mm.

Then the revision-36 full-rack requalification runs again with every revision-37 part.
"""

import argparse
import json
import os
import time

import build_and_verify_accessories_v26 as acc

os.environ.setdefault("SPARKSHIFT_SCENE", str(acc.WORK / "r37_scene"))

import cadquery as cq  # noqa: E402

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import fast_geometry  # noqa: E402
import r37_parts as P  # noqa: E402
from audit_tool_owned_2510 import bounds, compound, overlaps  # noqa: E402
from build_bambu_clean_r29 import sha  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31, confined, mass_properties, same_properties  # noqa: E402
from build_fan_mounts_r33 import export_assembly, export_print  # noqa: E402
from build_modular_toolhead import ROOT, STEP, load  # noqa: E402
from build_p24_cable_entry_r35 import NAMES as R35  # noqa: E402
from build_refined_docking_review import DOCK_NAMES  # noqa: E402

REPORT = "verification_probe_height_datum_dock_r37.json"
VARIANTS = ("Bambu", "RedLizard")
PITCH = 37.3


def zone(x, y, r=3.7, z0=-73.6, z1=-69.95):
    return (x - r, x + r, y - r, y + r, z0, z1)


def overlap_rows(group, others, skip=lambda a, b: False):
    rows, seen = [], set()
    for na, a in group.items():
        for nb, b in others.items():
            if na == nb or (nb, na) in seen or skip(na, nb):
                continue
            seen.add((na, nb))
            rows += [{"a": na, "b": nb, "mm3": v} for v in overlaps(a, {nb: b}).values()]
    return rows


def beacon_internal(a, b):
    return a.startswith("Beacon_") and b.startswith("Beacon_")


# --------------------------------------------------------------------------------------------
# Build and static checks
# --------------------------------------------------------------------------------------------

def check_p22(p22_new, air_new, report, failures):
    old_body, old_air = acc.build_p22_lower_plenum(P.MOUNT_DZ)
    old_body, old_air = cq.Shape.cast(old_body), cq.Shape.cast(old_air)
    reproduced = same_properties(mass_properties(old_body), mass_properties(load(R31["p22"])))
    zones = [zone(x, y) for x, y in acc.P22_PROBE_MOUNTS + P.P22_MOUNTS]
    floors = []
    for x, y in P.P22_MOUNTS:
        hole = cq.Solid.makeCylinder(2.27, P.INSERT_HOLE_Z[1] - P.INSERT_HOLE_Z[0], cq.Vector(x, y, P.INSERT_HOLE_Z[0]),
                                     cq.Vector(0, 0, 1))
        hit = fast_geometry.min_distance(fast_geometry.index_group([("hole", hole)]),
                                         fast_geometry.index_group([("air", air_new)]), cutoff=10.0)
        floors.append({"xy_mm": [x, y], "floor_to_air_duct_mm": hit[0]})
    report["p22"] = {
        "builder_reproduces_revision_31": reproduced,
        "spigots_xy_mm": {"removed": acc.P22_PROBE_MOUNTS, "added": P.P22_MOUNTS},
        "spigot_z_mm": P.SPIGOT_Z, "insert_hole_z_mm": P.INSERT_HOLE_Z,
        "volume_mm3": {"r31": old_body.Volume(), "r37": p22_new.Volume()},
        "confinement": confined(p22_new.copy(), old_body.copy(), zones),
        "air_domain_unchanged": same_properties(mass_properties(air_new), mass_properties(old_air)),
        "insert_floor_to_air_duct": floors}
    if not reproduced:
        failures.append("P22 builder does not reproduce revision 31 with its default spigots")
    if not report["p22"]["confinement"]["unchanged_outside_zones"]:
        failures.append("P22 changed outside the spigot zones")
    if not report["p22"]["air_domain_unchanged"]:
        failures.append("P22 air domain changed")
    if min(f["floor_to_air_duct_mm"] for f in floors) < 1.0:
        failures.append("Insert hole leaves under 1 mm to the air duct")


def check_p23(p23_new, report, failures):
    old = load("P23_Beacon_Cartographer_Mount")
    gauges = {
        "thickness_mm": P.Z_TOP - P.Z_SEAT,
        "relief_leg_thickness_mm": P.Z_TOP - P.RELIEF_TOP,
        "web_under_spigot_sockets_mm": P.SOCKET_BOTTOM - P.Z_SEAT,
        "socket_outboard_wall_mm": P.EAR_X[1] - (abs(P.PROBE_XY[0][0]) + 3.15),
        "ear_inner_wall_mm": abs(P.REAR_XY[0][0]) - 3.15 - P.EAR_X[0],
        "ear_rear_wall_mm": abs(P.EAR_Y_REAR - P.REAR_XY[0][1]) - 3.15,
        "rear_head_to_probe_board_y_mm": -15.8 - (P.REAR_XY[0][1] + 2.85),
        "rear_head_to_relief_edge_y_mm": -16.0 - (P.REAR_XY[0][1] + 2.85)}
    # Check the gauges against the solid itself, not only the constants.
    for x, y in P.P22_MOUNTS:
        ring = cq.Solid.makeCylinder(3.15 + 1.1, 0.5, cq.Vector(x, y, -72.0), cq.Vector(0, 0, 1)).cut(
            cq.Solid.makeCylinder(3.16, 0.5, cq.Vector(x, y, -72.0), cq.Vector(0, 0, 1)))
        missing = ring.Volume() - ring.intersect(p23_new.copy()).Volume()
        if missing > 1e-3:
            failures.append(f"P23 wall around the socket at ({x}, {y}) is under 1.1 mm")
    report["p23"] = {"volume_mm3": {"released": old.Volume(), "r37": p23_new.Volume()},
                     "bounds_mm": {"released": bounds(old), "r37": bounds(p23_new)}, "gauges": gauges,
                     "removed": "Four P23-to-P22 screw counterbores, the probe's two captive-nut slots",
                     "added": "Two rear ears with screw holes at (+/-15.8, -19.5); spigot sockets at the probe holes"}
    if min(v for k, v in gauges.items() if k.endswith("wall_mm")) < 1.1:
        failures.append("P23 wall under 1.1 mm")


def probe_heights(beacon_raised, carto, tip):
    out = {}
    for name, coil in (("Beacon_RevH", bounds(beacon_raised[0])[5]), ("Cartographer_V3", -76.600 + P.DZ)):
        out[name] = {"coil_face_z_mm": coil, "above_tip_mm": coil - tip,
                     "released_above_tip_mm": coil - P.DZ - tip}
    return out


def static_checks(parts, report, failures):
    tip = parts["tip"]
    b = parts["beacon"]
    new = {"P22_R37": parts["p22"], "P23_R37": parts["p23"], "Cable_R37": parts["cable"],
           "Beacon_component_block": b[2], "Beacon_board": b[3], "Beacon_connector": b[4], **dict(parts["hardware"])}
    fixed = {"Core_R31": load(R31["core"]), "P20": load("P20_CPAP_Hose_Inlet"), "P21": load("P21_CPAP_Gantry_Bridge"),
             "P24_R35": load(R35["p24"]), "EBB42": parts["ebb42"], **dict(parts["other_hardware"])}
    rows = overlap_rows(new, {**new, **fixed})
    report["carriage_internal"] = {
        "checked": "Every changed part, the raised Beacon and the new fasteners against each other and the "
                   "whole carriage (core, P20-P24, cable, EBB42, all accessory fasteners).",
        "beacon_model_internal_mm3": [r for r in rows if beacon_internal(r["a"], r["b"])],
        "intersections_mm3": [r for r in rows if not beacon_internal(r["a"], r["b"])]}
    if report["carriage_internal"]["intersections_mm3"]:
        failures.append("Carriage-internal intersection")
    # The released state, for the record: the hidden screws against the Beacon at its old height.
    old_b = P.beacon(0.0)
    report["released_finding"] = overlap_rows(
        dict(P.released_probe_hardware()), {"Beacon_component_block": old_b[2], "Beacon_board": old_b[3]})
    carto_rows = overlap_rows({"Cartographer": parts["cartographer"]},
                              {**{k: v for k, v in new.items() if not k.startswith("Beacon") and k != "Cable_R37"},
                               **fixed})
    report["cartographer"] = {"intersections_mm3": carto_rows,
                              "note": "Checked in place of the Beacon; the Beacon and its cable are not fitted with it."}
    if carto_rows:
        failures.append("Cartographer intersection")
    metal = {**dict(parts["hardware"]), **dict(parts["other_hardware"]), "EBB42": parts["ebb42"]}
    for label, v in parts["tools"].items():
        metal[f"{label}_hotend"] = v["hotend"]
    keep = {"top": P.beacon_top_keepout(b), "bottom": b[0]}
    report["beacon_keepouts"] = {name: {"metal_mm3": overlaps(ko, metal),
                                        "printed_core_mm3": overlaps(ko, {"P01_printed_motor_mount": fixed["Core_R31"]})}
                                 for name, ko in keep.items()}
    report["beacon_keepouts"]["note"] = ("Only metal is excluded. P01 is printed (is_metal false in the v26 "
                                         "metadata) and reached 121.7 mm3 into the top zone at the released height.")
    if any(v["metal_mm3"] for k, v in report["beacon_keepouts"].items() if k != "note"):
        failures.append("Metal in a Beacon keepout")
    mounted = []
    for label, v in parts["tools"].items():
        for name, s in v["parts"]:
            for target, vol in overlaps(s, {**new, "Cartographer": parts["cartographer"]}).items():
                mounted.append({"tool": label, "part": name, "b": target, "mm3": vol})
    report["mounted_tools_vs_changed_carriage"] = mounted
    if mounted:
        failures.append("Mounted tool intersects the revision-37 carriage")
    report["probe_heights"] = probe_heights(b, parts["cartographer"], tip)
    near = {**new, **fixed}
    lows = sorted(((bounds(s)[4], n) for n, s in near.items() if not n.startswith("Core")), key=lambda t: t[0])[:6]
    report["lowest_carriage_features_above_tip_mm"] = [{"part": n, "z_mm": z, "above_tip_mm": z - tip} for z, n in lows]
    hw = dict(parts["hardware"])
    report["thread_engagement_mm"] = {
        name: min(bounds(hw[name])[5], P.SPIGOT_Z[1]) - P.SPIGOT_Z[0]
        for name in hw if "M3x" in name and "HEATSET" not in name}
    report["screw_tip_to_insert_top_mm"] = {name: P.SPIGOT_Z[1] - bounds(hw[name])[5]
                                            for name in hw if "HEATSET" not in name}
    if min(report["thread_engagement_mm"].values()) < 2.0 or min(report["screw_tip_to_insert_top_mm"].values()) < 0:
        failures.append("Screw length")


def check_bambu_and_dock(parts, report, failures):
    tip = parts["tip"]
    old = load("Tool2510_Reversed_Bambu_Reference_REVIEW").Solids()[3]
    new = parts["bambu_hotend"].Solids()[3]
    zone_box = (-2.0, 2.0, 20.7, 24.7, -79.0, P.BORE_PLUG_TOP + 0.01)
    report["bambu_tip"] = dict(parts["bambu_info"], confinement=confined(new.copy(), old.copy(), [zone_box]))
    if not report["bambu_tip"]["confinement"]["unchanged_outside_zones"] or abs(bounds(new)[4] - tip) > 1e-6:
        failures.append("Bambu tip repair")
    dock = parts["dock"]
    pad, wiper = dock[3], dock[7]
    rl_pad, rl_wiper = load("RedLizard_Dock_Ooze_Pad_SILICONE_REVIEW"), load("RedLizard_Dock_Wiper_SILICONE_REVIEW")
    same = lambda a, b: abs(a.Volume() - b.Volume()) < 1e-6 and max(abs(p - q) for p, q in zip(bounds(a), bounds(b))) < 1e-6
    report["dock"] = {
        "source": "36_RedLizard_Dock_Complete_REVIEW (revision-36 chute, datum pad and wiper)",
        "pad_is_datum_pad": same(pad, rl_pad), "wiper_is_datum_wiper": same(wiper, rl_wiper),
        "pad_top_z_mm": bounds(pad)[5], "wiper_top_z_mm": bounds(wiper)[5],
        "retired_bambu_pad_top_z_mm": bounds(load("Bambu_Dock_Ooze_Pad_SILICONE_REVIEW"))[5],
        "pad_support_area_mm2": volume_support(pad, dock[0])}
    contact = {}
    for label, v in parts["tools"].items():
        hz = bounds(v["hotend"])[4]
        contact[label] = {"tip_z_mm": hz, "tip_to_pad_top_mm": hz - bounds(pad)[5],
                          "docked_intersections_mm3": overlaps(compound([s for _, s in v["parts"]]),
                                                               {n: s for n, s in zip(DOCK_NAMES, dock)})}
        if abs(contact[label]["tip_to_pad_top_mm"]) > 1e-3 or contact[label]["docked_intersections_mm3"]:
            failures.append(f"{label} docked contact")
    report["dock"]["docked_tools"] = contact
    if not (report["dock"]["pad_is_datum_pad"] and report["dock"]["wiper_is_datum_wiper"]) or \
            report["dock"]["pad_support_area_mm2"] < 20:
        failures.append("Dock pad/wiper")
    # Bambu hotend service: the repaired core drops 4 mm, then slides 40 mm to the rear.
    tools = parts["tools"]["Bambu"]
    names = dict(tools["parts"])
    fixed = compound([names["body"], names["hotend hardware"], tools["envelope"], names["fan screws"], names["fan inserts"]])
    removable = compound(parts["bambu_hotend"].Solids()[3:5])
    path = [(0, 0, -i * 0.25) for i in range(17)] + [(0, -i, -4) for i in range(1, 41)]
    from build_refined_docking_review import translated_hits
    hits = [{"offset_mm": o, "hits": h} for o in path if (h := translated_hits(removable, {"Fixed": fixed}, o))]
    report["bambu_service_path"] = {"samples": len(path), "hits": hits}
    if hits:
        failures.append("Bambu hotend service path")


def volume_support(pad, dock_body):
    return pad.translate((0, 0, -0.01)).intersect(dock_body).Volume() / 0.01


def check_p28(report, failures):
    released = load("P28_Dock_and_Probe_Calibration_Jig")
    rebuilt = P.p28(2.27)
    new = P.p28(2.60)
    reproduced = same_properties(mass_properties(rebuilt), mass_properties(released))
    report["p28"] = {"rebuild_at_2p27_reproduces_released": reproduced, "feeler_mm": {"released": 2.27, "r37": 2.60},
                     "volume_mm3": {"released": released.Volume(), "r37": new.Volume()}}
    if not reproduced:
        failures.append("P28 rebuild does not reproduce the released jig")
    return new


# --------------------------------------------------------------------------------------------
# Requalification scene
# --------------------------------------------------------------------------------------------

def carriage(parts):
    b = parts["beacon"]
    out = [(R31["core"], load(R31["core"])), (P.NAMES["p22"], parts["p22"]), ("P20_CPAP_Hose_Inlet", load("P20_CPAP_Hose_Inlet")),
           ("P21_CPAP_Gantry_Bridge", load("P21_CPAP_Gantry_Bridge")), (P.NAMES["p23"], parts["p23"]),
           (R35["p24"], load(R35["p24"])), (P.NAMES["cable"], parts["cable"]),
           ("Beacon_RevH_Raised", compound(b[2:5])), ("EBB42", parts["ebb42"])]
    return out + list(parts["other_hardware"]) + list(parts["hardware"])


def write_scene(parts):
    from audit_ten_tool_rack import snapshot
    folder = r36.scene_dir()
    folder.mkdir(exist_ok=True)
    for old in folder.glob("*.brep"):
        old.unlink()
    counter = iter(range(10 ** 6))

    def put(s):
        name = f"s{next(counter):04d}.brep"
        s.exportBrep(str(folder / name))
        return name

    sources = {}
    flying, xgantry, crossbar = (snapshot(n, sources) for n in ("Flying_Gantry", "X_Gantry", "crossbar"))
    meta = json.loads((acc.WORK / "rack_audit_X_Gantry_world.json").read_text())
    flying_meta = json.loads((acc.WORK / "rack_audit_Flying_Gantry_world.json").read_text())
    dock37 = put(compound(parts["dock"]))
    manifest = {
        "frames": r36.frames(), "chute": put(parts["dock"][6]), "sources": sources,
        "carriage": [[n, put(s)] for n, s in carriage(parts)], "cartographer": put(parts["cartographer"]),
        # The revision-36 scene keys are reused: "dock_r36" is the revision-37 dock (every bay) and
        # "dock_r21" the revision-36 per-hotend dock, for the before/after side clearances.
        "variants": {label: {"parts": [[n, put(s)] for n, s in v["parts"]], "envelope": put(v["envelope"]),
                             "hotend": put(v["hotend"]), "dock_r21": put(load(f"36_{label}_Dock_Complete_REVIEW")),
                             "dock_r36": dock37} for label, v in parts["tools"].items()},
        "fixed": {"hardware": put(load("P29_Rack_Hardware_Complete")), "crossbar": put(crossbar),
                  "flying": put(flying), "xgantry": put(xgantry)},
        "bearing_ids": [i for i, m in enumerate(meta) if m["name"] in (
            "_MGN9H (10)", "_MGN9H (11)", "_MGN9H (12)", "_MGN9H (13)")],
        "rail_ids": [i for i, m in enumerate(flying_meta) if m["name"] in (
            "R1_GANTRY_Y_RAIL_left_400_NOMINAL", "R1_GANTRY_Y_RAIL_left_400_NOMINAL (1)")],
        "x_rail": next(item for item in meta if item["name"] == "R1_GANTRY_X_RAIL_400_NOMINAL")}
    (folder / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


def tools(bambu_hotend):
    out = r36.tool_parts()
    out["Bambu"]["parts"] = [(n, bambu_hotend if n == "hotend" else s) for n, s in out["Bambu"]["parts"]]
    out["Bambu"]["hotend"] = bambu_hotend
    return out


# --------------------------------------------------------------------------------------------
# Exports
# --------------------------------------------------------------------------------------------

def exports(parts, p28_new, report):
    files = []
    for key, s in (("p22", parts["p22"]), ("p23", parts["p23"]), ("p28", p28_new)):
        files += export_print(P.NAMES[key], s)
    for key, s in (("pad", parts["dock"][3]), ("wiper", parts["dock"][7])):
        files += export_print(P.NAMES[key], s)
    grey, brass, steel = (0.55, 0.57, 0.6), (0.8, 0.55, 0.2), (0.35, 0.35, 0.38)
    files.append(export_assembly(P.NAMES["hardware"], [
        (s, n, brass if "HEATSET" in n else steel) for n, s in parts["hardware"]], len(parts["hardware"])))
    path = STEP / f"{P.NAMES['cable']}.step"
    cq.exporters.export(parts["cable"], str(path))
    files.append(path)
    path = STEP / f"{P.NAMES['bambu_hotend']}.step"
    cq.exporters.export(parts["bambu_hotend"], str(path))
    if len(cq.importers.importStep(str(path)).val().Solids()) != 6:
        raise ValueError("Bambu hotend readback")
    files.append(path)
    dock_colors = [(0.95, 0.4, 0.1) if i in (3, 7) else (0.6, 0.6, 0.63) if i in (4, 5, 8, 9, 10, 11, 12, 13)
                   else (0.22, 0.4, 0.32) for i in range(14)]
    files.append(export_assembly(P.NAMES["dock"], [(s, n, c) for s, n, c in zip(parts["dock"], DOCK_NAMES, dock_colors)], 14))
    # Review assembly: the revision-37 carriage with a Bambu docked, and a Red Lizard parked at +37.3.
    items, expected = [], 0
    for n, s in carriage(parts):
        color = (0.95, 0.55, 0.12) if n in (P.NAMES["p22"], P.NAMES["p23"]) else (
            0.15, 0.35, 0.85) if n == P.NAMES["cable"] else (0.1, 0.1, 0.12) if n.startswith("Beacon") else (
            brass if "HEATSET" in n else steel if n.startswith(("ACC_", "R37_")) else grey)
        items.append((s, n, color))
        expected += len(s.Solids())
    for label, dx in (("Bambu", 0.0), ("RedLizard", PITCH)):
        for n, s in parts["tools"][label]["parts"]:
            items.append((s.translate((dx, 0, 0)), f"{label}_{n.replace(' ', '_')}",
                          (0.9, 0.65, 0.1) if label == "Bambu" and n == "body" else (0.85, 0.3, 0.12)
                          if n == "body" else (0.62, 0.62, 0.65)))
            expected += len(s.Solids())
        for (n, s), c in zip(zip(DOCK_NAMES, parts["dock"]), dock_colors):
            items.append((s.translate((dx, 0, 0)), f"{label}_Dock_{n}", c))
            expected += 1
    files.append(export_assembly(P.NAMES["review"], items, expected))
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p),
                          "mb": round(p.stat().st_size / 1e6, 1)} for p in files]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    started = time.perf_counter()
    failures = []
    report = {"status": "PENDING", "raise_mm": P.DZ}
    print("Building", flush=True)
    p22_new, air_new = P.p22()
    bambu_hotend, bambu_info = P.bambu_hotend()
    parts = {"tip": P.tip_datum(), "p22": p22_new, "p23": P.p23(), "cable": P.cable(), "beacon": P.beacon(),
             "cartographer": P.cartographer(), "ebb42": P.ebb42(), "hardware": P.probe_hardware(),
             "other_hardware": P.other_hardware(), "bambu_hotend": bambu_hotend, "bambu_info": bambu_info,
             "dock": P.dock(), "tools": tools(bambu_hotend)}
    print("Static checks", flush=True)
    check_p22(p22_new, air_new, report, failures)
    check_p23(parts["p23"], report, failures)
    static_checks(parts, report, failures)
    check_bambu_and_dock(parts, report, failures)
    p28_new = check_p28(report, failures)
    report["static_failures"] = list(failures)
    if failures:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        raise SystemExit(f"Static failures: {failures}")
    print("Writing the requalification scene", flush=True)
    manifest = write_scene(parts)
    report["sources"] = manifest["sources"]
    specs = r36.specs()
    print(f"Running {len(specs)} cases on {args.workers} workers", flush=True)
    results = fast_geometry.run_parallel(r36.run_task, specs, workers=args.workers)
    rack = {}
    r36.summarise(results, rack, failures)
    s = r36.scene()
    r36.rack_geometry(s, rack, failures)
    rack["clearances_mm"] = {"r36_docks": rack["clearances_mm"]["r21"], "r37_dock": rack["clearances_mm"]["r36"]}
    report["requalification"] = rack
    print("Exports", flush=True)
    exports(parts, p28_new, report)
    report["failures"] = failures
    report["status"] = ("PROBE_RAISED_P23_SCREWS_OFF_BEACON_DATUM_DOCKS_RACK_REQUALIFIED_CAD_REVIEW_NOT_MACHINE_QUALIFICATION"
                        if not failures else "FAILED_SEE_FAILURES")
    report["hardware"] = {
        "probe": "2x M3x6 low-profile SHCS (head 5.5 x 1.5) through the probe board and P23 into 2x M3 x 3 mm "
                 "heat-set inserts (OD 4.5) in P22. Replaces the M3 screws and captive nuts in P23.",
        "p23_to_p22": "2x M3x4 ISO 7380 button-head screws on the rear ears into 2x M3 x 3 mm inserts in P22. "
                      "Replaces 4x M3 screws whose heads sat between P23 and the probe board.",
        "modelled_shank_diameter_mm": 2 * P.SHANK_R}
    report["limitations"] = [
        "Rigid CAD and sampled straight paths. Insert pull-out, P23 creep under the probe clamp and the probe's "
        "electrical behaviour are not qualified.",
        "The Beacon's 1.1 mm top-side block is the manufacturer model's component volume; it is treated as occupied.",
        "The Bambu tip is restored to the datum from the reference's own cone; measure the real nozzle: its tip "
        "should be 38.75 mm below the two upper mounting-hole centres (Z-40.13).",
        "The Cartographer is checked in place of the Beacon; its own cable route is not modelled."]
    report["runtime_s"] = time.perf_counter() - started
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    brief = {k: report[k] for k in ("status", "failures", "probe_heights", "lowest_carriage_features_above_tip_mm",
                                    "thread_engagement_mm", "released_finding", "runtime_s")}
    brief["bed"] = rack["bed"]["summary"]
    brief["clearances_mm"] = {k: {kk: round(vv["mm"], 3) for kk, vv in v.items() if vv}
                              for k, v in rack["clearances_mm"].items()}
    print(json.dumps(brief, indent=1, default=str))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
