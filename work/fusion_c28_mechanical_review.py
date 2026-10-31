import adsk.core
import adsk.fusion
import hashlib
import json
import os

CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
S = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
TITLE = "53 Bambu C28 - angled mounts and lower retainer"
ARCHIVE = os.path.join(S, "53_C28_Mechanical_Review.f3d")
report_path = os.path.join(CAD, "verification_c28_mechanical_geometry_r43.json")
with open(report_path) as file:
    report = json.load(file)
if report["status"] != "STATIC_GEOMETRY_EXPORT_AND_SERVICE_PATH_VERIFIED_REVIEW_ONLY":
    raise RuntimeError("Mechanical geometry/export qualification is incomplete")
existing = [document for document in app.documents if document.name == TITLE]
if existing and not globals().get("resume_created_review", False):
    raise RuntimeError("This review is already open; do not overwrite or create a duplicate")
if len(existing) > 1:
    raise RuntimeError("Ambiguous review document")
before = [document.name for document in app.documents]
if existing:
    doc = existing[0]
    doc.activate()
else:
    doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    doc.name = TITLE
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
sources = [
    os.path.join(CAD, "step", "53_C28_Bambu_Angled_Mounts_And_Retainer_REVIEW.step"),
    os.path.join(S, "swept_feed", "optC28_mechanical", "mechanical_inspection_sections.step"),
]
if not existing:
    for path in sources:
        if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(path), d.rootComponent):
            raise RuntimeError("Review STEP import failed: " + path)
volumes = {}
native_geometry_check = None
for key, name in (
    ("p01", "P01_C28_Bambu_45deg_Mounts_REVIEW"),
    ("p21", "P21_C28_Bambu_Forked_Retainer_REVIEW"),
    ("p22", "P22_C28_Bambu_45deg_Mounts_Retainer_Beacon_REVIEW"),
):
    matches = [o for o in d.rootComponent.allOccurrences if o.name.split(":")[0] == name]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {name}; found {len(matches)}")
    native = sum(body.getPhysicalProperties(
        adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume
        for body in matches[0].component.bRepBodies) * 1000
    expected = report["parts"][key]["volume_mm3"]
    if key == "p22":
        proof_path = os.path.join(S, "swept_feed", "optC28_mechanical", "native_p22_geometry_check.json")
        with open(proof_path) as file:
            native_geometry_check = json.load(file)
        for field, path in (
            ("source_brep_sha256", os.path.join(S, "swept_feed", "optC28_mechanical", "p22.brep")),
            ("source_step_sha256", sources[0]),
            ("native_export_sha256", os.path.join(S, "swept_feed", "optC28_mechanical", "fusion_p22_roundtrip.step")),
        ):
            if hashlib.sha256(open(path, "rb").read()).hexdigest() != native_geometry_check[field]:
                raise RuntimeError("Native geometry evidence is stale: " + field)
        if abs(native - native_geometry_check["native_api_volume_mm3"]) > 1e-5:
            raise RuntimeError("Native P22 changed after its geometry export")
        if not all(row["both_differences_valid"] and
                   max(abs(row["source_only_mm3"]), abs(row["native_only_mm3"])) < 1e-4
                   for row in native_geometry_check["checks"]):
            raise RuntimeError("Native P22 does not match the source geometry")
    elif abs(native - expected) > .05:
        raise RuntimeError(f"Native {key} volume {native} differs from CAD {expected}")
    volumes[key] = {"native_mm3": native, "cad_mm3": expected}

vp = app.activeViewport


def camera(target_mm, direction, extent):
    target = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    length = sum(v * v for v in direction) ** .5
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.target = target
        cam.eye = adsk.core.Point3D.create(*(a + 40 * b / length for a, b in
                                           zip((target.x, target.y, target.z), direction)))
        cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
        cam.viewExtents = extent
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()


views = [
    ("1 Bambu mechanical assembly - review, not print release", (0, -7, -58), (1, -.9, .35), 7.5),
    ("2 Section - underside M3 and cable bend", (120, 89.6, -57), (1, 0, 0), 3.8),
    ("3 Section - matched 45 degree faces", (258, 215.8, -55.9), (1, 0, 0), 2.8),
    ("4 Isolated fork and cable - insert before assembly", (-160, -29.8, -54.7), (0, 1, -.1), 3.3),
]
for name, target, direction, extent in views:
    camera(target, direction, extent)
    d.namedViews.add(vp.camera, name)
camera(*views[1][1:])
image = os.path.join(S, "swept_feed", "optC28_mechanical", "fusion_retainer_section.png")
if not vp.saveAsImageFile(image, 1500, 1000):
    raise RuntimeError("Native section snapshot failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native Fusion archive export failed")
after = [document.name for document in app.documents]
if any(name not in after for name in before):
    raise RuntimeError("An existing document disappeared during review creation")
result = {
    "document": doc.name, "archive": ARCHIVE, "archive_bytes": os.path.getsize(ARCHIVE),
    "native_volumes": volumes, "p22_native_geometry_check": native_geometry_check,
    "named_views": [row[0] for row in views],
    "earlier_documents_preserved": True,
    "geometry_report_sha256": hashlib.sha256(open(report_path, "rb").read()).hexdigest(),
    "source_sha256": {path: hashlib.sha256(open(path, "rb").read()).hexdigest() for path in sources},
    "scope": "Primary Bambu/Beacon mechanical assembly plus non-printing inspection sections. "
             "Separate Cartographer-seat STEP also exists. Earlier Fusion documents were not edited or closed.",
}
with open(os.path.join(CAD, "verification_c28_mechanical_fusion_r43.json"), "w") as file:
    json.dump(result, file, indent=2)
