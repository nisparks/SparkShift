import adsk.core, adsk.fusion, json, os

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
STEP_PATH = ROOT + r"\step\43_CPAP_Outlet_REVIEW.step"
CARRIAGE_STEP = ROOT + r"\step\43_CPAP_Outlet_Complete_REVIEW.step"
ARCHIVE = ROOT + r"\43_CPAP_Outlet_REVIEW.f3d"
REPORT = ROOT + r"\verification_cpap_outlet_r43.json"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
TITLE = "43 CPAP outlet: revision 41 and 43 P22 with both hotends (native review)"
CARRIAGE_TITLE = "43 Carriage with revision 43's P22"
COLUMNS = {"R41_Bambu": -90.0, "R43_Bambu": -30.0, "R41_RedLizard": 30.0, "R43_RedLizard": 90.0}

report = json.load(open(REPORT))
EXPECTED = {"R41_Bambu_P22": report["p22"]["r41_volume_mm3"], "R43_Bambu_P22": report["p22"]["volume_mm3"],
            "R41_RedLizard_P22": report["p22"]["r41_volume_mm3"], "R43_RedLizard_P22": report["p22"]["volume_mm3"]}
CUT_X, CUT_DZ = 150.0, 40.0             # the right halves of both P22s, revision 43's 40 mm above revision 41's

for d0 in list(app.documents):
    if d0.name.startswith("43 "):
        d0.close(False)
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "43 CPAP outlet"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R43 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = TITLE
doc.close(False)
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occs = list(d.rootComponent.allOccurrences)
bodies = sum(o.component.bRepBodies.count for o in occs) + d.rootComponent.bRepBodies.count


def find(name):
    found = [o for o in occs if o.name.split(":")[0] == name]
    if len(found) != 1:
        raise RuntimeError(f"{name}: {len(found)} occurrences")
    return found[0]


def volume(name):
    o = find(name)
    return sum(o.component.bRepBodies.item(i).getPhysicalProperties(
        adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume for i in range(o.component.bRepBodies.count)) * 1000


volumes = {n: round(volume(n), 2) for n in EXPECTED}
for n, v in volumes.items():
    if abs(v - EXPECTED[n]) > 0.1:
        raise RuntimeError(f"Native {n} volume {v} vs {EXPECTED[n]}")
vp = app.activeViewport


def camera(target_mm, direction, extent_cm, up=(0, 0, 1)):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(t_ + 40.0 * c / n for t_, c in zip((t.x, t.y, t.z), direction)))
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
    return vp.camera


B, L = COLUMNS["R43_Bambu"], COLUMNS["R41_Bambu"]
VIEWS = [
    ("1 Revision 43 and 41 with the Red Lizard (left pair), then with the Bambu (right pair), from the front and below",
     (0.0, 18.0, -70.0), (0.0, 1.0, -0.45), 15.0, (0, 0, 1)),
    ("2 Revision 43 with the Bambu, from the front: the jets either side of the sock", (B, 22.7, -75.0), (0.0, 1.0, -0.12), 3.2, (0, 0, 1)),
    ("3 Revision 43, cut away: the left-hand jet from the hotend slot, its floor 0.4 mm lower (0.8 mm thick)",
     (CUT_X - 10.2, 22.5, -75.3 + CUT_DZ), (1.0, 0.0, 0.22), 1.5, (0, 0, 1)),
    ("4 Revision 41, cut away, same view", (CUT_X - 10.2, 22.5, -75.3), (1.0, 0.0, 0.22), 1.5, (0, 0, 1)),
    ("5 Revision 43 with the Bambu, from below: the hotend slot, sock and jets", (B, 20.0, -78.0), (0.0, 0.0, -1.0), 3.6, (0, 1, 0)),
    ("6 Revision 43 with the Red Lizard, from the front", (COLUMNS["R43_RedLizard"], 22.7, -74.0), (0.0, 1.0, -0.12), 3.2, (0, 0, 1)),
    ("7 Revision 43 with the Bambu, from the front and above the left jet: the sock's 3.2 mm gap", (B - 8.0, 22.7, -72.0),
     (-0.3, 1.0, 0.5), 1.6, (0, 0, 1)),
    ("8 Both cut-aways: revision 43 above, revision 41 below", (CUT_X - 5.0, 10.0, -63.0 + CUT_DZ / 2), (1.0, 0.0, 0.0), 8.0,
     (0, 0, 1)),
    ("9 Revision 43 from above, into the window behind the block: its 45 degree notch prints without support",
     (B, -12.0, -57.0), (0.0, -0.35, 1.0), 4.4, (0, 1, 0)),
    ("10 Cut-aways, close: the notch leaves the block's bottom 1.8 mm for P23; the back's 45 degree chamfer",
     (CUT_X - 5.0, -20.0, -62.0 + CUT_DZ / 2), (1.0, 0.0, 0.0), 6.2, (0, 0, 1)),
]
named, shots = [], {}
for i, (name, target, direction, extent, up) in enumerate(VIEWS):
    cam = camera(target, direction, extent, up)
    fname = f"f43_view_{i + 1}.png"
    vp.saveAsImageFile(os.path.join(IMAGES, fname), 1600, 900)
    shots[name] = fname
    try:
        d.namedViews.add(cam, name)
        named.append(name)
    except Exception as ex:
        named.append(f"failed: {ex}")
camera(*VIEWS[0][1:])
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive re-export failed")

# the whole carriage with revision 43's P22, for looking round (not archived: 86 MB of STEP)
carriage = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
carriage.name = CARRIAGE_TITLE
dc = adsk.fusion.Design.cast(carriage.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(CARRIAGE_STEP), dc.rootComponent):
    raise RuntimeError("R43 carriage STEP import failed")
c_occs = list(dc.rootComponent.allOccurrences)
c_bodies = sum(o.component.bRepBodies.count for o in c_occs) + dc.rootComponent.bRepBodies.count
if c_bodies != report["assembly_bodies"]:
    raise RuntimeError(f"Carriage has {c_bodies} bodies, expected {report['assembly_bodies']}")
cam = camera((0.0, 10.0, -60.0), (0.6, 1.0, -0.35), 9.0)
vp.saveAsImageFile(os.path.join(IMAGES, "f43_carriage.png"), 1600, 900)
try:
    dc.namedViews.add(cam, "1 The carriage from the front, below: revision 43's P22 in teal")
except Exception:
    pass
opened.activate()
camera(*VIEWS[0][1:])
result = {"document": opened.name, "bodies": bodies, "native_volumes_mm3": volumes,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "named_views": named, "shots": shots,
          "carriage_document": carriage.name, "carriage_bodies": c_bodies}
