"""Where does the cooling air pass the nozzle tip: at the fresh bead, in front of it, behind it, or above it?

Usage: python cfd_tip_approach_r43.py <case> <out.png> [title]
       python cfd_tip_approach_r43.py --compare <out.png> <label=case> ...   (after the single-case run of each)
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
- Aim line: where each outlet points, before its air bends or collides. A straight line from the mean of the
  outlet's equal-flux seeds along the mean of their initial directions (first 0.5 mm), taken where it passes the
  nozzle axis: its fore/aft (or sideways) miss and its height above the print. A negative height means the line
  meets the print first; the distance from the axis where it does is also given.
- Aimed below the tip: the share of each outlet's streamlines whose own initial-direction line passes the nozzle
  axis below the tip's height, or meets the print first. Arrival: inward flux through vertical cylinders of radius
  3 and 5 mm around the nozzle axis, by height band (below the tip, tip to 1 mm, nozzle cone to 3.6 mm, above).
- Hot nozzle, cold bead: area-weighted mean air speed 0.4 mm off the CFD's wall faces of the exposed nozzle (below
  the sock, within 4 mm of the axis; tip to 1 mm and 1 mm to the sock) and of the sock and heater block (Z-75.45 to
  -71, |X| <= 7.3, Y 17.5-29.5). Convective cooling grows with this speed; the bead's own speed is the print-level
  ring mean of cfd_nozzle_focus_r43.py.
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


def aim_line(case):
    """Each outlet's mean aim line (see the definitions) where it passes the nozzle axis."""
    pts, offsets, label = F.streamlines(case)
    origin, dirs = F.initial_rays(pts, offsets)
    out = {}
    for i, key in enumerate(F.KEYS):
        o, d = origin[label == i].mean(0), dirs[label == i].mean(0)
        d /= np.linalg.norm(d)
        t = -(o[0] * d[0] + (o[1] - NY) * d[1]) / (d[0] ** 2 + d[1] ** 2)
        p = o + t * d
        h = float(p[2] - BED_Z)
        land = None
        if h < 0:
            q = o + (BED_Z - o[2]) / d[2] * d
            land = float(np.hypot(q[0], q[1] - NY))
        out[key] = {"from_mm": o.tolist(), "direction": d.tolist(), "at_axis_mm": p.tolist(),
                    "front_mm": float(p[1] - NY), "right_mm": float(p[0]), "above_print_mm": h,
                    "meets_print_first_at_r_mm": land}
    side = {k: (out["left"][k] + out["right"][k]) / 2 for k in ("front_mm", "above_print_mm")}
    out["side_jets_mean"] = side
    return out


def below_tip(case, report, factor, g):
    """Aimed below the tip, per outlet, and arrival through cylinders around the nozzle (see the definitions)."""
    pts, offsets, label = F.streamlines(case)
    o, d = F.initial_rays(pts, offsets)
    t = -(o[:, 0] * d[:, 0] + (o[:, 1] - NY) * d[:, 1]) / (d[:, 0] ** 2 + d[:, 1] ** 2)
    below = o[:, 2] + t * d[:, 2] - BED_Z < TIP_H
    aim, total, low = {}, 0.0, 0.0
    for i, key in enumerate(F.KEYS):
        lpm = report["outlets"][key]["lpm"] * factor
        aim[key] = {"lpm": lpm, "aimed_below_tip_pct": 100 * float(below[label == i].mean())}
        total, low = total + lpm, low + lpm * float(below[label == i].mean())
    aim["all"] = {"lpm": total, "aimed_below_tip_pct": 100 * low / total}
    bands = (("below the tip", 0.0, TIP_H), ("tip to 1 mm", TIP_H, 1.0), ("nozzle cone, 1-3.6 mm", 1.0, BLOCK_H),
             ("above 3.6 mm", BLOCK_H, 8.0))
    arrival = {}
    for r in (3.0, 5.0):
        h = np.arange(.01, 8.0, .02)
        a = np.linspace(0, 2 * np.pi, 180, endpoint=False)
        H, A = np.meshgrid(h, a, indexing="ij")
        ok, u = F.probe(g, np.column_stack((r * np.cos(A.ravel()), NY + r * np.sin(A.ravel()), BED_Z + H.ravel())))
        inward = np.where(ok, -(u[:, 0] * np.cos(A.ravel()) + u[:, 1] * np.sin(A.ravel())), 0.0) * factor
        q = np.clip(inward, 0, None) * (r * 2 * np.pi / len(a)) * .02 * 1e-6 * 60000
        lpm = {n: float(q[(H.ravel() >= lo) & (H.ravel() < hi)].sum()) for n, lo, hi in bands}
        arrival[f"r {r:.0f} mm"] = {"inflow_lpm": sum(lpm.values()), "bands_lpm": lpm}
    return {"aimed": aim, "arrival": arrival}


