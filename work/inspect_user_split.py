import json
from pathlib import Path

import cadquery as cq

ARTIFACTS = Path(__file__).parent
ROOT = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner")
parts = cq.importers.importStep(str(ARTIFACTS / "user_exact_body1_body2.step")).solids().vals()
parts.sort(key=lambda s: s.BoundingBox().zmax, reverse=True)
original = cq.importers.importStep(
    str(ROOT / r"cad\SparkShift_Accessories_v26\step\P17_Bambu_P2S_tool_carrier_3010.step")
).val()
front, rear = parts
combined = front.fuse(rear)
report = {
    "parts": [
        {"name": name, "valid": p.isValid(), "solids": len(p.Solids()), "volume_mm3": p.Volume()}
        for name, p in zip(("Body1", "Body2"), parts)
    ],
    "overlap_mm3": front.intersect(rear).Volume(),
    "added_vs_original_mm3": combined.cut(original).Volume(),
    "removed_vs_original_mm3": original.cut(combined).Volume(),
    "contact_faces": [],
    "fan_paths": [],
}
for f in front.Faces():
    if f.geomType() != "PLANE":
        continue
    for g in rear.Faces():
        if g.geomType() != "PLANE":
            continue
        shared = f.intersect(g)
        area = sum(face.Area() for face in shared.Faces())
        if area > 0.01:
            report["contact_faces"].append(
                {"area_mm2": area, "center_mm": shared.Center().toTuple()}
            )
for x in (-12, 12):
    for z in (-49.5, -25.5):
        probe = cq.Solid.makeCylinder(1.4, 24.43, cq.Vector(x, 11.5, z), cq.Vector(0, 1, 0))
        report["fan_paths"].append({
            "x_mm": x,
            "z_mm": z,
            "Body1_material_in_hole_path_mm3": front.intersect(probe).Volume(),
            "Body2_material_in_hole_path_mm3": rear.intersect(probe).Volume(),
            "rear_nominal_side_edge_margin_mm": rear.BoundingBox().xmax - abs(x),
        })
report["print_faces"] = []
for name, part, y, sign in (
    ("Body1", front, front.BoundingBox().ymax, 1),
    ("Body2", rear, rear.BoundingBox().ymin, -1),
):
    bed_faces = [
        f for f in part.Faces()
        if f.geomType() == "PLANE"
        and abs(f.Center().y - y) < 1e-5
        and f.normalAt().y * sign > 0.999
    ]
    report["print_faces"].append({
        "body": name,
        "bed_y_mm": y,
        "contact_area_mm2": sum(f.Area() for f in bed_faces),
        "build_height_mm": part.BoundingBox().ylen,
    })
(ARTIFACTS / "user_exact_split_inspection.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
