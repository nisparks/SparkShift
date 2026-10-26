"""Refine both side-fan toolheads and their shared dock without altering the core."""

import hashlib
import json
import math

import cadquery as cq
import trimesh

import fast_geometry
from audit_tool_owned_2510 import compound, bounds, overlaps, solid_bounds, boxes_overlap
from build_modular_toolhead import ROOT, STEP, STL, HOTEND_AXES, box, cylinder_y, load, volume, primitives
from build_tool_owned_2510_review import cylinder_x


DOCK_STANDOFF_MM = 6.5
DOCK_SCREW_HEAD_Y = 70.110082 + DOCK_STANDOFF_MM
REVIEW_REVISION = 22
REPORT_NAME = "verification_shelf_clearance_r22.json"
BODY_NAMES = {
    "Bambu": "Bambu_One_Piece_Shelf_Clearance_R22_REVIEW",
    "RedLizard": "RedLizard_Side2510_Shelf_Clearance_R22_REVIEW",
}


def export_print(name, shape, report):
    if not shape.isValid() or len(shape.Solids()) != 1:
        raise ValueError(f"Invalid/disconnected printed part {name}")
    cq.exporters.export(shape, str(STEP / f"{name}.step"))
    path = STL / f"{name}.stl"
    cq.exporters.export(shape, str(path), tolerance=0.03, angularTolerance=0.1)
    mesh = trimesh.load_mesh(path)
    check = {"valid": True, "solids": 1, "volume_mm3": volume(shape),
             "watertight": bool(mesh.is_watertight),
             "winding_consistent": bool(mesh.is_winding_consistent),
             "components": len(mesh.split(only_watertight=False)), "bounds_mm": bounds(shape)}
    report["printed_parts"][name] = check
    if not check["watertight"] or not check["winding_consistent"] or check["components"] != 1:
        raise ValueError(f"Invalid mesh {name}")


def require_clear(label, shape, targets, report, tolerance=0.001):
    hits = overlaps(shape, targets, tolerance)
    if hits:
        report["failures"].append({"check": label, "intersections_mm3": hits})
    return hits


