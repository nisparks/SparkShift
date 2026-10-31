"""Centre/side outlet balance figures for C28 CFD results (unbranded).

Usage:
  python render_outlet_balance_r43.py <out.png> <case>[:mean]                   one case in detail
  python render_outlet_balance_r43.py <out.png> --compare <label=case[:mean]> ...  near-print and delivery comparison
  python render_outlet_balance_r43.py <out.png> --symmetry <label=case[:mean]> ... left against right
Run cfd_outlet_balance_r43.py on each case first (with --mean for :mean).
"""
import json
import math
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import LineCollection
import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import cfd_outlet_balance_r43 as B
import cfd_direct_mount_r43 as D

BG, PANEL, TEXT, MUTED, EDGE = "#0f1d2e", "#13263b", "#e6eef6", "#9fb3c8", "#4b6584"
COLORS = {"left": "#ff9f43", "right": "#4dabf7", "centre": "#63e6be"}
NAMES = {"left": "left jet", "right": "right jet", "centre": "centre slot"}
KEYS = ("left", "right", "centre")
BED_Z = C.NOZZLE_TIP_Z - C.BED_GAP


def spec(text):
    case = text.split("=", 1)[-1]
    return case.split(":")[0], case.endswith(":mean")


def report_of(case, mean):
    return json.loads((C.results_dir(case) / f"outlet_balance{'_mean' if mean else ''}.json").read_text())


def lines_by_outlet(case, mean):
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(str(C.results_dir(case) / f"outlet_streamlines{'_mean' if mean else ''}.vtp"))
    reader.Update()
    poly = reader.GetOutput()
    xyz = vtk_to_numpy(poly.GetPoints().GetData())
    label = vtk_to_numpy(poly.GetCellData().GetArray("outlet"))
    out = {k: [] for k in KEYS}
    for cell in range(poly.GetNumberOfCells()):
        ids = poly.GetCell(cell).GetPointIds()
        out[KEYS[label[cell]]].append(xyz[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]])
    return out


def style(ax, title):
    ax.set_facecolor(PANEL)
    ax.set_title(title, color=TEXT, fontsize=13, loc="left")
    ax.tick_params(colors=MUTED, labelsize=9)
    for spine in ax.spines.values():
        spine.set_color(EDGE)


def legend(ax, **kw):
    handle = ax.legend(facecolor=PANEL, edgecolor=EDGE, **kw)
    for text in handle.get_texts():
        text.set_color(TEXT)


def streamlines(ax, lines, keys, axes, limits, title):
    style(ax, title)
    for key in keys:
        ax.add_collection(LineCollection([p[:, axes] for p in lines[key]], colors=COLORS[key], linewidths=.5,
                                         alpha=.5, label=NAMES[key]))
    if axes == [1, 2]:
        ax.axhline(BED_Z, color="#c9d6e3", lw=1.2)
        ax.text(limits[1] - .5, BED_Z - 1.2, "print surface", color=MUTED, ha="right", fontsize=9)
        ax.add_patch(plt.Polygon([(C.NOZZLE_Y - .5, C.NOZZLE_TIP_Z), (C.NOZZLE_Y + .5, C.NOZZLE_TIP_Z),
                                  (C.NOZZLE_Y + 3.2, -73.35), (C.NOZZLE_Y - 3.2, -73.35)], color="#b8c2cc", zorder=5))
        ax.set_xlabel("Y (mm), toward the front", color=MUTED)
        ax.set_ylabel("Z (mm)", color=MUTED)
    elif axes == [0, 2]:
        ax.axhline(BED_Z, color="#c9d6e3", lw=1.2)
        ax.text(limits[1] - .5, BED_Z - 1.2, "print surface", color=MUTED, ha="right", fontsize=9)
        ax.add_patch(plt.Polygon([(-.5, C.NOZZLE_TIP_Z), (.5, C.NOZZLE_TIP_Z), (3.2, -73.35), (-3.2, -73.35)],
                                 color="#b8c2cc", zorder=5))
        ax.set_xlabel("X (mm), looking from the front", color=MUTED)
        ax.set_ylabel("Z (mm)", color=MUTED)
    else:
        ax.add_patch(plt.Circle((0, C.NOZZLE_Y), .6, color="#b8c2cc", zorder=5))
        ax.set_xlabel("X (mm)", color=MUTED)
        ax.set_ylabel("Y (mm), toward the front", color=MUTED)
    ax.set_xlim(*limits[:2])
    ax.set_ylim(*limits[2:])
    ax.set_aspect("equal")
    legend(ax, loc="upper left", fontsize=9)


