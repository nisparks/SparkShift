"""Revision 38: the front print limit from exact 3D contact with the parked rack. No part changes.

Revision 34 set the front of the print area by whole-envelope separation: the rearmost point of any parked
tool or dock (Y35.41, the P26 chute lip) plus the active toolhead's deepest point ahead of its nozzle (27.8 mm),
so nozzle Y63.21 across the whole bed. The rack rides on the gantry at the active tool's height, so only solids
that really meet limit the approach, and the active tool's leading features (coupling pins and magnets, P18)
are narrower than the envelope.

Method: the active tool (Bambu or Red Lizard) on the revision-37 carriage, carrying both probes at once, moves
toward the rack at every nozzle X across the bed (1 mm steps). Fixed: all ten bays holding both parked tool
variants at once, so any mix of tools is covered and the active tool's own bay counts as occupied. Also fixed:
the ten docks, the crossbar, the P29/P30 mounts and the Monolith flying gantry with its Y rails. Each path starts
at the audited X corridor (nozzle Y80.71), steps 2 mm forward and bisects the first exact contact
(fast_geometry.touch_or_nest) to 0.01 mm. The print limit keeps a margin behind the worst first contact. It is
then re-verified contact-free every 0.1 mm of X for both active tools.

The X beam's path from the corridor to the dock and the carriage-to-beam fit are covered by the revision-36
requalification, rerun with the revision-37 parts. The scene is the revision-37 cache that
build_probe_height_datum_dock_r37.py writes (WORK/r37_scene).
"""

import argparse
import hashlib
import json
import math
import os
import re
import time

import build_and_verify_accessories_v26 as acc

os.environ.setdefault("SPARKSHIFT_SCENE", str(acc.WORK / "r37_scene"))

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import fast_geometry as fg  # noqa: E402
from audit_travel_limits_r34 import BED_REAR, first_contact, print_depth  # noqa: E402
from build_modular_toolhead import ROOT  # noqa: E402

REPORT = "verification_front_print_limit_r38.json"
TRAVEL_R34 = "verification_travel_limits_r34.json"
VARIANTS = ("Bambu", "RedLizard")
CORRIDOR_DY = 60.0          # nozzle Y80.71: X traverse audited clear for X0..350 (revision-36 requalification)
STEP, TOL = 2.0, 0.01
MARGIN = 1.0                # print limit kept this far behind the worst first contact, as at the rear
VERIFY_STEP = 0.1
X_PROFILE = [float(x) for x in range(0, 351)]

_GROUPS = {}


def groups(active):
    """[(moving, fixed)] for one active tool, both at nozzle X0 and the dock nozzle Y."""
    if active not in _GROUPS:
        s = r36.scene()
        f = s["frames"]
        v = s["variants"][active]
        moving = [(f"tool {n}", r36.world(p, 0.0, f)) for n, p in v["parts"]]
        moving += [(f"carriage {n}", r36.world(p, 0.0, f)) for n, p in s["carriage_parts"]]
        moving += [("carriage Cartographer_V3", r36.world(s["cartographer"], 0.0, f))]
        parked = [(f"parked T{i} {label} {n}", r36.world(p, center, f))
                  for i, center in enumerate(r36.CENTERS) for label, pv in s["variants"].items() for n, p in pv["parts"]]
        fixed = fg.index_group(parked + [(f"dock {k}", d) for k, d in s["docks"].items()]
                               + [("Crossbar", s["fixed"]["Crossbar"]),
                                  ("P29_P30_Hardware", s["fixed"]["P29_P30_Hardware"])])
        names = json.loads((acc.WORK / "rack_audit_Flying_Gantry_world.json").read_text())
        flying = s["fixed"]["Flying_Gantry"].Solids()
        if len(names) != len(flying):
            raise ValueError("Flying gantry snapshot and names differ")
        fixed += fg.index_group([(f"Flying_Gantry {m['name']}", sol) for m, sol in zip(names, flying)])
        _GROUPS[active] = [(fg.index_group(moving), fixed)]
    return _GROUPS[active]


