"""Revision 42: a P23 for the Cartographer V3, and the Cartographer's own keepout (parts in r42_parts.py).

Static checks:
- P23: a single valid solid, revision 37's P23 less its bottom 0.2 mm and nothing else; its webs and walls;
- heights: the Cartographer's coil 2.81 mm above the tip datum on this P23 (2.61 mm on revision 37's), and the
  Beacon's 2.60 mm on revision 37's P23 for comparison;
- screws: thread engagement in P22's inserts, and the gap from each tip to the end of its insert hole;
- fit: the Cartographer, this P23 and its screws against the whole revision-41 carriage (the Beacon, revision 37's
  P23 and the Beacon's screws taken out) and both mounted tools;
- keepouts: the Cartographer's own two zones, the last two solids of its model, against every metal part, with
  the probe on either P23. Metal of ours in either zone fails; the Monolith core's and the hotends' metal is
  recorded. The Beacon's zones against the core's metal, which revision 37 did not check;
- P28: the builder at 2.60 mm reproduces revision 37's jig; the new one differs only in its feeler.
Then, on a revision-42 scene (WORK/r42_scene) of the carriage as built for the Cartographer, the revision-36
full-rack requalification.

Run: python build_cartographer_mount_r42.py [--workers 10] [--static-only]
"""
import argparse
import json
import os
import time

import build_and_verify_accessories_v26 as acc
import build_carriage_fixes_r41 as V      # points SPARKSHIFT_SCENE at r41_scene; this revision's scene follows

os.environ["SPARKSHIFT_SCENE"] = str(acc.WORK / "r42_scene")

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import build_probe_height_datum_dock_r37 as b37  # noqa: E402
import fast_geometry as fg  # noqa: E402
import r37_parts as P37  # noqa: E402
import r42_parts as R  # noqa: E402
from audit_tool_owned_2510 import bounds, compound, overlaps  # noqa: E402
from build_bambu_clean_r29 import sha  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31, confined, mass_properties, same_properties  # noqa: E402
from build_fan_mounts_r33 import export_assembly, export_print  # noqa: E402
from build_modular_toolhead import ROOT, box, load  # noqa: E402

REPORT = "verification_cartographer_mount_r42.json"
PROBE = "Cartographer_V3_Raised"
BEACON_BUILD = ("Beacon_", P37.NAMES["p23"], "R37_PROBE_", "R37_REAR_")   # what the Cartographer build leaves out
TOOL_METAL = ("hotend", "screw", "insert", "magnet", "pin")
GREY, ORANGE, LIME, BOARD = (0.55, 0.57, 0.6), (0.95, 0.55, 0.12), (0.55, 0.85, 0.2), (0.1, 0.1, 0.12)
BRASS, STEEL, RED, PINK, TEAL = (0.8, 0.55, 0.2), (0.35, 0.35, 0.38), (0.9, 0.12, 0.12), (0.95, 0.6, 0.7), (0.0, 0.64, 0.61)


def r2(values):
    return [round(v, 3) for v in values]


def build_parts():
    parts = V.build_parts()
    parts["cartographer_r37"] = parts["cartographer"]
    parts["cartographer"] = R.cartographer()
    parts["p23c"] = R.p23()
    parts["carto_hardware"] = R.hardware()
    parts["p28c"] = R.p28()
    parts["tip"] = P37.tip_datum()
    return parts


def carriage(parts):
    """The revision-41 carriage as built for the Cartographer: this P23, the Cartographer and its screws, no
    Beacon. The Beacon's modelled cable stays, standing in for the probe cable's route up the raceway."""
    out = [(n, s) for n, s in V.carriage(parts) if not n.startswith(BEACON_BUILD)]
    return out + [(R.NAMES["p23"], parts["p23c"]), (PROBE, parts["cartographer"])] + list(parts["carto_hardware"])


