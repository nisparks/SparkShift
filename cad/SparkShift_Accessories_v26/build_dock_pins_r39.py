"""Revision 39: move the dock-coupling dowel pins from the tool (P18) into the dock (P25).

Revision 38 measured the front print limit by exact contact. Its binding feature was the two Ø5x12 mm dowel
pins that stick 5.5 mm out of every tool's P18: the active tool's pins reach into a parked tool's open rear,
around its filament stem, at nozzle Y51.22. Without them, P18's flat plate binds everywhere at Y47.25.

Revision 39 swaps the coupling halves. The pins are pressed into P25 and point at the tool. The 5x7x5.5 mm
bushings are pressed into P18, flush with its face. The hardware, straight-Y docking, insertion depth and
radial clearance are all unchanged, and the magnets do not move. P18's two pin bosses become one bar across
its existing width, with the bushing axes at X+/-4.8, Z21 (from X+/-6, Z22) to leave at least 1.48 mm of wall.
P25's released bushing seats and pin-clearance bores are filled, and two press-fit pin bores are cut.

Checks: both parts against their released versions outside the edit zones; walls and floors around every
seat and bore; hardware fits; the docked tool against the whole dock; the new P18 and its hardware against
the rest of both tools and the mounted carriage. Then, on a revision-39 scene (WORK/r39_scene):
- the revision-36 full-rack requalification;
- the revision-38 front-print-limit audit.
"""

import argparse
import json
import os
import time

import build_and_verify_accessories_v26 as acc

# This build writes and audits its own scene; worker processes inherit the variable.
os.environ["SPARKSHIFT_SCENE"] = str(acc.WORK / "r39_scene")

import cadquery as cq  # noqa: E402

import audit_front_print_limit_r38 as front  # noqa: E402
import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import build_probe_height_datum_dock_r37 as b37  # noqa: E402
import fast_geometry as fg  # noqa: E402
import r37_parts as P37  # noqa: E402
import r39_parts as P  # noqa: E402
from audit_tool_owned_2510 import bounds, compound, overlaps  # noqa: E402
from build_bambu_clean_r29 import sha  # noqa: E402
from build_carriage_lowered_mounts_r31 import confined  # noqa: E402
from build_fan_mounts_r33 import export_assembly, export_print  # noqa: E402
from build_modular_toolhead import ROOT, load  # noqa: E402

REPORT = "verification_dock_pins_r39.json"
FRONT_REPORT = "verification_front_print_limit_r39.json"
FRONT_R38 = "verification_front_print_limit_r38.json"
VARIANTS = ("Bambu", "RedLizard")
PITCH = 37.3
MIN_WALL = 1.4
STEPS = (3.0, 2.5, 2.0, 1.8, 1.6, 1.5, 1.45, 1.4, 1.3, 1.2, 1.0, 0.8, 0.5, 0.0)
BRASS, STEEL, MAGNET, ORANGE = (0.8, 0.55, 0.2), (0.78, 0.78, 0.8), (0.2, 0.2, 0.22), (0.95, 0.55, 0.12)


def cyl(x, z, y0, y1, r):
    return cq.Shape.cast(acc.cyl_y(x, z, y0, y1, r))


def solid_all_round(shape, region):
    return region.Volume() - region.intersect(shape).Volume() < 1e-3


def wall(shape, axis, r, y0, y1):
    """Largest tested wall (mm) that is solid all round a bore of radius r between y0 and y1."""
    x, z = axis
    for t in STEPS:
        if t and solid_all_round(shape, cyl(x, z, y0, y1, r + t).cut(cyl(x, z, y0 - 1, y1 + 1, r + 0.005))):
            return t
    return 0.0


def floor(shape, axis, r, y_bottom, direction):
    """Largest tested solid thickness beyond a blind bore's bottom (direction -1: toward -Y)."""
    x, z = axis
    for t in STEPS:
        if t and solid_all_round(shape, cyl(x, z, *sorted((y_bottom + direction * 0.005, y_bottom + direction * t)), r)):
            return t
    return 0.0


