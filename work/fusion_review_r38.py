import adsk.core, adsk.fusion, json, os

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
STEP_PATH = ROOT + r"\step\38_Front_Print_Limit_REVIEW.step"
ARCHIVE = ROOT + r"\38_Front_Print_Limit_REVIEW.f3d"
REPORT = ROOT + r"\verification_front_print_limit_r38.json"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
EXPECTED_BODIES = 389

report = json.load(open(REPORT))
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "38 Front print limit"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R38 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "38 Front print limit (native review)"
doc.close(False)
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occs = list(d.rootComponent.allOccurrences)
bodies = sum(o.component.bRepBodies.count for o in occs) + d.rootComponent.bRepBodies.count
if bodies != EXPECTED_BODIES:
    raise RuntimeError(f"Native review has {bodies} bodies, expected {EXPECTED_BODIES}")


def find(name):
    found = [o for o in occs if o.name.split(":")[0] == name]
    if len(found) != 1:
        raise RuntimeError(f"{name}: {len(found)} occurrences")
    return found[0]


def gap_mm(a, b):
    best = None
    for i in range(a.bRepBodies.count):
        for j in range(b.bRepBodies.count):
            v = app.measureManager.measureMinimumDistance(a.bRepBodies.item(i), b.bRepBodies.item(j)).value
            best = v if best is None else min(best, v)
    return round(best * 10.0, 3)


gaps = {
    "pins_to_T5_Bambu_body": gap_mm(find("Active_Bambu_coupling_pins_and_magnets"), find("T5_Bambu_body")),
    "P18_to_T5_Bambu_body": gap_mm(find("Active_Bambu_P18"), find("T5_Bambu_body")),
    "pins_to_T4_RedLizard_body": gap_mm(find("Active_Bambu_coupling_pins_and_magnets"), find("T4_RedLizard_body")),
    "body_to_T5_Bambu_body": gap_mm(find("Active_Bambu_body"), find("T5_Bambu_body")),
}
expected = report["by_active_tool"]["Bambu"]["clearance_at_print_limit"]["mm"]
if abs(gaps["pins_to_T5_Bambu_body"] - expected) > 0.02:
    raise RuntimeError(f"Native pin gap {gaps['pins_to_T5_Bambu_body']} vs audit {expected}")


def shot(file, eye, target, up, extent):
    cam = app.activeViewport.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.isFitView = False
    cam.isSmoothTransition = False
    cam.eye = adsk.core.Point3D.create(*eye)
    cam.target = adsk.core.Point3D.create(*target)
    cam.upVector = adsk.core.Vector3D.create(*up)
    cam.viewExtents = extent
    app.activeViewport.camera = cam
    app.activeViewport.refresh()
    adsk.doEvents()
    return app.activeViewport.saveAsImageFile(os.path.join(IMAGES, file), 1600, 1000)


saved = {
    # Above, rear right: the active Bambu on the new limit beside the parked T4-T6, limit strips on bed A.
    "iso": shot("f38_iso.png", (34.0, 22.0, 30.0), (19.0, 3.5, 4.0), (0, 0, 1), 16.0),
    # Straight down on the same area.
    "top": shot("f38_top.png", (19.0, 4.0, 60.0), (19.0, 4.0, 0.0), (0, 1, 0), 15.0),
}
result = {"document": opened.name, "bodies": bodies, "native_gaps_mm": gaps, "audit_gap_mm": expected,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "images": saved}
