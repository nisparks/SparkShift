"""Score every matched fine-mesh P22 case against the goals of a part cooler.

python evaluate_part_cooler_r43.py
Reads the matched verification JSONs and per-case dead_spots.json, writes verification_part_cooler_scorecard_r43.json
and images/r43_part_cooler_scorecard.png.

Goals, in priority order (see R43_SWEPT_FEED_REVIEW.md, "Part-cooler scorecard"):
1. Air onto the fresh bead and the print around it (downward L/min, below-tip speed, low-speed spots).
2. The same cooling in every print direction (weakest sector / mean around the nozzle).
3. Little air glancing back up off the print (up / down L/min, r 2-5 mm).
4. Little heat pulled from the bare nozzle (Churchill-Bernstein cylinder estimate; the sock is insulated and is
   reported, not scored).
Airflow, not temperature: the nozzle figure is an engineering estimate, not a thermal simulation.
"""
import glob
import json
import math
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

import build_and_verify_accessories_v26 as acc
from cfd_provenance_r43 import digest

HERE = Path(__file__).resolve().parent
RESULTS = acc.WORK / "cfd" / "results"
LABELS = {
    "r43auditRVMS28fine_bambu_bed": "RVMS",
    "r43auditRVMfineV2_bambu_bed": "RVM",
    "r43auditRVMS40fineV2_bambu_bed": "RVMS 40",
    "r43auditFR1fine_bambu_bed": "FR1",
    "r43auditFR2fine_bambu_bed": "FR2",
    "r43auditFR1H14fine_bambu_bed": "FR1 1.4",
    "r43auditFR1H09fine_bambu_bed": "FR1 0.9",
    "r43auditRC24fine_bambu_bed": "A",
    "r43auditRC36fine_bambu_bed": "B",
    "r43auditAFTCfine": "A aft C",
    "r43auditAFTFfine": "A aft F",
    "r43auditWIDECfine": "A wide C",
    "r43auditWIDEFfine": "A wide F",
}
WEIGHTS = {"delivery": .40, "uniformity": .25, "lift_off": .15, "nozzle_heat": .20}
# Bare nozzle below the sock, as a cylinder in cross-flow; film properties of air near 140 C.
NOZZLE_D_M, T_NOZZLE_C, T_AIR_C = 4.0e-3, 250.0, 35.0
NU_AIR, K_AIR, PR_AIR = 2.8e-5, 0.035, 0.69


def nozzle_watts(speed_ms, area_mm2):
    re = speed_ms * NOZZLE_D_M / NU_AIR
    nu = .3 + .62 * re ** .5 * PR_AIR ** (1 / 3) / (1 + (.4 / PR_AIR) ** (2 / 3)) ** .25 * (
        1 + (re / 282000) ** .625) ** .8
    return nu * K_AIR / NOZZLE_D_M * area_mm2 * 1e-6 * (T_NOZZLE_C - T_AIR_C)


def collect():
    cases, sources = {}, {}
    for path in sorted(HERE.glob("verification_cooling_review_r43*.json")):
        for v in json.loads(path.read_text())["cases"].values():
            if v["case"] in LABELS:
                cases[v["case"]] = v
                sources[v["case"]] = path.name
    rows = {}
    for case, v in cases.items():
        o, ring, hot, arrive = (v["outlets_estimate_lpm"], v["below_tip_ring_speed"], v["hot_part_speed_proxies"],
                                v["arriving_on_print"])
        spots = json.loads((RESULTS / case / "dead_spots.json").read_text())["spots"] if (
            RESULTS / case / "dead_spots.json").exists() else None
        uni = [min(ring[k]["sectors_ms"].values()) / ring[k]["mean_ms"] for k in ("r0p6_2", "r2_4")]
        nozzle = sum(nozzle_watts(hot[k]["mean_ms"], hot[k]["area_mm2"])
                     for k in ("nozzle tip to 1 mm", "nozzle 1 mm to the sock"))
        down = arrive["bead ring r 0.6-2 mm"]["down_lpm"] + arrive["print r 2-5 mm"]["down_lpm"]
        up = arrive["bead ring r 0.6-2 mm"]["up_lpm"] + arrive["print r 2-5 mm"]["up_lpm"]
        rows[LABELS[case]] = {
            "case": case, "source": sources[case], "blower_lpm": v["blower_estimate_lpm"],
            "centre_share_pct": 100 * o["centre"] / sum(o.values()),
            "bead_ring_down_lpm": arrive["bead ring r 0.6-2 mm"]["down_lpm"],
            "print_down_lpm": arrive["print r 2-5 mm"]["down_lpm"], "down_total_lpm": down,
            "up_total_lpm": up, "up_over_down": up / down,
            "ring_0p6_2_mean_ms": ring["r0p6_2"]["mean_ms"], "ring_2_4_mean_ms": ring["r2_4"]["mean_ms"],
            "ring_0p6_2_sectors_ms": ring["r0p6_2"]["sectors_ms"], "ring_2_4_sectors_ms": ring["r2_4"]["sectors_ms"],
            "weakest_sector_over_mean": sum(uni) / 2,
            "spots_bed_plus_0p1_ms": None if spots is None else {
                k: s["heights"]["bed_plus_0.1mm"]["mean_ms"] for k, s in spots.items()},
            "nozzle_tip_ms": hot["nozzle tip to 1 mm"]["mean_ms"], "nozzle_cone_ms": hot["nozzle 1 mm to the sock"]["mean_ms"],
            "sock_ms": hot["sock and heater block"]["mean_ms"], "bare_nozzle_loss_w": nozzle,
        }
    return rows


