"""Colour-scheme review: the current build in its print colours (print_colors.py), for Fusion.

The revision-40 carriage with every core part coloured separately (the print set's revision-31 P01 and COTS
P02-P05, the v26 bodies for the rest), withdrawn 60 mm from bay T4 with its tool; the nine other tools
parked in their docks (Bambu in even bays, Red Lizard in odd); the docks, crossbar, P29/P30 rack and the
Monolith X gantry. Tools and docks are located instances of one set of shapes per variant, so only the
rainbow tool bodies and chutes repeat. Writes WORK/print_colour_review.step (not committed).

Run: python build_print_colour_review.py
"""
import json
import os

import build_and_verify_accessories_v26 as acc

os.environ["SPARKSHIFT_SCENE"] = str(acc.WORK / "r40_scene")

import cadquery as cq  # noqa: E402

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import print_colors as C  # noqa: E402
import r37_parts as P37  # noqa: E402
import r40_parts as P  # noqa: E402
from audit_tool_owned_2510 import bounds, compound  # noqa: E402
from build_modular_toolhead import load  # noqa: E402
from build_p24_cable_entry_r35 import NAMES as R35  # noqa: E402
from build_refined_docking_review import DOCK_NAMES  # noqa: E402

OUT = acc.WORK / "print_colour_review.step"
ACTIVE, WITHDRAW = 4, 60.0
CORE_PRINTS = {
    "PRINT_motor_mount": "P01", "PRINT_REAR_MOTOR_SERVO_SPACER": "P02", "PRINT_000_outer_shell_of_extruder_1": "P03",
    "PRINT_carrier_box_left": "P04R", "PRINT_arm_front_half": "P04F", "PRINT_DIRECT_CAM": "P05",
    "PRINT_compound_left": "P06", "PRINT_compound_right": "P07", "PRINT_feed_left": "P08", "PRINT_feed_right": "P09",
    "PRINT_SINGLE_SPRING_PRESSURE_CUP": "P12", "PRINT_MONOLITH_CARTRIDGE_LINER_left": "P13",
    "PRINT_MONOLITH_CARTRIDGE_LINER_right": "P14", "PRINT_MONOLITH_CARTRIDGE_ARCH_left": "P15",
    "PRINT_MONOLITH_CARTRIDGE_ARCH_right": "P16"}
PRINT_SET = {"P01": "P01_Back_case_COTS_MR74_Lowered_Bosses_R31_REVIEW", "P02": "P02_Motor_servo_plate_12p5mm",
             "P03": "P03_Front_case_COTS", "P04F": "P04F_Swing_arm_front_half_COTS", "P05": "P05_Servo_cam_COTS"}
OLD_TOOL = ("TOOL_", "HF_0", "M2_5x8_HF", "PTFE_4x2", "REFERENCE_loaded", "PRINT_RedLizard", "OCT_TOOL_",
            "CLOSING_SPRING")
LEADS = {"red": (0.8, 0.1, 0.1), "green": (0.1, 0.6, 0.2), "yellow": (0.9, 0.8, 0.1), "blue": (0.1, 0.3, 0.8)}
COLOURS = {}


def colour(rgb):
    key = tuple(round(c, 5) for c in rgb)
    if key not in COLOURS:
        COLOURS[key] = cq.Color(*key)
    return COLOURS[key]


def place(f, center, dy=0.0):
    """r36.world() as a location: 180 degrees about Z, then to the bay."""
    return cq.Location(cq.Vector(center, f["world_y_offset_mm"] + dy, f["world_z_offset_mm"]), cq.Vector(0, 0, 1), 180)


def group(name, items, loc=None):
    a = cq.Assembly(name=name, loc=loc or cq.Location())
    seen = set()
    for n, shape, rgb in items:
        label, k = n, 1
        while label in seen:
            k += 1
            label = f"{n}_{k}"
        seen.add(label)
        a.add(shape, name=label, color=colour(rgb))
    return a


def hardware_colour(name):
    n = name.lower()
    for lead, rgb in LEADS.items():
        if n == f"ahg lead {lead}":
            return rgb
    for key, value in (("heatset", "brass"), ("insert", "brass"), ("magnet", "magnet"), ("belt", "belt"),
                       ("servo", "servo"), ("pinion", "steel"), ("lead exit", "connector"), ("ahg", "anodised"),
                       ("hall", "fan"), ("ptfe", "ptfe")):
        if key in n:
            return C.hex_rgb(value)
    return C.hex_rgb("steel")


def core():
    meta = json.loads((acc.WORK / "v26_meta.json").read_text())
    out = []
    for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep")):
        name = m["name"]
        if name.startswith(OLD_TOOL):
            continue
        key = CORE_PRINTS.get(name)
        if key:
            out.append((f"{key}_{PRINT_SET.get(key, name)}", load(PRINT_SET[key]) if key in PRINT_SET else P37.shape(s),
                        C.part(key)))
        else:
            out.append((name, P37.shape(s), hardware_colour(name)))
    if len(out) != 101:
        raise ValueError(f"Core has {len(out)} bodies, expected 101")
    return out


