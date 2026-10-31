"""Collect the printability, outlet-balance and repeatability evidence of the C28 balance round into one report.

Usage: python report_outlet_balance_r43.py
Needs cfd_outlet_balance_r43.py --mean on each averaged case (and on the current snapshot case), and the session
printability scorecard (printability_scorecard.py) in WORK. Writes verification_outlet_balance_r43.json.
"""
import hashlib
import json
from pathlib import Path

import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import cfd_cpap_r43 as A
import cfd_direct_mount_r43 as D
import cfd_outlet_balance_r43 as B
from build_modular_toolhead import ROOT

CASES = {   # label: (case, description)
    "current": ("r43avgV5d_bambu_bed", "Current Bambu set: C28 outlets, flow-neutral user post (v5d)"),
    "centre_slot_1p1": ("r43avgV5dD11_bambu_bed", "Current set with the 1.1 mm centre slot (D11 outlet)"),
    "side_jet_visor": ("r43avgV5dVisor_bambu_bed", "Current set, side-jet roof lowered 1.7 mm to Z-75.3 (screening)"),
    "side_jet_visor_mild": ("r43avgV5dVisorMild_bambu_bed",
                            "Current set, side-jet roof lowered 1.0 mm to Z-74.6 (screening)"),
    "current_repeat": ("r43avgV5dRep_bambu_bed", "Byte-identical repeat of the current case (run-to-run spread)"),
    "side_jet_lip_trim_1p5": ("r43avgV5dLip15_bambu_bed",
                              "Current set, each side jet's floor lip trimmed back 1.5 mm from the exit (screening)"),
    "side_jet_vanes_vc3": ("r43avgV5dVC3_bambu_bed",
                           "Current set, three 0.45 mm straightening vanes across each side-jet passage at Y 20.6, 23.2 "
                           "and 25.6, inside the duct (screening; within the hotend clearance limits)"),
    "side_jet_louver_l30": ("r43avgV5dL30_bambu_bed",
                            "Current set, a 0.5 mm louver blade along each side jet: exit edge at |X| 10.25, Z-75.3, "
                            "rising outward at 30 degrees (screening; within the hotend clearance limits)"),
    "side_jet_roof_ramp_r45": ("r43avgV5dR45_bambu_bed",
                               "Current set, each side jet's roof ends in a straight 45-degree ramp from the slot face "
                               "into the bell-mouth round, roof 0.92 mm lower at the exit (screening; within the hotend "
                               "clearance limits)"),
    "side_jet_louver_vanes_lv3": ("r43avgV5dLV3_bambu_bed",
                                  "Current set, the L30 louver and the VC3 vanes together (screening; within the "
                                  "hotend clearance limits)"),
    "side_chamber_user_u_u1": ("r43avgV5dU1_bambu_bed",
                               "Current set, the user's U end in each side chamber: the lower-front corner rounded "
                               "and the front wall curled back to the ceiling, following the front wall forward at "
                               "|X| 12.6-15.8 (screening; within the hotend clearance limits)"),
    "side_jet_roof_ramp_vanes_rv3": ("r43avgV5dRV3_bambu_bed",
                                     "Current set, the R45 roof ramp and the VC3 vanes together (screening; within the "
                                     "hotend clearance limits)"),
    "side_chamber_front_reach_f08": ("r43avgV5dF08_bambu_bed",
                                     "Current set, each side chamber's front wall thinned from the inside to about "
                                     "0.8 mm (0.82 mm minimum) between Z-76.65 and -71.6, so more chamber air sits in "
                                     "front of the jet passage (screening; within the hotend clearance limits)"),
    "side_jet_roof_ramp_chamfer_rc": ("r43avgV5dRC_bambu_bed",
                                      "Current set, the R45 roof ramp plus a floor-lip chamfer from |X| 11.2 down to "
                                      "Z-77.45 at the slot face, 0.4 mm lip left (screening; within the hotend "
                                      "clearance limits)"),
    "side_jet_louver_chamfer_lc": ("r43avgV5dLC_bambu_bed",
                                   "Current set, the L30 louver plus the same floor-lip chamfer (screening; within the "
                                   "hotend clearance limits)"),
    "rejected_nozzles_n22": ("r43avgV5dN22_bambu_bed",
                             "REJECTED, breaks the hotend clearance limit (1.27 mm to the sock): side-jet nozzles "
                             "turned down 22 degrees reaching into the hotend slot to |X| 8.27, plus two vanes"),
    "rejected_plates_ab": ("r43avgV5dAimAB_bambu_bed",
                           "REJECTED, breaks the hotend clearance limit (1.20 mm to the sock): three guide plates in "
                           "each side chamber and a 28-degree deflector lip reaching into the hotend slot to |X| 8.2"),
}
KEYS = ("left", "right", "centre")


