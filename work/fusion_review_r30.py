import adsk.core, adsk.fusion

STEP_PATH = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\30_Bambu_Compact_Fusion_Review.step"
ARCHIVE = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\30_Bambu_Compact_Review.f3d"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect"
EXPECTED_MM3 = 14320.946795668957
HIDDEN = ("R29_Print_compare", "Dock_reference", "Carriage_Core_reference", "CPAP_Probe_EBB42_Mounts_reference")

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "30 Bambu - Compact fan side"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R30 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "30 Bambu - Compact fan side (native review)"
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occ = {o.name.split(":")[0]: o for o in d.rootComponent.allOccurrences}
prints = list(occ["R30_Bambu_Print"].component.bRepBodies)
if len(prints) != 1:
    raise RuntimeError("Expected one R30 printed body")
vol = prints[0].getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000
if abs(vol - EXPECTED_MM3) > 0.01:
    raise RuntimeError(f"Native R30 volume mismatch: {vol}")


def set_visible(name, on):
    # Toggle through the opposite state so the viewport receives a real change event.
    occ[name].isLightBulbOn = not on
    occ[name].isLightBulbOn = on


def shot(file, eye, target, extent):
    cam = app.activeViewport.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.isFitView = False
    cam.eye = adsk.core.Point3D.create(*eye)
    cam.target = adsk.core.Point3D.create(*target)
    cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
    cam.viewExtents = extent
    app.activeViewport.camera = cam
    app.activeViewport.refresh()
    adsk.doEvents()
    return app.activeViewport.saveAsImageFile(IMAGES + "\\" + file, 1400, 1050)


for name in occ:
    if name != "30 Bambu compact review":
        set_visible(name, name not in HIDDEN)
saved = {
    "fan_side": shot("f30_fan_side.png", (30, 3.2, -1.8), (0.9, 2.5, -2.6), 5.5),
    "below": shot("f30_below.png", (-25, -9, -12), (0.0, 2.5, -2.8), 5.0),
    "rear_user_view": shot("f30_rear.png", (0.4, -30, -2.6), (0.4, 2.5, -2.6), 3.2),
}
result = {"document": opened.name, "native_print_volume_mm3": vol,
          "bodies": sum(o.component.bRepBodies.count for o in d.rootComponent.allOccurrences),
          "all_solid": all(b.isSolid for o in d.rootComponent.allOccurrences for b in o.component.bRepBodies),
          "hidden": [n for n, o in occ.items() if not o.isVisible], "images": saved, "archive": ARCHIVE}
