import adsk.core, adsk.fusion

IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect"
d = adsk.fusion.Design.cast(app.activeProduct)
occ = {o.name.split(":")[0]: o for o in d.rootComponent.allOccurrences}
state = {n: o.isLightBulbOn for n, o in occ.items()}


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


saved = {
    "rear_full": shot("u_rear_full.png", (0.4, -30, -2.6), (0.4, 2.5, -2.6), 3.2),
    "rear_zoom_bores": shot("u_rear_zoom.png", (0.0, -30, -1.75), (0.0, 2.5, -1.75), 1.0),
    "rear_above_bores": shot("u_rear_above.png", (0.0, -20, 12), (0.0, 3.1, -1.75), 1.0),
}
result = {"document": app.activeDocument.name, "saved": saved, "visibility": state}
