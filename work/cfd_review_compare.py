"""Revision 43 before and after the review (r43v1_* vs r43_*): pressure, blower flow, the plenum's loss (where the
rib is), the jets' split and turbulence, and the air over the print."""
import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import os  # noqa: E402

os.chdir(CAD)
import cfd_cpap_r41 as C  # noqa: E402
import cfd_cpap_r43 as R  # noqa: E402

out = {}
for tool in ("bambu", "redlizard", "bambu_bed"):
    row = {}
    for tag in ("r43v1", "r43"):
        name = f"{tag}_{tool}"
        p = C.results_dir(name) / "analysis_r43.json"
        if not p.exists():
            continue
        rows = json.loads(p.read_text())
        a = next(r for r in rows if r["lpm"] == 180.0)
        op = R.operating(rows)
        lb = {s["section"]: s["total_pressure_pa"] for s in a["loss_breakdown"]}
        v = {"iteration": a["iteration"], "pressure_180_pa": round(a["inlet_total_pa"]), "blower_lpm": op["lpm"],
             "plenum_loss_pa (P21 trunk to side channels)": lb["trunk (P21)"] - lb["side channels after the elbow"],
             "side_channels_pa": lb["side channels after the elbow"] - lb["side channels beside the hotend"],
             "jets_pa (beside hotend to exits)": lb["side channels beside the hotend"] - lb["jet exits"],
             "split_left_pct": a["split_left_pct"],
             "jets": {k: {kk: a["jets"][k][kk] for kk in ("lpm", "area_mm2", "mean_ms", "max_ms", "turbulence_intensity",
                                                         "angle_below_horizontal_deg")} for k in ("left", "right")},
             "up_share_pct": a["nozzle_box_outflow_lpm"]["share_pct"]["up"]}
        if a.get("over_print"):
            f = op["lpm"] / 180.0
            v["over_print_disc_at_op_ms"] = {k: round(val * f, 2) for k, val in a["over_print"]["disc_mean_speed_0.3mm_over_ms"].items()}
            v["over_print_speed_at_op_ms"] = {k: round(val * f, 1) for k, val in a["over_print"]["speed_0.3mm_over_ms"].items()}
        row[tag] = v
    out[tool] = row
print(json.dumps(out, indent=1))
