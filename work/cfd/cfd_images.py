"""Images and summary for the CPAP duct CFD (session scratch while developing)."""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cfd_post import *  # noqa: E402,F403

OUT = Path(__file__).parent / "images"
OUT.mkdir(exist_ok=True)
LABELS = {"r41_bambu": "Revision 41, Bambu hotend", "r41_redlizard": "Revision 41, Red Lizard hotend",
          "r41_bambu_bed": "Revision 41, Bambu, flat print 0.2 mm under the nozzle",
          "released_bambu": "Released duct (revision 40), Bambu hotend", "r41_bambu_fine": "Revision 41, finer mesh"}


def stage_time(case, lpm):
    stages = json.loads((CASES / case / "stages.json").read_text())["stages"]
    return min(stages, key=lambda s: abs(s["lpm"] - lpm))


def nozzle_sections(case, lpm, out, vmax=90):
    s = stage_time(case, lpm)
    g = internal(case, s["end"])
    fig, axs = plt.subplots(2, 2, figsize=(15, 10.5))
    w_xz = (-24, 24, -92, -64)
    section_plot(axs[0, 0], g, "y", NOZZLE_Y, w_xz, vmax=vmax,
                 title=f"Across the nozzle (Y {NOZZLE_Y}): both jets, {s['lpm']:.0f} L/min")
    section_plot(axs[0, 1], g, "z", -75.1, (-24, 24, 4, 42), vmax=vmax,
                 title="Seen from above at jet mid-height (Z -75.1)")
    section_plot(axs[1, 0], g, "z", TIP_Z - 0.1, (-24, 24, 4, 42), vmax=vmax / 2,
                 title=f"At the fresh bead, 0.1 mm under the nozzle tip (Z {TIP_Z - 0.1:.2f})")
    section_plot(axs[1, 1], g, "y", NOZZLE_Y, w_xz, field="ti", vmax=20, cmap="magma", arrows=False,
                 title="Turbulence across the nozzle (k-omega SST)")
    for ax, mark in ((axs[0, 0], (0, TIP_Z)), (axs[0, 1], (0, NOZZLE_Y)), (axs[1, 0], (0, NOZZLE_Y)),
                     (axs[1, 1], (0, TIP_Z))):
        ax.plot([mark[0]], [mark[1]], "w+", ms=10, mew=2)
    fig.suptitle(f"{LABELS.get(case, case)}: air speed around the nozzle at {s['lpm']:.0f} L/min "
                 "(grey = solid: P22, hotend, tool)", fontsize=13)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def channel_section(case, lpm, out):
    s = stage_time(case, lpm)
    g = internal(case, s["end"])
    fig, axs = plt.subplots(2, 1, figsize=(15, 11))
    w = (-50, 34, -82, -44)
    section_plot(axs[0], g, "x", 16.0, w, vmax=60, title="Air speed along the right-hand side channel (X 16)")
    section_plot(axs[1], g, "x", 16.0, w, field="p", arrows=False, cmap="coolwarm",
                 title="Static pressure above the room (Pa) along the same cut")
    fig.suptitle(f"{LABELS.get(case, case)} at {s['lpm']:.0f} L/min", fontsize=13)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def streamline_view(case, lpm, out, vmax=90):
    s = stage_time(case, lpm)
    g = internal(case, s["end"])
    meta = json.loads((CASES / case / "domain.json").read_text())
    lines = streamlines(g, inlet_seeds(meta), max_len=700)
    walls = boundary(case, s["end"], "walls")
    table = lut(vmax)
    actors = [tube_actor(lines, table, 0.18),
              surface_actor(walls, opacity=0.10, clip=(-24, 24, -62, 31, -80, 96))]
    render(actors, (-250, 230, 140), (0, -18, 2), (0, 0, 1), out, size=(1300, 1500),
           parallel_scale=104, bar=scalar_bar(table, "air speed (m/s)"))
    # close-up of the outlet: seeds across both side channels beside the hotend (Y 5)
    seeds = [(sx * x, 5.0, z) for sx in (-1, 1) for x in np.linspace(13.2, 20.6, 7) for z in np.linspace(-69.8, -58.6, 8)]
    near = streamlines(g, seeds, max_len=120)
    actors = [tube_actor(near, table, 0.10),
              surface_actor(walls, opacity=0.16, clip=(-24, 24, 2, 34, -82, -52))]
    render(actors, (-120, 170, 60), (0, 20, -74), (0, 0, 1), str(out).replace(".png", "_outlet.png"),
           size=(1500, 1100), parallel_scale=17, bar=scalar_bar(table, "air speed (m/s)"))


