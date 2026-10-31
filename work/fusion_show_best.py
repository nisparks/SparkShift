import adsk.core, adsk.fusion, os

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\fusion_r43b"
TITLE = "43b CPAP outlet: revision 41 and 43 P22 after the review (native review)"
doc = next((d0 for d0 in app.documents if d0.name == TITLE), None)
if doc is None:
    raise RuntimeError("review document not open")
doc.activate()
adsk.doEvents()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
vp = app.activeViewport


def camera(target_mm, direction, extent_cm, up=(0, 0, 1), persp=False, dist=40.0):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(tv + dist * c / n for tv, c in zip((t.x, t.y, t.z), direction)))
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = (adsk.core.CameraTypes.PerspectiveCameraType if persp
                          else adsk.core.CameraTypes.OrthographicCameraType)
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = e
        cam.target = t
        cam.upVector = adsk.core.Vector3D.create(*up)
        cam.viewExtents = extent_cm
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()
    return vp.camera


shots = {}
# revision 43 after the review, with the Bambu hotend, P23 and the Beacon (column at X-30)
views = [("best_top_front", (-30.0, -6.0, -62.0), (-0.55, 0.75, 0.9), 8.5, (0, 0, 1)),
         ("best_front_below", (-30.0, 10.0, -70.0), (-0.45, 1.0, -0.55), 8.5, (0, 0, 1))]
for name, target, direction, extent, up in views:
    cam = camera(target, direction, extent, up)
    vp.saveAsImageFile(os.path.join(OUT, f"{name}.png"), 1600, 1000)
    shots[name] = f"{name}.png"
    try:
        d.namedViews.add(cam, {"best_top_front": "0a Best version: revision 43 after the review, from above and in front",
                               "best_front_below": "0b Best version: from in front and below (jets either side of the "
                                                   "sock)"}[name])
    except Exception:
        pass
camera(*views[0][1:])
result = {"active": app.activeDocument.name, "shots": shots}
