import adsk.core, adsk.fusion, os, time

STEP_PATH = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r41_diag\r41_preview.step"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
t0 = time.time()
for d0 in list(app.documents):
    if d0.name.startswith("41 Carriage build fixes (preview"):
        d0.close(False)
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "41 Carriage build fixes (preview 2)"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("STEP import failed")
occs = list(d.rootComponent.allOccurrences)
bodies = sum(o.component.bRepBodies.count for o in occs) + d.rootComponent.bRepBodies.count


def shot(file, eye, target, up, extent):
    for _ in range(2):
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
    return app.activeViewport.saveAsImageFile(os.path.join(IMAGES, file), 1400, 1000)


# Fusion works in cm. From below and in front of the hotend slot: the two horizontal jets.
saved = {"outlet": shot("p2_outlet.png", (9.0, 9.0, -12.0), (0.0, 2.3, -7.55), (0, 0, 1), 4.0),
         "cheek": shot("p2_cheek.png", (16.0, 9.0, -1.0), (1.8, 1.6, -5.4), (0, 0, 1), 3.0),
         "servo": shot("p2_servo.png", (-6.0, -14.0, 9.0), (1.05, -1.0, 4.5), (0, 0, 1), 4.0)}
cam = app.activeViewport.camera
cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
cam.isSmoothTransition = False
cam.target = adsk.core.Point3D.create(0.0, 0.5, -5.0)
cam.eye = adsk.core.Point3D.create(14.0, 18.0, -14.0)
cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
cam.isFitView = True
app.activeViewport.camera = cam
app.activeViewport.refresh()
result = {"document": doc.name, "bodies": bodies, "seconds": round(time.time() - t0, 1), "images": saved}
