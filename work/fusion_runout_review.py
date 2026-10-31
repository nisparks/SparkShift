import adsk.core, adsk.fusion, os

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
OUT = FILES + r"\fusion_r43b"
TITLE = "43b CPAP outlet: revision 41 and 43 P22 after the review (native review)"
NEW = {"Jet_Runout_Proposed": FILES + r"\fusion_user_edit\Jet_Runout_Proposed.step",
       "P22_R43_Runout_Proposed": FILES + r"\fusion_user_edit\P22_R43_Runout_Proposed.step"}
os.makedirs(OUT, exist_ok=True)

# Only the 43b review document is touched; the user's "43 CPAP outlet: ..." document (manual edits) is left alone.
doc = next((d0 for d0 in app.documents if d0.name == TITLE), None)
if doc is None:
    raise RuntimeError("43b review document not open")
doc.activate()
adsk.doEvents()
d = adsk.fusion.Design.cast(doc.products.itemByProductType("DesignProductType"))
root = d.rootComponent


def all_bodies():
    out = [(None, root.bRepBodies.item(i)) for i in range(root.bRepBodies.count)]
    for o in root.allOccurrences:
        out += [(o, o.component.bRepBodies.item(i)) for i in range(o.component.bRepBodies.count)]
    return out


def min_x_mm(o, b):
    return (b if o is None else b.createForAssemblyContext(o)).boundingBox.minPoint.x * 10


# re-runs replace the earlier imports (anything at X > 260 mm)
for o in list(root.occurrences):
    bodies = [o.component.bRepBodies.item(i) for i in range(o.component.bRepBodies.count)]
    if bodies and all(min_x_mm(o, b) > 260.0 for b in bodies):
        o.deleteMe()
for o, b in all_bodies():
    if o is None and min_x_mm(o, b) > 260.0:
        b.deleteMe()
for name, path in NEW.items():
    if not app.importManager.importToTarget(app.importManager.createSTEPImportOptions(path), root):
        raise RuntimeError(f"{path} import failed")
adsk.doEvents()

green = None
for lib_name in ("Fusion Appearance Library", "Fusion 360 Appearance Library"):
    lib = app.materialLibraries.itemByName(lib_name)
    if lib:
        for ap_name in ("Paint - Enamel Glossy (Green)", "Plastic - Glossy (Green)", "Paint - Metal Flake (Green)"):
            src = lib.appearances.itemByName(ap_name)
            if src:
                green = d.appearances.itemByName(ap_name) or d.appearances.addByCopy(src, ap_name)
                break
    if green:
        break
new = []
for o, b in all_bodies():
    x = min_x_mm(o, b)
    if x > 260.0:
        if green:
            b.appearance = green
        new.append((o.name if o else "(root)", b.name, round(x, 1),
                    round(b.getPhysicalProperties(adsk.fusion.CalculationAccuracy.HighCalculationAccuracy).volume * 1000, 1)))
if len(new) != 2:
    raise RuntimeError(f"run-out bodies: {new}")

vp = app.activeViewport


def camera(target_mm, direction, extent_cm, up=(0, 0, 1), dist=40.0):
    t = adsk.core.Point3D.create(*(v / 10 for v in target_mm))
    n = sum(c * c for c in direction) ** 0.5
    e = adsk.core.Point3D.create(*(tv + dist * c / n for tv, c in zip((t.x, t.y, t.z), direction)))
    for _ in range(2):
        cam = vp.camera
        cam.cameraType = adsk.core.CameraTypes.OrthographicCameraType
        cam.isFitView = False
        cam.isSmoothTransition = False
        cam.eye = e
        cam.target = t
        cam.upVector = adsk.core.Vector3D.create(*up)
        cam.viewExtents = extent_cm
        vp.camera = cam
        vp.refresh()
        adsk.doEvents()
    return vp.camera


def add_view(cam, name):
    for i in range(d.namedViews.count - 1, -1, -1):
        if d.namedViews.item(i).name == name:
            d.namedViews.item(i).deleteMe()
    try:
        d.namedViews.add(cam, name)
    except Exception:
        pass


shots = {}
# The left jet's wall seen from its side channel, slightly from below: the same camera on each cut-away
for tag, dx in (("v1", 200.0), ("full", 240.0), ("runout", 280.0)):
    cam = camera((dx - 12.0, 21.5, -72.6), (-1.0, 0.0, -0.3), 1.9)
    vp.saveAsImageFile(os.path.join(OUT, f"jet_side_{tag}.png"), 1400, 1000)
    shots[f"jet_side_{tag}"] = cam
# and from below and in front, looking back along the wall's bottom edge
for tag, dx in (("v1", 200.0), ("full", 240.0), ("runout", 280.0)):
    cam = camera((dx - 11.2, 24.5, -73.2), (-0.8, 1.0, -0.75), 1.25)
    vp.saveAsImageFile(os.path.join(OUT, f"jet_oblique_{tag}.png"), 1400, 1000)
    shots[f"jet_oblique_{tag}"] = cam
# the whole proposed P22, from below and in front
cam = camera((340.0, 6.0, -66.0), (0.45, 1.0, -0.8), 7.5)
vp.saveAsImageFile(os.path.join(OUT, "runout_whole.png"), 1400, 1000)
shots["runout_whole"] = cam

add_view(shots["jet_side_runout"], "10a Proposed run-out (green, X+280): left jet from its side channel, front wall at left")
add_view(shots["jet_oblique_runout"], "10b Proposed run-out: from below and in front, along the wall's bottom edge")
add_view(shots["jet_oblique_full"], "10c Full-length round (X+240), same view")
add_view(shots["jet_oblique_v1"], "10d First version (X+200), same view")
add_view(shots["runout_whole"], "10e Proposed run-out P22 (green, X+340)")
camera((280.0 - 11.2, 24.5, -73.2), (-0.8, 1.0, -0.75), 1.25)
result = {"active": app.activeDocument.name, "new_bodies": new, "green": bool(green), "shots": sorted(shots)}
