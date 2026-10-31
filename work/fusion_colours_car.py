import adsk.core, adsk.fusion, os

IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [d0 for d0 in app.documents if d0.name == "SparkShift print colours"][0]
doc.activate()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
top = d.rootComponent.occurrences.item(0)
keep = ("Carriage_T4_withdrawn_60mm:1", "T4_Bambu_Green:1")


def shot(file, eye, target, up, extent=None):
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
    return app.activeViewport.saveAsImageFile(os.path.join(IMAGES, file), 1200, 1300)


def toward(target, direction, dist=150.0):
    n = sum(c * c for c in direction) ** 0.5
    return tuple(t + dist * c / n for t, c in zip(target, direction))


hidden = [o for o in top.childOccurrences if o.name not in keep]
for o in hidden:
    o.isLightBulbOn = False
car = (15.74, 11.02, 18.3)
saved = {"carriage_front": shot("c77_car_front.png", toward(car, (0.75, -1.0, 0.4)), car, (0, 0, 1), 16.5),
         "carriage_rear": shot("c77_car_rear.png", toward(car, (-0.75, 1.0, 0.4)), car, (0, 0, 1), 16.5)}
for o in hidden:
    o.isLightBulbOn = True
result = {"saved": saved, "hidden": len(hidden), "visible": all(o.isLightBulbOn for o in top.childOccurrences)}
