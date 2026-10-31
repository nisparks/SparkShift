"""Compare cleaned direct-mount A with its frozen fine-outlet predecessor.

Run cfd_cpap_r43.py analyse on the accepted cases first, then this script.
Use --aim for the matched-refinement 32/28-degree study. The default Bambu
cleanup comparison also changes local hotend refinement; it cannot isolate cleanup.
Use --feed-cleanup for the matched 28-degree feed-entry remnant removal.
Use --slot-height for the 0.9/1.1 mm slot comparison with the lower lip retained.
Use --printability for the Bambu C28 support-reduction geometry comparison.
Use --user-retainer for the user-post P21, matched P22 receiver and angled P01 against clean C28.
Use --flow-neutral v5b|v5c for a flow-neutral user-post retainer variant against clean C28.
Requires saved session CFD artifacts; not thermal validation or mesh independence.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import cfd_cpap_r43 as A
import render_r43_public_comparison as V
from cfd_swept_refine_r43 import HOTEND_BOXES, FEED_BOXES, OUTLET_BOX
from build_modular_toolhead import ROOT

PAIRS = {
    "Bambu": ("r43optAfine_bambu_bed", "r43directAq_bambu_bed"),
    "RedLizard": ("r43optAfine_redlizard_bed", "r43directA_redlizard_bed"),
}
REPAIR_BOXES = [[5.0, 8.0, 19.0, 22.0, -56.0, -53.0],
                [-8.0, -5.0, 19.0, 22.0, -56.0, -53.0]]
USER_RETAINER_SWAP = {
    "left_out_added": ["P01_Back_case", "R41_P22_P01_M3x8_BUTTON"],
    "removed": ["P01_Back_case_COTS_MR74_Lowered_Bosses_No_Tab_R41_REVIEW",
                "R41_P22_P01_M3x8_BUTTON_0", "R41_P22_P01_M3x8_BUTTON_1"],
    "added": ["C28_P22_P01_M3x4_HEATSET_0", "C28_P22_P01_M3x4_HEATSET_1", "C28_P22_P01_M3x8_BUTTON_0",
              "C28_P22_P01_M3x8_BUTTON_1", "P01_C28_Bambu_45deg_Mounts"],
}
FLOW_NEUTRAL = {   # variant: (case, label)
    "v5b": ("r43userpostV5_bambu_bed", "flow-neutral post, P22 skin under P21 boss"),
    "v5c": ("r43userpostV5c_bambu_bed", "flow-neutral post, skin with 45 deg keel"),
    "v5d": ("r43userpostV5d_bambu_bed", "flow-neutral post, keel, full recess fill"),
}

def coverage(grid, factor):
    radii, angles = np.arange(1, 5.01, .25), np.linspace(0, 2 * np.pi, 144, endpoint=False)
    radius, theta = np.meshgrid(radii, angles, indexing="ij")
    points = np.column_stack((radius.ravel() * np.cos(theta.ravel()),
                              C.NOZZLE_Y + radius.ravel() * np.sin(theta.ravel()),
                              np.full(radius.size, C.NOZZLE_TIP_Z - C.BED_GAP + .3)))
    u, ok = P.probe(grid, points)
    if not ok.any():
        raise ValueError("No valid near-print velocity samples")
    speed, weights = np.linalg.norm(u, axis=1) * factor, radius.ravel()
    sectors = {}
    for label, centre in (("right", 0), ("front", 90), ("left", 180), ("rear", 270)):
        mask = ok & ((np.degrees(theta.ravel()) - centre + 45) % 360 < 90)
        if not mask.any():
            raise ValueError(f"No valid samples in sector {label}")
        sectors[label] = float(np.average(speed[mask], weights=weights[mask]))
    return {
        "annulus_mm": [1, 5], "height_above_bed_mm": .3,
        "valid_samples": int(ok.sum()), "total_samples": len(ok),
        "sector_area_mean_speed_ms": sectors,
        "weakest_to_strongest_sector_mean_ratio": min(sectors.values()) / max(sectors.values()),
        "area_fraction_below_10_ms": float(np.average(speed[ok] < 10, weights=weights[ok])),
        "note": "Descriptive airflow diagnostics only; 10 m/s is not a cooling requirement. "
                "Low sampled speed does not establish low heat transfer at stagnation.",
    }


def validate_pair(tool, old, new, matched, user_retainer=False):
    if old["stage"] != new["stage"] or old["solver_settings"] != new["solver_settings"]:
        raise ValueError(f"{tool}: flow schedules or solver settings differ")
    if user_retainer:
        swap = validate_user_retainer_swap(old, new)
    elif old["left_out"] != new["left_out"] or old["domain_controls"] != new["domain_controls"]:
        raise ValueError(f"{tool}: obstacle exclusions, ambient domain or obstacles differ")
    boxes = [list(b) for b in HOTEND_BOXES[tool] + FEED_BOXES + [OUTLET_BOX]]
    for row in (old, new):
        if row["refinement"]["level"] != 3 or row["refinement"]["nominal_cell_mm"] != .125:
            raise ValueError(f"{tool}: unexpected refinement resolution")
    expected_old = boxes + REPAIR_BOXES if matched else boxes
    expected_new = boxes + REPAIR_BOXES if tool == "Bambu" else boxes
    if old["refinement"]["boxes_mm"] != expected_old or new["refinement"]["boxes_mm"] != expected_new:
        raise ValueError(f"{tool}: unexpected local refinement boxes")
    if user_retainer:
        return {
            "matched_refinement": old["refinement"]["boxes_mm"] == new["refinement"]["boxes_mm"],
            "obstacle_swap": swap,
            "interpretation": "Matched refinement and solver settings. Duct P21/P22 and the angled P01 with its "
                              "screws are replaced together; the difference is the whole mechanical change, "
                              "not thermal validation.",
        }
    return {
        "matched_refinement": old["refinement"]["boxes_mm"] == new["refinement"]["boxes_mm"],
        "interpretation": ("Matched refinement; geometry/aim study, not thermal validation."
                           if matched else "Bambu includes a hotend mesh repair; do not attribute its "
                           "difference to cleanup alone. Red Lizard retains matched refinement."),
    }


def validate_user_retainer_swap(old, new):
    """Only the declared P01/screw replacement may change the ambient obstacles."""
    a, b = old["domain_controls"], new["domain_controls"]
    for key in ("duct", "tool", "bed", "outlet_box_mm", "inlet", "bounds_mm"):
        if a[key] != b[key]:
            raise ValueError(f"User-retainer domain control {key} differs")
    if new["left_out"] != old["left_out"] + USER_RETAINER_SWAP["left_out_added"]:
        raise ValueError("User-retainer left-out parts differ from the declared swap")
    removed = sorted(set(a["obstacles"]) - set(b["obstacles"]))
    added = sorted(set(b["obstacles"]) - set(a["obstacles"]))
    if removed != USER_RETAINER_SWAP["removed"] or added != USER_RETAINER_SWAP["added"]:
        raise ValueError(f"Undeclared obstacle change: removed {removed}, added {added}")
    return {"removed": removed, "added": added}


def metrics(name):
    mesh = P.mesh_stats(name)
    if not mesh["mesh_ok"]:
        raise ValueError(f"{name}: failed mesh cannot enter the comparison")
    stages = P.stages(name)
    if not any(s["end"] == 1200 and s["lpm"] == 180 for s in stages):
        raise ValueError(f"{name}: missing matched stage")
    rows = A.rows_of(name)
    row = next(r for r in rows if r["iteration"] == 1200 and r["lpm"] == 180)
    flow = A.operating(rows)["lpm"]
    factor = flow / 180
    history = P.inlet_history(name)
    last = history[(history[:, 0] > 700) & (history[:, 0] <= 1200)]
    if len(last) < 20 or last[-1, 0] < 1195:
        raise ValueError(f"{name}: incomplete late pressure history")
    metadata = json.loads((C.results_dir(name) / "domain.json").read_text())
    settings = json.loads((C.results_dir(name) / "stages.json").read_text())
    log = (C.results_dir(name) / "log.simpleFoam").read_text()
    if "Time = 1200\n" not in log or "\nEnd\n" not in log:
        raise ValueError(f"{name}: solver did not finish normally at iteration 1200")
    row = {
        "mesh": mesh, "tool": metadata["tool"], "bed": metadata["bed"],
        "left_out": metadata["left_out"],
        "p22_variant": metadata["p22_variant"],
        "domain_controls": {k: metadata[k] for k in (
            "duct", "tool", "bed", "outlet_box_mm", "inlet", "bounds_mm", "obstacles", "left_out")},
        "solver_settings": {k: v for k, v in settings.items() if k != "additional_refinement"},
        "stage": next(s for s in stages if s["end"] == 1200 and s["lpm"] == 180),
        "inlet_pressure_pa_at_180": row["inlet_total_pa"],
        "side_jet_flow_lpm_at_180": row["jets_sum_lpm"],
        "estimated_blower_lpm_1m_hose": flow,
        "mean_speed_ms_at_estimated_blower": {
            k: v * factor for k, v in row["over_print"]["disc_mean_speed_0.3mm_over_ms"].items()
        },
        "net_radial_lpm_at_estimated_blower": {
            k: v * factor for k, v in row["over_print"]["outflow_within_1mm_lpm"].items()
        },
        "pressure_last500_peak_to_peak_pct": float(100 * np.ptp(last[:, 2]) / last[:, 2].mean()),
        "pressure_last500_std_pct": float(100 * last[:, 2].std() / last[:, 2].mean()),
        "pressure_first_to_last100_mean_pct": float(100 * (
            last[last[:, 0] > 1100, 2].mean() / last[last[:, 0] <= 800, 2].mean() - 1)),
        "refinement": settings["additional_refinement"],
    }
    for key in ("p21_variant", "extra_obstacles"):
        if key in metadata:
            row[key] = metadata[key]
    return row


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--aim", action="store_true")
    group.add_argument("--feed-cleanup", action="store_true")
    group.add_argument("--slot-height", action="store_true")
    group.add_argument("--printability", action="store_true")
    group.add_argument("--user-retainer", action="store_true")
    group.add_argument("--flow-neutral", choices=sorted(FLOW_NEUTRAL))
    args = parser.parse_args()
    user_retainer = args.user_retainer or bool(args.flow_neutral)
    pairs = ({"Bambu": ("r43directAq_bambu_bed", "r43directC28q_bambu_bed")}
             if args.aim else PAIRS)
    labels = ("32 deg direct A", "28 deg conformal C") if args.aim else ("before cleanup", "cleaned direct mount")
    stem = "direct_aim" if args.aim else "direct_mount"
    if args.feed_cleanup:
        pairs = {"Bambu": ("r43directC28q_bambu_bed", "r43directC28clean_bambu_bed")}
        labels = ("28 deg / feed-roof remnants", "28 deg / clear feed entries")
        stem = "feed_cleanup"
    if args.slot_height:
        pairs = {"Bambu": ("r43directC28clean_bambu_bed", "r43directD11_bambu_bed")}
        labels = ("C28 / 0.9 mm slot", "D11 / 1.1 mm slot, same lower lip")
        stem = "slot_height"
    if args.printability:
        pairs = {"Bambu": ("r43directC28clean_bambu_bed", "r43printC28_bambu_bed")}
        labels = ("C28 / before printability changes", "C28 / lower-support exterior")
        stem = "printability"
    if args.user_retainer:
        pairs = {"Bambu": ("r43directC28clean_bambu_bed", "r43userpostC28_bambu_bed")}
        labels = ("C28 clean / original P21", "C28 / user post + receiver")
        stem = "user_retainer"
    if args.flow_neutral:
        case, label = FLOW_NEUTRAL[args.flow_neutral]
        pairs = {"Bambu": ("r43directC28clean_bambu_bed", case)}
        labels = ("C28 clean / original P21", f"C28 / {label}")
        stem = f"flow_neutral_retainer_{args.flow_neutral}"
    sections = [("x", 0, (-8, 36, -79.8, -63.8)),
                ("z", -78.78, (-14, 14, 8.7, 36.7))]
    if args.feed_cleanup:
        sections.insert(0, ("x", 16, (-14, 6, -71, -57)))
    if args.user_retainer:
        sections[:0] = [("z", -56, (-24, 24, -48, -14)), ("x", 10, (-48, -14, -72, -44))]
    if args.flow_neutral:
        sections[:0] = [("z", -55, (-24, 24, -48, -14)), ("x", 2.5, (-48, -14, -72, -44))]
    cases, changes = {}, {}
    fig, axes = plt.subplots(len(sections), len(pairs) * 2,
                             figsize=(12 * len(pairs), 6 * len(sections)), squeeze=False)
    for pair_index, (tool, names) in enumerate(pairs.items()):
        for variant_index, name in enumerate(names):
            row = cases[name] = metrics(name)
            if row["tool"] != tool or not row["bed"]:
                raise ValueError(f"{name}: mismatched tool/bed")
            col = pair_index * 2 + variant_index
            grid = P.internal(name, 1200)
            row["coverage_at_estimated_blower"] = coverage(
                grid, row["estimated_blower_lpm_1m_hose"] / 180)
            section = P.plane_slice(grid, "y", 4.25)
            trunk = P.clip_box(section, (-9.2, 9.2, 4.15, 4.35, -72.8, -67))
            if not trunk.GetNumberOfCells():
                raise ValueError(f"{name}: missing rear-branch section")
            row["rear_branch_at_180"] = P.flux_weighted(trunk, (0, 1, 0))
            row["branch_sum_vs_inlet_pct"] = 100 * (
                (row["rear_branch_at_180"]["lpm"] + row["side_jet_flow_lpm_at_180"]) / 180 - 1)
            for index, (axis, at, limits) in enumerate(sections):
                ax = axes[index, col]
                _, _, speed, _, _ = V.sample_map(grid, axis, at, limits)
                ax.set_facecolor("#a9b5c3")
                field = ax.imshow(speed, origin="lower", extent=limits, cmap="turbo",
                                  vmin=0, vmax=65, aspect="equal")
                ax.set_xlabel("Y (mm)" if axis == "x" else "X (mm)")
                ax.set_ylabel("Z (mm)" if axis == "x" else "Y (mm)")
                ax.set_title(f"Section {axis.upper()} = {at:g} mm")
                fig.colorbar(field, ax=ax, shrink=.75, label="Air speed (m/s)", extend="max")
            axes[0, col].set_title(
                f"{tool} / {labels[variant_index]}\n"
                f"{row['inlet_pressure_pa_at_180']:,.0f} Pa at 180 L/min")
            axes[-1, col].plot(0, 22.7, "w+")
            axes[-1, col].set_title("0.3 mm above bed / nozzle marked")
            del grid
            gc.collect()
        old, new = (cases[n] for n in names)
        changes[tool] = {
            "before": names[0], "after": names[1],
            "controls": validate_pair(tool, old, new,
                                      args.aim or args.feed_cleanup or args.slot_height or args.printability
                                      or user_retainer, user_retainer),
            "pressure_pct": 100 * (new["inlet_pressure_pa_at_180"] / old["inlet_pressure_pa_at_180"] - 1),
            "rear_branch_flow_pct": 100 * (
                new["rear_branch_at_180"]["lpm"] / old["rear_branch_at_180"]["lpm"] - 1),
            "mean_speed_pct": {
                k: 100 * (v / old["mean_speed_ms_at_estimated_blower"][k] - 1)
                for k, v in new["mean_speed_ms_at_estimated_blower"].items()
            },
            "net_radial_lpm_change": {
                k: v - old["net_radial_lpm_at_estimated_blower"][k]
                for k, v in new["net_radial_lpm_at_estimated_blower"].items()
            },
            "weakest_sector_speed_pct": 100 * (
                min(new["coverage_at_estimated_blower"]["sector_area_mean_speed_ms"].values())
                / min(old["coverage_at_estimated_blower"]["sector_area_mean_speed_ms"].values()) - 1),
            "uniformity_ratio_change": (
                new["coverage_at_estimated_blower"]["weakest_to_strongest_sector_mean_ratio"]
                - old["coverage_at_estimated_blower"]["weakest_to_strongest_sector_mean_ratio"]),
        }
    title = (f"Flow-neutral user-post retainer {args.flow_neutral}: post, P22 skin and angled mounts vs clean C28"
             if args.flow_neutral else
             "User-post retainer: sealed post, matched receiver and angled mounts vs clean C28" if args.user_retainer else
             "C28 printability changes: same internal airway, matched numerical settings" if args.printability else
             "Rear-slot height: 0.9 vs 1.1 mm, same lower lip and 28-degree aim" if args.slot_height else
             "Feed-entry cleanup: same 28-degree aim and matched refinement" if args.feed_cleanup else
             "Rear-aim study: matched local refinement" if args.aim else
             "Direct-mount cleanup: Bambu also has repaired hotend refinement")
    fig.suptitle(
        title
        + "\n180 L/min, iteration 1200, common 0-65 m/s scale. Point-probed fields, not temperatures.")
    fig.tight_layout()
    fig.savefig(ROOT / "images" / f"r43_{stem}_cfd.png", dpi=150)
    plt.close(fig)
    report = {
        "method": "OpenFOAM v2512, steady k-omega SST; 180 L/min; saved iteration 1200. "
                  "Pressure averages the final 100 iterations. Near-print diagnostics scale to "
                  "estimated WS7040 operation with 1m hose, pressure exponent 1.983.",
        "limitations": "Residual oscillations remain; no mesh independence, temperature field, "
                       "deposited bead or physical cooling test. VTK contour warnings affect "
                       "approximate section integrals. Maps use regular point probes.",
        "cases": cases, "comparison_by_tool": changes,
        "released_r43_unchanged": True,
        "p22_geometry_sha256": {
            name: hashlib.sha256(Path(row["p22_variant"]).read_bytes()).hexdigest()
            for name, row in cases.items()
        },
        **({"p21_geometry_sha256": {
            name: hashlib.sha256(Path(row["p21_variant"]).read_bytes()).hexdigest()
            for name, row in cases.items() if "p21_variant" in row},
            "extra_obstacle_sha256": {
            name: {k: hashlib.sha256(Path(v).read_bytes()).hexdigest() for k, v in row["extra_obstacles"].items()}
            for name, row in cases.items() if "extra_obstacles" in row}} if user_retainer else {}),
        "comparison_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "inputs_sha256": {
            name: {
                file: hashlib.sha256((C.results_dir(name) / file).read_bytes()).hexdigest()
                for file in ("domain.json", "stages.json", "log.checkMesh", "log.simpleFoam",
                             "analysis_r43.json")
            } for names in pairs.values() for name in names
        },
    }
    (ROOT / f"verification_{stem}_cfd_r43.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(changes, indent=2))


if __name__ == "__main__":
    main()
