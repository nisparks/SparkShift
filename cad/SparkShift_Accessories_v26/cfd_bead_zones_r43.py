"""The user's own-side target zones, the air arriving on the print, and where the cone-scrubbing air leaves.

Usage:
  python cfd_bead_zones_r43.py <case> [<case> ...]                 writes results/<case>/bead_zones.json
  python cfd_bead_zones_r43.py --paths <out.png> "label=case" ...  front sections with each side jet's real paths
  python cfd_bead_zones_r43.py --scrub-map <out.png> "label=case" ...  where the cone-scrubbing air leaves
Run cfd_outlet_balance_r43.py <case> --mean and cfd_nozzle_focus_r43.py <case> <png> first.

Definitions (iteration-mean field at each design's own blower point; airflow, not temperature):
- Target zones (user, 2026-10-31). The left jet's zone is the half-disc left of the nozzle axis (X < 0), the
  right jet's is the half to the right (X > 0), and the rear slot's is the half behind it (Y < 22.7). Each lies
  just below the nozzle tip: radius 2.5 mm and 0-0.4 mm below the tip, or radius 4 mm and 0-1 mm below. The CFD's
  print surface is 0.2 mm below the tip, so in the CFD each zone is the air layer between the tip and the print,
  and the two sizes differ only in radius. Paths stop at their first centre-plane crossing; a later return
  from the other side cannot count as a successful hit.
- Zone score, the user's rule: love hitting the bead, punish higher exponentially and lower quadratically. Each
  flux-weighted streamline of an outlet scores +1 if it passes through its own zone. If it reaches the zone's
  half-cylinder only above tip level, D is its lowest height there above the tip and it scores
  1 - (exp(D / 1 mm) - 1), D capped at 4 mm. If it reaches tip level on its own side only outside the zone,
  D = 0.36 (r - R), the vertical miss of a 20-degree jet that lands that far short, and it scores
  1 - (D / 1 mm)^2, D capped at 5 mm. Otherwise D is its height above the tip where it comes nearest the axis,
  scored as higher. "path" follows the real streamline; "aim" extends its exit direction straight to the print.
  Scores are means per litre: 1 would put every litre of the outlet in its zone. "side jets" is the mean of the
  two side jets.
- Arriving on the print: downward and upward flow through a plane 0.5 mm above the print, in the bead ring
  (r 0.6-2 mm) and over the print at r 2-5 mm.
- Own-side reach: the share of side-jet streamlines that enter the half-cylinder r <= 4 mm on their own side, and
  the share whose lowest point there is within 0.2, 0.5 and 1.0 mm of the print.
- Exit angle: the inward-flux-weighted downward angle of the side jets at |X| 10.3, Y 18-27, with each Y column
  of the opening split into four equal bands, bottom to top.
- Cone scrub: the share of side-jet streamlines that pass within 0.5 mm of the nozzle's surface between 1 mm above
  the print and the sock, binned by where they leave the opening.
"""
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402
from vtk.util.numpy_support import vtk_to_numpy  # noqa: E402

import cfd_cpap_r41 as C  # noqa: E402
import cfd_nozzle_focus_r43 as F  # noqa: E402
import cfd_outlet_balance_r43 as B  # noqa: E402
import render_outlet_balance_r43 as R  # noqa: E402
import cfd_provenance_r43 as V  # noqa: E402

NY, BED_Z = F.NY, F.BED_Z
TIP_H = C.NOZZLE_TIP_Z - BED_Z
EPS = 1e-5                                    # coordinate roundoff only, not a band above the tip
ZONES = {"r 2.5 mm": 2.5, "r 4 mm": 4.0}
Y_BINS = ((16.5, 19.0), (19.0, 21.0), (21.0, 23.0), (23.0, 25.0), (25.0, 28.5))
Z_BINS = ((-77.1, -76.2), (-76.2, -75.3), (-75.3, -74.4), (-74.4, -73.0))


def operating(case):
    report = V.read_balance(case)
    return report, report["operating_point_1m_hose"]["lpm"] / 180


def own_side(key, p):
    return {"left": p[:, 0] < 0, "right": p[:, 0] > 0, "centre": p[:, 1] < NY}[key]


