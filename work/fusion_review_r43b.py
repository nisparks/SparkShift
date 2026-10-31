import adsk.core, adsk.fusion, json, os

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
STEP_PATH = ROOT + r"\step\43_CPAP_Outlet_REVIEW.step"
DETAILS = [FILES + r"\fusion_user_edit\Jet_Before_Review.step", FILES + r"\fusion_user_edit\Jet_After_Review.step",
           FILES + r"\fusion_user_edit\Jet_Full_Round_Study.step"]
ARCHIVE = ROOT + r"\43_CPAP_Outlet_REVIEW.f3d"
REPORT = ROOT + r"\verification_cpap_outlet_r43.json"
IMAGES = FILES + r"\fusion_r43b"
TITLE = "43b CPAP outlet: revision 41 and 43 P22 after the review (native review)"
COLUMNS = {"R41_Bambu": -90.0, "R43_Bambu": -30.0, "R41_RedLizard": 30.0, "R43_RedLizard": 90.0}
os.makedirs(IMAGES, exist_ok=True)

report = json.load(open(REPORT))
EXPECTED = {"R41_Bambu_P22": report["p22"]["r41_volume_mm3"], "R43_Bambu_P22": report["p22"]["volume_mm3"],
            "R41_RedLizard_P22": report["p22"]["r41_volume_mm3"], "R43_RedLizard_P22": report["p22"]["volume_mm3"]}
CUT_X, CUT_DZ = 150.0, 40.0

# Only this script's own documents are ever closed: the user's "43 CPAP outlet: ..." (with manual edits) stays open.
for d0 in list(app.documents):
    if d0.name.startswith("43b ") or d0.name == "43b temp":
        d0.close(False)
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "43b temp"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R43 review STEP import failed")
for p in DETAILS:
    if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(p), d.rootComponent):
        raise RuntimeError(f"{p} import failed")
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
        raise RuntimeError(f"{name}: {len(found)} occurrences of {[o.name for o in occs][:40]}")
    return found[0]


def volume(name):
    o = find(name)
    return sum(o.component.bRepBodies.item(i).getPhysicalProperties(
        adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume for i in range(o.component.bRepBodies.count)) * 1000


volumes = {n: round(volume(n), 2) for n in EXPECTED}
for n, v in volumes.items():
    if abs(v - EXPECTED[n]) > 0.1:
        raise RuntimeError(f"Native {n} volume {v} vs {EXPECTED[n]}")
# the jet details sit at X+186..+231 (they may come in as root bodies or as occurrences): colour them like P22
src = find("R43_Bambu_P22").component.bRepBodies.item(0).appearance
details = []
for o in [None] + occs:
    comp = d.rootComponent if o is None else o.component
    for i in range(comp.bRepBodies.count):
        b = comp.bRepBodies.item(i)
        bb = (b if o is None else b.createForAssemblyContext(o)).boundingBox
        if bb.minPoint.x > 18.0:
            if src:
                b.appearance = src
            details.append((o.name if o else "(root)", b.name, round(bb.minPoint.x * 10, 1)))
if len(details) != 3:
    raise RuntimeError(f"Jet details: {details}")
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
    ("2 The left jet from the side channel, after the review: the r 2.4 round runs from the heel's ramp and eases out "
     "into the front wall's corner over its last 3 mm (front wall at left)",
     (240.0 - 12.0, 21.5, -72.6), (-1.0, 0.0, -0.3), 1.9, (0, 0, 1)),
    ("2b The same, from below and in front, looking back along the wall's bottom edge",
     (240.0 - 11.2, 24.5, -73.2), (-0.8, 1.0, -0.75), 1.25, (0, 0, 1)),
    ("3 The same jet before the review: the round stopped at Y26.2 and its foot tapered into a notch at the heel",
     (200.0 - 12.0, 21.5, -72.6), (-1.0, 0.0, -0.3), 1.9, (0, 0, 1)),
    ("3b Before the review, from below and in front", (200.0 - 11.2, 24.5, -73.2), (-0.8, 1.0, -0.75), 1.25, (0, 0, 1)),
    ("3c Study, not adopted (X+280): the round at full size right to the front wall, from below and in front",
     (280.0 - 11.2, 24.5, -73.2), (-0.8, 1.0, -0.75), 1.25, (0, 0, 1)),
    ("4 From above, through the socket: the rib behind the cable boss, flaring into its nose, and the nose's rounds "
     "running on to the island's sides", (B, -37.5, -51.0), (0.0, 0.0, 1.0), 2.0, (-1, 0, 0)),
    ("5 From above, into the window: the notch now runs right through, its three edges rounded r 5",
     (B, -6.0, -57.0), (0.0, 0.0, 1.0), 4.0, (-1, 0, 0)),
    ("6 Revision 43 with the Bambu, from the front: the jets either side of the sock", (B, 22.7, -75.0), (0.0, 1.0, -0.12),
     3.2, (0, 0, 1)),
    ("7 Revision 43, cut away: the left-hand jet from the hotend slot, its floor 0.4 mm lower (0.8 mm thick)",
     (CUT_X - 10.2, 22.5, -75.3 + CUT_DZ), (1.0, 0.0, 0.22), 1.5, (0, 0, 1)),
    ("8 Both cut-aways: revision 43 above, revision 41 below", (CUT_X - 5.0, 10.0, -63.0 + CUT_DZ / 2), (1.0, 0.0, 0.0),
     8.0, (0, 0, 1)),
    ("9 Revision 43 with the Bambu, from below: the hotend slot, sock and jets", (B, 20.0, -78.0), (0.0, 0.0, -1.0), 3.6,
     (0, 1, 0)),
]
named, shots = [], {}
for i, (name, target, direction, extent, up) in enumerate(VIEWS):
    cam = camera(target, direction, extent, up)
    fname = f"f43b_view_{i + 1}.png"
    vp.saveAsImageFile(os.path.join(IMAGES, fname), 1600, 900)
    shots[name] = fname
    try:
        d.namedViews.add(cam, name)
        named.append(name)
    except Exception as ex:
        named.append(f"failed: {ex}")
camera(*VIEWS[2][1:])
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive re-export failed")
result = {"document": opened.name, "bodies": bodies, "native_volumes_mm3": volumes,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "named_views": named, "shots": shots,
          "jet_details": details}
