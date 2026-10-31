import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
names = [d0.name for d0 in app.documents]
out = {}
for title in ("40 P20-to-P21 screws (native review)", "SparkShift print colours", "05_SparkShift_Core_Carriage_v26j"):
    hits = [d0 for d0 in app.documents if d0.name == title]
    if not hits:
        out[title] = "not open"
        continue
    doc = hits[0]
    doc.activate()
    adsk.doEvents()
    vp = app.activeViewport
    tgt = adsk.core.Point3D.create(1.85, 3.3, -1.46)
    if title == "SparkShift print colours":
        out[title] = "skipped (assembly placed elsewhere)"
        continue
    dirn = (-0.58, 0.79, 0.19)
    n = sum(c * c for c in dirn) ** 0.5
    eye = adsk.core.Point3D.create(*(t + 12.0 * c / n for t, c in zip((tgt.x, tgt.y, tgt.z), dirn)))
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = eye
        cam.target = tgt
        cam.upVector = adsk.core.Vector3D.create(0, 0, 1)
        cam.viewExtents = 1.6
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()
    fname = "tab_" + title.split(" ")[0] + ".png"
    vp.saveAsImageFile(os.path.join(FILES, fname), 1200, 900)
    out[title] = fname
back = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"]
if back:
    back[0].activate()
result = out