def system_curve(analyses, out):
    fig, ax = plt.subplots(figsize=(11, 7))
    q = np.linspace(0, 360, 200)
    ax.plot(q, blower_pa(q), "k-", lw=2, label="WS7040 blower, 100 % PWM (Wonsmart curve)")
    ax.plot(q, blower_pa(q) - hose_pa(q), "k--", lw=1.5,
            label=f"... minus {HOSE['length_m']:.0f} m of Ø{HOSE['bore_mm']:.0f} mm CPAP hose")
    colours = {"r41_bambu": "tab:blue", "r41_redlizard": "tab:orange", "r41_bambu_bed": "tab:green",
               "released_bambu": "tab:red", "r41_bambu_fine": "tab:purple"}
    ops = {}
    for case, rows in analyses.items():
        if len(rows) < 2:
            ax.plot([r["lpm"] for r in rows], [r["inlet_total_pa"] for r in rows], "D", color=colours.get(case),
                    label=f"{LABELS.get(case, case)} (CFD)")
            continue
        c, n = fit_power(rows)
        ax.plot(q[1:], c * q[1:] ** n, "-", color=colours.get(case), lw=1.6)
        ax.plot([r["lpm"] for r in rows], [r["inlet_total_pa"] for r in rows], "o", color=colours.get(case),
                label=f"{LABELS.get(case, case)} (CFD)")
        op = operating_point(rows)
        ops[case] = op
        ax.plot([op["lpm"]], [op["duct_pa"]], "*", ms=16, color=colours.get(case), mec="k")
        ax.annotate(f"{op['lpm']:.0f} L/min", (op["lpm"], op["duct_pa"]), textcoords="offset points",
                    xytext=(8, 8), color=colours.get(case), fontsize=10, weight="bold")
    ax.set_xlim(0, 360)
    ax.set_ylim(0, 7500)
    ax.set_xlabel("air flow (L/min)")
    ax.set_ylabel("total pressure needed at P20's spigot / available (Pa)")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper right", fontsize=9)
    ax.set_title("Duct system curves (CFD, k-omega SST) against the blower: stars mark where they meet")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
    return ops


def comparison(a, lpm_a, b, lpm_b, out, vmax=90):
    fig, axs = plt.subplots(2, 2, figsize=(15, 10.5))
    for col, (case, lpm) in enumerate(((a, lpm_a), (b, lpm_b))):
        s = stage_time(case, lpm)
        g = internal(case, s["end"])
        section_plot(axs[0, col], g, "y", NOZZLE_Y, (-24, 24, -92, -64), vmax=vmax,
                     title=f"{LABELS.get(case, case)}\nacross the nozzle at {s['lpm']:.0f} L/min")
        section_plot(axs[1, col], g, "z", -75.1, (-24, 24, 4, 42), vmax=vmax,
                     title="seen from above at jet mid-height (Z -75.1)")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def convergence_and_losses(cases, analyses, ops, out):
    fig, axs = plt.subplots(1, 2, figsize=(16, 6.5))
    for case in cases:
        h = inlet_history(case)
        axs[0].plot(h[:, 0], h[:, 2] * RHO, lw=1.2, label=LABELS.get(case, case))
    axs[0].set_xlabel("solver iteration (the inlet flow steps 180 -> 120 -> 240 L/min)")
    axs[0].set_ylabel("total pressure at P20's spigot (Pa)")
    axs[0].set_title("Convergence: inlet total pressure through each flow stage")
    axs[0].grid(True, alpha=0.3)
    axs[0].legend(fontsize=8)
    width = 0.8 / max(len(cases), 1)
    for i, case in enumerate(cases):
        rows = analyses[case]
        row = min(rows, key=lambda r: abs(r["lpm"] - ops.get(case, {"lpm": 180})["lpm"]))
        lb = row["loss_breakdown"]
        names = [s["section"] for s in lb]
        drops = [lb[k]["total_pressure_pa"] - lb[k + 1]["total_pressure_pa"] for k in range(len(lb) - 1)]
        drops.append(lb[-1]["total_pressure_pa"])          # what leaves the jets: their kinetic energy and p
        labels = [f"{names[k]} -> {names[k + 1]}" for k in range(len(lb) - 1)] + ["leaving the jets"]
        x = np.arange(len(drops)) + i * width
        axs[1].bar(x, drops, width, label=f"{LABELS.get(case, case)} at {row['lpm']:.0f} L/min")
    axs[1].set_xticks(np.arange(len(labels)) + width * (len(cases) - 1) / 2)
    axs[1].set_xticklabels(labels, rotation=28, ha="right", fontsize=8)
    axs[1].set_ylabel("total pressure lost (Pa)")
    axs[1].set_title("Where the pressure goes, section by section")
    axs[1].grid(True, axis="y", alpha=0.3)
    axs[1].legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


if __name__ == "__main__":
    what = sys.argv[1]
    if what == "sections":
        case, lpm = sys.argv[2], float(sys.argv[3])
        nozzle_sections(case, lpm, OUT / f"{case}_nozzle_{lpm:.0f}.png")
        channel_section(case, lpm, OUT / f"{case}_channel_{lpm:.0f}.png")
    elif what == "streamlines":
        case, lpm = sys.argv[2], float(sys.argv[3])
        streamline_view(case, lpm, OUT / f"{case}_streamlines_{lpm:.0f}.png")
    elif what == "compare":
        comparison(sys.argv[2], float(sys.argv[3]), sys.argv[4], float(sys.argv[5]),
                   OUT / f"compare_{sys.argv[2]}_{sys.argv[4]}.png")
    elif what == "system":
        an = {c: json.loads((CASES / c / "analysis.json").read_text()) for c in sys.argv[2:]}
        ops = system_curve(an, OUT / "system_curves.png")
        convergence_and_losses(list(an), an, ops, OUT / "convergence_losses.png")
        print(json.dumps(ops, indent=1))
