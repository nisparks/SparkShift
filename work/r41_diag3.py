"""R41 rework diagnostics: P22's cheeks around P01's front bosses (session scratch)."""
import sys

sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
from r41_diag import *  # noqa: E402,F403
from r41_diag2 import hotends  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31N  # noqa: E402

if __name__ == "__main__":
    hot = hotends()
    tools = cq.Compound.makeCompound([s for n, s in hot])
    old22 = get("old_p22")
    p01 = load(R31N["p01"])
    hw = load(R31N["hardware"])
    print("P01 bounds", [round(v, 2) for v in bounds(p01)], "| hardware solids", len(hw.Solids()))
    for s in hw.Solids():
        print("  hw", [round(v, 2) for v in bounds(s)], round(s.Volume(), 1))
    # distances from a proud screw head on the cheek's front face to the tools
    for x in (18.0, -18.0):
        head = cq.Solid.makeCylinder(2.75, 3.0, cq.Vector(x, 19.8, -54.28), cq.Vector(0, 1, 0))
        print("proud SHCS head at X", x, "-> tools", round(head.distance(tools), 3), "| P22 x head", round(head.intersect(old22).Volume(), 2))
    items = [(old22, "#999999", "P22 released"), (p01, "magenta", "P01 R31"), (hw, "orange", "screws/inserts"),
             (tools, "green", "tool body + hotend")]
    for y in (13.0, 15.0, 17.0, 19.5):
        plot_sections(f"c_xz_y{y}.png", items, "y", y, (10, 26), (-64, -46), f"Cheek, XZ at Y {y}")
    plot_sections("c_yz_x18.png", items, "x", 18.0, (8, 26), (-64, -46), "Cheek, YZ at X 18")
    plot_sections("c_yz_x21.png", items, "x", 21.0, (8, 26), (-64, -46), "Cheek, YZ at X 21")
    for z in (-54.28, -51.0, -57.5):
        plot_sections(f"c_xy_z{z}.png", items, "z", z, (8, 26), (6, 26), f"Cheek, XY at Z {z}")
    print("ok")