def bed_field(case, mean, factor):
    g = B.load(case, mean)
    xs, ys = np.linspace(-14, 14, 141), np.linspace(C.NOZZLE_Y - 14, C.NOZZLE_Y + 14, 141)
    X, Y = np.meshgrid(xs, ys)
    u, ok = P.probe(g, np.column_stack((X.ravel(), Y.ravel(), np.full(X.size, BED_Z + .3))))
    speed = np.where(ok, np.linalg.norm(u, axis=1) * factor, np.nan).reshape(X.shape)
    cov = D.coverage(g, factor)
    del g
    return speed, cov


def bed_map(ax, fig, speed, cov, title):
    style(ax, title)
    im = ax.imshow(speed, origin="lower", extent=(-14, 14, C.NOZZLE_Y - 14, C.NOZZLE_Y + 14), cmap="turbo",
                   vmin=0, vmax=45)
    for angle in (45, 135, 225, 315):
        a = math.radians(angle)
        ax.plot([math.cos(a), 5 * math.cos(a)], [C.NOZZLE_Y + math.sin(a), C.NOZZLE_Y + 5 * math.sin(a)], color="w", lw=1)
    ax.add_patch(plt.Circle((0, C.NOZZLE_Y), 5, fill=False, color="w", lw=1))
    sectors = cov["sector_area_mean_speed_ms"]
    for name, angle in (("right", 0), ("front", 90), ("left", 180), ("rear", 270)):
        a = math.radians(angle)
        ax.text(8.7 * math.cos(a), C.NOZZLE_Y + 8.7 * math.sin(a), f"{name}\n{sectors[name]:.1f} m/s", color="w",
                ha="center", va="center", fontsize=11, fontweight="bold")
    ax.set_xlabel(f"Sector means over r 1-5 mm. Weakest/strongest {cov['weakest_to_strongest_sector_mean_ratio']:.2f}",
                  color=MUTED)
    bar = fig.colorbar(im, ax=ax, shrink=.85)
    bar.set_label("m/s at the blower operating point", color=MUTED)
    bar.ax.tick_params(colors=MUTED)


def delivery_bars(ax, report):
    style(ax, "Air supplied vs what passes over the print (L/min at 180 L/min)")
    supplied = [report["outlets"][k]["lpm"] for k in KEYS]
    r10 = [report["delivery"][k]["lpm_reaching_r10"] for k in KEYS]
    r5 = [report["delivery"][k]["lpm_reaching_r5"] for k in KEYS]
    up = [report["outlets"][k]["lpm"] * report["delivery"][k]["up_pct"] / 100 for k in KEYS]
    x = np.arange(3)
    w = .2
    ax.bar(x - 1.5 * w, supplied, w, color=[COLORS[k] for k in KEYS], alpha=.4, label="supplied")
    ax.bar(x - .5 * w, r10, w, color=[COLORS[k] for k in KEYS], label="within 1 mm of the print, r <= 10 mm")
    ax.bar(x + .5 * w, r5, w, color=[COLORS[k] for k in KEYS], hatch="//", edgecolor=PANEL,
           label="within 1 mm of the print, r <= 5 mm")
    ax.bar(x + 1.5 * w, up, w, color="#ff6b6b", label="rises past the hotend instead")
    for i, k in enumerate(KEYS):
        ax.text(i - .5 * w, r10[i] + 1, f"{report['delivery'][k]['r10_mm_pct']:.0f}%", color=TEXT, ha="center", fontsize=10)
        ax.text(i + 1.5 * w, up[i] + 1, f"{report['delivery'][k]['up_pct']:.0f}%", color=TEXT, ha="center", fontsize=10)
    ax.set_xticks(x, [NAMES[k] for k in KEYS], color=MUTED)
    ax.set_ylim(0, 80)
    legend(ax, loc="upper right", fontsize=9)


