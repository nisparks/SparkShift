"""Revision 40: the P20-to-P21 screws, fixed in place; two design notes measured.

Released: the two M3x8 heads on P20's lug tops reach 0.9 mm into the EBB42's bottom edge and headers, and
P21's insert pockets for them are 0.28 mm from the probe-cable raceway and 0.57 mm from P20's sleeve
socket. Revision 40 moves both screws to X+-5.5, 1 mm forward, with ISO 7380 button heads seated in
P20's lugs. Only the lugs of P20 and P21 change.

Static checks (revision-37 carriage, revision-39 tools and docks):
- the parameterised P20/P21/P22 builders and the cable route reproduce the released parts;
- revision-40 P20 and P21 are single valid solids, unchanged outside their lugs, with the released air paths;
- the P20-to-P21 joint: pocket walls, head clearances to the EBB42 and the probe cable, thread engagement;
- every pair of carriage parts and fasteners, the mounted tools, the Cartographer and the Beacon keepouts;
- distances to the real Monolith X gantry are not reduced below the released parts' (or 0.5 mm).
Notes, measured without changing parts: P21's conduit against the X beam (with a 1.5 mm column-shift
study), and the stack's anchor holes in P24, which the core's own case screws fill.
Then, on a revision-40 scene (WORK/r40_scene): the revision-36 full-rack requalification and a sweep of
the carriage at the rear travel limit (nozzle Y359 and the rails' Y365.15) against the flying gantry.

Run: python build_inlet_screws_r40.py [--workers 10] [--static-only]
"""
import argparse
import json
import os
import time

import build_and_verify_accessories_v26 as acc

os.environ["SPARKSHIFT_SCENE"] = str(acc.WORK / "r40_scene")

import cadquery as cq  # noqa: E402

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import build_probe_height_datum_dock_r37 as b37  # noqa: E402
import fast_geometry as fg  # noqa: E402
import r37_parts as P37  # noqa: E402
import r39_parts as P39  # noqa: E402
import r40_parts as P  # noqa: E402
from audit_tool_owned_2510 import bounds, compound, overlaps  # noqa: E402
from build_bambu_clean_r29 import sha  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31, confined, mass_properties, same_properties  # noqa: E402
from build_fan_mounts_r33 import export_assembly, export_print  # noqa: E402
from build_modular_toolhead import ROOT, STEP, box, load  # noqa: E402
from build_p24_cable_entry_r35 import NAMES as R35  # noqa: E402
from build_refined_docking_review import translated_hits  # noqa: E402

REPORT = "verification_inlet_screws_r40.json"
DOCK_NOZZLE_Y = 20.71
REAR_LIMITS = (359.0, 365.15)
GANTRY_CENTERS = (0.0, 175.0, 350.0)
LUG_ZONE = (-9.8, 9.8, -35.7, -25.9, -27.2, -10.0)
CHANGED = (P.NAMES["p20"], P.NAMES["p21"])
RUNNING = ("R1_GANTRY_X_2020_430_NOMINAL", "R1_GANTRY_X_RAIL_400_NOMINAL")


def carriage(parts):
    b = parts["beacon"]
    out = [(R31["core"], load(R31["core"])), (P37.NAMES["p22"], parts["p22"]), (P.NAMES["p20"], parts["p20"]),
           (P.NAMES["p21"], parts["p21"]), (P37.NAMES["p23"], parts["p23"]), (R35["p24"], parts["p24"]),
           (P37.NAMES["cable"], parts["cable"]), ("Beacon_RevH_Raised", compound(b[2:5])), ("EBB42", parts["ebb42"])]
    return out + list(parts["other_hardware"]) + list(parts["hardware"])


def carriage_r39(parts):
    b = parts["beacon"]
    out = [(R31["core"], load(R31["core"])), (P37.NAMES["p22"], parts["p22"]),
           ("P20_CPAP_Hose_Inlet", load("P20_CPAP_Hose_Inlet")), ("P21_CPAP_Gantry_Bridge", load("P21_CPAP_Gantry_Bridge")),
           (P37.NAMES["p23"], parts["p23"]), (R35["p24"], parts["p24"]), (P37.NAMES["cable"], parts["cable"]),
           ("Beacon_RevH_Raised", compound(b[2:5])), ("EBB42", parts["ebb42"])]
    return out + P37.other_hardware() + list(parts["hardware"])


