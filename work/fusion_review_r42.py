import adsk.core, adsk.fusion, json, os

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
STEP_PATH = ROOT + r"\step\42_Cartographer_Mount_REVIEW.step"
ARCHIVE = ROOT + r"\42_Cartographer_Mount_REVIEW.f3d"
REPORT = ROOT + r"\verification_cartographer_mount_r42.json"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
TITLE = "42 Cartographer mount (native review)"
P23C, P23 = "Cartographer_P23_Probe_Mount_Cartographer_R42_REVIEW", "Beacon_P23_Probe_Mount_Raised_Rear_Ears_R37_REVIEW"

report = json.load(open(REPORT))
EXPECTED = {P23C: report["p23"]["volume_mm3"]["r42"], P23: report["p23"]["volume_mm3"]["r37"]}

for d0 in list(app.documents):
    if d0.name.startswith("42 "):
        d0.close(False)
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "42 Cartographer mount"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R42 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = TITLE
doc.close(False)
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occs = list(d.rootComponent.allOccurrences)
bodies = sum(o.component.bRepBodies.count for o in occs) + d.rootComponent.bRepBodies.count
if bodies != report["review_bodies"]:
    raise RuntimeError(f"Native review has {bodies} bodies, expected {report['review_bodies']}")


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

translucent = []
SEE_THROUGH = {"keepout": 0.3, "_P22": 0.4, "_P01": 0.2}      # so the probe, the column and the nuts show through
for o in occs:
    n = o.name.split(":")[0]
    level = next((v for k, v in SEE_THROUGH.items() if k in n), None)
    if level is not None:
        for i in range(o.component.bRepBodies.count):
            try:
                o.component.bRepBodies.item(i).opacity = level
                translucent.append(n)
            except Exception as ex:
                translucent.append(f"{n}: {ex}")
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


VIEWS = [
    ("1 Beacon build (left, revision 37 P23) and Cartographer build (right, revision 42 P23), from behind",
     (-35.0, 0.0, -62.0), (0.35, -1.0, 0.45), 7.5),
    ("2 Cartographer build: its keepout column (red) and the metal that reaches into it", (0.0, 3.0, -64.0), (1.0, -0.65, 0.4), 4.2),
    ("3 The core's two lower nuts and draw-screw ends in the top of the column", (0.0, 5.3, -55.5), (-1.0, -0.5, 0.25), 2.4),
    ("4 The Red Lizard heater block at the column's front face", (0.0, 14.3, -58.3), (1.0, 0.25, 0.2), 1.4),
    ("5 Beacon build: its keepouts are clear", (-70.0, 3.0, -64.0), (-1.0, -0.65, 0.4), 4.2),
    ("6 Cartographer from the side: P23 3.67 mm, coil 2.81 mm above the tip", (0.0, 4.0, -73.0), (1.0, 0.0, 0.0), 3.0),
    ("7 Beacon from the side: P23 3.87 mm, coil 2.60 mm above the tip", (-70.0, 4.0, -73.0), (-1.0, 0.0, 0.0), 3.0),
]
named, shots = [], {}
for i, (name, target, direction, extent) in enumerate(VIEWS):
    cam = camera(target, direction, extent)
    fname = f"f42_view_{i + 1}.png"
    vp.saveAsImageFile(os.path.join(IMAGES, fname), 1600, 900)
    shots[name] = fname
    try:
        d.namedViews.add(cam, name)
        named.append(name)
    except Exception as ex:
        named.append(f"failed: {ex}")
camera(*VIEWS[0][1:])
# Save the archive again so it keeps the see-through settings and named views.
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive re-export failed")
result = {"document": opened.name, "bodies": bodies, "native_volumes_mm3": volumes, "translucent": translucent,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "named_views": named, "shots": shots}