def waterfall(ax, report):
    style(ax, "Where the total pressure goes (Pa at 180 L/min)")
    side = {r["station"]: r for r in report["pressure_budget"]["side_path"]}
    centre = {r["station"]: r for r in report["pressure_budget"]["centre_branch"]}
    steps = [("P20 hose inlet", side["hose"]["pt"] - side["P20 lower"]["pt"]),
             ("P21 trunk", side["P20 lower"]["pt"] - side["P21 above joint"]["pt"]),
             ("joint, lobes, elbow", side["P21 above joint"]["pt"] - side["after elbow"]["pt"]),
             ("channels to the split", side["after elbow"]["pt"] - side["before centre take-off"]["pt"])]
    branches = {"side jets": [("side channels", side["before centre take-off"]["pt"] - side["side channels beside hotend"]["pt"]),
                              ("turn into the jets", side["side channels beside hotend"]["pt"] - side["side jet exits"]["pt"])],
                "centre slot": [("centre feeds", side["before centre take-off"]["pt"] - centre["centre feeds (Y -2)"]["pt"]),
                                ("merge trunk", centre["centre feeds (Y -2)"]["pt"] - centre["centre trunk (Y 4.25)"]["pt"]),
                                ("slot", centre["centre trunk (Y 4.25)"]["pt"] - centre["centre slot exit"]["pt"])]}
    labels, starts, heights, colors = [], [], [], []
    level = side["hose"]["pt"]
    for name, drop in steps:
        labels.append(name)
        starts.append(level - drop)
        heights.append(drop)
        colors.append("#8fa3b8")
        level -= drop
    split = level
    for branch, rows in branches.items():
        level = split
        for name, drop in rows:
            labels.append(f"{branch}: {name}")
            starts.append(level - drop)
            heights.append(drop)
            colors.append(COLORS["left"] if branch == "side jets" else COLORS["centre"])
            level -= drop
    y = np.arange(len(labels))[::-1]
    ax.barh(y, heights, left=starts, color=colors)
    for yi, s, h in zip(y, starts, heights):
        ax.text(s - 4, yi, f"-{h:.0f}", color=TEXT, ha="right", va="center", fontsize=10)
    ax.set_yticks(y, labels, color=MUTED, fontsize=10)
    ax.axvline(side["hose"]["pt"], color="#c9d6e3", lw=1, ls=":")
    exits = report["outlets"]
    low = min(starts)
    ax.set_xlim(low - .12 * (side["hose"]["pt"] - low), side["hose"]["pt"] + .04 * (side["hose"]["pt"] - low))
    ax.set_xlabel(f"Inlet {side['hose']['pt']:.0f} Pa. Side-jet exits keep {side['side jet exits']['pt']:.0f} Pa, "
                  f"{side['side jet exits']['dyn']:.0f} Pa of it as jet speed ({exits['left']['mean_ms']:.0f} m/s mean)",
                  color=MUTED)


def detail(out, case, mean, title="current set"):
    report = report_of(case, mean)
    factor = report["operating_point_1m_hose"]["lpm"] / 180
    lines = lines_by_outlet(case, mean)
    fig, axes = plt.subplots(3, 2, figsize=(17, 18.5), dpi=100, gridspec_kw={"height_ratios": [.55, 1, .9]})
    fig.patch.set_facecolor(BG)
    streamlines(axes[0, 0], lines, ("left", "right"), [1, 2], (2, 46, -82, -62), "Side jets, side view")
    streamlines(axes[0, 1], lines, ("centre",), [1, 2], (2, 46, -82, -62), "Centre slot, side view")
    streamlines(axes[1, 0], lines, ("centre", "left", "right"), [0, 1], (-24, 24, 2, 46), "All outlets, plan view")
    speed, cov = bed_field(case, mean, factor)
    bed_map(axes[1, 1], fig, speed, cov, "Speed 0.3 mm above the print")
    delivery_bars(axes[2, 0], report)
    waterfall(axes[2, 1], report)
    fig.suptitle("Centre slot vs side jets: where the air goes and where the pressure goes\n"
                 f"Bambu C28, {title}. {'Iteration mean 700-1200' if mean else 'Snapshot'}; 180 L/min; "
                 f"blower operating point {report['operating_point_1m_hose']['lpm']:.0f} L/min with 1 m hose. "
                 "Airflow, not temperature.", color=TEXT, fontsize=16)
    fig.tight_layout(rect=(0, 0, 1, .965))
    fig.savefig(out, facecolor=BG)


