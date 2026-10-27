"""Revision 34: keep the dock rack rigid on the gantry and move the bed's front edge behind it.

The flying gantry is a U: the left and right Y arms are joined at the rear and the X beam travels
along them. The 2020 dock crossbar closes the open front of the U, so the ten docks and the parked
tools rise and fall with the gantry and tools can change at any height. That is the intended
design, and nothing in it changes here.

Revision 22 found the cost: the parked tools ride at the active tool's height, and their chutes,
silicone pads and wipers hang about 14 mm below the nozzle over the bed's front strip, so every
first-layer case hits the bed. A higher crossbar would not help, because the carriage, not the
crossbar, sets the parked tools' height. The rack cannot move forward either (revision 22).

The active nozzle cannot print forward of the parked tools anyway, so the bed in front of the
parked envelope is dead space whose only effect is the collision. This audit records the printer
change instead of adding a mechanism: the bed's front edge must lie behind the parked envelope.
It proves the unchanged rigid rack clears a bed whose front edge is at Y40 in every first-layer
case, checks the space the parked hardware drops into in front of that edge, and confirms the
print area, probe reach and a shifted-bed option.
"""

import hashlib
import json
import time

import cadquery as cq

import fast_geometry
from audit_low_z_bed_clearance import load_parked_variants
from audit_ten_tool_rack import world
from audit_tool_owned_2510 import bounds, compound
from build_fan_mounts_r33 import carriage
from build_modular_toolhead import ROOT, box, primitives
from build_refined_docking_review import DOCK_NAMES, DOCK_STANDOFF_MM, translated_hits

REPORT = "verification_bed_front_edge_r34.json"
BED_FRONT_Y = 40.0          # required printer change: the bed's front edge at or behind this Y
MIN_EDGE_GAP = 1.0          # smallest acceptable Y gap between the parked envelope and the bed edge
SHIFT = BED_FRONT_Y - 9.0   # option B: the stock 350 x 350 bed moved back by this much
PITCH, FIRST_BAY_X = 37.3, 7.0
NOZZLE_Z = {"first_layer": 0.2, "contact_touch": 0.0}
LOWEST_NOZZLE_Z = -2.0      # gantry 2 mm below nozzle touch, for the space under the bed plane
# Probe coil positions from the README (tool-local Y; the nozzle is at local Y 22.7 and local +Y
# faces the dock). World Y = frame Y - local Y, so a coil at a smaller local Y sits behind the nozzle.
COIL_LOCAL_Y = {"Beacon_RevH": 3.20, "Cartographer_V3": 2.88}
NOZZLE_LOCAL_Y = 22.7
COIL_RADIUS = 10.0          # keep this much bed around the coil centre line when probing


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def frames():
    f = json.loads((primitives.WORK / "rack_audit_frames.json").read_text())
    f["world_y_offset_mm"] += DOCK_STANDOFF_MM
    f["x_gantry_y_shift_to_dock_mm"] += DOCK_STANDOFF_MM
    return f


def source_bed():
    path = primitives.WORK / "rack_audit_Bed_world.step"
    baseline = json.loads((ROOT / "verification_low_z_bed_clearance.json").read_text())
    if sha(path) != baseline["low_z_bed_clearance"]["bed_source"]["sha256"]:
        raise ValueError("Bed source changed since the revision-22 low-Z audit")
    bed = cq.importers.importStep(str(path)).val()
    b = bounds(bed)
    if len(bed.Solids()) != 1 or max(abs(p - q) for p, q in zip(b, (0, 350, 9, 359, -8, 0))) > 1e-3:
        raise ValueError("Unexpected bed snapshot")
    return bed, {"file": str(path), "sha256": sha(path), "bounds_mm": b}


def beds(bed):
    b = bounds(bed)
    return {
        "original": bed,
        "front_edge_cut": bed.intersect(box(b[0] - 1, b[1] + 1, BED_FRONT_Y, b[3] + 1, b[4] - 1, b[5] + 1)),
        "shifted_back": bed.translate((0, SHIFT, 0)),
    }


def parked_solids(variant, label):
    dock = list(variant["dock"].Solids())
    if len(dock) != len(DOCK_NAMES):
        raise ValueError("Unexpected dock solid order/count")
    parts = [(f"{label}:{n}", s) for n, s in zip(DOCK_NAMES, dock)]
    return parts + [(f"{label}:Parked_Tool_Solid_{i}", s) for i, s in enumerate(variant["tool"].Solids())]


def z_shift(active, f, nozzle_z):
    return nozzle_z - (f["world_z_offset_mm"] + bounds(active["hotend"])[4])


