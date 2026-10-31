import adsk.core, adsk.fusion, json, os

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
STEP_PATH = ROOT + r"\step\40_Carriage_P20_P21_Screws_Complete_REVIEW.step"
ARCHIVE = ROOT + r"\40_P20_P21_Screws_REVIEW.f3d"
REPORT = ROOT + r"\verification_inlet_screws_r40.json"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"

report = json.load(open(REPORT))
EXPECTED_BODIES = report["review_bodies"]
NAMES = {"P20": "P20_CPAP_Hose_Inlet_Button_Head_Lugs_R40_REVIEW", "P21": "P21_CPAP_Gantry_Bridge_Moved_Inserts_R40_REVIEW"}
EXPECTED = {NAMES[k]: report["parts"][k]["volume_mm3"] for k in NAMES}

# Close the earlier preview of the rejected anchor draft, if it is still open.
for d0 in list(app.documents):
    if d0.name.startswith("40 ") and ("preview" in d0.name or "Stack anchor" in d0.name or "native review" in d0.name):
        d0.close(False)

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "40 P20-to-P21 screws"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R40 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "40 P20-to-P21 screws (native review)"
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


volumes = {n: volume(n) for n in EXPECTED}
for n, v in volumes.items():
    if abs(v - EXPECTED[n]) > 0.05:
        raise RuntimeError(f"Native {n} volume {v} vs {EXPECTED[n]}")
beam = find("Reference_R1_GANTRY_X_2020_430_NOMINAL")
gaps = {
    "button_head_to_ebb42": min(gap_mm(find(f"R40_INLET_M3x8_BUTTON_{i}"), find("EBB42")) for i in (0, 1)),
    "p21_to_x_beam_note": gap_mm(find(NAMES["P21"]), beam),
    "probe_cable_to_x_beam_note": gap_mm(find("Probe_Cable_Route_R37_REVIEW"), beam),
}


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


# Fusion works in cm; viewExtents is about the visible height in cm.
hidden = [o for o in occs if o.name.split(":")[0] in ("EBB42", "P24_EBB42_Controller_Mount_Cable_Entry_R35_REVIEW")]
for o in hidden:
    o.isLightBulbOn = False
# From above, EBB42 and P24 hidden: P20's lugs with the button heads, the probe cable between them.
saved = {"lugs": shot("f40_lugs.png", (0.0, -3.05, 12.0), (0.0, -3.05, -1.6), (0, 1, 0), 3.2)}
for o in hidden:
    o.isLightBulbOn = True
# From +X: P21's conduit meeting the X beam's cut end (note 1, unchanged).
saved["side"] = shot("f40_side.png", (14.0, -3.3, -3.4), (0.0, -3.3, -3.4), (0, 0, 1), 3.6)
saved["overall"] = shot("f40_overall.png", (-11.0, -15.0, 7.0), (0.0, -2.0, -1.5), (0, 0, 1), 16.0)
cam = app.activeViewport.camera
cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
cam.isSmoothTransition = False
cam.target = adsk.core.Point3D.create(0.0, -2.0, -1.0)
cam.eye = adsk.core.Point3D.create(-16.0, -24.0, 5.0)
cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
cam.isFitView = True
app.activeViewport.camera = cam
app.activeViewport.refresh()
result = {"document": opened.name, "bodies": bodies, "native_volumes_mm3": volumes, "native_gaps_mm": gaps,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "images": saved}