def classify(key, p, radius):
    """(hit / higher / lower, D) for one path given as points."""
    crossings = np.flatnonzero(~own_side(key, p))
    if len(crossings):
        p = p[:max(1, crossings[0])]
    h = p[:, 2] - BED_Z
    r = np.hypot(p[:, 0], p[:, 1] - NY)
    own = own_side(key, p)
    cyl = own & (r <= radius)
    if (cyl & (h <= TIP_H + EPS)).any():
        return "hit", 0.0
    if cyl.any():
        return "higher", float(h[cyl].min() - TIP_H)
    low = own & (h <= TIP_H + EPS)
    if low.any():
        return "lower", float(.36 * (r[low].min() - radius))
    i = int(np.argmin(r))
    return "higher", float(max(h[i] - TIP_H, 0.0))


def score(cat, d):
    if cat == "hit":
        return 1.0
    if cat == "higher":
        return 1 - (np.exp(min(d, 4.0)) - 1)
    return 1 - min(d, 5.0) ** 2


def straight(o, d, step=.05, length=25.0):
    p = o + np.arange(0, length, step)[:, None] * d
    stop = np.flatnonzero(p[:, 2] <= BED_Z)
    if not len(stop):
        return p
    i = int(stop[0])
    p = p[:i + 1].copy()
    if i:
        t = (BED_Z - p[i - 1, 2]) / (p[i, 2] - p[i - 1, 2])
        p[i] = p[i - 1] + t * (p[i] - p[i - 1])
    return p


def zones(report, factor, pts, offsets, label):
    o, d = F.initial_rays(pts, offsets)
    out = {}
    for zname, radius in ZONES.items():
        z, lpm = {}, {}
        for i, key in enumerate(F.KEYS):
            idx = np.flatnonzero(label == i)
            lpm[key] = report["outlets"][key]["lpm"] * factor
            z[key] = {}
            for kind in ("path", "aim"):
                res = [classify(key, pts[offsets[n]:offsets[n + 1]] if kind == "path" else straight(o[n], d[n]),
                                radius) for n in idx]
                cats = [c for c, _ in res]
                z[key][kind] = {"score": float(np.mean([score(c, dd) for c, dd in res])),
                                                "in_zone_lpm": lpm[key] * cats.count("hit") / len(cats),
                                **{f"{c}_pct": 100 * cats.count(c) / len(cats) for c in ("hit", "higher", "lower")}}
        for kind in ("path", "aim"):
            z[f"side_jets_{kind}_score"] = (z["left"][kind]["score"] + z["right"][kind]["score"]) / 2
            z[f"all_{kind}_score"] = sum(z[k][kind]["score"] * lpm[k] for k in F.KEYS) / sum(lpm.values())
            z[f"all_{kind}_in_zone_lpm"] = sum(z[k][kind]["in_zone_lpm"] for k in F.KEYS)
        out[zname] = z
    return out


def arriving(g, factor, h=.5):
    dr, dphi = .05, np.radians(2.0)
    rr, pp = np.meshgrid(np.arange(.6 + dr / 2, 5.0, dr), np.arange(0, 2 * np.pi, dphi), indexing="ij")
    ok, u = F.probe(g, np.column_stack((rr.ravel() * np.cos(pp.ravel()), NY + rr.ravel() * np.sin(pp.ravel()),
                                        np.full(rr.size, BED_Z + h))))
    w = np.where(ok, u[:, 2], 0.0).reshape(rr.shape) * factor
    area = rr * dr * dphi * 1e-6 * 60000          # mm2 times m/s, to L/min
    ok = ok.reshape(rr.shape)
    out = {}
    for name, lo, hi in (("bead ring r 0.6-2 mm", .6, 2.0), ("print r 2-5 mm", 2.0, 5.0)):
        m = (rr >= lo) & (rr < hi) & ok
        out[name] = {"down_lpm": float((np.clip(-w[m], 0, None) * area[m]).sum()),
                     "up_lpm": float((np.clip(w[m], 0, None) * area[m]).sum())}
    return out


def reach(pts, offsets, label, radius=4.0):
    lows = []
    for side, sign in (("left", -1), ("right", 1)):
        for n in np.flatnonzero(label == F.KEYS.index(side)):
            p = pts[offsets[n]:offsets[n + 1]]
            crossings = np.flatnonzero(~own_side(side, p))
            if len(crossings):
                p = p[:max(1, crossings[0])]
            m = (sign * p[:, 0] > 0) & (np.hypot(p[:, 0], p[:, 1] - NY) <= radius)
            lows.append(float((p[m, 2] - BED_Z).min()) if m.any() else np.nan)
    lows = np.array(lows)
    entered = np.isfinite(lows)
    out = {"enter_pct": 100 * float(entered.mean()), "median_lowest_mm": float(np.median(lows[entered]))}
    for name, t in (("0.2", .2 + EPS), ("0.5", .5), ("1.0", 1.0)):
        out[f"lowest_within_{name}_mm_pct"] = 100 * float(np.mean(lows[entered] <= t)) * float(entered.mean())
    return out


