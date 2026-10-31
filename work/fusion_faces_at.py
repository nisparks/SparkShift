import adsk.core, adsk.fusion

doc = app.activeDocument
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
vp = app.activeViewport
cam = vp.camera
eye = cam.eye
root = d.rootComponent
SKIP = ("Core_041",)
out = {}
for sy in range(270, 371, 10):
    for sx in range(830, 961, 10):
        p = vp.viewToModelSpace(adsk.core.Point2D.create(sx, sy))
        direction = adsk.core.Vector3D.create(p.x - eye.x, p.y - eye.y, p.z - eye.z)
        direction.normalize()
        hits = adsk.core.ObjectCollection.create()
        faces = root.findBRepUsingRay(eye, direction, adsk.fusion.BRepEntityTypes.BRepFaceEntityType, 0.0001, True, hits)
        rows = []
        for k in range(faces.count):
            f, hp = faces.item(k), hits.item(k)
            occ = f.assemblyContext.name if f.assemblyContext else "(root)"
            rows.append((eye.distanceTo(hp), occ, f, hp))
        rows.sort(key=lambda r: r[0])
        first = next((r for r in rows if not r[1].startswith(SKIP)), None)
        if first is None:
            continue
        _, occ, f, hp = first
        ok, n = f.evaluator.getNormalAtPoint(hp)
        k = f"{occ} | face {f.tempId}"
        e = out.setdefault(k, {"n": 0, "pts": [], "normal": [round(n.x, 3), round(n.y, 3), round(n.z, 3)],
                               "area_mm2": round(f.area * 100, 2), "geom": f.geometry.objectType.split("::")[-1]})
        e["n"] += 1
        e["pts"].append([round(hp.x * 10, 2), round(hp.y * 10, 2), round(hp.z * 10, 2)])
for v in out.values():
    pts = v.pop("pts")
    v["bbox_mm"] = [round(min(p[i] for p in pts), 2) for i in range(3)] + [round(max(p[i] for p in pts), 2) for i in range(3)]
result = dict(sorted(out.items(), key=lambda kv: -kv[1]["n"]))
