"""Rear-jet variant vs revision 43 (session scratch): Bambu, print surface 0.2 mm under the tip, 180 L/min, all four
cases on 46 cores where available. Side section through the rear jet and nozzle (X0), across the nozzle (Y22.7),
and 0.3 mm over the print; the rear jet's own flow; metrics against revision 41 at each design's own blower flow."""
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
import cfd_cpap_r43 as A  # noqa: E402
import render_cfd_cpap_r41 as F  # noqa: E402

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\rear_jet"
CASES = [("r41bm_bambu_bed", "Revision 41 (printed)"),
         ("r43np46_bambu_bed", "Revision 43 (committed final)"),
         ("r43rearjet_bambu_bed", "Rear-jet variant\n(narrow openings into the side channels)"),
         ("r43rearjetb_bambu_bed", "Rear-jet variant\n(wide openings into the side channels)")]
REAR = (-6.2, 6.2, 16.0, 17.0, -77.1, -75.2)     # the rear jet's opening, a little in front of its face


def rear_flow(g):
    """L/min through the plane Y16.6 inside the rear jet's opening, in +Y (towards the nozzle)."""
    sl = P.clip_box(P.plane_slice(g, "y", 16.6), (REAR[0], REAR[1], 16.5, 16.7, REAR[4], REAR[5]))
    if sl.GetNumberOfCells() == 0:
        return 0.0
    _, _, area = P.triangles(sl)
    u = P.cell_array(sl, "U")
    return float((u[:, 1] * area).sum()) * 1e-6 * 60000


base = A.rows_of("r41bm_bambu_bed")
b180 = next(r for r in base if r["lpm"] == 180.0)
fb = A.operating(base)["lpm"] / 180.0
rows, avail = {}, []
for name, label in CASES:
    if not (C.results_dir(name) / "analysis_r43.json").exists():
        continue
    avail.append((name, label))
    rs = A.rows_of(name)
    a = next(r for r in rs if r["lpm"] == 180.0)
    op = A.operating(rs)["lpm"]
    fa = op / 180.0
    pa, pb = a["over_print"], b180["over_print"]
    rows[name] = {
        "pressure_180_pa": round(a["inlet_total_pa"]), "blower_lpm": round(op, 1),
        "pressure_pct": round(100 * (a["inlet_total_pa"] / b180["inlet_total_pa"] - 1), 1),
        "blower_pct": round(100 * (fa / fb - 1), 1),
        **{f"within_{r[1:-3]}mm_pct": round(100 * (pa["disc_mean_speed_0.3mm_over_ms"][r] * fa
                                                   / (pb["disc_mean_speed_0.3mm_over_ms"][r] * fb) - 1), 1)
           for r in ("r5_mm", "r10_mm", "r14_mm")},
        "speed_over_print_ms": {k: round(v * fa, 1) for k, v in pa["speed_0.3mm_over_ms"].items()},
        "up_pct": a["nozzle_box_outflow_lpm"]["share_pct"]["up"],
        "side_jets_lpm": round(a["jets"]["left"]["lpm"] + a["jets"]["right"]["lpm"], 1)}

fig = plt.figure(figsize=(6.5 * len(avail), 25))
gs = fig.add_gridspec(4, len(avail), height_ratios=[1.0, 1.0, 1.15, 0.8])
for col, (name, label) in enumerate(avail):
    s = F.stage(name, 180.0)
    g = P.internal(name, s["end"])
    rf = rear_flow(g) if "rear" in name else 0.0
    rows[name]["rear_jet_lpm_at_180"] = round(rf, 1)
    ax = fig.add_subplot(gs[0, col])
    F.section(ax, g, "x", 0.0, (6, 34, -80, -64), title=f"{label}\nalong the slot's centre (X0); nozzle +, probe left")
    ax.plot([C.NOZZLE_Y], [C.NOZZLE_TIP_Z], "w+", ms=10, mew=2)
    ax = fig.add_subplot(gs[1, col])
    F.section(ax, g, "y", C.NOZZLE_Y, (-24, 24, -80, -64), title="across the nozzle (Y22.7)")
    F.mark(ax, "xz")
    ax = fig.add_subplot(gs[2, col])
    F.section(ax, g, "z", C.NOZZLE_TIP_Z + 0.1, (-16, 16, 8, 37), vmax=60.0, arrows=False,
              title="0.3 mm over the print, from above (front at the top)")
    F.mark(ax, "xy")
    del g
ax = fig.add_subplot(gs[3, :])
metrics = [("blower_pct", "blower flow"), ("pressure_pct", "duct pressure at 180 L/min"),
           ("within_5mm_pct", "air over the print\nwithin 5 mm"), ("within_10mm_pct", "within 10 mm"),
           ("within_14mm_pct", "within 14 mm")]
x = np.arange(len(metrics))
cols = {"r43np46_bambu_bed": "tab:green", "r43rearjet_bambu_bed": "tab:purple", "r43rearjetb_bambu_bed": "tab:red"}
shown = [n for n, _ in avail if n in cols]
for k, n in enumerate(shown):
    vals = [rows[n][m] for m, _ in metrics]
    w = 0.8 / len(shown)
    bars = ax.bar(x + (k - (len(shown) - 1) / 2) * w, vals, w, color=cols[n],
                  label=dict(avail)[n].replace("\n", " "))
    for b, v in zip(bars, vals):
        ax.annotate(f"{v:+.1f}", (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                    xytext=(0, 4 if v >= 0 else -14), ha="center", fontsize=10)
ax.axhline(0, color="k", lw=0.8)
ax.set_xticks(x)
ax.set_xticklabels([m[1] for m in metrics], fontsize=11)
ax.set_ylabel("against revision 41 (%)")
ax.set_title("Against revision 41, each at its own blower flow (1 m hose)", fontsize=12)
ax.grid(True, axis="y", alpha=0.3)
ax.legend(fontsize=10, loc="lower left")
fig.suptitle("Rear jet: Bambu, print surface 0.2 mm under the tip, air speed at 180 L/min (grey: solid)", fontsize=15)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "rear_jet_cfd.png"), dpi=66)
json.dump(rows, open(os.path.join(OUT, "rear_jet_cfd.json"), "w"), indent=1)
for n, r in rows.items():
    print(n, json.dumps(r))
