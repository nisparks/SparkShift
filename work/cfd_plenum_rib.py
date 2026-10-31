"""The plenum round the cable boss's nose, revision 43 before (r43v1_bambu_bed) and after the review (r43_bambu_bed),
at 180 L/min: air speed with in-plane streamlines, and the turbulent velocity fluctuation sqrt(2k/3), in horizontal
planes through the rib (session scratch; image for the user)."""
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import os  # noqa: E402

os.chdir(CAD)
import matplotlib  # noqa: E402
import numpy as np  # noqa: E402
import vtk  # noqa: E402
from vtk.util.numpy_support import vtk_to_numpy  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import cfd_cpap_r41_post as P  # noqa: E402

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\cfd_plenum_rib.png")
CASES = (("r43v1_bambu_bed", "Before the review (no rib)"), ("r43_bambu_bed", "After the review (rib, flares)"))
ZS = (-58.0, -63.0)
XS, YS = np.arange(-20.0, 20.01, 0.2), np.arange(-45.0, -22.99, 0.2)


def sample(g, z):
    gx, gy = np.meshgrid(XS, YS)
    pts = vtk.vtkPoints()
    for x, y in zip(gx.ravel(), gy.ravel()):
        pts.InsertNextPoint(x, y, z)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pr = vtk.vtkProbeFilter()
    pr.SetInputData(pd)
    pr.SetSourceData(g)
    pr.Update()
    o = pr.GetOutput().GetPointData()
    ok = vtk_to_numpy(o.GetArray("vtkValidPointMask")).astype(bool).reshape(gx.shape)
    u = vtk_to_numpy(o.GetArray("U")).reshape(gx.shape + (3,))
    k = vtk_to_numpy(o.GetArray("k")).reshape(gx.shape) if o.GetArray("k") is not None else np.zeros(gx.shape)
    return ok, u, k


fig, axes = plt.subplots(len(ZS) * 2, 2, figsize=(13, 6.2 * len(ZS) * 2 / 2 * 1.05))
stats = {}
for col, (name, label) in enumerate(CASES):
    g = P.internal(name, 1200)
    for i, z in enumerate(ZS):
        ok, u, k = sample(g, z)
        sp = np.where(ok, np.linalg.norm(u, axis=2), np.nan)
        tu = np.where(ok, np.sqrt(np.clip(2.0 * k / 3.0, 0, None)), np.nan)
        ax = axes[2 * i, col]
        im = ax.pcolormesh(XS, YS, sp, cmap="viridis", vmin=0, vmax=25, shading="auto")
        ux, uy = np.where(ok, u[..., 0], 0.0), np.where(ok, u[..., 1], 0.0)
        ax.streamplot(XS, YS, ux, uy, color="w", density=1.4, linewidth=0.5, arrowsize=0.6)
        ax.set_title(f"{label}: air speed at Z{z:g} (m/s)", fontsize=10)
        fig.colorbar(im, ax=ax, fraction=0.03)
        ax2 = axes[2 * i + 1, col]
        im2 = ax2.pcolormesh(XS, YS, tu, cmap="magma", vmin=0, vmax=4, shading="auto")
        ax2.set_title(f"{label}: turbulent fluctuation sqrt(2k/3) at Z{z:g} (m/s)", fontsize=10)
        fig.colorbar(im2, ax=ax2, fraction=0.03)
        m = ok & (np.abs(XS)[None, :] < 8.0) & (YS[:, None] < -36.0)
        stats[(name, z)] = (float(np.nanmean(sp[m])), float(np.nanmean(tu[m])), float(np.nanmax(tu[m])))
        for a in (ax, ax2):
            a.set_aspect("equal")
            a.set_xlim(XS[0], XS[-1])
            a.set_ylim(YS[0], YS[-1])
fig.suptitle("P22's plenum under the socket, 180 L/min, print surface case: behind the cable boss's nose (|X|<8, "
             "Y<-36)", fontsize=12)
fig.tight_layout(rect=(0, 0, 1, 0.97))
fig.savefig(OUT, dpi=70)
print(OUT)
for (name, z), (s, t, tm) in stats.items():
    print(f"{name} Z{z:g}: behind the nose mean speed {s:.2f} m/s, mean fluctuation {t:.3f} m/s, max {tm:.2f} m/s")
