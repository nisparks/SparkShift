import argparse
import gc
import json
import os
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
sys.path.insert(0, str(CAD))
os.chdir(CAD)
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cfd_cpap_r41_post as P
import render_cfd_cpap_r41 as F

parser = argparse.ArgumentParser()
parser.add_argument("--fine", action="store_true")
FINE = parser.parse_args().fine
cases = [
    ("r43_bambu_bed", "Released R43"),
    ("r43swept2_bambu_bed", "Original swept feed"),
    ("r43swept3_bambu_bed", "Taller feed / 1.3 mm slot"),
    ("r43optA_bambu_bed", "Candidate A / 0.9 mm, 32 deg"),
    ("r43optB38_bambu_bed", "Candidate B / 0.9 mm, 38 deg"),
]
if FINE:
    cases = [
        ("r43_bambu_bed", "Released R43 / Bambu"),
        ("r43optA_bambu_bed", "A / Bambu / previous outlet mesh"),
        ("r43optAfine_bambu_bed", "A / Bambu / finer outlet mesh"),
        ("r43optAfine_redlizard_bed", "A / Red Lizard / finer outlet mesh"),
    ]
report = json.loads((CAD / "verification_swept_feed_cfd_r43.json").read_text())
fig, axes = plt.subplots(3, len(cases), figsize=(22, 12))
for col, (name, label) in enumerate(cases):
    row = report["cases"][name]
    assert row["mesh"]["mesh_ok"]
    grid = P.internal(name, 1200)
    F.section(axes[0, col], grid, "x", 0, (-5, 35, -80, -64),
              title=f"{label}\n{row['pressure_at_180_pa']:.0f} Pa at 180 L/min", vmax=65)
    F.section(axes[1, col], grid, "z", -76, (-20, 20, 5, 35),
              title="Jet-height plane Z-76", vmax=65)
    F.section(axes[2, col], grid, "z", -78.78, (-14, 14, 9, 37),
              title="0.3 mm above bed", vmax=60, arrows=False)
    F.mark(axes[2, col], "xy")
    del grid
    gc.collect()
fig.suptitle(("Candidate A: local resolution and cross-tool check" if FINE else "Bambu outlet optimization")
             + ": field maps at the same 180 L/min and iteration 1200\n"
             "Airflow only, not heat transfer. Grey = solid; all meshes pass checkMesh.", fontsize=14)
fig.tight_layout()
fig.savefig(CAD / "images" / ("r43_candidate_a_resolution.png" if FINE
                             else "r43_swept_outlet_optimization.png"), dpi=110)
plt.close(fig)

fig, axes = plt.subplots(1, 3, figsize=(17, 5))
labels = ["R43", "Swept", "Taller", "A: 32 deg", "B: 38 deg"]
if FINE:
    cases = cases[:3]
    labels = ["R43 / Bambu", "A / previous mesh", "A / finer outlet"]
for sector in ("front", "rear", "left", "right"):
    values = [report["cases"][name]["coverage_at_estimated_blower"]["sector_area_mean_speed_ms"][sector]
              for name, _ in cases]
    axes[0].plot(labels, values, "o-", label=sector)
axes[0].set_ylabel("Mean speed, m/s")
axes[0].set_title("Directional coverage, 1-5 mm annulus")
axes[0].legend()
axes[1].bar(labels, [report["cases"][name][
    "near_print_net_radial_outflow_within_1mm_lpm_at_estimated_blower"]["r8_mm"] for name, _ in cases])
axes[1].set_ylabel("Net radial flow, L/min")
axes[1].set_title("Along print through radius 8 mm, first 1 mm")
axes[2].bar(labels, [report["cases"][name]["estimated_blower_lpm_1m_hose"] for name, _ in cases])
axes[2].set_ylabel("Estimated total blower flow, L/min")
axes[2].set_title("WS7040 operating point with 1 m hose")
for ax in axes:
    ax.tick_params(axis="x", rotation=20)
    ax.grid(axis="y", alpha=.2)
fig.suptitle("All diagnostics scaled to each design's estimated blower flow; no single metric is a cooling score")
fig.tight_layout()
fig.savefig(CAD / "images" / ("r43_candidate_a_resolution_metrics.png" if FINE
                             else "r43_swept_flow_coverage.png"), dpi=110)
plt.close(fig)
print("saved optimization field and coverage plots")
