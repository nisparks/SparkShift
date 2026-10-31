"""Before/after section gallery of the revision-41 changes, for Fusion (session helper)."""
import json
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402

import build_and_verify_accessories_v26 as acc  # noqa: E402
import r37_parts as P37  # noqa: E402
import r41_parts as R  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31  # noqa: E402
from build_modular_toolhead import box, load  # noqa: E402

FILES = Path(__file__).resolve().parent
OUT = FILES / "r41_changes_gallery.step"
BEFORE, AFTER = (0.55, 0.62, 0.72), (0.95, 0.55, 0.12)
TAN, NAVY, STEEL = (0.8, 0.72, 0.55), (0.12, 0.23, 0.54), (0.35, 0.35, 0.38)
GAP = {"A": 24.0, "B": 25.0, "C": 12.0, "D": 10.0}     # half the spacing of each before/after pair
ROW_Y = {"A": 0.0, "B": 120.0, "C": 240.0, "D": 360.0}
ROW_X = {"A": 0.0, "B": 0.0, "C": 17.0, "D": 18.0}       # centre of each row's region, moved to X0
BEFORE_SIDE = {"A": 1, "B": -1, "C": 1, "D": -1}         # seen from the front +X is on the left; from above, on the right


def v26():
    meta = json.loads((acc.WORK / "v26_meta.json").read_text())
    return {m["name"]: P37.shape(s) for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))}


def clip(s, b):
    return s.intersect(box(*b))


def main():
    parts = v26()
    first_p24 = cq.importers.importStep(str(FILES / "p24_first_r41.step")).val()
    items = []

    def add(name, shape, colour, row, side):
        """side -1 = before, +1 = after; placed so 'before' is on the left of the row's view."""
        x = BEFORE_SIDE[row] * (-side) * GAP[row] - ROW_X[row]
        moved = shape.translate(cq.Vector(x, ROW_Y[row], 0.0))
        if moved.Volume() < 1e-3:
            raise ValueError(f"{name}: empty")
        items.append((name, moved, colour))

    # A: P22 cut across the nozzle at Y22.2 (keep the back half), seen from the front
    a_box = (-40, 40, -60, 22.2, -90, -40)
    add("A1 P22 square-edged jets (before), cut at Y22.2", clip(R.p22(bell_mouth=False), a_box), BEFORE, "A", -1)
    add("A2 P22 bell-mouth jets (R41), cut at Y22.2", clip(load(R.NAMES["p22"]), a_box), AFTER, "A", 1)

    # B: the hall path cut at Z-15 (keep below), seen from above: the groove under the motor
    b_box = (-24, 24, -27, 19, -19, -15.0)
    sensor = parts["STOCK_059_A1104_hall_effect_sensor_1"]
    p21 = load(R.NAMES["p21"])
    for side, tag, p02, p24, colour in ((-1, "B1", load("P02_Motor_servo_plate_12p5mm"), first_p24, BEFORE),
                                        (1, "B2", load(R.NAMES["p02"]), load(R.NAMES["p24"]), AFTER)):
        label = "before" if side < 0 else "R41"
        add(f"{tag} P02 ({label}), cut at Z-15", clip(p02, b_box), colour, "B", side)
        add(f"{tag} P24 ({label}), cut at Z-15", clip(p24, b_box), colour, "B", side)
        add(f"{tag} P21, cut at Z-15", clip(p21, b_box), TAN, "B", side)
        add(f"{tag} hall sensor A1104", clip(sensor, b_box), NAVY, "B", side)

    # C: P01 round the +X front frame screw, P03 left out
    c_box = (8, 26, 18, 31, -23, -8)
    screw = parts["CLAM_M3x25_FRAME_2"]
    add("C1 P01 released, with the tab", clip(load(R31["p01"]), c_box), BEFORE, "C", -1)
    add("C1 frame screw", clip(screw, c_box), STEEL, "C", -1)
    add("C2 P01 R41, tab cut off", clip(load(R.NAMES["p01"]), c_box), AFTER, "C", 1)
    add("C2 frame screw", clip(screw, c_box), STEEL, "C", 1)

    # D: P22's roof behind the +X cheek, seen from above: the pit left by the released wrap pocket, then filled
    d_box = (12.0, 24.0, 5.0, 17.0, -64.0, -52.0)
    pitted = cq.importers.importStep(str(FILES / "p22_r41_with_pits.step")).val()
    add("D1 P22 with the pit behind the cheek (before)", clip(pitted, d_box), BEFORE, "D", -1)
    add("D2 P22 pit filled (R41)", clip(load(R.NAMES["p22"]), d_box), AFTER, "D", 1)

    assy = cq.Assembly(name="R41_changes_before_after")
    for name, s, colour in items:
        assy.add(s, name=name.replace(" ", "_").replace(",", "").replace("(", "").replace(")", ""),
                 color=cq.Color(*colour, 1.0))
    assy.save(str(OUT), "STEP")
    print(json.dumps({"file": str(OUT), "items": [(n, round(s.Volume(), 1)) for n, s, _ in items]}, indent=1))


if __name__ == "__main__":
    main()