def summary(case, mean=True):
    report = json.loads((C.results_dir(case) / f"outlet_balance{'_mean' if mean else ''}.json").read_text())
    op = report["operating_point_1m_hose"]
    factor = op["lpm"] / 180
    cov = D.coverage(B.load(case, mean), factor)
    sectors = cov["sector_area_mean_speed_ms"]
    over = {k: report["delivery"][k]["lpm_reaching_r10"] for k in KEYS}
    near = {k: report["delivery"][k]["lpm_reaching_r5"] for k in KEYS}
    rising = {k: report["outlets"][k]["lpm"] * report["delivery"][k]["up_pct"] / 100 for k in KEYS}
    return {
        "mesh_cells": P.mesh_stats(case)["cells"],
        "inlet_total_pa_at_180": A.rows_of(case)[0]["inlet_total_pa"],
        "operating_point_1m_hose": op,
        "outlets_at_180": {k: {f: report["outlets"][k][f] for f in ("lpm", "share_pct", "mean_ms", "max_ms",
                                                                     "angle_below_horizontal_deg")} for k in KEYS},
        "near_print_sectors_ms": sectors, "sector_mean_ms": sum(sectors.values()) / 4,
        "weakest_to_strongest": cov["weakest_to_strongest_sector_mean_ratio"],
        "over_print_r10_lpm_at_operating_point": {k: v * factor for k, v in over.items()},
        "over_print_r5_lpm_at_operating_point": {k: v * factor for k, v in near.items()},
        "rising_past_hotend_lpm_at_operating_point": {k: v * factor for k, v in rising.items()},
        "over_print_r10_total_lpm_at_operating_point": sum(over.values()) * factor,
        "rising_total_lpm_at_operating_point": sum(rising.values()) * factor,
        "pressure_budget_at_180": report["pressure_budget"],
        "fields": report["fields"],
    }


def focus_summary(case):
    """Aim and bead delivery from cfd_nozzle_focus_r43.py, when it has been run on the case."""
    path = C.results_dir(case) / "nozzle_focus.json"
    if not path.exists():
        return None
    f = json.loads(path.read_text())
    return {"totals_lpm_at_operating_point": f["totals_lpm"], "near_print_ring_mean_ms": f["near_print_ring_mean_ms"],
            "side_spill_lpm": f.get("side_spill_lpm"),
            "outlets": {k: {kk: v[kk] for kk in ("down_deg", "forward_deg", "aim_pct", "delivery_pct",
                                                  "scrubs_hotend_pct", "opening")} for k, v in f["outlets"].items()}}


def tip_summary(case):
    """Where the air passes the nozzle tip, from cfd_tip_approach_r43.py, when it has been run on the case."""
    path = C.results_dir(case) / "tip_approach.json"
    if not path.exists():
        return None
    t = json.loads(path.read_text())
    a = t["closest_approach"]
    return {"cells_lpm_at_operating_point": a["cells"], "cells_by_outlet_lpm": a.get("cells_by_outlet"),
            "mean_passing_point_mm": {k: a[k] for k in ("left", "right", "centre", "all")},
            "aim_line": t.get("aim_line"), "below_tip": t.get("below_tip"),
            "hot_nozzle_cold_bead": t.get("hot_nozzle_cold_bead"),
            "nozzle_surface_band_means_ms": t["nozzle_surface"]["band_means_ms"],
            "print_level_sectors_ms": t["print_level"]["sectors_ms"], "print_level_peak_r5": t["print_level"]["peak_r5"]}


