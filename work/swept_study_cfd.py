import argparse
import copy
import gc
import hashlib
import json
import math
import os
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
OUT = S / "swept_feed"
sys.path.insert(0, str(CAD))
os.chdir(CAD)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import cfd_cpap_r43 as A
import render_cfd_cpap_r41 as F
import r43_swept_feed as R

CASES = [
    ("r43_bambu_bed", "Released R43 / Bambu (30-core reference)"),
    ("r43centre_bambu_bed", "Previous box-plenum centre feed / Bambu"),
    ("r43swept2_bambu_bed", "Swept-island feed / Bambu"),
    ("r43swept2_redlizard_bed", "Swept-island feed / Red Lizard"),
]
parser = argparse.ArgumentParser()
parser.add_argument("--include-roof", action="store_true")
parser.add_argument("--include-opt", action="store_true")
parser.add_argument("--include-fine", action="store_true")
args = parser.parse_args()
INCLUDE_ROOF = args.include_roof
if INCLUDE_ROOF:
    CASES.extend([
        ("r43swept3_bambu_bed", "Taller swept feed (+3 mm roof) / Bambu"),
        ("r43swept3_redlizard_bed", "Taller swept feed (+3 mm roof) / Red Lizard"),
    ])
if args.include_opt:
    CASES.extend([
        ("r43optA_bambu_bed", "Taller feed, 0.9 mm slot, 32 deg / Bambu"),
        ("r43optB38_bambu_bed", "Taller feed, 0.9 mm slot, 38 deg / Bambu"),
    ])
if args.include_fine:
    CASES.extend([
        ("r43optAfine_bambu_bed", "Candidate A, finer outlet / Bambu"),
        ("r43optAfine_redlizard_bed", "Candidate A, finer outlet / Red Lizard"),
    ])


def coverage(grid, factor):
    """Airflow diagnostics only: no temperature field or heat-transfer ranking."""
    radii = np.arange(1.0, 5.01, .25)
    angles = np.linspace(0, 2 * math.pi, 144, endpoint=False)
    radius, theta = np.meshgrid(radii, angles, indexing="ij")
    points = np.column_stack((radius.ravel() * np.cos(theta.ravel()),
                              C.NOZZLE_Y + radius.ravel() * np.sin(theta.ravel()),
                              np.full(radius.size, -78.78)))
    u, ok = P.probe(grid, points)
    speed = np.linalg.norm(u, axis=1) * factor
    weights = radius.ravel()
    sectors = {}
    for label, centre in (("right", 0), ("front", 90), ("left", 180), ("rear", 270)):
        mask = ok & ((np.degrees(theta.ravel()) - centre + 45) % 360 < 90)
        if not mask.any():
            raise RuntimeError(f"No valid samples in near-print sector {label}")
        sectors[label] = float(np.average(speed[mask], weights=weights[mask]))
    return {
        "annulus_mm": [1, 5], "height_above_bed_mm": .3,
        "valid_samples": int(ok.sum()), "total_samples": len(ok),
        "sector_area_mean_speed_ms": sectors,
        "weakest_to_strongest_sector_mean_ratio": min(sectors.values()) / max(sectors.values()),
        "area_fraction_below_10_ms": float(
            np.sum(weights[ok] * (speed[ok] < 10)) / weights[ok].sum()),
        "note": "10 m/s is a descriptive common threshold, not a validated cooling requirement. "
                "A stagnation region can transfer heat well despite low sampled speed.",
    }

def section_flux(grid, y, windows):
    sliced = P.plane_slice(grid, "y", y)
    parts = []
    for x0, x1, z0, z1 in windows:
        sl = P.clip_box(sliced, (x0, x1, y - .1, y + .1, z0, z1))
        if not sl.GetNumberOfCells():
            raise RuntimeError(f"No CFD cells in internal section Y{y}: {x0,x1,z0,z1}")
        parts.append(P.flux_weighted(sl, (0, 1, 0)))
    flow = sum(row["lpm"] for row in parts)
    if flow <= 0:
        raise RuntimeError(f"Non-forward net branch flow at Y{y}")
    return {
        "flow_lpm": flow,
        "total_pressure_pa": sum(row["pt"] * row["lpm"] for row in parts) / flow,
        "area_mm2": sum(row["area_mm2"] for row in parts),
        "parts": parts,
    }

