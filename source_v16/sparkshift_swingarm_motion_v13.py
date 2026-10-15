"""Geometry-preserving cam/arm preview, separate from the closed-arm feed model."""

import hashlib
import importlib.util
import json
import math
import sys
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "sparkshift_swingarm_motion_v13"
STATE = {}
REFERENCES = ("MOTION_ONLY_CAM_GUIDE", "MOTION_ONLY_FOLLOWER_REFERENCE")
GUIDE_RELATION = "SWING_ARM_CAM_ANIMATION_GUIDE"


def load(name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2) + "\n")


def require_review(app):
    if not STATE or app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate only the owned native motion document")


def bodies(app):
    design = adsk.fusion.Design.cast(app.activeProduct)
    return {b.name: b for b in load("pancake_paths_study").proxies(design.rootComponent)}


def physical_stats(app):
    by = bodies(app)
    stats = load("sparkshift_cam_v8").stats
    return {name: stats(by[name]) for name in STATE["before"]}


def guard_physical_snapshot(app, phase):
    current = physical_stats(app)
    stats = load("sparkshift_cam_v8").stats
    statistics_changed = [name for name, body in STATE["before"].items()
                          if current[name] != stats(body)]
    changed, comparisons = [], []
    if statistics_changed:
        by = bodies(app)
        manager = adsk.fusion.TemporaryBRepManager.get()
        helper = STATE.get("exact_readback_helper")
        if helper is None:
            helper = sys.modules["sparkshift_corruption_v11"].STATE["exact_readback_helper"]

        def volume(body):
            value = body.volume * 1000
            if not math.isfinite(value) or value < 0:
                raise RuntimeError("Invalid native geometry-difference volume")
            return value

        for name in statistics_changed:
            definitions = STATE.get("before_part_definitions")
            if definitions is not None:
                first = definitions[name]
                second = manager.copy(by[name].nativeObject or by[name])
            else:
                first, second = STATE["before"][name], manager.copy(by[name])
            diagnostics = []
            removed = helper.exact_native_difference(
                manager, first, second, volume, diagnostics)
            added = helper.exact_native_difference(
                manager, second, first, volume, diagnostics)
            comparisons.append({"name": name, "removed_mm3": removed,
                                "added_mm3": added, "diagnostics": diagnostics,
                                "comparison_space": ("unplaced_component_definition"
                                                     if definitions is not None else "world")})
            if removed or added:
                changed.append(name)
    write("physical_snapshot_" + phase + ".json",
          {"phase": phase, "changed": changed, "original_body_count": len(current),
           "statistics_changed": statistics_changed,
           "native_exact_comparisons": comparisons})
    if changed:
        raise RuntimeError("The frozen physical snapshot changed: " + str(changed))


def rigid_group(root, name, occurrences):
    if any(g.name == name for g in root.allRigidGroups):
        raise RuntimeError("The owned rigid group already exists: " + name)
    collection = adsk.core.ObjectCollection.create()
    for occurrence in occurrences:
        collection.add(occurrence)
    group = root.rigidGroups.add(collection, False)
    if group is None:
        raise RuntimeError("Could not create the native rigid group: " + name)
    group.name = name
    return group