def distance(a, b, cutoff=5.0):
    hit = fg.min_distance(fg.index_group([("a", a)]), fg.index_group([("b", b)]), cutoff=cutoff)
    return None if hit is None else round(hit[0], 4)


def closest(group_a, group_b):
    found = [d for a in group_a for b in group_b if (d := distance(a, b)) is not None]
    return min(found) if found else None


def side(x):
    return "left" if x < 0 else "right"


def same_box(a, b, tolerance=1e-3):
    return max(abs(p - q) for p, q in zip(bounds(a), bounds(b))) < tolerance

# --------------------------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------------------------

def check_p18(p18_new, report, failures):
    old = load("P18_Tool_docking_backplate_3010")
    x, (y0, _), (z0, z1) = P.BAR["x"], P.BAR["y"], P.BAR["z"]
    zone = (-x - 0.1, x + 0.1, y0 - 0.1, P.BOSS_FACE_Y + 0.1, z0 - 0.1, z1 + 0.1)
    seat = (P.BOSS_FACE_Y - P.SEAT_DEPTH, P.BOSS_FACE_Y)
    ax, az = abs(P.AXES[0][0]), P.AXES[0][1]
    gauges = {"outer_x_wall_mm": x - (ax + P.SEAT_R), "between_seats_mm": 2 * (ax - P.SEAT_R),
              "top_wall_mm": z1 - (az + P.SEAT_R), "bottom_wall_mm": (az - P.SEAT_R) - z0}
    seats = {side(sx): {"radial_wall_tested_mm": wall(p18_new, (sx, sz), P.SEAT_R, seat[0] + 0.05, seat[1] - 0.05),
                        "floor_tested_mm": floor(p18_new, (sx, sz), P.SEAT_R, seat[0], -1)} for sx, sz in P.AXES}
    # The released press-fit pin bores below the new seat floor must now be solid.
    filled = {side(sx): solid_all_round(p18_new, cyl(sx, sz, 38.55, seat[0] - 0.05, 2.45)) for sx, sz in P.OLD_AXES}
    report["p18"] = {
        "volume_mm3": {"released": old.Volume(), "r39": p18_new.Volume()},
        "bounds_mm": {"released": bounds(old), "r39": bounds(p18_new)},
        "edit_zone_mm": zone, "confinement": confined(p18_new.copy(), old.copy(), [zone]),
        "bar_mm": P.BAR, "bushing_axes_xz_mm": P.AXES, "released_pin_axes_xz_mm": P.OLD_AXES,
        "seat": {"diameter_mm": 2 * P.SEAT_R, "depth_mm": P.SEAT_DEPTH, "y_mm": seat},
        "wall_gauges_mm": gauges, "seat_walls": seats, "released_pin_bores_filled": filled}
    if not report["p18"]["confinement"]["unchanged_outside_zones"]:
        failures.append("P18 changed outside the bar zone")
    if not same_box(p18_new, old):
        failures.append("P18 bounds changed")
    if min(min(gauges.values()), *(s["radial_wall_tested_mm"] for s in seats.values())) < MIN_WALL:
        failures.append("P18 bushing seat wall")
    if min(s["floor_tested_mm"] for s in seats.values()) < 2.0 or not all(filled.values()):
        failures.append("P18 seat floor or released bore fill")