def compare(out, specs):
    rows = []
    for text in specs:
        label, (case, mean) = text.split("=", 1)[0], spec(text)
        report = report_of(case, mean)
        factor = report["operating_point_1m_hose"]["lpm"] / 180
        cov = D.coverage(B.load(case, mean), factor)
        rows.append((label, report, cov, factor))
    fig, axes = plt.subplots(1, 3, figsize=(23, 7.5), dpi=100)
    fig.patch.set_facecolor(BG)
    x = np.arange(len(rows))
    names = [textwrap.fill(r[0], 12) for r in rows]
    ax = axes[0]
    style(ax, "Near-print sector means, r 1-5 mm (m/s)")
    for i, (name, c) in enumerate((("right", "#4dabf7"), ("front", "#e6eef6"), ("left", "#ff9f43"), ("rear", "#63e6be"))):
        ax.bar(x + (i - 1.5) * .2, [r[2]["sector_area_mean_speed_ms"][name] for r in rows], .2, color=c, label=name)
    for xi, r in zip(x, rows):
        s = r[2]["sector_area_mean_speed_ms"]
        ax.text(xi, max(s.values()) + 1, f"mean {sum(s.values()) / 4:.1f}\nratio "
                f"{r[2]['weakest_to_strongest_sector_mean_ratio']:.2f}", color=TEXT, ha="center", fontsize=9)
    ax.set_xticks(x, names, color=MUTED)
    ax.set_ylim(0, 1.3 * max(max(r[2]["sector_area_mean_speed_ms"].values()) for r in rows))
    legend(ax, loc="lower center", fontsize=9, ncol=4)
    ax = axes[1]
    style(ax, "Air per outlet that passes within 1 mm of the print, r <= 10 mm (L/min)")
    for i, key in enumerate(KEYS):
        ax.bar(x + (i - 1.5) * .2, [r[1]["delivery"][key]["lpm_reaching_r10"] * r[3] for r in rows], .2,
               color=COLORS[key], label=NAMES[key])
    up = [sum(r[1]["outlets"][k]["lpm"] * r[1]["delivery"][k]["up_pct"] / 100 for k in KEYS) * r[3] for r in rows]
    ax.bar(x + 1.5 * .2, up, .2, color="#ff6b6b", label="all outlets: rises past the hotend")
    for xi, r, u in zip(x, rows, up):
        total = sum(r[1]["delivery"][k]["lpm_reaching_r10"] for k in KEYS) * r[3]
        ax.text(xi, max(u, total / 2) + 4, f"over print {total:.0f}\nrising {u:.0f}", color=TEXT, ha="center",
                fontsize=9)
    ax.set_xticks(x, names, color=MUTED)
    ax.set_ylim(0, 1.35 * max(max(up), max(r[1]["delivery"][k]["lpm_reaching_r10"] * r[3] for r in rows for k in KEYS)))
    legend(ax, loc="upper right", fontsize=8)
    ax = axes[2]
    style(ax, "Centre share of the flow, and the blower operating point")
    centre = [r[1]["outlets"]["centre"]["share_pct"] for r in rows]
    ax.bar(x, centre, .5, color=COLORS["centre"])
    for xi, r, c in zip(x, rows, centre):
        op = r[1]["operating_point_1m_hose"]
        ax.text(xi, c + 1, f"{c:.0f}% centre\n{op['lpm']:.0f} L/min total\nduct {op['duct_pa']:,} Pa", color=TEXT,
                ha="center", fontsize=10)
    ax.set_xticks(x, names, color=MUTED)
    ax.set_ylim(0, 1.6 * max(centre))
    fig.suptitle("Balance trials, iteration-mean CFD. Air values at each design's own blower operating point "
                 "(WS7040, 1 m hose); not temperatures.", color=TEXT, fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, .95))
    fig.savefig(out, facecolor=BG)


