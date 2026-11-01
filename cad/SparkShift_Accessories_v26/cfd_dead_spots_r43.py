"""Air speed in the two low-speed spots the user circled on the plan view just below the nozzle tip.

python cfd_dead_spots_r43.py CASE [CASE ...]
Rear spot: X -2..2, Y 19..21 (the rear jet's stagnation line under the side jets' pressure pad).
Front spot: X -1.5..1.5, Y 23.5..26.5 (the nozzle/sock wake).
Sampled on a 0.25 mm grid 0.1, 0.2 and 0.4 mm above the bed; velocity scaled to each case's own blower point.
Writes dead_spots.json in each case's results folder. Airflow only, not temperature.
"""
import json
import sys

import numpy as np

import cfd_cpap_r41 as C
import cfd_nozzle_focus_r43 as N
import cfd_outlet_balance_r43 as B
import cfd_provenance_r43 as V

BED_Z = -79.08
SPOTS = {"rear": (-2.0, 2.0, 19.0, 21.0), "front": (-1.5, 1.5, 23.5, 26.5)}
HEIGHTS = (.1, .2, .4)


def grid(x0, x1, y0, y1, z, step=.25):
    xs, ys = np.meshgrid(np.arange(x0, x1 + 1e-6, step), np.arange(y0, y1 + 1e-6, step))
    return np.c_[xs.ravel(), ys.ravel(), np.full(xs.size, z)]


def summarize(speed):
    return {"mean_ms": float(speed.mean()), "p10_ms": float(np.percentile(speed, 10)),
            "below_5ms_pct": float((speed < 5).mean() * 100)}


def analyse(case):
    factor = V.read_balance(case)["operating_point_1m_hose"]["lpm"] / 180
    g = B.load(case, True)
    out = {"case": case, "velocity_scale": factor, "bed_z_mm": BED_Z, "spots": {}}
    for name, box in SPOTS.items():
        rows = {}
        for dz in HEIGHTS:
            valid, u = N.probe(g, grid(*box, BED_Z + dz))
            if not valid.all():
                raise ValueError(f"{case} {name} +{dz}: {int((~valid).sum())} probe points outside the fluid")
            rows[f"bed_plus_{dz:g}mm"] = summarize(np.linalg.norm(u, axis=1) * factor)
        out["spots"][name] = {"box_xy_mm": box, "heights": rows}
    out["limitations"] = "Air speed only, 0.1 mm off a no-slip bed is partly boundary layer; not temperature."
    (C.results_dir(case) / "dead_spots.json").write_text(json.dumps(out, indent=2) + "\n")
    return out


if __name__ == "__main__":
    for case in sys.argv[1:]:
        r = analyse(case)
        print(case, " ".join(f"{k}+{h[9:-2]}:{v['mean_ms']:.1f}/{v['p10_ms']:.1f}"
                             for k, s in r["spots"].items() for h, v in s["heights"].items()), flush=True)