def translated_hits(shape, targets, offset, tolerance=0.01):
    hits = {}
    for name, target in targets.items():
        total = 0
        for s, b in solid_bounds(shape):
            moved_bounds = [v + offset[i // 2] for i, v in enumerate(b)]
            if not boxes_overlap(moved_bounds, bounds(target)):
                continue
            # Only pairs that touch or nest can share volume; the rest skip the Boolean.
            index = fast_geometry.index_of(s)
            candidates = [t for t, tb in solid_bounds(target) if boxes_overlap(moved_bounds, tb)
                          and fast_geometry.touch_or_nest(index, fast_geometry.index_of(t), offset)]
            if candidates:
                moved = s.translate(offset)
                total += sum(volume(moved.intersect(t)) for t in candidates)
        if total > tolerance:
            hits[name] = total
    return hits


def stand_off_collar(dock):
    lower_jaw = load("Dock_3010_Complete").Solids()[2]
    lower_jaw_seat = dock.intersect(box(-19, 19, 50, 56, -15, -6))
    profile = [
        (45.910082, -8), (74.910082, -8), (74.910082, 22), (45.910082, 22),
        (45.910082, 17.2206), (65.910082, 17.2206), (65.910082, 10.2206),
        (63.910082, 10.2206), (63.910082, 4.2206), (65.910082, 4.2206),
        (65.910082, -2.7794), (58.910082, -2.7794), (57.910082, -1.7794),
        (53.910082, -1.7794), (52.910082, -2.7794), (45.910082, -2.7794)]
    collar = cq.Shape.cast(primitives.prism_yz_r(
        [(y + DOCK_STANDOFF_MM, z) for y, z in profile],
        [0] * 7 + [1, 1] + [0] * 7, -18.65, 18.65))
    dock = dock.cut(box(-19, 19, 50.76, 71.06, -2.9294, 17.3806))
    dock = dock.fuse(collar).fuse(
        box(-18.65, 18.65, 45.910082, 45.910082 + DOCK_STANDOFF_MM, -8, 22))
    # Real extrusion profile, with a 0.15 mm assembly allowance, not a solid 20 mm box.
    crossbar = cq.importers.importStep(str(primitives.WORK / "rack_audit_crossbar_world.step")).val()
    local_rail = crossbar.translate((-7, -(36.91 + DOCK_STANDOFF_MM), -191.2794)).rotate(
        (0, 0, 0), (0, 0, 1), 180)
    rail_clearance = local_rail
    for dy, dz in ((-0.15, 0), (0.15, 0), (0, -0.15), (0, 0.15)):
        rail_clearance = rail_clearance.fuse(local_rail.translate((0, dy, dz)))
    dock = dock.cut(rail_clearance)
    for x in (-10, 10):
        rear_access = 75.910082 + DOCK_STANDOFF_MM
        dock = dock.cut(cylinder_y(x, 7.2206, 63, rear_access, 2.6))
        dock = dock.cut(cylinder_y(x, 7.2206, DOCK_SCREW_HEAD_Y, rear_access, 4.6))
    for x in (-6, 6):
        dock = dock.cut(cylinder_y(x, 22, 45, 51.410082, 3.52))
        dock = dock.cut(cylinder_y(x, 22, 45, 57.910082, 2.58))
        dock = dock.cut(cylinder_y(x, -2, 45, 49.990082, 3.06))
    for cutter in (
        box(-7.62, 7.62, 45, 48.990082, -4.58, 0.58),
        box(-6.12, 6.12, 45, 48.990082, -5.12, 1.12),
        box(-4.5, 4.5, 47.790082, 48.990082, -5.75, 1.75)):
        dock = dock.cut(cutter)
    jaw_clearance = lower_jaw
    for axis in range(3):
        for sign in (-1, 1):
            delta = [0, 0, 0]
            delta[axis] = 0.2 * sign
            jaw_clearance = jaw_clearance.fuse(lower_jaw.translate(tuple(delta)))
    dock = dock.cut(jaw_clearance).fuse(lower_jaw_seat)
    return dock.clean()


def restrain_motor_leads(core):
    solids = core.Solids()
    routed = []
    h = math.sqrt(0.5)
    direction = cq.Vector(-h, 0, -h)
    normal = cq.Vector(-h, 0, h)
    for i in range(92, 96):
        lead = solids[i]
        if abs(volume(lead) - 10.45364955482) > 0.0001:
            raise ValueError("Unexpected AHG loose-lead reference order")
        caps = [f.Center() for f in lead.Faces() if f.geomType() == "PLANE"]
        start = max(caps, key=lambda p: p.x)
        first = start + direction
        center = first + normal * 4
        radial = normal * -4
        points = []
        for degrees in range(0, 136, 15):
            angle = math.radians(degrees)
            p = center + radial * math.cos(angle) + direction * (4 * math.sin(angle))
            blend = (1 - math.cos(math.pi * min(degrees / 45, 1))) / 2
            points.append(p + cq.Vector(0, -(95 - i) * 1.2 * blend, 0))
        tail = points[-1] + cq.Vector(0, 0, 1)
        path = [start, first, *points[1:], tail]
        segments = []
        for a, b in zip(path, path[1:]):
            delta = b - a
            segments.append(cq.Solid.makeCylinder(0.55, delta.Length, a, delta.normalized()))
        segments.extend(cq.Solid.makeSphere(0.55, p) for p in path[1:-1])
        new_lead = segments[0].fuse(*segments[1:]).clean()
        if not new_lead.isValid() or len(new_lead.Solids()) != 1:
            raise ValueError("Invalid restrained motor-lead envelope")
        routed.append(new_lead)
        solids[i] = new_lead
    return compound(solids), compound(routed)


def review_dock_sections(dock, report):
    seats = []
    for x in (-10, 10):
        annulus = cylinder_y(x, 7.2206, DOCK_SCREW_HEAD_Y - 0.2,
                             DOCK_SCREW_HEAD_Y, 4.3).cut(
            cylinder_y(x, 7.2206, DOCK_SCREW_HEAD_Y - 0.21,
                       DOCK_SCREW_HEAD_Y + 0.01, 2.7))
        missing = volume(annulus.cut(dock))
        seats.append({"x_mm": x, "missing_bearing_seat_mm3": missing})
        if missing > 0.001:
            report["failures"].append({"check": "M5 head bearing seat", "x_mm": x,
                                       "missing_mm3": missing})
    backing = []
    for x in (-6, 6):
        for dx, dz in ((0, 0), (-2, 0), (2, 0), (0, -2), (0, 2)):
            gauge = cylinder_y(x + dx, -2 + dz, 49.990082, 59.990082, 0.05)
            sections = sorted((bounds(s) for s in dock.intersect(gauge).Solids()),
                              key=lambda b: b[2])
            if not sections or abs(sections[0][2] - 49.990082) > 0.001:
                raise ValueError("Dock magnet pocket has no continuous backing at audit gauge")
            backing.append({"pocket_x_mm": x, "offset_xz_mm": [dx, dz],
                            "backing_y_thickness_mm": sections[0][3] - sections[0][2]})
    minimum_backing = min(p["backing_y_thickness_mm"] for p in backing)
    if minimum_backing < 2:
        report["failures"].append({"check": "Sampled magnet backing below 2mm target",
                                   "minimum_mm": minimum_backing})
    report["dock_section_review"] = {
        "m5_head_bearing_seats": seats,
        "magnet_backing_gauges": backing,
        "gauge_length_mm": 10,
        "minimum_sampled_magnet_backing_mm": minimum_backing,
        "sampled_backing_target_mm": 2,
        "qualification": "Local stock gauges only, not a global wall-thickness or strength analysis. "
                         "Stock readings are capped at the gauge length. Slicer/retention review "
                         "is still required; no printable-wall or load rating is certified."}


DOCK_NAMES = (
    "P25_Refined_Dock", "Upper_Snap_Jaw", "Lower_Snap_Jaw", "Silicone_Ooze_Pad",
    "Left_M5_Rack_Screw", "Right_M5_Rack_Screw", "P26_Entry_Relieved_Chute",
    "Silicone_Wiper", "Left_M3_Chute_Screw", "Right_M3_Chute_Screw",
    "Left_5mm_Bushing", "Right_5mm_Bushing", "Left_Dock_Magnet", "Right_Dock_Magnet",
)


def render_review():
    from render_accessories_v26 import shape_to_polydata, make_actor, render_view
    from PIL import Image, ImageDraw

    tmp = primitives.WORK / "refined_dock_render_tmp.stl"
    for label in ("Bambu", "RedLizard"):
        tool = load(BODY_NAMES[label])
        hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW" if label == "Bambu" else
                      "P17M_RedLizard_Hotend_Reference")
        fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
        if label == "RedLizard":
            fan = fan.translate((0.15, 0, 0))
        shapes = [
            (tool, (0.9, 0.65, 0.1) if label == "Bambu" else (0.85, 0.3, 0.12)),
            (hotend, (0.65, 0.65, 0.68)), (fan, (0.15, 0.15, 0.18)),
            (load("P18_Tool_docking_backplate_3010"), (0.25, 0.4, 0.55)),
            (load("P25_Closed_Panel_Side2510_Dock_REVIEW"), (0.22, 0.4, 0.32)),
            (load("P26_Nozzle_Entry_Clearance_Chute_REVIEW"), (0.7, 0.15, 0.15)),
            (load(f"{label}_Dock_Ooze_Pad_SILICONE_REVIEW"), (0.95, 0.4, 0.1)),
            (load(f"{label}_Dock_Wiper_SILICONE_REVIEW"), (0.1, 0.6, 0.7)),
        ]
        actors = [make_actor(shape_to_polydata(s.wrapped, tmp), color, edge_vis=True) for s, color in shapes]
        output = ROOT / "images" / f"43_{label.lower()}_shelf_clearance_r22.png"
        render_view(actors, (180, -180, 90), (0, 38, -17), (0, 0, 1), output,
                    width=1400, height=1200, zoom=1)
        image = Image.open(output)
        ImageDraw.Draw(image).text((20, 20), f"REVISION {REVIEW_REVISION} - {label} SIDE FAN / CLOSED PANEL DOCK - CAD REVIEW ONLY", fill=(20, 20, 20))
        image.save(output)
    tmp.unlink()


def build():
    report = {"revision": REVIEW_REVISION,
              "status": "CAD_REVIEW_NOT_PHYSICAL_THERMAL_OR_PRINT_QUALIFICATION",
              "failures": [], "printed_parts": {}, "variants": {}}
    original = load("Dock_3010_Complete").Solids()
    if len(original) != 14 or abs(volume(original[0]) - 74815.208) > 0.01:
        raise ValueError("Unexpected baseline dock revision/order")
    p18 = load("P18_Tool_docking_backplate_3010")
    dock = original[0]
    # Open only the two interfering entry lips; keep pin seats and jaw detents.
    dock = dock.cut(box(-10, 10, 35, 45.9501, -6.4001, -4.5793))
    dock = dock.cut(box(-10, 10, 35, 45.2001, 25.0205, 26.4001)).clean()
    report["dock_relief"] = {
        "baseline_backplate_overlap_mm3": volume(original[0].intersect(p18)),
        "removed_dock_volume_mm3": volume(original[0]) - volume(dock),
        "motion_sampling_mm": 0.5, "lip_clearance_mm": 0.2,
        "backplate_changed": False}
    vent_panel = box(-15.501, 15.499, 72.910082, 74.910082, -51.7794, -20.7794)
    before_cleanup = volume(dock)
    dock = dock.fuse(vent_panel)
    for x in (-12.001, 11.999):
        for z in (-24.2794, -48.2794):
            dock = dock.fuse(cylinder_y(x, z, 65.910082, 73.910082, 1.51))
    dock = dock.clean()
    report["obsolete_cooling_cleanup"] = {
        "description": "Close legacy front-fan exhaust grille with 2mm panel; fill four unused blind fan bores.",
        "added_volume_mm3": volume(dock) - before_cleanup,
        "missing_panel_mm3": volume(vent_panel.cut(dock)),
        "retained": "Hollow weight-relief recess, coupling jaws, rail collar, silicone pad flexure and purge/wiper openings"}
    if report["obsolete_cooling_cleanup"]["missing_panel_mm3"] > 0.001:
        report["failures"].append({"check": "Legacy vent not completely closed"})
    dock = stand_off_collar(dock)
    review_dock_sections(dock, report)
    report["rack_mount_refinement"] = {
        "tool_and_dock_front_world_y_shift_mm": DOCK_STANDOFF_MM,
        "unchanged": "Crossbar, P29/P30 mounts and X center datums",
        "collar_profile_allowance_mm": 0.15,
        "fasteners": "Replace two M5x12 references with M5x10 into matching 2020 M5 T-nuts",
        "reason": "Original dock magnets penetrated extrusion by 73.546mm3 each; M5x12 tips also hit slot floor. "
                  "A 5mm standoff cleared hardware but left only 0.770mm backing at sampled magnet gauges; "
                  "6.5mm preserves over 2mm sampled backing.",
        "nut_qualification": "Actual T-nut geometry, thread engagement and clamp torque require selected hardware."}
    core_path = primitives.WORK / "modular_audit_core_reference.step"
    source_core = cq.importers.importStep(str(core_path)).val()
    core, motor_leads = restrain_motor_leads(source_core)
    report["motor_lead_refinement"] = {
        "reference_only": "AHG red/green/yellow/blue flexible leads; rigid core solids unchanged",
        "connector_endpoints_preserved": True,
        "routing": "4mm nominal upward bend with separated Y lanes; restrain actual wires in this envelope",
        "qualification": "Illustrative flexible routing, not wire-length, insulation or strain-relief qualification",
        "bounds_mm": bounds(motor_leads),
        "source_core_sha256": hashlib.sha256(core_path.read_bytes()).hexdigest(),
        "connector_termination_overlap_mm3": volume(motor_leads.intersect(source_core.Solids()[91]))}
    require_clear("Restrained leads to rigid core", motor_leads,
                  {f"Core_{i}": s for i, s in enumerate(source_core.Solids())
                   if i not in range(91, 96)}, report)
    for i, lead in enumerate(motor_leads.Solids()):
        require_clear("Restrained lead separation", lead,
                      {f"Lead_{j}": s for j, s in enumerate(motor_leads.Solids()) if j > i}, report)
    cq.exporters.export(core, str(STEP / "Core_With_Restrained_AHG_Lead_References_REVIEW.step"))
    refs = {n: load(n) for n in (
        "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
        "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount")}
    require_clear("Restrained motor leads to accessories", motor_leads, refs, report)
    carriage = compound([core, *refs.values()])
    pins, magnets = [], []
    for x in (-6, 6):
        pins.append(cylinder_y(x, 22, 38.5, 48.5, 2.48).fuse(
            cq.Solid.makeCone(2.48, 1, 2, cq.Vector(x, 48.5, 22), cq.Vector(0, 1, 0))))
        magnets.append(cylinder_y(x, -2, 41.7, 45.7, 3))
    coupling = compound([*pins, *magnets])
    report["coupling"] = {
        "pin_diameter_mm": 4.96, "bushing_bore_mm": 5.04,
        "diametral_clearance_mm": 0.08,
        "tool_dock_magnet_face_gap_mm": 45.960082 - 45.7,
        "pin_and_tool_magnet_backplate_interference_mm3": volume(coupling.intersect(p18))}
    require_clear("Coupling hardware to dock", coupling, {"Dock": dock, **{
        f"DockHardware_{i}": original[i] for i in (1, 2, 4, 5, 8, 9, 10, 11, 12, 13)}}, report)
    report["inherited_snap_detents_mm3"] = {
        str(i): volume(dock.intersect(original[i])) for i in (1, 2)}
    report["snap_detent_note"] = (
        "Two 0.9 mm side nibs on each jaw geometrically overlap the dock; preserved as "
        "snap retention, not counted as rigid collision-free or physically qualified.")
    report["coupling_retention_note"] = (
        "Pin/bushing engagement and magnet gap retained; magnet holding force, jaw deflection, "
        "wear and T-lug load capacity are not validated.")
    export_print("P25_Closed_Panel_Side2510_Dock_REVIEW", dock, report)
    chute = original[6].cut(cylinder_y(0, -78.88, 18, 21.01, 1.6)).clean()
    export_print("P26_Nozzle_Entry_Clearance_Chute_REVIEW", chute, report)
    report["chute_refinement"] = {
        "removed_mm3": volume(original[6]) - volume(chute),
        "entry_relief": "Radius1.6 longitudinal nozzle-tip clearance at purge-window rear lip"}

    shelf_cut = box(-16, -13.5, 10, 38, -27, -22.5)
    red_body = load("RedLizard_Side2510_Clearance_Refined_REVIEW").cut(shelf_cut).clean()
    fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
    fan_box = box(11.45, 21.45, 13, 38, -47.8, -22.8)
    red_fan_screws, red_inserts = [], []
    for z in (-25.3, -45.3):
        red_fan_screws.append(cylinder_x(35.5, z, 6.8, 20.8, 1.25).fuse(
            cylinder_x(35.5, z, 20.8, 21.6, 2.25)).translate((0.15, 0, 0)))
        red_inserts.append(cylinder_x(35.5, z, 6.8, 9.8, 1.75).cut(
            cylinder_x(35.5, z, 6.7, 9.9, 1.05)).translate((0.15, 0, 0)))
    variants = {
        "Bambu": dict(body=load("Bambu_One_Piece_Docking_Audited_REVIEW").cut(shelf_cut).clean(),
                      hotend=load("Tool2510_Reversed_Bambu_Reference_REVIEW"), fan=fan, envelope=fan_box,
                      fan_screws=load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW"),
                      inserts=load("Tool2510_Two_Inner_Entry_L3_Heatsets_REVIEW"),
                      hardware=load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")),
        "RedLizard": dict(body=red_body, hotend=load("P17M_RedLizard_Hotend_Reference"),
                          fan=fan.translate((0.15, 0, 0)), envelope=fan_box.translate((0.15, 0, 0)),
                          fan_screws=compound(red_fan_screws), inserts=compound(red_inserts)),
    }
    report["shelf_refinement"] = {
        "previous_left_edge_x_mm": -14, "new_left_edge_x_mm": -13.5,
        "cut_domain_bounds_mm": [-16, -13.5, 10, 38, -27, -22.5],
        "variants": {},
        "qualification": "Unused shelf stock removal only; protected hardware is checked below. "
                         "Not a stiffness, vibration or fatigue qualification."}
    for label, baseline_name in (
            ("Bambu", "Bambu_One_Piece_Docking_Audited_REVIEW"),
            ("RedLizard", "RedLizard_Side2510_Clearance_Refined_REVIEW")):
        baseline = load(baseline_name)
        refined = variants[label]["body"]
        removed = baseline.intersect(shelf_cut)
        conservation_error = abs(volume(baseline) - volume(refined) - volume(removed))
        removed_bounds = bounds(removed)
        protected = {n: s for n, s in variants[label].items()
                     if n not in ("body", "envelope")}
        protected.update(Backplate=p18, Coupling=coupling)
        distances = {n: removed.distance(s) for n, s in protected.items()}
        evidence = {
            "baseline_file": f"{baseline_name}.step",
            "baseline_sha256": hashlib.sha256((STEP / f"{baseline_name}.step").read_bytes()).hexdigest(),
            "operation": "Subtractive shelf cut applied directly to revision-21 body",
            "removed_volume_mm3": volume(removed), "volume_conservation_error_mm3": conservation_error,
            "removed_bounds_mm": removed_bounds,
            "removed_stock_to_protected_parts_mm": distances}
        report["shelf_refinement"]["variants"][label] = evidence
        if (conservation_error > 0.001 or removed_bounds[0] < -14.0001 or
                removed_bounds[1] > -13.4999 or min(distances.values()) < 2):
            raise ValueError(f"Unsafe/unexpected unused shelf trim: {label}")
        export_print(BODY_NAMES[label], refined, report)
    gantry_meta = json.loads((primitives.WORK / "gantry_meta.json").read_text())
    gantry = {m["name"]: cq.Shape.cast(s) for m, (s, _) in zip(
        gantry_meta, primitives.load_brep_list(primitives.WORK / "gantry_cache.brep"))}
    beacon = [cq.Shape.cast(s).translate((0, 3.2, -75)) for s in
              primitives.load_step(primitives.SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")]
    top_ko = beacon[1].intersect(box(-20, 20, -20, 20, -76.61, -56.61))
    acc_hw = {n: cq.Shape.cast(s) for n, s in primitives.build_accessory_hardware()}
    cable = cq.Shape.cast(primitives.make_cable_pipe(1.5, -15.8, y_back=-34.9))
    report["probe_cable_refinement"] = {
        "rear_center_y_mm": -34.9, "previous_y_mm": -34.5,
        "endpoints_and_bend_radius_unchanged": True,
        "inherited_P24_route_overlap_mm3": volume(cable.intersect(refs["P24_EBB42_Controller_Mount"])),
        "qualification": "P24 entry overlap is inherited, unchanged, and needs a later cable/mount routing audit."}
    report["probe_cable_refinement"]["upper_bend_screen"] = []
    for candidate_z in (-13, -12, -11.5):
        candidate = cq.Shape.cast(primitives.make_cable_pipe(1.5, candidate_z, y_back=-34.9))
        report["probe_cable_refinement"]["upper_bend_screen"].append({
            "candidate_end_z_mm": candidate_z, "adopted": False,
            "P20_overlap_mm3": volume(candidate.intersect(refs["P20_CPAP_Hose_Inlet"])),
            "P24_overlap_mm3": volume(candidate.intersect(refs["P24_EBB42_Controller_Mount"])),
            "P24_clearance_mm": candidate.distance(refs["P24_EBB42_Controller_Mount"])})
    report["probe_cable_refinement"]["upper_bend_screen_conclusion"] = (
        "Raising the upper bend clears P24 only by colliding with the P20 cable-channel roof. "
        "These candidates also move the free endpoint; none is an approved replacement route. "
        "Original accessory prints and current cable endpoints remain unchanged.")
    require_clear("Revised cable to CPAP guide", cable,
                  {n: s for n, s in refs.items() if n != "P24_EBB42_Controller_Mount"}, report)
    carto = compound(cq.Shape.cast(s).rotate((0, 0, 0), (0, 0, 1), 180).translate(
        (0, -13.00701, -75)) for s in primitives.load_step(
            primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")[:100])
    ebb = compound(cq.Shape.cast(s).translate((-20, -20, 0)).rotate(
        (0, 0, 0), (0, 1, 0), 180).rotate((0, 0, 0), (1, 0, 0), 90).translate(
            (-1.248, -31.630, 6.5)) for s, _ in
        primitives.load_brep_list(primitives.WORK / "ebb42_cache.brep"))
    electronics = dict(Beacon=compound(beacon[2:5]), Beacon_Bottom_Keepout=beacon[0],
                       Cartographer=carto, EBB42=ebb, Probe_Cable=cable, **acc_hw)
    carriage = compound([carriage, *(s for n, s in electronics.items()
                                     if n not in ("Beacon_Bottom_Keepout", "Cartographer"))])
    for label, v in variants.items():
        print(f"Auditing {label} tool/dock", flush=True)
        vr = report["variants"][label] = {}
        tip = v["hotend"].BoundingBox().zmin
        rise = tip + 78.88
        # Retain the pad footprint and ramp, but seat it on the existing rigid floor.
        pad = original[3].translate((0, 0, rise)).intersect(
            box(-4, 4, 20, 30, -81.0794, tip + 0.01)).clean()
        blades = original[7]
        if rise > 0:
            blades = blades.fuse(original[7].translate((0, 0, rise))).clean()
        for x in (-2.2, 0, 2.2):
            blades = blades.cut(cylinder_y(x, tip, 9, 12.5, 0.75))
        blades = blades.clean()
        export_print(f"{label}_Dock_Ooze_Pad_SILICONE_REVIEW", pad, report)
        export_print(f"{label}_Dock_Wiper_SILICONE_REVIEW", blades, report)
        dock_parts = {f"Dock_{i}": s for i, s in enumerate(original)}
        dock_parts.update(Dock_0=dock, Dock_3=pad, Dock_7=blades)
        dock_parts["Dock_6"] = chute
        for i, x in ((4, -10), (5, 10)):
            dock_parts[f"Dock_{i}"] = cylinder_y(
                x, 7.2206, DOCK_SCREW_HEAD_Y - 10, DOCK_SCREW_HEAD_Y, 2.5).fuse(
                    cylinder_y(x, 7.2206, DOCK_SCREW_HEAD_Y, DOCK_SCREW_HEAD_Y + 3, 4.4))
        stationary_dock = compound(dock_parts.values())
        tool_parts = {n: s for n, s in v.items() if n != "envelope"}
        tool_parts.update(Backplate=p18, Coupling=coupling)
        tool = compound(tool_parts.values())
        vr["nozzle_tip_z_mm"] = tip
        vr["pad_top_z_mm"] = pad.BoundingBox().zmax
        vr["wiper_top_z_mm"] = blades.BoundingBox().zmax
        vr["pad_floor_z_mm"] = pad.BoundingBox().zmin
        vr["fan_to_hotend_mm"] = v["envelope"].distance(v["hotend"])
        vr["fan_center_mm"] = [16.45 + (0.15 if label == "RedLizard" else 0), 25.5, -35.3]
        vr["fan_screw_outer_x_mm"] = v["fan_screws"].BoundingBox().xmax
        vr["nozzle_contact_height_error_mm"] = abs(tip - pad.BoundingBox().zmax)
        vr["pad_support_area_finite_shift_mm2"] = volume(pad.translate((0, 0, -0.01)).intersect(dock)) / 0.01
        if vr["nozzle_contact_height_error_mm"] > 0.001 or vr["pad_support_area_finite_shift_mm2"] < 20:
            report["failures"].append({"check": f"{label} nozzle-pad height/support"})
        vr["dock_pairwise_intersections"] = []
        for i, (name, s) in enumerate(dock_parts.items()):
            for other, target in list(dock_parts.items())[i + 1:]:
                hit = overlaps(s, {other: target})
                if hit:
                    snap = name == "Dock_0" and other in ("Dock_1", "Dock_2")
                    vr["dock_pairwise_intersections"].append(
                        {"a": name, "b": other, "hits": hit,
                         "classification": "Preserved flexible snap detent" if snap else "UNEXPECTED"})
                    if not snap:
                        report["failures"].append({"check": f"{label} dock internal interference", "a": name,
                                                   "b": other, "hits": hit})
        for x in (-10, 10):
            require_clear(f"{label} dock M5 driver", cylinder_y(
                x, 7.2206, DOCK_SCREW_HEAD_Y + 3, DOCK_SCREW_HEAD_Y + 33, 2),
                          {"Dock": dock}, report)
        for x in (-11.75, 11.75):
            require_clear(f"{label} chute M3 driver", cylinder_y(x, -82.44, 16.91, 36.91, 1.5),
                          {"Dock": dock, "Chute": chute}, report)
        vr["parked_intersections"] = {}
        for name, s in tool_parts.items():
            vr["parked_intersections"][name] = require_clear(
                f"{label}/{name} parked", s, dict(dock_parts, **gantry, **electronics), report)
        for name in ("body", "fan_screws", "inserts"):
            require_clear(f"{label}/{name} external", v[name],
                          dict(Core=core, **refs, **gantry, **electronics), report)
        require_clear(f"{label} fan envelope external", v["envelope"],
                      dict(Core=core, Hotend=v["hotend"], **refs, **gantry, **electronics), report)
        require_clear(f"{label} body hotend", v["body"], {"Hotend": v["hotend"]}, report)
        require_clear(f"{label} fan/body", v["envelope"], {"Body": v["body"]}, report)
        require_clear(f"{label} fan screws/body", v["fan_screws"], {"Body": v["body"], "Fan": v["fan"]}, report)
        require_clear(f"{label} pad seat", pad, {"Dock": dock}, report)
        require_clear(f"{label} wiper seat", blades, {"Dock": dock, "Chute": chute}, report)
        vr["new_metal_probe_keepout"] = require_clear(
            f"{label} coupling/cooling probe keepout", top_ko,
            {"Coupling": coupling, "Fan": v["envelope"], "Fan_Screws": v["fan_screws"],
             "Fan_Inserts": v["inserts"]}, report)
        vr["fan_heatset_checks"] = []
        axes = [(15.5, -25.3), (35.5, -25.3)] if label == "Bambu" else [(35.5, -25.3), (35.5, -45.3)]
        dx = 0 if label == "Bambu" else 0.15
        for y, z in axes:
            shoulder = cylinder_x(y, z, 9.8, 10.8, 2.5).cut(cylinder_x(y, z, 9.8, 10.8, 1.4)).translate((dx, 0, 0))
            surround = cylinder_x(y, z, 6.8, 9.8, 2.5).cut(cylinder_x(y, z, 6.8, 9.8, 1.75)).translate((dx, 0, 0))
            seat = {"axis_yz_mm": [y, z], "missing_shoulder_mm3": volume(shoulder.cut(v["body"])),
                    "missing_surround_mm3": volume(surround.cut(v["body"]))}
            vr["fan_heatset_checks"].append(seat)
            if max(seat["missing_shoulder_mm3"], seat["missing_surround_mm3"]) > 0.001:
                report["failures"].append({"check": f"{label} incomplete heatset", "result": seat})
            require_clear(f"{label} heatset access", cylinder_x(y, z, -16, 6.8, 2.2).translate((dx, 0, 0)),
                          {"Body": v["body"]}, report)
            require_clear(f"{label} fan driver", cylinder_x(y, z, 21.6, 41.6, 1.5).translate((dx, 0, 0)),
                          {"Body": v["body"], "Hotend": v["hotend"], "Fan": v["envelope"]}, report)
        vr["hotend_mount_checks"] = []
        if label == "RedLizard":
            for x in (-5.657, 5.657):
                for y in (17.043, 28.357):
                    driver = cq.Solid.makeCylinder(1.5, 20, cq.Vector(x, y, -16.7794048), cq.Vector(0, 0, 1))
                    require_clear(f"{label} hotend driver {x}/{y}", driver, {"Body": v["body"]}, report)
                    bearing = cq.Solid.makeCylinder(2.25, 0.2, cq.Vector(x, y, -19.4794048), cq.Vector(0, 0, 1)).cut(
                        cq.Solid.makeCylinder(1.35, 0.2, cq.Vector(x, y, -19.4794048), cq.Vector(0, 0, 1)))
                    missing = volume(bearing.cut(v["body"]))
                    vr["hotend_mount_checks"].append({"axis_xy_mm": [x, y], "missing_bearing_mm3": missing})
                    if missing > 0.001:
                        report["failures"].append({"check": f"{label} hotend screw lacks bearing", "axis": [x, y]})
        else:
            fixed = compound(s for i, s in enumerate(v["hotend"].Solids()) if i not in (3, 4))
            for x, z in HOTEND_AXES:
                require_clear(f"{label} heating-assembly driver, nozzle removed",
                              cylinder_y(x, z, 7.2, 27.2, 1.5),
                              {"Body": v["body"], "Fixed_Hotend": fixed, "Fan": v["envelope"]}, report)
                shoulder = cylinder_y(x, z, 31.1, 33.9, 2.5).cut(cylinder_y(x, z, 31.1, 33.9, 1.4))
                surround = cylinder_y(x, z, 33.9, 37.9, 2.5).cut(cylinder_y(x, z, 33.9, 37.9, 1.75))
                missing = volume(shoulder.cut(v["body"])) + volume(surround.cut(v["body"]))
                vr["hotend_mount_checks"].append({"axis_xz_mm": [x, z], "missing_seat_mm3": missing})
                if missing > 0.001:
                    report["failures"].append({"check": f"{label} incomplete hotend insert seat"})
        vr["approach_and_retreat_samples"] = 0
        vr["approach_hits"] = []
        vr["carriage_retreat_hits"] = []
        print(f"{label}: static checks complete; {len(report['failures'])} findings; checking motion", flush=True)
        if report["failures"]:
            (ROOT / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n")
            raise ValueError(f"Static refinement findings: {report['failures']}")
        # Tool and carriage approach from -Y; after release the tool stays parked.
        active_assembly = compound([tool, carriage])
        retreat_targets = dict(dock_parts, Parked_Tool=tool)
        for step in range(121):
            dy = -step * 0.5
            hits = translated_hits(active_assembly, dock_parts, (0, dy, 0))
            if hits:
                vr["approach_hits"].append({"y_mm": dy, "hits": hits})
            hits = translated_hits(carriage, retreat_targets, (0, dy, 0))
            if hits:
                vr["carriage_retreat_hits"].append({"y_mm": dy, "hits": hits})
            vr["approach_and_retreat_samples"] += 1
            if step % 40 == 0:
                print(f"{label}: docking sample {step}/120", flush=True)
        if vr["approach_hits"] or vr["carriage_retreat_hits"]:
            report["failures"].append({"check": f"{label} docking motion",
                                       "approach": vr["approach_hits"], "retreat": vr["carriage_retreat_hits"]})
        vr["tool_x_bounds_mm"] = bounds(tool)[:2]
        if bounds(tool)[0] < -22.50001 or bounds(tool)[1] > 22.50001:
            report["failures"].append({"check": f"{label} tool exceeds 45 mm"})
        v.update(tool=tool, dock=stationary_dock, dock_parts=dock_parts)
        assembly = cq.Assembly(name=f"{REVIEW_REVISION} {label} side fan toolhead and closed panel dock")
        for name, s in tool_parts.items():
            color = cq.Color(0.9, 0.65, 0.1) if name == "body" else cq.Color(0.55, 0.55, 0.58)
            assembly.add(s, name=f"Tool_{name}", color=color)
        dock_assembly = cq.Assembly(name=f"{REVIEW_REVISION} {label} nozzle-contact dock")
        for i, s in enumerate(dock_parts.values()):
            color = cq.Color(0.22, 0.4, 0.32)
            if i in (3, 7):
                color = cq.Color(0.95, 0.4, 0.1)
            elif i in (4, 5, 8, 9, 10, 11, 12, 13):
                color = cq.Color(0.6, 0.6, 0.63)
            assembly.add(s, name=DOCK_NAMES[i], color=color)
            dock_assembly.add(s, name=DOCK_NAMES[i], color=color)
        dock_output = STEP / f"{REVIEW_REVISION}_{label}_Closed_Panel_Dock_Complete_REVIEW.step"
        dock_assembly.export(str(dock_output))
        dock_import = cq.importers.importStep(str(dock_output)).val()
        if not dock_import.isValid() or len(dock_import.Solids()) != 14:
            report["failures"].append({"check": f"{label} complete dock STEP reimport"})
        assembly.add(core, name="Rigid_Core_With_Restrained_Lead_References", color=cq.Color(0.5, 0.52, 0.55))
        for n, s in refs.items():
            assembly.add(s, name=n, color=cq.Color(0.22, 0.4, 0.32))
        output = STEP / f"{REVIEW_REVISION}_{label}_Toolhead_And_Closed_Panel_Dock_REVIEW.step"
        assembly.export(str(output))
        imported = cq.importers.importStep(str(output)).val()
        expected = sum(len(s.Solids()) for s in (*tool_parts.values(), *dock_parts.values(), core, *refs.values()))
        vr["export"] = {"solids": len(imported.Solids()), "expected_solids": expected,
                        "valid": imported.isValid(), "sha256": hashlib.sha256(output.read_bytes()).hexdigest()}
        if not imported.isValid() or len(imported.Solids()) != expected:
            report["failures"].append({"check": f"{label} STEP reimport"})
    from audit_low_z_bed_clearance import audit_bed_clearance
    audit_bed_clearance(variants, report)
    if report["failures"]:
        report["status"] = "BLOCKED_LOW_Z_BED_COLLISION"
        report["passed"] = False
        (ROOT / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n")
        raise ValueError("Do not qualify the rack: parked hardware intersects the bed at printing height")
    print("Auditing mixed-tool rack pitch", flush=True)
    report["neighbor_checks"] = []
    for label, v in variants.items():
        active_assembly = compound([v["tool"], carriage])
        for neighbor_label, neighbor in variants.items():
            for dx in (-37.3, 37.3):
                neighbor_shape = compound([neighbor["tool"], neighbor["dock"]]).translate((dx, 0, 0))
                hits = []
                for dy in range(0, 61):
                    overlap = translated_hits(active_assembly, {"Neighbor": neighbor_shape}, (0, -dy, 0))
                    if overlap:
                        hits.append({"retreat_y_mm": -dy, "intersections_mm3": overlap})
                check = {"tool": label, "neighbor": neighbor_label, "pitch_x_mm": dx, "hits": hits}
                report["neighbor_checks"].append(check)
                if hits:
                    report["failures"].append({"check": "37.3 mm neighboring docking path", "result": check})
    report["rack"] = {
        "pitch_mm": 37.3, "collars_touch": True, "centers_x_mm": [7 + 37.3 * i for i in range(10)],
        "center_span_mm": 335.7, "software_travel_assumed_mm": [0, 350],
        "unchanged": "P29 rack mounts, P30 end spacers, existing 2020 crossbar stock and X center datums",
        "qualification": "See full_ten_tool_rack for all-bay hardware, rail stroke and X-traverse checks."}
    from audit_ten_tool_rack import audit_rack
    audit_rack(variants, carriage, electronics, report)
    report["limitations"] = [
        "Physical docking repeatability, jaw snap strain, magnet strength and collision margins need measurement.",
        "Cam actuation/servo/peel moves are not simulated; straight approach/retreat is not a complete machine sequence.",
        "Fan cooling, polymer creep, vibration, inserts, screw availability and actual connectors remain unqualified.",
        "Red Lizard minimum fan gap improves from 0.45 to 0.60 mm; actual tolerance stack may still require more clearance.",
        "No parked fan power contacts/control/interlock implemented; fan must remain powered through cooldown.",
        "Pads/wipers are silicone references, not ordinary rigid filament prints. Fit their heights to measured physical nozzle datum.",
        "Bambu tip is the reconstructed reference; do not shift hotend just to make synthetic CAD match intended datum.",
        "Beacon geometry and Cartographer physical reference checked, not RF/EM calibration or thermal certification.",
    ]
    report["passed"] = not report["failures"]
    (ROOT / REPORT_NAME).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"passed": report["passed"], "failures": report["failures"]}, indent=2))
    if report["failures"]:
        raise ValueError("Refined docking audit failed")
    render_review()


if __name__ == "__main__":
    build()