def symmetry(out, specs):
    """Left against right: side-jet streamlines of the first and last case in plan and front view, and left/right
    pairs of the delivery and near-print numbers for every case."""
    rows = []
    for text in specs:
        label, (case, mean) = text.split("=", 1)[0], spec(text)
        report = report_of(case, mean)
        factor = report["operating_point_1m_hose"]["lpm"] / 180
        rows.append((label, case, mean, report, D.coverage(B.load(case, mean), factor), factor))
    fig, axes = plt.subplots(3, 2, figsize=(18, 24), dpi=100, gridspec_kw={"height_ratios": [1, .62, .75]})
    fig.patch.set_facecolor(BG)
    for column, (label, case, mean, *_rest) in enumerate((rows[0], rows[-1])):
        lines = lines_by_outlet(case, mean)
        streamlines(axes[0, column], lines, ("left", "right"), [0, 1], (-24, 24, 2, 46),
                    f"Side jets, plan view: {label}")
        ax = axes[1, column]
        streamlines(ax, lines, ("left", "right"), [0, 2], (-24, 24, -80, -45), f"Side jets, front view: {label}")
        if "mirrored_half" not in json.loads((C.results_dir(case) / "domain.json").read_text()):
            # the Bambu hotend fan's underside inside the CFD box (render_scene_symmetry_r43.py); right side only
            ax.add_patch(plt.Rectangle((9.8, -47.8), 10.0, 2.8, facecolor="#8fa3b8", edgecolor="w", hatch="//",
                                       alpha=.8, zorder=6))
            ax.text(14.8, -49.2, "hotend fan", color=TEXT, ha="center", va="top", fontsize=10, zorder=7)
    x = np.arange(len(rows))
    names = [textwrap.fill(r[0], 16) for r in rows]
    ax = axes[2, 0]
    style(ax, "Side-jet air within 1 mm of the print, r <= 10 mm (L/min)")
    for i, key in enumerate(("left", "right")):
        vals = [r[3]["delivery"][key]["lpm_reaching_r10"] * r[5] for r in rows]
        ax.bar(x + (i - .5) * .36, vals, .36, color=COLORS[key], label=NAMES[key])
        for xi, r, v in zip(x, rows, vals):
            ax.text(xi + (i - .5) * .36, v + .6, f"{v:.0f}\n{r[3]['delivery'][key]['r10_mm_pct']:.0f}% of\n"
                    f"its {r[3]['outlets'][key]['lpm'] * r[5]:.0f}", color=TEXT, ha="center", fontsize=9)
    ax.set_xticks(x, names, color=MUTED)
    ax.set_ylim(0, 1.45 * max(r[3]["delivery"][k]["lpm_reaching_r10"] * r[5] for r in rows for k in ("left", "right")))
    legend(ax, loc="upper right", fontsize=9)
    ax = axes[2, 1]
    style(ax, "Near-print sector means on each side, r 1-5 mm (m/s)")
    for i, key in enumerate(("left", "right")):
        vals = [r[4]["sector_area_mean_speed_ms"][key] for r in rows]
        ax.bar(x + (i - .5) * .36, vals, .36, color=COLORS[key], label=f"{key} sector")
        for xi, v in zip(x, vals):
            ax.text(xi + (i - .5) * .36, v + .4, f"{v:.1f}", color=TEXT, ha="center", fontsize=10)
    ax.set_xticks(x, names, color=MUTED)
    ax.set_ylim(0, 1.3 * max(r[4]["sector_area_mean_speed_ms"][k] for r in rows for k in ("left", "right")))
    legend(ax, loc="upper right", fontsize=9)
    fig.suptitle("Left against right. Iteration-mean CFD; air at each case's blower operating point (WS7040, 1 m hose). "
                 "Airflow, not temperature.", color=TEXT, fontsize=14)
    fig.tight_layout(rect=(0, 0, 1, .975))
    fig.savefig(out, facecolor=BG)


def main():
    out = sys.argv[1]
    if sys.argv[2] == "--compare":
        compare(out, sys.argv[3:])
    elif sys.argv[2] == "--symmetry":
        symmetry(out, sys.argv[3:])
    else:
        detail(out, *spec(sys.argv[2]), *(sys.argv[3:4] or []))
    print(out)


if __name__ == "__main__":
    main()
