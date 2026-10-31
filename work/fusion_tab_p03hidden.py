import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"][0]
doc.activate()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
vp = app.activeViewport
saved_cam = vp.camera
p03 = [o for o in d.rootComponent.allOccurrences if o.name.startswith(("P03_Front_Case", "P03_Magnet"))]
was = [o.isLightBulbOn for o in p03]
for o in p03:
    o.isLightBulbOn = False


def shot(file, direction, extent=1.6, target=(18.5, 31.0, -16.5)):
    t = adsk.core.Point3D.create(*(v / 10 for v in target))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(t_ + 12.0 * c / n for t_, c in zip((t.x, t.y, t.z), direction)))
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = e
        cam.target = t
        cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
        cam.viewExtents = extent
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()
    return vp.saveAsImageFile(os.path.join(FILES, file), 1200, 900)


saved = {"below_left": shot("tab_p03hidden_a.png", (-0.58, 0.79, -0.12)),
         "front_low": shot("tab_p03hidden_b.png", (-0.25, 0.95, -0.2))}
for o, w in zip(p03, was):
    o.isLightBulbOn = w
vp.camera = saved_cam
vp.refresh()
result = {"p03_hidden_then_restored": len(p03), "images": saved}