def accessories():
    b = P37.beacon()
    out = [("P20_" + P.NAMES["p20"], P.p20()[0], C.part("P20")), ("P21_" + P.NAMES["p21"], P.p21()[0], C.part("P21")),
           ("P22_" + P37.NAMES["p22"], P37.p22()[0], C.part("P22")), ("P23_" + P37.NAMES["p23"], P37.p23(), C.part("P23")),
           ("P24_" + R35["p24"], load(R35["p24"]), C.part("P24")), ("Probe_cable", P37.cable(), C.hex_rgb("cable")),
           ("Beacon_RevH", compound(b[2:5]), C.hex_rgb("probe")), ("EBB42", P37.ebb42(), C.hex_rgb("pcb"))]
    for n, s in P.other_hardware() + P37.probe_hardware():
        out.append((n, s, C.hex_rgb("brass" if "HEATSET" in n else "steel")))
    return out


def tool_template(parts):
    """(name, shape, colour) with colour None for the body, which takes the tool's colour."""
    out = []
    for n, s in parts:
        if n == "body":
            out.append(("body", s, None))
        elif n == "P18":
            out.append(("P18", s, C.part("P18")))
        elif n == "fan":
            out.append(("fan", s, C.hex_rgb("fan")))
        elif "insert" in n:
            out.append((n, s, C.hex_rgb("brass")))
        elif "bushings" in n:
            for k, x in enumerate(s.Solids()):
                b = bounds(x)
                bushing = max(b[1] - b[0], b[3] - b[2], b[5] - b[4]) > 6.5
                out.append((f"{'bushing' if bushing else 'magnet'}_{k}", x, C.hex_rgb("bronze" if bushing else "magnet")))
        elif "hotend" in n:
            out.append((n, s, C.hex_rgb("aluminium")))
        else:
            out.append((n, s, C.hex_rgb("steel")))
    return [(n.replace(" ", "_"), s, c) for n, s, c in out]


def dock_template(solids):
    """(name, shape, colour) with colour None for the P26 chute, which takes the tool's colour."""
    out = []
    for n, s in zip(DOCK_NAMES, solids):
        if n.startswith("P25"):
            c = C.part("P25")
        elif "Jaw" in n:
            c = C.part("Jaws")
        elif n.startswith("P26"):
            c = None
        elif "Silicone" in n:
            c = C.hex_rgb("silicone")
        elif "Magnet" in n:
            c = C.hex_rgb("magnet")
        else:
            c = C.hex_rgb("steel")
        out.append((n, s, c))
    return out


def gantry_colour(name):
    n = name.lower()
    if n.startswith("printed"):
        return C.part("P01")
    if "2020" in n:
        return C.hex_rgb("anodised")
    if "pulley" in n:
        return C.hex_rgb("aluminium")
    return C.hex_rgb("steel")


def solids(items):
    return sum(len(s.Solids()) for _, s, _ in items)


def main():
    s = r36.scene()
    f = s["frames"]
    top = cq.Assembly(name="SparkShift_print_colours")
    report = {"step": str(OUT), "groups": {}}

    def add(name, items, loc=None):
        top.add(group(name, items, loc))
        report["groups"][name] = solids(items)

    add(f"Carriage_T{ACTIVE}_withdrawn_{WITHDRAW:.0f}mm", core() + accessories(), place(f, r36.CENTERS[ACTIVE], WITHDRAW))
    templates = {label: (tool_template(v["parts"]), dock_template(v["dock_solids"]))
                 for label, v in s["variants"].items()}
    for i, center in enumerate(r36.CENTERS):
        label = "Bambu" if i % 2 == 0 else "RedLizard"
        tool, dock = templates[label]
        body = C.tool(i)
        add(f"T{i}_{label}_{C.TOOLS[i]}", [(n, x, body if c is None else c) for n, x, c in tool],
            place(f, center, WITHDRAW if i == ACTIVE else 0.0))
        add(f"Dock_{i}", [(n, x, body if c is None else c) for n, x, c in dock], place(f, center))
    rack = s["fixed"]["P29_P30_Hardware"].Solids()
    items = []
    for k, x in enumerate(rack):
        key = "P29" if k < 2 else "P30" if k < 4 else None
        items.append((f"{key}_{'LR'[k % 2]}" if key else f"M5_hardware_{k}", x, C.part(key) if key else C.hex_rgb("steel")))
    add("Rack", items + [("Crossbar_2020", s["fixed"]["Crossbar"], C.hex_rgb("anodised"))])
    meta = json.loads((acc.WORK / "rack_audit_X_Gantry_world.json").read_text())
    gantry = [(m["name"], x, gantry_colour(m["name"])) for m, x in zip(meta, s["xgantry"].Solids())]
    add(f"X_gantry_withdrawn_{WITHDRAW:.0f}mm", gantry, cq.Location(cq.Vector(0, WITHDRAW, 0)))
    top.export(str(OUT))
    report["bodies"] = sum(report["groups"].values())
    report["size_mb"] = round(OUT.stat().st_size / 1e6, 1)
    report["tool_split"] = {label: [(n, [round(v, 1) for v in bounds(x)]) for n, x, _ in t if n.startswith(("bushing", "magnet"))]
                            for label, (t, _) in templates.items()}
    (acc.WORK / "print_colour_review.json").write_text(json.dumps(report, indent=1))
    print(OUT, report["bodies"], "bodies", report["size_mb"], "MB")


if __name__ == "__main__":
    main()
