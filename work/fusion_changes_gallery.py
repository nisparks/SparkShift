import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
STEP = os.path.join(FILES, "r41_changes_gallery.step")
TITLE = "41 R41 changes, before and after (sections)"

for d0 in list(app.documents):
    if d0.name.startswith(TITLE):
        d0.close(False)
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = TITLE
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP), d.rootComponent):
    raise RuntimeError("gallery STEP import failed")
occs = [o for o in d.rootComponent.allOccurrences if o.childOccurrences.count == 0]
bodies = sum(o.component.bRepBodies.count for o in occs)
vp = app.activeViewport


def camera(target_mm, direction, extent_cm, up=(0, 0, 1), ortho=True):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(t_ + 40.0 * c / n for t_, c in zip((t.x, t.y, t.z), direction)))
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
    ("1 Jets, before (left) and bell-mouth (right), from the front", (0.0, 22.2, -75.0), (0, 1, 0), 2.6, (0, 0, 1)),
    ("2 Square-edged jet, close up (before)", (24 + 11.5, 22.2, -74.6), (0, 1, 0), 0.75, (0, 0, 1)),
    ("3 Bell-mouth jet, close up (R41)", (-24 + 11.5, 22.2, -74.6), (0, 1, 0), 0.75, (0, 0, 1)),
    ("4 Hall path from above, cut at Z-15: before (left) and R41 (right)", (0.0, 116.0, -15.0), (0, 0, 1), 5.6, (0, 1, 0)),
    ("5 Hall groove through P02 and P24, close up (R41)", (25.0, 108.0, -15.0), (0, 0, 1), 3.0, (0, 1, 0)),
    ("6 P01 under the +X front screw: tab (left) and cut off (right)", (0.0, 267.5, -16.5), (0.25, 0.9, -0.35), 2.0, (0, 0, 1)),
    ("7 P22 behind the +X cheek, from above: pit (left) and filled (right)", (0.0, 371.1, -58.25), (0, 0, 1), 3.2, (0, 1, 0)),
    ("8 The pit, close up (before)", (-10.0, 371.1, -58.25), (0.15, -0.35, 1), 0.6, (0, 1, 0)),
    ("9 Filled, close up (R41)", (10.0, 371.1, -58.25), (0.15, -0.35, 1), 0.6, (0, 1, 0)),
]
named, shots = [], {}
nv = getattr(d, "namedViews", None)
for i, (name, target, direction, extent, up) in enumerate(VIEWS):
    cam = camera(target, direction, extent, up)
    fname = f"gallery_view_{i + 1}.png"
    vp.saveAsImageFile(os.path.join(FILES, fname), 1600, 900)
    shots[name] = fname
    if nv is not None:
        try:
            nv.add(cam, name)
            named.append(name)
        except Exception as ex:
            named.append(f"failed: {ex}")
camera(*VIEWS[0][1:])
result = {"document": doc.name, "bodies": bodies, "occurrences": len(occs), "named_views": named, "shots": shots}