def build_parts():
    bambu_hotend, _ = P37.bambu_hotend()
    parts = {"p22": P37.p22()[0], "p23": P37.p23(), "p24": load(R35["p24"]), "cable": P37.cable(),
             "beacon": P37.beacon(), "cartographer": P37.cartographer(), "ebb42": P37.ebb42(),
             "hardware": P37.probe_hardware(), "dock": P37.dock(), "tools": b37.tools(bambu_hotend)}
    yf = P39.dock_face_y(parts["dock"])
    parts["dock"] = P39.dock(parts["dock"], yf)
    parts["tools"] = P39.tools(parts["tools"], P39.p18())
    parts["p20"], parts["air20"] = P.p20()
    parts["p21"], parts["air21"] = P.p21()
    parts["other_hardware"] = P.other_hardware()
    return parts


def volume(s):
    return s.Volume() if s is not None else 0.0


# --------------------------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------------------------

def check_regression(report, failures):
    mp = mass_properties
    rows = {
        "P20_builder_is_released_P20": same_properties(mp(P.shape(P.p20_base(0.0)[0])), mp(load("P20_CPAP_Hose_Inlet"))),
        "P21_builder_is_released_P21": same_properties(mp(P.shape(P.p21_base(0.0)[0])), mp(load("P21_CPAP_Gantry_Bridge"))),
        "P22_builder_is_revision_37_P22": same_properties(mp(P.shape(P.p22_base(0.0)[0])), mp(load(P37.NAMES["p22"]))),
        "cable_route_is_revision_37_cable": same_properties(mp(P.cable(0.0)), mp(load(P37.NAMES["cable"])))}
    report["builder_regression"] = rows
    if not all(rows.values()):
        failures.append("A parameterised builder does not reproduce its released part")


def check_parts(parts, report, failures):
    rows = {}
    for key, name, released in (("p20", "P20", "P20_CPAP_Hose_Inlet"), ("p21", "P21", "P21_CPAP_Gantry_Bridge")):
        s, old = parts[key], load(released)
        rows[name] = {"solids": len(s.Solids()), "valid": s.isValid(), "volume_mm3": s.Volume(),
                      "released_volume_mm3": old.Volume(), "bounds_mm": bounds(s), "released_bounds_mm": bounds(old),
                      "outside_lug_zone": confined(s.copy(), old.copy(), [LUG_ZONE])}
        if len(s.Solids()) != 1 or not s.isValid():
            failures.append(f"{name} is not one valid solid")
        if not rows[name]["outside_lug_zone"]["unchanged_outside_zones"]:
            failures.append(f"{name} changed outside its screw lugs")
    rows["lug_zone_mm"] = LUG_ZONE
    report["parts"] = rows


def check_air(parts, report, failures):
    a20, a21 = P.shape(P.p20_base(0.0)[1]), P.shape(P.p21_base(0.0)[1])
    rows = {"P20": {"released_mm3": a20.Volume(), "r40_mm3": parts["air20"].Volume(),
                    "released_part_in_air_mm3": volume(load("P20_CPAP_Hose_Inlet").intersect(a20)),
                    "r40_part_in_air_mm3": volume(parts["p20"].intersect(parts["air20"]))},
            "P21": {"released_mm3": a21.Volume(), "r40_mm3": parts["air21"].Volume(),
                    "released_part_in_air_mm3": volume(load("P21_CPAP_Gantry_Bridge").intersect(a21)),
                    "r40_part_in_air_mm3": volume(parts["p21"].intersect(parts["air21"]))},
            "note": "P21's 7.18 mm3 part-in-air is the released builder's own sliver at the cable-boss corners "
                    "(r3.00 in the part, r3.10 in its air model), unchanged."}
    report["air_paths"] = rows
    if any(abs(v["released_mm3"] - v["r40_mm3"]) > 1e-3 or abs(v["released_part_in_air_mm3"] - v["r40_part_in_air_mm3"]) > 1e-3
           for k, v in rows.items() if k != "note"):
        failures.append("CPAP air path changed")


def ring_fill(part, x, y, r_in, r_out, z0, z1):
    ring = cq.Solid.makeCylinder(r_out, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1)).cut(
        cq.Solid.makeCylinder(r_in, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1)))
    return volume(part.intersect(ring)) / ring.Volume()