def core_metal(rig):
    """The Monolith core's metal solids (is_metal in the v26 metadata; a solid without metadata counts as metal),
    the P03 magnets and the servo."""
    meta = json.loads((acc.WORK / "v26_meta.json").read_text())
    by_key = {V.key(P37.shape(s)): m for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))}
    out, unmatched = {}, 0
    for i, s in enumerate(load(R31["core"]).Solids()):
        name = f"Core_{i:03d}"
        if name not in rig:
            continue
        m = by_key.get(V.key(s))
        unmatched += m is None
        if m is None:
            out[f"{name}_no_metadata"] = rig[name]
        elif m.get("is_metal"):
            out[m["name"]] = rig[name]
    out.update({n: s for n, s in rig.items() if n.startswith("P03_Magnet_") or n == V.SERVO})
    return out, unmatched


def tool_metal(parts):
    out = {}
    for label, v in parts["tools"].items():
        out[f"{label}_hotend"] = v["hotend"]
        for n, s in v["parts"]:
            if V.key(s) != V.key(v["hotend"]) and any(k in n for k in TOOL_METAL):
                out[f"{label}_{n}"] = s
    return out


# --------------------------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------------------------

def check_p23(parts, report, failures):
    old, new = parts["p23"], parts["p23c"]
    slab = box(-25.0, 25.0, -30.0, 15.0, P37.Z_SEAT - 1.0, R.SEAT)
    removed, expected, added = old.cut(new).Volume(), old.intersect(slab).Volume(), new.cut(old).Volume()
    gauges = {"thickness_mm": P37.Z_TOP - R.SEAT, "web_under_spigot_sockets_mm": P37.SOCKET_BOTTOM - R.SEAT,
              "beacon_relief_depth_mm": P37.RELIEF_TOP - R.SEAT, "plate_over_relief_mm": P37.Z_TOP - P37.RELIEF_TOP}
    rings = []
    for x, y in P37.P22_MOUNTS:
        ring = load_ring(x, y)                    # 1.1 mm of wall round each 3.15 mm spigot socket
        rings.append(round(ring.Volume() - ring.intersect(new.copy()).Volume(), 4))
    report["p23"] = {"valid": new.isValid(), "solids": len(new.Solids()), "volume_mm3": {"r37": old.Volume(), "r42": new.Volume()},
                     "bounds_mm": {"r37": r2(bounds(old)), "r42": r2(bounds(new))},
                     "removed_mm3": removed, "slab_of_r37_mm3": expected, "added_mm3": added, "gauges": gauges,
                     "socket_wall_missing_mm3": rings}
    if not new.isValid() or len(new.Solids()) != 1 or abs(removed - expected) > 1e-3 or added > 1e-3:
        failures.append("P23 is not revision 37's less its bottom 0.2 mm")
    if gauges["web_under_spigot_sockets_mm"] < 1.2 or max(rings) > 1e-3:
        failures.append("P23 web or socket wall")


def load_ring(x, y):
    import cadquery as cq
    outer = cq.Solid.makeCylinder(3.15 + 1.1, 0.5, cq.Vector(x, y, -72.25), cq.Vector(0, 0, 1))
    return outer.cut(cq.Solid.makeCylinder(3.16, 0.5, cq.Vector(x, y, -72.25), cq.Vector(0, 0, 1)))


def check_heights(parts, report, failures):
    tip, b = parts["tip"], parts["beacon"]
    board = max(parts["cartographer"].Solids(), key=lambda s: s.BoundingBox().xlen * s.BoundingBox().ylen)
    bb = bounds(board)
    report["probe_heights"] = {
        "tip_datum_z_mm": tip,
        "Cartographer_V3_on_r42_P23": {"coil_face_z_mm": R.COIL_FACE, "above_tip_mm": R.COIL_FACE - tip},
        "Cartographer_V3_on_r37_P23": {"coil_face_z_mm": R.COIL_FACE - R.RAISE, "above_tip_mm": R.COIL_FACE - R.RAISE - tip},
        "Beacon_RevH_on_r37_P23": {"coil_face_z_mm": bounds(b[0])[5], "above_tip_mm": bounds(b[0])[5] - tip},
        "cartographer_board_z_mm": r2(bb[4:]),
        "makers": {"Beacon": "nominally 2.6 mm", "Cartographer": "2.6 to 3.0 mm"},
        "p28_feeler_mm": R.FEELER}
    h = R.COIL_FACE - tip
    if not 2.75 <= h <= 2.85 or abs(R.FEELER - h) > 0.005 or abs(bb[4] - R.COIL_FACE) > 1e-3 or abs(bb[5] - R.SEAT) > 1e-3:
        failures.append("Cartographer height")