def check_p25(p25_new, p25_old, yf, report, failures):
    zones = [(min(s * 2.2, s * 9.6), max(s * 2.2, s * 9.6), yf - 0.6, yf + 12.1, 18.4, 25.6) for s in (-1, 1)]
    depth = P.PIN["length"] - P.PIN["nose"]
    bores = {side(sx): {"radial_wall_tested_mm": wall(p25_new, (sx, sz), P.PIN_BORE_R, yf + 0.05, yf + depth - 0.05),
                        "floor_tested_mm": floor(p25_new, (sx, sz), P.PIN_BORE_R, yf + depth, 1)} for sx, sz in P.AXES}
    # The released counterbores and clearance bores, outside the new pin bores, must now be solid.
    filled = {}
    for (sx, sz), (nx, nz) in zip(P.OLD_AXES, P.AXES):
        deep = cyl(sx, sz, yf + depth + 0.05, yf + P.OLD_CLEARANCE[1] - 0.05, P.OLD_CLEARANCE[0] - 0.05)
        plug = cyl(sx, sz, yf + 0.05, yf + P.OLD_COUNTERBORE[1] - 0.05, P.OLD_COUNTERBORE[0] - 0.05)
        plug = plug.cut(cyl(nx, nz, yf - 1, yf + depth + 1, P.PIN_BORE_R + 0.05))
        filled[side(sx)] = solid_all_round(p25_new, deep) and solid_all_round(p25_new, plug)
    report["p25"] = {
        "volume_mm3": {"released": p25_old.Volume(), "r39": p25_new.Volume()},
        "bounds_mm": {"released": bounds(p25_old), "r39": bounds(p25_new)},
        "face_y_mm": yf, "edit_zones_mm": zones, "confinement": confined(p25_new.copy(), p25_old.copy(), zones),
        "pin_bore": {"diameter_mm": 2 * P.PIN_BORE_R, "depth_mm": depth, "axes_xz_mm": P.AXES},
        "pin_bores": bores, "released_seats_filled": filled}
    if not report["p25"]["confinement"]["unchanged_outside_zones"]:
        failures.append("P25 changed outside the coupling zones")
    if not same_box(p25_new, p25_old):
        failures.append("P25 bounds changed")
    if min(b["radial_wall_tested_mm"] for b in bores.values()) < MIN_WALL or \
            min(b["floor_tested_mm"] for b in bores.values()) < 2.0 or not all(filled.values()):
        failures.append("P25 pin bore wall, floor or released seat fill")


def check_hardware(p18_new, p25_new, yf, report, failures):
    rows = []
    for (sx, _), b, p in zip(P.AXES, P.bushings(), P.pins(yf)):
        rows.append({"side": side(sx),
                     "bushing_in_p18_intersections_mm3": overlaps(b, {"P18": p18_new}),
                     "bushing_to_p18_mm": distance(b, p18_new),
                     "pin_in_p25_intersections_mm3": overlaps(p, {"P25": p25_new}),
                     "pin_to_p25_mm": distance(p, p25_new),
                     "pin_pressed_mm": bounds(p)[3] - yf, "pin_proud_of_p25_face_mm": yf - bounds(p)[2]})
    report["hardware_fits"] = rows
    if any(r["bushing_in_p18_intersections_mm3"] or r["pin_in_p25_intersections_mm3"] for r in rows):
        failures.append("Hardware intersects its seat")


