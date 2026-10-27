"""Revision 35: a probe-cable entry slot in P24 for the Beacon/Cartographer cable.

The sensor cable (3.0 mm) runs from the Beacon's rear dome up the back of the carriage in P21's
raceway (Y-34.9), turns forward under P20's cable-channel roof at Z-15.8 and passes under the EBB42
into the wiring bay between the board and the extruder motor. Since revision 21 its last 2.4 mm ran
through P24's bottom crossbar and P21 bridge plate (15.5 mm3), and raising it hits P20 instead.

Revision 35 cuts one straight slot through P24's bottom at X0 along the cable, 0.4 mm clear of it on
each side and open to the bay above, and extends the modeled cable through the slot, around an R5
bend and up the middle of the bay. Nothing else in P24 changes; P20, P21 and the core are untouched.
"""

import json
import math
import time

import cadquery as cq
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeEdge, BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakeWire
from OCP.BRepOffsetAPI import BRepOffsetAPI_MakePipe
from OCP.GC import GC_MakeArcOfCircle, GC_MakeSegment
from OCP.gp import gp_Ax2, gp_Circ, gp_Dir, gp_Pnt

import build_and_verify_accessories_v26 as acc
import fast_geometry as fg
from audit_tool_owned_2510 import bounds, compound
from build_bambu_clean_r29 import sha, single
from build_carriage_lowered_mounts_r31 import NAMES as R31, confined
from build_fan_mounts_r33 import export_assembly, export_print
from build_modular_toolhead import ROOT, STEP, box, load, volume

NAMES = {"p24": "P24_EBB42_Controller_Mount_Cable_Entry_R35_REVIEW", "cable": "Probe_Cable_Route_R35_REVIEW",
         "assembly": "35_Carriage_Probe_Cable_Entry_REVIEW"}
REPORT = "verification_p24_cable_entry_r35.json"
CABLE_R, CLEAR = 1.5, 0.4
Y_BACK, Z_RUN = -34.9, -15.8          # revision-21 raceway line and forward run (unchanged)
Y_UP, R_UP, Z_TOP = -26.0, 5.0, 20.0  # new: start of the R5 turn up into the bay, and modeled top
BAY = {"board_standoff_plane_y": -25.4, "motor_rear_y": -16.7}
NEIGHBOURS = ("P20_CPAP_Hose_Inlet", "P21_CPAP_Gantry_Bridge", "P23_Beacon_Cartographer_Mount",
              R31["core"], R31["p22"], R31["hardware"])


def pipe(points):
    """Cable of radius CABLE_R along straight segments and three-point arcs: [p, (mid, p), p, ...]."""
    wire = BRepBuilderAPI_MakeWire()
    prev = gp_Pnt(*points[0])
    for item in points[1:]:
        if isinstance(item[0], tuple):
            mid, end = gp_Pnt(*item[0]), gp_Pnt(*item[1])
            wire.Add(BRepBuilderAPI_MakeEdge(GC_MakeArcOfCircle(prev, mid, end).Value()).Edge())
        else:
            end = gp_Pnt(*item)
            wire.Add(BRepBuilderAPI_MakeEdge(GC_MakeSegment(prev, end).Value()).Edge())
        prev = end
    circle = gp_Circ(gp_Ax2(gp_Pnt(*points[0]), gp_Dir(0, 0, 1)), CABLE_R)
    face = BRepBuilderAPI_MakeFace(BRepBuilderAPI_MakeWire(BRepBuilderAPI_MakeEdge(circle).Edge()).Wire()).Face()
    return cq.Shape.cast(BRepOffsetAPI_MakePipe(wire.Wire(), face).Shape())


def cable_route():
    """The revision-21 route (make_cable_pipe, y_back -34.9) up to its forward run, then the new turn up."""
    r, c = 5.0, 5.0 * math.cos(math.pi / 4)
    y_front, z_under = -12.90, -55.20
    s = math.sin(math.pi / 4)
    return pipe([
        (0, y_front, -66.50), (0, y_front, z_under - r),
        ((0, y_front - r + c, z_under - r + c), (0, y_front - r, z_under)),
        (0, Y_BACK + r, z_under),
        ((0, Y_BACK + r - c, z_under + r - c), (0, Y_BACK, z_under + r)),
        (0, Y_BACK, Z_RUN - r),
        ((0, Y_BACK + r - c, Z_RUN - r + c), (0, Y_BACK + r, Z_RUN)),
        (0, Y_UP, Z_RUN),
        ((0, Y_UP + R_UP * s, Z_RUN + R_UP - R_UP * s), (0, Y_UP + R_UP, Z_RUN + R_UP)),
        (0, Y_UP + R_UP, Z_TOP),
    ])


def slot_box(cable, p24):
    """Straight slot through P24's bottom layer covering the cable wherever it is inside that layer."""
    layer_top = -13.7
    low = cable.intersect(box(-5, 5, -40, 0, -30, layer_top + 0.7))
    b = bounds(low)
    rear = bounds(p24)[2] - 0.2
    return (-CABLE_R - CLEAR, CABLE_R + CLEAR, rear, b[3] + CLEAR, bounds(p24)[4] - 0.2, layer_top + 0.7)


