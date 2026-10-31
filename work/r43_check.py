"""R43 study: clearances and sections of the P22 variants (session scratch)."""
import json
import sys
from pathlib import Path

FILES = Path(__file__).parent
sys.path.insert(0, str(FILES))
import r43_sections as S  # noqa: E402

import cadquery as cq  # noqa: E402

VARIANTS = FILES / "r43" / "variants"


def scene_parts(scene):
    m = json.loads((scene / "manifest.json").read_text())
    out = []
    for n, f in m["carriage"]:
        if n.startswith("P22_"):
            continue
        s = cq.Shape.importBrep(str(scene / f))
        if S.near(S.bounds(s), (-30, 30, -5, 40, -82, -45)):
            out.append((n, s))
    for label, v in m["variants"].items():
        for n, f in v["parts"]:
            s = cq.Shape.importBrep(str(scene / f))
            if S.near(S.bounds(s), (-30, 30, -5, 40, -82, -45)):
                out.append((f"{label}:{n}", s))
    return out


def check(name, p22, parts):
    print(f"== {name}: bounds {[round(v, 2) for v in S.bounds(p22)]}")
    for n, s in parts:
        try:
            v = p22.intersect(s).Volume()
        except Exception:
            v = float("nan")
        d = p22.distance(s)
        if v > 1e-4 or d < 1.0:
            print(f"   {n[:48]:48s} overlap {v:9.4f} mm3   gap {d:6.3f} mm")


if __name__ == "__main__":
    parts41 = scene_parts(FILES / "r41_scene")
    parts42 = [(n, s) for n, s in scene_parts(FILES / "r42_scene") if "Cartographer" in n or "R42" in n or "CARTO" in n]
    names = sys.argv[1:] or ["long", "rear"]
    for k in names:
        p22 = cq.Shape.importBrep(str(VARIANTS / f"p22_{k}.brep"))
        check(k, p22, parts41 + parts42)
        items = [(p22, "teal", f"P22 {k}")] + [(s, "orange" if n.startswith("P23") else
                                               ("red" if n.startswith(("Beacon", "Cartographer")) else "blue"),
                                               n.split(":")[0][:20]) for n, s in parts41
                                              if n.startswith(("P23", "Beacon", "Bambu:hotend", "RedLizard:hotend"))]
        for z in (-76.0, -74.8, -73.4, -72.0):
            S.plot(f"{k}_plan_z{z:g}.png", items, "z", z, (-24, 24), (6, 31), f"P22 {k}: plan at Z{z:g}")
        for x in (10.6, 11.2, 13.5, 17.0):
            S.plot(f"{k}_side_x{x:g}.png", items, "x", x, (6, 31), (-79, -60), f"P22 {k}: side at X{x:g}")
