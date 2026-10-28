"""Revision 41 review images: the build fixes, before and after.

79: P24 released and revision 41; the CPAP joints in section; the outlet in section through the nozzle.
80: P02's servo recess, released and tightened; P22's cheek on P01's boss, wrapped and face-mounted; the four P03
    magnet variants.

Run after build_carriage_fixes_r41.py: python render_carriage_fixes_r41.py
"""
import json

from PIL import Image, ImageDraw

import r37_parts as P37
import r40_parts as P40
import r41_parts as R
from build_carriage_fixes_r41 import REPORT
from build_modular_toolhead import ROOT, box, load, primitives
from build_p24_cable_entry_r35 import NAMES as R35
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet

SIZE = (900, 760)
ORANGE, GREY, BOARD, TAN, CYAN, TEAL = (0.95, 0.55, 0.12), (0.6, 0.62, 0.66), (0.1, 0.45, 0.2), (0.8, 0.72, 0.55), \
    (0.07, 0.72, 0.9), (0.0, 0.64, 0.61)
VIOLET, NAVY, STEEL, BLUE = (0.48, 0.25, 0.89), (0.12, 0.23, 0.54), (0.72, 0.74, 0.78), (0.14, 0.33, 0.85)


def view(items, clip, eye, target, title, zoom=1.0, up=(0, 0, 1)):
    actors = []
    for shape, color, *rest in items:
        part = shape.intersect(clip) if clip is not None else shape
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, rest[0] if rest else 1.0, edge_vis=True))
    path = primitives.WORK / "carriage_fixes_r41_panel.png"
    render_view(actors, eye, target, up, path, width=SIZE[0], height=SIZE[1], zoom=zoom)
    image = Image.open(path).convert("RGB")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(title.split("\n")):
        draw.text((12, 12 + 14 * i), line, fill=(10, 10, 10))
    path.unlink()
    return image


def motor_and_servo():
    meta = json.loads((primitives.WORK / "v26_meta.json").read_text())
    import build_and_verify_accessories_v26 as acc
    v26 = {m["name"]: P37.shape(s) for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))}
    return [v26[n] for n in v26 if n.startswith("AHG laminated") or n.startswith("AHG rear")], v26["HOBBY_SERVO_ENVELOPE"]


def image_79(report):
    old24, new24 = load(R35["p24"]), load(R.NAMES["p24"])
    w_old, w_new = report["p24"]["released_walls"], report["p24"]["walls"]
    rear = ((110, -150, 70), (0, -15, 4))
    j = report["joints"]
    o = report["outlet"]
    motor, _ = motor_and_servo()
    ebb, p02, p21 = P37.ebb42(), load("P02_Motor_servo_plate_12p5mm"), load(R.NAMES["p21"])
    joint = box(-30, 10, -60, 0, -60, -12)
    side = ((300, -35, -35), (0, -35, -35))
    outlet = box(-30, 30, -60, 22.7, -80, -66)
    front = ((0, 300, -73), (0, 22.7, -73))
    bambu = [s for n, s in __import__("build_chute_chamfer_rack_r36").scene()["variants"]["Bambu"]["parts"] if "hotend" in n]
    panels = [
        view([(old24, ORANGE)], None, *rear,
             f"Released P24 from behind: about 20 blocks, a wire comb and box windows; walls down to "
             f"{w_old['min_mm']:.2f} mm\n({w_old['below_1.0_mm2']:.0f} mm2 under 1.0 mm)", zoom=1.55),
        view([(new24, ORANGE), (ebb, BOARD, 0.35), (p02, VIOLET, 0.5), (p21, TAN)] + [(m, GREY) for m in motor], None,
             *rear, f"Revision 41 in place: bottom block on P21, side wall, column, corner blocks and towers, all on "
                    f"P02;\nthinnest wall {w_new['min_mm']:.2f} mm, where the top-left insert channel passes the servo "
                    f"header's plug ({w_new['below_1.0_mm2']:.0f} mm2 under 1.0 mm)", zoom=1.3),
        view([(load(P40.NAMES["p20"]), BLUE), (load(P40.NAMES["p21"]), CYAN), (P37.p22()[0], TEAL)], joint, *side,
             f"Released joints, cut at X10: socket rims {j['walls']['P21_socket_and_sleeve']['released_min_mm']:.2f} mm, "
             f"sleeves about 0.8 mm", zoom=2.3),
        view([(load(R.NAMES["p20"]), BLUE), (load(R.NAMES["p21"]), CYAN), (load(R.NAMES["p22"]), TEAL)], joint, *side,
             f"Revision 41: walls {j['walls']['P21_socket_and_sleeve']['min_mm']:.2f} mm and more, same "
             f"{j['P20_in_P21']['radial_slip_mm']:.2f} mm slip;\nopen area through the sleeves "
             f"{j['P20_in_P21']['open_area_mm2']:.0f} and {j['P21_in_P22']['open_area_mm2']:.0f} mm2 "
             f"(hose bore 211)", zoom=2.3),
        view([(P37.p22()[0], TEAL)] + [(s, GREY) for s in bambu], outlet, *front,
             f"Released outlet, cut through the nozzle: 1.8 mm horizontal jets under knife-edge vanes, "
             f"{o['narrowest_mm2']['released_mm2']:.0f} mm2 in all", zoom=3.0),
        view([(load(R.NAMES["p22"]), TEAL)] + [(s, GREY) for s in bambu], outlet, *front,
             f"Revision 41: still horizontal, {R.ROOF + 76.65:.2f} mm tall under a flat 1.4 mm wall, "
             f"{o['narrowest_mm2']['r41_mm2']:.0f} mm2 in all\n({o['area_ratio']:.1f}x); solid floor below, nothing "
             f"blows down at the bed", zoom=3.0),
    ]
    out = ROOT / "images" / "79_carriage_fixes_r41_p24_joints_outlet.png"
    sheet(panels, 2, SIZE, out)
    return out


