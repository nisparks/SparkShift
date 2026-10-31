import json
import os
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
OUT = S / "swept_feed"
sys.path.insert(0, str(CAD))
os.chdir(CAD)
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image
import r43_swept_feed as R

original = cq.Shape.importBrep(str(OUT / "swept_air.brep"))
taller = cq.Shape.importBrep(str(OUT / "roof3" / "swept_air.brep"))
comparison = {
    "original_dedicated_air_volume_mm3": original.Volume(),
    "taller_dedicated_air_volume_mm3": taller.Volume(),
    "original_air_removed_mm3": original.cut(taller).Volume(),
    "sections": [],
    "control": "Roof raised 3 mm; feed floors, outlet position, height, span and direction unchanged.",
}
assert comparison["original_air_removed_mm3"] < 1e-4
for y in (-10, -6, -2, 1, 4.25, 8):
    plane = cq.Face.makePlane(100, 100, basePnt=(0, y, -70), dir=(0, 1, 0))
    comparison["sections"].append({
        "y_mm": y,
        "original_area_mm2": original.intersect(plane).Area(),
        "taller_area_mm2": taller.intersect(plane).Area(),
    })
base = cq.Shape.importBrep(str(S / "cfd" / "p22_r43.brep"))
default = R.p22(base)
frozen = cq.Shape.importBrep(str(OUT / "p22_merge_checked.brep"))
comparison["default_generator_vs_frozen_difference_mm3"] = {
    "generated_only": default.cut(frozen).Volume(),
    "frozen_only": frozen.cut(default).Volume(),
}
assert all(v < 1e-4 for v in comparison["default_generator_vs_frozen_difference_mm3"].values())
report_file = CAD / "verification_swept_feed_roof3_r43.json"
report = json.loads(report_file.read_text())
report["comparison_to_original"] = comparison
report_file.write_text(json.dumps(report, indent=2) + "\n")
(OUT / "roof3" / "qualification.json").write_text(json.dumps(report, indent=2) + "\n")
fig, axes = plt.subplots(2, 1, figsize=(12, 12))
for ax, folder, title in (
    (axes[0], OUT, "Original swept feed: 780 mm3 dedicated air passage"),
    (axes[1], OUT / "roof3", "Roof raised 3 mm: 1,484 mm3; same floor and outlet"),
):
    image = Image.open(folder / "fusion_cutaway.png")
    ax.imshow(image.crop((430, 250, 1160, 640)))
    ax.set_title(title, fontsize=15)
    ax.axis("off")
fig.suptitle("X0 centre cutaways at the same scale; orange = air, green = printed body\n"
             "The side feeds merge into the left edge of the orange section", fontsize=14)
fig.tight_layout()
fig.savefig(CAD / "images" / "r43_swept_feed_area_study.png", dpi=110)
plt.close(fig)
print(json.dumps(comparison, indent=2))
