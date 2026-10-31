import adsk.core, adsk.fusion, json, os

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
STEP_PATH = ROOT + r"\step\37_Probe_Height_And_Datum_Dock_REVIEW.step"
ARCHIVE = ROOT + r"\37_Probe_Height_And_Datum_Dock_REVIEW.f3d"
REPORT = ROOT + r"\verification_probe_height_datum_dock_r37.json"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"

report = json.load(open(REPORT))
EXPECTED = {"P23_Probe_Mount_Raised_Rear_Ears_R37_REVIEW": report["p23"]["volume_mm3"]["r37"],
            "P22_CPAP_Lower_Plenum_Probe_Mounts_R37_REVIEW": report["p22"]["volume_mm3"]["r37"]}

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "37 Probe height and datum dock"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R37 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "37 Probe height and datum dock (native review)"
doc.close(False)
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occ = {o.name.split(":")[0]: o for o in d.rootComponent.allOccurrences}
bodies = sum(o.component.bRepBodies.count for o in d.rootComponent.allOccurrences) + d.rootComponent.bRepBodies.count
volumes = {}
for name, expected in EXPECTED.items():
    found = [o for n, o in occ.items() if n.startswith(name)]
    if len(found) != 1 or found[0].component.bRepBodies.count != 1:
        raise RuntimeError(f"Expected one body for {name}: {[n for n in occ]}")
    volumes[name] = found[0].component.bRepBodies.item(0).getPhysicalProperties(
        adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000
    if abs(volumes[name] - expected) > 0.05:
        raise RuntimeError(f"Native {name} volume {volumes[name]} vs {expected}")
if bodies != 321:
    raise RuntimeError(f"Native review has {bodies} bodies, expected 321")


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
    # From below, front left: raised probe on P23 with its rear ears, Bambu docked, Red Lizard parked at +37.3.
    "below": shot("f37_below.png", (-14.0, 14.0, -22.0), (1.9, 1.0, -7.6), 13.0),
    # Closer, from below and behind: the four P23 screws.
    "p23": shot("f37_p23.png", (-6.0, -14.0, -20.0), (0.0, -0.6, -7.45), 6.0),
}
result = {"document": opened.name, "bodies": bodies, "native_volumes_mm3": volumes,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "images": saved}
