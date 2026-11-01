"""Collect the printability, outlet-balance and repeatability evidence of the C28 balance round into one report.

Usage: python report_outlet_balance_r43.py
Needs cfd_outlet_balance_r43.py --mean on each averaged case (and on the current snapshot case), and the session
printability scorecard (printability_scorecard.py) in WORK. Writes verification_outlet_balance_r43.json.
"""
import hashlib
import json
from pathlib import Path

import cfd_bead_zones_r43 as Z
import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import cfd_cpap_r43 as A
import cfd_direct_mount_r43 as D
import cfd_outlet_balance_r43 as B
import cfd_provenance_r43 as V
import cfd_nozzle_focus_r43 as F
import cfd_tip_approach_r43 as T
from build_modular_toolhead import ROOT

CASES = {   # label: (case, description)
    "review_rvm_fine": ("r43auditRVMfineV2_bambu_bed",
                         "Audited RVM, fixed P21 input, 0.0625 mm below-tip refinement"),
    "review_rvms_fine": ("r43auditRVMS28fine_bambu_bed",
                          "Audited RVMS control, 2.0 mm rear slot, 0.0625 mm below-tip refinement"),
    "review_rvms40_fine": ("r43auditRVMS40fineV2_bambu_bed",
                            "Audited 2.0 mm, 40-degree rear slot, fixed P21, matched below-tip refinement"),
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
    "side_jet_divider_l30t": ("r43avgV5dL30t_bambu_bed",
                              "Current set, the L30 louver thickened to a printable 0.8 mm divider (screening; within "
                              "the hotend clearance limits)"),
    "side_jet_divider_l40t": ("r43avgV5dL40t_bambu_bed",
                              "Current set, a 0.8 mm divider rising outward at 40 degrees; chokes, 0.48 mm upper-slot "
                              "throat (screening; within the hotend clearance limits)"),
    "side_jet_airfoil_divider_l30a": ("r43avgV5dL30a_bambu_bed",
                                      "Current set, a 30-degree airfoil divider in each side jet: 0.8 mm round leading "
                                      "edge tapering to 0.5 mm at the exit, exit edge at |X| 10.25, Z-75.3 (screening; "
                                      "within the hotend clearance limits)"),
    "side_jet_airfoil_divider_front_l30af": ("r43avgV5dL30aF_bambu_bed",
                                             "Current set, the L30a divider from Y 20.5 forward only (screening; "
                                             "within the hotend clearance limits)"),
    "side_jet_nose_cut_nc28": ("r43avgV5dNC28_bambu_bed",
                               "Current set, the lower part of each side jet's bell-mouth round cut away, leaving a "
                               "sharp 28-degree roof edge at the exit; material removed only (screening; within the "
                               "hotend clearance limits)"),
    "side_jet_nose_cut_divider_ncl": ("r43avgV5dNCL_bambu_bed",
                                      "Current set, the NC28 nose cut plus the L30a divider (screening; within the "
                                      "hotend clearance limits)"),
    "side_jet_secant_roof_sr32": ("r43avgV5dSR32_bambu_bed",
                                  "Current set, each side jet's roof made straight from the exit edge (|X| 10.2, "
                                  "Z-73.6) rising outward at 32 degrees into the bell-mouth round; same exit, material "
                                  "removed only (screening; within the hotend clearance limits)"),
    "side_jet_secant_roof_sr36": ("r43avgV5dSR36_bambu_bed",
                                  "Current set, the same straight roof at 36 degrees (screening; within the hotend "
                                  "clearance limits)"),
    "side_jet_split_roof_spr": ("r43avgV5dSPR_bambu_bed",
                                "Current set, each side jet's roof lowered to Z-75.0 over Y 19.5-23.0 only, the window "
                                "whose air scrubs the nozzle cone, with the SR32 straight roof elsewhere (screening; "
                                "within the hotend clearance limits)"),
    "side_jet_split_roof_deeper_spd": ("r43avgV5dSPD_bambu_bed",
                                       "Current set, the split roof deeper and wider: roof lowered to Z-75.4 over Y "
                                       "20.0-24.0, SR32 straight roof elsewhere (screening; within the hotend "
                                       "clearance limits)"),
    "side_jet_split_roof_ramped_ends_sprt": ("r43avgV5dSPRT_bambu_bed",
                                             "Current set, the SPR split roof with both ends ramped back up to the "
                                             "roof at 45 degrees along the slot face (Y 18.05-19.5 and 23.0-24.45; "
                                             "square further out along the round), straight roof outside them "
                                             "(screening; within the hotend clearance limits)"),
    "side_jet_split_roof_ramped_rear_sprr": ("r43avgV5dSPRR_bambu_bed",
                                             "Current set, the SPR split roof with only its rear end ramped the same "
                                             "way (screening; within the hotend clearance limits)"),
    "side_jet_split_roof_faded_ends_spf": ("r43avgV5dSPF_bambu_bed",
                                           "Current set, the split roof with both ends faded out at 45 degrees along "
                                           "the whole bell-mouth round (Y 18.05-19.5 and 23.0-24.45), straight roof "
                                           "only ahead of it (Y 24.45-27.55) (screening; within the hotend clearance "
                                           "limits; matched slicing adds no support in the jets)"),
    "side_jet_split_roof_faded_rear_spfr": ("r43avgV5dSPFR_bambu_bed",
                                            "Current set, the split roof with its rear end faded out at 45 degrees "
                                            "along the whole round (Y 18.05-19.5), a square front end at Y 23.0 that "
                                            "faces up when printed back face down, and the straight roof ahead of it "
                                            "(Y 23.0-27.55) (screening; within the hotend clearance limits)"),
    "side_jet_split_roof_chamfer_spfc": ("r43avgV5dSPFC_bambu_bed",
                                         "Current set, the SPF split roof plus the floor-lip chamfer of CH (screening; "
                                         "within the hotend clearance limits)"),
    "side_jet_floor_chamfer_ch": ("r43avgV5dCH_bambu_bed",
                                  "Current set, each side jet's floor lip chamfered from |X| 11.2 down to Z-77.45 at "
                                  "the slot face (22 degrees), over Y 22.4-28.6; material removed only (screening; "
                                  "within the hotend clearance limits)"),
    "side_jet_floor_chamfer_long_chx": ("r43avgV5dCHX_bambu_bed",
                                        "Current set, a longer, deeper floor-lip chamfer: from |X| 12.5 down to "
                                        "Z-77.65 at the slot face (15 degrees), 0.2 mm lip left at the edge "
                                        "(screening; within the hotend clearance limits)"),
    "side_jet_nose_cut_chamfer_ncx": ("r43avgV5dNCX_bambu_bed",
                                      "Current set, a 31-degree nose cut on the roof plus the CHX floor chamfer: the "
                                      "whole opening turned down by removing material only (screening; within the "
                                      "hotend clearance limits)"),
    "side_jet_ramp_mild_chamfer_rmc": ("r43avgV5dRMC_bambu_bed",
                                       "Current set, the R45 roof ramp plus a floor-lip chamfer from |X| 11.7 down to "
                                       "Z-77.37 at the slot face (12 degrees) (screening; within the hotend clearance "
                                       "limits)"),
    "side_jet_ramp_gentle_chamfer_rvm": ("r43avgV5dRVM_bambu_bed",
                                         "Current set, the R45 roof ramp plus a gentle floor-lip chamfer from |X| 11.7 "
                                         "down to Z-77.21 at the slot face (6 degrees) (screening; within the hotend "
                                         "clearance limits)"),
    "side_jet_ramp_deep_chamfer_rcx": ("r43avgV5dRCX_bambu_bed",
                                       "Current set, the R45 roof ramp plus the CHX floor chamfer (screening; within "
                                       "the hotend clearance limits)"),
    "side_jet_ramp_lip_trim_rt15": ("r43avgV5dRT15_bambu_bed",
                                    "Current set, the R45 roof ramp plus the floor lip trimmed back 1.5 mm under the "
                                    "jet passage (screening; within the hotend clearance limits)"),
    "side_jet_ramp_lip_trim_rt25": ("r43avgV5dRT25_bambu_bed",
                                    "Current set, the R45 roof ramp plus the floor lip trimmed back 2.5 mm "
                                    "(screening; within the hotend clearance limits)"),
    "side_jet_ramp_front_toe_rft": ("r43avgV5dRFT_bambu_bed",
                                    "Current set, the R45 roof ramp plus each passage's front end wall toed in: the "
                                    "exit ends at Y 25.6 at the slot face, the wall running back to |X| 12.6 at "
                                    "Y 27.65, to turn the front of each jet rearward (screening; within the hotend "
                                    "clearance limits)"),
    "side_jet_ramp_chamfer_toe_rvmt": ("r43avgV5dRVMT_bambu_bed",
                                       "Current set, RVM plus the RFT front-wall toe-in (screening; within the hotend "
                                       "clearance limits)"),
    "rear_slot_2mm_rs20": ("r43avgV5dRS20_bambu_bed",
                           "Current set, the rear centre slot's mouth raised from 0.9 to 2.0 mm by its upper lip only, "
                           "lower lip and probe gaps fixed (as the D11 trial); screening, within the hotend clearance "
                           "limits"),
    "ramp_chamfer_rear_slot_2mm_rvms": ("r43avgV5dRVMS_bambu_bed",
                                        "Current set, RVM plus the 2.0 mm rear slot of RS20 (screening; within the "
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
    report = V.read_balance(case) if mean else json.loads((C.results_dir(case) / "outlet_balance.json").read_text())
    if report.get("analysis_version") != 2:
        raise ValueError(f"{case}: historical outlet analysis must be regenerated before comparison")
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
        "analysis_version": report["analysis_version"],
        "rear_slot": report["rear_slot"],
        "measurement_closure": report["measurement_closure"],
        "mesh_settings": json.loads((C.results_dir(case) / "stages.json").read_text()),
    }


def focus_summary(case):
    """Aim and bead delivery from cfd_nozzle_focus_r43.py, when it has been run on the case."""
    path = C.results_dir(case) / "nozzle_focus.json"
    if not path.exists():
        return None
    f, _ = F.load_cached(case)
    return {"totals_lpm_at_operating_point": f["totals_lpm"], "near_print_ring_mean_ms": f["near_print_ring_mean_ms"],
            "side_spill_lpm": f.get("side_spill_lpm"), "metric_caution": f["metric_caution"],
            "outlets": {k: {kk: v[kk] for kk in ("down_deg", "forward_deg", "aim_pct", "delivery_pct",
                                                  "scrubs_hotend_pct", "opening")} for k, v in f["outlets"].items()}}


def tip_summary(case):
    """Where the air passes the nozzle tip, from cfd_tip_approach_r43.py, when it has been run on the case."""
    path = C.results_dir(case) / "tip_approach.json"
    if not path.exists():
        return None
    t = json.loads(path.read_text())
    V.require_current(t.get("inputs_sha256"), V.focus_inputs(case), f"{case} tip-approach data")
    V.require_current(t.get("analyser_sha256"), V.digest(Path(T.__file__)), f"{case} tip-approach code")
    a = t["closest_approach"]
    return {"cells_lpm_at_operating_point": a["cells"], "cells_by_outlet_lpm": a.get("cells_by_outlet"),
            "mean_passing_point_mm": {k: a[k] for k in ("left", "right", "centre", "all")},
            "aim_line": t.get("aim_line"), "below_tip": t.get("below_tip"),
            "hot_nozzle_cold_bead": t.get("hot_nozzle_cold_bead"),
            "nozzle_surface_band_means_ms": t["nozzle_surface"]["band_means_ms"],
            "print_level_sectors_ms": t["print_level"]["sectors_ms"], "print_level_peak_r5": t["print_level"]["peak_r5"]}


def zones_summary(case):
    """The user's own-side target zones, air arriving on the print and the cone scrub, from cfd_bead_zones_r43.py."""
    path = C.results_dir(case) / "bead_zones.json"
    if not path.exists():
        return None
    z = json.loads(path.read_text())
    V.require_current(z.get("inputs_sha256"), V.focus_inputs(case), f"{case} below-tip target data")
    V.require_current(z.get("analyser_sha256"), V.digest(Path(Z.__file__)), f"{case} target scoring code")
    return {k: v for k, v in z.items() if k not in ("case", "definitions")}


def main():
    out = {"method": "OpenFOAM v2512 simpleFoam, k-omega SST, 180 L/min inlet, 1,200 iterations; fieldAverage of U "
                     "and p over iterations 700-1200 (written with cfd_cpap_r41.py case --average-from 700). "
                     "Outlet flows from complete geometry-specific cut sections; delivery from flux-weighted "
                     "streamlines per outlet (counts recorded in each case) in the "
                     "mean field: the share passing within 1 mm of the print surface inside 10 (or 5) mm of the "
                     "nozzle axis, and the share leaving upward past the hotend (Z > -70 mm). Values at each "
                     "design's own estimated WS7040 operating point with a 1 m hose (flow exponent 1.983).",
           "limitations": "Airflow only: no temperature, heat transfer or printed result. Streamlines in a mean field "
                          "show transport, not residence. The visors, the lip trim and the aim variants (vanes, louver, "
                          "roof ramp) are CFD screening prototypes, not qualified or printed parts. Streamlines start "
                          "at the outlet sections, so air that a trimmed floor releases before them is reported only "
                          "as the nozzle_focus side_spill_lpm flux.",
           "analysis_version": 2,
           "metric_caution": "Historical nozzle_focus totals_lpm/bead uses h<=1 mm above the print, not the "
                             "user's below-tip zone. The 0.3 mm speed plane is above the nozzle tip. "
                             "Compare matched mesh settings; iteration means are not transient CFD.",
           "cases": {}, "excluded_historical_analyses": {}}
    for label, (case, text) in CASES.items():
        if (C.results_dir(case) / "outlet_balance_mean.json").exists():
            saved = json.loads((C.results_dir(case) / "outlet_balance_mean.json").read_text())
            if saved.get("analysis_version") != 2:
                reason = "Legacy fixed rear-slot mask and unverified caches; rerun the analysis chain"
                out["excluded_historical_analyses"][label] = {"case": case, "reason": reason}
                print(f"EXCLUDED {case}: {reason}")
                continue
            out["cases"][label] = {"case": case, "description": text, **summary(case)}
            focus = focus_summary(case)
            if focus:
                out["cases"][label]["nozzle_focus"] = focus
            tip = tip_summary(case)
            if tip:
                out["cases"][label]["tip_approach"] = tip
            zones = zones_summary(case)
            if zones:
                out["cases"][label]["bead_zones"] = zones
    out["bead_zones_definitions"] = Z.__doc__[Z.__doc__.index("Definitions"):].strip()
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
        "render_scene_symmetry_r43.py", "cfd_nozzle_focus_r43.py", "cfd_tip_approach_r43.py", "cfd_bead_zones_r43.py",
        "cfd_cpap_r41.py",
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