def branch_metrics(grid, roof_raise=0.0, mouth_height=1.3, angle_deg=32.0):
    upstream = section_flux(grid, -12, [(12.8, 21.1, -69.0, -58.5), (-21.1, -12.8, -69.0, -58.5)])
    feeds = section_flux(grid, 1, [(3.65, 10.95, -71.15, -67.65 + roof_raise),
                                  (-10.95, -3.65, -71.15, -67.65 + roof_raise)])
    trunk = section_flux(grid, 4.25, [(-9.2, 9.2, -72.8, -70.0 + roof_raise)])
    points = []
    for x in np.linspace(-8.5, 8.5, 35):
        for height in np.linspace(-mouth_height * .35, mouth_height * .35, 5):
            direction, up = R.outlet_axes(angle_deg)
            point = R.mouth(float(x)) + up * height + direction * .35
            points.append(point.toTuple())
    u, ok = P.probe(grid, points)
    xyz = np.asarray(points)
    side = ok & (np.abs(xyz[:, 0]) > 3)
    result = {
        "upstream_main_channels_y-12": upstream,
        "dedicated_feeds_y1": feeds,
        "merged_trunk_y4.25": trunk,
        "rear_share_at_180_pct": 100 * trunk["flow_lpm"] / 180,
        "branch_flux_mismatch_pct": 100 * (trunk["flow_lpm"] / feeds["flow_lpm"] - 1),
        "upstream_to_trunk_total_pressure_drop_pa": upstream["total_pressure_pa"] - trunk["total_pressure_pa"],
        "mouth_velocity_probe_valid": int(ok.sum()),
        "mouth_velocity_probe_count": len(points),
    }
    if side.any():
        result["side_mouth_samples_flowing_inward_fraction"] = float(
            (u[side, 0] * xyz[side, 0] < 0).mean())
    result["mouth_velocity_samples"] = [
        {"point_mm": list(pt), "u_ms": list(map(float, vel)), "valid": bool(valid)}
        for pt, vel, valid in zip(points, u, ok)
    ]
    return result

rows = {}
fig, axes = plt.subplots(3, len(CASES), figsize=(6.25 * len(CASES), 16))
for col, (name, label) in enumerate(CASES):
    mesh = P.mesh_stats(name)
    if not mesh["mesh_ok"]:
        raise RuntimeError(f"Refusing results from failed checkMesh: {name}")
    stage = F.stage(name, 180)
    g = P.internal(name, stage["end"])
    rs = A.rows_of(name)
    row = next(r for r in rs if r["lpm"] == 180)
    factor = A.operating(rs)["lpm"] / 180
    result = {
        "mesh": mesh,
        "pressure_at_180_pa": row["inlet_total_pa"],
        "inlet_total_relative_spread_last_100": row["inlet_total_relative_spread_last_100"],
        "estimated_blower_lpm_1m_hose": A.operating(rs)["lpm"],
        "near_print_mean_speed_ms_at_estimated_blower": {
            k: v * factor for k, v in row["over_print"]["disc_mean_speed_0.3mm_over_ms"].items()
        },
        "upward_outflow_share_pct": row["nozzle_box_outflow_lpm"]["share_pct"]["up"],
        "side_jet_flow_at_180_lpm": row["jets"]["left"]["lpm"] + row["jets"]["right"]["lpm"],
        "near_print_net_radial_outflow_within_1mm_lpm_at_estimated_blower": {
            k: v * factor for k, v in row["over_print"]["outflow_within_1mm_lpm"].items()
        },
        "coverage_at_estimated_blower": coverage(g, factor),
    }
    history = P.inlet_history(name)
    last = history[(history[:, 0] > stage["end"] - 500) & (history[:, 0] <= stage["end"])]
    if len(last) < 20 or last[-1, 0] < stage["end"] - 5:
        raise RuntimeError(f"Incomplete final pressure history: {name}")
    result["pressure_history_last_500"] = {
        "samples": len(last),
        "relative_std": float(last[:, 2].std() / abs(last[:, 2].mean())),
        "relative_peak_to_peak": float(np.ptp(last[:, 2]) / abs(last[:, 2].mean())),
        "relative_change_first_to_last_100_mean": float(
            last[last[:, 0] > stage["end"] - 100, 2].mean()
            / last[last[:, 0] <= stage["end"] - 400, 2].mean() - 1),
    }
    if name.startswith(("r43swept2", "r43swept3", "r43opt")):
        result["branch"] = branch_metrics(
            g, 0.0 if name.startswith("r43swept2") else 3.0,
            .9 if name.startswith("r43opt") else 1.3,
            38.0 if name.startswith("r43optB38") else 32.0)
        result["branch"]["side_jets_plus_rear_flow_lpm"] = (
            result["side_jet_flow_at_180_lpm"] + result["branch"]["merged_trunk_y4.25"]["flow_lpm"])
        result["branch"]["side_jets_plus_rear_vs_inlet_pct"] = (
            100 * (result["branch"]["side_jets_plus_rear_flow_lpm"] / 180 - 1))
        result["additional_refinement"] = json.loads(
            (C.results_dir(name) / "stages.json").read_text()).get("additional_refinement")
    rows[name] = result
    F.section(axes[0, col], g, "x", 0, (-12, 34, -80, -60), title=label + "\nCentre section X0", vmax=65)
    axes[0, col].plot([22.7], [-78.88], "w+", ms=10)
    F.section(axes[1, col], g, "z", -76, (-22, 22, -2, 35),
              title="At nozzle-jet height Z-76", vmax=65)
    F.section(axes[2, col], g, "z", -78.78, (-16, 16, 7, 37),
              title="0.3 mm above the bed", vmax=60, arrows=False)
    F.mark(axes[2, col], "xy")
    print(name, json.dumps({k: v for k, v in result.items() if k != "branch"}), flush=True)
    if "branch" in result:
        print("branch", name, json.dumps({k: v for k, v in result["branch"].items()
                                        if k != "mouth_velocity_samples"}), flush=True)
    del g
    gc.collect()

