"""A smooth physical cam using a 175-degree command range, in an owned copy."""

import ast
import hashlib
import importlib.util
import json
import math
import sys
import types
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "sparkshift_cam_v15"
STATE = {}


def load_file(name, path):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def exact_helper():
    paths = (
        BASE / "private-branch-review" / "source" / "CAD"
        / "YUDX_Compact_HF_CoarseSelector" / "native_probe.py",
        BASE / "private-branch-review" / "source" / "CAD"
        / "YUDX_FDM_HGX" / "CompactCam" / "publication_fusion.py",
    )
    wanted = ({"point", "extent", "overlap"}, {"exact_native_difference"})
    namespace = {"adsk": adsk}
    for path, names in zip(paths, wanted):
        tree = ast.parse(path.read_text())
        functions = [node for node in tree.body
                     if isinstance(node, ast.FunctionDef) and node.name in names]
        if {node.name for node in functions} != names:
            raise RuntimeError("The existing exact measurement helpers changed")
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), "exec"),
             namespace)
    return types.SimpleNamespace(
        exact_native_difference=namespace["exact_native_difference"])


def prepare(app):
    if STATE:
        raise RuntimeError("The smoother-cam study is already initialized")
    native = load_file("sparkshift_cam_v15_native", BASE / "sparkshift_opening_v14.py")
    native.OUT = OUT
    receipt = native.capture(app)
    STATE.update(native.STATE)
    native.STATE = STATE
    STATE["native"] = native
    STATE["exact_readback_helper"] = exact_helper()
    native.close_owned_pose(app)
    native.extract_design_input(app)
    app.activeDocument.name = "SparkShift v15 - gentle 175 degree cam - WIP"
    receipt.update(owned_document=app.activeDocument.creationId,
                   new_command_limit_degrees=175,
                   full_open_dwell_degrees=[170, 175],
                   nominal_servo_upper_margin_degrees=5,
                   original_v14_not_modified=True)
    native.write("v15_source_capture.json", receipt)
    return receipt


def restart_progressive_revision(app):
    require(app)
    if STATE.get("progressive_restart_complete"):
        raise RuntimeError("The progressive revision has already been restarted")
    old = app.activeDocument
    archive = OUT / "cad" / "Diagnostic_constant_rate_trial_NOT_FINAL.f3d"
    if archive.exists():
        raise RuntimeError("The owned diagnostic checkpoint already exists")
    if not adsk.fusion.Design.cast(app.activeProduct).exportManager.execute(
            adsk.fusion.Design.cast(app.activeProduct).exportManager
            .createFusionArchiveExportOptions(str(archive))):
        raise RuntimeError("Could not preserve the superseded constant-rate trial")
    history = OUT / "constant_rate_trial"
    history.mkdir(exist_ok=False)
    for name in ("smooth_cam_profile.json", "frozen_cam_profile.json",
                 "motion_guide_profile.json", "physical_cam_preflight.json"):
        (history / name).write_bytes((OUT / name).read_bytes())
    source = Path(STATE["input_path"])
    if hashlib.sha256(source.read_bytes()).hexdigest() != STATE["input_sha256"]:
        raise RuntimeError("The preserved v14 baseline changed")
    document = app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(source)))
    if document is None or document == old:
        raise RuntimeError("The progressive cam revision could not be isolated")
    document.name = "SparkShift v15 - progressive 175 degree cam - WIP"
    for key in ("cam_candidate", "stripped_cam", "strip_tool", "new_working_land",
                "candidate_preflight", "case_candidate", "case_relief_tool",
                "applied", "motion"):
        STATE.pop(key, None)
    STATE["document"] = document.creationId
    native().STATE = STATE
    native().close_owned_pose(app)
    STATE["progressive_restart_complete"] = True
    if not old.close(False):
        raise RuntimeError("Could not close the superseded owned trial after preserving it")
    report = {"source_v14_snapshot": str(source), "new_document": document.creationId,
              "superseded_trial": str(archive),
              "user_directed_change": "Increasing mechanical advantage through the loaded stroke",
              "absolute_spring_force_and_servo_torque_not_qualified": True}
    native().write("progressive_revision_restart.json", report)
    return report


def require(app):
    if not STATE or app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate only the owned v15 physical-cam document")


def native():
    return STATE["native"]


