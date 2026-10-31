import adsk.core
import adsk.fusion
import hashlib
import json
import os

CAD = os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
S = os.path.dirname(os.path.abspath(__file__))
TITLE = "54 Bambu C28 - user post retainer (REVIEW)"
USER_DOC = "53 Bambu C28 - angled mounts and lower retainer"
OUT = os.path.join(S, "swept_feed", "optC28_user_retainer")
ARCHIVE = os.path.join(OUT, "54_C28_User_Post_Retainer_Review.f3d")
SOURCE = os.path.join(CAD, "step", "54_C28_Bambu_User_Post_Retainer_REVIEW.step")
report_path = os.path.join(CAD, "verification_c28_user_retainer_geometry_r43.json")
with open(report_path) as file:
    report = json.load(file)
if report["status"] != "STATIC_GEOMETRY_SEAL_EXPORT_AND_SERVICE_PATH_VERIFIED_REVIEW_ONLY":
    raise RuntimeError("User-post geometry/export qualification is incomplete")
if hashlib.sha256(open(SOURCE, "rb").read()).hexdigest() != report["exports_sha256"][os.path.join("step", os.path.basename(SOURCE))]:
    raise RuntimeError("Assembly STEP differs from the audited export")
if any(document.name == TITLE for document in app.documents):
    raise RuntimeError("This review is already open; do not overwrite or create a duplicate")


def user_doc_state():
    docs = [document for document in app.documents if document.name == USER_DOC]
    if len(docs) != 1:
        return None
    design_ = adsk.fusion.Design.cast(docs[0].products.itemByProductType("DesignProductType"))
    p21 = [b for c in design_.allComponents for b in c.bRepBodies if c.name.startswith("P21_")]
    return {"timeline": design_.timeline.count, "modified": docs[0].isModified,
            "p21_volume_mm3": [round(b.physicalProperties.volume * 1000, 4) for b in p21]}


before_docs = [document.name for document in app.documents]
before_user = user_doc_state()
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = TITLE
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(SOURCE), d.rootComponent):
    raise RuntimeError("Review STEP import failed")
volumes = {}
for key, name in (("p01", "P01_C28_Bambu_45deg_Mounts_REVIEW"), ("p21", "P21_C28_Bambu_User_Post_Sealed_REVIEW"),
                  ("p22", "P22_C28_Bambu_User_Post_Receiver_Beacon_REVIEW")):
    matches = [o for o in d.rootComponent.allOccurrences if o.name.split(":")[0] == name]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one {name}; found {len(matches)}")
    native = sum(body.getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume
                 for body in matches[0].component.bRepBodies) * 1000
    expected = report["parts"][key]["volume_mm3"]
    relative = abs(native - expected) / expected
    if relative > 1e-4:
        raise RuntimeError(f"Native {key} volume {native} differs from CAD {expected}")
    volumes[key] = {"native_mm3": native, "cad_mm3": expected, "relative_difference": relative,
                    "bodies": matches[0].component.bRepBodies.count}

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
    ("1 Bambu user-post assembly - review, not print release", (0, -7, -58), (1, -.9, .35), 7.5),
    ("2 Post and receiver from the rear-left", (0, -31, -58), (.75, -1, -.2), 3.6),
    ("3 Underside M3 retainer", (0, -28.2, -70), (.6, -.4, -1), 3.0),
    ("4 Angled P01/P22 mount", (18, 15.8, -55.9), (1, 0, 0), 2.8),
]
for name, target, direction, extent in views:
    camera(target, direction, extent)
    d.namedViews.add(vp.camera, name)
camera(*views[1][1:])
image = os.path.join(OUT, "fusion_user_post_view.png")
if not vp.saveAsImageFile(image, 1500, 1000):
    raise RuntimeError("Native snapshot failed")
camera(*views[0][1:])
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native Fusion archive export failed")
after_docs = [document.name for document in app.documents]
after_user = user_doc_state()
if any(name not in after_docs for name in before_docs):
    raise RuntimeError("An existing document disappeared during review creation")
if before_user != after_user:
    raise RuntimeError(f"User document 53 changed: {before_user} -> {after_user}")
result = {
    "document": doc.name, "archive": os.path.relpath(ARCHIVE, S), "archive_bytes": os.path.getsize(ARCHIVE),
    "archive_sha256": hashlib.sha256(open(ARCHIVE, "rb").read()).hexdigest(),
    "native_volumes": volumes, "named_views": [row[0] for row in views],
    "user_document_53_unchanged": after_user, "earlier_documents_preserved": True,
    "geometry_report_sha256": hashlib.sha256(open(report_path, "rb").read()).hexdigest(),
    "source_step_sha256": hashlib.sha256(open(SOURCE, "rb").read()).hexdigest(),
    "scope": "Bambu/Beacon user-post assembly with hardware, cable and Beacon reference. The Cartographer-seat "
             "P22 is a separate STEP. Document 53 and earlier documents were not edited or closed.",
}
with open(os.path.join(CAD, "verification_c28_user_retainer_fusion_r43.json"), "w") as file:
    json.dump(result, file, indent=2)
