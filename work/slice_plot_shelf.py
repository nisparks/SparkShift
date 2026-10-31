"""Plot 2D sections of the Bambu body and all neighbouring parts (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection

import cadquery as _cq
from build_modular_toolhead import box, load

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
OUT.mkdir(exist_ok=True)
WINDOW = {"X": (6, 17), "Y": (10, 39), "Z": (-30, -16)}
PLANES = {"X": ("YZ", 1, 2), "Y": ("ZX", 0, 2), "Z": ("XY", 0, 1)}


def load_any(name):
    return _cq.importers.importStep(name).val() if name.lower().endswith('.step') else load(name)


def parts(body_name):
    return [
        ("body", load_any(body_name), (0.95, 0.62, 0.05), 0.85),
        ("core", load("Core_With_Restrained_AHG_Lead_References_REVIEW"), (0.35, 0.38, 0.42), 0.75),
        ("P18", load("P18_Tool_docking_backplate_3010"), (0.8, 0.15, 0.75), 0.8),
        ("hotend", load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.6, 0.6, 0.65), 0.8),
        ("hotend hw", load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"), (0.1, 0.7, 0.2), 0.9),
        ("fan", load("Tool2510_Single_Tool_Owned_2510_Nominal_Reference_REVIEW"), (0.15, 0.3, 0.85), 0.5),
        ("fan screws", load("Tool2510_Two_Upper_M2_5_Low_Head_Screws_REVIEW"), (0.0, 0.4, 0.1), 0.9),
        ("CPAP", load("P22_CPAP_Lower_Plenum"), (0.1, 0.65, 0.65), 0.6),
    ]


def section_polys(shape, axis, value, clip):
    plane, a, b = PLANES[axis]
    shape = shape.intersect(clip)
    if shape.isNull() or not shape.Solids():
        return []
    offset = value if axis != "Y" else value
    try:
        faces = cq.Workplane(plane).add(shape).section(offset).faces().vals()
    except Exception:
        return []
    polys = []
    for face in faces:
        vertices, triangles = face.tessellate(0.02, 0.2)
        pts = [(v.x, v.y, v.z) for v in vertices]
        for t in triangles:
            polys.append([(pts[i][a], pts[i][b]) for i in t])
    return polys


def plot(body_name, axis, value, tag, items):
    plane, a, b = PLANES[axis]
    names = "XYZ"
    fig, ax = plt.subplots(figsize=(9, 7), dpi=130)
    lo = {k: v[0] for k, v in WINDOW.items()}
    hi = {k: v[1] for k, v in WINDOW.items()}
    lo[axis], hi[axis] = value - 0.6, value + 0.6
    clip = box(lo["X"], hi["X"], lo["Y"], hi["Y"], lo["Z"], hi["Z"])
    handles = []
    for label, shape, color, alpha in items:
        polys = section_polys(shape, axis, value, clip)
        if polys:
            ax.add_collection(PolyCollection(polys, facecolors=[color], edgecolors="none", alpha=alpha))
            handles.append(plt.Rectangle((0, 0), 1, 1, color=color, alpha=alpha, label=label))
    ax.set_xlim(*WINDOW[names[a]])
    ax.set_ylim(*WINDOW[names[b]])
    ax.set_aspect("equal")
    ax.set_xticks(range(int(WINDOW[names[a]][0]), int(WINDOW[names[a]][1]) + 1, 2))
    ax.set_yticks(range(int(WINDOW[names[b]][0]), int(WINDOW[names[b]][1]) + 1, 2))
    ax.tick_params(labelsize=6)
    ax.grid(True, linewidth=0.3, alpha=0.6)
    ax.set_xlabel(names[a])
    ax.set_ylabel(names[b])
    ax.set_title(f"{tag}: section {axis}={value}")
    ax.legend(handles=handles, fontsize=6, loc="upper right")
    path = OUT / f"{tag}_sec_{axis}{value:+.2f}.png".replace("+", "p").replace("-", "m")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path)


if __name__ == "__main__":
    body_name, tag = sys.argv[1], sys.argv[2]
    items = parts(body_name)
    for spec in sys.argv[3:]:
        plot(body_name, spec[0], float(spec[1:]), tag, items)

