"""Revision 37 geometry: probe raise, P23/P22 joint off the Beacon, Bambu datum tip, one dock.

Imported by build_probe_height_datum_dock_r37.py (checks, requalification, exports) and the render
script, so every consumer uses the same parts.
"""

import math

import cadquery as cq

import build_and_verify_accessories_v26 as acc
from audit_tool_owned_2510 import bounds, compound
from build_bambu_clean_r29 import single
from build_carriage_lowered_mounts_r31 import MOUNT_DZ, NAMES as R31
from build_modular_toolhead import box, load, primitives
from build_p24_cable_entry_r35 import NAMES as R35

DZ = 0.33                                   # probe raise: Beacon coil 2.27 -> 2.60 mm above the tip datum
Z_TOP = -70.8                               # P23 top face = P22 bottom face (unchanged)
Z_SEAT = -75.0 + DZ                         # P23 bottom face = probe board top
PCB_BOTTOM = -76.611 + DZ                   # Beacon board bottom (the Cartographer's is 0.011 mm higher)
PROBE_XY = ((15.8, -0.3), (-15.8, -0.3))    # the probes' own M3 holes (Beacon and Cartographer alike)
REAR_XY = ((15.8, -19.5), (-15.8, -19.5))   # rear P23 screws, behind the probe board (rear edge Y-15.8)
P22_MOUNTS = PROBE_XY + REAR_XY
SPIGOT_Z = (-73.0, -70.0)                   # P22 bosses, 0.4 mm longer than before for a 3 mm insert
INSERT_HOLE_Z = (-73.4, -70.0)              # open-bottom heat-set hole; 1.1 mm floor to the air duct above
SOCKET_BOTTOM = SPIGOT_Z[0] - 0.02
RELIEF_TOP = -73.8 + DZ                     # over the Beacon's 1.1 mm top-side component block
EAR_X = (10.9, 20.4)
EAR_Y_REAR = -24.15
SHANK_R = 1.45                              # M3 thread major diameter about 2.9 mm
NAMES = {
    "p22": "P22_CPAP_Lower_Plenum_Probe_Mounts_R37_REVIEW",
    "p23": "P23_Probe_Mount_Raised_Rear_Ears_R37_REVIEW",
    "hardware": "P23_P22_Probe_Hardware_R37_REVIEW",
    "cable": "Probe_Cable_Route_R37_REVIEW",
    "bambu_hotend": "Tool2510_Reversed_Bambu_Reference_Datum_Tip_R37_REVIEW",
    "dock": "37_Dock_Complete_REVIEW",
    "pad": "Dock_Ooze_Pad_Datum_SILICONE_R37_REVIEW",
    "wiper": "Dock_Wiper_Datum_SILICONE_R37_REVIEW",
    "p28": "P28_Dock_and_Probe_Calibration_Jig_R37_REVIEW",
    "review": "37_Probe_Height_And_Datum_Dock_REVIEW",
}
BAMBU_CONE = {"apex_z": -79.7952, "semi_angle_deg": 31.004, "axis_xy": (0.0, 22.7)}
BORE_PLUG_TOP = -77.30                      # the 2 mm bore now stops here, 1.58 mm above the tip
ORIFICE_R = 0.2


def shape(s):
    return s if isinstance(s, cq.Shape) else cq.Shape.cast(s)


# --------------------------------------------------------------------------------------------
# Probes, cable and hardware
# --------------------------------------------------------------------------------------------