def check_docked(tools39, dock39, tools37, dock37, yf, report, failures):
    contact = {}
    for label in VARIANTS:
        hits = overlaps(compound([s for _, s in tools39[label]["parts"]]), dict(zip(P.DOCK_NAMES_R39, dock39)))
        contact[label] = hits
        if hits:
            failures.append(f"{label} docked in the revision-39 dock intersects it")
    pins37 = [s for s in dict(tools37["Bambu"]["parts"])["coupling pins and magnets"].Solids() if bounds(s)[3] > 48]
    pins39, bush39, bush37 = P.pins(yf), P.bushings(), dock37[P.LEFT:P.RIGHT + 1]

    def engagement(pin, bush, nose_low):
        pb, bb = bounds(pin), bounds(bush)
        if nose_low:   # revision 39: dock pin, nose toward -Y, entering a P18 bushing from its +Y end
            return {"insertion_mm": bb[3] - pb[2], "full_diameter_mm": bb[3] - (pb[2] + P.PIN["cone"]),
                    "radial_clearance_mm": distance(pin, bush)}
        return {"insertion_mm": pb[3] - bb[2], "full_diameter_mm": (pb[3] - P.PIN["cone"]) - bb[2],
                "radial_clearance_mm": distance(pin, bush)}

    eng = {"r37_tool_pins_in_dock_bushings": [engagement(p, b, False) for p, b in zip(pins37, bush37)],
           "r39_dock_pins_in_p18_bushings": [engagement(p, b, True) for p, b in zip(pins39, bush39)]}
    mags = P.tool_magnets()
    gaps = {"r37": closest(mags, dock37[12:14]), "r39": closest(mags, dock39[12:14])}
    p18_old, p18_new = load("P18_Tool_docking_backplate_3010"), dict(tools39["Bambu"]["parts"])["P18"]
    # Every dock solid except the coupling pair itself (released bushings, revision-39 pins).
    near = {n: {"r37": distance(p18_old, a), "r39": distance(p18_new, b)}
            for i, (n, a, b) in enumerate(zip(P.DOCK_NAMES_R39, dock37, dock39)) if i not in (P.LEFT, P.RIGHT)}
    near = {n: v for n, v in near.items() if v["r37"] is not None or v["r39"] is not None}
    tip = {"pin_tip_to_p18_mm": closest(pins39, [p18_new]), "bushing_to_p25_mm": closest(bush39, [dock39[0]])}
    report["docked"] = {"intersections_mm3": contact, "engagement": eng, "magnet_gap_mm": gaps,
                        "p18_to_dock_parts_mm": near, **tip}
    for e in eng["r39_dock_pins_in_p18_bushings"]:
        ref = eng["r37_tool_pins_in_dock_bushings"][0]
        if abs(e["insertion_mm"] - ref["insertion_mm"]) > 0.01 or abs(e["radial_clearance_mm"] - ref["radial_clearance_mm"]) > 0.005:
            failures.append("Pin engagement changed")
    if abs(gaps["r39"] - gaps["r37"]) > 1e-3:
        failures.append("Magnet gap changed")
    for n, v in near.items():
        # A dock part may only come closer to P18 if it stays at least 0.2 mm away.
        if v["r39"] is not None and v["r39"] < 0.2 - 1e-3 and (v["r37"] is None or v["r39"] < v["r37"] - 1e-3):
            failures.append(f"P18 closer to dock {n}")


def check_tools(tools39, carriage_parts, report, failures):
    rows = []
    for label in VARIANTS:
        parts = dict(tools39[label]["parts"])
        new = {n: parts[n] for n in ("P18", "bushings and magnets")}
        rest = {n: s for n, s in parts.items() if n not in new}
        for n, s in new.items():
            for target, v in {**overlaps(s, rest), **overlaps(s, dict(carriage_parts))}.items():
                rows.append({"tool": label, "part": n, "b": target, "mm3": v})
        if overlaps(new["P18"], {"bushings and magnets": new["bushings and magnets"]}):
            rows.append({"tool": label, "part": "P18", "b": "bushings and magnets", "mm3": "intersects"})
    report["tool_internal_and_mounted"] = {
        "checked": "Revision-39 P18 and its bushings and magnets against the rest of each tool and every mounted "
                   "carriage part (revision-37 carriage).", "intersections_mm3": rows}
    if rows:
        failures.append("Revision-39 P18 or its hardware intersects the tool or carriage")


# --------------------------------------------------------------------------------------------
# Exports
# --------------------------------------------------------------------------------------------

def dock_colors():
    out = []
    for i in range(14):
        if i == 0:
            out.append((0.3, 0.62, 0.45))
        elif i in (P.LEFT, P.RIGHT):
            out.append(STEEL)
        elif i in (12, 13):
            out.append(MAGNET)
        elif i in (3, 7):
            out.append((0.95, 0.4, 0.1))
        elif i in (4, 5, 8, 9):
            out.append((0.6, 0.6, 0.63))
        else:
            out.append((0.22, 0.4, 0.32))
    return out