def wire_rigidity(app):
    require_review(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    parents = {o.name[:2]: o for o in root.occurrences if o.name[:2].isdigit()}
    added = []
    for key, anchor_name in (("05", "PRINT_carrier_box_left"),
                             ("10", "PRINT_DIRECT_CAM")):
        parent = parents[key]
        covered = {o.fullPathName for g in parent.component.rigidGroups
                   if not g.isSuppressed for o in g.occurrences}
        missing = [o for o in parent.childOccurrences if o.fullPathName not in covered]
        if not missing:
            raise RuntimeError("The frozen incomplete subassembly has changed: " + key)
        anchor = next(o for o in parent.childOccurrences
                      if any(b.name == anchor_name for b in o.bRepBodies))
        group = rigid_group(root, "RIGID_COMPLETE_" + key, [anchor, *missing])
        added.append({"name": group.name,
                      "members": [o.fullPathName for o in group.occurrences]})
    write("final_native_rigidity.json", {"groups": added})
    return added


def configure_controls(app):
    require_review(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    for name in ("J_C", "J_CAM"):
        joint = root.joints.itemByName(name)
        joint.isLocked = False
        joint.jointMotion.rotationLimits.isRestValueEnabled = False
        if joint.isLocked or joint.jointMotion.rotationLimits.isRestValueEnabled:
            raise RuntimeError("The native motion control is not free: " + name)
    root.joints.itemByName("J_SC").isSuppressed = True
    root.motionLinks.itemByName("CLAMPED_HOB_14_37").isSuppressed = True
    root.joints.itemByName("J_S_R").isLocked = False
    if not root.joints.itemByName("J_TOOL_Y").isLocked:
        raise RuntimeError("The inherited tool-withdrawal lock changed")


def set_motion_mode(app, mode):
    require_review(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    if mode not in ("release", "feed"):
        raise ValueError("Use release or feed")
    if any(abs(math.remainder(root.joints.itemByName(n).jointMotion.rotationValue,
                              2 * math.pi)) > math.radians(.0001)
           for n in ("J_C", "J_CAM")):
        raise RuntimeError("Switch motion modes only at the original closed pose")
    if mode == "release":
        configure_controls(app)
    else:
        root.joints.itemByName("J_C").isLocked = True
        root.joints.itemByName("J_CAM").isLocked = True
        root.joints.itemByName("J_SC").isSuppressed = False
        root.motionLinks.itemByName("CLAMPED_HOB_14_37").isSuppressed = False
        root.joints.itemByName("J_S_R").isLocked = False
    root.attributes.add("SparkShiftMotion", "mode", mode)


def wire_motion_guide(app):
    require_review(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    if root.tangentRelationships.count or any(n in bodies(app) for n in REFERENCES):
        raise RuntimeError("Reference installation has already started")
    receipt = json.loads((OUT / "native_motion_reference_solids_receipt.json").read_text())
    profile = json.loads((OUT / "motion_guide_profile.json").read_text())
    path = Path(receipt["file"])
    if (receipt["source_sha256"] != STATE["input_sha256"]
            or hashlib.sha256(path.read_bytes()).hexdigest() != receipt["sha256"]
            or hashlib.sha256((OUT / "motion_guide_profile.json").read_bytes()).hexdigest()
            != receipt["guide_profile_sha256"]):
        raise RuntimeError("The exact native reference solids are not source-bound")
    manager = adsk.fusion.TemporaryBRepManager.get()
    shapes = manager.createFromFile(str(path))
    if shapes is None or shapes.count != 2:
        raise RuntimeError("The two exact native motion references are missing")
    parents = {o.name[:2]: o for o in root.occurrences if o.name[:2].isdigit()}
    STATE["reference_occurrences"] = []
    for index, (key, name, anchor) in enumerate((
        ("10", REFERENCES[0], "PRINT_DIRECT_CAM"),
        ("05", REFERENCES[1], "PRINT_carrier_box_left"),
    )):
        shape = shapes.item(index)
        if not shape.isSolid or not math.isfinite(shape.volume) or shape.volume <= 0:
            raise RuntimeError("The non-printing reference is not a valid native solid")
        occurrence = parents[key].component.occurrences.addNewComponent(
            adsk.core.Matrix3D.create())
        occurrence.component.name = name
        feature = occurrence.component.features.baseFeatures.add()
        feature.name = name
        if not feature.startEdit():
            raise RuntimeError("Could not edit the reference component")
        occurrence.component.bRepBodies.add(shape, feature)
        if not feature.finishEdit():
            raise RuntimeError("Could not finish the reference component")
        adsk.doEvents()
        if feature.bodies.count != 1:
            raise RuntimeError("The reference component must contain exactly one body")
        body = feature.bodies.item(0)
        body.name = name
        body.isLightBulbOn = False
        body.attributes.add("SparkShiftMotion", "purpose",
                            "NON_PRINTING_ANIMATION_REFERENCE_NOT_PHYSICAL_HARDWARE")
        proxy = occurrence.createForAssemblyContext(parents[key])
        STATE["reference_occurrences"].append(proxy)
        rigid_group(root, "RIGID_MOTION_REFERENCE_" + key,
                    [bodies(app)[anchor].assemblyContext, proxy])
        proxy.isLightBulbOn = False
    design.activateRootComponent()
    configure_controls(app)
    STATE["reference_bodies"] = list(REFERENCES)
    relation = add_guide_relationship(app, profile)
    configure_controls(app)
    result = {"relationship": relation.name, "cam_control": "J_CAM",
              "cam_range_degrees": [0, 155],
              "non_printing_reference_bodies": list(REFERENCES),
              "physical_cam_unchanged": True, "actual_follower_rotation_free": True,
              "closed_arm_feed_links_retained": True,
              "moving_hob_phase_relation_suspended_in_release_preview": True,
              "simultaneous_feed_and_release_simulated": False,
              "return_spring_force_simulated": False,
              "source_motion_fit": profile["validation"]}
    write("final_native_animation_guide.json", result)
    return result


def add_guide_relationship(app, profile):
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    configure_controls(app)
    root.joints.itemByName("J_CAM").jointMotion.rotationValue = math.radians(1)
    root.joints.itemByName("J_CAM").jointMotion.rotationValue = 0.
    if design.snapshots.hasPendingSnapshot:
        snapshot = design.snapshots.add()
        snapshot.name = "SWING_ARM_MOTION_CLOSED_READY"
    configure_controls(app)
    by = bodies(app)
    first = next(f for f in by[REFERENCES[1]].faces
                 if adsk.core.Cylinder.cast(f.geometry)
                 and abs(adsk.core.Cylinder.cast(f.geometry).radius-.5) < 1e-7)
    radius = profile["base_radius_mm"] / 10
    candidates = [f for f in by[REFERENCES[0]].faces
                  if adsk.core.Cylinder.cast(f.geometry)
                  and abs(adsk.core.Cylinder.cast(f.geometry).radius-radius) < 1e-7]
    if not candidates:
        candidates = [f for f in by[REFERENCES[0]].faces
                      if adsk.core.NurbsSurface.cast(f.geometry)]
    if not candidates:
        raise RuntimeError("The source-bound guide has no supported contact surface")
    second = min(candidates,
                 key=lambda f: app.measureManager.measureMinimumDistance(first, f).value)
    relation = root.tangentRelationships.add(
        root.tangentRelationships.createInput(first, second))
    relation.name = GUIDE_RELATION
    if relation.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError("The nonlinear native guide failed: "
                           + relation.errorOrWarningMessage)
    relation.attributes.add("SparkShiftMotion", "purpose",
                            "Non-printing kinematic return guide; no spring forces")
    return relation


def install(app):
    require_review(app)
    guard_physical_snapshot(app, "fresh_source")
    rigidity = wire_rigidity(app)
    guard_physical_snapshot(app, "rigidity")
    configure_controls(app)
    guard_physical_snapshot(app, "unlocked_controls")
    guide = wire_motion_guide(app)
    guard_physical_snapshot(app, "complete_installation")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    root.attributes.add("SparkShiftMotion", "mode", "release")
    root.attributes.add("SparkShiftMotion", "guide_notice",
                        "Two hidden non-printing reference bodies; physical cam unchanged")
    root.attributes.add("SparkShiftMotion", "feed_notice",
                        "Release preview is separate from closed-arm feed gearing")
    return {"rigidity": rigidity, "guide": guide}


def record_cam_samples(app, targets):
    require_review(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    parent = next(o for o in root.occurrences if o.name.startswith("05 "))
    profile = json.loads((OUT / "motion_guide_profile.json").read_text())
    expected = {p["cam_deg"]: p for p in profile["sampled_motion"]}
    samples = STATE.setdefault("native_samples", [])
    for target in targets:
        cam = root.joints.itemByName("J_CAM")
        if abs(cam.jointMotion.rotationValue-math.radians(target)) > 1e-10:
            cam.jointMotion.rotationValue = math.radians(target)
        matrix = parent.transform2.asArray()
        actual = math.degrees(math.atan2(matrix[2], matrix[0]))
        reference = expected[float(target)]
        row = {"requested_cam_deg": target,
               "actual_cam_deg": math.degrees(cam.jointMotion.rotationValue),
               "actual_arm_deg": actual, "guide_arm_deg": reference["guided_arm_deg"],
               "guide_error_deg": actual-reference["guided_arm_deg"],
               "physical_contact_arm_deg": reference["physical_contact_arm_deg"],
               "physical_arm_error_deg": actual-reference["physical_contact_arm_deg"]}
        samples.append(row)
        error = (abs(row["actual_cam_deg"]-target) > 1e-6
                 or abs(row["physical_arm_error_deg"]) > .03)
        if error:
            write("native_motion_samples.json", {"status": "failed", "samples": samples})
            raise RuntimeError("Native motion sample failed: " + str(row))
    write("native_motion_samples.json", {"status": "in_progress", "samples": samples})
    return {"sample_count": len(samples), "last": samples[-1],
            "maximum_native_guide_error_deg":
                max(abs(p["guide_error_deg"]) for p in samples)}


def refine_guide(app):
    require_review(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.revertPendingSnapshot()
    configure_controls(app)
    guard_physical_snapshot(app, "before_curvature_refinement")
    old_relation = root.tangentRelationships.itemByName(GUIDE_RELATION)
    if old_relation:
        old_relation.deleteMe()
        if root.tangentRelationships.itemByName(GUIDE_RELATION):
            raise RuntimeError("The old guide relationship was not removed")
    profile = json.loads((OUT / "motion_guide_profile.json").read_text())
    occurrence = next(o for o in root.allOccurrences if o.component.name == REFERENCES[0])
    component = occurrence.component
    sketch = component.sketches.add(component.xZConstructionPlane)
    sketch.name = "MOTION_ONLY_CURVATURE_PROFILE_BUILD"
    sketch.isComputeDeferred = True
    try:
        for item in profile["curves"]:
            if item["kind"] == "arc":
                cx, cz = item["centre_xz_mm"]
                radius, angle = item["radius_mm"], item["start_angle_rad"]
                centre = sketch.modelToSketchSpace(
                    adsk.core.Point3D.create(cx/10, 0, cz/10))
                start = sketch.modelToSketchSpace(adsk.core.Point3D.create(
                    (cx+radius*math.cos(angle))/10, 0,
                    (cz+radius*math.sin(angle))/10))
                x = sketch.modelToSketchSpace(
                    adsk.core.Point3D.create((cx+radius)/10, 0, cz/10))
                z = sketch.modelToSketchSpace(
                    adsk.core.Point3D.create(cx/10, 0, (cz+radius)/10))
                sign = 1 if ((x.x-centre.x)*(z.y-centre.y)
                             - (x.y-centre.y)*(z.x-centre.x)) > 0 else -1
                curve = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(
                    centre, start, sign*(item["end_angle_rad"]-angle))
            else:
                controls = [sketch.modelToSketchSpace(
                    adsk.core.Point3D.create(x/10, 0, z/10))
                    for x, z in item["controls_xz_mm"]]
                geometry = adsk.core.NurbsCurve3D.createNonRational(
                    controls, item["degree"], item["knots"], False)
                curve = sketch.sketchCurves.sketchFixedSplines.addByNurbsCurve(geometry)
            if curve is None:
                raise RuntimeError("The curvature-continuous guide sketch failed")
    finally:
        sketch.isComputeDeferred = False
    if sketch.profiles.count != 1:
        raise RuntimeError("The refined guide must have exactly one profile")
    extrude = component.features.extrudeFeatures.addSimple(
        sketch.profiles.item(0), adsk.core.ValueInput.createByReal(.4),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    extrude.name = "MOTION_ONLY_CURVATURE_GUIDE_BUILD"
    if extrude.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError("Refined guide extrusion failed: " + extrude.errorOrWarningMessage)
    manager = adsk.fusion.TemporaryBRepManager.get()
    shape = manager.copy(extrude.bodies.item(0))
    shift = adsk.core.Matrix3D.create()
    shift.translation = adsk.core.Vector3D.create(
        0, .7-(shape.boundingBox.minPoint.y+shape.boundingBox.maxPoint.y)/2, 0)
    if not manager.transform(shape, shift) or not shape.isSolid or shape.volume <= 0:
        raise RuntimeError("The refined reference solid is invalid")
    extrude.deleteMe()
    sketch.deleteMe()
    old_base = component.features.baseFeatures.itemByName(REFERENCES[0])
    if old_base is None:
        raise RuntimeError("The owned reference base feature is missing")
    old_base.deleteMe()
    if component.bRepBodies.count:
        raise RuntimeError("The old non-printing guide body was not removed")
    feature = component.features.baseFeatures.add()
    feature.name = REFERENCES[0]
    if not feature.startEdit():
        raise RuntimeError("Could not edit the refined guide base")
    component.bRepBodies.add(shape, feature)
    if not feature.finishEdit():
        raise RuntimeError("Could not finish the refined guide base")
    adsk.doEvents()
    body = feature.bodies.item(0)
    body.name = REFERENCES[0]
    body.isLightBulbOn = False
    body.attributes.add("SparkShiftMotion", "purpose",
                        "NON_PRINTING_ANIMATION_REFERENCE_NOT_PHYSICAL_HARDWARE")
    design.activateRootComponent()
    configure_controls(app)
    add_guide_relationship(app, profile)
    configure_controls(app)
    guard_physical_snapshot(app, "after_curvature_refinement")
    by = bodies(app)
    shapes = [manager.copy(by[name]) for name in REFERENCES]
    path = OUT / "native_motion_reference_solids_c2.smt"
    if not manager.exportToFile(shapes, str(path)):
        raise RuntimeError("The refined native reference checkpoint failed")
    receipt = {
        "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "body_order": list(REFERENCES), "source_sha256": STATE["input_sha256"],
        "guide_profile_sha256":
            hashlib.sha256((OUT / "motion_guide_profile.json").read_bytes()).hexdigest(),
        "volumes_mm3": [b.volume*1000 for b in shapes],
        "physical_source_geometry_not_included": True,
        "guide_continuity": "Quintic C4 spans with C2 circular-rest joins",
    }
    write("native_motion_reference_solids_receipt.json", receipt)
    return receipt


def refine_single_surface(app):
    require_review(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.revertPendingSnapshot()
    configure_controls(app)
    guard_physical_snapshot(app, "before_continuous_surface")
    relation = root.tangentRelationships.itemByName(GUIDE_RELATION)
    if relation:
        relation.deleteMe()
        if root.tangentRelationships.itemByName(GUIDE_RELATION):
            raise RuntimeError("The old guide relationship was not removed")
    profile = json.loads((OUT / "motion_guide_profile.json").read_text())
    manager = adsk.fusion.TemporaryBRepManager.get()
    wires = []
    for y in (.9, .5):
        curves = []
        for item in profile["curves"]:
            if item["kind"] == "arc":
                cx, cz = item["centre_xz_mm"]
                curve = adsk.core.Arc3D.createByCenter(
                    adsk.core.Point3D.create(cx/10, y, cz/10),
                    adsk.core.Vector3D.create(0, -1, 0),
                    adsk.core.Vector3D.create(1, 0, 0), item["radius_mm"]/10,
                    item["start_angle_rad"], item["end_angle_rad"])
            else:
                curve = adsk.core.NurbsCurve3D.createNonRational(
                    [adsk.core.Point3D.create(x/10, y, z/10)
                     for x, z in item["controls_xz_mm"]],
                    item["degree"], item["knots"], False)
            if curve is None:
                raise RuntimeError("The continuous guide curve failed")
            curves.append(curve)
        wire, _ = manager.createWireFromCurves(curves, False)
        if wire is None or wire.wires.count != 1:
            raise RuntimeError("The continuous guide wire failed")
        wires.append(wire)
    sheet = manager.createRuledSurface(wires[0].wires.item(0), wires[1].wires.item(0))
    if sheet is None or sheet.faces.count != 1:
        raise RuntimeError("The guide must have one continuous contact sheet")
    occurrence = next(o for o in root.allOccurrences if o.component.name == REFERENCES[0])
    component = occurrence.component
    build = component.features.baseFeatures.add()
    build.name = "MOTION_ONLY_CONTINUOUS_BUILD"
    if not build.startEdit():
        raise RuntimeError("Could not edit the temporary guide sheet")
    component.bRepBodies.add(sheet, build)
    if not build.finishEdit():
        raise RuntimeError("Could not finish the temporary guide sheet")
    adsk.doEvents()
    collection = adsk.core.ObjectCollection.create()
    collection.add(build.bodies.item(0))
    inp = component.features.thickenFeatures.createInput(
        collection, adsk.core.ValueInput.createByReal(-.001), False,
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation, False)
    thicken = component.features.thickenFeatures.add(inp)
    if thicken.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError("Continuous guide thickening failed: "
                           + thicken.errorOrWarningMessage)
    adsk.doEvents()
    solids = [b for b in thicken.bodies if b.isSolid]
    if len(solids) != 1 or solids[0].volume <= 0:
        raise RuntimeError("The continuous guide did not produce one native solid")
    shape = manager.copy(solids[0])
    thicken.deleteMe()
    build.deleteMe()
    old = component.features.baseFeatures.itemByName(REFERENCES[0])
    old.deleteMe()
    if component.bRepBodies.count:
        raise RuntimeError("Temporary reference geometry was not completely removed")
    feature = component.features.baseFeatures.add()
    feature.name = REFERENCES[0]
    if not feature.startEdit():
        raise RuntimeError("Could not edit the final continuous reference")
    component.bRepBodies.add(shape, feature)
    if not feature.finishEdit():
        raise RuntimeError("Could not finish the final continuous reference")
    adsk.doEvents()
    body = feature.bodies.item(0)
    body.name = REFERENCES[0]
    body.isLightBulbOn = False
    body.attributes.add("SparkShiftMotion", "purpose",
                        "NON_PRINTING_ANIMATION_REFERENCE_NOT_PHYSICAL_HARDWARE")
    design.activateRootComponent()
    configure_controls(app)
    add_guide_relationship(app, profile)
    configure_controls(app)
    guard_physical_snapshot(app, "after_continuous_surface")
    by = bodies(app)
    shapes = [manager.copy(by[name]) for name in REFERENCES]
    path = OUT / "native_motion_reference_solids_continuous.smt"
    if not manager.exportToFile(shapes, str(path)):
        raise RuntimeError("The continuous native guide checkpoint failed")
    receipt = {
        "file": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "body_order": list(REFERENCES), "source_sha256": STATE["input_sha256"],
        "guide_profile_sha256":
            hashlib.sha256((OUT / "motion_guide_profile.json").read_bytes()).hexdigest(),
        "volumes_mm3": [b.volume*1000 for b in shapes],
        "physical_source_geometry_not_included": True,
        "guide_contact_surface": "One continuous native NURBS face",
    }
    write("native_motion_reference_solids_receipt.json", receipt)
    return receipt


def verify_original_bodies(app, start=0, limit=40, key="closed_geometry_verification"):
    require_review(app)
    rows = STATE.setdefault(key, [])
    if start != len(rows):
        raise RuntimeError("Continue exact native verification from its recorded progress")
    by = bodies(app)
    if set(by) - set(STATE["before"]) != set(REFERENCES):
        raise RuntimeError("Unexpected bodies outside the frozen physical snapshot")
    manager = adsk.fusion.TemporaryBRepManager.get()
    helper = STATE.get("exact_readback_helper")
    if helper is None:
        helper = sys.modules["sparkshift_corruption_v11"].STATE["exact_readback_helper"]
    capture = json.loads((OUT / "motion_source_capture.json").read_text())
    original = next((d for d in app.documents
                     if d.creationId == capture["source_creation_id"]), None)
    if original is None:
        raise RuntimeError("The protected source is needed for exact unplaced part definitions")
    source = adsk.fusion.Design.cast(
        original.products.itemByProductType("DesignProductType"))
    original_bodies = {b.name: b for b in
                       load("pancake_paths_study").proxies(source.rootComponent)}

    def volume(body):
        value = body.volume * 1000
        if not math.isfinite(value) or value < 0:
            raise RuntimeError("Invalid exact native comparison volume")
        return value

    for name in list(STATE["before"])[start:start+limit]:
        source_world = manager.copy(original_bodies[name])
        diagnostics = []
        source_removed = helper.exact_native_difference(
            manager, STATE["before"][name], source_world, volume, diagnostics)
        source_added = helper.exact_native_difference(
            manager, source_world, STATE["before"][name], volume, diagnostics)
        if source_removed or source_added:
            raise RuntimeError("The protected original no longer matches the frozen input")
        before = manager.copy(original_bodies[name].nativeObject or original_bodies[name])
        actual = manager.copy(by[name].nativeObject or by[name])
        if not actual.isSolid or actual.volume <= 0:
            raise RuntimeError("A physical body is no longer a valid solid: " + name)
        removed = helper.exact_native_difference(
            manager, before, actual, volume, diagnostics)
        added = helper.exact_native_difference(
            manager, actual, before, volume, diagnostics)
        rows.append({"body": name, "comparison_space": "unplaced_component_definition",
                     "source_frozen_world_difference_mm3": source_removed+source_added,
                     "removed_mm3": removed, "added_mm3": added,
                     "diagnostics": diagnostics})
        write(key + ".json", {"document": STATE["document"], "parts": rows,
                             "source_sha256": STATE["input_sha256"]})
        if removed or added:
            raise RuntimeError("The physical native shape changed: " + str(rows[-1]))
    return {"verified": len(rows), "expected": len(STATE["before"]),
            "all_native_differences_exact_zero": True}


def canonical_closed_pose(app):
    require_review(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    capture = json.loads((OUT / "motion_source_capture.json").read_text())
    original = next((d for d in app.documents
                     if d.creationId == capture["source_creation_id"]), None)
    if original is None:
        raise RuntimeError("The protected original document is needed for its exact rest matrices")
    source = adsk.fusion.Design.cast(
        original.products.itemByProductType("DesignProductType"))
    reference = {o.name: o.transform2 for o in source.rootComponent.occurrences}
    changed = []
    for occurrence in design.rootComponent.occurrences:
        target = reference.get(occurrence.name)
        if target is None:
            raise RuntimeError("Unexpected top-level occurrence in the native motion copy")
        before = list(occurrence.transform2.asArray())
        if max(abs(a-b) for a, b in zip(before, target.asArray())) > 1e-14:
            occurrence.transform2 = target
            changed.append(occurrence.name)
    if design.snapshots.hasPendingSnapshot:
        snapshot = design.snapshots.add()
        snapshot.name = "EXACT_ORIGINAL_CLOSED_REST"
    configure_controls(app)
    write("canonical_closed_pose.json",
          {"protected_source_read_only": capture["source_creation_id"],
           "reset_owned_occurrence_matrices": changed})
    return changed
