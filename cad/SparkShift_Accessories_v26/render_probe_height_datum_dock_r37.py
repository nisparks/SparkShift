"""Revision 37 review images: 68 probe height and the P23/P22 joint, 69 the Bambu tip and the shared dock."""

import cadquery as cq
from PIL import Image, ImageDraw, ImageFont

import r37_parts as P
from audit_tool_owned_2510 import compound
from build_carriage_lowered_mounts_r31 import NAMES as R31
from build_modular_toolhead import ROOT, box, load, primitives
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP, sheet

ORANGE, BLUE, DARK, BLOCK, STEEL, BRASS, RED, GREY, GREEN, TAN, PAD = (
    (0.95, 0.55, 0.12), (0.35, 0.5, 0.78), (0.12, 0.12, 0.14), (0.42, 0.42, 0.5), (0.55, 0.56, 0.6),
    (0.8, 0.58, 0.2), (0.9, 0.05, 0.05), (0.66, 0.67, 0.7), (0.22, 0.4, 0.32), (0.8, 0.7, 0.45), (0.95, 0.4, 0.1))
SIZE = (900, 760)


def clipped(shape, clip):
    # Clip solid by solid: reference compounds with touching or nested solids can defeat one Boolean.
    pieces = [s.intersect(clip) for s in shape.Solids()]
    pieces = [p for p in pieces if not p.isNull() and p.Solids()]
    return compound(pieces) if pieces else None


def view(items, clip, eye, target, title, zoom=1.0):
    actors = []
    for shape, color in items:
        part = shape if clip is None else clipped(shape, clip)
        if part is None or part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), color, 1.0, edge_vis=True))
    path = primitives.WORK / "r37_panel.png"
    render_view(actors, eye, target, (0, 0, 1), path, width=SIZE[0], height=SIZE[1], zoom=zoom)
    image = Image.open(path).convert("RGB")
    draw, font = ImageDraw.Draw(image), ImageFont.truetype("arial.ttf", 17)
    lines, line = [], ""
    for word in title.split():
        if draw.textlength(f"{line} {word}", font=font) > SIZE[0] - 30:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    lines.append(line)
    draw.rectangle((0, 0, SIZE[0], 14 + 22 * len(lines)), fill=(255, 255, 255))
    for i, text in enumerate(lines):
        draw.text((12, 8 + 22 * i), text, fill=(10, 10, 10), font=font)
    path.unlink()
    return image


def bar(x, y, z0, z1, r=0.12):
    return cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0), cq.Vector(0, 0, 1))


def probe_image(tip):
    old_b, new_b = P.beacon(0.0), P.beacon()
    old_hw, new_hw = P.released_probe_hardware(), P.probe_hardware()
    clash = [s.intersect(old_b[2]) for n, s in old_hw if n.startswith("ACC_PROBE_BRIDGE_M3x8")]
    clash = [c for c in clash if c.Volume() > 1e-3]
    core = load(R31["core"])
    old = [(core, GREY), (load(R31["p22"]), ORANGE), (load("P23_Beacon_Cartographer_Mount"), BLUE),
           (old_b[3], DARK), (old_b[2], BLOCK), (old_b[4], DARK)] + [
        (s, BRASS if "HEATSET" in n or "NUT" in n else STEEL) for n, s in old_hw] + [(c, RED) for c in clash]
    p22_new, _ = P.p22()
    new = [(core, GREY), (p22_new, ORANGE), (P.p23(), BLUE), (new_b[3], DARK), (new_b[2], BLOCK), (new_b[4], DARK)] + [
        (s, BRASS if "HEATSET" in n else STEEL) for n, s in new_hw]
    section = box(4, 15.8, -30, 14, -82, -64)
    eye, target = (400, -8, -73), (15.8, -8, -73)
    bambu_hotend, _ = P.bambu_hotend()
    mid = box(-12, 0.0, -30, 30, -82, -60)
    side = (400, 6, -73), (0, 6, -73)
    coil_old, coil_new = -76.611, -76.611 + P.DZ
    panels = [
        view(old, section, eye, target,
             "Before (revision 36), section at X15.8 through the P23 screws, looking from +X: the two rear "
             "P23-to-P22 screw heads sit inside the Beacon's top-side component block (red, 25.5 mm3 each)", zoom=2.3),
        view(new, section, eye, target,
             "Revision 37: probe raised 0.33 mm; the probe's own screw (right) clamps board and P23 into a "
             "P22 insert; the rear screw (left) moves to an ear behind the board. Nothing sits between P23 and the board",
             zoom=2.3),
        view([(P.p23(), BLUE), (new_b[3], DARK), (new_b[2], BLOCK), (new_b[4], DARK)] + [
            (s, BRASS if "HEATSET" in n else STEEL) for n, s in new_hw] + [(p22_new, ORANGE)],
             box(-26, 26, -30, 16, -80, -69.5), (-60, -120, -170), (0, -6, -73),
             "Revision-37 P23 from below with the Beacon fitted: two probe screws, two button-head screws on the "
             "rear ears, both reachable from below", zoom=1.45),
        view([(core, GREY), (p22_new, ORANGE), (P.p23(), BLUE), (new_b[3], DARK), (new_b[2], BLOCK), (new_b[4], DARK),
              (bambu_hotend, TAN), (bar(-0.5, 12.0, tip, coil_new), RED), (bar(-0.5, 10.6, tip, coil_old), GREEN)]
             + [(s, BRASS if "HEATSET" in n else STEEL) for n, s in new_hw], mid, *side,
             f"Section at X0: coil face {coil_new - tip:.2f} mm above the nozzle tip (red bar; green: "
             f"{coil_old - tip:.2f} mm before). Lowest carriage parts: Beacon connector pins 0.91 mm, probe "
             "screw heads 1.10 mm above the tip", zoom=1.9),
    ]
    out = ROOT / "images" / "68_probe_height_p23_joint_r37_before_after.png"
    sheet(panels, 2, SIZE, out)
    return out