def hot_walls(case, g, factor, off=.4):
    """Mean air speed next to the hot parts (see the definitions)."""
    poly = F.hotend_walls(case)
    pts = vtk_to_numpy(poly.GetPoints().GetData()).astype(float)
    cells = vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    a, b, c = pts[cells[:, 0]], pts[cells[:, 1]], pts[cells[:, 2]]
    cen = (a + b + c) / 3
    n = np.cross(b - a, c - a)
    area = np.linalg.norm(n, axis=1) / 2
    n /= np.maximum(np.linalg.norm(n, axis=1), 1e-12)[:, None]
    ok_m, u_m = F.probe(g, cen - off * n)
    ok_p, u_p = F.probe(g, cen + off * n)
    speed = np.linalg.norm(np.where(ok_m[:, None], u_m, u_p), axis=1) * factor
    ok = ok_m | ok_p
    r = np.hypot(cen[:, 0], cen[:, 1] - NY)
    h = cen[:, 2] - BED_Z
    groups = {"nozzle tip to 1 mm": ok & (cen[:, 2] < -75.45) & (r < 4.0) & (h <= 1.0) & (h > TIP_H - .05),
              "nozzle 1 mm to the sock": ok & (cen[:, 2] < -75.45) & (r < 4.0) & (h > 1.0),
              "sock and heater block": ok & (cen[:, 2] >= -75.45) & (cen[:, 2] <= -71.0) & (np.abs(cen[:, 0]) <= 7.3)
                                       & (cen[:, 1] >= 17.5) & (cen[:, 1] <= 29.5)}
    return {k: {"mean_ms": float(np.average(speed[m], weights=area[m])), "area_mm2": float(area[m].sum())}
            for k, m in groups.items() if m.any()}


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