def exports(p18_new, dock39, tools39, report):
    files = export_print(P.NAMES["p18"], p18_new) + export_print(P.NAMES["p25"], dock39[0])
    colors = dock_colors()
    files.append(export_assembly(P.NAMES["dock"], [(s, n, c) for s, n, c in zip(dock39, P.DOCK_NAMES_R39, colors)], 14))
    hw = [(b, f"{side(x).title()}_5x7x5p5_Bushing", BRASS) for (x, _), b in zip(P.AXES, P.bushings())]
    hw += [(m, f"{s}_6x4_N52_Tool_Magnet", MAGNET) for s, m in zip(("Left", "Right"), P.tool_magnets())]
    files.append(export_assembly(P.NAMES["tool_hardware"], hw, 4))
    # Review: a Bambu docked at X0, and a Red Lizard 12 mm out of its dock at +37.3 to show the pins and bushings.
    items = []
    for label, dx, dy in (("Bambu", 0.0, 0.0), ("RedLizard", PITCH, -12.0)):
        for n, s in tools39[label]["parts"]:
            if n == "bushings and magnets":
                for (x, _), b in zip(P.AXES, s.Solids()[:2]):
                    items.append((b.translate((dx, dy, 0)), f"{label}_{side(x).title()}_Bushing", BRASS))
                for k, m in enumerate(s.Solids()[2:]):
                    items.append((m.translate((dx, dy, 0)), f"{label}_{('Left', 'Right')[k]}_Tool_Magnet", MAGNET))
                continue
            color = ORANGE if n == "P18" else (0.9, 0.65, 0.1) if (label, n) == ("Bambu", "body") else \
                (0.85, 0.3, 0.12) if n == "body" else (0.62, 0.62, 0.65)
            items.append((s.translate((dx, dy, 0)), f"{label}_{n.replace(' ', '_')}", color))
        for n, s, c in zip(P.DOCK_NAMES_R39, dock39, colors):
            items.append((s.translate((dx, 0, 0)), f"{label}_Dock_{n}", c))
    files.append(export_assembly(P.NAMES["review"], items, sum(len(s.Solids()) for s, _, _ in items)))
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p), "mb": round(p.stat().st_size / 1e6, 1)}
                         for p in files]
    report["review_bodies"] = sum(len(s.Solids()) for s, _, _ in items)