def score(rows):
    def norm(key, higher=True):
        vals = [r[key] for r in rows.values()]
        lo, hi = min(vals), max(vals)
        return {n: ((r[key] - lo) / (hi - lo) if higher else (hi - r[key]) / (hi - lo)) for n, r in rows.items()}

    delivery = {n: (a + b + c) / 3 for n, a, b, c in zip(
        rows, norm("down_total_lpm").values(), norm("ring_0p6_2_mean_ms").values(), norm("ring_2_4_mean_ms").values())}
    parts = {"delivery": delivery, "uniformity": norm("weakest_sector_over_mean"),
             "lift_off": norm("up_over_down", False), "nozzle_heat": norm("bare_nozzle_loss_w", False)}
    for n in rows:
        rows[n]["scores"] = {k: parts[k][n] for k in parts}
        rows[n]["weighted_score"] = sum(WEIGHTS[k] * parts[k][n] for k in parts)
    return sorted(rows, key=lambda n: -rows[n]["weighted_score"])


def figure(rows, order, out):
    fig, axs = plt.subplots(1, 5, figsize=(22, 5.2))
    panels = [("down_total_lpm", "Air DOWN onto bead + print\nr 0.6-5 mm (L/min), higher better"),
              ("ring_0p6_2_mean_ms", "Air speed just under the nozzle\nr 0.6-2 mm (m/s), higher better"),
              ("weakest_sector_over_mean", "Same in every direction\nweakest sector / mean, higher better"),
              ("up_over_down", "Air glancing back up\nup / down, lower better"),
              ("bare_nozzle_loss_w", "Heat pulled from bare nozzle\nestimate (W), lower better")]
    colours = ["#2ca02c" if n == order[0] else "#1f77b4" if n == "FR1" else "#9aa4b1" for n in order]
    for ax, (key, title) in zip(axs, panels):
        ax.barh(order[::-1], [rows[n][key] for n in order[::-1]], color=colours[::-1])
        ax.set_title(title, fontsize=11)
        ax.grid(axis="x", alpha=.3)
    fig.suptitle("Part-cooler scorecard, matched fine CFD at estimated blower flow. Ranked top to bottom by weighted "
                 f"score ({', '.join(f'{k} {int(w * 100)}%' for k, w in WEIGHTS.items())}). Airflow, not temperature.",
                 fontsize=12)
    fig.tight_layout()
    fig.savefig(out, dpi=120)


def main():
    rows = collect()
    order = score(rows)
    image = HERE / "images" / "r43_part_cooler_scorecard.png"
    figure(rows, order, image)
    report = {
        "ranking": order, "weights": WEIGHTS, "cases": rows,
        "nozzle_model": {"correlation": "Churchill-Bernstein cylinder in cross-flow", "diameter_m": NOZZLE_D_M,
                         "nozzle_c": T_NOZZLE_C, "air_c": T_AIR_C, "nu_m2s": NU_AIR, "k_w_mk": K_AIR, "pr": PR_AIR,
                         "note": "Bare nozzle only; sock speed reported but not scored (silicone insulated)."},
        "image_sha256": digest(image), "generator_sha256": digest(Path(__file__)),
        "caution": "Airflow, not temperature. Weights are a judgement; the ranking of the leader is unchanged by any "
                   "single weight moving +-10 points (checked in sensitivity).",
    }
    sens = {}
    for k in WEIGHTS:
        for d in (-.1, .1):
            w = dict(WEIGHTS)
            w[k] = max(0, w[k] + d)
            t = sum(w.values())
            best = max(rows, key=lambda n: sum(w[j] / t * rows[n]["scores"][j] for j in w))
            sens[f"{k}{d:+.1f}"] = best
    report["sensitivity_leader"] = sens
    out = HERE / "verification_part_cooler_scorecard_r43.json"
    out.write_bytes((json.dumps(report, indent=2) + "\n").encode())
    for n in order:
        r = rows[n]
        print(f"{n:8s} score {r['weighted_score']:.2f} | down {r['down_total_lpm']:5.1f} | r0.6-2 {r['ring_0p6_2_mean_ms']:4.1f}"
              f" | uni {r['weakest_sector_over_mean']:.2f} | up/down {r['up_over_down']:.2f} | nozzle {r['bare_nozzle_loss_w']:.2f} W"
              f" | sock {r['sock_ms']:.1f} | blower {r['blower_lpm']:.0f} | C {r['centre_share_pct']:.0f}%")
    print("sensitivity leader:", sens)


if __name__ == "__main__":
    main()