def check_screws(parts, report, failures):
    rows = {}
    for n, s in parts["carto_hardware"]:
        if "HEATSET" not in n:
            top = bounds(s)[5]
            rows[n] = {"tip_z_mm": top, "engagement_mm": min(top, P37.SPIGOT_Z[1]) - P37.SPIGOT_Z[0],
                       "tip_to_insert_hole_end_mm": P37.INSERT_HOLE_Z[1] - top}
    report["screws"] = {"rows": rows, "m3x6_tip_to_insert_hole_end_mm": P37.INSERT_HOLE_Z[1] - (R.COIL_FACE + 6.0)}
    probe = [r for n, r in rows.items() if "CARTO" in n]
    rear = [r for n, r in rows.items() if "REAR" in n]
    if min(r["engagement_mm"] for r in probe) < 1.9 or min(r["tip_to_insert_hole_end_mm"] for r in probe) < 0.5 \
            or min(r["engagement_mm"] for r in rear) < 2.0 or min(r["tip_to_insert_hole_end_mm"] for r in rear) < 0.2:
        failures.append("Screw length")


def check_fit(parts, report, failures):
    rig = dict(carriage(parts))
    left_out = sorted(n for n, _ in V.carriage(parts) if n.startswith(BEACON_BUILD))
    mine = {PROBE: parts["cartographer"], R.NAMES["p23"]: parts["p23c"], **dict(parts["carto_hardware"])}
    rest = {n: s for n, s in rig.items() if n not in mine and n != P37.NAMES["cable"]}
    rows = b37.overlap_rows(mine, {**mine, **rest})
    mounted = []
    for label, v in parts["tools"].items():
        for name, s in v["parts"]:
            mounted += [{"tool": label, "part": name, "b": t, "mm3": m} for t, m in overlaps(s, mine).items()]
    near = {n: s for n, s in rig.items() if not n.startswith("Core_")}
    lows = sorted(((bounds(s)[4], n) for n, s in near.items()), key=lambda t: t[0])[:6]
    report["fit"] = {
        "left_out_for_the_cartographer": left_out,
        "checked": "The Cartographer, this P23 and its screws against each other and the whole revision-41 carriage "
                   "(core with P01-P03 and magnets, servo, P20-P22, P24, EBB42, all fasteners); the probe cable is "
                   "left out, as the Cartographer's own is not modelled.",
        "intersections_mm3": rows, "mounted_tools_mm3": mounted,
        "gap_to_p22_mm": parts["cartographer"].distance(parts["p22"]),
        "lowest_features_above_tip_mm": [{"part": n, "z_mm": z, "above_tip_mm": z - parts["tip"]} for z, n in lows]}
    if len(left_out) != 10 or rows or mounted:
        failures.append("Cartographer build fit")


def intrusions(zone, group, base_z):
    out = {}
    for n in overlaps(zone, group):
        hit = group[n].intersect(zone)
        b = bounds(hit)
        out[n] = {"mm3": round(hit.Volume(), 3), "bounds_mm": r2(b), "above_board_mm": r2((b[4] - base_z, b[5] - base_z))}
    return out


