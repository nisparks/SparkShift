import adsk.core, adsk.fusion, json, os

ARCHIVE = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26\36_Ten_Tool_Rack_Requalified_REVIEW.f3d"
REPORT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26\verification_rack_requalification_r36.json"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"

chute = json.load(open(REPORT))["chute"]
doc = app.activeDocument
if doc.name not in ("Untitled", "36 Ten-tool rack - requalified"):
    raise RuntimeError(f"Unexpected active document {doc.name}")
doc.name = "36 Ten-tool rack - requalified"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "36 Ten-tool rack - requalified (native review)"
doc.close(False)
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occ = {o.name.split(":")[0]: o for o in d.rootComponent.allOccurrences}
new_chutes, old_chutes, bodies = 0, 0, 0
for name, o in occ.items():
    for b in o.component.bRepBodies:
        bodies += 1
        if name.startswith("D"):
            v = b.getPhysicalProperties(adsk.fusion.CalculationAccuracy.HighCalculationAccuracy).volume * 1000
            new_chutes += abs(v - chute["r36_volume_mm3"]) < 0.05
            old_chutes += abs(v - chute["released_volume_mm3"]) < 0.05
if bodies != 748 or new_chutes != 10 or old_chutes:
    raise RuntimeError(f"Native check failed: bodies {bodies}, R36 chutes {new_chutes}, R21 chutes {old_chutes}")


def shot(file, eye, target, extent):
    cam = app.activeViewport.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.isFitView = False
    cam.isSmoothTransition = False
    cam.eye = adsk.core.Point3D.create(*eye)
    cam.target = adsk.core.Point3D.create(*target)
    cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
    cam.viewExtents = extent
    app.activeViewport.camera = cam
    app.activeViewport.refresh()
    adsk.doEvents()
    return app.activeViewport.saveAsImageFile(os.path.join(IMAGES, file), 1600, 1000)


saved = {
    # Whole rack from the front, above: ten tools on the rigid crossbar, carriage at T0.
    "overview": shot("f36_overview.png", (-15.0, -70.0, 55.0), (17.5, 0.0, 17.0), 46.0),
    # Bays 3 and 4 from the front, below: the chamfered chute arms facing each other.
    "chutes": shot("f36_chutes.png", (13.75, -40.0, -5.0), (13.75, 1.0, 11.6), 9.0),
}
result = {"document": opened.name, "bodies": bodies, "r36_chutes": new_chutes, "r21_chutes": old_chutes,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "images": saved}
