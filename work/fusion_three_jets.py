import adsk.core, adsk.fusion, os
TITLE = "43b CPAP outlet: revision 41 and 43 P22 after the review (native review)"
doc = next(d0 for d0 in app.documents if d0.name == TITLE)
doc.activate()
adsk.doEvents()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
vp = app.activeViewport
t = adsk.core.Point3D.create(24.0 - 1.12, 2.3, -7.3)
direction = (-0.8, 1.0, -0.75)
n = sum(c * c for c in direction) ** 0.5
for _ in range(2):
    cam = vp.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.isFitView = False
    cam.isSmoothTransition = False
    cam.target = t
    cam.eye = adsk.core.Point3D.create(*(tv + 40.0 * c / n for tv, c in zip((t.x, t.y, t.z), direction)))
    cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
    cam.viewExtents = 6.2
    vp.camera = cam
    vp.refresh()
    adsk.doEvents()
for i in range(d.namedViews.count - 1, -1, -1):
    if d.namedViews.item(i).name.startswith("10 "):
        d.namedViews.item(i).deleteMe()
d.namedViews.add(vp.camera, "10 Jet round, three versions: first (X+200), full (X+240), proposed run-out (green, X+280)")
vp.saveAsImageFile(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\fusion_r43b\three_jets_overview.png", 1800, 1000)
result = "ok"
