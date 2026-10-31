"""R43 study: the Cartographer build (R42 scene) and both probes' keepouts around P22's outlet (session scratch)."""
import json
import sys
from pathlib import Path

FILES = Path(__file__).parent
sys.path.insert(0, str(FILES))
import r43_sections as S  # noqa: E402  (sets cwd and sys.path to the repo folder)

import cadquery as cq  # noqa: E402
import r37_parts as P37  # noqa: E402
import r42_parts as R42  # noqa: E402

SCENE = FILES / "r42_scene"


def main():
    m = json.loads((SCENE / "manifest.json").read_text())
    carriage = []
    for n, f in m["carriage"]:
        s = cq.Shape.importBrep(str(SCENE / f))
        if S.near(S.bounds(s)):
            carriage.append((n, s))
    tools = {}
    for label, v in m["variants"].items():
        tools[label] = [(n, s) for n, s in ((n, cq.Shape.importBrep(str(SCENE / f))) for n, f in v["parts"])
                        if S.near(S.bounds(s))]
    print([n for n, _ in carriage])
    keep = [(R42.shape(ko) if not isinstance(ko, cq.Shape) else ko, "purple", f"Cartographer keepout {z}")
            for z, ko in R42.keepouts().items()]
    beacon = [s for n, s in carriage if n.startswith("Beacon")]
    for label, parts in tools.items():
        items = [(s, S.colour_of(n), n[:28]) for n, s in carriage] + keep + \
                [(s, "blue", f"{label} tool") for _, s in parts]
        tag = "carto_" + label.lower()
        for z in (-76.0, -74.6, -73.0, -71.0):
            S.plot(f"{tag}_plan_z{z:g}.png", items, "z", z, (-30, 30), (-20, 36), f"Cartographer, {label}: plan at Z{z:g}",
                   marks=[S.NOZZLE[:2]])
        for x in (0.0, 8.0):
            S.plot(f"{tag}_side_x{x:g}.png", items, "x", x, (-20, 36), (-82, -55),
                   f"Cartographer, {label}: side at X{x:g}", marks=[(S.NOZZLE[1], S.NOZZLE[2])])
    for n, s in carriage:
        if n.startswith(("Cartographer", "P23")):
            print(n, [round(v, 2) for v in S.bounds(s)])
    for z, ko in R42.keepouts().items():
        s = R42.shape(ko) if not isinstance(ko, cq.Shape) else ko
        print("keepout", z, [round(v, 2) for v in S.bounds(s)])


if __name__ == "__main__":
    main()
