"""Side by side, Bambu with a print 0.2 mm under the tip, 180 L/min: revision 41, revision 43's first version, the
review's full-length round, and the proposed run-out. Across the nozzle, across the jets' front end, and just over the
print; then the near-nozzle metrics against revision 41 at each design's own blower flow."""
import json
import os
import sys

CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, CAD)
os.chdir(CAD)
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

import cfd_cpap_r41 as C  # noqa: E402
import cfd_cpap_r41_post as P  # noqa: E402
import render_cfd_cpap_r41 as F  # noqa: E402

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\cfd_review_visuals.png"
CASES = [("r41bm_bambu_bed", "Revision 41 (printed)"),
         ("r43v1_bambu_bed", "R43 first version: round stops\nsquare at Y26.2 (the notches)"),
         ("r43_bambu_bed", "R43 review: full r 2.4 round\nto the front wall"),
         ("r43revrunout_bambu_bed", "R43 review: round runs out\nY24.6-27.3 (proposed)")]
Z_PRINT = C.NOZZLE_TIP_Z - 0.2 + 0.3

fig = plt.figure(figsize=(26, 25))
gs = fig.add_gridspec(4, 4, height_ratios=[1.0, 1.0, 1.15, 0.8])
for col, (name, label) in enumerate(CASES):
    s = F.stage(name, 180.0)
    g = P.internal(name, s["end"])
    ax = fig.add_subplot(gs[0, col])
    F.section(ax, g, "y", C.NOZZLE_Y, (-24, 24, -80, -64), title=f"{label}\nacross the nozzle (Y{C.NOZZLE_Y})")
    F.mark(ax, "xz")
    ax = fig.add_subplot(gs[1, col])
    F.section(ax, g, "y", 26.6, (5, 19, -80, -67), title="right jet's front end (Y26.6): side channel at right")
    ax = fig.add_subplot(gs[2, col])
    F.section(ax, g, "z", Z_PRINT, (-16, 16, 8, 37), vmax=60.0, arrows=False,
              title="0.3 mm over the print, from above (front at top)")
    F.mark(ax, "xy")
    del g

rep = json.load(open("verification_cfd_cpap_r43.json"))["design_search_vs_r41"]["cases"]
ax = fig.add_subplot(gs[3, :])
metrics = [("blower_flow_pct", "blower flow"), ("pressure_at_180_pct", "duct pressure at 180 L/min"),
           ("air_over_print_within_5mm_pct", "air over the print\nwithin 5 mm"),
           ("air_over_print_within_10mm_pct", "within 10 mm"), ("air_over_print_within_14mm_pct", "within 14 mm")]
x = np.arange(len(metrics))
colours = {"r43v1_bambu_bed": "tab:gray", "r43_bambu_bed": "tab:orange", "r43revrunout_bambu_bed": "tab:green"}
for k, (name, label) in enumerate(CASES[1:]):
    vals = [rep[name][m] for m, _ in metrics]
    bars = ax.bar(x + (k - 1) * 0.26, vals, 0.26, color=colours[name], label=label.replace("\n", " "))
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:+.1f}", (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                    xytext=(0, 4 if v >= 0 else -14), ha="center", fontsize=10)
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels([m[1] for m in metrics], fontsize=11)
ax.set_ylabel("% against revision 41", fontsize=11)
ax.set_title("Against revision 41, each at its own blower flow (1 m hose); lower pressure = less restrictive", fontsize=12)
ax.grid(True, axis="y", alpha=0.3)
ax.legend(fontsize=10, loc="lower left")
fig.suptitle("P22 jets, Bambu, print surface 0.2 mm under the tip: air speed at 180 L/min (grey: solid; +: nozzle)",
             fontsize=15)
fig.tight_layout()
fig.savefig(OUT, dpi=72)
print("saved", OUT)
