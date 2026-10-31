import adsk.core, adsk.fusion, os

IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"][0]
doc.activate()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
occs = list(d.rootComponent.allOccurrences)
keep = ("P21_", "P24_", "P20_", "R40_INLET", "ACC_EBB42_BRIDGE")
hidden = []
for o in occs:
    n = o.name.split(":")[0]
    if o.childOccurrences.count == 0 and not n.startswith(keep) and o.isLightBulbOn:
        o.isLightBulbOn = False
        hidden.append(o)


def shot(file, eye, target, extent):
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
    return app.activeViewport.saveAsImageFile(os.path.join(IMAGES, file), 1600, 700)


# Fusion works in cm. From the +X side at the saddle, then from above-front at an angle.
saved = {"side": shot("f41_p21_flat_side.png", (20.0, -1.6, -1.75), (0.0, -1.6, -1.75), 3.2),
         "angle": shot("f41_p21_flat_angle.png", (14.0, 8.0, 6.0), (0.0, -1.8, -2.0), 6.0)}
for o in hidden:
    o.isLightBulbOn = True
result = {"saved": saved, "hidden": len(hidden)}
