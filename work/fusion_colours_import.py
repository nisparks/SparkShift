import adsk.core, adsk.fusion, json, time

STEP_PATH = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\print_colour_review.step"
t0 = time.time()
for d0 in list(app.documents):
    if d0.name.startswith("SparkShift print colours"):
        d0.close(False)
doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "SparkShift print colours"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("STEP import failed")
occs = list(d.rootComponent.allOccurrences)
bodies = sum(o.component.bRepBodies.count for o in occs) + d.rootComponent.bRepBodies.count


def rgb(a):
    if a is None:
        return None
    p = a.appearanceProperties.itemByName("Color")
    if p is None:
        return a.name
    c = adsk.core.ColorProperty.cast(p).value
    return "#%02X%02X%02X" % (c.red, c.green, c.blue)


groups = {}
for o in d.rootComponent.occurrences:
    for c in o.childOccurrences:
        b = c.boundingBox
        groups[c.name] = [round(v * 10, 1) for v in (b.minPoint.x, b.maxPoint.x, b.minPoint.y, b.maxPoint.y, b.minPoint.z, b.maxPoint.z)]
samples = {}
for o in occs:
    n = o.name.split(":")[0]
    if n.startswith(("P0", "P1", "P2", "body", "P18", "P26", "Upper_Snap", "EBB42", "Beacon")) and n not in samples:
        comp = o.component
        if comp.bRepBodies.count:
            samples[f"{o.fullPathName}"] = {"body": rgb(comp.bRepBodies.item(0).appearance), "occ": rgb(o.appearance)}
result = {"bodies": bodies, "occurrences": len(occs), "components": d.allComponents.count, "seconds": round(time.time() - t0, 1),
          "top": [o.name for o in d.rootComponent.occurrences], "groups": groups, "samples": dict(list(samples.items())[:60])}
