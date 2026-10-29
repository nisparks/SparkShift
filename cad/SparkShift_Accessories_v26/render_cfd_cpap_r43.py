"""Revision 43 CPAP CFD figures (run after `cfd_cpap_r43.py analyse` for each case).

89: the design search: system curves against the blower; each design's blower flow against the air it puts over the
    print within 5 and 14 mm of the nozzle; the speed over a print round the nozzle.
90: revision 41 and revision 43 side by side at the nozzle: across it, along a jet, from above at jet height, and over
    a print.
91: why the jets weren't made longer: revision 41 against the long-jets study, along the hotend slot's centre.
92: streamlines through revision 43's outlet, seen from the front.
94: the review's jet ends, print surface 0.2 mm under the tip: revision 41, revision 43's first version, the round at
    full size to the front wall and revision 43's run-out, across the nozzle, across the jets' front end and just
    over the print, with the near-nozzle figures against revision 41.

Run: python render_cfd_cpap_r43.py
"""
import json
import math

import numpy as np
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import cfd_cpap_r41 as C  # noqa: E402
import cfd_cpap_r41_post as P  # noqa: E402
import cfd_cpap_r43 as A  # noqa: E402
import render_cfd_cpap_r41 as F  # noqa: E402
from build_modular_toolhead import ROOT  # noqa: E402

IMAGES = ROOT / "images"
R41, R41_BED, R41_RL = "r41bm_bambu", "r41bm_bambu_bed", "r41bm_redlizard"
R43, R43_BED, R43_RL = "r43_bambu", "r43_bambu_bed", "r43_redlizard"
STUDIES = [(R41_BED, "Revision 41", "tab:blue"), ("r43long_bambu_bed", "Jets run back to Y13", "tab:red"),
           ("r43rear_bambu_bed", "... front 4 mm closed", "tab:orange"), ("r43bell_bambu_bed", "Bell-mouth r 2.4", "tab:purple"),
           ("r43pocket_bambu_bed", "Lower floor", "tab:olive"), ("r43front_bambu_bed", "Floor lower where flat", "tab:cyan"),
           ("r43frontbell_bambu_bed", "... with the bell-mouth", "tab:pink"),
           ("r43low_bambu_bed", "Flat pocket (not printable)", "tab:gray"),
           ("r43combo_bambu_bed", "Flat pocket, bell-mouth (not printable)", "tab:brown"),
           ("r43v1_bambu_bed", "Revision 43's first version", "goldenrod"),
           ("r43full_bambu_bed", "Review: round at full size to the front wall", "darkorange"),
           (R43_BED, "Revision 43: lower floor, bell-mouth", "tab:green")]
PROFILES = (R41_BED, "r43long_bambu_bed", "r43pocket_bambu_bed", "r43front_bambu_bed", "r43frontbell_bambu_bed", R43_BED)
LABEL_AT = {R41_BED: (-8, 8, "right"), "r43bell_bambu_bed": (8, -14, "left"), "r43frontbell_bambu_bed": (-8, 4, "right"),
            R43_BED: (8, 9, "left"), "r43full_bambu_bed": (10, -46, "left")}   # label offsets (points) where the defaults collide
W_XZ_BED = (-24, 24, -80, -64)


def rows(name):
    return A.rows_of(name)


def at180(name):
    return next(r for r in rows(name) if r["lpm"] == 180.0)


def op(name):
    return A.operating(rows(name))


def grid(name, lpm=180.0):
    s = F.stage(name, lpm)
    return P.internal(name, s["end"]), s


