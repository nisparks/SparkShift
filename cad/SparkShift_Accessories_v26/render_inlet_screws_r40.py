"""Revision 40 review image: the P20-to-P21 screws, before and after, and the two recorded notes."""

import json

import cadquery as cq
from PIL import Image, ImageDraw

import build_and_verify_accessories_v26 as acc
import r37_parts as P37
import r40_parts as P
from build_carriage_lowered_mounts_r31 import NAMES as R31
from build_inlet_screws_r40 import REPORT, gantry_groups
from build_modular_toolhead import ROOT, box, load, primitives
from build_p24_cable_entry_r35 import NAMES as R35
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet

SIZE = (900, 760)
GREY, BEAM, ORANGE, TAN, GREEN, PURPLE = (0.62, 0.64, 0.68), (0.8, 0.8, 0.83), (0.95, 0.55, 0.12), (0.8, 0.72, 0.55), \
    (0.35, 0.7, 0.4), (0.6, 0.45, 0.8)
BOARD, BLUE, STEEL, BRASS, RED = (0.1, 0.45, 0.2), (0.15, 0.35, 0.85), (0.3, 0.3, 0.33), (0.85, 0.6, 0.15), (0.9, 0.05, 0.05)


def view(items, clip, eye, target, title, zoom=1.0, up=(0, 0, 1)):
    actors = []
    for shape, color in items:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "inlet_screws_r40_panel.png"
    render_view(actors, eye, target, up, path, width=SIZE[0], height=SIZE[1], zoom=zoom)
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(title.split("\n")):
        draw.text((12, 12 + 14 * i), line, fill=(10, 10, 10))
    path.unlink()
    return image


def colour(name):
    return BRASS if "HEATSET" in name else STEEL


def scenes():
    beam = [s for _, s in gantry_groups(175.0)[0]]
    ebb = P37.ebb42()
    common = [(load(R31["core"]), GREY), (ebb, BOARD), (P37.p22()[0], ORANGE), (load(R35["p24"]), PURPLE),
              (P37.cable(), BLUE)] + [(s, BEAM) for s in beam]
    old_hw, new_hw = P37.other_hardware(), P.other_hardware()
    keep = lambda n: not n.startswith(("ACC_CASE", "ACC_EBB42_M3"))
    clash = [s.intersect(ebb) for n, s in old_hw if n.startswith("ACC_UPPER_INLET_M3x8")]
    before = common + [(load("P20_CPAP_Hose_Inlet"), GREEN), (load("P21_CPAP_Gantry_Bridge"), TAN)]
    before += [(s, colour(n)) for n, s in old_hw if keep(n)] + [(c, RED) for c in clash]
    after = common + [(P.p20()[0], GREEN), (P.p21()[0], TAN)] + [(s, colour(n)) for n, s in new_hw if keep(n)]
    return before, after


def anchor_scene():
    meta = json.loads((primitives.WORK / "v26_meta.json").read_text())
    core = {m["name"]: P37.shape(s) for m, (s, _) in zip(meta, acc.load_brep_list(primitives.WORK / "v26_cache.brep"))}
    picks = {"UPPER_RIGHT_SHARED_M3x35_FRAME": STEEL, "UPPER_RIGHT_REAR_M3_HEATSET_4p6x4": BRASS,
             "PRINT_REAR_MOTOR_SERVO_SPACER": GREY, "PRINT_motor_mount": (0.5, 0.52, 0.56)}
    return [(core[n], c) for n, c in picks.items()] + [(load(R35["p24"]), PURPLE), (P37.ebb42(), BOARD)]


def main():
    r = json.loads((ROOT / REPORT).read_text())
    j = r["inlet_joint"]
    beam = r["note_conduit_on_x_beam"]
    up = r["note_stack_anchor"]["holes"]["upper"]
    before, after = scenes()
    eye = lambda x: ((x + 300, -31, -16), (x, -31, -16))
    plan = box(-25, 25, -60, 0, -32, -19.0)
    top = ((0, -31, 300), (0, -31, -19))
    x0 = box(-30, 0, -60, 5, -62, 0)
    side = ((300, -32, -35), (0, -32, -35))
    ax, az = P.UPPER_CLAMP
    rel_beam = beam["released_to_beam_and_rail_mm"]
    panels = [
        view(before, box(-30, -4.5, -45, -20, -30, 0), *eye(-4.5),
             "Released, section through a P20-to-P21 screw (X-4.5): the M3x8 head sits on the lug top and\n"
             f"reaches into the EBB42's bottom edge and headers ({j['head_to_ebb42_mm']['released_overlap_mm3']:.0f} mm3, red)",
             zoom=3.2),
        view(after, box(-30, -P.LUG_X, -45, -20, -30, 0), *eye(-P.LUG_X),
             f"Revision 40 (X-{P.LUG_X:.1f}): an ISO 7380 button head seated 1.6 mm down in P20's lug,\n"
             f"{j['head_to_ebb42_mm']['r40']:.2f} mm under the board and {j['head_to_probe_cable_mm']['r40']:.2f} mm "
             "from the probe cable", zoom=3.2),
        view(before, plan, *top,
             "Released, plan section at Z-19 through P21's top flange: the insert pockets are "
             f"{j['p21_pocket_to_cable_raceway_mm']['released']:.2f} mm\nfrom the probe-cable raceway and "
             f"{j['p21_pocket_to_p20_sleeve_socket_mm']['released']:.2f} mm from P20's sleeve socket",
             zoom=2.2, up=(0, 1, 0)),
        view(after, plan, *top,
             f"Revision 40: pockets at X+-{P.LUG_X:.1f}, 1 mm forward: "
             f"{j['p21_pocket_to_cable_raceway_mm']['r40']:.2f} mm to the raceway, "
             f"{j['p21_pocket_to_p20_sleeve_socket_mm']['r40']:.2f} mm to the socket", zoom=2.2, up=(0, 1, 0)),
        view(after, x0, *side,
             "Note, no change: at X0, P21's conduit front face lies on the X beam's rear face "
             f"({rel_beam['P21']['mm']:.1f} mm)\nand the probe cable runs {rel_beam['Probe_Cable']['mm']:.1f} mm "
             "from it, over the whole X travel", zoom=1.7),
        view(anchor_scene(), box(-30, ax, -30, 20, az - 9, az + 9), (ax + 300, -9, az), (ax, -9, az),
             f"Note, no change: P24's upper rear hole (X{ax:.1f}) lines up with P02's case-clamp insert, but the core's\n"
             f"own M3x35 case screw fills it ({up['free_thread_behind_core_screw_mm']:.1f} mm of thread left)",
             zoom=3.0),
    ]
    out = ROOT / "images" / "75_p20_p21_screws_r40_before_after.png"
    sheet(panels, 2, SIZE, out)
    print(out)


if __name__ == "__main__":
    main()
