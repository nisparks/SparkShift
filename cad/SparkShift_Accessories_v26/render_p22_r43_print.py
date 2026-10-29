"""Revision 43 printing figure: P22 on its back face, revision 41 against revision 43, overhangs coloured.

93: where each P22 needs support on its back face. Red: facets facing down more steeply than the 30 degree
    threshold over P22 itself, where a support from the plate can't reach; orange: those a support from the plate
    can reach; yellow: 30-45 degrees, printed without support; blue: on the plate.

Run: python render_p22_r43_print.py
"""
import math

import cadquery as cq
import numpy as np
import trimesh

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

import build_and_verify_accessories_v26 as acc  # noqa: E402
import build_cpap_outlet_r43 as Bv  # noqa: E402
import r41_parts as R41  # noqa: E402
import r43_parts as R43  # noqa: E402
from build_modular_toolhead import ROOT  # noqa: E402

LIGHT = np.array([0.35, -0.55, 0.75]) / np.linalg.norm([0.35, -0.55, 0.75])


def printed_mesh(s, tag):
    path = acc.WORK / f"r43_render_{tag}.stl"
    cq.exporters.export(Bv.print_oriented(s), str(path), tolerance=0.02, angularTolerance=0.1)
    m = trimesh.load_mesh(str(path))
    path.unlink()
    return m


def colours(m):
    n, c = m.face_normals, m.triangles_center
    bed = (n[:, 2] < -0.999) & (c[:, 2] < 0.02)
    d30 = (n[:, 2] < -math.sin(math.radians(90 - Bv.SUPPORT_DEG))) & ~bed
    d45 = (n[:, 2] < -math.sin(math.radians(45))) & ~bed & ~d30
    idx = np.nonzero(d30)[0]
    hit = np.zeros(len(n), bool)
    hit[idx] = m.ray.intersects_any(c[idx] + [0, 0, -0.02], np.tile([0.0, 0.0, -1.0], (len(idx), 1)))
    base = np.tile([0.62, 0.78, 0.76], (len(n), 1))
    base[d45] = [0.98, 0.80, 0.25]
    base[d30 & ~hit] = [0.95, 0.45, 0.10]
    base[d30 & hit] = [0.85, 0.10, 0.15]
    base[bed] = [0.25, 0.35, 0.85]
    shade = 0.55 + 0.45 * np.clip(n @ LIGHT, 0, 1)
    return np.clip(base * shade[:, None], 0, 1)


def view(ax, m, elev, azim, title):
    ax.add_collection3d(Poly3DCollection(m.vertices[m.faces], facecolors=colours(m), edgecolors="none", linewidths=0))
    lo, hi = m.bounds
    ax.set_xlim(lo[0], hi[0])
    ax.set_ylim(lo[1], hi[1])
    ax.set_zlim(0, hi[2])
    ax.set_box_aspect(hi - [lo[0], lo[1], 0])
    ax.view_init(elev=elev, azim=azim)
    ax.set_title(title, fontsize=11, pad=26)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")
    ax.set_zlabel("print height (mm)")


def main():
    meshes = {"Revision 41": printed_mesh(R41.p22(), "r41"), "Revision 43": printed_mesh(R43.p22(), "r43")}
    fig = plt.figure(figsize=(18, 17))
    for col, (tag, m) in enumerate(meshes.items()):
        o = Bv.overhang(m)
        head = (f"{tag}: {o['on_plate_mm2']:.0f} mm2 on the plate; {o['needs_support_mm2']:.0f} mm2 needs support, "
                f"{o['reachable_from_plate_mm2']:.0f} of it reachable from the plate")
        view(fig.add_subplot(2, 2, col + 1, projection="3d"), m, -22, -62, head + "\nfrom the front, below")
        view(fig.add_subplot(2, 2, col + 3, projection="3d"), m, -22, 118, "from the back, below")
    fig.suptitle("P22 on its back face. Red: overhang under 30 degrees over P22 itself (a support from the plate can't reach it);\n"
                 "orange: under 30 degrees, reachable from the plate; yellow: 30-45 degrees, no support; blue: on the plate",
                 fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    path = ROOT / "images" / "93_p22_r43_print_overhangs.png"
    fig.savefig(path, dpi=75)
    print(path)


if __name__ == "__main__":
    main()
