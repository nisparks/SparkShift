"""XZ sections through the Red Lizard and Bambu fronts (investigation only)."""

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
red = load_parked_variants()["RedLizard"]["tool"].Solids()
P18 = load("P18_Tool_docking_backplate_3010")
SETS = {
    "rl": [("RL R32 body", load("RedLizard_Side2510_Flush_Side_R32_REVIEW"), (0.95, 0.55, 0.15), 0.85),
           ("RL hotend+hw", cq.Compound.makeCompound(red[1:14]), (0.6, 0.6, 0.65), 0.7),
           ("fan", red[14], (0.15, 0.15, 0.2), 0.5), ("screws/inserts", cq.Compound.makeCompound(red[15:19]), (0.9, 0.75, 0.1), 0.9),
           ("P18", P18, (0.75, 0.2, 0.7), 0.6)],
    "bambu": [("Bambu R32 body", load("Bambu_Compact_Flush_Side_R32_REVIEW"), (0.95, 0.62, 0.05), 0.85),
              ("hotend", load("Tool2510_Reversed_Bambu_Reference_REVIEW"), (0.6, 0.6, 0.65), 0.7),
              ("hotend hw", load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"), (0.1, 0.7, 0.2), 0.9),
              ("fan+screws", load("Bambu_Fan_2510_And_Screws_R30_REVIEW"), (0.15, 0.15, 0.2), 0.5),
              ("P18", P18, (0.75, 0.2, 0.7), 0.6)],
}


def polys(shape, plane, value, clip, a, b):
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


def section_y(tag, y, xr=(-16, 24), zr=(-52, -14)):
    clip = box(xr[0], xr[1], y - 0.6, y + 0.6, zr[0], zr[1])
    fig, ax = plt.subplots(figsize=(8, 7), dpi=120)
    handles = []
    for label, shape, color, alpha in SETS[tag]:
        p = polys(shape, "ZX", y, clip, 0, 2)
        if p:
            ax.add_collection(PolyCollection(p, facecolors=[color], edgecolors="none", alpha=alpha))
            handles.append(Rectangle((0, 0), 1, 1, color=color, alpha=alpha, label=label))
    ax.set_xlim(*xr)
    ax.set_ylim(*zr)
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.3, alpha=0.6)
    ax.set_xlabel("X")
    ax.set_ylabel("Z")
    ax.set_title(f"{tag}: section Y={y}")
    ax.legend(handles=handles, fontsize=6, loc="lower left")
    path = OUT / f"front_{tag}_Y{y:.2f}.png".replace(".", "p", 1)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)
    return path


for tag, ys in (("rl", (31.0, 32.3, 34.0, 36.5)), ("bambu", (34.0, 36.5))):
    for y in ys:
        print(section_y(tag, y), flush=True)
