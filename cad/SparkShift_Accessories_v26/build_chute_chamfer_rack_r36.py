"""Revision 36: chamfer the chute arms, then requalify the full ten-tool rack with every current part.

P26 chute. With the revision-31 carriage, the active carriage passes the neighbouring dock's P26 at
1.73 mm on both sides: P22's rounded lower outer edge against the sharp top outer edge of the
chute's side arm (X+/-15, Z-78.80). Revision 32 suggested narrowing the arms to X+/-14, but each
arm is a tube around the M3 screw-head channel (dia. 5.5 at X+/-11.75) with a 0.5 mm outer wall,
so narrowing would open the channel. Instead, that top outer edge gets a 1.5 mm x 45 deg chamfer
along the arm (Y15..45.91). This only removes material, and leaves about 1 mm of wall around the
channel.

Full rack. Revisions 30-35 changed the toolheads (fan position, shelf trims, fan mounts) and the
carriage (P01 bosses, P22 mounts, P24 cable slot). Each change was checked locally. This script
reruns the revision-21 ten-tool qualification with all of them together and the revision-36
docks, and adds the revision-34 bed front edge as a gate:
- each tool docking into and withdrawing from its own dock, and the carriage backing away;
- all eight mixed neighbour cases at +/-37.3 mm;
- all 20 bay/hotend cases against the crossbar, P29/P30 hardware and flying gantry;
- the X gantry backing out over the full rack, and both tools traversing X0..350 at 60 mm withdrawal;
- the bed with its front edge at Y40 (and the shifted stock bed) at first-layer and touch heights,
  plus the frame below the bed plane;
- the Cartographer as the alternative probe;
- side clearances with the revision-21 and revision-36 docks.

The independent cases run in parallel worker processes on a cached scene.
"""

import argparse
import hashlib
import json
import time

import cadquery as cq
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.gp import gp_Vec

import build_and_verify_accessories_v26 as acc
import fast_geometry
from audit_tool_owned_2510 import bounds, compound, overlaps
from build_bambu_clean_r29 import sha, single
from build_bambu_clean_r30 import PITCH, fan_parts
from build_carriage_lowered_mounts_r31 import MOUNT_DZ, NAMES as R31, confined
from build_fan_mounts_r33 import NAMES as R33, RL_SEAT_X, export_assembly, export_print, red_lizard_parts, tool_sets
from build_modular_toolhead import ROOT, STEP, box, cylinder_y, load, volume, primitives
from build_p24_cable_entry_r35 import NAMES as R35
from build_refined_docking_review import DOCK_NAMES, DOCK_STANDOFF_MM, translated_hits

CHAMFER = 1.5
ARM_X, ARM_TOP, ARM_Y = 15.0, -78.80, (15.0, 45.910082)
SCREW_X, SCREW_Z, HEAD_R, CHANNEL_Y = 11.75, -82.44, 2.75, (14.0, 39.91)
MIN_WALL = 1.0
OLD_CHUTE = "P26_Nozzle_Entry_Clearance_Chute_REVIEW"
NAMES = {"chute": "P26_Chute_Arm_Chamfer_R36_REVIEW", "Bambu": "36_Bambu_Dock_Complete_REVIEW",
         "RedLizard": "36_RedLizard_Dock_Complete_REVIEW", "rack": "36_Ten_Tool_Rack_Requalified_REVIEW"}
REPORT = "verification_rack_requalification_r36.json"
SCENE = primitives.WORK / "r36_scene"
CENTERS = [7.0 + PITCH * i for i in range(10)]
DY = (0, -1, -3, -10, -30)
VARIANTS = ("Bambu", "RedLizard")


# ---------------------------------------------------------------------------------------------
# Revision-36 chute
# ---------------------------------------------------------------------------------------------

def prism_xz(points, y0, y1):
    """Closed XZ polygon at Y=y0, extruded to Y=y1."""
    vertices = [cq.Vector(x, y0, z) for x, z in points]
    face = cq.Face.makeFromWires(cq.Wire.makePolygon(vertices + vertices[:1]))
    return cq.Shape.cast(BRepPrimAPI_MakePrism(face.wrapped, gp_Vec(0, y1 - y0, 0)).Shape())


def chamfer_cutters():
    """One triangular prism per arm: its inner face is the 45 deg chamfer plane through the edge."""
    cutters = []
    for s in (-1, 1):
        x0 = ARM_X * s
        corner = [(x0 - CHAMFER * s, ARM_TOP), (x0 + s, ARM_TOP + 1.0), (x0, ARM_TOP - CHAMFER)]
        cutters.append(prism_xz(corner, ARM_Y[0] - 1.0, ARM_Y[1] + 1.0))
    return cutters


