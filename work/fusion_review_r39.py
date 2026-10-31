import adsk.core, adsk.fusion, json, os

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
STEP_PATH = ROOT + r"\step\39_Dock_Pins_And_P18_Bushings_REVIEW.step"
ARCHIVE = ROOT + r"\39_Dock_Pins_And_P18_Bushings_REVIEW.f3d"
REPORT = ROOT + r"\verification_dock_pins_r39.json"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"

report = json.load(open(REPORT))
EXPECTED_BODIES = report["review_bodies"]
EXPECTED = {"Bambu_P18": report["p18"]["volume_mm3"]["r39"],
            "Bambu_Dock_P25_Refined_Dock": report["p25"]["volume_mm3"]["r39"]}

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "39 Dock pins and P18 bushings"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R39 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "39 Dock pins and P18 bushings (native review)"
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
gaps = {
    "docked_pin_to_bushing": gap_mm(find("Bambu_Dock_Left_5x12_Dowel_Pin"), find("Bambu_Left_Bushing")),
    "docked_p18_to_p25": gap_mm(find("Bambu_P18"), find("Bambu_Dock_P25_Refined_Dock")),
    "docked_pin_to_p18": gap_mm(find("Bambu_Dock_Left_5x12_Dowel_Pin"), find("Bambu_P18")),
}


def shot(file, eye, target, up, extent):
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


saved = {
    # Docked Bambu (X0) and the Red Lizard 12 mm out of its dock (X37.3), from above and the +X side.
    "pair": shot("f39_pair.png", (11.5, 1.0, 9.5), (1.9, 4.6, 0.8), (0, 0, 1), 9.0),
    # Side view into the Red Lizard's gap: the dock's pins stand proud of P25, in line with P18's bushings.
    "gap": shot("f39_gap.png", (13.0, 4.2, 1.6), (3.73, 4.2, 1.6), (0, 0, 1), 3.2),
}
# From the dock side with the Red Lizard's dock body hidden: P18's bushings with the pins lined up in front.
hidden = [o for o in occs if o.name.startswith("RedLizard_Dock_") and "Dowel_Pin" not in o.name
          and "Dock_Magnet" not in o.name]
for o in hidden:
    o.isLightBulbOn = False
saved["face"] = shot("f39_face.png", (3.73 - 2.5, 12.0, 4.5), (3.73, 4.3, 1.6), (0, 0, 1), 3.4)
for o in hidden:
    o.isLightBulbOn = True
result = {"document": opened.name, "bodies": bodies, "native_volumes_mm3": volumes, "native_gaps_mm": gaps,
          "archive_mb": round(os.path.getsize(ARCHIVE) / 1e6, 1), "images": saved}
