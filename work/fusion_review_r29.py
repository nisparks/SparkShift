import adsk.core, adsk.fusion

ARCHIVE = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\29_Bambu_Clean_Rebuild_Review.f3d"
IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect"
EXPECTED_MM3 = 14455.672883796635

opened = app.importManager.importToNewDocument(app.importManager.createFusionArchiveImportOptions(ARCHIVE))
opened.name = "29 Bambu - Clean rebuild (native review)"
d = adsk.fusion.Design.cast(opened.products.itemByProductType("DesignProductType"))
occ = {o.name.split(":")[0]: o for o in d.rootComponent.allOccurrences}
prints = [b for b in occ["R29_Bambu_Print"].component.bRepBodies]
if len(prints) != 1:
    raise RuntimeError("Expected one R29 printed body")
vol = prints[0].getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000
if abs(vol - EXPECTED_MM3) > 0.01:
    raise RuntimeError(f"Native R29 volume mismatch: {vol}")


def show(name, on):
    occ[name].isLightBulbOn = on


def shot(file, eye, target, extent):
    cam = app.activeViewport.camera
    cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
    cam.isFitView = False
    cam.eye = adsk.core.Point3D.create(*eye)
    cam.target = adsk.core.Point3D.create(*target)
    cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
    cam.viewExtents = extent
    app.activeViewport.camera = cam
    app.activeViewport.refresh()
    return app.activeViewport.saveAsImageFile(IMAGES + "\\" + file, 1400, 1050)


saved = {}
show("R22_Baseline_Print_compare", False)
show("Dock_reference", False)
saved["a_plusX_fan"] = shot("f29_a_plusX_fan.png", (30, 3.2, -1.8), (1.0, 2.5, -2.6), 5.5)
show("Fan_2510", False); show("Fan_Screws_M2p5x14", False)
saved["b_plusX_nofan"] = shot("f29_b_plusX_nofan.png", (30, 3.2, -1.8), (1.0, 2.5, -2.6), 5.5)
show("Carriage_Core_reference", False); show("CPAP_Probe_EBB42_Mounts_reference", False)
saved["c_minusX_below"] = shot("f29_c_minusX_below.png", (-25, -9, -12), (0.0, 2.5, -2.6), 4.5)
saved["d_front_right_below"] = shot("f29_d_front_right_below.png", (22, 22, -12), (0.6, 3.0, -2.5), 4.5)
saved["e_front"] = shot("f29_e_front.png", (6, 30, -2), (0.0, 3.4, -2.4), 4.5)
show("Carriage_Core_reference", True); show("CPAP_Probe_EBB42_Mounts_reference", True)
show("Fan_2510", True); show("Fan_Screws_M2p5x14", True)
result = {"document": opened.name, "native_print_volume_mm3": vol,
          "bodies": sum(o.component.bRepBodies.count for o in d.rootComponent.allOccurrences),
          "all_solid": all(b.isSolid for o in d.rootComponent.allOccurrences for b in o.component.bRepBodies),
          "hidden_by_default": [n for n, o in occ.items() if not o.isLightBulbOn], "images": saved}
