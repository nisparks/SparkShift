import adsk.core, adsk.fusion

STEP_PATH = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\29_Bambu_Clean_Fusion_Review.step"
ARCHIVE = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\29_Bambu_Clean_Rebuild_Review.f3d"
HIDDEN = ("R22_Baseline_Print_compare", "Dock_reference")

doc = app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
doc.name = "29 Bambu - Clean rebuild from R22"
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(STEP_PATH), d.rootComponent):
    raise RuntimeError("R29 review STEP import failed")
names = []
for o in d.rootComponent.allOccurrences:
    names.append(o.name)
    if any(o.name.startswith(h) for h in HIDDEN):
        o.isLightBulbOn = False
if not d.exportManager.execute(d.exportManager.createFusionArchiveExportOptions(ARCHIVE)):
    raise RuntimeError("Native archive export failed")
result = {"document": doc.name, "occurrences": names,
          "bodies": sum(o.component.bRepBodies.count for o in d.rootComponent.allOccurrences),
          "archive": ARCHIVE}