def exit_bands(g):
    ys, zs = np.arange(18.0, 27.0001, .1), np.arange(-77.3, -73.0, .025)
    yy, zz = np.meshgrid(ys, zs, indexing="ij")
    num, den = np.zeros(4), np.zeros(4)
    for side in (1, -1):
        ok, u = F.probe(g, np.column_stack((np.full(yy.size, 10.3 * side), yy.ravel(), zz.ravel())))
        ok, u = ok.reshape(yy.shape), u.reshape(yy.shape + (3,))
        for i in range(len(ys)):
            col = np.flatnonzero(ok[i])
            if len(col) < 4:
                continue
            z0, z1 = zs[col[0]], zs[col[-1]]
            inward = -u[i, col, 0] * side
            angle = np.degrees(np.arctan2(-u[i, col, 2], np.maximum(inward, 1e-9)))
            w = np.clip(inward, 0, None)
            band = np.minimum(((zs[col] - z0) / max(z1 - z0, 1e-9) * 4).astype(int), 3)
            for b in range(4):
                num[b] += (angle[band == b] * w[band == b]).sum()
                den[b] += w[band == b].sum()
    return [float(v) for v in num / den], float(num.sum() / den.sum())


def cone_tree(case):
    poly = F.hotend_walls(case)
    p = vtk_to_numpy(poly.GetPoints().GetData()).astype(float)
    tri = vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    a, b, c = p[tri[:, 0]], p[tri[:, 1]], p[tri[:, 2]]
    s = np.array([(i / 4, j / 4) for i in range(5) for j in range(5 - i)])      # dense samples on each triangle
    samples = (a[:, None] + s[None, :, :1] * (b - a)[:, None] + s[None, :, 1:] * (c - a)[:, None]).reshape(-1, 3)
    r = np.hypot(samples[:, 0], samples[:, 1] - NY)
    return cKDTree(samples[(samples[:, 2] < -75.45) & (r < 4.0) & (samples[:, 2] - BED_Z > 1.0)])


def scrub_lines(case, pts, offsets, label):
    """Start point of each side-jet streamline and whether it passes within 0.5 mm of the nozzle cone."""
    tree = cone_tree(case)
    starts, hits = [], []
    for n in np.flatnonzero(np.isin(label, [F.KEYS.index("left"), F.KEYS.index("right")])):
        d, _ = tree.query(pts[offsets[n]:offsets[n + 1]], distance_upper_bound=2.0)
        starts.append(pts[offsets[n]])
        hits.append(bool(d.min() < .5))
    return np.array(starts), np.array(hits)


def scrub(starts, hits):
    def by(bins, axis):
        out = []
        for lo, hi in bins:
            m = (starts[:, axis] >= lo) & (starts[:, axis] < hi)
            out.append(100 * float(hits[m].mean()) if m.any() else 0.0)
        return out
    return {"side_lines": int(len(hits)), "scrub_pct": 100 * float(hits.mean()),
            "scrub_pct_by_start_y": dict(zip([f"{a}-{b}" for a, b in Y_BINS], by(Y_BINS, 1))),
            "scrub_pct_by_start_z": dict(zip([f"{a}..{b}" for a, b in Z_BINS], by(Z_BINS, 2)))}


def analyse(case):
    report, factor = operating(case)
    pts, offsets, label = F.streamlines(case)
    g = B.load(case, True)
    bands, mean = exit_bands(g)
    arrive = arriving(g, factor)
    del g
    starts, hits = scrub_lines(case, pts, offsets, label)
    return {"case": case, "operating_point_lpm": report["operating_point_1m_hose"]["lpm"],
            "zones": zones(report, factor, pts, offsets, label), "arriving_on_the_print": arrive,
            "own_side_reach_r4": reach(pts, offsets, label),
            "side_jet_exit_angle_deg": {"bottom_to_top": bands, "mean": mean},
            "cone_scrub": scrub(starts, hits), "definitions": __doc__[__doc__.index("Definitions"):].strip(),
            "inputs_sha256": V.focus_inputs(case), "analyser_sha256": V.digest(Path(__file__))}


