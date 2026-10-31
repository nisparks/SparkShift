import adsk.core, adsk.fusion, os
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [x for x in app.documents if x.name.startswith("43 CPAP outlet")][0]
doc.activate()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
vp = app.activeViewport
keep = ("R41_Cutaway_P22", "R43_Cutaway_P22")
hidden = []
for o in d.rootComponent.allOccurrences:
    if o.childOccurrences.count == 0 and o.name.split(":")[0] not in keep and o.isLightBulbOn:
        o.isLightBulbOn = False
        hidden.append(o)


def camera(target_mm, direction, extent_cm, up=(0, 0, 1)):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(t_ + 40.0 * c / n for t_, c in zip((t.x, t.y, t.z), direction)))
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = e
        cam.target = t
        cam.upVector = adsk.core.Vector3D.create(*up)
        cam.viewExtents = extent_cm
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()


shots = {}
for name, target, direction, extent in (("f43_cut_r43.png", (160.2, 22.5, -35.3), (-1.0, 0.0, 0.22), 1.5),
                                        ("f43_cut_r41.png", (160.2, 22.5, -75.3), (-1.0, 0.0, 0.22), 1.5),
                                        ("f43_cut_both.png", (160.2, 14.0, -55.0), (-1.0, 0.0, 0.0), 6.5)):
    camera(target, direction, extent)
    vp.saveAsImageFile(os.path.join(IMAGES, name), 1600, 900)
    shots[name] = True
for o in hidden:
    o.isLightBulbOn = True
camera((0.0, 18.0, -70.0), (0.0, 1.0, -0.45), 15.0)
result = {"hidden_and_restored": len(hidden), "shots": list(shots)}

