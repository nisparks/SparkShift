"""R41 rework diagnostics: P22 outlet against both hotends, P22 cheeks against P01's bosses (session scratch)."""
import sys

sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
from r41_diag import *  # noqa: E402,F403


def hotends():
    path = OUT / "hotends.brep"
    names = OUT / "hotends.txt"
    if path.exists():
        return list(zip(names.read_text().split("\n"), cq.Shape.importBrep(str(path)).Solids()))
    import build_probe_height_datum_dock_r37 as b37
    tools = b37.tools(P37.bambu_hotend()[0])
    out = []
    for label, v in tools.items():
        for n, s in v["parts"]:
            if "hotend" in n.lower() or n == "body":
                for k, x in enumerate(s.Solids()):
                    out.append((f"{label}|{n}|{k}", x))
    cq.Compound.makeCompound([s for _, s in out]).exportBrep(str(path))
    names.write_text("\n".join(n for n, _ in out))
    return out


if __name__ == "__main__":
    from build_carriage_lowered_mounts_r31 import NAMES as R31N
    hot = hotends()
    for n, s in hot:
        if "body" not in n:
            print(n, [round(v, 2) for v in bounds(s)])
    bam = cq.Compound.makeCompound([s for n, s in hot if n.startswith("Bambu") and "|body|" not in n])
    rl = cq.Compound.makeCompound([s for n, s in hot if n.startswith("RedLizard") and "|body|" not in n])
    bodies = cq.Compound.makeCompound([s for n, s in hot if "|body|" in n])
    old22, new22 = get("old_p22"), get("p22")
    p01 = load(R31N["p01"]) if "p01" in R31N else None
    print("R31 names", R31N)
    items = [(old22, "#999999", "P22 released"), (bam, "green", "Bambu hotend"), (rl, "blue", "Red Lizard hotend")]
    for y in (19.5, 22.7, 26.0):
        plot_sections(f"o2_xz_y{y}.png", items, "y", y, (0, 24), (-80, -68), f"Outlet, XZ at Y {y}")
    for x in (9.0, 10.6, 12.5):
        plot_sections(f"o2_yz_x{x}.png", items, "x", x, (10, 31), (-80, -68), f"Outlet, YZ at X {x}")
    print("ok")