def beacon(dz=DZ):
    """Beacon RevH Normal: 0 bottom keepout, 1 top keepout, 2 top-side component block, 3 board, 4 connector."""
    return [shape(s).translate((0, 3.2, -75 + dz)) for s in
            primitives.load_step(primitives.SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")]


def beacon_top_keepout(b):
    face = bounds(b[0])[5]
    return b[1].intersect(box(-20, 20, -20, 20, face, face + 20.0))


def cartographer(dz=DZ):
    return compound(shape(s).rotate((0, 0, 0), (0, 0, 1), 180).translate((0, -13.00701, -75 + dz))
                    for s in primitives.load_step(primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")[:100])


def ebb42():
    return compound(shape(s).translate((-20, -20, 0)).rotate((0, 0, 0), (0, 1, 0), 180).rotate(
        (0, 0, 0), (1, 0, 0), 90).translate((-1.248, -31.630, 6.5))
        for s, _ in primitives.load_brep_list(primitives.WORK / "ebb42_cache.brep"))


def cable(dz=DZ):
    """Revision-35 route; its first 0.33 mm sat in the Beacon connector, which now rises by that much."""
    old = load(R35["cable"])
    return single(old.intersect(box(-30, 30, -60, 10, -66.5 + dz, 40)).clean(), "revision-37 cable")


def screw(x, y, z_head_bottom, head_r, head_h, length, shank_r=SHANK_R):
    head = cq.Solid.makeCylinder(head_r, head_h, cq.Vector(x, y, z_head_bottom), cq.Vector(0, 0, 1))
    shank = cq.Solid.makeCylinder(shank_r, length, cq.Vector(x, y, z_head_bottom + head_h), cq.Vector(0, 0, 1))
    return head.fuse(shank).clean()


def insert(x, y):
    outer = cq.Solid.makeCylinder(2.25, SPIGOT_Z[1] - SPIGOT_Z[0], cq.Vector(x, y, SPIGOT_Z[0]), cq.Vector(0, 0, 1))
    bore = cq.Solid.makeCylinder(1.5, SPIGOT_Z[1] - SPIGOT_Z[0] + 0.2, cq.Vector(x, y, SPIGOT_Z[0] - 0.1),
                                 cq.Vector(0, 0, 1))
    return outer.cut(bore)


def probe_hardware():
    """Probe screws clamp board + P23 into P22; rear screws hold P23 when the probe is off."""
    hw = []
    for i, (x, y) in enumerate(PROBE_XY):
        # Low-profile M3x6 (head 5.5 x 1.5): through the probe board and P23 into a 3 mm insert in P22.
        hw.append((f"R37_PROBE_M3x6_LOW_HEAD_{i}", screw(x, y, PCB_BOTTOM - 1.5, 2.75, 1.5, 6.0)))
        hw.append((f"R37_PROBE_M3x3_HEATSET_{i}", insert(x, y)))
    for i, (x, y) in enumerate(REAR_XY):
        # ISO 7380 button-head M3x4 (head 5.7 x 1.65) on the ear's bottom face, behind the probe board.
        hw.append((f"R37_REAR_M3x4_BUTTON_{i}", screw(x, y, Z_SEAT - 1.65, 2.85, 1.65, 4.0)))
        hw.append((f"R37_REAR_M3x3_HEATSET_{i}", insert(x, y)))
    return hw


def other_hardware():
    return [(n, shape(s)) for n, s in acc.build_accessory_hardware(MOUNT_DZ)
            if not n.startswith(("ACC_PROBE_BRIDGE", "ACC_SENSOR_PCB"))]


def released_probe_hardware():
    return [(n, shape(s)) for n, s in acc.build_accessory_hardware(MOUNT_DZ)
            if n.startswith(("ACC_PROBE_BRIDGE", "ACC_SENSOR_PCB"))]


# --------------------------------------------------------------------------------------------
# Printed parts
# --------------------------------------------------------------------------------------------

def p22():
    body, air = acc.build_p22_lower_plenum(MOUNT_DZ, P22_MOUNTS, SPIGOT_Z, INSERT_HOLE_Z)
    return single(shape(body), "revision-37 P22"), shape(air)


def p23():
    xi, xo = EAR_X
    outline = [(-19.2, 11.55), (19.2, 11.55), (19.2, 4.6), (xo, 3.4), (xo, EAR_Y_REAR), (xi, EAR_Y_REAR),
               (xi, -14.2), (-xi, -14.2), (-xi, EAR_Y_REAR), (-xo, EAR_Y_REAR), (-xo, 3.4), (-19.2, 4.6)]
    radii = [2.0, 2.0, 0.6, 0.6, 2.0, 2.0, 0.0, 0.0, 2.0, 2.0, 0.6, 0.6]
    body = acc.prism_xy_r(outline, radii, Z_SEAT, Z_TOP)
    cutters = [
        # Unchanged: thermal setback at the front centre and the connector / header opening at the rear centre.
        acc.rounded_box_xy(-11.65, 11.65, 8.30, 20.00, Z_SEAT - 1.0, Z_TOP + 1.0, 4.65),
        acc.box(-11.50, 11.50, -16.00, -5.80, Z_SEAT - 1.0, Z_TOP + 1.0),
        # Relief over the Beacon's top-side component block, raised with the board.
        acc.box(-xo - 0.5, xo + 0.5, -16.00, -7.95, Z_SEAT - 0.5, RELIEF_TOP),
    ]
    for x, y in P22_MOUNTS:
        cutters.append(acc.cyl_z(x, y, Z_SEAT - 1.0, Z_TOP + 1.0, 1.65))
        cutters.append(acc.cyl_z(x, y, SOCKET_BOTTOM, Z_TOP + 0.5, 3.15))
    body = acc.cut_all(body, cutters)
    return single(shape(body).clean(), "revision-37 P23")


def p28(step):
    """P28 jig rebuilt with a given probe feeler height (released: 2.27 mm)."""
    base = acc.rounded_box_xy(-25.00, 25.00, -12.00, 12.00, 0.00, 8.00, 2.5)
    pins = [acc.cyl_z(sx * 18.65, 5.50, 8.00, 14.50, 2.42) for sx in (-1.0, 1.0)]
    pins += [acc.cyl_z(sx * 17.50, -5.50, 8.00, 14.50, 2.42) for sx in (-1.0, 1.0)]
    step_pad = acc.rounded_box_xy(-9.00, 9.00, -12.00, -3.50, 8.00, 8.00 + step, 1.5)
    jig = acc.cut_all(acc.fuse_all([base, step_pad] + pins), [
        acc.box(-12.50, 12.50, -2.05, 2.05, 5.50, 8.50),
        acc.rounded_box_xy(-10.70, 10.70, 2.50, 9.50, 4.50, 8.50, 1.2),
        acc.cyl_z(0.0, -7.50, -1.0, 12.0, 2.60)])
    from OCP.ShapeUpgrade import ShapeUpgrade_UnifySameDomain
    unify = ShapeUpgrade_UnifySameDomain(jig, True, True, True)
    unify.Build()
    return single(shape(unify.Shape()), f"P28 with {step} mm feeler")


# --------------------------------------------------------------------------------------------
# Bambu tip and dock
# --------------------------------------------------------------------------------------------

def tip_datum():
    return bounds(load("P17M_RedLizard_Hotend_Reference"))[4]


def bambu_hotend():
    """The synthetic Bambu reference with its tip restored at the datum.

    Its cone was drawn with r0.55 at the datum (a 1.1 mm tip face), but the 2 mm filament bore was cut
    straight through the tip, leaving a knife edge 0.75 mm higher. Fill the bore below Z-77.30 with the
    same cone, then drill a 118-degree point down to a 0.4 mm orifice. Nothing above Z-77.30 changes.
    """
    tip = tip_datum()
    solids = load("Tool2510_Reversed_Bambu_Reference_REVIEW").Solids()
    nozzle = solids[3]
    if abs(bounds(nozzle)[4] + 78.1312) > 1e-3 or len(solids) != 6:
        raise ValueError("Unexpected Bambu reference: solid 3 should end in the knife edge at Z-78.131")
    x, y = BAMBU_CONE["axis_xy"]
    tan = math.tan(math.radians(BAMBU_CONE["semi_angle_deg"]))
    r_tip = (tip - BAMBU_CONE["apex_z"]) * tan
    r_top = (BORE_PLUG_TOP - BAMBU_CONE["apex_z"]) * tan
    frustum = cq.Solid.makeCone(r_tip, r_top, BORE_PLUG_TOP - tip, cq.Vector(x, y, tip), cq.Vector(0, 0, 1))
    drill_h = (1.0 - ORIFICE_R) / math.tan(math.radians(59.0))
    drill = cq.Solid.makeCone(ORIFICE_R, 1.0, drill_h, cq.Vector(x, y, BORE_PLUG_TOP - drill_h), cq.Vector(0, 0, 1))
    orifice = cq.Solid.makeCylinder(ORIFICE_R, BORE_PLUG_TOP - drill_h - tip + 0.2, cq.Vector(x, y, tip - 0.1),
                                    cq.Vector(0, 0, 1))
    fixed = single(nozzle.fuse(frustum).cut(drill).cut(orifice).clean(), "repaired Bambu nozzle")
    info = {"tip_z_mm": tip, "tip_face_diameter_mm": 2 * r_tip, "orifice_diameter_mm": 2 * ORIFICE_R,
            "orifice_length_mm": BORE_PLUG_TOP - drill_h - tip, "bore_now_ends_z_mm": BORE_PLUG_TOP,
            "knife_edge_z_mm": bounds(nozzle)[4], "added_mm3": fixed.Volume() - nozzle.Volume()}
    return compound([*solids[:3], fixed, *solids[4:]]), info


def dock():
    """One dock for every bay: the revision-36 dock with the datum-height pad and wiper."""
    solids = load("36_RedLizard_Dock_Complete_REVIEW").Solids()
    if len(solids) != 14:
        raise ValueError("Unexpected revision-36 dock")
    return solids
