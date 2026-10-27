"""After revision 39: what else limits the print area, measured on the revision-39 scene. No part changes.

1. Front. Revision 39's first contact is P18's plate (down to Z-22.45) against a parked tool's rear face, whose
   lower block tops out at Z-19.28. Two what-ifs, on every tool: P18 cut at Z-18.28 (1 mm above that block), and
   P18 with its hardware removed. Same exact method as audit_front_print_limit_r38.py, over one bay pitch
   around bay 4 (the profile repeats every pitch) in 0.5 mm steps, both active tools.
2. Dock standoff. P25 holds the coupling face 6.5 mm off the crossbar; how close each dock part sits to the
   crossbar bounds how much of that could go.
3. Z ceiling. The highest nozzle Z before the flying gantry, or the rack it carries, reaches the frame.
"""

import argparse
import json
import os
import time

import build_and_verify_accessories_v26 as acc

os.environ.setdefault("SPARKSHIFT_SCENE", str(acc.WORK / "r39_scene"))

import audit_front_print_limit_r38 as A  # noqa: E402
import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import fast_geometry as fg  # noqa: E402
import r39_parts as P  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402
from audit_travel_limits_r34 import first_contact  # noqa: E402
from build_modular_toolhead import ROOT, box, primitives  # noqa: E402

REPORT = "verification_whats_left_r39.json"
ZCUT = -18.28
SCENARIOS = ("p18_trim", "no_p18")


def patch(scenario):
    for v in r36.scene()["variants"].values():
        parts = []
        for n, p in v["parts"]:
            if scenario == "no_p18" and n in ("P18", "bushings and magnets"):
                continue
            if scenario == "p18_trim" and n == "P18":
                p = p.intersect(box(-30, 30, 0, 60, ZCUT, 60))
            parts.append((n, p))
        v["parts"] = parts


def task(t):
    """One first-contact path; each scenario runs in its own worker pool, patched once per process."""
    active, x, scenario = t
    if "patched" not in A._GROUPS:
        patch(scenario)
        A._GROUPS["patched"] = scenario
    return A.task_profile((active, x))


def front(workers):
    c = r36.CENTERS[4]
    xs = [round(c + 0.5 * i, 3) for i in range(int(37.3 / 0.5) + 1)]
    out = {"x_mm": [xs[0], xs[-1]], "step_mm": 0.5, "p18_cut_z_mm": ZCUT}
    for scenario in SCENARIOS:
        rows = fg.run_parallel(task, [(a, x, scenario) for a in A.VARIANTS for x in xs], workers=workers)
        worst = max((r for r in rows if r.get("first_contact_nozzle_y_mm")), key=lambda r: r["first_contact_nozzle_y_mm"])
        binding = {}
        for r in rows:
            if r.get("pair"):
                k = f"{r['active']} {r['pair'][0]} -> {r['pair'][1].split(' ', 2)[-1]}"
                binding[k] = max(binding.get(k, -1e9), r["first_contact_nozzle_y_mm"])
        out[scenario] = {"worst_first_contact": worst, "binding_max_nozzle_y_mm": binding,
                         "failures": [r for r in rows if r.get("error") or not r.get("first_contact_nozzle_y_mm")]}
        print(scenario, worst, flush=True)
    return out


def standoff(s):
    f = s["frames"]
    crossbar = fg.index_group([("crossbar", s["fixed"]["Crossbar"])])
    rows = {}
    for name, solid in zip(P.DOCK_NAMES_R39, s["variants"]["Bambu"]["dock_solids"]):
        hit = fg.min_distance(fg.index_group([(name, r36.world(solid, r36.CENTERS[4], f))]), crossbar, cutoff=8.0)
        rows[name] = None if hit is None else round(hit[0], 3)
    cb = bounds(s["fixed"]["Crossbar"])
    pin = s["variants"]["Bambu"]["dock_solids"][P.LEFT]
    face = f["world_y_offset_mm"] - (bounds(pin)[2] + P.PIN["nose"])     # P25 coupling face, world Y
    return {"coupling_face_to_crossbar_mm": round(face - cb[3], 3), "dock_part_to_crossbar_mm": rows,
            "note": "The dock magnets overlap the crossbar's height band; the pins and jaws pass above or below it."}


def ceilings(s):
    tip0 = s["frames"]["world_z_offset_mm"] - 78.8794
    rows = json.loads((primitives.WORK / "frame_world_bodies.json").read_text())["rows"]
    frame = fg.index_group([(f"{r['path'].split('/')[-1]}/{r['body']}",
                             box(r["min"][0], r["max"][0], r["min"][1], r["max"][1], r["min"][2], r["max"][2]))
                            for r in rows if not r["body"].startswith("R1_BED")])
    names = json.loads((acc.WORK / "rack_audit_Flying_Gantry_world.json").read_text())
    groups = {
        "flying_gantry": fg.index_group([(f"gantry {m['name']}", x) for m, x in zip(names, s["fixed"]["Flying_Gantry"].Solids())]),
        "rack": fg.index_group([("crossbar", s["fixed"]["Crossbar"]), ("P29/P30", s["fixed"]["P29_P30_Hardware"])]
                               + [(f"dock {k}", d) for k, d in s["docks"].items()]
                               + [(f"parked {k}", t) for k, t in s["parked"].items()])}
    out = {}
    for label, g in groups.items():
        lo, hi = 250.0, 420.0
        while hi - lo > 0.01:
            mid = 0.5 * (lo + hi)
            lo, hi = (lo, mid) if first_contact([(g, frame)], (0, 0, mid - tip0)) else (mid, hi)
        out[label] = {"last_clear_nozzle_z_mm": round(lo, 2), "first_contact": first_contact([(g, frame)], (0, 0, hi - tip0))}
    out["note"] = "Voron's stock 2.4 350 configuration uses position_max 310."
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()
    started = time.perf_counter()
    report = {"front_what_ifs": front(args.workers)}
    s = r36.scene()
    report["dock_standoff"] = standoff(s)
    report["z_ceiling"] = ceilings(s)
    r39 = json.loads((ROOT / "verification_front_print_limit_r39.json").read_text())
    report["revision_39_first_contact_nozzle_y_mm"] = r39["worst_first_contact"]["first_contact_nozzle_y_mm"]
    report["runtime_s"] = round(time.perf_counter() - started, 1)
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    brief = {k: report["front_what_ifs"][k]["worst_first_contact"] for k in SCENARIOS}
    print(json.dumps({"front": brief, "standoff": report["dock_standoff"], "z": report["z_ceiling"],
                      "runtime_s": report["runtime_s"]}, indent=1, default=str))


if __name__ == "__main__":
    main()