def compare(out_png, specs):
    """Variants side by side: where the air passes the bead, in the side and front sections and as a matrix, with a
    summary row per case. Run the single-case analysis (and cfd_nozzle_focus_r43.py) on each case first."""
    cases = []
    for spec in specs:
        label, case = spec.split("=", 1)
        report = json.loads((C.results_dir(case) / "outlet_balance_mean.json").read_text())
        factor = report["operating_point_1m_hose"]["lpm"] / 180
        res = json.loads((C.results_dir(case) / "tip_approach.json").read_text())
        if "aim_line" not in res:
            res["aim_line"] = aim_line(case)
        _, sections = F.load_cached(case)
        cases.append((label, report, res, closest(case, report, factor), sections))
    n = len(cases)
    fig = plt.figure(figsize=(10 * n, 19), dpi=100)
    fig.patch.set_facecolor(R.BG)
    grid = fig.add_gridspec(4, n, height_ratios=[.8, .8, 1, .42], hspace=.3, wspace=.18)
    lines = []
    for i, (label, report, res, c, sections) in enumerate(cases):
        a = res["closest_approach"]
        p = c["point"]
        for row, (sec, axis, title_, xlabel) in enumerate((
                (sections["side"], 1, "side section (X 0)", "Y (mm), toward the front"),
                (sections["front"], 0, "front section (Y 22.7)", "X (mm)"))):
            ax = fig.add_subplot(grid[row, i])
            centre = NY if axis == 1 else 0.0
            F.draw_section(ax, sec, f"{label}: {title_}", xlabel, [], (centre - F.BEAD_R, centre + F.BEAD_R))
            slab = (np.abs(p[:, 0]) <= 2.5) if axis == 1 else (np.abs(p[:, 1] - NY) <= 2.5)
            for k, key in enumerate(F.KEYS):
                m = (c["label"] == k) & slab
                ax.scatter(p[m, axis], p[m, 2], s=7, color=R.COLORS[key], edgecolor="k", lw=.2, alpha=.85, zorder=10)
                s = a[key]
                ax.scatter((s["front_mm"] + NY) if axis == 1 else s["right_mm"], s["above_print_mm"] + BED_Z, s=280,
                           marker="o", color=R.COLORS[key], edgecolor="w", lw=2.2, zorder=12)
                if axis == 0 and key == "centre":
                    continue
                al = res["aim_line"][key]
                (x0, z0), (x1, z1) = (al["from_mm"][axis], al["from_mm"][2]), (al["at_axis_mm"][axis], al["at_axis_mm"][2])
                ax.plot([x0, x1], [z0, z1], color=R.COLORS[key], lw=2.4, ls="--", zorder=13)
                ax.scatter([x1], [z1], s=150, marker="X", color=R.COLORS[key], edgecolor="w", lw=1.2, zorder=14)
            ax.set_xlim(centre - 11, centre + 11)
            ax.set_ylim(BED_Z - .7, BED_Z + 7.2)
        ax = fig.add_subplot(grid[2, i])
        R.style(ax, f"{label}: where the air passes the bead (L/min)")
        M = np.array([[a["cells"][f"{lv}/{pl_}"]["lpm"] for pl_, _ in PLACES] for lv, _ in LEVELS])
        ax.imshow(M, cmap="magma", vmin=0, vmax=70, aspect="auto")
        for r_, (lv, _) in enumerate(LEVELS):
            for k_, (pl_, _) in enumerate(PLACES):
                cell = a["cells"][f"{lv}/{pl_}"]
                text = f"{cell['lpm']:.0f}"
                if cell["mean_speed_ms"] is not None and cell["lpm"] >= 1:
                    text += f"\n{cell['mean_speed_ms']:.0f} m/s"
                ax.text(k_, r_, text, ha="center", va="center", fontsize=12, fontweight="bold",
                        color="#0f1d2e" if M[r_, k_] > 38 else R.TEXT)
        ax.set_xticks(range(len(PLACES)), [t for _, t in PLACES], color=R.MUTED, fontsize=10)
        ax.set_yticks(range(len(LEVELS)), [t for _, t in LEVELS], color=R.MUTED, fontsize=10)
        ax.add_patch(plt.Rectangle((.5, 1.5), 1, 1, fill=False, ec="#ffd43b", lw=3))
        side = {k: (a["left"][k] * a["left"]["lpm"] + a["right"][k] * a["right"]["lpm"]) / (a["left"]["lpm"] + a["right"]["lpm"])
                for k in ("front_mm", "above_print_mm")}
        bead = res["print_level"]["sectors_ms"]["r 0.6-2.0 mm"]
        surf = res["nozzle_surface"]["band_means_ms"]["tip to 1 mm"]["all"]
        aim = res["aim_line"]["side_jets_mean"]
        lines.append([label, f"{report['operating_point_1m_hose']['lpm']:.0f}",
                      f"{aim['front_mm']:+.1f} / {aim['above_print_mm']:+.1f}",
                      f"{side['front_mm']:+.1f} / {side['above_print_mm']:.1f}",
                      f"{a['centre']['front_mm']:+.1f} / {a['centre']['above_print_mm']:.1f}",
                      f"{a['cells']['print/at']['lpm']:.1f}",
                      f"{sum(a['cells'][f'print/{q}']['lpm'] for q, _ in PLACES):.0f}",
                      f"{sum(a['cells'][f'block/{q}']['lpm'] for q, _ in PLACES):.0f}",
                      "/".join(f"{bead[q]:.0f}" for q in ("behind", "left", "front", "right")), f"{surf:.0f}"])
    ax = fig.add_subplot(grid[3, :])
    ax.axis("off")
    head = ["case", "blower\nL/min", "side jets aim at\nthe axis: front / up", "side jets pass\nfront / up (mm)",
            "centre slot pass\nfront / up (mm)",
            "at the bead\nL/min", "print level\nL/min", "above 3.6 mm\nL/min", "within 2 mm\nB/L/F/R m/s",
            "nozzle surface\ntip-1 mm m/s"]
    table = ax.table(cellText=lines, colLabels=head, loc="center", cellLoc="center")
    table.auto_set_font_size(False)
    table.set_fontsize(13)
    table.scale(1, 2.6)
    for (r_, k_), cell in table.get_celld().items():
        cell.set_facecolor(R.PANEL if r_ else "#1d3550")
        cell.set_edgecolor(R.EDGE)
        cell.get_text().set_color(R.TEXT)
        if r_ == 0:
            cell.set_height(cell.get_height() * 1.7)
    fig.suptitle("Where the air passes the nozzle tip: " + " vs ".join(c[0] for c in cases) + ". Iteration-mean CFD, "
                 "each design at its own blower point. Dots: closest approach to the bead of air passing within 2.5 mm "
                 "of the section; rings: each outlet's mean; dashed lines: each outlet's mean aim, X where it passes "
                 "the nozzle axis. Airflow, not temperature.", color=R.TEXT, fontsize=15,
                 wrap=True)
    fig.savefig(out_png, facecolor=R.BG, bbox_inches="tight", pad_inches=.4)
    print(out_png)


def main():
    if sys.argv[1] == "--compare":
        compare(sys.argv[2], sys.argv[3:])
        return
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
    low = below_tip(case, report, factor, g)
    hot = hot_walls(case, g, factor)
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
              "heater_block_skirt_above_print_mm": BLOCK_H, "closest_approach": summary, "aim_line": aim_line(case),
              "below_tip": low, "hot_nozzle_cold_bead": hot,
              "nozzle_surface": surface,
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
