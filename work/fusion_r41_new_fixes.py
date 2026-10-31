import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"][0]
doc.activate()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
occs = [o for o in d.rootComponent.allOccurrences if o.childOccurrences.count == 0]
vp = app.activeViewport


def hide(prefixes):
    out = [o for o in occs if o.name.split(":")[0].startswith(prefixes) and o.isLightBulbOn]
    for o in out:
        o.isLightBulbOn = False
    return out


def show(items):
    for o in items:
        o.isLightBulbOn = True


def shot(file, target_mm, direction, extent_cm):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(t_ + 15.0 * c / n for t_, c in zip((t.x, t.y, t.z), direction)))
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = e
        cam.target = t
        cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
        cam.viewExtents = extent_cm
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()
    return vp.saveAsImageFile(os.path.join(FILES, file), 1400, 1000)


saved = {}
h = hide(("P03_",))
saved["p01_tab"] = shot("f41_p01_no_tab.png", (18.5, 27.5, -17.5), (0.35, 0.9, -0.25), 2.2)
show(h)
h = hide(("EBB42", "R41_EBB42_M3x", "P20_", "R40_INLET", "ACC_EBB42_BRIDGE", "Probe_Cable", "P21_", "P22_", "P23_",
          "Beacon", "R37_", "R41_P22", "ACC_CASE"))
saved["hall_rear"] = shot("f41_hall_groove_rear.png", (0.0, -25.4, -15.0), (-0.3, -0.92, -0.25), 2.0)
show(h)
cam = vp.camera
cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
cam.isSmoothTransition = False
cam.target = adsk.core.Point3D.create(0.0, -1.5, -0.8)
cam.eye = adsk.core.Point3D.create(-11.0, -15.0, 7.0)
cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
cam.isFitView = True
vp.camera = cam
vp.refresh()
result = saved