class Rack:
    """One variant's dock and parked tool placed once at bay 0; every case is an offset of it."""

    def __init__(self, variant, label, f):
        self.parts = [(n, world(s, FIRST_BAY_X, f)) for n, s in parked_solids(variant, label)]
        self.group = fast_geometry.index_group(self.parts)
        self.zmin = min(bounds(s)[4] for _, s in self.parts)

    def hits(self, targets, offset):
        out = {}
        for n, s in self.parts:
            for target, v in translated_hits(s, targets, offset).items():
                out[f"{n} | {target}"] = v
        return out


def nearest(group_a, group_b, cutoff, offset_a=(0, 0, 0)):
    hit = fast_geometry.min_distance(group_a, group_b, offset_a=offset_a, cutoff=cutoff)
    return None if hit is None else {"mm": hit[0], "moving": hit[1], "fixed": hit[2]}


def envelope(variants, f):
    out = {}
    for label, v in variants.items():
        b = bounds(world(compound([v["dock"], v["tool"]]), FIRST_BAY_X, f))
        out[label] = {"ymin_mm": b[2], "ymax_mm": b[3], "zmin_source_mm": b[4]}
    return out


def bed_cases(variants, racks, f, bed):
    cases, target = [], fast_geometry.index_group([("Bed", bed)])
    for active_label, active in variants.items():
        for height, nozzle_z in NOZZLE_Z.items():
            dz = z_shift(active, f, nozzle_z)
            for parked_label, rack in racks.items():
                for bay in range(10):
                    offset = (PITCH * bay, 0.0, dz)
                    cases.append({"active_hotend": active_label, "parked_hotend": parked_label, "bay": bay,
                                  "height": height, "active_nozzle_z_mm": nozzle_z,
                                  "lowest_parked_z_mm": rack.zmin + dz,
                                  "bed_intersections_mm3": rack.hits({"Bed": bed}, offset),
                                  "min_distance_to_bed": nearest(rack.group, target, 60.0, offset)})
    return cases


def frame_boxes():
    path = primitives.WORK / "frame_world_bodies.json"
    rows = json.loads(path.read_text())["rows"]
    out = []
    for r in rows:
        if r["body"].startswith("R1_BED"):
            continue
        out.append((f"{r['path'].split('/')[-1]}/{r['body']}", box(r["min"][0], r["max"][0], r["min"][1],
                                                                 r["max"][1], r["min"][2], r["max"][2])))
    return out, {"file": str(path), "sha256": sha(path), "bodies": len(out),
                 "note": "Nominal frame, panels and door from 01_Voron24_350_Frame_and_Enclosure as world "
                         "bounding boxes (conservative for the extrusion profiles). No Z drives, bed supports "
                         "or bed wiring are modeled."}


def space_below(variants, racks, f, frame):
    targets, group = dict(frame), fast_geometry.index_group(frame)
    out = []
    for active_label, active in variants.items():
        dz = z_shift(active, f, LOWEST_NOZZLE_Z)
        for parked_label, rack in racks.items():
            hits, near = {}, None
            for bay in range(10):
                offset = (PITCH * bay, 0.0, dz)
                hits.update({f"bay {bay}: {k}": v for k, v in rack.hits(targets, offset).items()})
                found = nearest(rack.group, group, 80.0, offset)
                if found and (near is None or found["mm"] < near["mm"]):
                    near = dict(found, bay=bay)
            out.append({"active_hotend": active_label, "parked_hotend": parked_label,
                        "active_nozzle_z_mm": LOWEST_NOZZLE_Z, "lowest_parked_z_mm": rack.zmin + dz,
                        "frame_intersections_mm3": hits, "nearest_frame_body": near})
    return out


