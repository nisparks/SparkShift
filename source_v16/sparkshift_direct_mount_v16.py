"""Measured MG90S direct-spline cam prototype, with explicit physical-fit gates."""

import hashlib
import importlib.util
import json
import math
import sys
import time
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "sparkshift_direct_mount_v16"
STATE = {}
CAM = "PRINT_DIRECT_CAM"
SPLINE = "OEM_SERVO_SPLINE"
HORN = "OEM_SERVO_HORN"
SCREW = "CAM_CENTRE_RETAINER_M2x16_REFERENCE_VERIFY_THREAD"
WASHER = "CAM_CENTRE_WASHER_2p2x5x0p3"
PLATE = "PRINT_REAR_MOTOR_SERVO_SPACER"
FRONT = "PRINT_000_outer_shell_of_extruder_1"


def load_file(name, path):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def write(name, data):
    (OUT / name).write_text(json.dumps(data, indent=2)+"\n")


def require(app):
    if not STATE or app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate only the owned direct-spline prototype")


def native():
    return STATE["native"]


def bodies(app):
    return native().bodies(app)


def prepare(app, ui):
    if STATE:
        raise RuntimeError("The direct-spline prototype already exists")
    prior = sys.modules["sparkshift_cam_v15"]
    player = prior.STATE["controller"]
    if ui.activeCommand == player.COMMAND_ID:
        if player._busy:
            raise RuntimeError("Finish the current preview cycle before starting the mounting copy")
        ui.terminateActiveCommand()
    elif ui.activeCommand != "SelectCommand":
        raise RuntimeError("Do not interrupt an unrelated active CAD command")
    source = app.activeDocument
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = {b.name: b for o in design.rootComponent.allOccurrences for b in o.bRepBodies}
    if len(by) != 143 or any(name not in by for name in (CAM, SPLINE, HORN, SCREW, WASHER, PLATE)):
        raise RuntimeError("The expected current assembly/interface inventory changed")
    manager = adsk.fusion.TemporaryBRepManager.get()
    before = {name: manager.copy(body.nativeObject or body) for name, body in by.items()}
    OUT.mkdir(exist_ok=True)
    (OUT / "cad").mkdir(exist_ok=True)
    path = OUT / "cad" / ("Input_before_direct_spline_"+time.strftime("%Y%m%d_%H%M%S")+".f3d")
    if not design.exportManager.execute(
            design.exportManager.createFusionArchiveExportOptions(str(path))):
        raise RuntimeError("The current user assembly could not be preserved")
    receipt = {"input": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
               "source_document": source.creationId, "source_name": source.name,
               "physical_body_count": len(by), "source_geometry_not_modified": True}
    write("direct_mount_input_capture.json", receipt)
    document = app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(path)))
    if document is None or document == source:
        raise RuntimeError("The measured mounting prototype could not be isolated")
    document.name = "SparkShift v16 - direct 21T spline - FIT PENDING"
    adapter = load_file("sparkshift_v16_native", BASE / "sparkshift_opening_v14.py")
    adapter.OUT = OUT
    STATE.update(document=document.creationId, before=before, native=adapter,
                 source_document=source.creationId, input_sha256=receipt["sha256"],
                 exact_readback_helper=prior.exact_helper(), aliases={}, applied=[])
    adapter.STATE = STATE
    player.drive(app, 0.)
    helper = load_file("sparkshift_v16_profile_builder", BASE / "sparkshift_cam_v15.py")
    helper.STATE = STATE
    helper.OUT = OUT
    STATE["profile_builder"] = helper
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    point = root.joints.itemByName("J_CAM").geometryOrOriginTwo.origin
    base_y = before[SPLINE].boundingBox.minPoint.y*10
    spec = {
        "source_sha256": receipt["sha256"],
        "centre_xz_mm": [point.x*10, point.z*10],
        "spline_major_diameter_mm": 4.86, "exposed_height_mm": 3.36,
        "tooth_count": 21, "retaining_thread": "M2.5",
        "these_four_hardware_values_are_user_confirmed": True,
        "spline_root_diameter_photo_estimate_mm": 4.62,
        "spline_flank_profile_is_an_approximation_requiring_fit_trial": True,
        "boss_plane_model_y_mm": base_y,
        "absolute_boss_to_ear_datum_is_inherited_not_measured": True,
        "boss_running_clearance_mm": .20,
        "shaft_tip_y_mm": base_y+3.36, "hub_rear_y_mm": base_y+.20,
        "nominal_spline_engagement_mm": 3.16,
        "socket_normal_clearance_trial_mm": .025,
        "spline_clocking_deg": 0., "clocking_requires_hardware_endpoint_calibration": True,
        "rear_hub_outer_diameter_mm": 8.5,
        "entry_lead_length_mm": .20, "entry_lead_radial_clearance_mm": .15,
        "centre_clearance_diameter_mm": 2.9,
        "journal_outer_diameter_mm": 4.95,
        "journal_minimum_radial_wall_mm": (4.95-2.9)/2,
        "journal_loaded_strength_not_qualified": True,
        "retainer_selected_standard": "M2.5x16 socket head; standard coarse pitch assumed",
        "retainer_head_diameter_mm": 4.5, "retainer_head_height_mm": 2.5,
        "retainer_hex_across_flats_mm": 2.,
        "washer_id_od_thickness_mm": [2.7, 6., .5],
        "retainer_under_head_y_mm": 14.2, "retainer_tip_y_mm": -1.8,
        "nominal_retainer_engagement_mm": base_y+3.36+1.8,
        "minimum_required_usable_thread_depth_mm": base_y+3.36+1.8+.20,
        "usable_thread_depth_not_measured": True,
        "outside_ear_span_photo_mm": 32.21,
        "ear_hole_pitch_not_inferred_from_outer_span": True,
    }
    write("measured_interface.json", spec)
    receipt["prototype_document"] = document.creationId
    write("direct_mount_input_capture.json", receipt)
    return {"capture": receipt, "interface": spec}


