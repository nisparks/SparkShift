"""Design diagnostics on the R41 CFD result (session scratch): where the 5 kPa goes and why."""
import json
import sys
from pathlib import Path

HERE = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(HERE))
import os  # noqa: E402
os.chdir(HERE)

import numpy as np  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import cfd_cpap_r41 as C  # noqa: E402
import cfd_cpap_r41_post as P  # noqa: E402
import render_cfd_cpap_r41 as RR  # noqa: E402

OUT = Path(__file__).parent / "images"


def box_fluxes(g, b):
    """Net outflow (L/min) through each face of box b = (x0, x1, y0, y1, z0, z1)."""
    out = {}
    faces = {"x-": ("x", b[0], (-1, 0, 0), (b[0] - 0.5, b[0] + 0.5, b[2], b[3], b[4], b[5])),
             "x+": ("x", b[1], (1, 0, 0), (b[1] - 0.5, b[1] + 0.5, b[2], b[3], b[4], b[5])),
             "y- (back)": ("y", b[2], (0, -1, 0), (b[0], b[1], b[2] - 0.5, b[2] + 0.5, b[4], b[5])),
             "y+ (front)": ("y", b[3], (0, 1, 0), (b[0], b[1], b[3] - 0.5, b[3] + 0.5, b[4], b[5])),
             "z- (down)": ("z", b[4], (0, 0, -1), (b[0], b[1], b[2], b[3], b[4] - 0.5, b[4] + 0.5)),
             "z+ (up)": ("z", b[5], (0, 0, 1), (b[0], b[1], b[2], b[3], b[5] - 0.5, b[5] + 0.5))}
    for k, (axis, at, n, clip) in faces.items():
        sl = P.clip_box(P.plane_slice(g, axis, at), clip)
        if sl.GetNumberOfCells() == 0:
            out[k] = 0.0
            continue
        _, _, area = P.triangles(sl)
        out[k] = round(float(((P.cell_array(sl, "U") @ np.array(n)) * area).sum()) * 1e-6 * 60000, 2)
    return out


def reversed_fraction(g, axis, at, clip, normal):
    sl = P.clip_box(P.plane_slice(g, axis, at), clip)
    _, _, area = P.triangles(sl)
    un = P.cell_array(sl, "U") @ np.array(normal)
    return round(float(area[un < 0].sum() / area.sum()), 3), round(float(area.sum()), 1)


def main(name="r41_bambu", lpm=180):
    s = RR.stage(name, lpm)
    g = P.internal(name, s["end"])
    rep = {"case": name, "lpm": s["lpm"]}
    rep["nozzle_box_fluxes_lpm"] = box_fluxes(g, (-10.15, 10.15, 14.0, 29.5, -79.0, -72.0))
    rep["reversed_area_fraction"] = {
        f"side channels at Y{y}": reversed_fraction(g, "y", y, (-23, 23, y - 1, y + 1, -73, -55), (0, 1, 0))
        for y in (-30.0, -25.0, -20.0, -15.0, -5.0)}
    # jet exit profile: static pressure and speed over the passage at |X| 10.3 (right jet)
    sl = P.clip_box(P.cut(g, (10.3, 0, 0), (1, 0, 0)), (9.3, 11.3) + C.JET_WINDOW)
    pts, tris, area = P.triangles(sl)
    u, p = P.cell_array(sl, "U"), P.cell_array(sl, "p") * C.RHO
    rep["right_jet_exit"] = {"static_pa_mean": round(float((p * area).sum() / area.sum())),
                             "static_pa_range": [round(float(p.min())), round(float(p.max()))],
                             "speed_range_ms": [round(float(np.linalg.norm(u, axis=1).min()), 1),
                                                round(float(np.linalg.norm(u, axis=1).max()), 1)],
                             "uy_mean_ms": round(float((u[:, 1] * area).sum() / area.sum()), 2),
                             "uz_mean_ms": round(float((u[:, 2] * area).sum() / area.sum()), 2),
                             "ux_mean_ms": round(float((u[:, 0] * area).sum() / area.sum()), 2)}
    print(json.dumps(rep, indent=1))
    fig, axs = plt.subplots(3, 2, figsize=(16, 16))
    RR.section(axs[0, 0], g, "y", C.NOZZLE_Y, RR.W_XZ, field="p", vmax=None, arrows=False, cmap="coolwarm",
               title="Static pressure across the nozzle (Y 22.7)")
    RR.section(axs[0, 1], g, "z", -75.1, RR.W_XY, field="p", vmax=None, arrows=False, cmap="coolwarm",
               title="Static pressure at jet mid-height (Z -75.1)")
    RR.section(axs[1, 0], g, "x", 10.3, (12, 32, -80, -66), title="Right jet exit plane (X 10.3): speed")
    RR.section(axs[1, 1], g, "x", 10.3, (12, 32, -80, -66), field="p", vmax=None, arrows=False, cmap="coolwarm",
               title="Right jet exit plane (X 10.3): static pressure")
    RR.section(axs[2, 0], g, "x", 13.0, (8, 32, -80, -60), title="Inside the plenum, X 13: speed")
    RR.section(axs[2, 1], g, "z", -66.0, (-24, 24, -44, 30), vmax=40, title="Side channels from above (Z -66)")
    fig.tight_layout()
    fig.savefig(OUT / f"diag_{name}_{lpm}.png", dpi=90)
    plt.close(fig)


if __name__ == "__main__":
    main(*(sys.argv[1:2] or ["r41_bambu"]))
