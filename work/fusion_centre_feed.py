import adsk.core, adsk.fusion, os

STEP = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\center_feed\centre_feed_review.step"
OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\center_feed"
TITLE = "45 Centre-feed variant (study): P23 folded into P22, rear jet fed over the probe"

# only this script's own document is ever closed; the user's "43 CPAP outlet" and the 43b review stay open
for d0 in list(app.documents):
    if d0.name == TITLE:
        d0.close(False)
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = TITLE
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP), d.rootComponent):
    raise RuntimeError("STEP import failed")
adsk.doEvents()
vp = app.activeViewport


def camera(target_mm, direction, extent_cm, up, persp=False, dist=40.0):
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


views = [
    ("1 From below, front at the bottom: revision 43 with P23 (left), the centre feed with the Bambu (middle) and the Red Lizard (right)",
     (0.0, 10.0, -76.0), (0.0, 0.0, -1.0), 17.0, (0, -1, 0)),
    ("2 Centre feed with the Bambu, from below: the drop past the probe's nose, the manifold and the rear jet under the sock",
     (0.0, 13.0, -76.0), (0.0, 0.0, -1.0), 5.0, (0, -1, 0)),
    ("3 Cut along the slot's centre (X0): the plenum on the probe's board, the drop past its nose, the manifold, the rear jet",
     (110.0, 8.0, -74.0), (1.0, 0.0, 0.0), 4.6, (0, 0, 1)),
    ("4 Cut through the plenum (Z-72.3), from above, front at the top: the openings from both side channels and the plenum over the probe",
     (165.0, 4.0, -73.0), (0.0, 0.0, 1.0), 5.2, (0, 1, 0)),
    ("5 From in front and below, through the hotend slot: the rear jet aimed at the nozzle",
     (0.0, 16.0, -76.5), (0.0, 1.0, -0.35), 4.0, (0, 0, 1)),
    ("6 Red Lizard, from the side, in front and below: the manifold under its block's neck and the legs beside it",
     (55.0, 15.0, -75.0), (0.6, 1.0, -0.5), 4.5, (0, 0, 1)),
]
shots = []
for i, (name, target, direction, extent, up) in enumerate(views):
    cam = camera(target, direction, extent, up)
    path = os.path.join(OUT, f"fusion_view_{i + 1}.png")
    vp.saveAsImageFile(path, 1600, 900)
    shots.append(path)
    try:
        d.namedViews.add(cam, name)
    except Exception:
        pass
camera(*views[2][1:])
result = {"document": doc.name, "occurrences": d.rootComponent.allOccurrences.count, "shots": shots}


