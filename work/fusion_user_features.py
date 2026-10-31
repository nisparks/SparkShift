import adsk.core, adsk.fusion, os, json

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\fusion_user_edit"
doc = app.activeDocument
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
root = d.rootComponent
occ = next(o for o in root.allOccurrences if o.fullPathName.endswith("R43_RedLizard_P22:1"))
comp = occ.component
body = comp.bRepBodies.item(0)
info = {"occ": occ.fullPathName}
m = occ.transform2 if hasattr(occ, "transform2") else occ.transform
info["occ_transform_translation_mm"] = [round(m.translation.x * 10, 3), round(m.translation.y * 10, 3), round(m.translation.z * 10, 3)]
parent = occ.assemblyContext
info["parent"] = parent.fullPathName if parent else None
if parent:
    pm = parent.transform2 if hasattr(parent, "transform2") else parent.transform
    info["parent_translation_mm"] = [round(pm.translation.x * 10, 3), round(pm.translation.y * 10, 3), round(pm.translation.z * 10, 3)]
bb = body.boundingBox
info["body_bbox_native_mm"] = [round(v * 10, 3) for v in (bb.minPoint.x, bb.minPoint.y, bb.minPoint.z, bb.maxPoint.x, bb.maxPoint.y, bb.maxPoint.z)]
proxy = body.createForAssemblyContext(occ)
bw = proxy.boundingBox
info["body_bbox_world_mm"] = [round(v * 10, 3) for v in (bw.minPoint.x, bw.minPoint.y, bw.minPoint.z, bw.maxPoint.x, bw.maxPoint.y, bw.maxPoint.z)]


def pt(p):
    return [round(p.x * 10, 3), round(p.y * 10, 3), round(p.z * 10, 3)]


def curve_rows(sk):
    rows = []
    for c in sk.sketchCurves:
        t = c.objectType.split("::")[-1]
        g = c.worldGeometry
        r = {"type": t, "construction": c.isConstruction}
        try:
            r["start"], r["end"] = pt(g.startPoint), pt(g.endPoint)
        except Exception:
            pass
        try:
            r["center"], r["radius_mm"] = pt(g.center), round(g.radius * 10, 3)
        except Exception:
            pass
        rows.append(r)
    return rows


feats = []
for i in range(comp.features.count):
    f = comp.features.item(i)
    t = f.objectType.split("::")[-1]
    r = {"name": f.name, "type": t}
    try:
        tli = f.timelineObject
        r["timeline_index"] = tli.index if tli else None
    except Exception:
        pass
    if t == "ExtrudeFeature":
        e = adsk.fusion.ExtrudeFeature.cast(f)
        r["operation"] = int(e.operation)
        try:
            prof = e.profile
            profs = [prof] if not hasattr(prof, "count") else [prof.item(k) for k in range(prof.count)]
            sk = profs[0].parentSketch
            r["sketch"] = sk.name
            pl = sk.referencePlane
            r["sketch_plane"] = pl.objectType.split("::")[-1]
            tr = sk.transform
            r["sketch_origin_mm"] = pt(sk.origin) if hasattr(sk, "origin") else None
            r["sketch_xdir"] = [round(sk.xDirection.x, 4), round(sk.xDirection.y, 4), round(sk.xDirection.z, 4)]
            r["sketch_ydir"] = [round(sk.yDirection.x, 4), round(sk.yDirection.y, 4), round(sk.yDirection.z, 4)]
            r["profile_areas_mm2"] = [round(p.areaProperties().area * 100, 3) for p in profs]
            r["profile_bbox_world_mm"] = []
            for p in profs:
                b = p.boundingBox
                r["profile_bbox_world_mm"].append(pt(b.minPoint) + pt(b.maxPoint))
            r["sketch_curves"] = curve_rows(sk)
        except Exception as ex:
            r["profile_error"] = str(ex)
        try:
            ext = e.extentOne
            r["extent_one"] = ext.objectType.split("::")[-1]
            if hasattr(ext, "distance"):
                r["distance_mm"] = round(ext.distance.value * 10, 3)
        except Exception as ex:
            r["extent_error"] = str(ex)
        try:
            r["has_two_extents"] = e.hasTwoExtents
            if e.hasTwoExtents:
                r["distance_two_mm"] = round(e.extentTwo.distance.value * 10, 3)
        except Exception:
            pass
        try:
            r["start_extent"] = e.startExtent.objectType.split("::")[-1]
        except Exception:
            pass
        try:
            r["faces_created"] = len(e.faces)
            r["created_faces_bbox_mm"] = []
            for k in range(e.faces.count):
                b = e.faces.item(k).boundingBox
                r["created_faces_bbox_mm"].append(pt(b.minPoint) + pt(b.maxPoint))
        except Exception as ex:
            r["faces_error"] = str(ex)
    elif t == "FilletFeature":
        fl = adsk.fusion.FilletFeature.cast(f)
        try:
            sets = []
            for k in range(fl.edgeSets.count):
                es = fl.edgeSets.item(k)
                s = {"type": es.objectType.split("::")[-1]}
                try:
                    s["radius_mm"] = round(es.radius.value * 10, 3)
                except Exception:
                    pass
                try:
                    s["tangent_chain"] = es.isTangentChain
                except Exception:
                    pass
                try:
                    edges = es.edges
                    s["edges"] = [{"len_mm": round(edges.item(j).length * 10, 3),
                                   "start": pt(edges.item(j).startVertex.geometry) if edges.item(j).startVertex else None,
                                   "end": pt(edges.item(j).endVertex.geometry) if edges.item(j).endVertex else None,
                                   "geom": edges.item(j).geometry.objectType.split("::")[-1]}
                                  for j in range(edges.count)]
                except Exception as ex:
                    s["edges_error"] = str(ex)
                sets.append(s)
            r["edge_sets"] = sets
        except Exception as ex:
            r["fillet_error"] = str(ex)
        try:
            r["faces_created_bbox_mm"] = [pt(fl.faces.item(k).boundingBox.minPoint) + pt(fl.faces.item(k).boundingBox.maxPoint)
                                          for k in range(fl.faces.count)]
        except Exception as ex:
            r["faces_error"] = str(ex)
    elif t == "DeleteFaceFeature":
        df = f
        r["attrs"] = [a for a in dir(df) if not a.startswith("_")][:80]
        for a in ("deletedFaces", "faces", "inputFaces"):
            try:
                v = getattr(df, a)
                r[a] = [{"bbox_mm": pt(v.item(k).boundingBox.minPoint) + pt(v.item(k).boundingBox.maxPoint),
                         "area_mm2": round(v.item(k).area * 100, 3),
                         "geom": v.item(k).geometry.objectType.split("::")[-1]} for k in range(v.count)]
            except Exception as ex:
                r[a + "_error"] = str(ex)[:120]
    feats.append(r)
info["features"] = feats
# export the edited body's component as STEP (component coordinates) for comparison with the R43 STEP
step = os.path.join(OUT, "user_r43_redlizard_p22.step")
em = d.exportManager
ok = em.execute(em.createSTEPExportOptions(step, comp))
info["step_export"] = ok
info["step_size"] = os.path.getsize(step) if os.path.exists(step) else None
json.dump(info, open(os.path.join(OUT, "features.json"), "w"), indent=1)
result = {"saved": os.path.join(OUT, "features.json"), "n_features": len(feats), "step": info["step_size"],
          "bbox_native": info["body_bbox_native_mm"], "bbox_world": info["body_bbox_world_mm"],
          "occ_t": info["occ_transform_translation_mm"]}