# --------------------------------------------------------------------------------------------
# Main
# --------------------------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--static-only", action="store_true", help="stop after the static checks")
    args = parser.parse_args()
    started = time.perf_counter()
    failures = []
    report = {"status": "PENDING"}
    print("Building", flush=True)
    bambu_hotend, _ = P37.bambu_hotend()
    parts = {"p22": P37.p22()[0], "p23": P37.p23(), "cable": P37.cable(), "beacon": P37.beacon(),
             "cartographer": P37.cartographer(), "ebb42": P37.ebb42(), "hardware": P37.probe_hardware(),
             "other_hardware": P37.other_hardware(), "dock": P37.dock(), "tools": b37.tools(bambu_hotend)}
    dock37, tools37 = parts["dock"], parts["tools"]
    yf = P.dock_face_y(dock37)
    p18_new = P.p18()
    dock39 = P.dock(dock37, yf)
    tools39 = P.tools(tools37, p18_new)

    print("Static checks", flush=True)
    check_p18(p18_new, report, failures)
    check_p25(dock39[0], dock37[0], yf, report, failures)
    check_hardware(p18_new, dock39[0], yf, report, failures)
    check_docked(tools39, dock39, tools37, dock37, yf, report, failures)
    check_tools(tools39, b37.carriage(parts), report, failures)
    report["static_failures"] = list(failures)
    if failures:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        raise SystemExit(f"Static failures: {failures}")
    if args.static_only:
        print(json.dumps({k: report[k] for k in ("p18", "p25", "hardware_fits", "docked", "tool_internal_and_mounted")},
                         indent=1, default=str))
        return

    print("Writing the revision-39 scene", flush=True)
    manifest = b37.write_scene(dict(parts, dock=dock39, tools=tools39))
    report["sources"] = manifest["sources"]
    specs = r36.specs()
    print(f"Requalification: {len(specs)} cases on {args.workers} workers", flush=True)
    results = fg.run_parallel(r36.run_task, specs, workers=args.workers)
    rack = {}
    r36.summarise(results, rack, failures)
    r36.rack_geometry(r36.scene(), rack, failures)
    rack["clearances_mm"] = {"r36_docks": rack["clearances_mm"]["r21"], "r39_dock": rack["clearances_mm"]["r36"]}
    report["requalification"] = rack

    print("Front print limit", flush=True)
    limit = front.measure(args.workers)
    r38 = json.loads((ROOT / FRONT_R38).read_text())
    before = r38["front_print_limit_nozzle_y_mm"]
    limit["method"] += " Revision-39 tools and docks: dowel pins in P25, bushings in P18."
    limit["revision_38_front_print_limit_nozzle_y_mm"] = before
    limit["print_depth_revision_38"] = r38["print_depth"]
    limit["gain_over_revision_38_mm"] = round(before - limit["front_print_limit_nozzle_y_mm"], 2)
    (ROOT / FRONT_REPORT).write_text(json.dumps(limit, indent=2, default=str) + "\n")
    front.summary(limit)
    report["front_print_limit"] = {k: limit[k] for k in (
        "status", "front_print_limit_nozzle_y_mm", "revision_38_front_print_limit_nozzle_y_mm",
        "gain_over_revision_38_mm", "worst_first_contact", "binding_features", "print_depth")}
    report["front_print_limit"]["report"] = FRONT_REPORT
    if limit["status"] != "FRONT_PRINT_LIMIT_MEASURED_NOT_COMMISSIONED" or limit["gain_over_revision_38_mm"] <= 0:
        failures.append("Front print limit")

    print("Exports", flush=True)
    exports(p18_new, dock39, tools39, report)
    report["hardware"] = {
        "per_tool": "P18: 2x 5x7x5.5 mm bushings pressed flush into the bar (was 2x Ø5x12 mm dowel pins); "
                    "2x Ø6x4 mm N52 magnets unchanged.",
        "per_dock": "P25: 2x Ø5x12 mm rounded dowel pins pressed 6.5 mm in, 5.5 mm proud (was 2x 5x7x5.5 mm "
                    "bushings); 2x Ø6x4 mm N52 magnets unchanged.",
        "totals_for_ten_tools_and_docks": "20 dowel pins, 20 bushings, 40 magnets: the same as before."}
    report["failures"] = failures
    report["status"] = ("DOCK_PINS_MOVED_TO_P25_RACK_REQUALIFIED_FRONT_LIMIT_MEASURED_CAD_REVIEW_NOT_MACHINE_QUALIFICATION"
                        if not failures else "FAILED_SEE_FAILURES")
    report["limitations"] = [
        "Rigid CAD and sampled straight paths. Press fits, bushing retention, magnet pull and pin wear are not "
        "qualified; the fits copy the released seats (bushing seat Ø7.04, pin bore Ø4.98).",
        "The dock pins stand 5.5 mm proud of an empty dock; nothing in the audited paths reaches them, but keep "
        "hands and wiring clear when servicing the rack.",
        "Both hotends use the same P18; the Red Lizard's released P18 snapshot (0.1 mm3 different) is replaced by it.",
        "World CAD coordinates; commission the slicer front limit on the machine."]
    report["runtime_s"] = round(time.perf_counter() - started, 1)
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    brief = {k: report[k] for k in ("status", "failures", "runtime_s")}
    brief["p18_walls"] = report["p18"]["wall_gauges_mm"]
    brief["docked"] = {k: report["docked"][k] for k in ("engagement", "magnet_gap_mm")}
    brief["front_limit"] = report["front_print_limit"]["front_print_limit_nozzle_y_mm"]
    brief["bed"] = rack["bed"]["summary"]
    brief["clearances_mm"] = {k: {kk: round(vv["mm"], 3) for kk, vv in v.items() if vv}
                              for k, v in rack["clearances_mm"].items()}
    print(json.dumps(brief, indent=1, default=str))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
