import adsk.core, adsk.fusion

IMAGE = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect\f29_final_state.png"
ARCHIVE = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\29_Bambu_Clean_Rebuild_Review.f3d"
if app.activeDocument.name != "29 Bambu - Clean rebuild (native review)":
    raise RuntimeError("Unexpected active document: " + app.activeDocument.name)
d = adsk.fusion.Design.cast(app.activeProduct)
occ = {o.name.split(":")[0]: o for o in d.rootComponent.allOccurrences}
hidden = ("R22_Baseline_Print_compare", "Dock_reference", "Carriage_Core_reference",
          "CPAP_Probe_EBB42_Mounts_reference")
for name, o in occ.items():
    if name == "29 Bambu clean rebuild review":
        continue
    want = name not in hidden
    o.isLightBulbOn = not want
    o.isLightBulbOn = want
cam = app.activeViewport.camera
cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
cam.isFitView = False
cam.eye = adsk.core.Point3D.create(-25, -9, -12)
cam.target = adsk.core.Point3D.create(0.0, 2.5, -2.8)
cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
cam.viewExtents = 5.0
app.activeViewport.camera = cam
app.activeViewport.refresh()
adsk.doEvents()
saved = app.activeViewport.saveAsImageFile(IMAGE, 1400, 1050)
exported = d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE))
result = {"image": saved, "archive_updated": exported,
          "visible": [n for n, o in occ.items() if o.isVisible],
          "hidden": [n for n, o in occ.items() if not o.isVisible]}