def check_inlet_joint(parts, report, failures):
    socket_front = -33.20 - 0.84
    p21_old = load("P21_CPAP_Gantry_Bridge")
    rows = {
        "screw_xy_mm": {"released": [[-4.50, -31.20], [4.50, -31.20]], "r40": [[-P.LUG_X, P.LUG_Y], [P.LUG_X, P.LUG_Y]]},
        "p21_pocket_to_cable_raceway_mm": {"released": 4.50 - P.P21_INSERT_R - 1.95, "r40": P.LUG_X - P.P21_INSERT_R - 1.95},
        "p21_pocket_to_p20_sleeve_socket_mm": {"released": (-31.20 - P.P21_INSERT_R) - socket_front,
                                               "r40": (P.LUG_Y - P.P21_INSERT_R) - socket_front},
        "p21_pocket_1mm_ring_filled_fraction": {
            "released": min(ring_fill(p21_old, x, -31.20, P.P21_INSERT_R, P.P21_INSERT_R + 1.0, -21.30, -17.78)
                            for x in (-4.50, 4.50)),
            "r40": min(ring_fill(parts["p21"], x, P.LUG_Y, P.P21_INSERT_R, P.P21_INSERT_R + 1.0, -21.30, -17.78)
                       for x in (-P.LUG_X, P.LUG_X))},
        "p20_counterbore_to_cable_channel_mm": P.LUG_X - P.LUG_CBORE_R - 1.95,
        "p20_counterbore_outer_wall_mm": P.P20_LUG_R - P.LUG_CBORE_R,
        "p20_floor_under_head_mm": P.LUG_HEAD_SEAT - (-17.78),
        "head_radial_clearance_mm": P.LUG_CBORE_R - P.BUTTON_HEAD_R,
        "thread_engagement_mm": P.P21_INSERT_Z[1] - P.P21_INSERT_Z[0],
        "screw_tip_z_mm": P.LUG_HEAD_SEAT - 8.0, "clearance_hole_bottom_z_mm": -27.0}
    rig = dict(carriage(parts))
    eb = fg.index_group([("EBB42", rig["EBB42"])])
    cab = fg.index_group([("cable", parts["cable"])])
    new_heads = [(n, s) for n, s in parts["other_hardware"] if n.startswith("R40_INLET_M3x8")]
    old_heads = [(n, s) for n, s in P37.other_hardware() if n.startswith("ACC_UPPER_INLET_M3x8")]
    rows["head_to_ebb42_mm"] = {"r40": min(fg.min_distance(fg.index_group([h]), eb, cutoff=5.0)[0] for h in new_heads),
                                "released_overlap_mm3": sum(volume(s.intersect(rig["EBB42"])) for _, s in old_heads)}
    rows["head_to_probe_cable_mm"] = {"r40": fg.min_distance(fg.index_group(new_heads), cab, cutoff=5.0)[0],
                                      "released": fg.min_distance(fg.index_group(old_heads), cab, cutoff=5.0)[0]}
    report["inlet_joint"] = rows
    if rows["p21_pocket_1mm_ring_filled_fraction"]["r40"] < 0.999 or rows["p20_counterbore_to_cable_channel_mm"] < 0.45 \
            or rows["head_to_ebb42_mm"]["r40"] < 0.3 or rows["head_to_probe_cable_mm"]["r40"] < 0.8:
        failures.append("P20-to-P21 joint walls or clearances")


def split_contacts(rows, shapes):
    """Separate zero-thickness face contacts from real interferences."""
    real, touch = [], []
    for r in rows:
        b = bounds(shapes[r["a"]].intersect(shapes[r["b"]]))
        thin = min(b[1] - b[0], b[3] - b[2], b[5] - b[4])
        (touch if thin < 0.01 else real).append(dict(r, min_thickness_mm=thin))
    return real, touch


