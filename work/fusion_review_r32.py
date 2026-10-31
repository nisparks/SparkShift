import adsk.core, adsk.fusion

STEP_PATH = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\32_Flush_Side_Fusion_Review.step"
ARCHIVE = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\32_Flush_Side_Review.f3d"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect"
EXPECTED = {"R32_Bambu_Print_active": 14241.8293, "R32_Bambu_Print_parked_plusX": 14241.8293,
            "R32_RedLizard_Print_parked_minusX": 8293.6822}
R32 = tuple(EXPECTED)
R30 = ("R30_Prints_compare",)
ALWAYS_HIDDEN = ("Docks_reference",)

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "32 Toolheads - flush side clearances"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R32 review STEP import failed")
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "32 Toolheads - flush side clearances (native review)"
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


def show(revision, hide=()):
    for name in occ:
        if name.startswith("32 Flush"):
            continue
        on = (name not in ALWAYS_HIDDEN and name not in hide
              and not (name in R30 and revision == 32) and not (name in R32 and revision == 30))
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


# Rear view of the +X gap (active carriage side face to the parked Bambu's non-fan side),
# the Red Lizard fan side from below with its fan hidden, then a three-bay overview.
REAR_GAP = ((2.37, -30.0, -2.4), (2.37, 1.2, -2.4), (0.0, 0.0, 1.0), 2.6)
RL_SKIN = ((-2.4, 2.2, -30.0), (-2.4, 2.2, -2.25), (0.0, 1.0, 0.0), 3.2)
OVERVIEW = ((22.0, -30.0, -16.0), (0.0, 1.5, -3.0), (0.0, 0.0, 1.0), 13.0)
saved = {}
for revision in (30, 32):
    show(revision)
    saved[f"rear_gap_r{revision}"] = shot(f"f32_rear_gap_r{revision}.png", *REAR_GAP)
    show(revision, hide=("Parked_RedLizard_parts_minusX", "R31_P22_Lowered_Mounts"))
    saved[f"rl_skin_r{revision}"] = shot(f"f32_rl_skin_r{revision}.png", *RL_SKIN)
show(32)
saved["overview_r32"] = shot("f32_overview_r32.png", *OVERVIEW)
result = {"document": opened.name, "native_volumes_mm3": volumes,
          "bodies": sum(o.component.bRepBodies.count for o in d.rootComponent.allOccurrences),
          "all_solid": all(b.isSolid for o in d.rootComponent.allOccurrences for b in o.component.bRepBodies),
          "hidden": [n for n, o in occ.items() if not o.isVisible], "images": saved, "archive": ARCHIVE}
