"""Revision 42: a P23 for the Cartographer V3, and the Cartographer's own keepout.

Revision 37's P23 puts the Beacon RevH's coil 2.60 mm above the nozzle tip, Beacon's nominal 2.6 mm. The
Cartographer V3 on the same P23 sits at 2.61 mm, on the bottom edge of the 2.6-3.0 mm range Cartographer asks for.
This P23 is 0.2 mm thinner, so the Cartographer's board sits 0.2 mm higher, at 2.81 mm. Nothing else moves: P22,
its inserts and the rear-ear screws stay. The probe's own screws become M3x5, because an M3x6 would end 0.07 mm
short of the end of P22's insert hole.

The Cartographer's model carries its keepout zones as its last two solids. Revision 37 loaded only the first 100
(the probe itself), so they were never checked: a 22.5 x 22.5 mm column 20 mm tall standing on the board over the
coil, where Cartographer allows no metal, and a 15 x 15 x 3 mm zone under the coil.
"""
import r37_parts as P37
from audit_tool_owned_2510 import compound
from build_bambu_clean_r29 import single
from build_modular_toolhead import box, primitives

RAISE = 0.2
DZ = P37.DZ + RAISE                          # the Cartographer's placement (revision 37: P37.DZ)
SEAT = P37.Z_SEAT + RAISE                    # this P23's bottom face = the Cartographer board's top
COIL_FACE = -76.600 + DZ                     # the Cartographer board's bottom, its coil face
PROBE_SCREW_L = 5.0                          # M3x5 low-profile socket head (head 5.5 x 1.5)
FEELER = 2.81                                # P28's probe feeler: the coil face above the tip datum
MODEL = "Cartographer_V3_RightAngle.step"
NAMES = {
    "p23": "P23_Probe_Mount_Cartographer_R42_REVIEW",
    "p28": "P28_Dock_and_Probe_Calibration_Jig_Cartographer_R42_REVIEW",
    "hardware": "P23_P22_Cartographer_Hardware_R42_REVIEW",
    "keepouts": "Cartographer_V3_Keepouts_R42_REVIEW",
    "review": "42_Cartographer_Mount_REVIEW",
}

_MODEL = []


def model():
    """All 102 solids of the Cartographer model, cached: 0-99 the probe, 100 and 101 its keepout zones."""
    if not _MODEL:
        _MODEL.extend(P37.shape(s) for s in primitives.load_step(primitives.SENSOR_DIR / MODEL))
        if len(_MODEL) != 102:
            raise ValueError(f"{MODEL}: {len(_MODEL)} solids, expected 102")
    return _MODEL


def placed(s, dz=DZ):
    """Revision 37's placement: turned 180 degrees about Z (coil forward), board top on P23's seat."""
    return s.rotate((0, 0, 0), (0, 0, 1), 180).translate((0, -13.00701, -75 + dz))


def cartographer(dz=DZ):
    """The probe itself, the model's first 100 solids, as revision 37 placed it but 0.2 mm higher."""
    return compound(placed(s, dz) for s in model()[:100])


def keepouts(dz=DZ):
    """Cartographer's keepout zones: "top", the column over the coil where no metal may be (20 mm tall, standing
    on the board), and "bottom", the zone under the coil (3 mm deep)."""
    return {"top": placed(model()[101], dz), "bottom": placed(model()[100], dz)}


def p23():
    """Revision 37's P23 less its bottom 0.2 mm."""
    cut = box(-25.0, 25.0, -30.0, 15.0, P37.Z_SEAT - 1.0, SEAT)
    return single(P37.p23().cut(cut).clean(), "revision-42 P23")


def hardware():
    """The Cartographer's own screws, M3x5, through its board and P23 into P22's inserts (unchanged); the rear
    ears keep their M3x4 button heads, on a face 0.2 mm higher."""
    hw = []
    for i, (x, y) in enumerate(P37.PROBE_XY):
        hw.append((f"R42_CARTO_M3x5_LOW_HEAD_{i}", P37.screw(x, y, COIL_FACE - 1.5, 2.75, 1.5, PROBE_SCREW_L)))
        hw.append((f"R42_CARTO_M3x3_HEATSET_{i}", P37.insert(x, y)))
    for i, (x, y) in enumerate(P37.REAR_XY):
        hw.append((f"R42_REAR_M3x4_BUTTON_{i}", P37.screw(x, y, SEAT - 1.65, 2.85, 1.65, 4.0)))
        hw.append((f"R42_REAR_M3x3_HEATSET_{i}", P37.insert(x, y)))
    return hw


def p28():
    """The calibration jig with its probe feeler at the Cartographer's new height."""
    return P37.p28(FEELER)