def check_carriage(parts, report, failures):
    rig = dict(carriage(parts))
    changed = {n: s for n, s in rig.items() if n in CHANGED or n.startswith("R40_")}
    rows, contacts = split_contacts(b37.overlap_rows(rig, rig, skip=b37.beacon_internal), rig)
    old = dict(carriage_r39(parts))
    old_rows, old_contacts = split_contacts(b37.overlap_rows(old, old, skip=b37.beacon_internal), old)
    report["carriage_internal"] = {
        "checked": "Every pair of carriage parts and fasteners (core, P20-P24, cable, Beacon, EBB42, all fasteners); "
                   "earlier revisions checked only their changed parts against the rest.",
        "intersections_mm3": rows, "face_contacts": contacts,
        "revision_39_intersections_mm3": old_rows, "revision_39_face_contacts": old_contacts,
        "note": "A face contact is a Boolean common under 0.01 mm thick: two faces that touch, such as a screw "
                "head bearing on the EBB42 board, not an interference."}
    if rows:
        failures.append("Carriage-internal intersection")
    carto = b37.overlap_rows({"Cartographer": parts["cartographer"]}, changed)
    report["cartographer_vs_changed_mm3"] = carto
    if carto:
        failures.append("Cartographer intersection")
    mounted = []
    for label, v in parts["tools"].items():
        for name, s in v["parts"]:
            mounted += [{"tool": label, "part": name, "b": t, "mm3": m} for t, m in overlaps(s, changed).items()]
    report["mounted_tools_vs_changed_mm3"] = mounted
    if mounted:
        failures.append("Mounted tool intersects the revision-40 carriage")
    b = parts["beacon"]
    metal = {n: s for n, s in parts["other_hardware"] if n.startswith("R40_")}
    report["beacon_keepouts_metal_mm3"] = {k: overlaps(ko, metal) for k, ko in
                                          (("top", P37.beacon_top_keepout(b)), ("bottom", b[0]))}
    if any(report["beacon_keepouts_metal_mm3"].values()):
        failures.append("Metal in a Beacon keepout")


# --------------------------------------------------------------------------------------------
# X gantry distances and the two notes
# --------------------------------------------------------------------------------------------

def x_gantry_local(center):
    from audit_ten_tool_rack import snapshot
    f = r36.frames()
    world = snapshot("X_Gantry", {}).translate((0, f["x_gantry_y_shift_to_dock_mm"], 0))
    return world.rotate((0, 0, 0), (0, 0, 1), 180).translate((center, f["world_y_offset_mm"], -f["world_z_offset_mm"]))


def gantry_groups(center):
    meta = json.loads((acc.WORK / "rack_audit_X_Gantry_world.json").read_text())
    g = [(m["name"], s) for m, s in zip(meta, x_gantry_local(center).Solids())
         if bounds(s)[0] < 70 and bounds(s)[1] > -70]
    return [x for x in g if x[0] in RUNNING], [x for x in g if x[0] not in RUNNING]


def nearest(parts_by_name, targets, cutoff=6.0):
    out, tg = {}, fg.index_group(targets)
    for name, s in parts_by_name.items():
        hit = fg.min_distance(fg.index_group([(name, s)]), tg, cutoff=cutoff)
        out[name] = None if hit is None else {"mm": hit[0], "gantry_body": hit[2], "at_mm": [round(v, 2) for v in hit[3]]}
    return out


def check_gantry(parts, report, failures):
    """The changed parts must not come closer to the X gantry than the released ones (or 0.5 mm)."""
    new = {"P20": parts["p20"], "P21": parts["p21"], **{n: s for n, s in parts["other_hardware"] if n.startswith("R40_")}}
    old = {"P20": load("P20_CPAP_Hose_Inlet"), "P21": load("P21_CPAP_Gantry_Bridge"),
           **{n: s for n, s in P37.other_hardware() if n.startswith("ACC_UPPER_INLET")}}
    out = {}
    for c in GANTRY_CENTERS:
        beam, ends = gantry_groups(c)
        out[f"carriage_at_world_x{c:.0f}"] = {"beam_and_rail": {"r40": nearest(new, beam), "released": nearest(old, beam)},
                                              "end_joints": {"r40": nearest(new, ends), "released": nearest(old, ends)}}
    report["x_gantry_min_distance"] = out

    def worst(kind, version, name):
        hits = [v[kind][version].get(name) for v in out.values()]
        hits = [h["mm"] for h in hits if h]
        return min(hits) if hits else None
    rows = {}
    for kind in ("beam_and_rail", "end_joints"):
        for part in ("P20", "P21"):
            r40, rel = worst(kind, "r40", part), worst(kind, "released", part)
            rows[f"{part}_{kind}_mm"] = {"r40": r40, "released": rel}
            if r40 is not None and r40 < min(rel if rel is not None else 6.0, 0.5) - 1e-6:
                failures.append(f"{part} closer to the X gantry ({kind}) than released")
    report["x_gantry_summary"] = rows


