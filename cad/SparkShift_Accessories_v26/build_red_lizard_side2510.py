"""One-piece Red Lizard side-fan feasibility build; does not alter the Bambu or dock."""

import hashlib
import json

import cadquery as cq
import trimesh

from build_modular_toolhead import ROOT, STEP, STL, box, load, volume, primitives
from build_tool_owned_2510_review import cylinder_x
from audit_tool_owned_2510 import compound, bounds, overlaps


def build():
    core = cq.importers.importStep(str(primitives.WORK / "modular_audit_core_reference.step")).val()
    red = load("P17M_RedLizard_Hotend_Reference")
    refs = {n: load(n) for n in (
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge",
        "P22_CPAP_Lower_Plenum", "P23_Beacon_Cartographer_Mount",
        "P24_EBB42_Controller_Mount", "P25_SparkShift_3010_Dock")}
    stem = load("P17M_Reusable_Carrier_3010_REVIEW").intersect(box(-16, 16, 10, 36, -19.2794, 50))
    shelf = load("P17M_RedLizard_Adapter_V3_REVIEW").intersect(
        box(-16, 16, 10, 36, -24.2794048, -17.2794))
    body = stem.fuse(shelf).clean()
    # Only the clear +Y edge is supported; neither inner heatset enters the fins.
    body = body.fuse(box(7.45, 11.45, 33, 38, -47.8, -22.8))
    body = body.fuse(box(7.45, 11.2, 31.5, 35.5, -24.2794048, -22.8))
    body = body.cut(box(11.45, 21.7, 12.75, 38.25, -48.05, -22.55))
    body = body.cut(refs["P18_Tool_docking_backplate_3010"])
    fan = load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW")
    envelope = box(11.45, 21.45, 13, 38, -47.8, -22.8)
    screws, inserts = [], []
    for z in (-25.3, -45.3):
        body = body.cut(cylinder_x(35.5, z, -16, 6.8, 2.2))
        body = body.cut(cylinder_x(35.5, z, 6.7, 9.8, 1.55))
        body = body.cut(cylinder_x(35.5, z, 9.8, 10.9, 1.4))
        screws.append(cylinder_x(35.5, z, 6.8, 20.8, 1.25).fuse(
            cylinder_x(35.5, z, 20.8, 21.6, 2.25)))
        inserts.append(cylinder_x(35.5, z, 6.8, 9.8, 1.75).cut(
            cylinder_x(35.5, z, 6.7, 9.9, 1.05)))
    body = body.clean()
    screws, inserts = compound(screws), compound(inserts)
    report = {
        "status": "GEOMETRIC_FEASIBILITY_NOT_THERMALLY_OR_PHYSICALLY_QUALIFIED",
        "fan_center_mm": [16.45, 25.5, -35.3],
        "mount": "Two +Y-edge holes, upper and lower, instead of two upper holes; 5 mm edge rail, no airflow shroud",
        "hardware": "Two M2.5x14 OD<=4.5 H<=0.8 heads; two inner-entry M2.5 L3 OD3.5 inserts, 1 mm outer shoulders",
        "hotend_retention": "Original four vertical M2.5x8 heatsink screws retained in reference; no shelf joint",
        "fan_to_hotend_gap_mm": envelope.distance(red),
        "fan_to_references_mm": {n: envelope.distance(s) for n, s in dict(Core=core, **refs).items()},
        "body_valid": body.isValid(), "body_solids": len(body.Solids()),
        "failures": [], "heatset_checks": [], "access_checks": [],
    }
    targets = dict(Core=core, Hotend=red, **refs)
    for name, shape in dict(Body=body, Fan=envelope, Screws=screws, Inserts=inserts).items():
        hits = overlaps(shape, targets)
        report.setdefault("static_intersections_mm3", {})[name] = hits
        if hits:
            report["failures"].append(f"{name} interference: {hits}")
    for name, a, b in (("fan_body", envelope, body), ("screws_body", screws, body),
                       ("screws_fan", screws, fan)):
        v = volume(a.intersect(b))
        report.setdefault("internal_intersections_mm3", {})[name] = v
        if v > 0.001:
            report["failures"].append(f"{name}: {v}")
    for z in (-25.3, -45.3):
        shoulder = cylinder_x(35.5, z, 9.8, 10.8, 2.5).cut(cylinder_x(35.5, z, 9.8, 10.8, 1.4))
        surround = cylinder_x(35.5, z, 6.8, 9.8, 2.5).cut(cylinder_x(35.5, z, 6.8, 9.8, 1.75))
        check = {"z_mm": z, "missing_shoulder_mm3": volume(shoulder.cut(body)),
                 "missing_surround_mm3": volume(surround.cut(body))}
        report["heatset_checks"].append(check)
        if max(check["missing_shoulder_mm3"], check["missing_surround_mm3"]) > 0.001:
            report["failures"].append(f"Incomplete heatset seat: {check}")
        for name, corridor, targets in (
            ("heatset before hotend", cylinder_x(35.5, z, -16, 6.8, 2.2), dict(Body=body)),
            ("screwdriver", cylinder_x(35.5, z, 21.6, 41.6, 1.5), dict(Body=body, Hotend=red, Fan=envelope))):
            hits = overlaps(corridor, targets)
            report["access_checks"].append({"z_mm": z, "operation": name, "hits": hits})
            if hits:
                report["failures"].append(f"Blocked {name}: {hits}")
    gantry_meta = json.loads((primitives.WORK / "gantry_meta.json").read_text())
    gantry = {m["name"]: cq.Shape.cast(s) for m, (s, _) in zip(
        gantry_meta, primitives.load_brep_list(primitives.WORK / "gantry_cache.brep"))}
    beacon = [cq.Shape.cast(s).translate((0, 3.2, -75)) for s in
              primitives.load_step(primitives.SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")]
    top_ko = beacon[1].intersect(box(-20, 20, -20, 20, -76.61, -56.61))
    report["new_cooling_beacon_metal_keepout_mm3"] = overlaps(
        top_ko, dict(Fan=envelope, Screws=screws, Inserts=inserts))
    report["red_lizard_beacon_metal_keepout_mm3"] = overlaps(top_ko, dict(Hotend=red))
    full_tool = compound([body, red, envelope, screws, inserts, refs["P18_Tool_docking_backplate_3010"]])
    external = dict(Core=core, **gantry, Beacon=compound(beacon[2:5]), Beacon_Bottom_Keepout=beacon[0],
                    **{n: s for n, s in refs.items() if n not in
                       ("P18_Tool_docking_backplate_3010", "P25_SparkShift_3010_Dock")})
    report["forward_withdrawal_intersections"] = []
    for dy in range(36):
        hits = overlaps(full_tool.translate((0, dy, 0)), external, tolerance=0.01)
        if hits:
            report["forward_withdrawal_intersections"].append({"forward_mm": dy, "hits": hits})
    if report["forward_withdrawal_intersections"]:
        report["failures"].append("Sampled forward withdrawal interference")
    if report["new_cooling_beacon_metal_keepout_mm3"] or report["red_lizard_beacon_metal_keepout_mm3"]:
        report["failures"].append("Beacon metal keepout interference")
    extent = bounds(compound([full_tool, *refs.values()]))
    report["assembly_width_excluding_core_mm"] = extent[1] - extent[0]
    if extent[0] < -22.50001 or extent[1] > 22.50001:
        report["failures"].append("45 mm envelope exceeded")
    report["adjacent_45mm_pitch_new_cooling_mm3"] = {
        str(dx): volume(compound([envelope, screws, inserts]).intersect(
            compound([full_tool, refs["P25_SparkShift_3010_Dock"]]).translate((dx, 0, 0))))
        for dx in (-45, 45)}
    if max(report["adjacent_45mm_pitch_new_cooling_mm3"].values()) > 0.001:
        report["failures"].append("Adjacent-tool cooling interference")
    if not body.isValid() or len(body.Solids()) != 1:
        report["failures"].append("Invalid/disconnected one-piece body")
    output = STEP / "19_One_Piece_Red_Lizard_Side2510_REVIEW.step"
    assembly = cq.Assembly(name="19 One piece Red Lizard side 2510")
    for name, s, color in (
        ("One_Piece_Red_Lizard_Toolhead", body, cq.Color(0.85, 0.3, 0.12)),
        ("Red_Lizard_Reference_With_Four_Mount_Screws", red, cq.Color(0.65, 0.65, 0.65)),
        ("Side_2510_Reference", fan, cq.Color(0.16, 0.16, 0.18)),
        ("Two_Fan_Screws", screws, cq.Color(0.4, 0.4, 0.4)),
        ("Two_Inner_Heatsets", inserts, cq.Color(0.75, 0.52, 0.16)),
    ):
        assembly.add(s, name=name, color=color)
    assembly.add(core, name="Unchanged_Core", color=cq.Color(0.5, 0.52, 0.55))
    for n, s in refs.items():
        assembly.add(s, name=n, color=cq.Color(0.22, 0.4, 0.32))
    cq.exporters.export(body, str(STEP / "RedLizard_One_Piece_Side2510_REVIEW.step"))
    mesh_path = STL / "RedLizard_One_Piece_Side2510_REVIEW.stl"
    cq.exporters.export(body, str(mesh_path), tolerance=0.03, angularTolerance=0.1)
    mesh = trimesh.load_mesh(mesh_path)
    report["mesh"] = {"watertight": bool(mesh.is_watertight),
                      "components": len(mesh.split(only_watertight=False))}
    if not mesh.is_watertight or report["mesh"]["components"] != 1:
        report["failures"].append("Invalid mesh")
    report["limitations"] = [
        "0.45 mm nominal fan/heatsink gap needs actual fan, heatsink and thermal tolerance confirmation.",
        "Geometric fin coverage is not airflow/heat-creep qualification; cylinder fins do not prove equivalent Bambu cooling.",
        "Front-edge upper/lower retention differs from the user's earlier upper-only preference to avoid fin interference.",
        "No exact connector/wire-bend, stress, insert torque, full rack pitch or continuous dock/cam validation.",
        "Dock unchanged; inherited P18/dock overlap still unresolved. No thermal or physical approval.",
    ]
    report["passed"] = not report["failures"]
    if report["passed"]:
        assembly.export(str(output))
        imported = cq.importers.importStep(str(output)).val()
        expected = sum(len(s.Solids()) for s in (body, red, fan, screws, inserts, core, *refs.values()))
        if not imported.isValid() or len(imported.Solids()) != expected:
            raise ValueError("Invalid assembly STEP reimport")
        report["export_solids"] = expected
        report["assembly_sha256"] = hashlib.sha256(output.read_bytes()).hexdigest()
    (ROOT / "verification_red_lizard_side2510.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    if report["failures"]:
        raise ValueError("Red Lizard side fan audit failed")


if __name__ == "__main__":
    build()