def image_89():
    fig, axs = plt.subplots(1, 3, figsize=(25, 7.6))
    q = np.linspace(1, 360, 300)
    ax = axs[0]
    ax.plot(q, C.blower_pa(q), "k-", lw=2, label="WS7040 blower, 100 % PWM")
    ax.plot(q, C.blower_pa(q) - C.hose_pa(q), "k--", lw=1.4, label="... less 1 m of Ø19 CPAP hose")
    for name, label, colour in ((R41, "Revision 41, Bambu", "tab:blue"), (R43, "Revision 43, Bambu", "tab:green"),
                                (R41_RL, "Revision 41, Red Lizard", "tab:cyan"), (R43_RL, "Revision 43, Red Lizard", "tab:olive")):
        if not (C.results_dir(name) / "analysis_r43.json").exists():
            continue
        rs = rows(name)
        c, k = C.fit_power(rs) if len(rs) > 1 else (rs[0]["inlet_total_pa"] / 180.0 ** A.N_EXP, A.N_EXP)
        ax.plot([r["lpm"] for r in rs], [r["inlet_total_pa"] for r in rs], "o", color=colour)
        ax.plot(q, c * q ** k, "-" if "Bambu" in label else ":", color=colour, lw=1.6, label=label)
        o = A.operating(rs)
        ax.plot([o["lpm"]], [o["duct_pa"]], "*", ms=17, color=colour, mec="k")
        if "Bambu" in label:   # the Red Lizard's operating points fall on the Bambu's
            ax.annotate(f"{o['lpm']:.0f} L/min", (o["lpm"], o["duct_pa"]), textcoords="offset points",
                        xytext=(-78, 6) if "41" in label else (10, -16), color=colour, fontsize=10, weight="bold")
    ax.set_xlim(0, 360)
    ax.set_ylim(0, 7000)
    ax.set_xlabel("air flow (L/min)")
    ax.set_ylabel("total pressure at P20's spigot (Pa)")
    ax.set_title("Duct system curves (CFD) against the blower; stars: where they meet")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=9, loc="upper right")

    ax = axs[1]
    names = [s for s in STUDIES if (C.results_dir(s[0]) / "analysis_r43.json").exists()]
    base = at180(R41_BED)["over_print"]["disc_mean_speed_0.3mm_over_ms"]
    base_op = op(R41_BED)["lpm"]
    for n, label, colour in names:
        f = op(n)["lpm"] / base_op
        disc = at180(n)["over_print"]["disc_mean_speed_0.3mm_over_ms"]
        x = 100 * (f - 1)
        near, far = (100 * (disc[r] * f / base[r] - 1) for r in ("r5_mm", "r14_mm"))
        ax.plot([x, x], [far, near], "-", color=colour, lw=1.2, alpha=0.7)
        ax.plot([x], [near], "o", ms=11 if n in (R41_BED, R43_BED) else 8, color=colour, mec="k")
        ax.plot([x], [far], "o", ms=8, mfc="white", mec=colour, mew=1.8)
        dx, dy, ha = LABEL_AT.get(n, (7, 4, "left"))
        ax.annotate(label, (x, near), textcoords="offset points", xytext=(dx, dy), ha=ha, fontsize=8.5, color=colour)
    ax.axhline(0, color="k", lw=0.8)
    ax.axvline(0, color="k", lw=0.8)
    ax.set_xlabel("blower flow against revision 41, 1 m hose (%)")
    ax.set_ylabel("air speed 0.3 mm over the print, area mean, against revision 41 (%)")
    ax.set_title("The design search: filled, within 5 mm of the nozzle; hollow, within 14 mm")
    ax.grid(True, alpha=0.3)

    ax = axs[2]
    radii = ("r2_mm", "r3_mm", "r5_mm", "r7_mm", "r10_mm", "r14_mm")
    rr = [float(r[1:-3]) for r in radii]
    for n, label, colour in [s for s in names if s[0] in PROFILES]:
        f = op(n)["lpm"] / 180.0
        sp = at180(n)["over_print"]["speed_0.3mm_over_ms"]
        ax.plot(rr, [sp[r] * f for r in radii], "o-", color=colour, label=f"{label}, {op(n)['lpm']:.0f} L/min")
    ax.set_xlabel("distance from the nozzle axis (mm)")
    ax.set_ylabel("mean air speed 0.3 mm over the print (m/s)")
    ax.set_xlim(0, 15)
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8.5)
    ax.set_title("Over the print, at each design's blower flow (1 m hose)")
    fig.tight_layout()
    return F.save(fig, "89_cfd_r43_design_search.png")


def image_90():
    fig, axs = plt.subplots(4, 2, figsize=(16, 22))
    for col, (open_case, bed_case, tag) in enumerate(((R41, R41_BED, "Revision 41"), (R43, R43_BED, "Revision 43"))):
        g, s = grid(open_case)
        p = at180(open_case)["inlet_total_pa"]
        F.section(axs[0, col], g, "y", C.NOZZLE_Y, F.W_XZ,
                  title=f"{tag}, Bambu, {s['lpm']:.0f} L/min ({p / 1000:.2f} kPa at the spigot): across the nozzle")
        F.section(axs[1, col], g, "x", 10.9, (12, 32, -79, -69),
                  title=f"{tag}: along the right jet, under the wall (X10.9); the nozzle is at Y{C.NOZZLE_Y}")
        F.section(axs[2, col], g, "z", -75.2, F.W_XY, title=f"{tag}: from above at jet height (Z-75.2)")
        gb, sb = grid(bed_case)
        F.section(axs[3, col], gb, "y", C.NOZZLE_Y, W_XZ_BED, title=f"{tag}: print surface 0.2 mm under the tip, across the nozzle")
        F.mark(axs[0, col], "xz")
        F.mark(axs[2, col], "xy")
        F.mark(axs[3, col], "xz")
    fig.suptitle("Air speed at 180 L/min (speeds scale with flow; revision 43's blower gives it more). Grey: solid", fontsize=13)
    fig.tight_layout()
    return F.save(fig, "90_cfd_r43_nozzle_vs_r41.png")


def image_91():
    fig, axs = plt.subplots(2, 2, figsize=(17, 11))
    for col, (name, tag) in enumerate(((R41_BED, "Revision 41"), ("r43long_bambu_bed", "Study: jets run back to Y13"))):
        g, s = grid(name)
        F.section(axs[0, col], g, "x", 0.0, (6, 36, -80, -60),
                  title=f"{tag}, print surface: along the slot's centre (X0); the hotend is grey, the probe at the left")
        F.section(axs[1, col], g, "z", -75.2, F.W_XY, title=f"{tag}: from above at jet height (Z-75.2)")
        F.mark(axs[1, col], "xy")
        axs[0, col].plot([C.NOZZLE_Y], [C.NOZZLE_TIP_Z], "w+", ms=10, mew=2)
    fig.suptitle("The longer jets blow into the gap behind the hotend and the air goes up, not over the print (180 L/min)",
                 fontsize=13)
    fig.tight_layout()
    return F.save(fig, "91_cfd_r43_long_jets_study.png")


