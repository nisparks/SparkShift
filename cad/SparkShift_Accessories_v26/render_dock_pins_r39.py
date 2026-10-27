"""Revision 39 review image: the dock-coupling dowel pins move from P18 into the dock."""

import json
import os
import re

import build_and_verify_accessories_v26 as acc

os.environ.setdefault("SPARKSHIFT_SCENE", str(acc.WORK / "r39_scene"))

import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from PIL import Image  # noqa: E402

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import r37_parts as P37  # noqa: E402
import r39_parts as P  # noqa: E402
from build_modular_toolhead import ROOT, box, load, primitives  # noqa: E402
from render_bambu_clean_r29 import sheet  # noqa: E402
from render_front_print_limit_r38 import SIZE, panel  # noqa: E402

FRONT_REPORT, FRONT_R38 = "verification_front_print_limit_r39.json", "verification_front_print_limit_r38.json"

TOOL, P18C, STEEL, BRASS, MAG = (0.95, 0.67, 0.1), (0.95, 0.5, 0.1), (0.75, 0.75, 0.8), (0.85, 0.6, 0.15), (0.15, 0.15, 0.17)
P25C, JAW, ACTIVE, RIG, DOCK = (0.3, 0.62, 0.45), (0.55, 0.57, 0.6), (0.2, 0.55, 0.9), (0.55, 0.6, 0.68), (0.75, 0.2, 0.7)


def coupling_sets(s):
    """Released (revision 37) and revision-39 coupling parts, all in the docked tool/dock frame."""
    yf = P.dock_face_y(P37.dock())
    pins37 = [x for x in r36.coupling().Solids() if x.BoundingBox().ymax > 48]
    body = dict(s["variants"]["Bambu"]["parts"])["body"]
    p18 = dict(s["variants"]["Bambu"]["parts"])["P18"]
    before = {"body": body, "p18": load("P18_Tool_docking_backplate_3010"), "tool_hw": pins37, "dock": P37.dock()}
    after = {"body": body, "p18": p18, "tool_hw": P.bushings(), "dock": s["variants"]["Bambu"]["dock_solids"]}
    return before, after, yf


def items(c, dx=0.0, dy=0.0, dock=True, tool=True):
    out = []
    if tool:
        out += [(c["body"].translate((dx, dy, 0)), TOOL, 1.0), (c["p18"].translate((dx, dy, 0)), P18C, 1.0)]
        out += [(h.translate((dx, dy, 0)), STEEL if h.BoundingBox().ymax > 48 else BRASS, 1.0) for h in c["tool_hw"]]
        out += [(m.translate((dx, dy, 0)), MAG, 1.0) for m in P.tool_magnets()]
    if dock:
        d = c["dock"]
        out += [(d[0].translate((dx, 0, 0)), P25C, 1.0), (d[1].translate((dx, 0, 0)), JAW, 1.0),
                (d[2].translate((dx, 0, 0)), JAW, 1.0)]
        out += [(d[i].translate((dx, 0, 0)), STEEL if d[i].BoundingBox().ymin < 45.0 else BRASS, 1.0)
                for i in (P.LEFT, P.RIGHT)]
        out += [(d[i].translate((dx, 0, 0)), MAG, 1.0) for i in (12, 13)]
    return out


def section(c, x, title):
    clip = box(x - 16, x, 33, 58, -12, 34)
    return panel(items(c), clip, (x + 400, 45.5, 11.0), (x, 45.5, 11.0), (0, 0, 1), title, zoom=1.0)


def chart(r38, r39):
    fig, ax = plt.subplots(figsize=(SIZE[0] / 100, SIZE[1] / 100), dpi=100)
    for rep, color, label in ((r38, (0.75, 0.1, 0.1), "Revision 38: pins on P18"),
                              (r39, (0.1, 0.5, 0.2), "Revision 39: pins in the dock")):
        for active, style in (("Bambu", "-"), ("RedLizard", "--")):
            rows = sorted((p["x_mm"], p["y_mm"]) for p in rep["profile"] if p["active"] == active and p["y_mm"])
            ax.plot([a for a, _ in rows], [b for _, b in rows], style, color=color, lw=1.3,
                    label=f"{label}, {active} active")
        lim = rep["front_print_limit_nozzle_y_mm"]
        ax.axhline(lim, color=color, lw=2.2, ls=":", label=f"{label.split(':')[0]} limit Y{lim:.2f}")
    for x in r36.CENTERS:
        ax.axvline(x, color=(0.7, 0.7, 0.7), lw=0.6, zorder=0)
    gain = r38["front_print_limit_nozzle_y_mm"] - r39["front_print_limit_nozzle_y_mm"]
    ax.set_xlim(0, 350)
    ax.set_ylim(44, 56)
    ax.set_xlabel("Nozzle X (mm)")
    ax.set_ylabel("First-contact nozzle Y (mm, world CAD)")
    ax.set_title(f"First contact with the parked rack: the pin peaks are gone, P18's plate binds everywhere\n"
                 f"Front limit Y{r38['front_print_limit_nozzle_y_mm']:.2f} -> Y{r39['front_print_limit_nozzle_y_mm']:.2f}"
                 f" ({gain:.2f} mm more depth)", fontsize=10)
    ax.legend(loc="upper right", fontsize=7, ncol=2)
    fig.tight_layout()
    path = primitives.WORK / "dock_pins_r39_chart.png"
    fig.savefig(path)
    plt.close(fig)
    image = Image.open(path).convert("RGB").resize(SIZE)
    path.unlink()
    return image


