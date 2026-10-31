"""Area-weighted air speed over the print disc round the nozzle, at each design's operating flow (session scratch)."""
import sys, os, json, math
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
import numpy as np
import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import cfd_cpap_r43 as A

CASES = ["r41bm_bambu_bed", "r43_bambu_bed", "r43low_bambu_bed", "r43front_bambu_bed", "r43bell_bambu_bed",
         "r43lowbell_bambu_bed", "r43frontbell_bambu_bed", "r43combo_bambu_bed"]
surf = C.NOZZLE_TIP_Z - C.BED_GAP
rs = np.arange(1.0, 14.01, 0.5)
th = np.linspace(0, 2 * math.pi, 96, endpoint=False)
out = {}
for n in CASES:
    rows = A.rows_of(n)
    r180 = next(r for r in rows if r["lpm"] == 180.0)
    op = A.operating(rows)["lpm"]
    f = op / 180.0
    st = [s for s in P.stages(n) if s["lpm"] == 180.0][0]
    g = P.internal(n, st["end"])
    row = {"op_lpm": round(op, 1), "box_share_pct": r180["nozzle_box_outflow_lpm"]["share_pct"],
           "jet_angle_deg": r180["jets"]["left"]["angle_below_horizontal_deg"]}
    for h in (0.3, 1.0):
        pts = [(r * math.cos(t), C.NOZZLE_Y + r * math.sin(t), surf + h) for r in rs for t in th]
        u, ok = P.probe(g, pts)
        sp = np.linalg.norm(u, axis=1).reshape(len(rs), len(th)) * f
        okr = ok.reshape(len(rs), len(th))
        ring = np.array([sp[i][okr[i]].mean() if okr[i].any() else np.nan for i in range(len(rs))])
        for R in (5.0, 10.0, 14.0):
            m = (rs <= R) & ~np.isnan(ring)
            row[f"mean_h{h}_r{R:g}"] = round(float((ring[m] * rs[m]).sum() / rs[m].sum()), 2)
            row[f"u08_h{h}_r{R:g}"] = round(float(((ring[m] ** 0.8) * rs[m]).sum() / rs[m].sum()), 2)
    out[n] = row
    print(n, json.dumps(row), flush=True)
base = out["r41bm_bambu_bed"]
print("\n% against revision 41 (at each design's blower flow):")
keys = [k for k in base if k.startswith(("mean_", "u08_"))]
print("case".ljust(24), " ".join(k.ljust(13) for k in keys))
for n, row in out.items():
    print(n.ljust(24), " ".join(f"{100 * (row[k] / base[k] - 1):+6.1f}".ljust(13) for k in keys), "| op", row["op_lpm"],
          "| angle", row["jet_angle_deg"], "| share", row["box_share_pct"])
json.dump(out, open(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\disc_metrics.json", "w"), indent=1)