def image_92():
    out = []
    for name, tag in ((R41, "Revision 41"), (R43, "Revision 43")):
        g, s = grid(name)
        walls = P.boundary(name, s["end"], "walls")
        near = [(sx * x, 5.0, z) for sx in (-1, 1) for x in np.linspace(13.2, 20.6, 6) for z in np.linspace(-69.8, -58.6, 7)]
        path = IMAGES / f"_cfd92_{tag[-2:]}.png"
        F.render([F.streamlines(g, near, 120), F.surface(walls, (-24, 24, 10, 34, -82, -62), 0.16)],
                 (0, 200, -110), (0, 22, -76), 15, (1300, 1300), path, f"{tag}: the outlet from the front, {s['lpm']:.0f} L/min")
        out.append(path)
    a, b = Image.open(out[0]), Image.open(out[1])
    sheet = Image.new("RGB", (a.width + b.width, max(a.height, b.height)), "white")
    sheet.paste(a, (0, 0))
    sheet.paste(b, (a.width, 0))
    path = IMAGES / "92_cfd_r43_streamlines.png"
    sheet.save(path)
    for t in out:
        t.unlink()
    return path


REVIEW = [(R41_BED, "Revision 41", None), ("r43v1_bambu_bed", "Revision 43's first version:\nround stops square at Y26.2", "tab:gray"),
          ("r43full_bambu_bed", "The review's first pass:\nround at full size to the front wall", "tab:orange"),
          (R43_BED, "Revision 43: the round eases out\nover the jet's last 3 mm", "tab:green")]


def image_94():
    fig = plt.figure(figsize=(26, 25))
    gs = fig.add_gridspec(4, 4, height_ratios=[1.0, 1.0, 1.15, 0.8])
    for col, (name, label, _) in enumerate(REVIEW):
        g, s = grid(name)
        ax = fig.add_subplot(gs[0, col])
        F.section(ax, g, "y", C.NOZZLE_Y, W_XZ_BED, title=f"{label}\nacross the nozzle (Y{C.NOZZLE_Y})")
        F.mark(ax, "xz")
        F.section(fig.add_subplot(gs[1, col]), g, "y", 26.6, (5, 19, -80, -67),
                  title="the right jet's front end (Y26.6); the side channel is at the right")
        ax = fig.add_subplot(gs[2, col])
        F.section(ax, g, "z", C.NOZZLE_TIP_Z + 0.1, (-16, 16, 8, 37), vmax=60.0, arrows=False,
                  title="0.3 mm over the print, from above (front at the top)")
        F.mark(ax, "xy")
        del g
    search = json.loads((ROOT / A.REPORT).read_text())["design_search_vs_r41"]["cases"]
    metrics = [("blower_flow_pct", "blower flow"), ("pressure_at_180_pct", "duct pressure at 180 L/min"),
               ("air_over_print_within_5mm_pct", "air over the print\nwithin 5 mm"),
               ("air_over_print_within_10mm_pct", "within 10 mm"), ("air_over_print_within_14mm_pct", "within 14 mm")]
    ax = fig.add_subplot(gs[3, :])
    x = np.arange(len(metrics))
    for k, (name, label, colour) in enumerate(REVIEW[1:]):
        vals = [search[name][m] for m, _ in metrics]
        bars = ax.bar(x + (k - 1) * 0.26, vals, 0.26, color=colour, label=label.replace("\n", " "))
        for b, v in zip(bars, vals):
            ax.annotate(f"{v:+.1f}", (b.get_x() + b.get_width() / 2, v), textcoords="offset points",
                        xytext=(0, 4 if v >= 0 else -14), ha="center", fontsize=10)
    ax.axhline(0, color="k", lw=0.8)
    ax.set_xticks(x)
    ax.set_xticklabels([m[1] for m in metrics], fontsize=11)
    ax.set_ylabel("against revision 41 (%)", fontsize=11)
    ax.set_title("Against revision 41, each at its own blower flow (1 m hose); lower duct pressure is less restrictive",
                 fontsize=12)
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=10, loc="lower left")
    fig.suptitle("The jets' front end, Bambu, print surface 0.2 mm under the tip: air speed at 180 L/min "
                 "(grey: solid; +: the nozzle)", fontsize=15)
    fig.tight_layout()
    fig.savefig(IMAGES / "94_cfd_r43_review_jet_ends.png", dpi=72)
    plt.close(fig)
    return IMAGES / "94_cfd_r43_review_jet_ends.png"


def main():
    for f in (image_89, image_90, image_91, image_92, image_94):
        print(f(), flush=True)


if __name__ == "__main__":
    main()
