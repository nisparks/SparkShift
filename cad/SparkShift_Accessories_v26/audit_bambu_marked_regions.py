"""Inspect marked fan/junction regions without inferring screenshot identities."""

import hashlib
import json

import cadquery as cq
import trimesh

from audit_tool_owned_2510 import bounds
from build_modular_toolhead import ROOT, STEP, load


def main():
    names = (
        "Bambu_One_Piece_Docking_Audited_REVIEW",
        "Core_With_Restrained_AHG_Lead_References_REVIEW",
        "P18_Tool_docking_backplate_3010", "P20_CPAP_Hose_Inlet",
        "P21_CPAP_Gantry_Bridge", "P22_CPAP_Lower_Plenum",
        "P23_Beacon_Cartographer_Mount", "P24_EBB42_Controller_Mount",
    )
    parts = {n: load(n) for n in names}
    body = parts[names[0]]
    corridor = cq.Solid.makeCylinder(
        11, 51.45, cq.Vector(-40, 25.5, -35.3), cq.Vector(1, 0, 0)).cut(
            cq.Solid.makeCylinder(
                4, 51.45, cq.Vector(-40, 25.5, -35.3), cq.Vector(1, 0, 0)))
    checks = []
    for name, part in parts.items():
        common = part.intersect(corridor)
        checks.append({
            "part": name, "projected_corridor_intersection_mm3": common.Volume(),
            "intersection_bounds_mm": bounds(common) if common.Solids() else None,
        })
    # A small material witness through the central spine, not a load-bearing rating.
    witness = cq.Solid.makeCylinder(
        0.3, 8, cq.Vector(0, 20, -23), cq.Vector(0, 0, 1))
    missing = witness.cut(body)
    vertices, triangles = body.tessellate(0.03, 0.1)
    mesh = trimesh.Trimesh(
        vertices=[v.toTuple() for v in vertices], faces=triangles, process=True)
    components = len(mesh.split(only_watertight=False))
    if not body.isValid() or len(body.Solids()) != 1 or not mesh.is_watertight or components != 1:
        raise ValueError("Upper body continuity evidence failed")
    if abs(missing.Volume()) > 0.001:
        raise ValueError("Central-spine material witness is not continuous")
    sections = []
    for z in (-22, -21, -20, -19.3, -19, -18, -17.4, -17.2, -17, -16.8, -16, -15):
        wires = cq.Workplane("XY").add(body).section(z).wires().vals()
        sections.append({
            "z_mm": z,
            "closed_loop_areas_mm2": [cq.Face.makeFromWires(w).Area() for w in wires],
            "qualification": "Individual enclosed loop areas include hole loops; do not sum as net load-bearing area.",
        })
    driver_checks = []
    for y in (15.5, 35.5):
        gauge = cq.Solid.makeCylinder(
            2.25, 4, cq.Vector(22.25, y, -25.3), cq.Vector(1, 0, 0))
        hits = {}
        for name, part in parts.items():
            common = gauge.intersect(part)
            if common.Solids() and common.Volume() > 0.001:
                hits[name] = common.Volume()
        driver_checks.append({
            "axis_yz_mm": [y, -25.3], "radius_mm": 2.25,
            "x_extent_mm": [22.25, 26.25], "intersections_mm3": hits})
    report = {
        "status": "MARKED_REGION_INVESTIGATION_NOT_A_REPAIR_OR_STRENGTH_APPROVAL",
        "source_sha256": {
            n: hashlib.sha256((STEP / f"{n}.step").read_bytes()).hexdigest() for n in names},
        "fan_corridor": {
            "axis": "+X/-X", "x_extent_mm": [-40, 11.45],
            "center_yz_mm": [25.5, -35.3], "outer_inner_radius_mm": [11, 4],
            "checks": checks,
            "qualification": "Parallel projection through the generic annular aperture, not a view-ray match, airflow simulation or finite fan suction envelope.",
        },
        "body_continuity": {
            "valid": True, "solid_count": 1, "mesh_watertight": True,
            "mesh_components": components,
            "central_material_witness": {
                "axis_xy_mm": [0, 20], "radius_mm": 0.3,
                "z_extent_mm": [-23, -15], "missing_volume_mm3": missing.Volume()},
            "qualification": "Confirms a material path through the central spine; does not certify the marked outer junction, wall thickness, print orientation or loaded strength.",
        },
        "upper_junction_sections": sections,
        "fan_screw_outer_access": {
            "checks": driver_checks,
            "qualification": "Only the first 4 mm outside each nominal upper fan screw head is screened against the listed parts. Not a full screwdriver, docked-neighbor, insertion-path or wrench-access qualification.",
        },
        "findings": [
            "No screened gray core/accessory solid occupies the straight-through annular corridor. The gray screenshot patch is not positively identified.",
            "The current yellow printed body is one valid, connected, watertight solid with continuous central-spine material across the upper shelf transition.",
            "Yellow printed material does occupy part of the projected corridor; its spatial position must be distinguished from the working fin passages before changing it.",
            "The visible upper-right step may be a relief or a local weak section; global connectivity does not settle its local strength or assembly clearance.",
        ],
        "decision": "Do not merge, cut or bridge the marked regions based solely on this perspective screenshot. Preserve geometry pending positive identification of the exact faces and intended correction.",
        "unchanged": "Fan coordinates, printed body, core, accessories, docks and mounting hardware.",
    }
    path = ROOT / "verification_bambu_marked_regions.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
