import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
STEP = os.path.join(FILES, "r41_lower_duct.step")
TITLE = "41 Lower CPAP duct, P21 + P22 (R41)"

for d0 in list(app.documents):
    if d0.name.startswith(TITLE):
        d0.close(False)
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = TITLE
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP), d.rootComponent):
    raise RuntimeError("lower duct STEP import failed")
occs = [o for o in d.rootComponent.allOccurrences if o.childOccurrences.count == 0]
bodies = sum(o.component.bRepBodies.count for o in occs)
vols = {o.name.split(":")[0]: round(sum(o.component.bRepBodies.item(i).getPhysicalProperties(
    adsk.fusion.CalculationAccuracy.HighCalculationAccuracy).volume for i in range(o.component.bRepBodies.count)) * 1000, 1)
    for o in occs}
vp = app.activeViewport


def camera(target_mm, direction, extent_cm, up=(0, 0, 1), ortho=True):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(t_ + 60.0 * c / n for t_, c in zip((t.x, t.y, t.z), direction)))
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = (adsk.core.CameraTypes.OrthographicCameraType if ortho
                          else adsk.core.CameraTypes.PerspectiveCameraType)
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


VIEWS = [
    ("1 Lower duct from behind, left, above", (0.0, -8.0, -48.0), (-0.55, -0.7, 0.45), 9.5, (0, 0, 1)),
    ("2 Lower duct from the front, below: jets and cheeks", (0.0, 0.0, -62.0), (0.45, 0.8, -0.4), 8.5, (0, 0, 1)),
    ("3 Cutaway along the right side channel (X16), from the side", (86.0, -8.0, -48.0), (1, 0, 0), 6.8, (0, 0, 1)),
    ("4 Cutaway at Z-63: side channels round the hotend slot, from above", (-70.0, -8.0, -63.0), (0, 0, 1), 8.2, (0, 1, 0)),
    ("5 Cutaway at Z-63, from above and behind", (-70.0, -8.0, -66.0), (-0.3, -0.75, 0.6), 8.0, (0, 0, 1)),
]
named, shots = [], {}
nv = getattr(d, "namedViews", None)
for i, (name, target, direction, extent, up) in enumerate(VIEWS):
    cam = camera(target, direction, extent, up)
    fname = f"lower_duct_view_{i + 1}.png"
    vp.saveAsImageFile(os.path.join(FILES, fname), 1600, 900)
    shots[name] = fname
    if nv is not None:
        try:
            nv.add(cam, name)
            named.append(name)
        except Exception as ex:
            named.append(f"failed: {ex}")
camera(*VIEWS[0][1:])
result = {"document": doc.name, "bodies": bodies, "volumes_mm3": vols, "named_views": named}