def check_keepouts(parts, report, failures):
    rig = dict(carriage(parts))
    core, unmatched = core_metal(rig)
    tools = tool_metal(parts)
    out = {"core_metal_parts": len(core), "core_solids_without_metadata_counted_as_metal": unmatched,
           "tool_metal_parts": sorted(tools)}
    for tag, dz, hw in (("cartographer_on_r37_p23_2p61", P37.DZ, parts["hardware"]),
                        ("cartographer_on_r42_p23_2p81", R.DZ, parts["carto_hardware"])):
        ours = {**dict(hw), **dict(parts["other_hardware"]), "EBB42": parts["ebb42"]}
        rows = {}
        for zone, ko in R.keepouts(dz).items():
            base = bounds(ko)[4]
            rows[zone] = {"bounds_mm": r2(bounds(ko)), "volume_mm3": ko.Volume(),
                          "our_metal": intrusions(ko, ours, base), "core_metal": intrusions(ko, core, base),
                          "tool_metal": intrusions(ko, tools, base),
                          "nearest_metal_of_ours_mm": min(ko.distance(s) for s in ours.values())}
            if rows[zone]["our_metal"]:
                failures.append(f"Our metal in the Cartographer's {zone} keepout ({tag})")
        out[tag] = rows
    b = parts["beacon"]
    out["beacon_on_r37_p23"] = {zone: {"core_metal": intrusions(ko, core, bounds(ko)[4]),
                                       "tool_metal": intrusions(ko, tools, bounds(ko)[4])}
                                for zone, ko in (("top", P37.beacon_top_keepout(b)), ("bottom", b[0]))}
    out["note"] = ("The Cartographer's zones come from its own model (solids 100 and 101). Metal of ours fails the check; "
                   "the core's and the hotends' is existing design, recorded here and not changed.")
    report["keepouts"] = out


def check_p28(parts, report, failures):
    released, rebuilt, new = load(P37.NAMES["p28"]), P37.p28(2.60), parts["p28c"]
    reproduced = same_properties(mass_properties(rebuilt), mass_properties(released))
    zone = (-9.6, 9.6, -12.6, -2.9, 8.0 + 2.60 - 0.01, 8.0 + R.FEELER + 0.01)
    conf = confined(new.copy(), rebuilt.copy(), [zone])
    pad_top = bounds(new.intersect(box(-9.6, 9.6, -12.6, -2.9, 8.0, 14.0)))[5]
    report["p28"] = {"rebuild_at_2p60_reproduces_r37": reproduced, "feeler_mm": {"r37": 2.60, "r42": R.FEELER},
                     "pad_top_z_mm": pad_top, "unchanged_outside_the_feeler": conf["unchanged_outside_zones"],
                     "volume_mm3": {"r37": released.Volume(), "r42": new.Volume()}}
    if not reproduced or not conf["unchanged_outside_zones"] or abs(pad_top - (8.0 + R.FEELER)) > 1e-3:
        failures.append("P28")


# --------------------------------------------------------------------------------------------
# Exports
# --------------------------------------------------------------------------------------------

def review_items(parts):
    """Both builds side by side for Fusion: the Beacon on revision 37's P23 at X-70, the Cartographer on this P23
    in place; each with P22, P01, its screws, its keepout zones, the core's metal near them and the Red Lizard."""
    rig = dict(carriage(parts))
    core, _ = core_metal(rig)
    near_core = {n: s for n, s in core.items() if n.startswith(("MONOC_M3_NUT", "MONOC_M3x16_DRAW")) and "41.8" in n}
    hotend = parts["tools"]["RedLizard"]["hotend"]
    b = parts["beacon"]
    common = [(parts["p22"], "P22", TEAL), (rig[V.R.NAMES["p01"]], "P01", GREY), (hotend, "RedLizard_hotend", (0.7, 0.7, 0.72))]
    common += [(s, n, STEEL) for n, s in near_core.items()]
    builds = {
        "Cartographer": (0.0, [(parts["p23c"], R.NAMES["p23"], LIME), (parts["cartographer"], PROBE, BOARD)]
                         + [(s, n, BRASS if "HEATSET" in n else STEEL) for n, s in parts["carto_hardware"]]
                         + [(ko, f"Cartographer_keepout_{z}", RED if z == "top" else PINK) for z, ko in R.keepouts().items()]),
        "Beacon": (-70.0, [(parts["p23"], P37.NAMES["p23"], LIME), (compound(b[2:5]), "Beacon_RevH", BOARD)]
                   + [(s, n, BRASS if "HEATSET" in n else STEEL) for n, s in parts["hardware"]]
                   + [(P37.beacon_top_keepout(b), "Beacon_keepout_top", RED), (b[0], "Beacon_keepout_bottom", PINK)]),
    }
    items = []
    for build, (dx, own) in builds.items():
        for s, n, c in common + own:
            items.append((s.translate((dx, 0, 0)), f"{build}_{n}", c))
    return items