def build_profile_solid(app, curves, y0=4.85, y1=9.2):
    require(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    occurrence = design.rootComponent.occurrences.addNewComponent(adsk.core.Matrix3D.create())
    occurrence.component.name = "TEMP_V15_SMOOTH_PROFILE"
    sketch = occurrence.component.sketches.add(occurrence.component.xZConstructionPlane)
    sketch.isComputeDeferred = True
    try:
        for curve in curves:
            if curve["kind"] == "arc":
                cx, cz = curve["centre_xz_mm"]
                angle, radius = curve["start_angle_rad"], curve["radius_mm"]
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
                added = sketch.sketchCurves.sketchArcs.addByCenterStartSweep(
                    centre, start, sign*(curve["end_angle_rad"]-angle))
            else:
                points = [sketch.modelToSketchSpace(
                    adsk.core.Point3D.create(x/10, 0, z/10))
                    for x, z in curve["controls_xz_mm"]]
                geometry = adsk.core.NurbsCurve3D.createNonRational(
                    points, curve["degree"], curve["knots"], False)
                if geometry is None:
                    raise RuntimeError("The continuous physical cam spline could not be created")
                added = sketch.sketchCurves.sketchFixedSplines.addByNurbsCurve(geometry)
            if added is None:
                raise RuntimeError("A smooth physical cam segment could not be created")
    finally:
        sketch.isComputeDeferred = False
    if sketch.profiles.count != 1:
        raise RuntimeError("The smooth physical cam must define one closed native profile")
    extrude = occurrence.component.features.extrudeFeatures.addSimple(
        sketch.profiles.item(0), adsk.core.ValueInput.createByReal((y1-y0)/10),
        adsk.fusion.FeatureOperations.NewBodyFeatureOperation)
    if int(extrude.healthState) != 0 or extrude.bodies.count != 1:
        raise RuntimeError("The smooth physical cam extrusion failed")
    manager = adsk.fusion.TemporaryBRepManager.get()
    shape = manager.copy(extrude.bodies.item(0))
    shift = adsk.core.Matrix3D.create()
    shift.translation = adsk.core.Vector3D.create(
        0, (y0+y1)/20-(shape.boundingBox.minPoint.y+shape.boundingBox.maxPoint.y)/2, 0)
    if not manager.transform(shape, shift) or not shape.isSolid:
        raise RuntimeError("The smooth cam working-land placement failed")
    design.activateRootComponent()
    if not occurrence.deleteMe():
        raise RuntimeError("The owned temporary profile component was not removed")
    return shape


def prepare_cam(app):
    require(app)
    if "cam_candidate" in STATE:
        raise RuntimeError("The new physical cam is already prepared")
    spec = json.loads((OUT / "smooth_cam_profile.json").read_text())
    if spec["source_sha256"] != STATE["input_sha256"]:
        raise RuntimeError("The smooth profile is not bound to this preserved source")
    s = native().load("pancake_paths_study")
    manager = s.tbm()
    centre = spec["cam_centre_xz_mm"]
    land = build_profile_solid(app, spec["curves"])
    s.op(land, s.cyl(*centre, 4.7, 9.35, 1.1), "cut")
    tool = s.box(-40, 50, 4.85, 9.2, 15, 90)
    s.op(tool, s.cyl(*centre, 4.7, 9.35, 4.1), "cut")
    stripped = manager.copy(STATE["before"][native().CAM])
    s.op(stripped, tool, "cut")
    cam = manager.copy(stripped)
    s.op(cam, land, "join")
    if not cam.isSolid or cam.lumps.count != 1 or cam.volume <= 0:
        raise RuntimeError("The revised cam is not one valid native solid")
    outside_land = manager.copy(STATE["before"][native().CAM])
    s.op(outside_land, s.box(-100, 100, 4.85, 9.2, -100, 150), "cut")
    new_outside = manager.copy(cam)
    s.op(new_outside, s.box(-100, 100, 4.85, 9.2, -100, 150), "cut")
    difference = native().exact_difference(outside_land, new_outside)
    if difference:
        raise RuntimeError("The horn interface, rear hub or front journal changed")
    dwell_radius = next(c["radius_mm"] for c in spec["curves"]
                        if c["kind"] == "arc" and c["full_open_dwell"])
    dwell_faces = [f for f in cam.faces if adsk.core.Cylinder.cast(f.geometry)
                   and abs(adsk.core.Cylinder.cast(f.geometry).radius*10-dwell_radius) < 1e-6]
    if len(dwell_faces) != 1:
        raise RuntimeError("The physical open dwell is not one exact native cylinder")
    axis = adsk.core.Cylinder.cast(dwell_faces[0].geometry)
    axis_error = math.hypot(axis.origin.x*10-centre[0], axis.origin.z*10-centre[1])
    if axis_error > 1e-7 or abs(axis.axis.y) < .999999:
        raise RuntimeError("The open-dwell reaction is not concentric with the servo axis")
    STATE.update(cam_candidate=cam, stripped_cam=stripped, strip_tool=tool,
                 new_working_land=land)
    report = {
        "working_land_y_mm": [4.85, 9.2], "native_cam_volume_mm3": cam.volume*1000,
        "horn_rear_hub_and_journal_exact_difference_mm3": difference,
        "native_continuous_working_land": True,
        "source_cam_volume_mm3": STATE["before"][native().CAM].volume*1000,
        "physical_changes_not_applied_yet": True,
        "exact_native_full_open_dwell_radius_mm": dwell_radius,
        "full_open_dwell_axis_error_mm": axis_error,
    }
    native().write("native_cam_candidate.json", report)
    return report


def preflight(app, start=0, count=12):
    require(app)
    adapter = native()
    s, motion = adapter.load("pancake_paths_study"), adapter.load("sparkshift_ahg_min")
    by = adapter.bodies(app)
    source = STATE["before"]
    angles = {p["cam_deg"]: p["arm_deg"] for p in
              json.loads((OUT / "smooth_cam_profile.json").read_text())["physical_motion"]}
    camera_pivot = (10.5, 50.72059521522819)
    arm_pivot = (9.5, 13.0999827910455)
    moving = [name for name, body in by.items()
              if name in source and body.assemblyContext.fullPathName[:2]
              in ("05", "07", "09", "11")]
    fixed = [name for name, body in by.items()
             if name in source and body.assemblyContext.fullPathName.startswith("01 ")]
    phi_list = list(range(0, 176, 5))
    rows = STATE.setdefault("candidate_preflight", [])
    if len(rows) != start:
        raise RuntimeError("Continue native cam preflight from its recorded progress")
    delta = s.tbm().copy(STATE["cam_candidate"])
    s.op(delta, source[adapter.CAM], "cut")
    for phi in phi_list[start:start+count]:
        cam = motion.rotated(STATE["cam_candidate"], camera_pivot, phi)
        addition = motion.rotated(delta, camera_pivot, phi)
        theta = angles[float(phi)]
        hits = []
        for name in fixed:
            volume, overlap = s.common_volume(addition, source[name])
            if volume > 1e-5:
                hits.append({"moving": "new cam material", "fixed": name,
                             "volume_mm3": volume,
                             "bounds_mm": [[v*10 for v in p.asArray()] for p in
                                           (overlap.boundingBox.minPoint,
                                            overlap.boundingBox.maxPoint)]})
        for name in moving:
            if name == "CAM_FOLLOWER_623":
                continue
            arm = motion.rotated(source[name], arm_pivot, theta)
            volume, overlap = s.common_volume(cam, arm)
            if volume > 1e-5:
                hits.append({"moving": name, "fixed": "new full cam",
                             "volume_mm3": volume,
                             "bounds_mm": [[v*10 for v in p.asArray()] for p in
                                           (overlap.boundingBox.minPoint,
                                            overlap.boundingBox.maxPoint)]})
        rows.append({"cam_deg": phi, "arm_deg": theta, "interferences": hits})
        adapter.write("physical_cam_preflight.json", {"poses": rows})
    return {"poses": len(rows), "expected": len(phi_list),
            "interferences": [dict(cam_deg=row["cam_deg"], **hit)
                              for row in rows for hit in row["interferences"]]}


def prepare_case_clearance(app):
    require(app)
    if len(STATE.get("candidate_preflight", [])) != 36:
        raise RuntimeError("Complete the full physical-cam preflight before authoring relief")
    adapter = native()
    s = adapter.load("pancake_paths_study")
    centre = (10.5, 50.72059521522819)
    tool = s.cyl(*centre, 4.65, 9.4, 9.65)
    s.op(tool, s.box(11.5, 20.2, 4.6, 9.45, 55.2, 60.7), "common")
    before = STATE["before"][adapter.FRONT]
    after = s.tbm().copy(before)
    s.op(after, tool, "cut")
    if not after.isSolid or after.lumps.count != 1:
        raise RuntimeError("The upper cam-window relief disconnected the front case")
    removed = s.tbm().copy(before)
    s.op(removed, after, "cut")
    protected_losses = []
    for name, body in STATE["before"].items():
        if not any(token in name for token in (
                "INSERT", "HEATSET", "MAGNET", "LOCATOR_PIN", "MF85", "hall_effect")):
            continue
        box = body.boundingBox
        region = s.box(box.minPoint.x*10-1.6, box.maxPoint.x*10+1.6,
                       box.minPoint.y*10-1.6, box.maxPoint.y*10+1.6,
                       box.minPoint.z*10-1.6, box.maxPoint.z*10+1.6)
        loss, _ = s.common_volume(removed, region)
        if loss > 1e-7:
            protected_losses.append({"hardware": name, "stock_removed_mm3": loss})
    if protected_losses:
        adapter.write("upper_cam_window_protected_losses.json", protected_losses)
        raise RuntimeError("The upper cam-window relief removes protected interface stock")
    rows = []
    motion = adapter.load("sparkshift_ahg_min")
    for phi in range(0, 176, 5):
        cam = motion.rotated(STATE["cam_candidate"], centre, phi)
        overlap, _ = s.common_volume(cam, after)
        if overlap > 1e-5:
            raise RuntimeError("The real cam still interferes with the relieved housing")
        rows.append({"cam_deg": phi, "cam_case_overlap_mm3": overlap})
    STATE.update(case_candidate=after, case_relief_tool=tool)
    report = {"front_case_removed_mm3": removed.volume*1000,
              "relief_bounds_mm": [[v*10 for v in p.asArray()] for p in
                                  (removed.boundingBox.minPoint, removed.boundingBox.maxPoint)],
              "protected_hardware_backing_removed_mm3": protected_losses,
              "one_connected_case": True, "real_cam_case_checks": rows}
    adapter.write("upper_cam_window_relief.json", report)
    return {k: v for k, v in report.items() if k != "real_cam_case_checks"}


def apply_cam(app):
    require(app)
    if STATE.get("applied"):
        raise RuntimeError("Native profile installation already started; inspect its receipt")
    adapter = native()
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    relation = root.tangentRelationships.itemByName("SWING_ARM_CAM_ANIMATION_GUIDE")
    if relation is None:
        raise RuntimeError("The preserved v14 native guide is missing")
    relation.isSuppressed = True
    report = [
        adapter.append_boolean(
            app, adapter.CAM, STATE["strip_tool"], "cut",
            "V15 retain horn hub and journal - replace working land", STATE["stripped_cam"]),
        adapter.append_boolean(
            app, adapter.CAM, STATE["new_working_land"], "join",
            "V15 smooth 175 degree physical cam", STATE["cam_candidate"]),
        adapter.append_boolean(
            app, adapter.FRONT, STATE["case_relief_tool"], "cut",
            "V15 bounded upper cam-window clearance", STATE["case_candidate"]),
    ]
    limits = root.joints.itemByName("J_CAM").jointMotion.rotationLimits
    limits.maximumValue = math.radians(175)
    limits.isMaximumValueEnabled = True
    for name in ("J_C", "J_CAM"):
        joint = root.joints.itemByName(name)
        joint.isLocked = False
        joint.jointMotion.rotationLimits.isRestValueEnabled = False
    root.joints.itemByName("J_SC").isSuppressed = True
    root.motionLinks.itemByName("CLAMPED_HOB_14_37").isSuppressed = True
    source = json.loads((OUT / "physical_opening_design_input.json").read_text())
    source.update(
        outline_xz_mm=adapter.outer_profile(adapter.bodies(app)[adapter.CAM].nativeObject),
        arm_range_deg=[-8., 1.], cam_range_deg=[0., 175.])
    adapter.write("frozen_cam_profile.json", source)
    adapter.write("physical_parts_applied.json", {"operations": report})
    return report


def install_motion(app):
    require(app)
    motion = load_file("sparkshift_cam_v15_progressive_motion",
                       BASE / "sparkshift_swingarm_motion_v13.py")
    motion.OUT = OUT
    by = native().bodies(app)
    manager = adsk.fusion.TemporaryBRepManager.get()
    motion.STATE = {
        "document": STATE["document"], "input_sha256": STATE["input_sha256"],
        "before": {name: manager.copy(body) for name, body in by.items()
                   if name in STATE["before"]},
        "exact_readback_helper": STATE["exact_readback_helper"],
        "before_part_definitions": {
            name: (STATE["cam_candidate"] if name == native().CAM else
                   STATE["case_candidate"] if name == native().FRONT else body)
            for name, body in STATE["before"].items()},
    }
    STATE["motion"] = motion
    report = motion.refine_single_surface(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    root.attributes.add("SparkShiftMotion", "physical_opening",
                        "V15 progressive working cam: nominal 2.50 mm rim gap from 170 through 175 deg")
    root.attributes.add("SparkShiftMotion", "geometry_notice",
                        "New smooth physical working lobe and bounded upper front-case relief only; "
                        "horn, spline, journal, bearings, HGX/tool datums and screw sizes preserved")
    root.attributes.add("SparkShiftMotion", "progressive_leverage",
                        "After a softened entry, decreasing arm travel per cam degree increases "
                        "mechanical advantage as the spring loads. Exact concentric open dwell "
                        "minimizes ideal backdrive torque, not spring force; friction and "
                        "actual spring/servo loads remain unqualified.")
    root.attributes.add("SparkShiftMotion", "drive_instructions",
                        "Drive J_CAM 0..175 deg smoothly; full-open dwell 170..175 deg. "
                        "Nominal 5 deg upper margin below user-stated 180 deg servo travel; "
                        "calibrate actual servo endpoints before hardware use.")
    root.attributes.add("SparkShiftMotion", "guide_notice",
                        "Two hidden non-printing kinematic references; "
                        "no spring-force or simultaneous feed/release simulation")
    return report


def install_solid_motion_references(app):
    require(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    motion = STATE["motion"]
    if STATE.get("solid_motion_references"):
        raise RuntimeError("The solid non-printing motion references are already installed")
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.revertPendingSnapshot()
    relation = root.tangentRelationships.itemByName(motion.GUIDE_RELATION)
    if relation is not None:
        relation.deleteMe()
    motion.configure_controls(app)
    for name in ("J_CAM", "J_C"):
        root.joints.itemByName(name).jointMotion.rotationValue = 0.
        if abs(root.joints.itemByName(name).jointMotion.rotationValue) > 1e-8:
            raise RuntimeError("The reference geometry must be installed at exact closed rest")
    root.joints.itemByName("J_C").jointMotion.rotationLimits.maximumValue = 0.
    root.joints.itemByName("J_C").jointMotion.rotationLimits.isMaximumValueEnabled = True
    profile = json.loads((OUT / "motion_guide_profile.json").read_text())
    guide = build_profile_solid(app, profile["curves"], 5., 9.)
    source = json.loads((OUT / "frozen_cam_profile.json").read_text())
    fx, fz = source["follower_xz_mm"]
    follower = native().load("pancake_paths_study").cyl(fx, fz, 5., 9., 5.)
    for name, shape in zip(motion.REFERENCES, (guide, follower)):
        occurrence = next(o for o in root.allOccurrences if o.component.name == name)
        component = occurrence.component
        previous = component.features.baseFeatures.itemByName(name)
        if previous is None:
            raise RuntimeError("The owned non-printing reference feature is missing")
        previous.deleteMe()
        if component.bRepBodies.count:
            raise RuntimeError("The old motion reference body was not removed")
        feature = component.features.baseFeatures.add()
        feature.name = name
        if not feature.startEdit():
            raise RuntimeError("Could not edit the canonical motion reference")
        component.bRepBodies.add(shape, feature)
        if not feature.finishEdit():
            raise RuntimeError("Could not finish the canonical motion reference")
        adsk.doEvents()
        if feature.bodies.count != 1 or not feature.bodies.item(0).isSolid:
            raise RuntimeError("The motion reference must be one valid solid")
        body = feature.bodies.item(0)
        body.name = name
        body.isLightBulbOn = False
        body.attributes.add("SparkShiftMotion", "purpose",
                            "NON_PRINTING_ANIMATION_REFERENCE_NOT_PHYSICAL_HARDWARE")
        occurrence.isLightBulbOn = False
    design.activateRootComponent()
    motion.configure_controls(app)
    relation = motion.add_guide_relationship(app, profile)
    motion.configure_controls(app)
    motion.guard_physical_snapshot(app, "solid_motion_references")
    STATE["solid_motion_references"] = True
    report = {"guide": relation.name, "healthy": int(relation.healthState) == 0,
              "physical_parts_modified_by_reference_replacement": False,
              "reference_bodies_are_solid_to_exclude_inner_shell_tangency": True,
              "reference_outer_contact_geometry_source_bound": True,
              "preview_closed_grip_stop_deg": 0.,
              "physical_cam_still_has_intentional_closed_clearance": True}
    native().write("solid_motion_references.json", report)
    return report


def use_single_face_reference(app):
    require(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    motion = STATE["motion"]
    if design.snapshots.hasPendingSnapshot:
        design.snapshots.revertPendingSnapshot()
    relation = root.tangentRelationships.itemByName(motion.GUIDE_RELATION)
    if relation is not None:
        relation.deleteMe()
    motion.configure_controls(app)
    for name in ("J_CAM", "J_C"):
        root.joints.itemByName(name).jointMotion.rotationValue = 0.
    profile = json.loads((OUT / "motion_guide_profile.json").read_text())
    curve = profile["single_face_reference_curve"]
    shape = build_profile_solid(app, [curve], 5., 9.)
    if sum(f.geometry.objectType == "adsk::core::NurbsSurface"
           for f in shape.faces) != 1:
        raise RuntimeError("The non-printing guide must have one continuous outer surface")
    occurrence = next(o for o in root.allOccurrences
                      if o.component.name == motion.REFERENCES[0])
    component = occurrence.component
    component.features.baseFeatures.itemByName(motion.REFERENCES[0]).deleteMe()
    feature = component.features.baseFeatures.add()
    feature.name = motion.REFERENCES[0]
    if not feature.startEdit():
        raise RuntimeError("Could not edit the single-face motion reference")
    component.bRepBodies.add(shape, feature)
    if not feature.finishEdit():
        raise RuntimeError("Could not finish the single-face motion reference")
    adsk.doEvents()
    body = feature.bodies.item(0)
    body.name = motion.REFERENCES[0]
    body.isLightBulbOn = False
    body.attributes.add("SparkShiftMotion", "purpose",
                        "NON_PRINTING_ANIMATION_REFERENCE_NOT_PHYSICAL_HARDWARE")
    design.activateRootComponent()
    root.joints.itemByName("J_C").jointMotion.rotationLimits.maximumValue = 0.
    motion.configure_controls(app)
    relation = motion.add_guide_relationship(app, profile)
    motion.configure_controls(app)
    motion.guard_physical_snapshot(app, "single_face_solid_reference")
    STATE["single_face_reference"] = True
    report = {"healthy_native_relation": int(relation.healthState) == 0,
              "solid_reference_with_single_outer_contact_face": True,
              "closed_grip_preview_stop_deg": 0.,
              "reference_outline_deviation_mm":
                  curve["maximum_sampled_outline_deviation_mm"],
              "physical_cam_circular_dwell_unchanged": True}
    native().write("single_face_solid_motion_reference.json", report)
    return report


def use_point_contact_reference(app):
    require(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    motion = STATE["motion"]
    old = root.tangentRelationships.itemByName(motion.GUIDE_RELATION)
    if old is not None:
        old.deleteMe()
    motion.configure_controls(app)
    for name in ("J_CAM", "J_C"):
        root.joints.itemByName(name).jointMotion.rotationValue = 0.
    root.joints.itemByName("J_C").jointMotion.rotationLimits.maximumValue = math.radians(1)
    source = json.loads((OUT / "frozen_cam_profile.json").read_text())
    fx, fz = source["follower_xz_mm"]
    sphere = adsk.fusion.TemporaryBRepManager.get().createSphere(
        adsk.core.Point3D.create(fx/10, .7, fz/10), .5)
    occurrence = next(o for o in root.allOccurrences
                      if o.component.name == motion.REFERENCES[1])
    component = occurrence.component
    component.features.baseFeatures.itemByName(motion.REFERENCES[1]).deleteMe()
    feature = component.features.baseFeatures.add()
    feature.name = motion.REFERENCES[1]
    if not feature.startEdit():
        raise RuntimeError("Could not edit the point-contact motion reference")
    component.bRepBodies.add(sphere, feature)
    if not feature.finishEdit():
        raise RuntimeError("Could not finish the point-contact motion reference")
    adsk.doEvents()
    body = feature.bodies.item(0)
    body.name = motion.REFERENCES[1]
    body.isLightBulbOn = False
    body.attributes.add(
        "SparkShiftMotion", "purpose",
        "NON_PRINTING 5mm point-contact surrogate at the real roller axial midplane")
    occurrence.isLightBulbOn = False
    motion.configure_controls(app)
    root.joints.itemByName("J_CAM").jointMotion.rotationValue = math.radians(90)
    face = next(f for f in native().bodies(app)[motion.REFERENCES[0]].faces
                if adsk.core.NurbsSurface.cast(f.geometry))
    px, pz = source["pivot_xz_mm"]

    def gap(theta):
        t = math.radians(theta)
        dx, dz = fx-px, fz-pz
        point = adsk.core.Point3D.create(
            (px+dx*math.cos(t)+dz*math.sin(t))/10, .7,
            (pz-dx*math.sin(t)+dz*math.cos(t))/10)
        return app.measureManager.measureMinimumDistance(point, face).value*10-5.

    lo, hi = -8., 0.
    if gap(lo) < 0 or gap(hi) > 0:
        raise RuntimeError("The point-contact seed is not bracketed")
    for _ in range(45):
        mid = (lo+hi)/2
        if gap(mid) > 0:
            lo = mid
        else:
            hi = mid
    seed = (lo+hi)/2
    preferences = app.preferences.unitAndValuePreferences
    previous = preferences.angularPrecision
    try:
        preferences.angularPrecision = 8
        root.joints.itemByName("J_C").jointMotion.rotationValue = math.radians(seed)
    finally:
        preferences.angularPrecision = previous
    if design.snapshots.hasPendingSnapshot:
        snapshot = design.snapshots.add()
        snapshot.name = "V15 axial-midplane point-contact seed"
    motion.configure_controls(app)
    by = native().bodies(app)
    first = next(f for f in by[motion.REFERENCES[1]].faces
                 if adsk.core.Sphere.cast(f.geometry))
    second = next(f for f in by[motion.REFERENCES[0]].faces
                  if adsk.core.NurbsSurface.cast(f.geometry))
    relation = root.tangentRelationships.add(
        root.tangentRelationships.createInput(first, second))
    relation.name = motion.GUIDE_RELATION
    if int(relation.healthState) != 0:
        raise RuntimeError("The axial-midplane point-contact relationship failed")
    motion.configure_controls(app)
    STATE["point_contact_reference"] = True
    report = {
        "native_guide_healthy": True, "reference_radius_mm": 5.,
        "reference_axial_midplane_y_mm": 7., "engaged_seed_arm_deg": seed,
        "physical_623_bearing_and_its_free_rotation_unchanged": True,
        "reference_is_non_printing_not_physical_hardware": True,
    }
    native().write("point_contact_motion_reference.json", report)
    return report


def configure_curve_playback(app):
    require(app)
    design = adsk.fusion.Design.cast(app.activeProduct)
    root = design.rootComponent
    design.isContactAnalysisEnabled = False
    for contact in list(design.contactSets):
        if contact.name != "CONTACT_PREVIEW_GUIDE_NO_PENETRATION":
            raise RuntimeError("Unexpected contact relationship outside the owned preview")
        contact.deleteMe()
    for name in ("J_C", "J_CAM"):
        joint = root.joints.itemByName(name)
        joint.isLocked = False
        joint.jointMotion.rotationLimits.isRestValueEnabled = False
    root.joints.itemByName("J_C").jointMotion.rotationLimits.maximumValue = math.radians(1.)
    root.joints.itemByName("J_CAM").jointMotion.rotationLimits.maximumValue = math.radians(175.)
    root.joints.itemByName("J_SC").isSuppressed = True
    root.motionLinks.itemByName("CLAMPED_HOB_14_37").isSuppressed = True
    for name in ("J_C", "J_CAM"):
        root.joints.itemByName(name).isLocked = False
        root.joints.itemByName(name).jointMotion.rotationLimits.isRestValueEnabled = False
    profile = json.loads((OUT / "motion_guide_profile.json").read_text())
    payload = {
        "schema": 1, "cam_range_deg": [0, 175],
        "samples": [[r["cam_deg"], r["guided_arm_deg"]]
                    for r in profile["sampled_motion"]],
        "physical_cam_contact_source_sha256":
            hashlib.sha256((OUT / "frozen_cam_profile.json").read_bytes()).hexdigest(),
        "source_native_input_sha256": STATE["input_sha256"],
        "guide_clearance_margin_mm": profile["radial_margin_mm"],
        "maximum_reference_arm_error_deg": profile["validation"]["maximum_arm_error_deg"],
        "physical_cam_has_exact_concentric_open_dwell": True,
        "spring_forces_or_simultaneous_feed_not_simulated": True,
    }
    joint = root.motionLinks.itemByName("CLAMPED_HOB_14_37")
    if not joint.isReversed:
        raise RuntimeError("The retained HGX ratio direction changed")
    input_data = json.loads((OUT / "physical_opening_design_input.json").read_text())
    payload.update(
        arm_pivot_mm=[input_data["pivot_xz_mm"][0], 0., input_data["pivot_xz_mm"][1]],
        cam_pivot_mm=[input_data["cam_centre_xz_mm"][0], 0.,
                      input_data["cam_centre_xz_mm"][1]],
        moving_hob_axis_mm=[input_data["moving_hob_xz_mm"][0], 0.,
                            input_data["moving_hob_xz_mm"][1]],
        moving_hob_ratio=abs(joint.valueTwo.value/joint.valueOne.value),
        held_left_compound_deg=math.degrees(
            root.joints.itemByName("J_S_L").jointMotion.rotationValue),
        fixed_frame_transform=list(next(
            o for o in root.occurrences if o.name.startswith("01 ")).transform2.asArray()),
        held_input_transforms={
            o.name[:2]: list(o.transform2.asArray()) for o in root.occurrences
            if o.name[:2] in ("03", "04", "06")},
        explicit_forward_kinematics=True)
    root.joints.itemByName("J_S_R").isLocked = True
    path = OUT / "playback" / "SparkShiftCamPlayback" / "cam_motion.json"
    path.write_text(json.dumps(payload, indent=2)+"\n")
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    root.attributes.add("SparkShiftMotion", "playback_data_sha256", digest)
    root.attributes.add("SparkShiftMotion", "mode", "CHECKED_CONTACT_CURVE_PLAYBACK")
    root.attributes.add(
        "SparkShiftMotion", "drive_instructions",
        "Use the supplied SparkShiftCamPlayback script cam-angle slider or Play cycle. "
        "Direct Drive Joint does not synchronize both axes. The automatic tangent "
        "solver is disabled because it selected penetrating take-up poses.")
    root.attributes.add(
        "SparkShiftMotion", "guide_notice",
        ("No non-printing drive bodies remain. " if STATE.get("diagnostic_references_removed")
         else "Hidden diagnostic references are non-printing and are not active drivers. ")
        + "The supplied playback drives native poses from the checked cam-contact curve.")
    root.attributes.add(
        "SparkShiftMotion", "playback_qualification",
        "Geometric cam-contact kinematics with bounded reference clearance; "
        "explicit forward kinematics keeps native occurrences consistent below "
        "Drive Joint's angular deadband. Not spring-force, friction, servo-current "
        "or endurance qualification.")
    for relation in list(root.tangentRelationships):
        if relation.name not in ("SWING_ARM_CAM_ANIMATION_GUIDE",
                                 "DIAGNOSTIC_AUTO_TANGENCY_DISABLED"):
            raise RuntimeError("Unexpected tangent relationship outside the owned preview")
        relation.deleteMe()
    if root.tangentRelationships.count:
        raise RuntimeError("The unreliable diagnostic tangent was not removed")
    controller = load_file(
        "sparkshift_cam_v15_playback", path.with_name("SparkShiftCamPlayback.py"))
    STATE["controller"] = controller
    controller.drive(app, 0.)
    report = {"controller_script": str(path.with_name("SparkShiftCamPlayback.py")),
              "data": str(path), "data_sha256": digest,
              "automatic_tangent_disabled_explicitly": True,
              "native_joint_angle_control_and_playback_available": True,
              "physical_cam_geometry_unchanged_by_playback_configuration": True}
    native().write("curve_playback_setup.json", report)
    return report


def record_playback_samples(app, targets, key="checked_native_playback"):
    require(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    controller = STATE["controller"]
    _, data = controller.validate(adsk.fusion.Design.cast(app.activeProduct))
    arm = next(o for o in root.occurrences if o.name.startswith("05 "))
    rows = STATE.setdefault(key, [])
    for target in targets:
        driven = controller.drive(app, float(target))
        matrix = arm.transform2.asArray()
        actual = math.degrees(math.atan2(matrix[2], matrix[0]))
        expected = controller.arm_angle(data, float(target))
        if abs(actual-expected) > 1e-6:
            raise RuntimeError("The real native arm departed from its checked contact pose")
        by = native().bodies(app)
        gap = app.measureManager.measureMinimumDistance(
            by["STOCK_003_extrude_wheel_1"], by["STOCK_038_extrude_wheel_1"]).value*10
        if target >= 170 and gap < 2.5:
            raise RuntimeError("The real native open dwell loses the target opening")
        rows.append({"cam_deg": target, "arm_deg": actual,
                     "expected_arm_deg": expected, "native_angle_error_deg": actual-expected,
                     "rim_gap_mm": gap,
                     "joint_angle_field_error_deg": driven.get("joint_angle_field_error_deg")})
    native().write(key+".json", {
        "document": STATE["document"], "samples": rows,
        "native_joints_driven_from_actual_physical_cam_contact_curve": True,
        "automatic_tangent_solver_not_used": True})
    return {"samples": len(rows), "last": rows[-1],
            "maximum_native_angle_error_deg": max(abs(r["native_angle_error_deg"]) for r in rows)}


def verify_parts(app, key="physical_parts_verification"):
    require(app)
    by = native().bodies(app)
    expected = {native().CAM: STATE["cam_candidate"],
                native().FRONT: STATE["case_candidate"]}
    manager = adsk.fusion.TemporaryBRepManager.get()
    rows = []
    for name, before in STATE["before"].items():
        actual = manager.copy(by[name].nativeObject or by[name])
        if not actual.isSolid or actual.lumps.count != 1 or actual.volume <= 0:
            raise RuntimeError("A physical part is no longer a single solid: "+name)
        difference = native().exact_difference(expected.get(name, before), actual)
        rows.append({"part": name, "intended_change": name in expected,
                     "exact_expected_difference_mm3": difference})
        native().write(key+".json", {"parts": rows, "document": STATE["document"]})
        if difference:
            raise RuntimeError("A physical part changed outside the approved cam revision: "+name)
    expected_extra = set() if STATE.get("diagnostic_references_removed") else set(
        STATE["motion"].REFERENCES)
    if set(by)-set(STATE["before"]) != expected_extra:
        raise RuntimeError("Unexpected bodies remain in the native revision")
    return {"verified_physical_parts": len(rows), "unchanged_definitions": 141,
            "modified_physical_parts": list(expected),
            "hidden_inactive_diagnostic_references": len(expected_extra),
            "all_native_expected_differences_exact_zero": True}


def remove_unused_references(app):
    require(app)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    if root.tangentRelationships.count:
        raise RuntimeError("Do not remove geometry used by an active native relationship")
    for group in list(root.allRigidGroups):
        if group.name in ("RIGID_MOTION_REFERENCE_05", "RIGID_MOTION_REFERENCE_10"):
            if not group.deleteMe():
                raise RuntimeError("Could not remove the owned diagnostic rigid group")
    for occurrence in list(root.allOccurrences):
        if occurrence.component.name in STATE["motion"].REFERENCES:
            if not occurrence.deleteMe():
                raise RuntimeError("Could not remove the unused diagnostic reference")
    STATE["diagnostic_references_removed"] = True
    root.attributes.add(
        "SparkShiftMotion", "guide_notice",
        "No non-printing drive bodies remain. Use the supplied checked contact-curve "
        "playback slider; native joints and original 143 bodies are retained.")
    return verify_parts(app, "final_physical_parts_verification")


def check_native_sweep(app, start=0, count=12):
    require(app)
    adapter = native()
    s = adapter.load("pancake_paths_study")
    rows = STATE.setdefault("native_clearance_samples", [])
    if len(rows) != start:
        raise RuntimeError("Continue clearance checks from their recorded progress")
    angles = list(range(0, 176, 5))
    for angle in angles[start:start+count]:
        STATE["controller"].drive(app, float(angle))
        by = adapter.bodies(app)
        hits = []
        groups = {name: body.assemblyContext.fullPathName[:2]
                  for name, body in by.items() if name in STATE["before"]}
        for name, key in groups.items():
            if key not in ("05", "07", "09", "11"):
                continue
            for case in (adapter.BACK, adapter.FRONT, "PRINT_REAR_MOTOR_SERVO_SPACER"):
                volume, _ = s.common_volume(by[name], by[case])
                if volume > 1e-5:
                    hits.append({"moving": name, "fixed": case, "overlap_mm3": volume})
            if name != "CAM_FOLLOWER_623":
                volume, _ = s.common_volume(by[name], by[adapter.CAM])
                if volume > 1e-5:
                    hits.append({"moving": name, "fixed": adapter.CAM,
                                 "overlap_mm3": volume})
        for name, key in groups.items():
            if key != "10":
                continue
            for case in (adapter.BACK, adapter.FRONT, "PRINT_REAR_MOTOR_SERVO_SPACER"):
                volume, _ = s.common_volume(by[name], by[case])
                if volume > 1e-5:
                    hits.append({"moving": name, "fixed": case, "overlap_mm3": volume})
        working = s.tbm().copy(by[adapter.CAM])
        s.op(working, s.box(-100, 100, 5., 9., -100, 150), "common")
        volume, _ = s.common_volume(working, by["CAM_FOLLOWER_623"])
        if volume > 1e-5:
            hits.append({"moving": adapter.CAM, "fixed": "CAM_FOLLOWER_623",
                         "overlap_mm3": volume})
        gap = app.measureManager.measureMinimumDistance(
            working, s.tbm().copy(by["CAM_FOLLOWER_623"])).value*10
        rows.append({"cam_deg": angle, "interferences": hits,
                     "real_cam_follower_clearance_mm": gap})
        adapter.write("native_physical_sweep.json",
                      {"poses": rows, "sampled_not_continuous_force_qualification": True})
        if hits:
            raise RuntimeError("The actual native progressive-cam assembly interferes: "
                               + str(hits))
    return {"checked_native_poses": len(rows), "expected": len(angles),
            "interferences": sum(len(r["interferences"]) for r in rows),
            "minimum_cam_follower_clearance_mm":
                min(r["real_cam_follower_clearance_mm"] for r in rows)}


def verify_physical_dwell(app):
    require(app)
    adapter = native()
    motion = adapter.load("sparkshift_ahg_min")
    spec = json.loads((OUT / "smooth_cam_profile.json").read_text())
    source = json.loads((OUT / "physical_opening_design_input.json").read_text())
    centre = spec["cam_centre_xz_mm"]
    pivot, follower = source["pivot_xz_mm"], source["follower_xz_mm"]
    theta = math.radians(spec["target_open_arm_deg"])
    dx, dz = follower[0]-pivot[0], follower[1]-pivot[1]
    point = adsk.core.Point3D.create(
        (pivot[0]+dx*math.cos(theta)+dz*math.sin(theta))/10, .7,
        (pivot[1]-dx*math.sin(theta)+dz*math.cos(theta))/10)
    radius = next(c["radius_mm"] for c in spec["curves"]
                  if c["kind"] == "arc" and c["full_open_dwell"])
    rows = []
    for phi in (170., 175., 180., 185., 190.):
        body = motion.rotated(STATE["cam_candidate"], centre, phi)
        face = next(f for f in body.faces if adsk.core.Cylinder.cast(f.geometry)
                    and abs(adsk.core.Cylinder.cast(f.geometry).radius*10-radius) < 1e-6)
        cylinder = adsk.core.Cylinder.cast(face.geometry)
        error = math.hypot(cylinder.origin.x*10-centre[0],
                           cylinder.origin.z*10-centre[1])
        gap = app.measureManager.measureMinimumDistance(point, face).value*10-5.
        if error > 1e-7 or abs(gap) > 1e-5:
            raise RuntimeError("The real full-open land is not a concentric, constant-lift dwell")
        rows.append({"cam_deg": phi, "axis_offset_mm": error,
                     "roller_centre_distance_minus_radius_mm": gap,
                     "beyond_175_is_geometry_check_not_servo_command": phi > 175})
    report = {"native_dwell_radius_mm": radius, "physical_dwell_deg": [170, 190],
              "commanded_dwell_deg": [170, 175], "checks": rows,
              "ideal_normal_reaction_passes_through_cam_axis": True,
              "spring_force_remains_and_friction_not_modelled": True}
    adapter.write("physical_concentric_dwell_verification.json", report)
    return report
