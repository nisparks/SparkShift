import adsk.core, adsk.fusion, json, os

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
STEP_PATH = ROOT + r"\step\41_Carriage_Build_Fixes_Complete_REVIEW.step"
ARCHIVE = ROOT + r"\41_Carriage_Build_Fixes_REVIEW.f3d"
REPORT = ROOT + r"\verification_carriage_fixes_r41.json"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"

report = json.load(open(REPORT))
EXPECTED_BODIES = report["review_bodies"]
NAMES = {"P20": "P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW", "P21": "P21_CPAP_Gantry_Bridge_Thick_Joints_R41_REVIEW",
         "P22": "P22_CPAP_Lower_Plenum_Wide_Jets_Face_Mounts_R41_REVIEW", "P24": "P24_EBB42_Frame_Mount_R41_REVIEW",
         "P02": "P02_Motor_Servo_Plate_MG90D_Snug_Pocket_R41_REVIEW", "P03_15x5x3": "P03_Front_Case_Magnets_15x5x3_R41_REVIEW",
         "P01": "P01_Back_case_COTS_MR74_Lowered_Bosses_No_Tab_R41_REVIEW"}
P01 = NAMES["P01"]
EXPECTED = {NAMES[k]: report["parts"][k]["volume_mm3"] for k in NAMES}

for d0 in list(app.documents):
    if d0.name.startswith("41 "):
        d0.close(False)

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "41 Carriage build fixes"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R41 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "41 Carriage build fixes (native review)"
doc.close(False)
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occs = list(d.rootComponent.allOccurrences)
bodies = sum(o.component.bRepBodies.count for o in occs) + d.rootComponent.bRepBodies.count
if bodies != EXPECTED_BODIES:
    raise RuntimeError(f"Native review has {bodies} bodies, expected {EXPECTED_BODIES}")


def find(name):
    found = [o for o in occs if o.name.split(":")[0] == name]
    if len(found) != 1:
        raise RuntimeError(f"{name}: {len(found)} occurrences")
    return found[0]


def volume(name):
    o = find(name)
    if o.component.bRepBodies.count != 1:
        raise RuntimeError(f"{name}: {o.component.bRepBodies.count} bodies")
    return o.component.bRepBodies.item(0).getPhysicalProperties(
        adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000


def gap_mm(a, b):
    best = None
    for i in range(a.bRepBodies.count):
        for j in range(b.bRepBodies.count):
            v = app.measureManager.measureMinimumDistance(a.bRepBodies.item(i), b.bRepBodies.item(j)).value
            best = v if best is None else min(best, v)
    return round(best * 10.0, 4)


volumes = {n: round(volume(n), 2) for n in EXPECTED}
for n, v in volumes.items():
    if abs(v - EXPECTED[n]) > 0.1:
        raise RuntimeError(f"Native {n} volume {v} vs {EXPECTED[n]}")
gaps = {"p24_to_ebb42": gap_mm(find(NAMES["P24"]), find("EBB42")),
        "p24_to_p20": gap_mm(find(NAMES["P24"]), find(NAMES["P20"])),
        "p22_to_p01": gap_mm(find(NAMES["P22"]), find(P01))}


def shot(file, eye, target, up, extent):
    # The first viewExtents set after switching to orthographic is dropped, so apply the camera twice.
    for _ in range(2):
        cam = app.activeViewport.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = adsk.core.Point3D.create(*eye)
        cam.target = adsk.core.Point3D.create(*target)
        cam.upVector = adsk.core.Vector3D.create(*up)
        cam.viewExtents = extent
        app.activeViewport.camera = cam
        app.activeViewport.refresh()
        adsk.doEvents()
    return app.activeViewport.saveAsImageFile(os.path.join(IMAGES, file), 1600, 1000)


def hide(prefixes):
    out = [o for o in occs if o.name.split(":")[0].startswith(prefixes) and o.isLightBulbOn]
    for o in out:
        o.isLightBulbOn = False
    return out


def show(items):
    for o in items:
        o.isLightBulbOn = True


# Fusion works in cm; viewExtents is about the visible height in cm.
saved = {}
h = hide(("EBB42", "P20_", "R41_EBB42_M3x18", "R41_EBB42_M3x14", "Beacon", "Probe_Cable"))
saved["p24"] = shot("f41_p24.png", (-9.0, -16.0, 7.0), (0.0, -1.6, 0.5), (0, 0, 1), 6.2)
show(h)
saved["outlet"] = shot("f41_outlet.png", (9.0, 9.0, -12.0), (0.0, 2.3, -7.55), (0, 0, 1), 4.0)
saved["cheek"] = shot("f41_cheek.png", (16.0, 9.0, -1.0), (1.8, 1.6, -5.4), (0, 0, 1), 3.0)
saved["servo"] = shot("f41_servo.png", (-6.0, -14.0, 9.0), (1.05, -1.0, 4.5), (0, 0, 1), 4.0)
saved["overall"] = shot("f41_overall.png", (-11.0, -15.0, 7.0), (0.0, -1.5, -0.8), (0, 0, 1), 15.0)
cam = app.activeViewport.camera
cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
cam.isSmoothTransition = False
cam.target = adsk.core.Point3D.create(0.0, -1.5, 0.0)
cam.eye = adsk.core.Point3D.create(-16.0, -24.0, 6.0)
cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
cam.isFitView = True
app.activeViewport.camera = cam
app.activeViewport.refresh()
result = {"document": opened.name, "bodies": bodies, "native_volumes_mm3": volumes, "native_gaps_mm": gaps,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "images": saved}