def shifted_rear_strip(variants, f, shifted):
    """The shifted bed's rear strip (Y359..390) lies under the gantry: prove nothing reaches it."""
    rig = compound([s for _, s in carriage()])
    beam = cq.importers.importStep(str(primitives.WORK / "rack_audit_X_Gantry_world.step")).val()
    flying = cq.importers.importStep(str(primitives.WORK / "rack_audit_Flying_Gantry_world.step")).val()
    target = {"Shifted_Bed": shifted}
    group = fast_geometry.index_group([("Shifted_Bed", shifted)])
    out = []
    rear_nozzle_y = 359.0
    dy = rear_nozzle_y - (f["world_y_offset_mm"] - NOZZLE_LOCAL_Y)
    for active_label, active in variants.items():
        dz = z_shift(active, f, NOZZLE_Z["first_layer"])
        parts = [("Active_Tool", world(active["tool"], 0.0, f)), ("Carriage", world(rig, 0.0, f)),
                 ("X_Beam", beam.translate((0, f["x_gantry_y_shift_to_dock_mm"], 0)))]
        moving = fast_geometry.index_group(parts)
        for x in (0.0, 175.0, 350.0):
            hits, near = {}, {}
            for n, s in parts:
                # The X beam spans the full width; only the carriage and tool move along it.
                offset = (0.0 if n == "X_Beam" else x, dy, dz)
                hits.update({f"{n} | {k}": v for k, v in translated_hits(s, target, offset).items()})
                near[n] = nearest([g for g in moving if g.label == n], group, 60.0, offset)
            out.append({"active_hotend": active_label, "nozzle_x_mm": x, "nozzle_y_mm": rear_nozzle_y,
                        "active_nozzle_z_mm": NOZZLE_Z["first_layer"], "intersections_mm3": hits,
                        "nearest_by_part": near})
    dz = z_shift(variants["Bambu"], f, LOWEST_NOZZLE_Z)
    out.append({"flying_gantry_at_nozzle_z_mm": LOWEST_NOZZLE_Z,
                "intersections_mm3": translated_hits(flying, target, (0, 0, dz)),
                "nearest": nearest(fast_geometry.index_group([("Flying_Gantry", flying)]), group, 60.0, (0, 0, dz))})
    return out


def print_area(env):
    rack = json.loads((ROOT / "verification_ten_tool_closed_panel_dock.json").read_text())
    strip = rack["full_ten_tool_rack"]["front_service_strip"]
    front = strip["conservative_nozzle_y_for_whole_envelope_separation_mm"]
    coil = {name: NOZZLE_LOCAL_Y - y for name, y in COIL_LOCAL_Y.items()}
    ymax = max(e["ymax_mm"] for e in env.values())
    return {
        "parked_envelope_world_ymax_mm": ymax,
        "minimum_bed_front_edge_y_mm": ymax + MIN_EDGE_GAP,
        "required_bed_front_edge_y_mm": BED_FRONT_Y,
        "parked_to_bed_edge_y_gap_mm": BED_FRONT_Y - ymax,
        "front_print_limit_nozzle_y_mm": front,
        "x_traverse_corridor_nozzle_y_mm": strip["audited_x_corridor_nozzle_y_mm"],
        "bed_in_front_of_print_limit_mm": front - BED_FRONT_Y,
        "print_area_unchanged": front - BED_FRONT_Y >= 0,
        "probe_coil_offset_behind_nozzle_mm": coil,
        "probe_coil_y_at_front_print_limit_mm": {k: front + v for k, v in coil.items()},
        "probe_over_bed_at_front_print_limit": all(front + v - COIL_RADIUS >= BED_FRONT_Y for v in coil.values()),
        "rear_print_limit_nozzle_y_mm": 359.0,
        # The mesh is measured at probe positions: the coil can reach bed Y up to the bed edge less its radius.
        "probe_mesh_rear_bed_y_mm": {"cut_bed": 359.0 - COIL_RADIUS, "shifted_bed": 359.0 + SHIFT - COIL_RADIUS},
        "probe_reaches_whole_print_area_with_shifted_bed": 359.0 + SHIFT - COIL_RADIUS >= 359.0,
        "probe_reaches_whole_print_area_with_cut_bed": 359.0 - COIL_RADIUS >= 359.0,
        "source": {"file": "verification_ten_tool_closed_panel_dock.json",
                   "sha256": sha(ROOT / "verification_ten_tool_closed_panel_dock.json")},
        "klipper_note": ("The coils sit behind the nozzle in printer Y (Y grows toward the rear). The README's "
                         "probe snippets give y_offset -19.50 / -19.82; in printer coordinates these look "
                         "sign-flipped (+19.50 / +19.82). Confirm with a probe-accuracy test before meshing."),
    }


