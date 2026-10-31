import adsk.core, adsk.fusion, os

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\fusion_r43b"
TITLE = "43b CPAP outlet: revision 41 and 43 P22 after the review (native review)"
doc = next(d0 for d0 in app.documents if d0.name == TITLE)
doc.activate()
adsk.doEvents()
vp = app.activeViewport


def camera(target_mm, direction, extent_cm, up=(0, 0, 1), dist=40.0):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(tv + dist * c / n for tv, c in zip((t.x, t.y, t.z), direction)))
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


for tag, dx in (("v1", 200.0), ("full", 240.0), ("runout", 280.0)):
    camera((dx - 11.9, 16.6, -73.0), (-0.8, 1.0, -0.75), 0.55)
    vp.saveAsImageFile(os.path.join(OUT, f"heel_zoom_{tag}.png"), 1000, 800)
    camera((dx - 11.9, 16.6, -73.0), (-1.0, -0.35, -0.5), 0.55)
    vp.saveAsImageFile(os.path.join(OUT, f"heel_back_{tag}.png"), 1000, 800)
camera((280.0 - 11.0, 26.6, -73.2), (-1.0, 0.0, -0.6), 0.6)
vp.saveAsImageFile(os.path.join(OUT, "front_zoom_runout.png"), 1000, 800)
result = "ok"