def rear_clearance(column, nozzle_y, xs, mounts):
    f = r36.frames()
    mg = fg.index_group(mounts)
    best = None
    for x in xs:
        for name, s in column.items():
            w = r36.world(s, 0, f).translate((x, nozzle_y - DOCK_NOZZLE_Y, 0))
            hit = fg.min_distance(fg.index_group([(name, w)]), mg, cutoff=20.0)
            if hit and (best is None or hit[0] < best["mm"]):
                best = {"mm": hit[0], "part": name, "gantry_body": hit[2], "carriage_x_mm": x}
    return best


def notes(parts, report):
    """Measured, no part change: the conduit against the X beam, and the stack's anchor."""
    from audit_ten_tool_rack import snapshot
    beam, _ = gantry_groups(175.0)
    released = {"P20": load("P20_CPAP_Hose_Inlet"), "P21": load("P21_CPAP_Gantry_Bridge"), "P22": parts["p22"],
                "Probe_Cable": parts["cable"]}
    d = P.DY_STUDY
    shifted = {"P20": P.shape(P.p20_base(d, 4.50, -31.20 + d)[0]),
               "P21": P.shape(P.p21_base(d, P.FAIRING_Z_STUDY, 4.50, -31.20 + d)[0]),
               "P22": P.shape(P.p22_base(d)[0]), "Probe_Cable": P.cable(d)}
    fm = json.loads((acc.WORK / "rack_audit_Flying_Gantry_world.json").read_text())
    flying = snapshot("Flying_Gantry", {}).Solids()
    mounts = [(m["name"], s) for m, s in zip(fm, flying) if "rear_motor_mount" in m["name"] or "tensioner" in m["name"]]
    xs = (0, 10, 40, 310, 340, 350)
    report["note_conduit_on_x_beam"] = {
        "finding": "In the Monolith gantry model, P21's conduit front face lies on the X beam's rear face (Y-33.20) "
                   "and the probe cable runs 0.2 mm from it, over the whole X travel. The original accessory audit "
                   "used an older gantry model with the beam's rear face at Y-32.70 (0.5 mm).",
        "released_to_beam_and_rail_mm": nearest(released, beam),
        "study_column_moved_mm": d,
        "study_note": "P20, P21's conduit, P22's collar, riser and elbow and the cable riser moved rearward; P21's "
                      "fairing underside raised to Z-27.0; P20's wing seats, P24 and P22's plenum stay put.",
        "study_to_beam_and_rail_mm": nearest(shifted, beam),
        "rear_motor_mounts_at_nozzle_y359_mm": {"released": rear_clearance(released, 359.0, xs, mounts),
                                                "study": rear_clearance(shifted, 359.0, xs, mounts)}}
    meta = json.loads((acc.WORK / "v26_meta.json").read_text())
    core = {m["name"]: s for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))}

    def along_y(shape, x, z, r=1.3):
        common = shape.intersect(cq.Solid.makeCylinder(r, 80.0, cq.Vector(x, -40.0, z), cq.Vector(0, 1, 0)))
        b = bounds(common)
        return [b[2], b[3]]
    anchor = {}
    for label, (x, z), screw, insert in (("upper", P.UPPER_CLAMP, "UPPER_RIGHT_SHARED_M3x35_FRAME",
                                          "UPPER_RIGHT_REAR_M3_HEATSET_4p6x4"),
                                         ("lower", P.LOWER_CLAMP, "LOWER_CASE_M3x35_BUTTON", "CLAM_M3_FRAME_INSERT_3")):
        sy, iy = along_y(P37.shape(core[screw]), x, z, 0.6), along_y(P37.shape(core[insert]), x, z, 2.0)
        anchor[label] = {"axis_xz_mm": [x, z], "core_screw_y_mm": sy, "core_insert_y_mm": iy,
                         "free_thread_behind_core_screw_mm": sy[0] - iy[0]}
    report["note_stack_anchor"] = {
        "finding": "P24's two rear holes line up with the core's right case-clamp inserts in P02, but the core's own "
                   "M3x35 case screws, fitted from the front, already fill them. No screw for P24 was ever specified "
                   "and none can engage, so nothing screws P20, P21, P24 or the EBB42 to the carriage: the stack rests "
                   "on P22's collar, against P02's rear face and under P02, located by P24's pockets over three core "
                   "screw heads.",
        "holes": anchor,
        "options": ["Core change note: separate anchor inserts in P02 for P24, or longer inserts shared by both screws.",
                    "Accessory option: two M2.5 screws from below in the column's chamfered rear corners, inside its "
                    "outline (not adopted).",
                    "A rear foot on P21 screwed to a ledge on P22 was tried and rejected: at the stock rear limit it "
                    "hits the rear motor mounts near X0 and X350."]}


