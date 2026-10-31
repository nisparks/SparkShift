import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
ui = app.userInterface
doc = app.activeDocument
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
vp = app.activeViewport
cam = vp.camera
W, H = vp.width, vp.height
vp.saveAsImageFile(os.path.join(FILES, "user_view.png"), W, H)

sel = []
for i in range(ui.activeSelections.count):
    e = ui.activeSelections.item(i).entity
    if e is None:
        sel.append({"type": None})
        continue
    row = {"type": e.objectType}
    for attr in ("name",):
        try:
            row[attr] = getattr(e, attr)
        except Exception:
            pass
    try:
        row["body"] = e.body.name
    except Exception:
        pass
    try:
        row["occurrence"] = e.assemblyContext.fullPathName if e.assemblyContext else None
    except Exception:
        pass
    sel.append(row)

eye, tgt = cam.eye, cam.target
view = adsk.core.Vector3D.create(tgt.x - eye.x, tgt.y - eye.y, tgt.z - eye.z)
view.normalize()
ortho = cam.cameraType == adsk.core.CameraTypes.OrthographicCameraType
root = d.rootComponent
legend, grid = {}, []
NX, NY = 48, 36
for j in range(NY):
    line = ""
    for i in range(NX):
        sx, sy = (i + 0.5) * W / NX, (j + 0.5) * H / NY
        p = vp.viewToModelSpace(adsk.core.Point2D.create(sx, sy))
        if ortho:
            direction = view.copy()
            origin = adsk.core.Point3D.create(p.x - view.x * 100, p.y - view.y * 100, p.z - view.z * 100)
        else:
            direction = adsk.core.Vector3D.create(p.x - eye.x, p.y - eye.y, p.z - eye.z)
            direction.normalize()
            origin = eye
        hits = adsk.core.ObjectCollection.create()
        faces = root.findBRepUsingRay(origin, direction, adsk.fusion.BRepEntityTypes.BRepFaceEntityType, 0.0001, True, hits)
        if faces.count == 0:
            line += "."
            continue
        # nearest hit to the ray origin
        best, bd = None, None
        for k in range(faces.count):
            hp = hits.item(k)
            dist = origin.distanceTo(hp)
            if bd is None or dist < bd:
                best, bd = (faces.item(k), hp), dist
        f, hp = best
        occ = f.assemblyContext.fullPathName if f.assemblyContext else "(root)"
        key = f"{occ} | {f.body.name}"
        if key not in legend:
            legend[key] = chr(ord("A") + len(legend)) if len(legend) < 26 else chr(ord("a") + len(legend) - 26)
        line += legend[key]
    grid.append(line)
result = {"document": doc.name, "viewport_px": [W, H], "ortho": ortho,
          "eye_cm": [round(eye.x, 3), round(eye.y, 3), round(eye.z, 3)],
          "target_cm": [round(tgt.x, 3), round(tgt.y, 3), round(tgt.z, 3)],
          "extents_cm": round(cam.viewExtents, 3), "selection": sel,
          "legend": {v: k for k, v in legend.items()}, "grid": grid}
