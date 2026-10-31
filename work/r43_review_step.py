"""Regenerate only build_cpap_outlet_r43's review STEP (left-half cut-aways) and update its row in the report."""
import sys, os, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
import build_cpap_outlet_r43 as Bv
from build_bambu_clean_r29 import sha
from build_fan_mounts_r33 import export_assembly
from build_modular_toolhead import ROOT
parts = Bv.build_parts()
items = Bv.review_items(parts)
path = export_assembly(Bv.R.NAMES["review"], items, sum(len(s.Solids()) for s, _, _ in items))
rep = json.loads((ROOT / Bv.REPORT).read_text())
rel = str(path.relative_to(ROOT))
for e in rep["exports"]:
    if e["file"] == rel:
        e["sha256"], e["mb"] = sha(path), round(path.stat().st_size / 1e6, 1)
        print("updated", e)
(ROOT / Bv.REPORT).write_text(json.dumps(rep, indent=2, default=str) + "\n")