def image_80(report):
    from build_carriage_lowered_mounts_r31 import NAMES as R31
    _, servo = motor_and_servo()
    p, m = report["p02"], report["p22_mounts"]
    # P02 cut through the recess (Y-10.5 to -7.0), seen from behind; the cheek cut along the screw's axis, from above
    clip = box(-2, 23, -10.5, -7.0, 28, 63)
    recess = ((10.5, -150, 45.34), (10.5, -8.75, 45.34))
    p01 = load(R31["p01"])
    hw = [s for n, s in R.other_hardware() if n.startswith(("R41_P22_P01", "ACC_CASE_BOSS_HEATSET"))]
    old_hw = [s for n, s in P37.other_hardware() if n.startswith("ACC_CASE_BOSS")]
    zb = R.P01_BOSS_Z
    cheek_clip, cheek_view = box(10.5, 25.5, 6, 24, zb - 6, zb), ((18, 15, 150), (18, 15, zb))
    m_ = m["bosses"]["x+18"]
    panels = [
        view([(load("P02_Motor_servo_plate_12p5mm"), VIOLET), (servo, NAVY)], clip, *recess,
             f"Released P02, cut through the recess, from behind: the MG90D's top 4.5 mm sits in a "
             f"{p['recess_mm']['released'][0]:.2f} x {p['recess_mm']['released'][1]:.2f} mm recess,\n"
             f"{p['play_per_side_mm']['released']['across']:.2f} mm play a side across and "
             f"{p['play_per_side_mm']['released']['along']:.3f} mm along", zoom=1.15),
        view([(load(R.NAMES["p02"]), VIOLET), (servo, NAVY)], clip, *recess,
             f"Revision 41: the same recess, {p['recess_mm']['r41'][0]:.2f} x {p['recess_mm']['r41'][1]:.2f} mm: line "
             f"to line across the 12.2 x 22.8 body,\n{p['play_per_side_mm']['r41']['along']:.2f} mm at each end; "
             f"nothing else on P02 changes", zoom=1.15),
        view([(P37.p22()[0], TEAL), (p01, (0.75, 0.2, 0.55))] + [(s, STEEL) for s in old_hw], cheek_clip,
             *cheek_view, f"Released P22 cheek, cut along the screw, from above (P01 magenta): wrapped round P01's "
             f"boss,\nwalls down to {m['released_walls']['min_mm']:.2f} mm, the boss showing through its top",
             zoom=1.2, up=(0, 1, 0)),
        view([(load(R.NAMES["p22"]), TEAL), (p01, (0.75, 0.2, 0.55))] + [(s, STEEL) for s in hw], cheek_clip,
             *cheek_view, f"Revision 41: the cheek stops at the boss face and the screw locates it; walls "
             f"{m['walls']['min_mm']:.2f} mm and up,\n{m_['bearing_on_boss_mm2']:.0f} mm2 on the boss, an M3x8 button "
             f"head on the front", zoom=1.2, up=(0, 1, 0)),
    ]
    for kind in R.MAGNETS:
        q = report["p03"][kind]
        mags = [(m, STEEL) for m in R.magnet(kind)]
        opens = R.MAGNET_SPECS[kind][1] >= 6.0
        panels.append(view([(load(R.NAMES[f"p03_{kind}"]), (0.9, 0.9, 0.92))] + mags, box(-25, 25, 20, 40, -25, 60),
                           (0, 200, 14), (0, 31.5, 14),
                           f"P03 for {kind} magnets: {q['side_clearance_mm']:.2f} mm a side, faces "
                           f"{q['proud_of_front_face_mm']:.2f} mm proud" +
                           ("\npockets open into the centre slot where the wall would be under 0.6 mm" if opens else
                            "\n0.75 mm wall to the centre slot"), zoom=2.0))
    out = ROOT / "images" / "80_carriage_fixes_r41_servo_mounts_magnets.png"
    sheet(panels, 2, SIZE, out)
    return out


def main():
    report = json.loads((ROOT / REPORT).read_text())
    print(image_79(report))
    print(image_80(report))


if __name__ == "__main__":
    main()