def contact(active, x, dy):
    return first_contact(groups(active), (x, dy, 0.0))


def dock_y():
    f = r36.scene()["frames"]
    return f["world_y_offset_mm"] - 22.7


def task_profile(task):
    """First contact walking forward from the corridor at one nozzle X."""
    active, x = task
    base = dock_y()
    dy = CORRIDOR_DY
    if contact(active, x, dy):
        return {"active": active, "x_mm": x, "error": "contact at the audited corridor"}
    while dy - STEP > -30.0:
        if contact(active, x, dy - STEP):
            lo, hi = dy - STEP, dy                       # lo touches, hi is clear
            while hi - lo > TOL:
                mid = 0.5 * (lo + hi)
                lo, hi = (mid, hi) if contact(active, x, mid) else (lo, mid)
            return {"active": active, "x_mm": x, "first_contact_nozzle_y_mm": round(base + hi, 3),
                    "pair": contact(active, x, lo)}
        dy -= STEP
    return {"active": active, "x_mm": x, "first_contact_nozzle_y_mm": None, "pair": None}


def task_verify(task):
    """Contacts at the print limit for a run of nozzle X positions."""
    active, xs, nozzle_y = task
    dy = nozzle_y - dock_y()
    return {"active": active, "x_mm": [xs[0], xs[-1]], "samples": len(xs),
            "hits": [{"x_mm": x, "pair": hit} for x in xs for hit in [contact(active, x, dy)] if hit]}