def prepare_parts(app):
    require(app)
    if "expected_parts" in STATE:
        raise RuntimeError("The direct-mount geometry was already prepared")
    spec = json.loads((OUT / "spline_geometry.json").read_text())
    measured = json.loads((OUT / "measured_interface.json").read_text())
    if spec["source_sha256"] != STATE["input_sha256"]:
        raise RuntimeError("The direct-spline geometry is not bound to this input")
    adapter = native()
    s, m = adapter.load("pancake_paths_study"), adapter.load("sparkshift_ahg_min")
    manager = s.tbm()
    cx, cz = measured["centre_xz_mm"]
    rear, tip = measured["hub_rear_y_mm"], measured["shaft_tip_y_mm"]
    male = STATE["profile_builder"].build_profile_solid(
        app, [spec["male_curve"]], measured["boss_plane_model_y_mm"], tip)
    s.op(male, s.cyl(cx, cz, measured["boss_plane_model_y_mm"]-.1, tip+.1, 1.25), "cut")
    cavity = STATE["profile_builder"].build_profile_solid(
        app, [spec["female_curve"]], rear-.1, tip)
    cam = manager.copy(STATE["before"][CAM])
    s.op(cam, s.cyl(cx, cz, rear, .4, 4.25), "join")
    s.op(cam, s.cyl(cx, cz, .3, 2., 7.3), "join")
    s.op(cam, cavity, "cut")
    lead_end = rear+.20
    slope = (spec["female_max_radius_mm"]+.15
             - (spec["female_min_radius_mm"]-.035))/.20
    lead = m.cone_y(cx, cz, rear-.05,
                    spec["female_max_radius_mm"]+.15+slope*.05,
                    lead_end, spec["female_min_radius_mm"]-.035)
    s.op(cam, lead, "cut")
    s.op(cam, s.cyl(cx, cz, tip-.1, 14., 1.45), "cut")
    screw = m.screw_shape(cx, cz, 14.2, 2.25, 2.5, -1.8, r=1.25)
    hexagon = [(cx+2/math.sqrt(3)*math.cos(i*math.pi/3),
                cz+2/math.sqrt(3)*math.sin(i*math.pi/3)) for i in range(6)]
    socket = adapter.prism(app, hexagon, 15.3, 16.8)
    s.op(screw, socket, "cut")
    washer = m.ring(cx, cz, 13.7, 14.2, 3., 1.35)
    plate = manager.copy(STATE["before"][PLATE])
    clearance = s.cyl(cx, cz, rear-.15, .4, 4.45)
    s.op(plate, clearance, "cut")
    parts = {CAM: cam, SPLINE: male, SCREW: screw, WASHER: washer, PLATE: plate}
    for name, shape in parts.items():
        if not shape.isSolid or shape.lumps.count != 1 or shape.volume <= 0:
            raise RuntimeError("A direct-mount candidate is not one valid solid: "+name)
    protected = s.box(-100, 100, 4.85, 9.2, -100, 150)
    s.op(protected, s.cyl(cx, cz, 4.7, 9.4, 3.), "cut")
    old = manager.copy(STATE["before"][CAM])
    new = manager.copy(cam)
    s.op(old, protected, "common")
    s.op(new, protected, "common")
    difference = adapter.exact_difference(old, new)
    if difference:
        raise RuntimeError("The real v15 cam actuation profile changed")
    sleeve_zone = s.box(-100, 100, 9.2, 13.7, -100, 150)
    s.op(sleeve_zone, s.cyl(cx, cz, 9.1, 13.8, 1.5), "cut")
    old, new = manager.copy(STATE["before"][CAM]), manager.copy(cam)
    s.op(old, sleeve_zone, "common")
    s.op(new, sleeve_zone, "common")
    journal_difference = adapter.exact_difference(old, new)
    if journal_difference:
        raise RuntimeError("The external bearing journal or shoulder changed")
    STATE["expected_parts"] = parts
    STATE["plate_clearance_tool"] = clearance
    report = {
        "candidate_part_volumes_mm3": {name: b.volume*1000 for name, b in parts.items()},
        "actuation_profile_native_difference_mm3": difference,
        "external_bearing_journal_native_difference_mm3": journal_difference,
        "spline_tooth_count_confirmed": 21,
        "nominal_engagement_mm": 3.16, "full_depth_after_entry_lead_mm": 2.96,
        "journal_minimum_radial_wall_mm": 1.025,
        "retainer_nominal_engagement_mm": measured["nominal_retainer_engagement_mm"],
        "requires_usable_thread_depth_mm": measured["minimum_required_usable_thread_depth_mm"],
        "thread_depth_and_loaded_strength_not_qualified": True,
        "tooth_flanks_are_fit_trial_geometry": True,
        "not_applied_to_native_model_yet": True,
    }
    write("direct_mount_candidates.json", report)
    return report