reference = rows["r43_bambu_bed"]
for name in rows:
    if name == "r43_bambu_bed" or "bambu" not in name:
        continue
    row = rows[name]
    row["vs_released_r43_bambu_pct"] = {
        k: 100 * (v / reference["near_print_mean_speed_ms_at_estimated_blower"][k] - 1)
        for k, v in row["near_print_mean_speed_ms_at_estimated_blower"].items()
    }
fig.suptitle("Air speed at 180 L/min; R43 reference on 30 cores, studies on 46, with recorded local hotend refinement.\n"
             "Red Lizard is a different tool, not a direct Bambu performance comparison. Grey = solid.", fontsize=14)
fig.tight_layout()
fig.savefig(OUT / "swept_cfd_comparison.png", dpi=90)
plt.close(fig)
report = {
    "method": "OpenFOAM v2512 steady k-omega SST, 180 L/min, 1200 iterations; bed 0.2 mm below nozzle. "
              "Near-print speeds scaled to the estimated WS7040 operating point with 1m hose and exponent 1.983. "
              "Internal section flows use existing cell-slice integration. Velocity probes are point samples. "
              "No thermal prediction or formal mesh-independence claim.",
    "probe_configuration": "Beacon at its existing datum in both CFD scenes; Cartographer checked geometrically only.",
    "postprocessing_limitations": "VTK warns about non-manifold triangulations in some exported polyhedron "
                                 "contours. All accepted OpenFOAM meshes pass checkMesh, but section fluxes "
                                 "are approximate: feed/trunk and inlet/outlet closure errors are recorded. "
                                 "Small differences require further numerical qualification.",
    "reference_selection": "r43_bambu_bed passes Mesh OK and uses the same released P22 BREP, on 30 cores. "
                           "r43np46_bambu_bed is excluded: two highly skew faces, max 8.689, failed checkMesh. "
                           "Taller-versus-original swept pairs use identical 46-core settings and refinement. "
                           "Outlet candidates A/B use identical additional feed-junction refinement to one another.",
    "frozen_p22_brep_sha256": hashlib.sha256((OUT / "p22_merge_checked.brep").read_bytes()).hexdigest(),
    "cases": rows,
}
if INCLUDE_ROOF:
    report["roof3_p22_brep_sha256"] = hashlib.sha256(
        (OUT / "roof3" / "p22_swept_beacon.brep").read_bytes()).hexdigest()
    report["taller_vs_original_swept"] = {}
    for tool in ("bambu", "redlizard"):
        before = rows[f"r43swept2_{tool}_bed"]
        after = rows[f"r43swept3_{tool}_bed"]
        report["taller_vs_original_swept"][tool] = {
            "pressure_at_180_pct": 100 * (after["pressure_at_180_pa"] / before["pressure_at_180_pa"] - 1),
            "blower_flow_pct": 100 * (after["estimated_blower_lpm_1m_hose"]
                                     / before["estimated_blower_lpm_1m_hose"] - 1),
            "rear_branch_flow_at_180_pct": 100 * (
                after["branch"]["merged_trunk_y4.25"]["flow_lpm"]
                / before["branch"]["merged_trunk_y4.25"]["flow_lpm"] - 1),
            "near_print_speed_at_estimated_blower_pct": {
                k: 100 * (v / before["near_print_mean_speed_ms_at_estimated_blower"][k] - 1)
                for k, v in after["near_print_mean_speed_ms_at_estimated_blower"].items()
            },
        }
