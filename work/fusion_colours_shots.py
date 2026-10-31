import adsk.core, adsk.fusion, os

IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [d0 for d0 in app.documents if d0.name == "SparkShift print colours"][0]
doc.activate()


def shot(file, eye, target, up, extent=None):
    # The first viewExtents set after switching to orthographic is dropped, so apply the camera twice.
    for _ in range(2):
        cam = app.activeViewport.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isSmoothTransition = False
        cam.eye = adsk.core.Point3D.create(*eye)
        cam.target = adsk.core.Point3D.create(*target)
        cam.upVector = adsk.core.Vector3D.create(*up)
        cam.isFitView = extent is None
        if extent is not None:
            cam.viewExtents = extent
        app.activeViewport.camera = cam
        app.activeViewport.refresh()
        adsk.doEvents()
    return app.activeViewport.saveAsImageFile(os.path.join(IMAGES, file), 1600, 1000), round(app.activeViewport.camera.viewExtents, 2)


def toward(target, direction, dist=150.0):
    n = sum(c * c for c in direction) ** 0.5
    return tuple(t + dist * c / n for t, c in zip(target, direction))


mid = (17.5, 6.0, 17.5)
car = (15.7, 11.0, 18.5)
docks = (15.6, 1.0, 17.0)
saved = {
    "front": shot("c77_front.png", toward(mid, (-0.55, -1.0, 0.65)), mid, (0, 0, 1), 30.0),
    "rear": shot("c77_rear.png", toward(mid, (0.55, 1.0, 0.75)), mid, (0, 0, 1), 30.0),
    "carriage": shot("c77_carriage.png", toward(car, (-0.8, 1.0, 0.6)), car, (0, 0, 1), 17.0),
    "docks": shot("c77_docks.png", toward(docks, (0.45, -1.0, 0.45)), docks, (0, 0, 1), 15.0),
}
result = saved