def real_paths(case, side):
    """Median real path, in X-Z, of the bottom / middle / top quarter (by start height) of one side jet: each
    streamline's height where it first reaches each X station on its way in, then the median per station where at
    least half the quarter's lines reach it."""
    pts, offsets, label = F.streamlines(case)
    sign = -1 if side == "left" else 1
    stations = np.arange(10.2, -.01, -.25)
    rows = []
    for n in np.flatnonzero(label == F.KEYS.index(side)):
        p = pts[offsets[n]:offsets[n + 1]]
        ax_ = sign * p[:, 0]
        zs = np.full(len(stations), np.nan)
        for k, xs in enumerate(stations):
            j = np.flatnonzero(ax_ <= xs)
            if len(j) and j[0] > 0:
                a, b = j[0] - 1, j[0]
                t = (ax_[a] - xs) / max(ax_[a] - ax_[b], 1e-9)
                zs[k] = p[a, 2] + t * (p[b, 2] - p[a, 2])
            elif len(j):
                zs[k] = p[0, 2]
        rows.append((p[0, 2], zs))
    rows.sort(key=lambda r: r[0])
    z = np.array([r[1] for r in rows])
    q = max(len(z) // 4, 1)
    out = []
    for grp in (z[:q], z[len(z) // 2 - q // 2:][:q], z[-q:]):
        with np.errstate(all="ignore"):
            med, frac = np.nanmedian(grp, axis=0), np.mean(np.isfinite(grp), axis=0)
        ok = np.isfinite(med) & (frac >= .5)
        out.append((sign * stations[ok], med[ok]))
    return out


def paths_figure(out_png, specs):
    specs = [s.split("=", 1) for s in specs]
    cols = min(len(specs), 3)
    rows = (len(specs) + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(9.5 * cols, 6.2 * rows), dpi=100, squeeze=False)
    fig.patch.set_facecolor(R.BG)
    im, tip = None, C.NOZZLE_TIP_Z
    for ax, (label, case) in zip(axes.ravel(), specs):
        _, sec = F.load_cached(case)
        z = json.loads((C.results_dir(case) / "bead_zones.json").read_text())
        z4 = z["zones"]["r 4 mm"]
        title = (f"{label}\nscore {z4['side_jets_path_score']:+.1f} (side jets, r 4 mm zones); "
                 f"{z4['all_path_in_zone_lpm']:.1f} L/min in them; {z['operating_point_lpm']:.0f} L/min")
        im = F.draw_section(ax, sec["front"], title, "X (mm)", [], (90.0, 90.1))
        for t in list(ax.texts):
            if t.get_text() == "fresh bead":
                t.remove()
        for side in ("left", "right"):
            for xs, zs in real_paths(case, side):
                if len(xs) < 2:
                    continue
                ax.plot(xs, zs, color="w", lw=4.0, zorder=8, solid_capstyle="round")
                ax.plot(xs, zs, color=R.COLORS[side], lw=2.2, zorder=9, solid_capstyle="round")
                ax.annotate("", xy=(xs[-1], zs[-1]), xytext=(xs[-2], zs[-2]), zorder=10,
                            arrowprops=dict(arrowstyle="-|>", color=R.COLORS[side], lw=2.2, mutation_scale=14))
        for x0, color in ((-4.0, R.COLORS["left"]), (0.0, R.COLORS["right"])):
            ax.add_patch(plt.Rectangle((x0, tip - 1.0), 4.0, 1.0, fill=False, ec=color, lw=1.6, ls="--", zorder=7))
            ax.add_patch(plt.Rectangle((x0 * 2.5 / 4.0, tip - .4), 2.5, .4, fc=color, alpha=.35, ec=color, lw=1.2,
                                       zorder=7))
        ax.text(0, tip - 1.15, "target zones below the tip, own side only", color="#ffd43b", ha="center", va="top",
                fontsize=9.5, zorder=8)
        ax.set_ylim(tip - 1.6, ax.get_ylim()[1])
        ax.title.set_fontsize(11.5)
    for ax in axes.ravel()[len(specs):]:
        ax.set_visible(False)
    bar = fig.colorbar(im, ax=axes.ravel().tolist(), shrink=.5, pad=.01, fraction=.015)
    bar.set_label("m/s", color=R.MUTED)
    bar.ax.tick_params(colors=R.MUTED)
    fig.suptitle("Front section through the nozzle (Y 22.7). Lines: the real median path of the bottom, middle and "
                 "top quarter of each side jet (all its air, any Y). Zones: filled r 2.5 mm, 0-0.4 mm below the tip; "
                 "dashed r 4 mm, 0-1 mm below.\nPath score: the user's rule against each jet's own-side zone (+1 in "
                 "it; higher punished exponentially, lower quadratically). Airflow, not temperature.",
                 color=R.TEXT, fontsize=14)
    fig.savefig(out_png, facecolor=R.BG, bbox_inches="tight", pad_inches=.3)
    print(out_png)


def scrub_map(out_png, specs):
    specs = [s.split("=", 1) for s in specs]
    fig, axes = plt.subplots(1, len(specs), figsize=(7.2 * len(specs), 5.6), dpi=110, squeeze=False)
    fig.patch.set_facecolor(R.BG)
    for ax, (label, case) in zip(axes[0], specs):
        pts, offsets, lab = F.streamlines(case)
        starts, hits = scrub_lines(case, pts, offsets, lab)
        g = B.load(case, True)
        ys, zs = np.arange(16.0, 28.6, .05), np.arange(-77.6, -72.8, .025)
        yy, zz = np.meshgrid(ys, zs, indexing="ij")
        ok, _ = F.probe(g, np.column_stack((np.full(yy.size, 10.3), yy.ravel(), zz.ravel())))
        del g
        ok = ok.reshape(yy.shape).T.astype(float)
        R.style(ax, f"{label}: {100 * hits.mean():.0f}% of side-jet air passes the cone")
        ax.contourf(ys, zs, ok, levels=[.5, 1.5], colors=["#1d3a55"], zorder=0)
        ax.contour(ys, zs, ok, levels=[.5], colors=["#c9d6e3"], linewidths=.9, zorder=1)
        ax.scatter(starts[~hits, 1], starts[~hits, 2], s=7, color="#4dabf7", alpha=.55, lw=0, zorder=2,
                   label="misses the cone")
        ax.scatter(starts[hits, 1], starts[hits, 2], s=16, color="#ff6b6b", edgecolor="k", lw=.3, zorder=3,
                   label="passes within 0.5 mm of the cone")
        ax.axhline(-75.48, color="#ffd43b", lw=.8, ls=":")
        ax.text(28.4, -75.42, "sock bottom", color="#ffd43b", fontsize=8, ha="right", va="bottom")
        ax.axvline(NY, color="#c9d6e3", lw=.8, ls="--")
        ax.text(NY + .1, -72.95, "nozzle Y", color=R.MUTED, fontsize=8, va="top")
        ax.set_xlim(16.0, 28.6)
        ax.set_ylim(-77.6, -72.8)
        ax.set_xlabel("Y (mm), toward the front", color=R.MUTED)
        ax.set_ylabel("Z (mm)", color=R.MUTED)
        R.legend(ax, loc="upper left", fontsize=8, markerscale=1.5)
    fig.suptitle("Where the side-jet air that passes the nozzle cone leaves the opening (seen from the nozzle at "
                 "|X| 10.3, both jets overlaid). Airflow, not temperature.", color=R.TEXT, fontsize=13)
    fig.tight_layout(rect=(0, 0, 1, .94))
    fig.savefig(out_png, facecolor=R.BG)
    print(out_png)


def main():
    if sys.argv[1] == "--paths":
        paths_figure(sys.argv[2], sys.argv[3:])
        return
    if sys.argv[1] == "--scrub-map":
        scrub_map(sys.argv[2], sys.argv[3:])
        return
    for case in sys.argv[1:]:
        r = analyse(case)
        (C.results_dir(case) / "bead_zones.json").write_text(json.dumps(r, indent=1) + "\n")
        z4, a = r["zones"]["r 4 mm"], r["arriving_on_the_print"]["bead ring r 0.6-2 mm"]
        print(f"{case}: side jets path {z4['side_jets_path_score']:+.2f} aim {z4['side_jets_aim_score']:+.2f}; "
              f"in zones {z4['all_path_in_zone_lpm']:.1f} L/min; onto the bead ring {a['down_lpm']:.2f} L/min; "
              f"cone scrub {r['cone_scrub']['scrub_pct']:.1f}%; exit {r['side_jet_exit_angle_deg']['mean']:.1f} deg")


if __name__ == "__main__":
    main()
