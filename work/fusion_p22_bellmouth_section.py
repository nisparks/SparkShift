import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
doc = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"][0]
doc.activate()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
root = d.rootComponent
section = [o for o in root.occurrences if o.component.name == "P22 bell-mouth jets, section at Y22.2"][0]
full = [o for o in root.occurrences if o.component.name == "P22 bell-mouth jets (latest)"][0]
body = section.component.bRepBodies.item(0)

cut_look = d.appearances.itemByName("Section cut")
if cut_look is None:
    cut_look = d.appearances.addByCopy(body.appearance, "Section cut")
    adsk.core.ColorProperty.cast(cut_look.appearanceProperties.itemByName("Color")).value = \
        adsk.core.Color.create(96, 106, 120, 255)
cut_faces = 0
for f in body.faces:
    g = f.geometry
    if isinstance(g, adsk.core.Plane) and abs(abs(g.normal.y) - 1) < 1e-6 and abs(f.pointOnFace.y - 2.22) < 1e-4:
        f.appearance = cut_look
        cut_faces += 1


def shot(file, eye, target, extent):
    for _ in range(2):
        cam = app.activeViewport.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
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


full.isLightBulbOn = False
section.isLightBulbOn = True
leaves = [o for o in root.allOccurrences if o.childOccurrences.count == 0 and o.isLightBulbOn and o != section]
for o in leaves:
    o.isLightBulbOn = False
# Looking from the front (+Y) at the cut: screen right is -X.
saved = {"both_jets": shot("f41_bm_section_both.png", (0.0, 20.0, -7.2), (0.0, 2.22, -7.2), 1.9),
         "right_jet": shot("f41_bm_section_right.png", (1.08, 20.0, -7.43), (1.08, 2.22, -7.43), 0.62),
         "angle": shot("f41_bm_section_angle2.png", (7.0, 13.0, -11.5), (1.0, 2.0, -7.35), 1.5)}
for o in leaves:
    o.isLightBulbOn = True
section.isLightBulbOn = False
full.isLightBulbOn = True

cam = app.activeViewport.camera
cam.cameraType = adsk.core.CameraTypes.PerspectiveCameraType
cam.isSmoothTransition = False
cam.target = adsk.core.Point3D.create(0.0, 0.5, -3.5)
cam.eye = adsk.core.Point3D.create(16.0, 24.0, 2.0)
cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
cam.isFitView = True
app.activeViewport.camera = cam
app.activeViewport.refresh()
result = {"cut_faces": cut_faces, "images": saved}
