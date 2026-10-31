import adsk.core, adsk.fusion

doc = [d0 for d0 in app.documents if d0.name == "41 Carriage build fixes (native review)"][0]
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
colours = {}
for o in d.rootComponent.allOccurrences:
    if o.childOccurrences.count or o.component.bRepBodies.count == 0:
        continue
    b = o.component.bRepBodies.item(0)
    a = b.appearance or o.appearance
    name = a.name if a else None
    colours.setdefault(name, []).append(o.name.split(":")[0])
result = {k: (v if len(v) < 40 else v[:40] + [f"... {len(v)} in all"]) for k, v in colours.items()}