def main():
    out = {"method": "OpenFOAM v2512 simpleFoam, k-omega SST, 180 L/min inlet, 1,200 iterations; fieldAverage of U "
                     "and p over iterations 700-1200 (written with cfd_cpap_r41.py case --average-from 700). "
                     "Outlet flows from cut sections; delivery from 600 flux-weighted streamlines per outlet in the "
                     "mean field: the share passing within 1 mm of the print surface inside 10 (or 5) mm of the "
                     "nozzle axis, and the share leaving upward past the hotend (Z > -70 mm). Values at each "
                     "design's own estimated WS7040 operating point with a 1 m hose (flow exponent 1.983).",
           "limitations": "Airflow only: no temperature, heat transfer or printed result. Streamlines in a mean field "
                          "show transport, not residence. The visors, the lip trim and the aim variants (vanes, louver, "
                          "roof ramp) are CFD screening prototypes, not qualified or printed parts. Streamlines start "
                          "at the outlet sections, so air that a trimmed floor releases before them is reported only "
                          "as the nozzle_focus side_spill_lpm flux.",
           "cases": {}}
    for label, (case, text) in CASES.items():
        if (C.results_dir(case) / "outlet_balance_mean.json").exists():
            out["cases"][label] = {"case": case, "description": text, **summary(case)}
            focus = focus_summary(case)
            if focus:
                out["cases"][label]["nozzle_focus"] = focus
            tip = tip_summary(case)
            if tip:
                out["cases"][label]["tip_approach"] = tip
    snapshot = {name: D.coverage(B.load(name, False), A.operating(A.rows_of(name))["lpm"] / 180)
                for name in ("r43userpostV5d_bambu_bed", "r43avgV5d_bambu_bed")}
    out["snapshot_repeatability"] = {
        "note": "The same geometry and settings meshed and solved twice; snappyHexMesh in parallel is not "
                "bit-reproducible. Single iteration-1200 snapshots of the near-print sectors differ by up to "
                "this much, which is why this round uses iteration means.",
        "cases": {n: {"mesh_cells": P.mesh_stats(n)["cells"], "sectors_ms": c["sector_area_mean_speed_ms"],
                      "weakest_to_strongest": c["weakest_to_strongest_sector_mean_ratio"]} for n, c in snapshot.items()},
        "largest_sector_difference_pct": max(
            100 * abs(snapshot["r43avgV5d_bambu_bed"]["sector_area_mean_speed_ms"][k]
                      / snapshot["r43userpostV5d_bambu_bed"]["sector_area_mean_speed_ms"][k] - 1)
            for k in ("right", "front", "left", "rear")),
    }
    if "current_repeat" in out["cases"]:
        a, b = out["cases"]["current"], out["cases"]["current_repeat"]
        out["mean_field_repeatability"] = {
            "sector_difference_pct": {k: 100 * (b["near_print_sectors_ms"][k] / a["near_print_sectors_ms"][k] - 1)
                                      for k in a["near_print_sectors_ms"]},
            "sector_mean_difference_pct": 100 * (b["sector_mean_ms"] / a["sector_mean_ms"] - 1),
            "over_print_r10_difference_pct": 100 * (b["over_print_r10_total_lpm_at_operating_point"]
                                                    / a["over_print_r10_total_lpm_at_operating_point"] - 1),
            "inlet_pressure_difference_pct": 100 * (b["inlet_total_pa_at_180"] / a["inlet_total_pa_at_180"] - 1),
        }
    scorecard = C.CFD.parent / "printability_swept" / "scorecard" / "scorecard.json"
    if scorecard.exists():
        out["printability"] = json.loads(scorecard.read_text())
    mounted, withdrawal = (C.CFD.parent / f"aim_hotend_{k}.json" for k in ("mounted_gaps", "withdrawal"))
    if mounted.exists() and withdrawal.exists():
        out["hotend_clearance_limits"] = {
            "rule": "Hard limit: no P22 material nearer any Bambu hotend part than the released P22, mounted and "
                    "along the 60 mm -Y withdrawal (1 mm steps), and nothing added inside the hotend slot "
                    "(|X| < 10.2 mm). Exact BREP distances.",
            "mounted_gap_mm": json.loads(mounted.read_text()),
            "withdrawal_min_mm": json.loads(withdrawal.read_text())}
    out["source_sha256"] = {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in (
        "cfd_outlet_balance_r43.py", "render_outlet_balance_r43.py", "report_outlet_balance_r43.py",
        "render_scene_symmetry_r43.py", "cfd_nozzle_focus_r43.py", "cfd_tip_approach_r43.py", "cfd_cpap_r41.py",
        "cfd_swept_refine_r43.py", "cfd/run_case.sh")}
    (ROOT / "verification_outlet_balance_r43.json").write_text(json.dumps(out, indent=2) + "\n")
    for label, row in out["cases"].items():
        print(label, json.dumps({k: row[k] for k in ("inlet_total_pa_at_180", "sector_mean_ms", "weakest_to_strongest",
                                                     "over_print_r10_total_lpm_at_operating_point",
                                                     "rising_total_lpm_at_operating_point")}),
              json.dumps(row["operating_point_1m_hose"]))
    print(json.dumps({k: v for k, v in out.items() if k in ("snapshot_repeatability", "mean_field_repeatability")},
                     indent=1))


if __name__ == "__main__":
    main()