def tip_image(tip):
    bambu_old = load("Tool2510_Reversed_Bambu_Reference_REVIEW")
    bambu_new, info = P.bambu_hotend()
    dock_old = load("36_Bambu_Dock_Complete_REVIEW").Solids()
    dock_new = P.dock()
    rl = load("P17M_RedLizard_Hotend_Reference")
    section = box(-6, 0.0, 4, 30, -84, -70)
    eye, target = (400, 18, -78.5), (0, 18, -78.5)

    def dock_items(d):
        return [(d[0], GREEN), (d[6], (0.75, 0.2, 0.2)), (d[3], PAD), (d[7], (0.1, 0.6, 0.7))]

    close = box(-3, 0.0, 19.5, 26.0, -79.3, -76.2)
    ceye, ctarget = (400, 22.7, -77.75), (0, 22.7, -77.75)
    old_nozzle, new_nozzle = bambu_old.Solids()[3], bambu_new.Solids()[3]
    panels = [
        view([(bambu_old, TAN)] + dock_items(dock_old), section, eye, target,
             "Before: section at X0 through a docked Bambu. The reference nozzle's 2 mm bore runs out through "
             "the tip, leaving a knife edge 0.75 mm high, so its pad and wiper were raised to match", zoom=2.6),
        view([(bambu_new, TAN)] + dock_items(dock_new), section, eye, target,
             f"Revision 37: tip restored at the datum Z{tip:.2f}; the Bambu uses the same pad and wiper as the "
             "Red Lizard, so all ten docks are identical", zoom=2.6),
        view([(old_nozzle, TAN), (new_nozzle.cut(old_nozzle), (0.15, 0.35, 0.85))], close, ceye, ctarget,
             f"Tip detail, section at X0: material added to the reference (blue). "
             f"{info['tip_face_diameter_mm']:.2f} mm tip face, 0.4 mm orifice {info['orifice_length_mm']:.1f} mm long, "
             f"118-degree taper up to the 2 mm bore at Z{info['bore_now_ends_z_mm']:.1f}", zoom=2.4),
        view([(rl, TAN)] + dock_items(dock_new), section, eye, target,
             "The Red Lizard on the same revision-37 dock: tip on the same pad height", zoom=2.6),
    ]
    out = ROOT / "images" / "69_bambu_datum_tip_shared_dock_r37.png"
    sheet(panels, 2, SIZE, out)
    return out


def main():
    tip = P.tip_datum()
    print(probe_image(tip))
    print(tip_image(tip))


if __name__ == "__main__":
    main()
