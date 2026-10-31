import adsk.core, adsk.fusion

STEP_PATH = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\33_Fan_Mounts_Fusion_Review.step"
ARCHIVE = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\33_Fan_Mounts_Review.f3d"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect"
EXPECTED = {"R33_Bambu_Print": 14221.5207, "R33_RedLizard_Print": 9201.7145}
R33 = tuple(EXPECTED)
R30_HIDDEN = ("R32_Prints_compare", "Docks_reference", "Carriage_R31_reference")

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "33 Toolheads - fan mounts"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R33 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "33 Toolheads - fan mounts (native review)"
doc.close(False)
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occ = {o.name.split(":")[0]: o for o in d.rootComponent.allOccurrences}
volumes = {}
for name, expected in EXPECTED.items():
    bodies = list(occ[name].component.bRepBodies)
    if len(bodies) != 1:
        raise RuntimeError(f"Expected one body in {name}")
    volumes[name] = bodies[0].getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000
    if abs(volumes[name] - expected) > 0.05:
        raise RuntimeError(f"Native {name} volume mismatch: {volumes[name]} vs {expected}")


def set_visible(name, on):
    # Toggle through the opposite state so the viewport receives a real change event.
    occ[name].isLightBulbOn = not on
    occ[name].isLightBulbOn = on


def show(revision):
    for name in occ:
        if name.startswith("33 Fan"):
            continue
        hidden = name in R30_HIDDEN or (revision == 32 and name in R33)
        if revision == 32 and name == "R32_Prints_compare":
            hidden = False
        set_visible(name, not hidden)


def shot(file, eye, target, up, extent):
    cam = app.activeViewport.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.isFitView = False
    cam.eye = adsk.core.Point3D.create(*eye)
    cam.target = adsk.core.Point3D.create(*target)
    cam.upVector = adsk.core.Vector3D.create(*up)
    cam.viewExtents = extent
    app.activeViewport.camera = cam
    app.activeViewport.refresh()
    adsk.doEvents()
    return app.activeViewport.saveAsImageFile(IMAGES + "\\" + file, 1600, 900)


# Front view of both tools as parked (Bambu at X0, Red Lizard one bay toward -X), like the rack review.
FRONT = ((6.0, 30.0, -1.5), (-1.85, 3.2, -3.4), (0.0, 0.0, 1.0), 6.5)
BELOW = ((2.0, 25.0, -25.0), (-1.85, 3.0, -3.4), (0.0, 0.0, 1.0), 7.0)
saved = {}
for revision in (32, 33):
    show(revision)
    saved[f"front_r{revision}"] = shot(f"f33_front_r{revision}.png", *FRONT)
    saved[f"below_r{revision}"] = shot(f"f33_below_r{revision}.png", *BELOW)
show(33)
shot("f33_final.png", *FRONT)
result = {"document": opened.name, "native_volumes_mm3": volumes,
          "bodies": sum(o.component.bRepBodies.count for o in d.rootComponent.allOccurrences),
          "all_solid": all(b.isSolid for o in d.rootComponent.allOccurrences for b in o.component.bRepBodies),
          "hidden": [n for n, o in occ.items() if not o.isVisible], "images": saved, "archive": ARCHIVE}