def exports(parts, report):
    files = export_print(R.NAMES["p23"], parts["p23c"]) + export_print(R.NAMES["p28"], parts["p28c"])
    hw = parts["carto_hardware"]
    files.append(export_assembly(R.NAMES["hardware"], [(s, n, BRASS if "HEATSET" in n else STEEL) for n, s in hw], len(hw)))
    ko = R.keepouts()
    files.append(export_assembly(R.NAMES["keepouts"], [(ko["top"], "Cartographer_keepout_top_no_metal", RED),
                                                       (ko["bottom"], "Cartographer_zone_under_coil", PINK)], 2))
    items = review_items(parts)
    expected = sum(len(s.Solids()) for s, _, _ in items)
    files.append(export_assembly(R.NAMES["review"], items, expected))
    report["review_bodies"] = expected
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p), "mb": round(p.stat().st_size / 1e6, 1)}
                         for p in files]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--static-only", action="store_true", help="stop after the static checks")
    args = parser.parse_args()
    started = time.perf_counter()
    failures, report = [], {"status": "PENDING", "raise_mm": R.RAISE}
    print("Building", flush=True)
    parts = build_parts()
    print("Static checks", flush=True)
    for check in (check_p23, check_heights, check_screws, check_fit, check_keepouts, check_p28):
        t0 = time.perf_counter()
        check(parts, report, failures)
        print(f"  {check.__name__}: {time.perf_counter() - t0:.0f} s, failures {failures}", flush=True)
    report["static_failures"] = list(failures)
    if failures or args.static_only:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        if failures:
            raise SystemExit(f"Static failures: {failures}")
        return

    print("Writing the revision-42 scene", flush=True)
    b37.carriage = carriage
    manifest = b37.write_scene(parts)
    report["sources"] = manifest["sources"]
    specs = r36.specs()
    print(f"Requalification: {len(specs)} cases on {args.workers} workers", flush=True)
    results = fg.run_parallel(r36.run_task, specs, workers=args.workers)
    rack = {}
    r36.summarise(results, rack, failures)
    r36.rack_geometry(r36.scene(), rack, failures)
    rack["clearances_mm"] = {"r36_docks": rack["clearances_mm"]["r21"], "r39_dock": rack["clearances_mm"]["r36"]}
    report["requalification"] = rack

    print("Exports", flush=True)
    exports(parts, report)
    report["hardware"] = {
        "cartographer": "2x M3x5 low-profile socket heads (head 5.5 x 1.5) through the Cartographer's board and this P23 "
                        "into the same 2x M3 x 3 mm inserts in P22. An M3x6 would end 0.07 mm short of the insert "
                        "hole's end.",
        "p23_to_p22": "Unchanged: 2x M3x4 ISO 7380 button heads on the rear ears into P22's inserts.",
        "modelled_shank_diameter_mm": 2 * P37.SHANK_R}
    report["limitations"] = [
        "Rigid CAD and sampled straight paths. Insert pull-out, P23 creep under the probe clamp and the probe's "
        "electrical behaviour are not qualified.",
        "The Cartographer's keepouts are its model's own zones. The metal recorded in them belongs to the Monolith core "
        "and the Red Lizard hotend, is existing design and is not changed; its effect on readings is not qualified.",
        "The Cartographer's own cable route is not modelled; the Beacon's cable route stands in for it in the "
        "requalification and is left out of the fit and keepout checks."]
    report["failures"] = failures
    report["status"] = ("CARTOGRAPHER_P23_KEEPOUT_CHECKED_RACK_REQUALIFIED_CAD_REVIEW_NOT_MACHINE_QUALIFICATION"
                        if not failures else "FAILED_SEE_FAILURES")
    report["runtime_s"] = time.perf_counter() - started
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    brief = {k: report[k] for k in ("status", "failures", "probe_heights", "runtime_s")}
    brief["bed"] = rack["bed"]["summary"]
    print(json.dumps(brief, indent=1, default=str))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
