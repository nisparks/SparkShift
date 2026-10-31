"""Is any of P22's support inside its duct? Map support samples back to assembly coordinates and classify them."""
import sys
from pathlib import Path

import numpy as np
import trimesh

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))
sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")

import cadquery as cq  # noqa: E402
from OCP.BRepClass3d import BRepClass3d_SolidClassifier  # noqa: E402
from OCP.gp import gp_Pnt  # noqa: E402
from OCP.TopAbs import TopAbs_IN  # noqa: E402

import r41_parts as R  # noqa: E402
import support_map as S  # noqa: E402

FILES = Path(__file__).resolve().parent


def main():
    pts = S.support_points()
    placed = trimesh.load_mesh(str(S.PLACED / "P22_CPAP_Lower_Plenum_Wide_Jets_Face_Mounts_R41_REVIEW_PRINT_ORIENTED.stl"))
    plo, phi = placed.bounds
    near = pts[(pts[:, 0] > plo[0]) & (pts[:, 0] < phi[0]) & (pts[:, 1] > plo[1]) & (pts[:, 1] < phi[1]) & (pts[:, 2] < phi[2])]
    # print -> assembly: rotated +90 deg about X (x, y, z)asm -> (x, -z, y), then centred in XY and set on the bed
    p22 = R.p22()
    bb = p22.BoundingBox()
    cx, cy = (plo[0] + phi[0]) / 2, (plo[1] + phi[1]) / 2
    xa = near[:, 0] - cx + (bb.xmin + bb.xmax) / 2
    za = -((near[:, 1] - cy) + (-bb.zmax - bb.zmin) / 2)
    ya = near[:, 2] + bb.ymin
    asm = np.column_stack([xa, ya, za])
    # the duct's air: inside its side profile and its plan outline (socket, trunk, channels; not the open slot or window)
    air = R.common(R.horn_in(-25.0, 25.0), [R.p22_air_xy(-80.0, -45.0)])
    solid = air.Solids()[0].wrapped if hasattr(air, "Solids") else air.wrapped
    rng = np.random.default_rng(1)
    pick = rng.choice(len(asm), size=min(6000, len(asm)), replace=False)
    inside = []
    for i in pick:
        c = BRepClass3d_SolidClassifier(solid, gp_Pnt(*asm[i]), 1e-6)
        if c.State() == TopAbs_IN:
            inside.append(i)
    inside = np.array(inside, int)
    print(f"P22 support samples within its footprint: {len(near)}; checked {len(pick)}; inside the duct's air: {len(inside)}")
    if len(inside):
        a = asm[inside]
        print("  inside-duct support, assembly bounds X %.1f..%.1f  Y %.1f..%.1f  Z %.1f..%.1f" %
              (a[:, 0].min(), a[:, 0].max(), a[:, 1].min(), a[:, 1].max(), a[:, 2].min(), a[:, 2].max()))
        print("  depth below the socket mouth (Z-49): up to %.1f mm" % (-49.0 - a[:, 2].min()))
        for lo, hi in ((-52, -49), (-56, -52), (-60, -56), (-64, -60), (-70, -64)):
            sel = a[(a[:, 2] >= lo) & (a[:, 2] < hi)]
            print(f"    Z {lo}..{hi}: {len(sel)} samples" + (f", X {sel[:, 0].min():.1f}..{sel[:, 0].max():.1f}, Y {sel[:, 1].min():.1f}..{sel[:, 1].max():.1f}" if len(sel) else ""))
    np.save(FILES / "p22_support_asm.npy", asm[pick])


if __name__ == "__main__":
    main()
