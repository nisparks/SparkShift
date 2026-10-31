import adsk.core, adsk.fusion, os

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\fusion_user_edit"
os.makedirs(OUT, exist_ok=True)
docs = [{"name": d0.name, "active": d0 == app.activeDocument, "modified": d0.isModified, "saved": d0.isSaved}
        for d0 in app.documents]
doc = app.activeDocument
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
info = {"documents": docs, "active": doc.name, "design_type": str(d.designType)}
tl = []
try:
    for i in range(d.timeline.count):
        it = d.timeline.item(i)
        e = it.entity
        tl.append({"i": i, "name": it.name, "type": e.objectType.split("::")[-1] if e else None,
                   "suppressed": it.isSuppressed, "group": it.isGroup})
except Exception as ex:
    tl.append({"error": str(ex)})
info["timeline_count"] = len(tl)
info["timeline_tail"] = tl[-40:]
root = d.rootComponent


def bodies_of(comp, path):
    rows = []
    for i in range(comp.bRepBodies.count):
        b = comp.bRepBodies.item(i)
        try:
            v = round(b.getPhysicalProperties(adsk.fusion.CalculationAccuracy.HighCalculationAccuracy).volume * 1000, 2)
        except Exception:
            v = None
        rows.append({"path": path, "body": b.name, "visible": b.isLightBulbOn, "solid": b.isSolid, "volume_mm3": v,
                     "faces": b.faces.count})
    return rows


rows = bodies_of(root, "(root)")
for o in root.allOccurrences:
    rows += [dict(r, occ_visible=o.isLightBulbOn) for r in bodies_of(o.component, o.fullPathName)]
info["bodies_with_p22_or_visible"] = [r for r in rows if "P22" in r["path"] or "P22" in r["body"]]
info["n_bodies"] = len(rows)
# component-level features (direct edits made inside components show here when the design is parametric)
feats = []
for o in root.allOccurrences:
    c = o.component
    try:
        n = c.features.count
    except Exception:
        n = 0
    if n:
        for i in range(n):
            f = c.features.item(i)
            feats.append({"occ": o.fullPathName, "feature": f.name, "type": f.objectType.split("::")[-1]})
info["component_features"] = feats[:80]
an = []
try:
    for i in range(d.analyses.count):
        a = d.analyses.item(i)
        an.append({"name": a.name, "type": a.objectType.split("::")[-1], "visible": a.isLightBulbOn})
except Exception as ex:
    an.append({"error": str(ex)})
info["analyses"] = an
vp = app.activeViewport
cam = vp.camera
info["camera"] = {"eye_mm": [round(cam.eye.x * 10, 2), round(cam.eye.y * 10, 2), round(cam.eye.z * 10, 2)],
                  "target_mm": [round(cam.target.x * 10, 2), round(cam.target.y * 10, 2), round(cam.target.z * 10, 2)],
                  "up": [round(cam.upVector.x, 3), round(cam.upVector.y, 3), round(cam.upVector.z, 3)],
                  "extent_cm": round(cam.viewExtents, 3), "ortho": cam.cameraType == adsk.core.CameraTypes.OrthographicCameraType}
vp.saveAsImageFile(os.path.join(OUT, "current_view.png"), 1600, 900)
result = info
