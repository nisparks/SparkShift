import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import trimesh
from audit_c28_mechanical_r43 import NAMES, OUTPUT, SOURCE, digest

files = {
    "geometry": "verification_c28_mechanical_geometry_r43.json",
    "motion": "verification_c28_mechanical_motion_r43.json",
    "slicing": "verification_c28_mechanical_slicing_r43.json",
    "support_access": "verification_c28_mechanical_support_access_r43.json",
}
data = {k: json.loads((CAD / p).read_text()) for k, p in files.items()}
assert data["geometry"]["status"] == "STATIC_GEOMETRY_EXPORT_AND_SERVICE_PATH_VERIFIED_REVIEW_ONLY"
assert data["motion"]["status"] == "INCREMENTAL_RIGID_TRANSLATION_PATHS_CLEAR"
assert data["slicing"]["status"] == "MATCHED_SLICER_COMPARISON_COMPLETE_NOT_PRINT_QUALIFIED"
assert data["geometry"]["source_sha256"]["r43_c28_mechanical.py"] == digest(CAD / "r43_c28_mechanical.py")
assert data["geometry"]["frozen_scene_manifest_sha256"] == digest(SOURCE / "manifest.json")
manifest_file = OUTPUT / "build_manifest.json"
manifest = json.loads(manifest_file.read_text())
assert data["motion"]["source_build_manifest_sha256"] == digest(manifest_file)
for name, sha in manifest["body_sha256"].items():
    assert digest(OUTPUT / name) == sha
    assert cq.Shape.importBrep(str(OUTPUT / name)).isValid()
for name, sha in data["geometry"]["exports_sha256"].items():
    assert digest(CAD / name) == sha, name
for row in data["geometry"]["head_to_mounted_bambu_mm"].values():
    assert row.get("mm", row.get("greater_than_mm")) >= 3
assert min(data["geometry"]["insert_walls"].values()) > .999
assert min(data["geometry"]["air_changes"][k] for k in (
    "root_pockets_to_remaining_channel_mm", "circular_socket_to_remaining_channel_mm")) >= 1.15
assert data["support_access"]["c28_mechanical_back"]["narrow_rear_passage_samples"] == 0
assert data["support_access"]["c28_mechanical_inlet_face"]["estimated_support_in_passage_mm3"] > 300

print_meshes = {}
for key, height in (("p01", 28.7), ("p21", 47.22), ("p22", 74.67619047619048),
                    ("cartographer", 74.67619047619048)):
    path = CAD / "stl" / f"{NAMES[key]}_PRINT_ORIENTED.stl"
    mesh = trimesh.load_mesh(str(path))
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert abs(mesh.bounds[0, 2]) < 1e-4
    assert abs(mesh.extents[2] - height) < .001
    print_meshes[key] = {"height_mm": float(mesh.extents[2]), "watertight": True,
                         "orientation": data["geometry"]["print_orientations"][key]}

backup = S / "53_C28_Live_Edits_Preserved.f3d"
assert backup.is_file() and backup.stat().st_size > 1000
report = {
    "status": "CHECKED_MECHANICAL_STUDY_DELIVERED_PRINT_OPTIMIZATION_PENDING",
    "evidence_sha256": {name: digest(CAD / name) for name in files.values()},
    "current_generator_sha256": digest(CAD / "r43_c28_mechanical.py"),
    "share_image_sha256": digest(CAD / "images" / "r43_c28_mechanical_review_share.jpg"),
    "renderer_sha256": digest(CAD / "render_c28_mechanical_r43.py"),
    "print_meshes": print_meshes,
    "live_fusion_edits": {
        "document": "53 Bambu C28 - angled mounts and lower retainer",
        "status": "LIVE_EDITS_PRESERVED_NOT_REQUALIFIED",
        "archive": str(backup), "archive_sha256": digest(backup),
        "timeline_at_backup": [
            "Group1", "Group2", "Extrude1", "Extrude2", "Sketch1", "Extrude3", "Sketch2",
            "Extrude4", "Extrude5", "Extrude6", "Fillet1", "DeleteFace1", "DeleteFace2",
            "DeleteFace3", "DeleteFace4", "DeleteFace5", "Extrude7",
        ],
        "decision": "New live edits appeared after import. User was unavailable; preserve them rather than "
                    "overwrite or silently adopt them. The edited document was left active. Fusion's "
                    "Documents.add API explicitly permits only visible new documents, so no additional "
                    "document was created while live editing continued. This archive is a snapshot, not "
                    "a qualification of later edits or a substitute for the checked STEP/STL set.",
    },
    "remaining": [
        "Reconcile the live Fusion edits before adopting a new baseline.",
        "Reduce whole-set support; the mechanical study currently adds 1.7%.",
        "Do not use the assessed inlet-down pose: rear-passage support risk.",
        "Fresh CFD must represent revised P01, P21 and P22, not only P22.",
        "Physical fit, cable service, tightening, sealing and thermal qualification.",
    ],
}
(CAD / "verification_c28_mechanical_delivery_r43.json").write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps({"status": report["status"], "checked_exports": len(data["geometry"]["exports_sha256"]),
                  "motion_paths": len(data["motion"]["paths"]), "print_meshes": print_meshes,
                  "preserved_live_edit_archive": str(backup)}, indent=2))
