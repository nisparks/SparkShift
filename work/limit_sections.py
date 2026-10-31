"""Sections of the two printed bodies at the features that limit the remaining clearances (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from matplotlib.patches import Rectangle

from audit_low_z_bed_clearance import load_parked_variants
from build_modular_toolhead import box, load

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
PLANES = {"X": ("YZ", 1, 2), "Y": ("ZX", 0, 2), "Z": ("XY", 0, 1)}
red = load_parked_variants()["RedLizard"]["tool"].Solids()
BODIES = {
    "bambu": [("R30 body", load("Bambu_Compact_Fan_Closed_Bores_R30_REVIEW"), (0.95, 0.62, 0.05), 0.85),
              ("hotend", load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.6, 0.6, 0.65), 0.6),
              ("hotend hw", load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"), (0.1, 0.7, 0.2), 0.9),
              ("fan", load("Bambu_Fan_2510_And_Screws_R30_REVIEW"), (0.15, 0.15, 0.2), 0.5),
              ("P18", load("P18_Tool_docking_backplate_3010"), (0.8, 0.15, 0.75), 0.7),
              ("dock", load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW"), (0.2, 0.45, 0.3), 0.5)],
    "redlizard": [("R30 trimmed body", load("RedLizard_Side2510_Strip_Trim_R30_REVIEW"), (0.95, 0.62, 0.05), 0.85),
                  ("hotend+hw", cq.Compound.makeCompound(red[1:14]), (0.6, 0.6, 0.65), 0.6),
                  ("fan+screws", cq.Compound.makeCompound(red[14:19]), (0.15, 0.15, 0.2), 0.5),
                  ("P18", cq.Compound.makeCompound(red[19:]), (0.8, 0.15, 0.75), 0.7),
                  ("dock", load("21_RedLizard_Closed_Panel_Dock_Complete_REVIEW"), (0.2, 0.45, 0.3), 0.5)],
}


def polys(shape, axis, value, clip):
    plane, a, b = PLANES[axis]
    shape = shape.intersect(clip)
    if shape.isNull() or not shape.Solids():
        return []
    try:
        faces = cq.Workplane(plane).add(shape).section(value).faces().vals()
    except Exception:
        return []
    out = []
    for face in faces:
        vertices, triangles = face.tessellate(0.02, 0.2)
        pts = [(v.x, v.y, v.z) for v in vertices]
        out += [[(pts[i][a], pts[i][b]) for i in t] for t in triangles]
    return out


def plot(tag, axis, value, window, marks=()):
    plane, a, b = PLANES[axis]
    names = "XYZ"
    lo = {k: v[0] for k, v in window.items()}
    hi = {k: v[1] for k, v in window.items()}
    lo[axis], hi[axis] = value - 0.6, value + 0.6
    clip = box(lo["X"], hi["X"], lo["Y"], hi["Y"], lo["Z"], hi["Z"])
    fig, ax = plt.subplots(figsize=(8, 6.5), dpi=130)
    handles = []
    for label, shape, color, alpha in BODIES[tag]:
        p = polys(shape, axis, value, clip)
        if p:
            ax.add_collection(PolyCollection(p, facecolors=[color], edgecolors="none", alpha=alpha))
            handles.append(Rectangle((0, 0), 1, 1, color=color, alpha=alpha, label=label))
    for x, y, text in marks:
        ax.axvline(x, color="red", lw=0.6, ls="--") if y is None else ax.axhline(y, color="red", lw=0.6, ls="--")
        ax.text(x if x is not None else window[names[a]][0] + 0.2, y if y is not None else window[names[b]][1] - 0.6,
                text, color="red", fontsize=7)
    ax.set_xlim(*window[names[a]])
    ax.set_ylim(*window[names[b]])
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.3, alpha=0.6)
    ax.set_xlabel(names[a])
    ax.set_ylabel(names[b])
    ax.set_title(f"{tag}: section {axis}={value}")
    ax.legend(handles=handles, fontsize=6, loc="lower right")
    path = OUT / f"lim_{tag}_{axis}{value:+.2f}.png".replace("+", "p").replace("-", "m")
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    print(path, flush=True)


if __name__ == "__main__":
    win_side = {"X": (-17, 1), "Y": (8, 42), "Z": (-32, -14)}
    for tag in ("bambu", "redlizard"):
        plot(tag, "Y", 20.0, win_side, marks=[(-12.4, None, "X-12.4"), (-13.5, None, "X-13.5")])
        plot(tag, "Z", -24.0, {"X": (-17, 24), "Y": (8, 42), "Z": (-30, -16)}, marks=[(None, 11.4, "P01 front Y11.4")])
    plot("redlizard", "Z", -21.0, {"X": (-17, 24), "Y": (8, 42), "Z": (-30, -16)},
         marks=[(None, 11.4, "P01 front Y11.4"), (14.8, None, "carriage edge from -X bay")])
    plot("redlizard", "X", 14.9, {"X": (0, 30), "Y": (8, 42), "Z": (-30, -14)}, marks=[(11.4, None, "P01 front")])