def main():
    started = time.perf_counter()
    old = single(load("P24_EBB42_Controller_Mount"), "released P24")
    cable = cable_route()
    old_cable = cq.Shape.cast(acc.make_cable_pipe(CABLE_R, Z_RUN, y_back=Y_BACK))
    zone = slot_box(cable, old)
    new = single(old.cut(box(*zone)).clean(), "revision-35 P24")
    removed = volume(old) - volume(new)
    report = {
        "status": "PENDING",
        "slot_mm": {"x": zone[:2], "y": zone[2:4], "z": zone[4:]},
        "cable": {"diameter_mm": 2 * CABLE_R, "side_clearance_in_slot_mm": CLEAR,
                  "route": "Revision-21 route to the forward run at Z-15.8, then straight to Y-26.0, an R5 bend "
                           "up and a vertical run at Y-21.0 to Z20 (the umbilical exit above is not modeled).",
                  "bay_mm": BAY,
                  "vertical_run_to_board_standoff_plane_mm": (Y_UP + R_UP - CABLE_R) - BAY["board_standoff_plane_y"],
                  "vertical_run_to_motor_rear_mm": BAY["motor_rear_y"] - (Y_UP + R_UP + CABLE_R)},
        "p24": {"released_volume_mm3": volume(old), "r35_volume_mm3": volume(new), "removed_mm3": removed,
                "solids": len(new.Solids()), "valid": new.isValid(),
                "confinement": confined(new.copy(), old.copy(), [tuple(v + d for v, d in zip(zone, (
                    -0.01, 0.01, -0.01, 0.01, -0.01, 0.01)))])},
    }
    failures = []
    if not report["p24"]["confinement"]["unchanged_outside_zones"]:
        failures.append("P24 changed outside the slot")
    if abs(removed - volume(old.intersect(box(*zone)))) > 1e-3:
        failures.append("Removed volume does not match the slot")
    # The two P24-to-P21 bolts and their counterbores must keep their walls.
    bolts = [(x, -15.80) for x in (-6.0, 6.0)]
    wall = min(math.hypot(max(zone[0] - x, 0, x - zone[1]), max(zone[2] - y, 0, y - zone[3])) - 3.0
               for x, y in bolts)
    report["p24"]["slot_to_counterbore_wall_mm"] = wall
    if wall < 1.5:
        failures.append(f"Slot leaves only {wall:.2f} mm to a P21 bolt counterbore")
    seat_old = old.intersect(box(-30, 30, -40, 0, -18.45, -18.35)).Area()
    seat_new = new.intersect(box(-30, 30, -40, 0, -18.45, -18.35)).Area()
    report["p24"]["seat_band_area_on_p21_mm2"] = {"released": seat_old, "r35": seat_new}
    print("Clearances", flush=True)
    parts = {name: load(name) for name in NEIGHBOURS}
    parts["P24 (revision 35)"] = new
    clear = {}
    for name, part in parts.items():
        hit = fg.min_distance(fg.index_group([("cable", cable)]), fg.index_group([(name, part)]), cutoff=20.0)
        overlap = volume(cable.intersect(part))
        clear[name] = {"min_distance_mm": None if hit is None else hit[0], "overlap_mm3": overlap}
        if overlap > 1e-3:
            failures.append(f"Cable intersects {name}: {overlap:.3f} mm3")
    report["cable_clearances"] = clear
    report["revision_21_cable"] = {
        "overlap_with_released_p24_mm3": volume(old_cable.intersect(old)),
        "overlap_with_r35_p24_mm3": volume(old_cable.intersect(new)),
    }
    if report["revision_21_cable"]["overlap_with_r35_p24_mm3"] > 1e-3:
        failures.append("Revision-21 cable still intersects P24")
    report["static_failures"] = failures
    if failures:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        raise ValueError(f"Revision-35 P24 checks failed: {failures}")
    print("Exports", flush=True)
    files = export_print(NAMES["p24"], new)
    cq.exporters.export(cable, str(STEP / f"{NAMES['cable']}.step"))
    grey, orange, blue = (0.55, 0.57, 0.6), (0.95, 0.55, 0.12), (0.15, 0.35, 0.85)
    assembly = [(new, "R35_P24_Print", orange), (cable, "Probe_Cable_Route_R35", blue)]
    assembly += [(parts[n], n, grey) for n in NEIGHBOURS]
    expected = 2 + sum(len(parts[n].Solids()) for n in NEIGHBOURS)
    files.append(export_assembly(NAMES["assembly"], assembly, expected))
    report["exports"] = {str(p.name): sha(p) for p in files + [STEP / f"{NAMES['cable']}.step"]}
    report["status"] = "LOCAL_CAD_REVIEW_NOT_PRINT_OR_MACHINE_QUALIFICATION"
    report["limitations"] = [
        "The EBB42 board and its connectors are not modeled; the board position comes from P24's standoffs.",
        "The cable is a 3.0 mm rigid tube; its connectors, strain relief and the exit above Z20 are not modeled.",
        "Printed strength of the split bottom crossbar is not qualified; both halves stay bolted to P21.",
    ]
    report["runtime_s"] = time.perf_counter() - started
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k not in ("exports",)}, indent=1, default=str))


if __name__ == "__main__":
    main()