def main():
    started = time.perf_counter()
    f = frames()
    variants = load_parked_variants()
    bed, bed_source = source_bed()
    options = beds(bed)
    frame, frame_source = frame_boxes()
    env = envelope(variants, f)
    print("Bed cases", flush=True)
    report = {
        "status": "PENDING",
        "decision": ("The dock rack stays rigidly bolted across the open front of the gantry U (no independent "
                     "lift). The printer change is recorded instead: the bed's front edge moves behind the "
                     "parked envelope. No rack, dock, tool, carriage or gantry geometry changes."),
        "required_printer_change": {
            "bed_front_edge_y_mm": BED_FRONT_Y,
            "option_a_cut_or_custom_bed": f"Bed plate, heater and build sheet spanning Y{BED_FRONT_Y:g}..359 "
                                          f"(350 x {359 - BED_FRONT_Y:g} mm).",
            "option_b_shift_stock_bed": f"Keep the 350 x 350 bed, heater and sheet; move the bed and its mounts "
                                        f"back {SHIFT:g} mm to Y{BED_FRONT_Y:g}..{359 + SHIFT:g}.",
            "build_sheet": "No tab or overhang at the front edge.",
        },
        "sources": {"bed": bed_source, "frame": frame_source,
                    "tools_and_docks": {k: v["source"] for k, v in variants.items()},
                    "frames": json.loads((primitives.WORK / "rack_audit_frames.json").read_text())},
        "parked_envelope": env,
        "print_area_and_probe": print_area(env),
    }
    racks = {label: Rack(v, label, f) for label, v in variants.items()}
    report["bed_cases"] = {"original_bed_control": bed_cases(variants, racks, f, options["original"])}
    report["bed_cases"]["bed_front_edge_y40"] = bed_cases(variants, racks, f, options["front_edge_cut"])
    report["bed_cases"]["shifted_stock_bed"] = bed_cases(variants, racks, f, options["shifted_back"])
    print("Space below the bed plane", flush=True)
    report["space_below_bed_plane"] = space_below(variants, racks, f, frame)
    print("Shifted bed rear strip", flush=True)
    report["shifted_bed_rear_strip"] = shifted_rear_strip(variants, f, options["shifted_back"])
    summary = {}
    for name, cases in report["bed_cases"].items():
        gaps = [c["min_distance_to_bed"]["mm"] for c in cases if c["min_distance_to_bed"]]
        summary[name] = {"cases": len(cases), "collision_cases": sum(bool(c["bed_intersections_mm3"]) for c in cases),
                         "minimum_clearance_mm": min(gaps) if gaps and len(gaps) == len(cases) else 0.0}
    summary["space_below_frame_collisions"] = sum(bool(c["frame_intersections_mm3"]) for c in report["space_below_bed_plane"])
    summary["space_below_min_frame_clearance_mm"] = min(
        c["nearest_frame_body"]["mm"] for c in report["space_below_bed_plane"] if c["nearest_frame_body"])
    summary["shifted_rear_strip_collisions"] = sum(bool(c["intersections_mm3"]) for c in report["shifted_bed_rear_strip"])
    rear = [c for c in report["shifted_bed_rear_strip"] if "nearest_by_part" in c]
    summary["shifted_rear_strip_min_clearance_mm"] = {
        part: min(c["nearest_by_part"][part]["mm"] for c in rear) for part in ("Active_Tool", "Carriage", "X_Beam")}
    summary["shifted_rear_strip_min_clearance_mm"]["Flying_Gantry"] = report["shifted_bed_rear_strip"][-1]["nearest"]["mm"]
    summary["space_below_nearest_frame_note"] = (
        "Bay-0 dock front (Y-38) to the door-buffer plane (Y-40): the existing 2 mm front gap, the same at every "
        "gantry height and unchanged by the bed.")
    report["summary"] = summary
    area = report["print_area_and_probe"]
    passed = (summary["bed_front_edge_y40"]["collision_cases"] == 0 and summary["shifted_stock_bed"]["collision_cases"] == 0
              and summary["original_bed_control"]["collision_cases"] == summary["original_bed_control"]["cases"]
              and summary["space_below_frame_collisions"] == 0 and summary["shifted_rear_strip_collisions"] == 0
              and area["parked_to_bed_edge_y_gap_mm"] >= MIN_EDGE_GAP and area["print_area_unchanged"]
              and area["probe_over_bed_at_front_print_limit"])
    report["status"] = ("RIGID_RACK_CLEARS_BED_WITH_FRONT_EDGE_AT_Y40_REQUIRED_PRINTER_CHANGE_NOT_MACHINE_QUALIFIED"
                        if passed else "FAILED_SEE_SUMMARY")
    report["limitations"] = [
        "Rigid CAD envelopes at the revision-21 parked tools and docks; the revision-33 toolheads keep the same "
        "docking interface and lower envelope but the full ten-tool rack has not been re-audited with them.",
        "The model has no Z drives, bed supports, bed wiring or nozzle brush. Check the space in front of the new "
        "bed edge, from Y-38 to the edge and down to 16 mm below the bed top, on the real printer.",
        "No thermal expansion, bed mesh, gantry sag or QGL residual is included; the 4.6 mm edge gap covers them "
        "in Y, which is the only direction that matters for this clearance.",
        "Klipper coordinates, probe offsets and the bed mesh limits must be commissioned on the machine.",
    ]
    report["runtime_s"] = time.perf_counter() - started
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({"status": report["status"], "summary": summary,
                      "print_area_and_probe": {k: v for k, v in area.items() if k not in ("source", "klipper_note")}},
                     indent=1, default=str))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
