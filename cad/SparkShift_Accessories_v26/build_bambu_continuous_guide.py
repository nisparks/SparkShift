"""Close the Bambu filament transition/front gap and finish the fan mounting seats."""

import hashlib
import json

import cadquery as cq
import trimesh

from audit_tool_owned_2510 import bounds, compound, overlaps
from build_modular_toolhead import ROOT, STEP, STL, HOTEND_AXES, box, cylinder_y, load, volume


BODY_NAME = "Bambu_Continuous_Guide_Clean_Fan_Mount_R25_REVIEW"


def render_review():
    from PIL import Image, ImageDraw
    from render_accessories_v26 import make_actor, render_view, shape_to_polydata
    from build_modular_toolhead import primitives

    temp = primitives.WORK / "bambu_r25_render.stl"
    panels = []
    clip = box(-30, 30, 10, 40, -55, -10)
    for name, title in (
        ("Bambu_One_Piece_Shelf_Clearance_R22_REVIEW", "BEFORE: exposed inlet span / upper step / original fan seats"),
        (BODY_NAME, "R25: enclosing inlet socket / filled step / clean fan seats"),
    ):
        shapes = [
            (load(name).intersect(clip), (0.95, 0.67, 0.1)),
            (load("Tool2510_Reversed_Bambu_Reference_REVIEW").intersect(clip), (0.65, 0.65, 0.68)),
        ]
        actors = [make_actor(shape_to_polydata(s.wrapped, temp), c, edge_vis=True) for s, c in shapes]
        path = primitives.WORK / f"bambu_r25_panel_{len(panels)}.png"
        render_view(actors, (180, -65, 10), (0, 25, -30), (0, 0, 1),
                    path, width=1000, height=1100, zoom=1.05)
        image = Image.open(path).convert("RGB")
        ImageDraw.Draw(image).text((15, 15), title, fill=(20, 20, 20))
        panels.append(image)
        path.unlink()
    image = Image.new("RGB", (2000, 1100), "white")
    for i, panel in enumerate(panels):
        image.paste(panel, (1000 * i, 0))
    comparison = ROOT / "images" / "47_bambu_continuous_guide_before_after.png"
    image.save(comparison)
    shapes = [
        (load(BODY_NAME), (0.95, 0.67, 0.1)),
        (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.65, 0.65, 0.68)),
        (load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW"), (0.16, 0.16, 0.18)),
        (load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW"), (0.4, 0.4, 0.42)),
    ]
    actors = [make_actor(shape_to_polydata(s.wrapped, temp), c, edge_vis=True) for s, c in shapes]
    complete = ROOT / "images" / "48_bambu_continuous_guide_with_fan.png"
    render_view(actors, (180, -65, 10), (0, 25, -14.7), (0, 0, 1),
                complete, width=1200, height=1400, zoom=0.85)
    image = Image.open(complete)
    ImageDraw.Draw(image).text((20, 20), "R25 BAMBU - LOCAL CAD REVIEW ONLY - FAN POSITION UNCHANGED", fill=(20, 20, 20))
    image.save(complete)
    temp.unlink()
    return [{"file": "images/" + p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
            for p in (comparison, complete)]


def cylinder_z(radius, z0, z1):
    return cq.Solid.makeCylinder(radius, z1 - z0, cq.Vector(0, 22.7, z0), cq.Vector(0, 0, 1))


def cylinder_x(y, x0, x1, radius):
    return cq.Solid.makeCylinder(radius, x1 - x0, cq.Vector(x0, y, -25.3), cq.Vector(1, 0, 0))


def build():
    source_name = "Bambu_One_Piece_Shelf_Clearance_R22_REVIEW"
    baseline = load(source_name)
    hotend = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    refs = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet",
        "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
        "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
        "Core_With_Restrained_AHG_Lead_References_REVIEW",
    )}
    fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
    fan_envelope = box(11.45, 21.45, 13, 38, -47.8, -22.8)
    fan_screws = load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW")
    fan_inserts = load("Tool2510_Two_Inner_Entry_L3_Heatsets_REVIEW")
    hardware = load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")
    # The inlet tube is radius2.375, centered at Y22.7, ending at Z-29.48.
    sleeve_blank = cylinder_z(4, -30.4, -25)
    front_blank = box(-10, 10, 31.8, 35.93, -19.6, -16.8)
    front_riser = box(-9, 9, 11.5, 12.5, -19.6, -17.2794)
    front_riser_blank_volume = volume(front_riser)
    core = refs["Core_With_Restrained_AHG_Lead_References_REVIEW"]
    for delta in ((0, 0, 0), (-0.15, 0, 0), (0.15, 0, 0), (0, -0.15, 0),
                  (0, 0.15, 0), (0, 0, -0.15), (0, 0, 0.15)):
        front_riser = front_riser.cut(core.translate(delta))
    boss_blanks = [
        cylinder_x(y, 7.45, 11.2, 3).intersect(box(7, 12, 13, 38, -29, -22))
        for y in (15.5, 35.5)]
    p18 = refs["P18_Tool_docking_backplate_3010"]
    p18_clearance = [
        p18, *(p18.translate(d) for d in (
            (-0.15, 0, 0), (0.15, 0, 0), (0, -0.15, 0),
            (0, 0.15, 0), (0, 0, -0.15), (0, 0, 0.15))),
    ]
    bosses = []
    for boss in boss_blanks:
        for clearance in p18_clearance:
            boss = boss.cut(clearance)
        bosses.append(boss)
    body = baseline.fuse(sleeve_blank, front_blank, front_riser, *bosses)
    pocket = cylinder_z(2.625, -30.41, -29.28)
    guide = cylinder_z(1.15, -29.29, -25)
    funnel = cq.Solid.makeCone(
        1.15, 2.15, 1.2, cq.Vector(0, 22.7, -27), cq.Vector(0, 0, 1))
    body = body.cut(pocket).cut(guide).cut(funnel)
    for x in (-6, 6):
        body = body.cut(cylinder_y(x, -19.26, 31, 37, 2.28))
    for y in (15.5, 35.5):
        body = body.cut(cylinder_x(y, -16, 7.45, 2.2))
        body = body.cut(cylinder_x(y, 7.44, 10.45, 1.55))
        body = body.cut(cylinder_x(y, 10.45, 11.46, 1.4))
        body = body.cut(cq.Solid.makeCone(
            1.4, 1.7, 0.3, cq.Vector(10.9, y, -25.3), cq.Vector(1, 0, 0)))
    body = body.clean()
    if not body.isValid() or len(body.Solids()) != 1:
        raise ValueError("Revised Bambu print is invalid or disconnected")
    report = {
        "status": "LOCAL_BAMBU_GEOMETRY_REVIEW_NOT_MACHINE_OR_THERMAL_QUALIFICATION",
        "failures": [],
        "baseline": {"file": source_name + ".step", "sha256": hashlib.sha256(
            (STEP / f"{source_name}.step").read_bytes()).hexdigest()},
        "fan_center_mm": [16.45, 25.5, -35.3],
        "filament_transition": {
            "axis_xy_mm": [0, 22.7], "legacy_guide_axis_y_mm": 22.68,
            "existing_exposed_axial_gap_mm": 3.48,
            "guide_outer_diameter_mm": 8, "guide_bore_diameter_mm": 2.3,
            "guide_sleeve_bottom_z_mm": -30.4, "hotend_inlet_top_z_mm": -29.48,
            "socket_top_z_mm": -29.28, "socket_diameter_mm": 5.25,
            "inlet_outer_diameter_mm": 4.75,
            "nominal_socket_radial_clearance_mm": 0.25,
            "nominal_internal_axial_clearance_mm": 0.2,
            "sleeve_overlap_below_inlet_top_mm": 0.92,
            "qualification": "An enclosing socket removes the exposed filament span; internal assembly clearance is intentional. Cool-side polymer temperature, print accuracy and actual hotend inlet dimensions require physical confirmation.",
        },
        "front_fill": {
            "blank_bounds_mm": bounds(front_blank),
            "front_riser_bounds_mm": bounds(front_riser),
            "front_riser_core_relief_removed_mm3": front_riser_blank_volume - volume(front_riser),
            "core_relief_note": "The unwanted front undercut is filled except where actual fixed-core material and a 0.15 mm translated clearance screen require relief.",
            "preserved_P18_passages": "X+/-6, Z-19.26, diameter4.56 along Y",
        },
        "fan_holes": {
            "axes_yz_mm": [[15.5, -25.3], [35.5, -25.3]],
            "boss_outer_diameter_mm": 6,
            "boss_edge_limits_y_mm": [13, 38],
            "insert_seat_x_mm": [7.45, 10.45], "insert_pilot_diameter_mm": 3.1,
            "screw_clearance_diameter_mm": 2.8,
            "outer_edge_chamfer_mm": 0.3,
            "inner_insert_access_diameter_mm": 4.4,
            "hardware": "Unchanged two M2.5x14 ultra-low-head screws and M2.5 L3 OD3.5 heatsets.",
            "qualification": "Only the two upper printed mounting seats are used. Lower fan-frame holes remain unused reference geometry; the fan frame is not a printed shroud.",
        },
        "unchanged": "Fan pose and hardware, physical hotend, core, CPAP, probe/EBB42, P18, dock geometry and pitch.",
    }
    protected = dict(refs, Hotend=hotend, Fan_Envelope=fan_envelope, Fan_Screws=fan_screws,
                     Hotend_Screws=compound(hardware.Solids()[i] for i in (1, 4, 7)),
                     Hotend_Washers=compound(hardware.Solids()[i] for i in (2, 5)))
    report["body_intersections_mm3"] = overlaps(body, protected)
    if report["body_intersections_mm3"]:
        raise ValueError(f"New body interference: {report['body_intersections_mm3']}")
    report["geometry_checks"] = {}
    checks = report["geometry_checks"]
    # An annular witness covers the former open span and wraps around the inlet.
    sleeve_wall = cylinder_z(3.8, -30.39, -25.1).cut(cylinder_z(2.8, -30.4, -25))
    checks["missing_enclosing_sleeve_wall_mm3"] = volume(sleeve_wall.cut(body))
    checks["guide_bore_obstruction_mm3"] = volume(body.intersect(cylinder_z(1.149, -29.28, -25.01)))
    checks["inlet_socket_obstruction_mm3"] = volume(
        body.intersect(cylinder_z(2.624, -30.4, -29.281)))
    checks["continuous_filament_axis_obstruction_mm3"] = volume(
        body.intersect(cylinder_z(0.9, -29.48, -8.31)))
    front_witness = front_blank
    for x in (-6, 6):
        front_witness = front_witness.cut(cylinder_y(x, -19.26, 30, 38, 2.281))
    checks["missing_front_fill_mm3"] = volume(front_witness.cut(body))
    checks["missing_front_riser_mm3"] = volume(front_riser.cut(body))
    for y in (15.5, 35.5):
        checks[f"fan_{y}_pilot_obstruction_mm3"] = volume(body.intersect(cylinder_x(y, 7.45, 10.45, 1.549)))
        checks[f"fan_{y}_screw_obstruction_mm3"] = volume(body.intersect(cylinder_x(y, 10.45, 11.45, 1.399)))
        checks[f"fan_{y}_insert_access_obstruction_mm3"] = volume(
            body.intersect(cylinder_x(y, -16, 7.449, 2.199)))
        shoulder = cylinder_x(y, 10.45, 10.9, 2.5).cut(cylinder_x(y, 10.44, 10.91, 1.401))
        checks[f"fan_{y}_missing_retaining_shoulder_mm3"] = volume(shoulder.cut(body))
        surround = cylinder_x(y, 7.75, 10.4, 2.5).cut(cylinder_x(y, 7.74, 10.41, 1.751))
        checks[f"fan_{y}_missing_insert_surround_mm3"] = volume(surround.cut(body))
    for x, z in HOTEND_AXES:
        seat = cylinder_y(x, z, 31.1, 33.9, 2.5).cut(cylinder_y(x, z, 31, 34, 1.401))
        checks[f"hotend_{x}_{z}_missing_shoulder_mm3"] = volume(seat.cut(body))
    if max(abs(v) for v in checks.values()) > 0.001:
        raise ValueError(f"Feature validation failed: {checks}")
    if bounds(body)[0] < -13.5001 or bounds(body)[1] > 15.0001:
        raise ValueError("Changed established tool width")
    if bounds(body)[3] > 38.0001:
        raise ValueError("New fan bosses extend beyond the original depth envelope")
    from build_refined_docking_review import translated_hits
    dock = load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")
    tool = compound([body, hotend, hardware, fan, fan_screws, fan_inserts])
    report["dock_path_samples"] = []
    for sample in range(121):
        hits = translated_hits(tool, {"Existing_Bambu_Dock": dock}, (0, -sample * 0.5, 0))
        if hits:
            report["dock_path_samples"].append({"withdrawal_mm": sample * 0.5, "hits": hits})
    if report["dock_path_samples"]:
        raise ValueError(f"Revised tool interferes with existing dock: {report['dock_path_samples']}")
    report["dock_path_scope"] = "Fixed-X local Y0..-60 sampled every0.5mm; inherited dock remains unchanged."
    report["neighbor_motion"] = []
    from audit_low_z_bed_clearance import load_parked_variants
    parked_variants = load_parked_variants()
    for label, neighbor in (
        ("Bambu", compound([tool, dock])),
        ("RedLizard", compound([
            parked_variants["RedLizard"]["tool"], parked_variants["RedLizard"]["dock"]])),
    ):
        for dx in (-37.3, 37.3):
            hits = []
            target = neighbor.translate((dx, 0, 0))
            for sample in range(61):
                result = translated_hits(tool, {"Neighbor": target}, (0, -sample, 0))
                if result:
                    hits.append({"withdrawal_mm": sample, "hits": result})
            report["neighbor_motion"].append({"variant": label, "dx_mm": dx, "hits": hits})
            if hits:
                raise ValueError(f"Revised tool intersects neighbor: {label}/{dx}")
    removable = compound(hotend.Solids()[3:5])
    fixed = compound([body, hardware, fan_envelope, fan_screws, fan_inserts])
    report["hotend_service_samples"] = []
    for down, rear in [(d * 0.25, 0) for d in range(17)] + [(4, d) for d in range(1, 41)]:
        hits = translated_hits(removable, {"Fixed_Tool_Parts": fixed}, (0, -rear, -down))
        if hits:
            report["hotend_service_samples"].append({"down_mm": down, "rear_mm": rear, "hits": hits})
    if report["hotend_service_samples"]:
        raise ValueError(f"Guide traps hotend service path: {report['hotend_service_samples']}")
    report["hotend_service_scope"] = "Removed tool: down0..4 every0.25mm, then rearward0..40 every1mm; native latch/finger motion unqualified."
    report["printed_body"] = {"valid": True, "solids": 1, "bounds_mm": bounds(body),
                              "volume_mm3": volume(body), "net_volume_change_mm3": volume(body) - volume(baseline)}
    output = STEP / f"{BODY_NAME}.step"
    cq.exporters.export(body, str(output))
    stl = STL / f"{BODY_NAME}.stl"
    cq.exporters.export(body, str(stl), tolerance=0.03, angularTolerance=0.1)
    mesh = trimesh.load_mesh(stl)
    if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split(only_watertight=False)) != 1:
        raise ValueError("New print STL is not a single watertight mesh")
    imported = cq.importers.importStep(str(output)).val()
    if not imported.isValid() or len(imported.Solids()) != 1 or abs(volume(imported) - volume(body)) > 0.001:
        raise ValueError("Revised print STEP readback failed")
    report["printed_body"].update(watertight=True, winding_consistent=True, mesh_components=1,
                                  step_sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
                                  stl_sha256=hashlib.sha256(stl.read_bytes()).hexdigest())
    assembly = cq.Assembly(name="25 Bambu continuous guide and cleaned fan seats - local review")
    for name, shape, color in (
        ("Revised_Bambu_Print", body, (0.95, 0.67, 0.1)),
        ("Unchanged_Hotend", hotend, (0.65, 0.65, 0.68)),
        ("Unchanged_2510", fan, (0.16, 0.16, 0.18)),
        ("Hotend_Hardware", hardware, (0.45, 0.45, 0.48)),
        ("Fan_Screws", fan_screws, (0.4, 0.4, 0.42)),
        ("Fan_Inserts", fan_inserts, (0.75, 0.5, 0.15)),
    ):
        assembly.add(shape, name=name, color=cq.Color(*color))
    assembly_path = STEP / "25_Bambu_Continuous_Guide_Toolhead_REVIEW.step"
    assembly.export(str(assembly_path))
    count = sum(len(s.Solids()) for s in (body, hotend, fan, hardware, fan_screws, fan_inserts))
    readback = cq.importers.importStep(str(assembly_path)).val()
    if not readback.isValid() or len(readback.Solids()) != count:
        raise ValueError("Toolhead assembly readback failed")
    report["assembly_export"] = {"file": assembly_path.name, "solids": count, "valid": True,
                                 "sha256": hashlib.sha256(assembly_path.read_bytes()).hexdigest()}
    full_source_name = "21_Bambu_Toolhead_And_Closed_Panel_Dock_REVIEW"
    full_source = load(full_source_name)
    prior_body = load("Bambu_One_Piece_Docking_Audited_REVIEW")
    matches = [i for i, s in enumerate(full_source.Solids())
               if max(abs(a - b) for a, b in zip(bounds(s), bounds(prior_body))) < 0.001
               and abs(volume(s) - volume(prior_body)) < 0.01]
    if len(matches) != 1:
        raise ValueError("Cannot uniquely identify previous printed body in complete assembly")
    complete_checks = []
    for i, s in enumerate(full_source.Solids()):
        if i == matches[0]:
            continue
        before = sum(overlaps(prior_body, {"Reference": s}).values())
        after = sum(overlaps(body, {"Reference": s}).values())
        complete_checks.append({
            "reference_solid_index": i, "prior_intersection_mm3": before,
            "revised_intersection_mm3": after, "increase_mm3": after - before})
        if after - before > 0.001:
            raise ValueError(f"New complete-assembly interference at solid{i}: {after - before}")
    report["complete_assembly_interference_regression"] = {
        "reference_solids_checked": len(complete_checks),
        "maximum_increase_mm3": max(c["increase_mm3"] for c in complete_checks),
        "checks": complete_checks,
        "qualification": "Existing intentional insert interference remains; no increased intersection with any other complete-assembly solid.",
    }
    complete = cq.Assembly(name="25 Bambu complete carriage and dock - revised local print")
    complete.add(body, name="R25_Revised_Bambu_Print", color=cq.Color(0.95, 0.67, 0.1))
    for i, s in enumerate(full_source.Solids()):
        if i != matches[0]:
            complete.add(s, name=f"Unchanged_Reference_{i}", color=cq.Color(0.55, 0.57, 0.6))
    complete_path = STEP / "25_Bambu_Complete_Carriage_And_Dock_REVIEW.step"
    complete.export(str(complete_path))
    complete_readback = cq.importers.importStep(str(complete_path)).val()
    if not complete_readback.isValid() or len(complete_readback.Solids()) != len(full_source.Solids()):
        raise ValueError("Complete assembly roundtrip failed")
    report["complete_assembly_export"] = {
        "file": complete_path.name, "valid": True, "solids": len(complete_readback.Solids()),
        "sha256": hashlib.sha256(complete_path.read_bytes()).hexdigest(),
        "source_file": full_source_name + ".step",
        "source_sha256": hashlib.sha256((STEP / f"{full_source_name}.step").read_bytes()).hexdigest(),
        "replaced_body_index": matches[0],
        "qualification": "Only the printed Bambu body replaced; all other source solids retain their poses and geometry. Existing rack bed blocker and flexible cable-entry issue remain.",
    }
    report["limitations"] = [
        "Current rack low-Z bed collision remains unresolved; this is a local toolhead revision only.",
        "No physical thermal, strength, insert-pullout, fan airflow or machine commissioning.",
        "Enclosing guide socket must not be mistaken for a load-bearing hotend clamp or a zero-clearance polymer/metal fit.",
    ]
    source_names = list(refs) + [
        "Tool2510_Reversed_Bambu_Reference_REVIEW",
        "Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW",
        "Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW",
        "Tool2510_Two_Inner_Entry_L3_Heatsets_REVIEW",
        "Tool2510_Existing_Tool_M2_5_Hardware_REVIEW",
        "21_Bambu_Closed_Panel_Dock_Complete_REVIEW",
    ]
    report["unchanged_source_sha256"] = {
        n: hashlib.sha256((STEP / f"{n}.step").read_bytes()).hexdigest()
        for n in source_names}
    report["neighbor_source_evidence"] = {k: v["source"] for k, v in parked_variants.items()}
    report["images"] = render_review()
    (ROOT / "verification_bambu_continuous_guide_r25.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    build()