def nearest(active, x, nozzle_y, cutoff):
    hit = fg.min_distance(*groups(active)[0], offset_a=(x, nozzle_y - dock_y(), 0.0), cutoff=cutoff)
    if hit is None:
        return None
    return {"mm": round(hit[0], 3), "moving": hit[1], "fixed": hit[2],
            "moving_point_world_mm": [round(v, 2) for v in hit[3]],
            "fixed_point_world_mm": [round(v, 2) for v in hit[4]]}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    started = time.perf_counter()
    scene = r36.scene_dir()
    travel = json.loads((ROOT / TRAVEL_R34).read_text())
    old_front = travel["front"]["front_print_limit_nozzle_y_mm"]
    soft = travel["rear"]["recommended_soft_limit_nozzle_y_mm"]

    print(f"Profile: {len(X_PROFILE)} nozzle X positions x {len(VARIANTS)} active tools", flush=True)
    profile = fg.run_parallel(task_profile, [(a, x) for a in VARIANTS for x in X_PROFILE], workers=args.workers)
    failures = [r for r in profile if r.get("error") or r.get("first_contact_nozzle_y_mm") is None]
    worst = max((r for r in profile if r.get("first_contact_nozzle_y_mm") is not None),
                key=lambda r: r["first_contact_nozzle_y_mm"])
    limit = math.ceil((worst["first_contact_nozzle_y_mm"] + MARGIN) * 100.0 - 1e-6) / 100.0

    print(f"Verify nozzle Y{limit:.2f} every {VERIFY_STEP} mm of X", flush=True)
    xs = [round(VERIFY_STEP * i, 3) for i in range(int(round(350.0 / VERIFY_STEP)) + 1)]
    chunks = [xs[i:i + 50] for i in range(0, len(xs), 50)]
    checks = fg.run_parallel(task_verify, [(a, c, limit) for a in VARIANTS for c in chunks], workers=args.workers)
    hits = [h for c in checks for h in c["hits"]]

    by_variant = {}
    for a in VARIANTS:
        rows = [r for r in profile if r["active"] == a and r.get("first_contact_nozzle_y_mm") is not None]
        w = max(rows, key=lambda r: r["first_contact_nozzle_y_mm"])
        b = min(rows, key=lambda r: r["first_contact_nozzle_y_mm"])
        by_variant[a] = {"worst": w, "best": b,
                         "contact_at_worst": nearest(a, w["x_mm"], w["first_contact_nozzle_y_mm"], 0.1),
                         "clearance_at_print_limit": nearest(a, w["x_mm"], limit, 5.0)}
    binding = {}
    for r in profile:
        if r.get("pair"):
            fixed = re.sub(r" T\d ", " ", r["pair"][1])
            key = f"{r['active']} {r['pair'][0]} -> {fixed}"
            e = binding.setdefault(key, {"positions": 0, "max_first_contact_nozzle_y_mm": -1e9})
            e["positions"] += 1
            e["max_first_contact_nozzle_y_mm"] = max(e["max_first_contact_nozzle_y_mm"], r["first_contact_nozzle_y_mm"])

    depth_old = print_depth(old_front, soft)
    depth_new = print_depth(limit, soft)
    report = {
        "status": "FRONT_PRINT_LIMIT_MEASURED_NOT_COMMISSIONED" if not failures and not hits else "CHECK_RESULTS",
        "frame": "World CAD coordinates: bed X0..350; revision-34 bed front edge Y40; nozzle positions.",
        "method": ("Active tool + revision-37 carriage (both probes) moved toward the rack at nozzle X0..350 every "
                   "1 mm, from the audited corridor in 2 mm steps, first exact contact bisected to 0.01 mm. Fixed: "
                   "all ten bays with both parked tool variants, ten docks, crossbar, P29/P30 mounts, flying "
                   "gantry with Y rails. The limit is then re-verified every 0.1 mm of X."),
        "sources": {"scene": str(scene), "scene_manifest_sha256": sha(scene / "manifest.json"),
                    "travel_r34": {"file": TRAVEL_R34, "sha256": sha(ROOT / TRAVEL_R34)}},
        "revision_34_front_print_limit_nozzle_y_mm": old_front,
        "dock_nozzle_y_mm": dock_y(),
        "worst_first_contact": worst,
        "by_active_tool": by_variant,
        "binding_features": binding,
        "margin_mm": MARGIN,
        "front_print_limit_nozzle_y_mm": limit,
        "gain_mm": round(old_front - limit, 2),
        "verification_at_limit": {"x_step_mm": VERIFY_STEP, "samples": sum(c["samples"] for c in checks),
                                  "hits": hits},
        "profile_failures": failures,
        "rear_soft_limit_nozzle_y_mm": soft,
        "print_depth_revision_34": depth_old,
        "print_depth": depth_new,
        "bed_options_rear_mm": BED_REAR,
        "profile": [{"active": r["active"], "x_mm": r["x_mm"], "y_mm": r.get("first_contact_nozzle_y_mm"),
                     "pair": r.get("pair")} for r in profile],
        "limitations": [
            "Every bay holds both parked tool variants at once and the active tool's own bay counts as occupied: "
            "conservative for any real mix of tools.",
            "Parked tools sit on the modeled dock seat; the margin covers small seating and frame errors only.",
            "Hoses, cable chains, umbilicals and toolhead wiring are not modeled.",
            "Tool changes run forward of this limit, so a Klipper Y soft limit cannot enforce it: use the slicer "
            "bed shape (or an excluded front strip) and keep the toolchange macros' straight-Y bay moves.",
            "World CAD coordinates; commission the firmware/slicer values on the machine.",
        ],
        "runtime_s": round(time.perf_counter() - started, 1),
    }
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: report[k] for k in ("status", "worst_first_contact", "front_print_limit_nozzle_y_mm",
                                             "gain_mm", "binding_features", "runtime_s")}, indent=1, default=str))
    for a, v in by_variant.items():
        print(a, json.dumps({k: v[k] for k in ("contact_at_worst", "clearance_at_print_limit")}, default=str))
    for option, d in depth_new.items():
        print(f"{option}: depth {depth_old[option]['depth_mm']:.2f} -> {d['depth_mm']:.2f} mm, "
              f"mesh bed Y {d['probe_mesh_bed_y_range_mm'][0]:.2f}..{d['probe_mesh_bed_y_range_mm'][1]:.2f}")
    print(f"verification hits: {len(hits)}; profile failures: {len(failures)}")


if __name__ == "__main__":
    main()
