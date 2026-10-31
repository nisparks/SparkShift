import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))

import cadquery as cq
from audit_c28_mechanical_r43 import OUTPUT, digest

source_file = OUTPUT / "p22.brep"
native_file = OUTPUT / "fusion_p22_roundtrip.step"
source = cq.Shape.importBrep(str(source_file))
native = cq.importers.importStep(str(native_file)).val()
assert source.isValid() and native.isValid()
assert len(source.Solids()) == len(native.Solids()) == 1
rows = []
for tolerance in (1e-5, .001):
    a = source.copy().cut(native.copy(), tol=tolerance)
    b = native.copy().cut(source.copy(), tol=tolerance)
    row = {"coincidence_tolerance_mm": tolerance, "both_differences_valid": a.isValid() and b.isValid(),
           "source_only_mm3": a.Volume(), "native_only_mm3": b.Volume()}
    print(row, flush=True)
    assert row["both_differences_valid"] and max(abs(a.Volume()), abs(b.Volume())) < 1e-4
    rows.append(row)
report = {
    "source_brep_sha256": digest(source_file),
    "source_step_sha256": digest(CAD / "step" / "53_C28_Bambu_Angled_Mounts_And_Retainer_REVIEW.step"),
    "native_export_sha256": digest(native_file),
    "source_default_volume_mm3": source.Volume(),
    "native_api_volume_mm3": 17789.826954211767,
    "native_roundtrip_default_volume_mm3": native.Volume(),
    "source_faces": len(source.Faces()), "native_faces": len(native.Faces()),
    "checks": rows,
    "conclusion": "The native STEP and source have zero valid Boolean difference at the listed tolerances. "
                  "Their default volume-integrator values are not interchangeable. The native import merges "
                  "faces; source trimmed-surface mass integration is tolerance-sensitive. Geometry agreement, "
                  "not a relaxed volume-only threshold, qualifies this native review.",
}
(OUTPUT / "native_p22_geometry_check.json").write_text(json.dumps(report, indent=2) + "\n")