def limit_section(s, r39):
    """Side section through the new binding point: P18's plate against the parked tool, 1 mm apart."""
    f = s["frames"]
    worst = r39["by_active_tool"]["Bambu"]["worst"]
    contact = r39["by_active_tool"]["Bambu"]["contact_at_worst"]
    gap = r39["by_active_tool"]["Bambu"]["clearance_at_print_limit"]["mm"]
    pitch = r36.CENTERS[1] - r36.CENTERS[0]
    k = round((175.0 - worst["x_mm"]) / pitch)
    show_x = worst["x_mm"] + k * pitch
    px, py, pz = contact["fixed_point_world_mm"]
    px += k * pitch
    bay = int(re.search(r"T(\d)", contact["fixed"]).group(1)) + k
    v = s["variants"]["RedLizard" if "RedLizard" in contact["fixed"] else "Bambu"]
    new = r39["front_print_limit_nozzle_y_mm"]
    move = (0, new - r39["dock_nozzle_y_mm"], 0)
    bambu = s["variants"]["Bambu"]
    things = [(r36.world(v["dock"], r36.CENTERS[bay], f), DOCK, 1.0), (r36.world(v["tool"], r36.CENTERS[bay], f), TOOL, 1.0),
              (r36.world(bambu["tool"], show_x, f).translate(move), ACTIVE, 1.0),
              (r36.world(s["carriage"], show_x, f).translate(move), RIG, 1.0),
              (box(px - 3, px + 3, py + 0.25, py + 0.75, pz - 3, pz + 3), (0.9, 0.05, 0.05), 1.0)]
    clip = box(px - 3, px + 3, py - 28, py + 28, pz - 24, pz + 24)
    return panel(things, clip, (px + 600, py, pz), (px, py, pz), (0, 0, 1),
                 f"Revision 39 at the new limit Y{new:.2f}, section X{px - 3:.1f}..{px + 3:.1f}: the binding feature "
                 f"is now P18's\nplate (blue) {gap:.2f} mm from the parked T{bay} (yellow, red marker). No pin "
                 f"reaches into the parked tool.", zoom=1.0)


def main():
    s = r36.scene()
    r38 = json.loads((ROOT / FRONT_R38).read_text())
    r39 = json.loads((ROOT / FRONT_REPORT).read_text())
    before, after, yf = coupling_sets(s)
    ax0, ax1 = P.OLD_AXES[0][0], P.AXES[0][0]
    panels = [
        section(before, ax0, f"Revision 37/38 (before), docked, section at X{ax0:g} through a pin: the 5x12 mm dowel "
                             "(steel) sticks 5.5 mm\nout of P18 (orange) into a bushing (brass) in the dock (green). "
                             "Magnets (black) below."),
        section(after, ax1, f"Revision 39 (after), docked, section at X{ax1:g}: the same dowel is pressed into the dock "
                            "and enters a bushing\nflush in P18. Same 4.59 mm insertion, 0.04 mm clearance, magnets "
                            "unchanged."),
        panel(items(before, dx=13.0, dock=False) + items(after, dx=-13.0, dock=False), box(-30, 30, 30, 56, -25, 50),
              (-120, 400, 140), (0, 40, 13), (0, 0, 1),
              "P18 from the dock side. Left: released, two bosses with pins sticking out. Right: revision 39, one "
              "bar\n(X+/-9.8, Z16..26.2) with two 5x7x5.5 bushings flush; axes X+/-4.8, Z21. Magnet bar unchanged.",
              zoom=1.05),
        panel(items(before, dx=-22.0, tool=False) + items(after, dx=22.0, tool=False), box(-41, 41, 40, 62, -16, 38),
              (120, -320, 140), (0, 50, 12), (0, 0, 1),
              "P25 from the tool side (coupling region). Left: released, bushings flush in the dock. Right: revision "
              "39,\nthe released seats filled and two 5x12 mm pins pressed 6.5 mm in, 5.5 mm proud.", zoom=1.05),
        chart(r38, r39),
        limit_section(s, r39),
    ]
    out = ROOT / "images" / "73_dock_pins_r39_before_after.png"
    sheet(panels, 2, SIZE, out)
    print(out)


if __name__ == "__main__":
    main()