if args.include_opt:
    report["outlet_optimization"] = {
        "candidate_for_further_validation": "r43optA_bambu_bed",
        "not_a_release_or_thermal_ranking": True,
        "reason": "At 32 degrees the 0.9 mm slot restores much of the near-print radial flow lost by "
                  "the taller 1.3 mm outlet and has more balanced quadrant mean speeds than 38 degrees. "
                  "It does not beat released R43 on the within-5-mm mean-speed proxy.",
        "geometry": {"roof_raise_mm": 3, "mouth_height_mm": .9, "angle_deg": 32},
        "limits": "Bambu airflow optimization only; both probe geometries checked, but Cartographer not "
                  "simulated. No heat-transfer solution, physical print, hot-warp tolerance qualification "
                  "or formal mesh independence. A 0.9 mm slot on the current grid needs local resolution "
                  "checking before strong performance claims. VTK contour warnings and up to roughly 3% "
                  "branch-section mismatch further limit small differences.",
    }
if args.include_fine:
    before = rows["r43optA_bambu_bed"]
    after = rows["r43optAfine_bambu_bed"]
    report["candidate_a_local_resolution_check"] = {
        "coarse": "r43optA_bambu_bed", "fine": "r43optAfine_bambu_bed",
        "nominal_outlet_cell_mm": [.25, .125],
        "pressure_at_180_pct": 100 * (after["pressure_at_180_pa"] / before["pressure_at_180_pa"] - 1),
        "rear_branch_at_180_pct": 100 * (
            after["branch"]["merged_trunk_y4.25"]["flow_lpm"]
            / before["branch"]["merged_trunk_y4.25"]["flow_lpm"] - 1),
        "near_print_mean_speed_at_estimated_blower_pct": {
            k: 100 * (v / before["near_print_mean_speed_ms_at_estimated_blower"][k] - 1)
            for k, v in after["near_print_mean_speed_ms_at_estimated_blower"].items()
        },
        "near_print_net_radial_outflow_at_estimated_blower_pct": {
            k: 100 * (v / before["near_print_net_radial_outflow_within_1mm_lpm_at_estimated_blower"][k] - 1)
            for k, v in after["near_print_net_radial_outflow_within_1mm_lpm_at_estimated_blower"].items()
            if abs(before["near_print_net_radial_outflow_within_1mm_lpm_at_estimated_blower"][k]) > 1
        },
        "limitation": "Two local resolutions only; no global mesh-independence or thermal-convergence claim. "
                      "Signed net radial flow near zero should be compared in absolute units, not percentages.",
    }
(OUT / "swept_cfd.json").write_text(json.dumps(report, indent=2) + "\n")
summary = copy.deepcopy(report)
for row in summary["cases"].values():
    if "branch" in row:
        del row["branch"]["mouth_velocity_samples"]
(CAD / "verification_swept_feed_cfd_r43.json").write_text(json.dumps(summary, indent=2) + "\n")
print("saved comparison", flush=True)
