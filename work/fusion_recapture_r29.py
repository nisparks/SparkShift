import adsk.core, adsk.fusion

IMAGES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect"
d = adsk.fusion.Design.cast(app.activeProduct)
if app.activeDocument.name != "29 Bambu - Clean rebuild (native review)":
    raise RuntimeError("Unexpected active document: " + app.activeDocument.name)
occ = {o.name.split(":")[0]: o for o in d.rootComponent.allOccurrences}


def set_visible(name, on):
    # Toggle through the opposite state so the viewport receives a real change event.
    occ[name].isLightBulbOn = not on
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
    adsk.doEvents()
    return app.activeViewport.saveAsImageFile(IMAGES + "\\" + file, 1400, 1050)


for name in ("R22_Baseline_Print_compare", "Dock_reference", "Fan_2510", "Fan_Screws_M2p5x14",
             "Carriage_Core_reference", "CPAP_Probe_EBB42_Mounts_reference"):
    set_visible(name, False)
saved = {
    "c_minusX_below": shot("f29_c_minusX_below.png", (-25, -9, -12), (0.0, 2.5, -2.6), 4.5),
    "d_front_right_below": shot("f29_d_front_right_below.png", (22, 22, -12), (0.6, 3.0, -2.5), 4.5),
    "e_front": shot("f29_e_front.png", (6, 30, -2), (0.0, 3.4, -2.4), 4.5),
    "b_plusX_nofan": shot("f29_b_plusX_nofan.png", (30, 3.2, -1.8), (1.0, 2.5, -2.6), 5.5),
}
for name in ("Fan_2510", "Fan_Screws_M2p5x14", "Carriage_Core_reference", "CPAP_Probe_EBB42_Mounts_reference"):
    set_visible(name, True)
saved["a_plusX_fan"] = shot("f29_a_plusX_fan.png", (30, 3.2, -1.8), (1.0, 2.5, -2.6), 5.5)
result = {"saved": saved, "state": {n: o.isVisible for n, o in occ.items()}}
