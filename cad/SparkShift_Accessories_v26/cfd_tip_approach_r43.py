"""Where does the cooling air pass the nozzle tip: at the fresh bead, in front of it, behind it, or above it?

Usage: python cfd_tip_approach_r43.py <case> <out.png> [title]
Needs cfd_outlet_balance_r43.py <case> --mean (flux-weighted streamlines, 600 per outlet) and
cfd_nozzle_focus_r43.py <case> (saved front and side sections). Writes results/<case>/tip_approach.json. Air values
are at the case's blower operating point (WS7040, 1 m hose).

- Closest approach: each streamline carries an equal share of its outlet's flow. Its point nearest the bead point
  (on the nozzle axis, midway between the tip and the print) says where that air passes the bead. Places: within
  2 mm of the nozzle axis, otherwise in front (+Y), behind, or beside it; at print level (up to 1 mm above the
  print), from 1 mm up to the bottom of the heater block's skirt (3.6 mm), or higher.
- Nozzle surface: mean speed 0.2-0.6 mm off the nozzle cone, in each quarter around it, from the print up to the
  heater block. The CFD mesh closes the 0.2 mm gap under the tip, as the bead does when printing.
- Print level: mean speed 0.3 mm above the print around the nozzle.
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

import cfd_cpap_r41 as C
import cfd_outlet_balance_r43 as B
import cfd_nozzle_focus_r43 as F
import render_outlet_balance_r43 as R

NY, BED_Z = C.NOZZLE_Y, F.BED_Z
TIP_H = C.NOZZLE_TIP_Z - BED_Z
BEAD = np.array([0.0, NY, BED_Z + TIP_H / 2])
BLOCK_H = -75.5 - BED_Z                    # bottom of the Bambu heater block's skirt, height above the print
LEVELS = (("block", "above 3.6 mm\n(heater-block\nskirt and up)"), ("cone", "1-3.6 mm up\n(nozzle cone)"),
          ("print", "print level\n(<= 1 mm up)"))
PLACES = (("behind", "behind"), ("at", "at the nozzle\n(<= 2 mm)"), ("front", "in front"),
          ("beside", "beside\n(left or right)"))
QUARTER_COLORS = {"behind": "#63e6be", "left": "#ff9f43", "front": "#ffd43b", "right": "#4dabf7", "all": "#ffffff"}


def streamlines(case):
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(str(C.results_dir(case) / "outlet_streamlines_mean.vtp"))
    reader.Update()
    poly = reader.GetOutput()
    cells = poly.GetLines()
    offsets = vtk_to_numpy(cells.GetOffsetsArray()).astype(np.int64)
    conn = vtk_to_numpy(cells.GetConnectivityArray())
    pts = vtk_to_numpy(poly.GetPoints().GetData()).astype(float)[conn]
    u = vtk_to_numpy(poly.GetPointData().GetArray("U")).astype(float)[conn]
    return pts, u, offsets, vtk_to_numpy(poly.GetCellData().GetArray("outlet"))


def closest(case, report, factor):
    pts, u, offsets, label = streamlines(case)
    d = np.linalg.norm(pts - BEAD, axis=1)
    idx = np.array([s + int(np.argmin(d[s:e])) for s, e in zip(offsets[:-1], offsets[1:])])
    p = pts[idx]
    weight = np.empty(len(p))
    for i, key in enumerate(F.KEYS):
        mine = label == i
        weight[mine] = report["outlets"][key]["lpm"] * factor / mine.sum()
    dx, dy, h = p[:, 0], p[:, 1] - NY, p[:, 2] - BED_Z
    angle = np.degrees(np.arctan2(dy, dx)) % 360
    place = np.where(np.hypot(dx, dy) <= 2.0, "at",
                     np.where((angle >= 45) & (angle < 135), "front",
                              np.where((angle >= 225) & (angle < 315), "behind", "beside")))
    level = np.where(h <= 1.0, "print", np.where(h <= BLOCK_H, "cone", "block"))
    return {"point": p, "speed": np.linalg.norm(u[idx], axis=1) * factor, "distance": d[idx], "weight": weight,
            "label": label, "place": place, "level": level}


def summarise(c):
    w, total = c["weight"], c["weight"].sum()
    cells = {}
    for lv, _ in LEVELS:
        for pl, _ in PLACES:
            m = (c["level"] == lv) & (c["place"] == pl)
            q = float(w[m].sum())
            cells[f"{lv}/{pl}"] = {"lpm": q, "pct": 100 * q / total,
                                   "mean_speed_ms": float(np.average(c["speed"][m], weights=w[m])) if m.any() else None}
    p = c["point"]

    def centroid(m):
        order = np.argsort(c["distance"][m])
        cum = np.cumsum(w[m][order])
        return {"front_mm": float(np.average(p[m, 1] - NY, weights=w[m])),
                "right_mm": float(np.average(p[m, 0], weights=w[m])),
                "above_print_mm": float(np.average(p[m, 2] - BED_Z, weights=w[m])),
                "from_axis_mm": float(np.average(np.hypot(p[m, 0], p[m, 1] - NY), weights=w[m])),
                "median_distance_to_bead_mm": float(c["distance"][m][order][np.searchsorted(cum, cum[-1] / 2)]),
                "lpm": float(w[m].sum())}
    out = {"cells": cells, "all": centroid(np.ones(len(w), bool))}
    out["cells_by_outlet"] = {}
    for i, key in enumerate(F.KEYS):
        out[key] = centroid(c["label"] == i)
        mine = c["label"] == i
        out["cells_by_outlet"][key] = {
            f"{lv}/{pl}": float(w[mine & (c["level"] == lv) & (c["place"] == pl)].sum())
            for lv, _ in LEVELS for pl, _ in PLACES}
    near = c["distance"] <= 2.0
    out["within_2mm_of_bead_point"] = {"lpm": float(w[near].sum()), "pct": 100 * float(w[near].sum()) / total,
                                       "mean_speed_ms": float(np.average(c["speed"][near], weights=w[near]))}
    return out


def surface_profile(g, factor, h_max=5.2):
    """Mean speed 0.2-0.6 mm off the nozzle's surface: rays out from the nozzle axis at each height, sampled just
    beyond the first fluid point, then averaged over each quarter around the nozzle."""
    hs = np.arange(.05, h_max + 1e-9, .05)
    phis = np.arange(-180, 180, 5.0)
    rs = np.arange(0, 8.0, .04)
    H, P, Rr = np.meshgrid(hs, phis, rs, indexing="ij")
    a = np.radians(P)
    ok, u = F.probe(g, np.column_stack(((Rr * np.sin(a)).ravel(), (NY + Rr * np.cos(a)).ravel(), (BED_Z + H).ravel())))
    ok = ok.reshape(H.shape)
    speed = np.where(ok, np.linalg.norm(u, axis=1).reshape(H.shape) * factor, np.nan)
    first = np.argmax(ok, axis=2)
    band = [first + k for k in range(int(round(.2 / .04)), int(round(.6 / .04)) + 1)]
    ii, jj = np.meshgrid(np.arange(len(hs)), np.arange(len(phis)), indexing="ij")
    samples = np.stack([np.where(ok.any(axis=2), speed[ii, jj, np.minimum(k, len(rs) - 1)], np.nan) for k in band])
    ring = np.nanmean(samples, axis=0)
    quarters = {"front": np.abs(phis) <= 45, "right": (phis > 45) & (phis < 135), "behind": np.abs(phis) >= 135,
                "left": (phis < -45) & (phis > -135)}
    with np.errstate(all="ignore"):
        profiles = {k: np.nanmean(ring[:, m], axis=1) for k, m in quarters.items()}
        profiles["all"] = np.nanmean(ring, axis=1)
    return {"h_mm": hs, "profiles": profiles, "surface_r_mm": np.nanmean(np.where(ok.any(axis=2), rs[first], np.nan), 1)}


def plan(g, factor, h=.3, half=8.0, step=.05):
    xs = np.arange(-half, half + 1e-9, step)
    X, Y = np.meshgrid(xs, NY + xs)
    ok, u = F.probe(g, np.column_stack((X.ravel(), Y.ravel(), np.full(X.size, BED_Z + h))))
    speed = np.where(ok, np.linalg.norm(u, axis=1) * factor, np.nan).reshape(X.shape)
    rho, angle = np.hypot(X, Y - NY), np.degrees(np.arctan2(Y - NY, X)) % 360
    sectors = {}
    for lo, hi in ((.6, 2.0), (2.0, 5.0)):
        ring = (rho >= lo) & (rho <= hi) & np.isfinite(speed)
        sectors[f"r {lo}-{hi} mm"] = {
            name: float(np.mean(speed[ring & ((angle - centre + 45) % 360 < 90)]))
            for name, centre in (("right", 0), ("front", 90), ("left", 180), ("behind", 270))}
    disc = (rho <= 5.0) & np.isfinite(speed)
    peak = np.unravel_index(np.nanargmax(np.where(disc, speed, -1)), speed.shape)
    return {"x": xs, "y": NY + xs, "speed": speed, "sectors_ms": sectors,
            "peak_r5": {"right_mm": float(X[peak]), "front_mm": float(Y[peak] - NY), "ms": float(speed[peak])}}


def main():
    case, out_png = sys.argv[1], sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "current Bambu set"
    report = json.loads((C.results_dir(case) / "outlet_balance_mean.json").read_text())
    op = report["operating_point_1m_hose"]
    factor = op["lpm"] / 180
    c = closest(case, report, factor)
    summary = summarise(c)
    g = B.load(case, True)
    surf = surface_profile(g, factor)
    pl = plan(g, factor)
    del g
    _, sections = F.load_cached(case)
    hs, prof = surf["h_mm"], surf["profiles"]
    bands = {"tip to 1 mm": hs <= 1.0, "1-3.6 mm": (hs > 1.0) & (hs <= BLOCK_H), "above 3.6 mm": hs > BLOCK_H}
    with np.errstate(all="ignore"):
        surface = {"h_mm": hs.tolist(), "profiles_ms": {k: v.tolist() for k, v in prof.items()},
                   "cone_radius_mm": surf["surface_r_mm"].tolist(),
                   "band_means_ms": {b: {k: float(np.nanmean(v[m])) for k, v in prof.items()} for b, m in bands.items()},
                   "fastest_height_mm": float(hs[np.nanargmax(prof["all"])])}
    result = {"case": case, "operating_point_lpm": op["lpm"], "bead_point_mm": BEAD.tolist(),
              "heater_block_skirt_above_print_mm": BLOCK_H, "closest_approach": summary, "nozzle_surface": surface,
              "print_level": {k: v for k, v in pl.items() if k not in ("x", "y", "speed")},
              "definitions": __doc__.split("\n\n", 2)[2].strip()}
    (C.results_dir(case) / "tip_approach.json").write_text(json.dumps(result, indent=1) + "\n")

    fig = plt.figure(figsize=(24, 17), dpi=100)
    fig.patch.set_facecolor(R.BG)
    grid = fig.add_gridspec(2, 6, height_ratios=[1, 1.1], hspace=.25, wspace=.6)
    p = c["point"]
    for col, (sec, axis, title_, xlabel) in enumerate((
            (sections["side"], 1, "Side section through the nozzle (X 0)", "Y (mm), toward the front"),
            (sections["front"], 0, "Front section through the nozzle (Y 22.7)", "X (mm)"))):
        ax = fig.add_subplot(grid[0, 3 * col:3 * col + 3])
        centre = NY if axis == 1 else 0.0
        im = F.draw_section(ax, sec, title_, xlabel, [], (centre - F.BEAD_R, centre + F.BEAD_R))
        slab = (np.abs(p[:, 0]) <= 2.5) if axis == 1 else (np.abs(p[:, 1] - NY) <= 2.5)
        for i, key in enumerate(F.KEYS):
            m = (c["label"] == i) & slab
            ax.scatter(p[m, axis], p[m, 2], s=8, color=R.COLORS[key], edgecolor="k", lw=.2, alpha=.85, zorder=10,
                       label=R.NAMES[key])
            s = summary[key]
            ax.scatter((s["front_mm"] + NY) if axis == 1 else s["right_mm"], s["above_print_mm"] + BED_Z, s=300,
                       marker="o", color=R.COLORS[key], edgecolor="w", lw=2.2, zorder=12)
        ax.axhline(BED_Z + BLOCK_H, color="#c9d6e3", lw=.8, ls=":")
        ax.text(centre + 10.8, BED_Z + BLOCK_H + .1, "heater-block skirt", color=R.MUTED, ha="right", fontsize=9)
        ax.text(centre - 10.8, BED_Z + 6.9, "dots: where air passing within 2.5 mm of this plane comes closest to "
                "the bead\nlarge rings: each outlet's mean passing point (all its air)", color=R.TEXT, fontsize=9.5,
                va="top", zorder=14, bbox=dict(facecolor=R.BG, alpha=.75, edgecolor="none"))
        ax.set_xlim(centre - 11, centre + 11)
        ax.set_ylim(BED_Z - .7, BED_Z + 7.2)
        R.legend(ax, loc="upper right", fontsize=9, markerscale=1.8)
    bar = fig.colorbar(im, ax=ax, shrink=.75, pad=.02)
    bar.set_label("m/s", color=R.MUTED)
    bar.ax.tick_params(colors=R.MUTED)

    ax = fig.add_subplot(grid[1, :2])
    R.style(ax, "Where the air passes the bead (L/min, all outlets)")
    M = np.array([[summary["cells"][f"{lv}/{pl_}"]["lpm"] for pl_, _ in PLACES] for lv, _ in LEVELS])
    ax.imshow(M, cmap="magma", vmin=0, vmax=M.max() * 1.15, aspect="auto")
    for r_, (lv, _) in enumerate(LEVELS):
        for k_, (pl_, _) in enumerate(PLACES):
            cell = summary["cells"][f"{lv}/{pl_}"]
            text = f"{cell['lpm']:.0f}\n({cell['pct']:.0f}%)"
            if cell["mean_speed_ms"] is not None and cell["lpm"] >= 1:
                text += f"\n{cell['mean_speed_ms']:.0f} m/s"
            ax.text(k_, r_, text, ha="center", va="center", fontsize=12, fontweight="bold",
                    color="#0f1d2e" if M[r_, k_] > .55 * M.max() else R.TEXT)
    ax.set_xticks(range(len(PLACES)), [t for _, t in PLACES], color=R.MUTED, fontsize=10)
    ax.set_yticks(range(len(LEVELS)), [t for _, t in LEVELS], color=R.MUTED, fontsize=10)
    ax.add_patch(plt.Rectangle((.5, 1.5), 1, 1, fill=False, ec="#ffd43b", lw=3))
    ax.set_xlabel("closest approach of each parcel of air to the bead; mean speed there", color=R.MUTED)

    ax = fig.add_subplot(grid[1, 2:4])
    R.style(ax, "Speed 0.2-0.6 mm off the nozzle cone, by side (m/s)")
    ax.axhspan(0, 1.0, color="#ffd43b", alpha=.1)
    for key in ("behind", "left", "front", "right", "all"):
        ax.plot(prof[key], hs, color=QUARTER_COLORS[key], lw=3.2 if key == "all" else 1.8,
                label="mean all around" if key == "all" else key)
    ax.axhline(TIP_H, color="w", lw=1, ls="--")
    ax.text(1, TIP_H + .04, "nozzle tip", color="w", fontsize=10, va="bottom")
    ax.axhline(BLOCK_H, color="#c9d6e3", lw=1, ls=":")
    ax.text(1, BLOCK_H + .04, "heater-block skirt", color=R.MUTED, fontsize=10, va="bottom")
    b = surface["band_means_ms"]
    ax.set_xlim(0, 1.1 * np.nanmax([np.nanmax(v) for v in prof.values()]))
    ax.set_ylim(0, hs[-1])
    ax.set_xlabel("m/s. Mean all around: tip to 1 mm {:.0f}; 1-3.6 mm {:.0f}; above 3.6 mm {:.0f}".format(
        b["tip to 1 mm"]["all"], b["1-3.6 mm"]["all"], b["above 3.6 mm"]["all"]), color=R.MUTED)
    ax.set_ylabel("height above the print (mm)", color=R.MUTED)
    R.legend(ax, loc="upper right", fontsize=9)

    ax = fig.add_subplot(grid[1, 4:])
    R.style(ax, "Speed 0.3 mm above the print (m/s)")
    ax.imshow(pl["speed"], origin="lower", cmap="turbo", vmin=0, vmax=60,
              extent=(pl["x"][0], pl["x"][-1], pl["y"][0], pl["y"][-1]), interpolation="bilinear")
    ax.add_patch(plt.Circle((0, NY), .6, color="#b8c2cc"))
    ax.add_patch(plt.Circle((0, NY), F.BEAD_R, fill=False, ec="#ffd43b", lw=2, ls="--"))
    ax.add_patch(plt.Circle((0, NY), 5, fill=False, ec="w", lw=.8, ls=":"))
    bead = pl["sectors_ms"]["r 0.6-2.0 mm"]
    outer = pl["sectors_ms"]["r 2.0-5.0 mm"]
    for name, (tx, ty) in {"front": (0, 6.6), "behind": (0, -6.6), "left": (-6.4, 0), "right": (6.4, 0)}.items():
        ax.text(tx, NY + ty, f"{name}\n{bead[name]:.0f} | {outer[name]:.0f}", color="w", ha="center", va="center",
                fontsize=11, fontweight="bold")
    pk = pl["peak_r5"]
    ax.scatter(pk["right_mm"], NY + pk["front_mm"], marker="x", s=120, color="w", lw=2.5, zorder=6)
    ax.set_xlabel("sector means: within 2 mm | 2-5 mm. x = fastest point within 5 mm", color=R.MUTED)
    ax.set_ylabel("Y (mm), toward the front", color=R.MUTED)
    ax.set_xlim(pl["x"][0], pl["x"][-1])
    ax.set_ylim(pl["y"][0], pl["y"][-1])
    ax.set_aspect("equal")

    side = {k: (summary["left"][k] * summary["left"]["lpm"] + summary["right"][k] * summary["right"]["lpm"])
            / (summary["left"]["lpm"] + summary["right"]["lpm"]) for k in ("front_mm", "above_print_mm")}
    cen = summary["centre"]
    at = summary["cells"]["print/at"]
    fb = lambda v: f"{abs(v):.1f} mm {'in front of' if v >= 0 else 'behind'}"
    fig.suptitle(f"Where does the air pass the nozzle tip? {title}. Iteration-mean CFD at the {op['lpm']:.0f} L/min "
                 f"blower point.\nSide jets: on average {fb(side['front_mm'])} the nozzle and "
                 f"{side['above_print_mm']:.1f} mm above the print. Centre slot: {fb(cen['front_mm'])} it, "
                 f"{cen['above_print_mm']:.1f} mm up. At the bead itself: {at['lpm']:.0f} L/min ({at['pct']:.0f}%). "
                 "Airflow, not temperature.", color=R.TEXT, fontsize=15)
    fig.savefig(out_png, facecolor=R.BG, bbox_inches="tight", pad_inches=.4)
    print(json.dumps({"closest_approach": {k: v for k, v in summary.items() if k not in ("cells", "cells_by_outlet")},
                      "side_jets_mean": side,
                      "cells": {k: {kk: (round(vv, 1) if isinstance(vv, float) else vv) for kk, vv in v.items()}
                                for k, v in summary["cells"].items()},
                      "nozzle_surface": {k: v for k, v in surface.items() if k in ("band_means_ms", "fastest_height_mm")},
                      "print_level": result["print_level"]}, indent=1, default=float))
    print(out_png)


if __name__ == "__main__":
    main()