def apply_part(app, name):
    require(app)
    if name in STATE["applied"]:
        raise RuntimeError("This direct-mount part was already applied: "+name)
    adapter = native()
    s = adapter.load("pancake_paths_study")
    manager = s.tbm()
    before, expected = STATE["before"][name], STATE["expected_parts"][name]
    if adapter.exact_difference(before, manager.copy(bodies(app)[name].nativeObject)):
        raise RuntimeError("The source part changed concurrently; no mounting edit applied: "+name)
    lost = manager.copy(before)
    gained = manager.copy(expected)
    s.op(lost, expected, "cut")
    s.op(gained, before, "cut")
    intermediate = manager.copy(before)
    if lost.lumps.count:
        s.op(intermediate, lost, "cut")
        adapter.append_boolean(app, name, lost, "cut",
                               "V16 measured direct-mount clearance", intermediate)
    if gained.lumps.count:
        adapter.append_boolean(app, name, gained, "join",
                               "V16 measured direct-mount material", expected)
    if not lost.lumps.count and not gained.lumps.count:
        STATE.setdefault("unchanged_candidates", []).append(name)
    actual = manager.copy(bodies(app)[name].nativeObject)
    difference = adapter.exact_difference(expected, actual)
    if difference:
        raise RuntimeError("The applied direct coupling differs from the reviewed candidate")
    if name not in STATE["applied"]:
        STATE["applied"].append(name)
    write("applied_direct_mount_parts.json", {"parts": STATE["applied"]})
    return {"part": name, "exact_candidate_difference_mm3": difference,
            "removed_mm3": lost.volume*1000 if lost.lumps.count else 0.,
            "added_mm3": gained.volume*1000 if gained.lumps.count else 0.}


