"""Sections of the carriage under the own and neighbour 2510 fans (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle

from build_modular_toolhead import box, load

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
PLANES = {"X": ("YZ", 1, 2), "Y": ("ZX", 0, 2), "Z": ("XY", 0, 1)}
PITCH = 37.3

core = load("Core_With_Restrained_AHG_Lead_References_REVIEW").Solids()
p01 = core[54]
core_other = cq.Compound.makeCompound([s for i, s in enumerate(core) if i != 54])
fan = load("Bambu_Fan_2510_And_Screws_R30_REVIEW")
body = load("Bambu_Compact_Fan_Closed_Bores_R30_REVIEW")
ITEMS = [
    ("P01", p01, (0.45, 0.47, 0.52), 0.85),
    ("other core", core_other, (0.25, 0.25, 0.75), 0.6),
    ("P22", load("P22_CPAP_Lower_Plenum"), (0.1, 0.65, 0.65), 0.7),
    ("P21", load("P21_CPAP_Gantry_Bridge"), (0.2, 0.8, 0.3), 0.6),
    ("P23", load("P23_Beacon_Cartographer_Mount"), (0.85, 0.3, 0.3), 0.6),
    ("acc hw", load("Accessory_Hardware_Complete") if False else None, (0.9, 0.8, 0.1), 0.9),
    ("R30 body", body, (0.95, 0.62, 0.05), 0.5),
    ("own fan", fan, (0.1, 0.1, 0.12), 0.6),
    ("neighbour fan", fan.translate(cq.Vector(-PITCH, 0, 0)), (0.5, 0.1, 0.5), 0.6),
]
ITEMS = [i for i in ITEMS if i[1] is not None]


def section_polys(shape, axis, value, clip):
    plane, a, b = PLANES[axis]
    shape = shape.intersect(clip)
    if shape.isNull() or not shape.Solids():
        return []
    try:
        faces = cq.Workplane(plane).add(shape).section(value).faces().vals()
    except Exception:
        return []
    polys = []
    for face in faces:
        vertices, triangles = face.tessellate(0.02, 0.2)
        pts = [(v.x, v.y, v.z) for v in vertices]
        for t in triangles:
            polys.append([(pts[i][a], pts[i][b]) for i in t])
    return polys


def plot(axis, value, window, tag):
    plane, a, b = PLANES[axis]
    names = "XYZ"
    lo = {k: v[0] for k, v in window.items()}
    hi = {k: v[1] for k, v in window.items()}
    lo[axis], hi[axis] = value - 0.6, value + 0.6
    clip = box(lo["X"], hi["X"], lo["Y"], hi["Y"], lo["Z"], hi["Z"])
    fig, ax = plt.subplots(figsize=(9, 7), dpi=130)
    handles = []
    for label, shape, color, alpha in ITEMS:
        polys = section_polys(shape, axis, value, clip)
        if polys:
            ax.add_collection(PolyCollection(polys, facecolors=[color], edgecolors="none", alpha=alpha))
            handles.append(Rectangle((0, 0), 1, 1, color=color, alpha=alpha, label=label))
    ax.set_xlim(*window[names[a]])
    ax.set_ylim(*window[names[b]])
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.3, alpha=0.6)
    ax.set_xlabel(names[a])
    ax.set_ylabel(names[b])
    ax.set_title(f"{tag}: section {axis}={value}")
    ax.legend(handles=handles, fontsize=6, loc="upper right")
    path = OUT / f"{tag}_{axis}{value:+.2f}.png".replace("+", "p").replace("-", "m")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path, flush=True)


if __name__ == "__main__":
    yz = {"X": (-30, 30), "Y": (-2, 42), "Z": (-64, -40)}
    for x in (18.0, 20.5, -18.0, -21.0):
        plot("X", x, yz, "mounts")
    plot("Z", -49.5, {"X": (-30, 30), "Y": (-2, 42), "Z": (-64, -40)}, "mounts")
    plot("Z", -52.78, {"X": (-30, 30), "Y": (-2, 42), "Z": (-64, -40)}, "mounts")
    plot("Y", 14.0, {"X": (-30, 30), "Y": (-2, 42), "Z": (-64, -40)}, "mounts")
    plot("Y", 18.0, {"X": (-30, 30), "Y": (-2, 42), "Z": (-64, -40)}, "mounts")