def build_chute():
    old = single(load(OLD_CHUTE), "revision-21 chute")
    cutters = chamfer_cutters()
    new = old.copy()
    for cutter in cutters:
        new = new.cut(cutter)
    new = single(new.clean(), "revision-36 chute")
    zones = [(ARM_X * s - CHAMFER - 0.01 if s > 0 else -ARM_X - 0.01,
              ARM_X + 0.01 if s > 0 else -ARM_X + CHAMFER + 0.01,
              ARM_Y[0] - 0.01, ARM_Y[1] + 0.01, ARM_TOP - CHAMFER - 0.01, ARM_TOP + 0.01) for s in (1, -1)]
    removed = volume(old) - volume(new)
    expected = sum(volume(old.copy().intersect(c)) for c in cutters)
    walls = {f"x{s * SCREW_X:+.2f}": cylinder_y(s * SCREW_X, SCREW_Z, *CHANNEL_Y, HEAD_R).distance(cutter)
             for s, cutter in zip((-1, 1), cutters)}
    report = {"chamfer_mm": CHAMFER, "edge": f"X+/-{ARM_X}, Z{ARM_TOP}, Y{ARM_Y[0]}..{ARM_Y[1]:.2f}",
              "released_volume_mm3": volume(old), "r36_volume_mm3": volume(new), "removed_mm3": removed,
              "added_mm3": volume(new.copy().cut(old.copy())),
              "confinement": confined(new.copy(), old.copy(), zones),
              "wall_to_m3_head_channel_mm": walls,
              "wall_note": "Thinnest remaining wall between the chamfer and each M3 screw-head channel "
                           "(dia. 5.5). The channel's existing side wall at X+/-15 is 0.5 mm and is unchanged."}
    failures = []
    if not report["confinement"]["unchanged_outside_zones"]:
        failures.append("Chute changed outside the two chamfer zones")
    if report["added_mm3"] > 1e-4 or abs(removed - expected) > 1e-3:
        failures.append("Chamfer is not a pure removal")
    if min(walls.values()) < MIN_WALL:
        failures.append(f"Chamfer leaves {min(walls.values()):.2f} mm to an M3 head channel")
    return new, report, failures


def dock_sets(chute):
    old = single(load(OLD_CHUTE), "revision-21 chute")
    out = {}
    for label in VARIANTS:
        solids = list(load(f"21_{label}_Closed_Panel_Dock_Complete_REVIEW").Solids())
        if len(solids) != len(DOCK_NAMES) or abs(volume(solids[6]) - volume(old)) > 1e-3 or max(
                abs(p - q) for p, q in zip(bounds(solids[6]), bounds(old))) > 1e-3:
            raise ValueError(f"{label} revision-21 dock does not hold the released chute as solid 6")
        out[label] = {"r21": solids, "r36": solids[:6] + [chute] + solids[7:]}
    return out


# ---------------------------------------------------------------------------------------------
# Scene: every current part, written once as BREP for the worker processes
# ---------------------------------------------------------------------------------------------

def coupling():
    pins = [cylinder_y(x, 22, 38.5, 48.5, 2.48).fuse(
        cq.Solid.makeCone(2.48, 1, 2, cq.Vector(x, 48.5, 22), cq.Vector(0, 1, 0))) for x in (-6, 6)]
    magnets = [cylinder_y(x, -2, 41.7, 45.7, 3) for x in (-6, 6)]
    return compound([*pins, *magnets])