# --------------------------------------------------------------------------------------------
# Rear travel (worker task) and the dispatcher the workers import
# --------------------------------------------------------------------------------------------

def rear_group(name):
    for key in ("P20", "P21", "P22", "P23", "P24", "EBB42", "Beacon", "Probe_Cable", "Core"):
        if name.startswith(key):
            return key
    return "Hardware"


def task_rear_travel(s, nozzle_y, xs):
    f, groups = s["frames"], {}
    for n, p in s["carriage_parts"]:
        groups.setdefault(rear_group(n), []).append(p)
    world = {k: r36.world(compound(v), 0, f) for k, v in groups.items()}
    flying = s["fixed"]["Flying_Gantry"]
    dy, hits = nozzle_y - DOCK_NOZZLE_Y, []
    for x in xs:
        for k, w in world.items():
            h = translated_hits(w, {"Flying_Gantry": flying}, (x, dy, 0))
            if h:
                hits.append({"x_mm": x, "part": k, "mm3": h["Flying_Gantry"]})
    rear = [(k, world[k]) for k in ("P20", "P21", "P22", "Hardware") if k in world]
    near, fly = None, fg.index_group([("Flying_Gantry", flying)])
    for x in (xs[0], xs[-1]):
        hit = fg.min_distance(fg.index_group(rear), fly, (x, dy, 0), (0, 0, 0), cutoff=30.0)
        if hit and (near is None or hit[0] < near["mm"]):
            near = {"mm": hit[0], "part": hit[1], "x_mm": x}
    return {"nozzle_y_mm": nozzle_y, "x_mm": [xs[0], xs[-1]], "samples": len(xs), "hits": hits, "nearest": near}


def run_task(spec):
    if spec["kind"] == "rear_travel":
        started = time.perf_counter()
        result = task_rear_travel(r36.scene(), **spec["args"])
        return {**spec, "result": result, "seconds": time.perf_counter() - started}
    return r36.run_task(spec)


def rear_specs():
    return [{"kind": "rear_travel", "args": {"nozzle_y": y, "xs": list(range(a, b, 2))}}
            for y in REAR_LIMITS for a, b in ((0, 60), (60, 120), (120, 180), (180, 240), (240, 300), (300, 352))]


def summarise_rear(results, report, failures):
    rows = [r for r in results if r["kind"] == "rear_travel"]
    out = {}
    for y in REAR_LIMITS:
        mine = [r["result"] for r in rows if r["args"]["nozzle_y"] == y]
        near = [m["nearest"] for m in mine if m["nearest"]]
        out[f"nozzle_y{y}"] = {"samples": sum(m["samples"] for m in mine),
                               "hits": [h for m in mine for h in m["hits"]],
                               "nearest_rear_part_mm": min(near, key=lambda n: n["mm"]) if near else None}
        if out[f"nozzle_y{y}"]["hits"]:
            failures.append(f"Carriage hits the flying gantry at nozzle Y{y}")
    report["rear_travel"] = out


# --------------------------------------------------------------------------------------------
# Exports
# --------------------------------------------------------------------------------------------