def remove_horn_and_label(app):
    require(app)
    if STATE.get("horn_removed"):
        raise RuntimeError("The OEM horn was already removed")
    by = bodies(app)
    horn = by[HORN].nativeObject
    horn_component = horn.parentComponent
    feature = horn_component.features.removeFeatures.add(horn)
    if feature is None or int(feature.healthState) != 0:
        raise RuntimeError("The old OEM horn was not removed by a valid downstream feature")
    feature.name = "V16 remove OEM horn - cam keys directly to measured output"
    if HORN in bodies(app):
        raise RuntimeError("The old horn remains in the prototype")
    horn_component.name = "OEM horn removed in v16 - empty history component"
    renamed = {
        SPLINE: ("MG90S_21T_OD4p86_H3p36_M2p5_REFERENCE_FIT_PENDING",
                 "MG90S measured output - 21T flank fit pending"),
        SCREW: ("CAM_M2p5x16_RETAINER_VERIFY_USABLE_DEPTH",
                "M2.5x16 cam retainer - depth verification required"),
        WASHER: ("CAM_M2p5_WASHER_2p7x6x0p5",
                 "M2.5 flat washer - 2.7x6x0.5"),
    }
    for original, (name, component_name) in renamed.items():
        body = bodies(app)[original].nativeObject
        body.name = name
        body.parentComponent.name = component_name
        STATE["aliases"][original] = name
    cam = bodies(app)[CAM].nativeObject
    cam.parentComponent.name = "P05 Direct 21T spline cam - measured prototype FIT PENDING"
    shaft = bodies(app)[STATE["aliases"][SPLINE]].nativeObject
    shaft.attributes.add("DirectServoMount", "measured", "User: 21T; crest OD4.86; exposed H3.36; M2.5 thread")
    shaft.attributes.add("DirectServoMount", "unverified", "Flanks/root approximate; bore is thread-major envelope, not verified blind depth")
    cam.attributes.add("DirectServoMount", "fit_status", "Confirmed count/dimensions; flank clearance trial +0.025mm normal; physical fit and clocking pending")
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    root.attributes.add("SparkShiftMotion", "revision", "v16 measured direct 21T servo coupling - FIT PENDING")
    root.attributes.add("SparkShiftMotion", "geometry_notice",
                        "No OEM horn: one-piece printed cam/hub keys directly to 21T output. "
                        "Measured OD4.86/H3.36/M2.5; tooth flanks and thread depth require fit checks.")
    root.attributes.add("SparkShiftMotion", "retention",
                        "M2.5x16 envelope and2.7x6x0.5 washer. Nominal thread engagement2.96mm; "
                        "requires measured usable blind depth>=3.16mm before tightening.")
    root.attributes.add("SparkShiftMotion", "bearing_journal",
                        "Original4.95mm OD/MF85 interface retained;2.9mm M2.5 clearance leaves1.025mm wall. Loaded strength unqualified.")
    root.attributes.add("SparkShiftMotion", "servo_datum",
                        "Boss plane inherited from prior envelope; only exposed spline height and OD, count/thread and outer-ear span measured. Ear-hole pitch/ear-to-boss datum not certified.")
    STATE["horn_removed"] = True
    report = {"horn_body_removed": True, "one_printed_cam_and_hub": True,
              "retention_thread_user_confirmed": "M2.5", "aliases": STATE["aliases"],
              "remaining_authoring_bodies": len(bodies(app)),
              "flank_fit_clocking_thread_depth_and_strength_pending": True}
    write("direct_mount_installed.json", report)
    return report


def verify_parts(app):
    require(app)
    by = bodies(app)
    manager = adsk.fusion.TemporaryBRepManager.get()
    rows = []
    for name, before in STATE["before"].items():
        if name == HORN:
            if name in by:
                raise RuntimeError("The removed OEM horn body returned")
            continue
        actual_name = STATE["aliases"].get(name, name)
        if actual_name not in by:
            raise RuntimeError("A physical body disappeared from the measured prototype: "+name)
        actual = manager.copy(by[actual_name].nativeObject or by[actual_name])
        expected = STATE["expected_parts"].get(name, before)
        if not actual.isSolid or actual.lumps.count != 1 or actual.volume <= 0:
            raise RuntimeError("A direct-mount body is no longer one solid: "+actual_name)
        difference = native().exact_difference(expected, actual)
        rows.append({"part": actual_name, "intended_change": (
            name in STATE["expected_parts"] and name not in STATE.get("unchanged_candidates", [])),
                     "exact_expected_difference_mm3": difference})
        write("direct_mount_part_verification.json", {"parts": rows})
        if difference:
            raise RuntimeError("Unintended source geometry change: "+name)
    if len(by) != len(STATE["before"])-1:
        raise RuntimeError("Unexpected helper or duplicate bodies remain")
    return {"verified_bodies": len(rows),
            "unchanged_source_definitions": sum(not r["intended_change"] for r in rows),
            "removed_body": HORN, "all_native_differences_exact_zero": True}