def carriage_parts():
    parts = [(name, load(name)) for name in (
        R31["core"], R31["p22"], "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
        "P23_Beacon_Cartographer_Mount", R35["p24"], R35["cable"])]
    beacon = [cq.Shape.cast(s).translate((0, 3.2, -75)) for s in
              primitives.load_step(primitives.SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")]
    parts.append(("Beacon_RevH", compound(beacon[2:5])))
    parts.append(("EBB42", compound(
        cq.Shape.cast(s).translate((-20, -20, 0)).rotate((0, 0, 0), (0, 1, 0), 180).rotate(
            (0, 0, 0), (1, 0, 0), 90).translate((-1.248, -31.630, 6.5))
        for s, _ in primitives.load_brep_list(primitives.WORK / "ebb42_cache.brep"))))
    # All accessory fasteners, with the P22-to-P01 boss hardware at its revision-31 height.
    parts += [(name, cq.Shape.cast(s)) for name, s in acc.build_accessory_hardware(MOUNT_DZ)]
    cartographer = compound(cq.Shape.cast(s).rotate((0, 0, 0), (0, 0, 1), 180).translate((0, -13.00701, -75))
                            for s in primitives.load_step(
                                primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")[:100])
    return parts, cartographer


def tool_parts():
    bodies = {"Bambu": load(R33["bambu"]), "RedLizard": load(R33["redlizard"])}
    fan_and_screws = load(R33["bambu_fan"]).Solids()
    fan, _, envelope = fan_parts()
    if len(fan_and_screws) != 4 or abs(volume(fan_and_screws[0]) - volume(fan)) > 1e-3:
        raise ValueError("Unexpected revision-33 Bambu fan/screw export")
    hardware = {"Bambu": {"inserts": load(R33["bambu_inserts"]), "screws": compound(fan_and_screws[1:])},
                "RedLizard": {"inserts": load(R33["redlizard_inserts"])}}
    sets = tool_sets(bodies, hardware)
    if len(red_lizard_parts()["p18"].Solids()) != 5:
        raise ValueError("Red Lizard P18 snapshot should carry its two pins and two magnets")
    out = {}
    for label, t in sets.items():
        parts = list(t["parts"])
        if label == "Bambu":
            # Revision 33's Bambu set has the bare P18; the Red Lizard snapshot already carries these.
            parts.append(("coupling pins and magnets", coupling()))
        out[label] = {"parts": parts,
                      "envelope": envelope if label == "Bambu" else box(RL_SEAT_X, RL_SEAT_X + 10, 13, 38, -47.8, -22.8),
                      "hotend": load("Tool2510_Reversed_Bambu_Reference_REVIEW" if label == "Bambu"
                                     else "P17M_RedLizard_Hotend_Reference")}
    return out


def frames():
    f = json.loads((primitives.WORK / "rack_audit_frames.json").read_text())
    if abs(f["world_y_offset_mm"] - 36.91) > 0.001 or abs(f["world_z_offset_mm"] - 191.2794) > 0.001:
        raise ValueError("Unexpected dock world frame")
    f["world_y_offset_mm"] += DOCK_STANDOFF_MM
    f["x_gantry_y_shift_to_dock_mm"] += DOCK_STANDOFF_MM
    return f


def world(shape, center, f):
    return shape.rotate((0, 0, 0), (0, 0, 1), 180).translate(
        (center, f["world_y_offset_mm"], f["world_z_offset_mm"]))


def write_scene(chute, docks):
    from audit_ten_tool_rack import snapshot
    SCENE.mkdir(exist_ok=True)
    for old in SCENE.glob("*.brep"):
        old.unlink()
    counter = iter(range(10 ** 6))

    def put(shape):
        name = f"s{next(counter):04d}.brep"
        shape.exportBrep(str(SCENE / name))
        return name

    sources = {}
    carriage, cartographer = carriage_parts()
    tools = tool_parts()
    flying = snapshot("Flying_Gantry", sources)
    xgantry = snapshot("X_Gantry", sources)
    crossbar = snapshot("crossbar", sources)
    meta = json.loads((primitives.WORK / "rack_audit_X_Gantry_world.json").read_text())
    flying_meta = json.loads((primitives.WORK / "rack_audit_Flying_Gantry_world.json").read_text())
    manifest = {
        "frames": frames(), "chute": put(chute), "sources": sources,
        "carriage": [[n, put(s)] for n, s in carriage], "cartographer": put(cartographer),
        "variants": {label: {"parts": [[n, put(s)] for n, s in v["parts"]], "envelope": put(v["envelope"]),
                             "hotend": put(v["hotend"]),
                             "dock_r21": put(compound(docks[label]["r21"])),
                             "dock_r36": put(compound(docks[label]["r36"]))} for label, v in tools.items()},
        "fixed": {"hardware": put(load("P29_Rack_Hardware_Complete")), "crossbar": put(crossbar),
                  "flying": put(flying), "xgantry": put(xgantry)},
        "bearing_ids": [i for i, m in enumerate(meta) if m["name"] in (
            "_MGN9H (10)", "_MGN9H (11)", "_MGN9H (12)", "_MGN9H (13)")],
        "rail_ids": [i for i, m in enumerate(flying_meta) if m["name"] in (
            "R1_GANTRY_Y_RAIL_left_400_NOMINAL", "R1_GANTRY_Y_RAIL_left_400_NOMINAL (1)")],
        "x_rail": next(item for item in meta if item["name"] == "R1_GANTRY_X_RAIL_400_NOMINAL"),
    }
    if len(manifest["bearing_ids"]) != 4 or len(manifest["rail_ids"]) != 2:
        raise ValueError("Unexpected inherited bearing/rail reference components")
    (SCENE / "manifest.json").write_text(json.dumps(manifest, indent=1))
    return manifest


_SCENE = None


def scene():
    global _SCENE
    if _SCENE is not None:
        return _SCENE
    m = json.loads((SCENE / "manifest.json").read_text())
    read = lambda name: cq.Shape.importBrep(str(SCENE / name))
    f = m["frames"]
    s = {"frames": f, "manifest": m, "carriage_parts": [(n, read(p)) for n, p in m["carriage"]],
         "cartographer": read(m["cartographer"]), "variants": {}}
    s["carriage"] = compound([p for _, p in s["carriage_parts"]])
    for label, v in m["variants"].items():
        parts = [(n, read(p)) for n, p in v["parts"]]
        dock = read(v["dock_r36"])
        s["variants"][label] = {"parts": parts, "tool": compound([p for _, p in parts]), "dock": dock,
                                "dock_solids": list(dock.Solids()), "dock_r21": list(read(v["dock_r21"]).Solids()),
                                "envelope": read(v["envelope"]), "hotend": read(v["hotend"])}
    fx = {k: read(p) for k, p in m["fixed"].items()}
    flying, rails = fx["flying"].Solids(), set(m["rail_ids"])
    xg = fx["xgantry"].translate((0, f["x_gantry_y_shift_to_dock_mm"], 0))
    s["fixed"] = {"P29_P30_Hardware": fx["hardware"], "Crossbar": fx["crossbar"], "Flying_Gantry": fx["flying"]}
    s["flying_rails"] = compound(x for i, x in enumerate(flying) if i in rails)
    s["flying_without_rails"] = compound(x for i, x in enumerate(flying) if i not in rails)
    s["xgantry"] = xg
    s["x_without_bearings"] = compound(x for i, x in enumerate(xg.Solids()) if i not in set(m["bearing_ids"]))
    s["parked"], s["docks"] = {}, {}
    for i, center in enumerate(CENTERS):
        for label, v in s["variants"].items():
            s["parked"][f"T{i}_{label}"] = world(v["tool"], center, f)
            s["docks"][f"T{i}_{label}"] = world(v["dock"], center, f)
    _SCENE = s
    return s


# ---------------------------------------------------------------------------------------------
# Worker tasks
# ---------------------------------------------------------------------------------------------

def dock_parts(v, solids=None):
    return {f"Dock_{i}_{n}": d for i, (n, d) in enumerate(zip(DOCK_NAMES, solids or v["dock_solids"]))}


def task_dock_motion(s, label):
    v = s["variants"][label]
    parts = dock_parts(v)
    active = compound([v["tool"], s["carriage"]])
    out = {"samples": 121, "step_mm": 0.5, "approach_hits": [], "carriage_retreat_hits": [],
           "cartographer_retreat_hits": []}
    for step in range(121):
        offset = (0, -0.5 * step, 0)
        for key, moving, targets in (("approach_hits", active, parts),
                                     ("carriage_retreat_hits", s["carriage"], dict(parts, Parked_Tool=v["tool"])),
                                     ("cartographer_retreat_hits", s["cartographer"], dict(parts, Parked_Tool=v["tool"]))):
            hits = translated_hits(moving, targets, offset)
            if hits:
                out[key].append({"withdrawal_mm": -offset[1], "hits": hits})
    out["cartographer_on_mounted_tool_mm3"] = overlaps(s["cartographer"], {"Tool": v["tool"]})
    return out


def task_neighbours(s, label, other):
    v, o = s["variants"][label], s["variants"][other]
    active = compound([v["tool"], s["carriage"]])
    out = []
    for dx in (-PITCH, PITCH):
        moved = compound([o["tool"], o["dock"]]).translate((dx, 0, 0))
        hits, carto = [], []
        for d in range(61):
            found = translated_hits(active, {"Neighbour": moved}, (0, -d, 0))
            if found:
                hits.append({"withdrawal_mm": d, "hits": found})
            found = translated_hits(s["cartographer"], {"Neighbour": moved}, (0, -d, 0))
            if found:
                carto.append({"withdrawal_mm": d, "hits": found})
        out.append({"tool": label, "neighbour": other, "offset_x_mm": dx, "samples": 61, "hits": hits,
                    "cartographer_hits": carto})
    return out


def task_bay(s, bay):
    f, center, out = s["frames"], CENTERS[bay], []
    for label, v in s["variants"].items():
        key = f"T{bay}_{label}"
        check = {"bay": bay, "variant": label,
                 "tool_hits": overlaps(s["parked"][key], s["fixed"]),
                 "dock_hits": overlaps(s["docks"][key], s["fixed"]),
                 "samples": 121, "approach_hits": [], "carriage_retreat_hits": []}
        active = world(compound([v["tool"], s["carriage"]]), center, f)
        carriage = world(s["carriage"], center, f)
        for step in range(121):
            offset = (0, step * 0.5, 0)
            hits = translated_hits(active, s["fixed"], offset)
            if hits:
                check["approach_hits"].append({"withdrawal_mm": offset[1], "hits": hits})
                hits = translated_hits(carriage, s["fixed"], offset)
                if hits:
                    check["carriage_retreat_hits"].append({"withdrawal_mm": offset[1], "hits": hits})
        out.append(check)
    return out


def stationary(s):
    targets = {"P29_P30_Hardware": s["fixed"]["P29_P30_Hardware"], "Crossbar": s["fixed"]["Crossbar"],
               "Flying_Except_Y_Rails": s["flying_without_rails"]}
    targets.update(s["parked"])
    targets.update({f"Dock_{k}": d for k, d in s["docks"].items()})
    return targets


def task_crossbeam(s, steps):
    targets, out = stationary(s), []
    for step in steps:
        offset = (0, step * 0.5, 0)
        hits = translated_hits(s["xgantry"], targets, offset)
        hits.update(translated_hits(s["x_without_bearings"], {"Flying_Y_Rails": s["flying_rails"]}, offset))
        if hits:
            out.append({"withdrawal_mm": offset[1], "hits": hits})
    return {"samples": len(steps), "hits": out}


def task_traverse(s, label, xs):
    v, f = s["variants"][label], s["frames"]
    targets = dict(stationary(s), Flying_Y_Rails=s["flying_rails"], X_Gantry=s["xgantry"].translate((0, 60, 0)))
    active = world(compound([v["tool"], s["carriage"]]), 0, f).translate((0, 60, 0))
    out = []
    for x in xs:
        hits = translated_hits(active, targets, (x, 0, 0))
        if hits:
            out.append({"x_mm": x, "hits": hits})
    return {"variant": label, "x_mm": [xs[0], xs[-1]], "samples": len(xs), "hits": out}


def task_lateral(s):
    out = []
    for label, v in s["variants"].items():
        active = compound([v["tool"], s["carriage"]])
        for other, o in s["variants"].items():
            targets = {f"Neighbour_{dx:+.1f}": compound([o["tool"], o["dock"]]).translate((dx, 0, 0))
                       for dx in (-PITCH, PITCH)}
            for retreat in (0, 12.7, 60):
                for lateral in (-6.5, -1.5, 1.5, 6.5):
                    out.append({"tool": label, "neighbour": other, "local_x_mm": lateral, "withdrawal_mm": retreat,
                                "hits": translated_hits(active, targets, (lateral, -retreat, 0))})
    return out


def task_clearances(s, version):
    rig = fast_geometry.index_group(s["carriage_parts"])
    carto = fast_geometry.index_group([("Cartographer_V3", s["cartographer"])])
    out = {}
    for label, v in s["variants"].items():
        solids = v["dock_solids"] if version == "r36" else v["dock_r21"]
        parked = fast_geometry.index_group(v["parts"] + [(f"dock {n}", d) for n, d in zip(DOCK_NAMES, solids)])
        for dx in (PITCH, -PITCH):
            worst, worst_carto = None, None
            for dy in DY:
                for group, name in ((rig, "carriage"), (carto, "cartographer")):
                    hit = fast_geometry.min_distance(group, parked, (0, dy, 0), (dx, 0, 0), cutoff=6.0)
                    if hit is None:
                        continue
                    row = {"mm": hit[0], "moving": hit[1], "parked": hit[2], "carriage_dy_mm": dy}
                    if name == "carriage" and (worst is None or hit[0] < worst["mm"]):
                        worst = row
                    if name == "cartographer" and (worst_carto is None or hit[0] < worst_carto["mm"]):
                        worst_carto = row
            out[f"active carriage | {label} parked at {dx:+.1f}"] = worst
            out[f"cartographer | {label} parked at {dx:+.1f}"] = worst_carto
    return out


def task_bed(s):
    import audit_bed_front_edge_r34 as r34
    f = r34.frames()
    variants = {label: {"tool": v["tool"], "dock": v["dock"], "hotend": v["hotend"]}
                for label, v in s["variants"].items()}
    bed, source = r34.source_bed()
    options = r34.beds(bed)
    racks = {label: r34.Rack(v, label, f) for label, v in variants.items()}
    cases = {"original_bed_control": r34.bed_cases(variants, racks, f, options["original"]),
             "bed_front_edge_y40": r34.bed_cases(variants, racks, f, options["front_edge_cut"]),
             "shifted_stock_bed": r34.bed_cases(variants, racks, f, options["shifted_back"])}
    frame, frame_source = r34.frame_boxes()
    below = r34.space_below(variants, racks, f, frame)
    summary = {}
    for name, rows in cases.items():
        gaps = [c["min_distance_to_bed"]["mm"] for c in rows if c["min_distance_to_bed"]]
        summary[name] = {"cases": len(rows), "collision_cases": sum(bool(c["bed_intersections_mm3"]) for c in rows),
                         "minimum_clearance_mm": min(gaps) if gaps and len(gaps) == len(rows) else 0.0}
    summary["space_below_frame_collisions"] = sum(bool(c["frame_intersections_mm3"]) for c in below)
    summary["space_below_min_frame_clearance_mm"] = min(
        c["nearest_frame_body"]["mm"] for c in below if c["nearest_frame_body"])
    return {"bed_source": source, "frame_source": frame_source, "parked_envelope": r34.envelope(variants, f),
            "cases": cases, "space_below_bed_plane": below, "summary": summary}


TASKS = {"dock_motion": task_dock_motion, "neighbours": task_neighbours, "bay": task_bay,
         "crossbeam": task_crossbeam, "traverse": task_traverse, "lateral": task_lateral,
         "clearances": task_clearances, "bed": task_bed}


def run_task(spec):
    started = time.perf_counter()
    result = TASKS[spec["kind"]](scene(), **spec["args"])
    return {**spec, "result": result, "seconds": time.perf_counter() - started}


def specs():
    out = [{"kind": "bed", "args": {}}, {"kind": "lateral", "args": {}}]
    out += [{"kind": "traverse", "args": {"label": label, "xs": list(range(a, b))}}
            for label in VARIANTS for a, b in ((0, 88), (88, 176), (176, 264), (264, 351))]
    out += [{"kind": "crossbeam", "args": {"steps": list(range(a, b))}} for a, b in ((0, 31), (31, 61), (61, 91), (91, 121))]
    out += [{"kind": "bay", "args": {"bay": i}} for i in range(10)]
    out += [{"kind": "dock_motion", "args": {"label": label}} for label in VARIANTS]
    out += [{"kind": "neighbours", "args": {"label": a, "other": b}} for a in VARIANTS for b in VARIANTS]
    out += [{"kind": "clearances", "args": {"version": v}} for v in ("r21", "r36")]
    return out


# ---------------------------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------------------------

def rack_geometry(s, report, failures):
    """Cheap whole-rack figures, as in the revision-21 audit."""
    f, m = s["frames"], s["manifest"]
    tools = [v["tool"] for v in s["variants"].values()]
    gap = min(PITCH + bounds(a)[0] - bounds(b)[1] for a in tools for b in tools)
    rail_min, rail_max = m["x_rail"]["min_mm"][0], m["x_rail"]["max_mm"][0]
    margins = [CENTERS[0] - (rail_min + 22.7), (rail_max - 22.7) - CENTERS[-1]]
    parked = bounds(compound([*s["parked"].values(), *s["docks"].values()]))
    moving_rear = max(bounds(s["carriage"])[3], *(bounds(t)[3] for t in tools))
    nonadjacent = [[i, j, a, b] for i in range(10) for j in range(i + 2, 10) for a in VARIANTS for b in VARIANTS
                   if bounds(s["parked"][f"T{i}_{a}"])[1] > bounds(s["parked"][f"T{j}_{b}"])[0]]
    report["rack"] = {
        "pitch_mm": PITCH, "centers_x_mm": CENTERS, "minimum_parked_tool_x_gap_mm": gap,
        "rail_x_bounds_mm": [rail_min, rail_max], "end_rail_margins_mm": margins,
        "nonadjacent_overlap_candidates": nonadjacent,
        "parked_tool_dock_world_bounds_mm": parked,
        "front_print_limit_nozzle_y_mm": parked[3] + moving_rear - 22.7,
        "x_corridor_nozzle_y_mm": f["world_y_offset_mm"] + 60 - 22.7}
    if gap < 1.3:
        failures.append(f"Parked tool gap {gap:.2f} mm below 1.3 mm")
    if min(margins) <= 0:
        failures.append("End bay outside the physical X-rail stroke")
    if nonadjacent:
        failures.append("Nonadjacent tool X envelopes overlap")


def export_rack(s, report):
    f = s["frames"]
    rack = cq.Assembly(name="36 Ten tool rack requalified")
    expected = 0
    for i, center in enumerate(CENTERS):
        label = "Bambu" if i % 2 == 0 else "RedLizard"
        for prefix, shape, color in (("T", s["parked"][f"T{i}_{label}"], (0.9, 0.65, 0.1) if label == "Bambu"
                                      else (0.85, 0.3, 0.12)),
                                     ("D", s["docks"][f"T{i}_{label}"], (0.22, 0.4, 0.32))):
            rack.add(shape, name=f"{prefix}{i}_{label}", color=cq.Color(*color))
            expected += len(shape.Solids())
    for name, shape, color in (("P29_P30_Hardware", s["fixed"]["P29_P30_Hardware"], (0.3, 0.35, 0.4)),
                               ("Crossbar_2020", s["fixed"]["Crossbar"], (0.65, 0.65, 0.68)),
                               ("Monolith_X_Gantry_At_Dock", s["xgantry"], (0.55, 0.55, 0.58)),
                               ("Carriage_At_T0", world(s["carriage"], CENTERS[0], f), (0.5, 0.52, 0.55))):
        rack.add(shape, name=name, color=cq.Color(*color))
        expected += len(shape.Solids())
    path = STEP / f"{NAMES['rack']}.step"
    rack.export(str(path))
    back = cq.importers.importStep(str(path)).val()
    report["exports"]["rack"] = {"file": path.name, "solids": len(back.Solids()), "expected": expected,
                                 "sha256": sha(path)}
    if len(back.Solids()) != expected:
        raise ValueError("Rack STEP readback solid count changed")


def summarise(results, report, failures):
    by = {}
    for r in results:
        by.setdefault(r["kind"], []).append(r)
    motion = report["docking"] = {r["args"]["label"]: r["result"] for r in by["dock_motion"]}
    for label, m in motion.items():
        for key in ("approach_hits", "carriage_retreat_hits", "cartographer_retreat_hits"):
            if m[key]:
                failures.append(f"{label} own-dock {key}")
        if m["cartographer_on_mounted_tool_mm3"]:
            failures.append(f"Cartographer intersects the mounted {label} tool")
    report["neighbours"] = [c for r in by["neighbours"] for c in r["result"]]
    for c in report["neighbours"]:
        if c["hits"] or c["cartographer_hits"]:
            failures.append(f"Neighbour path {c['tool']} next to {c['neighbour']} at {c['offset_x_mm']:+.1f}")
    report["bays"] = sorted((c for r in by["bay"] for c in r["result"]), key=lambda c: (c["bay"], c["variant"]))
    for c in report["bays"]:
        if c["tool_hits"] or c["dock_hits"] or c["approach_hits"]:
            failures.append(f"Bay {c['bay']} {c['variant']}")
    cross = sorted(by["crossbeam"], key=lambda r: r["args"]["steps"][0])
    report["x_gantry_withdrawal"] = {"samples": sum(r["result"]["samples"] for r in cross),
                                     "hits": [h for r in cross for h in r["result"]["hits"]]}
    if report["x_gantry_withdrawal"]["hits"]:
        failures.append("X gantry against the parked rack")
    report["x_traverse"] = {}
    for label in VARIANTS:
        rows = sorted((r for r in by["traverse"] if r["args"]["label"] == label), key=lambda r: r["args"]["xs"][0])
        report["x_traverse"][label] = {"withdrawal_mm": 60, "samples": sum(r["result"]["samples"] for r in rows),
                                       "hits": [h for r in rows for h in r["result"]["hits"]]}
        if report["x_traverse"][label]["hits"]:
            failures.append(f"{label} X traverse")
    report["lateral_diagnostic"] = by["lateral"][0]["result"]
    for c in report["lateral_diagnostic"]:
        if c["withdrawal_mm"] == 60 and c["hits"]:
            failures.append("Lateral move obstructed after 60 mm withdrawal")
    report["clearances_mm"] = {r["args"]["version"]: r["result"] for r in by["clearances"]}
    bed = report["bed"] = by["bed"][0]["result"]
    s = bed["summary"]
    if not (s["bed_front_edge_y40"]["collision_cases"] == 0 and s["shifted_stock_bed"]["collision_cases"] == 0
            and s["original_bed_control"]["collision_cases"] == s["original_bed_control"]["cases"]
            and min(s["bed_front_edge_y40"]["minimum_clearance_mm"], s["shifted_stock_bed"]["minimum_clearance_mm"]) >= 1.0
            and s["space_below_frame_collisions"] == 0):
        failures.append("Bed gate")
    report["task_seconds"] = {f"{r['kind']} {json.dumps(r['args'])[:60]}": round(r["seconds"], 1) for r in results}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    started = time.perf_counter()
    print("Revision-36 chute", flush=True)
    chute, chute_report, failures = build_chute()
    report = {"status": "PENDING", "chute": chute_report, "exports": {}}
    if failures:
        (ROOT / REPORT).write_text(json.dumps(dict(report, failures=failures), indent=2, default=str) + "\n")
        raise ValueError(failures)
    docks = dock_sets(chute)
    report["exports"]["chute"] = [str(p.name) for p in export_print(NAMES["chute"], chute)]
    for label in VARIANTS:
        parts = [(d, n, (0.95, 0.4, 0.1) if i in (3, 7) else (0.6, 0.6, 0.63) if i in (4, 5, 8, 9, 10, 11, 12, 13)
                  else (0.22, 0.4, 0.32)) for i, (n, d) in enumerate(zip(DOCK_NAMES, docks[label]["r36"]))]
        report["exports"][label] = export_assembly(NAMES[label], parts, len(DOCK_NAMES)).name
    print("Writing the scene", flush=True)
    manifest = write_scene(chute, docks)
    report["sources"] = manifest["sources"]
    report["carriage_parts"] = [n for n, _ in manifest["carriage"]]
    report["tool_parts"] = {label: [n for n, _ in v["parts"]] for label, v in manifest["variants"].items()}
    tasks = specs()
    print(f"Running {len(tasks)} cases on {args.workers} workers", flush=True)
    results = fast_geometry.run_parallel(run_task, tasks, workers=args.workers)
    summarise(results, report, failures)
    s = scene()
    rack_geometry(s, report, failures)
    from audit_ten_tool_rack import parked_intake_review
    report["parked_fan_intake_review"] = parked_intake_review(
        {label: {"tool": v["tool"], "dock": v["dock"], "envelope": v["envelope"]} for label, v in s["variants"].items()})
    print("Exporting the rack", flush=True)
    export_rack(s, report)
    report["failures"] = failures
    report["status"] = ("FULL_TEN_TOOL_RACK_REQUALIFIED_CAD_REVIEW_NOT_MACHINE_QUALIFICATION" if not failures
                        else "FAILED_SEE_FAILURES")
    report["inherited_not_counted"] = [
        "Dock jaw snap detents overlap the dock body by design (flexible retention, dock-internal).",
        "Four MGN9H bearing references overlap their own Y rails in the source gantry model; the X-gantry "
        "sweep checks those blocks against everything except the rails.",
        "The Bambu hotend is the synthetic reference (tip Z-78.131); its pad and wiper follow that tip."]
    report["limitations"] = [
        "Rigid CAD and sampled straight-line paths (0.5 mm in Y, 1 mm in X), not continuous motion, "
        "jaw flexure, thermal growth or machine tolerances.",
        "The Cartographer is checked as an alternative to the Beacon on the same mount; both are not fitted at once.",
        "The bed, frame and gantry are the session snapshots; Z drives, bed supports and wiring are not modelled.",
        "Klipper limits, fan power for parked tools and the cam/servo sequence are outside this geometric audit."]
    report["runtime_s"] = time.perf_counter() - started
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    brief = {"status": report["status"], "failures": failures, "chute": {k: chute_report[k] for k in (
        "removed_mm3", "wall_to_m3_head_channel_mm")}, "rack": report["rack"],
        "bed": report["bed"]["summary"], "clearances": report["clearances_mm"], "runtime_s": report["runtime_s"]}
    print(json.dumps(brief, indent=1, default=str))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
