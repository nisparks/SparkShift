"""R41 diagnostics: cache parts as BREP, take sections, report interferences (session scratch, not committed)."""
import os
import sys
import time
from pathlib import Path

HERE = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
OUT = Path(__file__).parent / "r41_diag"
sys.path.insert(0, str(HERE))
os.chdir(HERE)

import cadquery as cq  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from OCP.BRepAlgoAPI import BRepAlgoAPI_Section  # noqa: E402
from OCP.gp import gp_Pln, gp_Pnt, gp_Dir  # noqa: E402

import importlib  # noqa: E402
import r41_parts as R  # noqa: E402
import r40_parts as P40  # noqa: E402
import r37_parts as P37  # noqa: E402
from build_modular_toolhead import load, box  # noqa: E402
from build_p24_cable_entry_r35 import NAMES as R35  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402

BUILD = {
    "p20": lambda: R.p20(), "p21": lambda: R.p21(), "p22": lambda: R.p22(), "p24": lambda: R.p24(),
    "p02": lambda: R.p02(),
    "old_p20": lambda: load(P40.NAMES["p20"]), "old_p21": lambda: load(P40.NAMES["p21"]),
    "old_p22": lambda: P37.p22()[0], "old_p24": lambda: load(R35["p24"]),
    "old_p02": lambda: load("P02_Motor_servo_plate_12p5mm"),
}


def get(name, rebuild=False):
    path = OUT / f"{name}.brep"
    if path.exists() and not rebuild:
        return cq.Shape.importBrep(str(path))
    t = time.perf_counter()
    s = BUILD[name]()
    s.exportBrep(str(path))
    print(f"built {name} in {time.perf_counter() - t:.1f} s", flush=True)
    return s


def section_edges(s, axis, at):
    n = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    o = [0, 0, 0]
    o["xyz".index(axis)] = at
    sec = BRepAlgoAPI_Section(s.wrapped, gp_Pln(gp_Pnt(*o), gp_Dir(*n)))
    sec.Build()
    out = []
    for e in cq.Shape.cast(sec.Shape()).Edges():
        pts = [e.positionAt(t) for t in [i / 40 for i in range(41)]]
        out.append(pts)
    return out


def plot_sections(fname, items, axis, at, xlim, ylim, title, marks=()):
    """items: list of (shape, colour, label)."""
    h, v = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    fig, ax = plt.subplots(figsize=(9, 9 * (ylim[1] - ylim[0]) / (xlim[1] - xlim[0]) + 0.6))
    for s, colour, label in items:
        first = True
        for pts in section_edges(s, axis, at):
            ax.plot([p.toTuple()[h] for p in pts], [p.toTuple()[v] for p in pts], color=colour, lw=1.2,
                    label=label if first else None)
            first = False
    for m in marks:
        ax.plot([m[0]], [m[1]], "kx", ms=8)
    ax.set_xlim(*xlim)
    ax.set_ylim(*ylim)
    ax.set_aspect("equal")
    ax.grid(True, lw=0.3)
    ax.legend(loc="best", fontsize=8)
    ax.set_title(title)
    fig.savefig(OUT / fname, dpi=110, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    what = sys.argv[1:] or ["build"]
    if "build" in what:
        for k in BUILD:
            get(k, rebuild=not k.startswith("old_"))
