import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"][0]
doc.activate()


def shot(file, eye, target, extent, size=(1600, 1000)):
    for _ in range(2):
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
    return app.activeViewport.saveAsImageFile(os.path.join(FILES, file), *size)


saved = {"rear": shot("f41_bm_overall_rear.png", (-11.0, -15.0, 7.0), (0.0, -1.5, -0.8), 15.0),
         "front_low": shot("f41_bm_overall_front.png", (10.0, 16.0, -9.0), (0.0, 1.0, -3.0), 15.0)}
cam = app.activeViewport.camera
cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
cam.isSmoothTransition = False
cam.target = adsk.core.Point3D.create(0.0, -1.0, -1.0)
cam.eye = adsk.core.Point3D.create(-16.0, -24.0, 9.0)
cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
cam.isFitView = True
app.activeViewport.camera = cam
app.activeViewport.refresh()
result = {"images": saved}
