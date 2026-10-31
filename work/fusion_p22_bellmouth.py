import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
OLD_P22 = "P22_CPAP_Lower_Plenum_Wide_Jets_Face_Mounts_R41_REVIEW"
NEW = (("f41_p22_bellmouth.step", "P22 bell-mouth jets (latest)", 17381.17),
       ("f41_p22_bellmouth_section_y22.step", "P22 bell-mouth jets, section at Y22.2", 16898.56))

doc = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"][0]
doc.activate()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
root = d.rootComponent

for o in list(root.occurrences):                     # earlier runs of this script
    if o.component.name.startswith("P22 bell-mouth"):
        o.deleteMe()

old = [o for o in root.allOccurrences if o.name.split(":")[0] == OLD_P22]
if len(old) != 1:
    raise RuntimeError(f"old P22: {len(old)} occurrences")
old = old[0]
old_body = old.component.bRepBodies.item(0)
look = old_body.appearance or old.appearance


def import_step(fname, label, expected):
    n0 = root.occurrences.count
    if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(os.path.join(FILES, fname)), root):
        raise RuntimeError(f"{fname} import failed")
    if root.occurrences.count != n0 + 1:
        raise RuntimeError(f"{fname}: {root.occurrences.count - n0} new occurrences")
    occ = root.occurrences.item(root.occurrences.count - 1)
    occ.component.name = label
    bodies = [b for o in [occ] + list(occ.childOccurrences) for b in o.component.bRepBodies]
    if len(bodies) != 1:
        raise RuntimeError(f"{fname}: {len(bodies)} bodies")
    vol = bodies[0].getPhysicalProperties(adsk.fusion.CalculationAccuracy.VeryHighCalculationAccuracy).volume * 1000
    if abs(vol - expected) > 0.1:
        raise RuntimeError(f"{fname}: volume {vol:.2f} vs {expected}")
    if look:
        bodies[0].appearance = look
    return occ, round(vol, 2)


full, v_full = import_step(*NEW[0])
section, v_sec = import_step(*NEW[1])
old.isLightBulbOn = False


def shot(file, eye, target, extent, perspective=False):
    for _ in range(2):
        cam = app.activeViewport.camera
        cam.cameraType = (adsk.core.CameraTypes.PerspectiveCameraType if perspective
                          else adsk.core.CameraTypes.OrthographicCameraType)
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = adsk.core.Point3D.create(*eye)
        cam.target = adsk.core.Point3D.create(*target)
        cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
        cam.viewExtents = extent
        app.activeViewport.camera = cam
        app.activeViewport.refresh()
        adsk.doEvents()
    return app.activeViewport.saveAsImageFile(os.path.join(FILES, file), 1600, 1000)


# Fusion works in cm. Section: only the cut P22, seen from the front at the cut face (Y22.2).
full.isLightBulbOn = False
leaves = [o for o in root.allOccurrences if o.childOccurrences.count == 0 and o.isLightBulbOn and o != section]
for o in leaves:
    o.isLightBulbOn = False
saved = {"section": shot("f41_bm_section.png", (0.0, 20.0, -6.4), (0.0, 2.22, -6.4), 3.4),
         "jet_close": shot("f41_bm_jet_close.png", (1.1, 20.0, -7.42), (1.1, 2.22, -7.42), 0.75),
         "section_angle": shot("f41_bm_section_angle.png", (6.0, 12.0, -10.5), (0.9, 2.0, -7.3), 1.6)}
for o in leaves:
    o.isLightBulbOn = True
section.isLightBulbOn = False
full.isLightBulbOn = True
saved["overall"] = shot("f41_bm_overall.png", (11.0, 15.0, -4.0), (0.0, 0.5, -3.5), 13.0)

# Leave the whole carriage with the latest P22, from the front.
cam = app.activeViewport.camera
cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
cam.isSmoothTransition = False
cam.target = adsk.core.Point3D.create(0.0, 0.5, -3.5)
cam.eye = adsk.core.Point3D.create(16.0, 24.0, 2.0)
cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
cam.isFitView = True
app.activeViewport.camera = cam
app.activeViewport.refresh()
result = {"document": doc.name, "new_p22_mm3": v_full, "section_mm3": v_sec, "old_hidden": not old.isLightBulbOn,
          "appearance": look.name if look else None, "images": saved}
