import sys, os, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
import cfd_cpap_r41 as C
import cfd_cpap_r43 as A
names = sys.argv[1:] or ["r41bm_bambu_bed", "r43long_bambu_bed", "r43rear_bambu_bed", "r43low_bambu_bed", "r43bell_bambu_bed", "r43combo_bambu_bed", "r43_bambu_bed"]
base = None
for n in names:
    if not (C.results_dir(n) / "analysis_r43.json").exists():
        continue
    rows = A.rows_of(n)
    r = next(x for x in rows if x["lpm"] == 180.0)
    op = A.operating(rows)
    f = op["lpm"] / 180.0
    po = r.get("over_print")
    row = {"p180": round(r["inlet_total_pa"]), "op": round(op["lpm"], 1), "it": r["iteration"],
           "jets_ms": r["jets"]["left"]["mean_ms"], "jets_mm2": r["jets"]["left"].get("area_mm2")}
    if po:
        row["out_r8"] = round(po["outflow_within_1mm_lpm"]["r8_mm"] * f, 1)
        row["sp"] = {k: round(v * f, 1) for k, v in po["speed_0.3mm_over_ms"].items()}
    if base is None:
        base = row
    else:
        row["dp_pct"] = round(100 * (row["p180"] / base["p180"] - 1), 1)
        row["op_pct"] = round(100 * (row["op"] / base["op"] - 1), 1)
        if po and "out_r8" in base:
            row["out_pct"] = round(100 * (row["out_r8"] / base["out_r8"] - 1), 1)
            row["sp_pct"] = {k: round(100 * (row["sp"][k] / base["sp"][k] - 1), 1) for k in row["sp"]}
    print(n, json.dumps(row))
