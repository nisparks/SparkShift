"""R43 study: sections of P22's outlet region with the hotends, the probe and their neighbours (session scratch)."""
import json
import sys
from pathlib import Path

HERE = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
FILES = Path(__file__).parent
OUT = FILES / "r43"
OUT.mkdir(exist_ok=True)
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(FILES))
import os  # noqa: E402
os.chdir(HERE)

import cadquery as cq  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section  # noqa: E402
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir  # noqa: E402

SCENE = FILES / "r41_scene"
NOZZLE = (0.0, 22.7, -78.88)
REGION = (-32.0, 32.0, -20.0, 40.0, -82.0, -45.0)


def manifest():
    return json.loads((SCENE / "manifest.json").read_text())


def bounds(s):
    b = s.BoundingBox()
    return (b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax)


def near(b, o=REGION):
    return b[1] > o[0] and b[0] < o[1] and b[3] > o[2] and b[2] < o[3] and b[5] > o[4] and b[4] < o[5]


def load_scene():
    m = manifest()
    carriage = []
    for n, f in m["carriage"]:
        s = cq.Shape.importBrep(str(SCENE / f))
        if near(bounds(s)):
            carriage.append((n, s))
    tools = {}
    for label, v in m["variants"].items():
        tools[label] = [(n, cq.Shape.importBrep(str(SCENE / f))) for n, f in v["parts"]]
        tools[label] = [(n, s) for n, s in tools[label] if near(bounds(s))]
    return carriage, tools


def section_edges(s, axis, at):
    n = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    o = [0, 0, 0]
    o["xyz".index(axis)] = at
    sec = BRepAlgoAPI_Section(s.wrapped, gp_Pln(gp_Pnt(*o), gp_Dir(*n)))
    sec.Build()
    out = []
    for e in cq.Shape.cast(sec.Shape()).Edges():
        out.append([e.positionAt(t / 30).toTuple() for t in range(31)])
    return out


def plot(fname, items, axis, at, xlim, ylim, title, marks=()):
    h, v = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    fig, ax = plt.subplots(figsize=(10, 10 * (ylim[1] - ylim[0]) / (xlim[1] - xlim[0]) + 0.8))
    seen = set()
    for s, colour, label in items:
        for pts in section_edges(s, axis, at):
            ax.plot([p[h] for p in pts], [p[v] for p in pts], color=colour, lw=1.1,
                    label=None if label in seen else label)
            seen.add(label)
    for m in marks:
        ax.plot([m[0]], [m[1]], "kx", ms=9)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.3)
    ax.legend(loc="upper right", fontsize=7)
    ax.set_title(title)
    fig.savefig(OUT / fname, dpi=100, bbox_inches="tight")
    plt.close(fig)


COLOURS = {"P22": "teal", "P23": "orange", "P01": "magenta", "Beacon": "red", "Cartographer": "red"}


def colour_of(n):
    for k, c in COLOURS.items():
        if k.lower() in n.lower():
            return c
    return "grey"


if __name__ == "__main__":
    carriage, tools = load_scene()
    print("carriage near the outlet:", [n for n, _ in carriage])
    for label, parts in tools.items():
        print(label, [n for n, _ in parts])
    for label, parts in tools.items():
        items = [(s, colour_of(n), n.split(":")[-1][:28]) for n, s in carriage] + \
                [(s, "blue", f"{label} tool") for _, s in parts]
        tag = label.lower()
        for z in (-77.4, -76.0, -74.6, -73.0, -71.0, -68.0, -64.0):
            plot(f"{tag}_plan_z{z:g}.png", items, "z", z, (-30, 30), (-20, 36), f"{label}: plan at Z{z:g}",
                 marks=[NOZZLE[:2]])
        for x in (0.0, 11.0, 16.0):
            plot(f"{tag}_side_x{x:g}.png", items, "x", x, (-20, 36), (-82, -55), f"{label}: side section at X{x:g}",
                 marks=[(NOZZLE[1], NOZZLE[2])])
        for y in (22.7, 17.0, 27.0, 12.0):
            plot(f"{tag}_front_y{y:g}.png", items, "y", y, (-30, 30), (-82, -55), f"{label}: section at Y{y:g}",
                 marks=[(NOZZLE[0], NOZZLE[2])])
    print("written to", OUT)
