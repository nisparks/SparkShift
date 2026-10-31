import adsk.core, adsk.fusion

STEP_PATH = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\31_Carriage_Lowered_Mounts_Fusion_Review.step"
ARCHIVE = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\31_Carriage_Lowered_Mounts_Review.f3d"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect"
EXPECTED = {"R31_P01_Lowered_Bosses": EXPECTED_P01, "R31_P22_Lowered_Mounts": EXPECTED_P22}
R31 = ("R31_P01_Lowered_Bosses", "R31_P22_Lowered_Mounts", "R31_P22_P01_M3_Screws_And_Heatsets")
R30 = ("R30_P01_released_compare", "R30_P22_released_compare", "R30_P22_P01_hardware_compare")
ALWAYS_HIDDEN = ("Dock_reference",)

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "31 Carriage - lowered P22 mounts"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R31 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "31 Carriage - lowered P22 mounts (native review)"
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
        if name.startswith("31 Carriage"):
            continue
        on = name not in ALWAYS_HIDDEN and not (name in R30 and revision == 31) and not (name in R31 and revision == 30)
        set_visible(name, on)


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


# The user's fan-side view from the question, then the -X side under the parked neighbour's fan.
USER = ((42.7228, -13.3663, -5.3738), (-2.3186, 0.6568, -4.588), (0.0381, 0.0664, 0.9971), EXTENT)
NEIGHBOUR = ((-45.0, -14.0, -5.6), (-1.8, 1.4, -4.9), (0.0, 0.0, 1.0), EXTENT)
saved = {}
for revision in (30, 31):
    show(revision)
    saved[f"user_view_r{revision}"] = shot(f"f31_user_view_r{revision}.png", *USER)
    saved[f"neighbour_side_r{revision}"] = shot(f"f31_neighbour_side_r{revision}.png", *NEIGHBOUR)
show(31)
shot("f31_final.png", *USER)
result = {"document": opened.name, "native_volumes_mm3": volumes,
          "bodies": sum(o.component.bRepBodies.count for o in d.rootComponent.allOccurrences),
          "all_solid": all(b.isSolid for o in d.rootComponent.allOccurrences for b in o.component.bRepBodies),
          "hidden": [n for n, o in occ.items() if not o.isVisible], "images": saved, "archive": ARCHIVE}