def check_mounting(app, angles=(0., 90., 175.)):
    require(app)
    player = sys.modules["sparkshift_cam_v15"].STATE["controller"]
    s = native().load("pancake_paths_study")
    cases = ("PRINT_motor_mount", "PRINT_000_outer_shell_of_extruder_1", PLATE)
    rows = []
    for angle in angles:
        player.drive(app, angle)
        by = bodies(app)
        moving = [CAM, *(STATE["aliases"][n] for n in (SPLINE, SCREW, WASHER))]
        hits = []
        for name in moving:
            for case in cases:
                overlap, _ = s.common_volume(by[name], by[case])
                if overlap > 1e-5:
                    hits.append({"moving": name, "fixed": case, "overlap_mm3": overlap})
        for original in (SPLINE, SCREW, WASHER):
            name = STATE["aliases"][original]
            overlap, _ = s.common_volume(by[CAM], by[name])
            if overlap > 1e-5:
                hits.append({"moving": name, "fixed": CAM, "overlap_mm3": overlap})
        gap = app.measureManager.measureMinimumDistance(
            by[CAM], by["HOBBY_SERVO_ENVELOPE"]).value*10
        plate_gap = app.measureManager.measureMinimumDistance(by[CAM], by[PLATE]).value*10
        rows.append({"cam_deg": angle, "interferences": hits,
                     "model_servo_housing_gap_mm": gap,
                     "model_actuator_plate_gap_mm": plate_gap})
        write("direct_mount_native_clearances.json", {"poses": rows})
        if hits:
            raise RuntimeError("The measured direct-mount prototype interferes: "+str(hits))
    player.drive(app, 0.)
    return rows


def clear_retainer_pocket(app):
    require(app)
    if FRONT in STATE["expected_parts"]:
        raise RuntimeError("The measured retainer pocket was already reviewed")
    s = native().load("pancake_paths_study")
    manager = s.tbm()
    cx, cz = json.loads((OUT / "measured_interface.json").read_text())["centre_xz_mm"]
    tool = s.cyl(cx, cz, 13.5, 14.4, 3.2)
    s.op(tool, s.cyl(cx, cz, 14.3, 16.9, 2.45), "join")
    expected = manager.copy(STATE["before"][FRONT])
    s.op(expected, tool, "cut")
    removed = manager.copy(STATE["before"][FRONT])
    s.op(removed, expected, "cut")
    protected = s.box(-100, 100, -50, 13.2, -100, 150)
    loss, _ = s.common_volume(removed, protected)
    if loss > 1e-7:
        raise RuntimeError("The M2.5 clearance changed the bearing seat")
    losses = []
    for name, body in STATE["before"].items():
        if not any(token in name for token in ("INSERT", "HEATSET", "MAGNET", "LOCATOR_PIN")):
            continue
        box = body.boundingBox
        region = s.box(box.minPoint.x*10-1.6, box.maxPoint.x*10+1.6,
                       box.minPoint.y*10-1.6, box.maxPoint.y*10+1.6,
                       box.minPoint.z*10-1.6, box.maxPoint.z*10+1.6)
        volume, _ = s.common_volume(removed, region)
        if volume > 1e-7:
            losses.append({"hardware": name, "backing_removed_mm3": volume})
    if losses:
        write("retainer_pocket_protected_losses.json", losses)
        raise RuntimeError("The M2.5 pocket alters protected mounting/coupling stock")
    STATE["expected_parts"][FRONT] = expected
    result = apply_part(app, FRONT)
    report = {"operation": result, "washer_pocket_diameter_mm": 6.4,
              "head_pocket_diameter_mm": 4.9, "pocket_fore_limit_y_mm": 16.9,
              "bearing_seat_change_mm3": loss, "protected_backing_losses": losses,
              "no_new_exterior_driver_tunnel_added": True}
    write("M2p5_blind_pocket.json", report)
    return report


