import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"][0]
doc.activate()
vp = app.activeViewport
saved_cam = vp.camera


def shot(file, target_mm, direction, extent_cm, up=(0, 0, 1)):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(t_ + 12.0 * c / n for t_, c in zip((t.x, t.y, t.z), direction)))
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
    return vp.saveAsImageFile(os.path.join(FILES, file), 1200, 900)


head = (18.5, 33.0, -14.6)
saved = {
    "a": shot("tab_a.png", head, (-0.58, 0.79, 0.19), 1.6),
    "b": shot("tab_b.png", head, (0.0, 1.0, 0.0), 1.6),
    "c": shot("tab_c.png", head, (0.5, 0.8, -0.35), 1.6),
    "d": shot("tab_d.png", (-18.5, 33.0, -14.6), (0.58, 0.79, 0.19), 1.6),
}
vp.camera = saved_cam
vp.refresh()
result = saved
