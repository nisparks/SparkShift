"""R41 rework: build the new P22 and P02, measure the jets, walls, face mounts and servo pocket (session scratch)."""
import sys

sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
from r41_diag import *  # noqa: E402,F403
from r41_diag2 import hotends  # noqa: E402
import build_carriage_fixes_r41 as B  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31N  # noqa: E402

OUTLET = [(8.3, 21.5, 15.0, 30.0, -78.2, -73.0), (-21.5, -8.3, 15.0, 30.0, -78.2, -73.0)]
CHEEKS = [(13.8, 22.6, 11.0, 21.0, -63.0, -49.4), (-22.6, -13.8, 11.0, 21.0, -63.0, -49.4)]


def throat(p22):
    """Open area in planes across the jets, inside P22's outer YZ profile (not the air under its heel)."""
    horn = R.shape(R.a.prism_yz_r(R.HORN_OUT, R.HORN_OUT_R, -23.0, 23.0))
    out = {}
    for x in (10.3, 10.9, 11.5):
        total = 0.0
        for s in (-1, 1):
            win = B.box(*sorted((s * (x - 0.01), s * (x + 0.01))), 16.0, 29.5, -76.70, -73.0).intersect(horn)
            total += (win.Volume() - win.intersect(p22).Volume()) / 0.02
        out[x] = round(total, 1)
    return out


what = set(sys.argv[1:]) or {"p22", "p02"}
old22 = get("old_p22")
if "p22" in what:
    hot = hotends()
    tools = cq.Compound.makeCompound([s for n, s in hot])
    print("released throat", throat(old22))
    if "roofs" in what:
        for roof in (-73.6, -73.4):
            R.ROOF = roof
            s = R.p22()
            print("ROOF", roof, "throat", throat(s))
        R.ROOF = -74.0
    if "only_throat" in what:
        print("ROOF -74.0 throat", throat(get("p22")))
        what.discard("p22")
if "p22" in what:
    hot = hotends()
    tools = cq.Compound.makeCompound([s for n, s in hot])
    p22 = get("p22", rebuild=True)
    print("P22 valid", p22.isValid(), len(p22.Solids()), round(p22.Volume(), 1), [round(v, 3) for v in B.exact_bounds(p22)])
    print("ROOF", R.ROOF, "throat", throat(p22))
    m, mo = B.to_mesh(p22, "p22"), B.to_mesh(old22, "old_p22")
    for label, zones in (("outlet", OUTLET), ("cheeks", CHEEKS)):
        r, o = B.wall_report(m, zones), B.wall_report(mo, zones)
        print(label, "R41", {k: v for k, v in r.items() if k != "thinnest_at"}, r["thinnest_at"][:3])
        print("   released", {k: v for k, v in o.items() if k != "thinnest_at"}, o["thinnest_at"][:2])
    p01 = load(R31N["p01"])
    hw = dict(R.other_hardware())
    print("P22 x P01", round(p22.intersect(p01).Volume(), 4), "| gap", round(p22.distance(p01), 3),
          "| released gap", round(old22.distance(p01), 3))
    for n, s in hw.items():
        if n.startswith(("R41_P22", "ACC_CASE_BOSS")):
            print(n, "x P22", round(s.intersect(p22).Volume(), 4), "x P01", round(s.intersect(p01).Volume(), 4),
                  "to tools", round(s.distance(tools), 3), [round(v, 2) for v in bounds(s)])
    for label, hw_ in (("Bambu", [s for n, s in hot if n.startswith("Bambu") and "hotend" in n]),
                       ("RedLizard", [s for n, s in hot if n.startswith("RedLizard") and "hotend" in n])):
        c = cq.Compound.makeCompound(hw_)
        print("hotend gap", label, round(p22.distance(c), 3), "released", round(old22.distance(c), 3))
    bam = cq.Compound.makeCompound([s for n, s in hot if n.startswith("Bambu") and "|body|" not in n])
    rl = cq.Compound.makeCompound([s for n, s in hot if n.startswith("RedLizard") and "|body|" not in n])
    items = [(old22, "#bbbbbb", "P22 released"), (p22, "red", "P22 R41"), (bam, "green", "Bambu"), (rl, "blue", "Red Lizard")]
    for y in (19.5, 22.7, 26.0):
        plot_sections(f"n_xz_y{y}.png", items, "y", y, (0, 24), (-80, -68), f"Outlet, XZ at Y {y}")
    plot_sections("n_yz_x10.6.png", items, "x", 10.6, (10, 31), (-80, -68), "Outlet, YZ at X 10.6")
    items = [(old22, "#bbbbbb", "P22 released"), (p22, "red", "P22 R41"), (p01, "magenta", "P01"),
             (cq.Compound.makeCompound([s for n, s in hw.items() if n.startswith(("R41_P22", "ACC_CASE_BOSS_HEAT"))]),
              "orange", "screw + insert")]
    plot_sections("n_cheek_yz_x18.png", items, "x", 18.0, (8, 26), (-64, -46), "Cheek, YZ at X 18")
    plot_sections("n_cheek_xy_z-54.28.png", items, "z", -54.28, (8, 26), (6, 26), "Cheek, XY at Z -54.28")
    plot_sections("n_cheek_xz_y17.png", items, "y", 17.0, (10, 26), (-64, -46), "Cheek, XZ at Y 17")
if "p02" in what:
    p02, old02 = get("p02", rebuild=True), get("old_p02")
    print("P02 valid", p02.isValid(), len(p02.Solids()), round(p02.Volume(), 2), "released", round(old02.Volume(), 2))
    body = R.shape(R.pocket_box(R.SERVO_DATASHEET, R.PLATE_REAR))
    env = B.box(*R.SERVO_ENVELOPE[:2], R.PLATE_REAR, R.POCKET_FLOOR, *R.SERVO_ENVELOPE[2:])
    print("datasheet body: x P02", round(p02.intersect(body).Volume(), 4), "gap", round(p02.distance(body), 3),
          "| released gap", round(old02.distance(body), 3))
    print("STEP envelope body: x P02", round(p02.intersect(env).Volume(), 4), [round(v, 3) for v in bounds(p02.intersect(env))])
    zone = [(2.0, 19.0, -11.3, -6.6, 31.0, 59.5)]
    r, o = B.wall_report(B.to_mesh(p02, "p02"), zone), B.wall_report(B.to_mesh(old02, "old_p02"), zone)
    print("P02 pocket walls R41", {k: v for k, v in r.items() if k != "thinnest_at"}, r["thinnest_at"][:2])
    print("   released", {k: v for k, v in o.items() if k != "thinnest_at"}, o["thinnest_at"][:2])
    from build_carriage_lowered_mounts_r31 import confined
    c = confined(p02.copy(), old02.copy(), [(4.2, 16.8, -11.4, -6.6, 33.6, 57.1)])
    print("P02 unchanged outside the pocket", c["unchanged_outside_zones"])
    items = [(old02, "#bbbbbb", "P02 released"), (p02, "red", "P02 R41"), (body, "green", "MG90D 12.2 x 22.8")]
    plot_sections("n_p02_xz_y-9.png", items, "y", -9.0, (0, 21), (30, 61), "P02 pocket, XZ at Y -9")
print("done")