def check_assembly_access(app):
    require(app)
    adapter = native()
    s, m = adapter.load("pancake_paths_study"), adapter.load("sparkshift_ahg_min")
    cx, cz = json.loads((OUT / "measured_interface.json").read_text())["centre_xz_mm"]
    by = bodies(app)
    driver = s.cyl(cx, cz, 16.8, 40., 1.4)
    driver_hits = []
    for case in ("PRINT_motor_mount", FRONT, PLATE):
        volume, _ = s.common_volume(driver, by[case])
        if volume > 1e-5:
            driver_hits.append({"part": case, "tool_path_overlap_mm3": volume})
    trials = []
    for angle in (0., 90., 175.):
        sys.modules["sparkshift_cam_v15"].STATE["controller"].drive(app, angle)
        by = bodies(app)
        stack = [CAM, *(STATE["aliases"][name] for name in (SPLINE, SCREW, WASHER)),
                 "CAM_OUTBOARD_MF85ZZ_5x8x2p5"]
        hits = []
        for offset in (20., 15., 10., 8., 6., 5., 4., 3., 2., 1., .5, 0.):
            case = m.translated(by[FRONT], dy=offset)
            for name in stack:
                volume, _ = s.common_volume(case, by[name])
                if volume > 1e-5:
                    hits.append({"offset_y_mm": offset, "stack_part": name,
                                 "overlap_mm3": volume})
        trials.append({"cam_deg": angle, "case_axial_path_interferences": hits})
        write("mount_assembly_access.json",
              {"straight_driver_hits": driver_hits, "front_case_trials": trials,
               "no_exterior_driver_hole_added": True,
               "sampled_interface_path_not_a_whole_design_installation_claim": True})
    sys.modules["sparkshift_cam_v15"].STATE["controller"].drive(app, 0.)
    return {"straight_front_driver_clear": not driver_hits,
            "clear_front_case_slide_orientations_deg":
                [row["cam_deg"] for row in trials if not row["case_axial_path_interferences"]],
            "sampled_interface_only": True}


def capture_coupling_views(app):
    require(app)
    sys.modules["sparkshift_cam_v15"].STATE["controller"].drive(app, 0.)
    root = adsk.fusion.Design.cast(app.activeProduct).rootComponent
    s = native().load("pancake_paths_study")
    by = bodies(app)
    centre = json.loads((OUT / "measured_interface.json").read_text())["centre_xz_mm"]
    cx, cz = centre
    original_camera = app.activeViewport.camera
    source_occurrences = list(root.occurrences)
    lights = [(occurrence, occurrence.isLightBulbOn) for occurrence in source_occurrences]
    (OUT / "images").mkdir(exist_ok=True)
    reports = []
    for kind in ("socket_rear", "axial_section"):
        temporary = None
        try:
            if kind == "socket_rear":
                names = [CAM]
            else:
                names = [CAM, *(STATE["aliases"][name] for name in (SPLINE, SCREW, WASHER)),
                         "CAM_OUTBOARD_MF85ZZ_5x8x2p5", "HOBBY_SERVO_ENVELOPE"]
            items = []
            for name in names:
                shape = s.tbm().copy(by[name])
                if kind == "axial_section":
                    s.op(shape, s.box(cx-20, cx, -6, 18, cz-15, cz+15), "common")
                if shape.lumps.count:
                    items.append((shape, "DISPLAY ONLY "+name, by[name].appearance))
            for occurrence, _ in lights:
                occurrence.isLightBulbOn = False
            temporary = s.add_group(root, "DISPLAY ONLY direct spline "+kind, items)
            camera = adsk.core.Camera.create()
            camera.cameraType = adsk.core.CameraTypes.OrthographicCameraType
            camera.isFitView = False
            camera.isSmoothTransition = False
            camera.upVector = adsk.core.Vector3D.create(0, 0, 1)
            if kind == "socket_rear":
                camera.target = adsk.core.Point3D.create(cx/10, .3, cz/10)
                camera.eye = adsk.core.Point3D.create(cx/10, -60, cz/10)
                camera.viewExtents = 2.65
            else:
                camera.target = adsk.core.Point3D.create(cx/10, .5, cz/10)
                camera.eye = adsk.core.Point3D.create(cx/10+60, .5, cz/10)
                camera.viewExtents = 3.05
            app.activeViewport.camera = camera
            app.activeViewport.refresh()
            path = OUT / "images" / ("V16_"+kind+"_FIT_PENDING.png")
            if not app.activeViewport.saveAsImageFile(str(path), 1400, 1000):
                raise RuntimeError("The actual native coupling image could not be captured")
            reports.append({"view": kind, "file": str(path),
                            "native_cad_display_only_cutaway_not_geometry_change": True})
        finally:
            if temporary is not None and temporary.isValid:
                if not temporary.deleteMe():
                    raise RuntimeError("Could not remove the owned cutaway display component")
            for occurrence, light in lights:
                occurrence.isLightBulbOn = light
            app.activeViewport.camera = original_camera
            app.activeViewport.refresh()
    if len(bodies(app)) != 142:
        raise RuntimeError("A temporary display body leaked into the prototype")
    write("coupling_images.json", {"images": reports})
    return reports