def exports(parts, report):
    files = export_print(P.NAMES["p20"], parts["p20"]) + export_print(P.NAMES["p21"], parts["p21"])
    brass, steel = (0.8, 0.55, 0.2), (0.35, 0.35, 0.38)
    hw = [(n, s) for n, s in parts["other_hardware"] if n.startswith("R40_")]
    files.append(export_assembly(P.NAMES["hardware"], [(s, n, brass if "HEATSET" in n else steel) for n, s in hw],
                                 len(hw)))
    items, expected = [], 0
    for n, s in carriage(parts):
        color = (0.95, 0.55, 0.12) if n in CHANGED else (0.15, 0.35, 0.85) if n == P37.NAMES["cable"] else (
            0.1, 0.1, 0.12) if n.startswith("Beacon") else (0.13, 0.45, 0.2) if n == "EBB42" else (
            brass if "HEATSET" in n else steel if n.startswith(("ACC_", "R37_", "R40_")) else (0.55, 0.57, 0.6))
        items.append((s, n, color))
        expected += len(s.Solids())
    beam, _ = gantry_groups(175.0)
    clip = box(-60, 60, -40, 0, -60, -20)
    for n, s in beam:
        items.append((s.intersect(clip), f"Reference_{n}", (0.75, 0.75, 0.78)))
        expected += 1
    files.append(export_assembly(P.NAMES["assembly"], items, expected))
    report["review_bodies"] = expected
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p), "mb": round(p.stat().st_size / 1e6, 1)}
                         for p in files]


# --------------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--static-only", action="store_true", help="stop after the static checks and notes")
    args = parser.parse_args()
    started = time.perf_counter()
    failures = []
    report = {"status": "PENDING"}
    print("Building", flush=True)
    parts = build_parts()
    print("Static checks", flush=True)
    check_regression(report, failures)
    check_parts(parts, report, failures)
    check_air(parts, report, failures)
    check_inlet_joint(parts, report, failures)
    check_carriage(parts, report, failures)
    check_gantry(parts, report, failures)
    print("Notes", flush=True)
    notes(parts, report)
    report["static_failures"] = list(failures)
    if failures or args.static_only:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps({k: report.get(k) for k in (
            "static_failures", "builder_regression", "inlet_joint", "carriage_internal", "x_gantry_summary",
            "note_conduit_on_x_beam", "note_stack_anchor")}, indent=1, default=str))
        if failures:
            raise SystemExit(f"Static failures: {failures}")
        return

    print("Writing the revision-40 scene", flush=True)
    b37.carriage = carriage                          # write_scene takes the carriage from this module
    manifest = b37.write_scene(parts)
    report["sources"] = manifest["sources"]
    specs = r36.specs() + rear_specs()
    print(f"Requalification and rear travel: {len(specs)} cases on {args.workers} workers", flush=True)
    results = fg.run_parallel(run_task, specs, workers=args.workers)
    rack = {}
    r36.summarise([r for r in results if r["kind"] != "rear_travel"], rack, failures)
    r36.rack_geometry(r36.scene(), rack, failures)
    rack["clearances_mm"] = {"r36_docks": rack["clearances_mm"]["r21"], "r39_dock": rack["clearances_mm"]["r36"]}
    report["requalification"] = rack
    summarise_rear(results, report, failures)

    print("Exports", flush=True)
    exports(parts, report)
    report["hardware"] = {
        "changed": "P20 to P21: 2x M3x8 ISO 7380 button-head screws (were socket heads) at X+-5.5, 1 mm forward, "
                   "seated 1.6 mm down in P20's lugs, into the same 2x M3 x 3 mm (OD 4.5) inserts, which move with "
                   "them in P21's top flange. Fit them before the EBB42: they sit under its board.",
        "unchanged": "Everything else, including P22, P24 and their screws."}
    report["failures"] = failures
    report["status"] = ("P20_P21_SCREWS_CLEAR_RACK_REQUALIFIED_CAD_REVIEW_NOT_MACHINE_QUALIFICATION"
                        if not failures else "FAILED_SEE_FAILURES")
    report["limitations"] = [
        "Rigid CAD, sampled straight paths. Insert pull-out and printed-part creep are not qualified.",
        "The two notes are measured on the user's nominal Monolith model; real extrusion and printed-joint "
        "tolerances decide whether the conduit actually rubs the beam."]
    report["runtime_s"] = round(time.perf_counter() - started, 1)
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    brief = {k: report[k] for k in ("status", "failures", "runtime_s", "x_gantry_summary")}
    brief["rear_travel"] = {k: {"hits": len(v["hits"]), "nearest": v["nearest_rear_part_mm"]}
                            for k, v in report["rear_travel"].items()}
    brief["bed"] = rack["bed"]["summary"]
    brief["clearances_mm"] = {k: {kk: round(vv["mm"], 3) for kk, vv in v.items() if vv}
                              for k, v in rack["clearances_mm"].items()}
    print(json.dumps(brief, indent=1, default=str))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
