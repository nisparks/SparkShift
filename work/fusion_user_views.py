import adsk.core, adsk.fusion, os

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\fusion_user_edit"
doc = app.activeDocument
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
vp = app.activeViewport
saved = vp.camera   # restored at the end
info = {}
for i in range(d.analyses.count):
    a = d.analyses.item(i)
    try:
        sa = adsk.fusion.SectionAnalysis.cast(a)
        pl = sa.sectionPlane if hasattr(sa, "sectionPlane") else None
        g = None
        if pl is not None:
            try:
                g = pl.geometry
            except Exception:
                g = None
        row = {"visible": a.isLightBulbOn}
        if g is not None:
            row["origin_mm"] = [round(g.origin.x * 10, 3), round(g.origin.y * 10, 3), round(g.origin.z * 10, 3)]
            row["normal"] = [round(g.normal.x, 4), round(g.normal.y, 4), round(g.normal.z, 4)]
        try:
            row["offset_mm"] = round(sa.initialPosition.value * 10, 3) if hasattr(sa, "initialPosition") else None
        except Exception:
            pass
        try:
            row["plane_type"] = pl.objectType.split("::")[-1]
        except Exception:
            pass
        info[a.name] = row
    except Exception as ex:
        info[a.name] = {"error": str(ex)}


def shot(name, target_mm, direction, extent_cm, up):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(tv + 40.0 * c / n for tv, c in zip((t.x, t.y, t.z), direction)))
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
    vp.saveAsImageFile(os.path.join(OUT, name), 1600, 900)


X0 = 90.0   # the user's edited P22 (R43_RedLizard column)
try:
    shot("top_view.png", (X0, -8.0, -60.0), (0, 0, 1), 9.0, (-1, 0, 0))
    shot("bottom_view.png", (X0, -8.0, -60.0), (0, 0, -1), 9.0, (-1, 0, 0))
    shot("boss_top_close.png", (X0, -36.0, -52.0), (0, 0, 1), 2.2, (-1, 0, 0))
finally:
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = saved.cameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = saved.eye
        cam.target = saved.target
        cam.upVector = saved.upVector
        cam.viewExtents = saved.viewExtents
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()
now = vp.camera
info["camera_restored"] = abs(now.eye.x - saved.eye.x) + abs(now.eye.y - saved.eye.y) + abs(now.eye.z - saved.eye.z) < 1e-6
result = info
