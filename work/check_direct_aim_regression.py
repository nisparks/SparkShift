import hashlib
import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
sys.path.insert(0, str(CAD))
import cadquery as cq
import numpy as np
import trimesh
import r43_swept_feed as R

out = S / "swept_feed" / "optC28_conformal"
old = S / "swept_feed" / "optC28_direct"
air = cq.Shape.importBrep(str(out / "swept_air.brep"))
old_air = cq.Shape.importBrep(str(old / "swept_air.brep"))
air_change = {"new_only_mm3": air.cut(old_air).Volume(),
              "old_only_mm3": old_air.cut(air).Volume()}
assert max(air_change.values()) < 1e-5, air_change

def mesh(s):
    v, f = s.tessellate(.005, .05)
    return trimesh.Trimesh(np.array([p.toTuple() for p in v]), np.array(f), process=True)

def inside(s, p):
    return any(solid.isInside(cq.Vector(*p), 1e-6) for solid in s.Solids())

keep = R.mouth_keep(28)
previous = cq.Shape.importBrep(str(old / "p22_swept_beacon.brep"))
beacon = cq.Shape.importBrep(str(out / "p22_swept_beacon.brep"))
points = json.loads((old / "checks.json").read_text())["sampled_wall_check"]["failed_points_mm"]
genuine = [p for p in points if inside(keep, p) and not inside(previous, p)]
assert all(inside(beacon, p) for p in genuine)

carto = cq.Shape.importBrep(str(out / "p22_swept_cartographer.brep"))
m, ma = mesh(carto), mesh(air)
centres = ma.triangles_center
samples = centres + ma.face_normals * .75
ends = np.array([R.mouth(float(np.clip(p[0], -10, 10))).toTuple() for p in centres])
outlet = np.einsum("ij,j->i", centres - ends, R.outlet_axes(28)[0].toTuple()) > -.02
eligible = (~outlet & mesh(keep).contains(samples)
            & ~mesh(R.RJ.duct_air()).contains(samples) & ~ma.contains(samples))
suspects = samples[eligible][~m.contains(samples[eligible])]
bad = [p.tolist() for p in suspects if inside(keep, p) and not inside(carto, p)]
assert not bad, bad

bores = {}
for label, part in (("beacon", beacon), ("cartographer", carto)):
    before = cq.Shape.importBrep(str(S / "swept_feed" / "optA_direct" / f"p22_swept_{label}.brep"))
    regions = [cq.Solid.makeBox(7, 7, 6, cq.Vector(x - 3.5, -.3 - 3.5, -75))
               for x in (-15.8, 15.8)]
    difference = sum(part.cut(before).intersect(region).Volume()
                     + before.cut(part).intersect(region).Volume() for region in regions)
    assert difference < 1e-4, (label, difference)
    bores[label] = difference

report = {
    "airway_change_from_uncorrected_28_mm3": air_change,
    "old_report_stored_points_checked": len(points),
    "old_report_stored_points_confirmed_missing_wall": len(genuine),
    "outer_material_change_from_original_28_mm3": {
        "removed": previous.cut(beacon).Volume(), "added": beacon.cut(previous).Volume()},
    "cartographer_wall_screen": {"samples": int(eligible.sum()), "normal_offset_mm": .75,
                                "triangulated_suspects": len(suspects), "exact_failures": bad},
    "live_probe_bore_region_difference_from_cleaned_32_mm3": bores,
    "inputs_sha256": {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in (
        CAD / "r43_swept_feed.py", out / "p22_swept_beacon.brep",
        out / "p22_swept_cartographer.brep", out / "swept_air.brep")},
    "note": "Stored old screening failures do not establish an actual missing CAD wall. "
            "The exact-CAD fallback corrects tessellation classification, not the wall requirement. "
            "Not slicing, continuous wall-thickness or thermal qualification.",
}
(CAD / "verification_direct_aim_regression_r43.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report, indent=2))
