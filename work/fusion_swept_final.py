import adsk.core
import adsk.fusion
import os

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\swept_feed"
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "47 Swept-island feed STUDY - geometry checked, not print released"
design = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(
        os.path.join(OUT, "swept_island_review_final.step")), design.rootComponent):
    raise RuntimeError("Swept study STEP import failed")
for occ in design.rootComponent.allOccurrences:
    if "Air_route_P22" in occ.name:
        occ.isLightBulbOn = False
vp = app.activeViewport

def view(target, direction, extent, up):
    target = adsk.core.Point3D.create(*(v / 10 for v in target))
    length = sum(v*v for v in direction) ** .5
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.target = target
        cam.eye = adsk.core.Point3D.create(*(t + 30*v/length for t, v in zip(
            (target.x, target.y, target.z), direction)))
        cam.upVector = adsk.core.Vector3D.create(*up)
        cam.viewExtents = extent
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()

views = [
    ("1 Orange INTERNAL AIR, not printed material or CFD - swept feeds from above",
     (130, -1, -69), (0, 0, 1), 5.5, (0, 1, 0), "route"),
    ("2 Actual Bambu assembly from below - no crossbar below the probe",
     (0, 7, -74), (0, 0, -1), 6.4, (0, -1, 0), "underside"),
    ("3 X0 cutaway - closed floor over PCB, curved downward outlet",
     (195, 4, -71), (1, 0, 0), 4.5, (0, 0, 1), "cutaway"),
    ("4 Red Lizard and Cartographer - dedicated seat, probe datum unchanged",
     (65, 12, -74), (.6, 1, -.4), 4.5, (0, 0, 1), "redlizard"),
    ("5 Curved nozzle outlet from the front and below",
     (0, 13, -74), (0, 1, -.45), 3.8, (0, 0, 1), "mouth"),
]
for name, target, direction, extent, up, tag in views:
    view(target, direction, extent, up)
    design.namedViews.add(vp.camera, name)
    vp.saveAsImageFile(os.path.join(OUT, "fusion_" + tag + ".png"), 1600, 1000)
view(*views[0][1:5])
export = design.exportManager.createFusionArchiveExportOptions(os.path.join(OUT, "47_Swept_Island_Routing_STUDY.f3d"))
if not design.exportManager.execute(export):
    raise RuntimeError("Study Fusion archive export failed")
result = {"document": doc.name, "archive": export.filename, "views": [v[0] for v in views]}
