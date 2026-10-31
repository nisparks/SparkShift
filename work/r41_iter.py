"""Fast R41 iteration: rebuild the changed parts, then interference, wall thickness and sections."""
import sys
import time

sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
from r41_diag import *  # noqa: E402,F403
import build_carriage_fixes_r41 as B  # noqa: E402

what = set(sys.argv[1:]) or {"build", "walls", "plots"}
if "build" in what:
    for k in ("p20", "p21", "p22", "p24", "p02"):
        get(k, rebuild=True)
    for k in R.MAGNETS:
        t = time.perf_counter()
        R.p03(k).exportBrep(str(OUT / f"p03_{k}.brep"))
        print(f"built p03_{k} in {time.perf_counter() - t:.1f} s", flush=True)
new = {k: get(k) for k in ("p20", "p21", "p22", "p24", "p02")}
old = {k: get("old_" + k) for k in ("p20", "p21", "p22", "p24", "p02")}
p03 = {k: cq.Shape.importBrep(str(OUT / f"p03_{k}.brep")) for k in R.MAGNETS}
for k, s in list(new.items()) + [(f"p03_{k}", v) for k, v in p03.items()]:
    print(k, "valid", s.isValid(), "solids", len(s.Solids()), "volume", round(s.Volume(), 1))
print("P21 x P22", round(new["p21"].intersect(new["p22"]).Volume(), 3),
      "P20 x P21", round(new["p20"].intersect(new["p21"]).Volume(), 3))

if "walls" in what:
    zones = {"P20_sleeve": ("p20", [B.JOINTS[0][4]]), "P21_joints": ("p21", [B.JOINTS[0][4], B.JOINTS[1][4]]),
             "P22_socket": ("p22", [B.JOINTS[1][4]]),
             "P22_outlet": ("p22", [(8.4, 18.5, 16.5, 28.6, -78.0, -73.0), (-18.5, -8.4, 16.5, 28.6, -78.0, -73.0)]),
             "P24": ("p24", None)}
    meshes, old_meshes = {}, {}
    for label, (k, z) in zones.items():
        if k not in meshes:
            meshes[k], old_meshes[k] = B.to_mesh(new[k], k), B.to_mesh(old[k], "old_" + k)
        r, o = B.wall_report(meshes[k], z), B.wall_report(old_meshes[k], z)
        print(label, "R41", {kk: v for kk, v in r.items() if kk != "thinnest_at"})
        print("   thinnest", r.get("thinnest_at"))
        print("   released", {kk: v for kk, v in o.items() if kk != "thinnest_at"})
    cots = B.to_mesh(load("P03_Front_case_COTS"), "old_p03")
    o = B.wall_report(cots, B.ZONES["P03"])
    print("P03 released", {kk: v for kk, v in o.items() if kk != "thinnest_at"}, o.get("thinnest_at"))
    for k, s in p03.items():
        r = B.wall_report(B.to_mesh(s, f"p03_{k}"), B.ZONES["P03"])
        print(f"P03 {k}", {kk: v for kk, v in r.items() if kk != "thinnest_at"})
        print("   thinnest", r.get("thinnest_at"))

if "plots" in what:
    p20, p21, p22, p24 = new["p20"], new["p21"], new["p22"], new["p24"]
    plot_sections("j1_yz_x8.74.png", [(old["p20"], "#bbbbbb", "P20 released"), (p20, "red", "P20 R41"), (p21, "blue", "P21 R41")],
                  "x", 8.74, (-47, -40), (-23, -14), "P20/P21 joint, YZ at X 8.74 (back wall)")
    plot_sections("j2_yz_x5.png", [(old["p22"], "#bbbbbb", "P22 released"), (p22, "red", "P22 R41"), (p21, "blue", "P21 R41")],
                  "x", 5.16, (-47, -28), (-55, -47), "P21/P22 joint, YZ at X 5.16")
    for y in (20.0, 21.7, 25.0):
        plot_sections(f"out_xz_y{y}.png", [(old["p22"], "#bbbbbb", "P22 released"), (p22, "red", "P22 R41")],
                      "y", y, (6, 22), (-79, -71), f"Outlet, XZ at Y {y}")
    for z in (-77.2, -76.4):
        plot_sections(f"out_xy_z{z}.png", [(old["p22"], "#bbbbbb", "P22 released"), (p22, "red", "P22 R41")],
                      "z", z, (-23, 23), (14, 31), f"Outlet, XY at Z {z}")
    core_near = cq.Shape.importBrep(str(OUT / "core_near_p24.brep"))
    ebb = P37.ebb42()
    zones = cq.Compound.makeCompound([box(*z) for z in R.PLUG_ZONES])
    items = [(core_near, "#999999", "core near P24"), (ebb, "green", "EBB42"), (zones, "orange", "plug zones"),
             (p24, "red", "P24 R41")]
    for y in (-8.0, -15.0, -21.0):
        plot_sections(f"p24_xz_y{y}.png", items, "y", y, (-25, 25), (-20, 30), f"P24, XZ at Y {y}")
    plot_sections("p24_yz_x14.25.png", items, "x", 14.252, (-36, -5), (-20, 30), "P24, YZ at X 14.252 (TL insert)")
    plot_sections("p24_yz_x-16.75.png", items, "x", -16.748, (-36, -5), (-20, 30), "P24, YZ at X -16.748 (TR insert)")
    items = [(load("P03_Front_case_COTS"), "#999999", "P03 released (COTS)"), (p03["15x5x3"], "red", "15x5x3"),
             (p03["12x6x3"], "blue", "12x6x3"), (p03["D6x4"], "green", "D6x4")]
    plot_sections("p03_xz_y30.5.png", items, "y", 30.5, (-14, 14), (-8, 38), "P03, XZ at Y 30.5")
    print("plots done")
