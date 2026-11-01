"""Do the side jets and the rear jet work together under the nozzle, or against each other?

python cfd_flow_opposition_r43.py CASE [CASE ...]
Probes the solved field in the gap between the nozzle tip and the print (and 1 mm above the tip) and reports:
  centreline: Uy and Uz along X 0 from Y 12 to 34 (+Y is forward, away from the rear slot);
  stagnation_y: where the centreline Uy first turns negative in front of the rear slot (air pushed back);
  plane flux: net and reverse (-Y) volume flux through X-Z planes behind, at and in front of the nozzle;
  side inflow: inward |X| flux through planes X +-3 behind the nozzle (side air turned toward the rear jet).
Velocities scaled to the operating flow like the other r43 metrics. Airflow only, not temperature.
"""
import json
import sys

import numpy as np

import cfd_cpap_r41 as C
import cfd_outlet_balance_r43 as B
import cfd_nozzle_focus_r43 as N
import cfd_provenance_r43 as V

TIP, BED, NY = C.NOZZLE_TIP_Z, C.NOZZLE_TIP_Z - C.BED_GAP, C.NOZZLE_Y
STEP = .05


def plane_flux(g, factor, normal, at, a_lims, z_lims):
    a = np.arange(a_lims[0] + STEP / 2, a_lims[1], STEP)
    z = np.arange(z_lims[0] + STEP / 2, z_lims[1], STEP)
    A, Z = np.meshgrid(a, z)
    pts = (np.c_[A.ravel(), np.full(A.size, at), Z.ravel()] if normal == "y"
           else np.c_[np.full(A.size, at), A.ravel(), Z.ravel()])
    ok, u = N.probe(g, pts)
    un = np.where(ok, u[:, 1 if normal == "y" else 0], 0.0) * factor
    da = STEP * STEP * 1e-6 * 60000.0                              # m2 -> L/min per m/s
    return {"net_lpm": float(un.sum() * da), "forward_lpm": float(un[un > 0].sum() * da),
            "reverse_lpm": float(-un[un < 0].sum() * da), "valid_fraction": float(ok.mean())}


def analyse(case):
    report = V.read_balance(case)
    factor = report["operating_point_1m_hose"]["lpm"] / 180.0
    g = B.load(case, True)
    out = {"case": case, "velocity_factor": factor}
    ys = np.arange(12.0, 34.01, .1)
    for label, z in (("below_tip_0p1", TIP - .1), ("tip_plus_1", TIP + 1.0)):
        ok, u = N.probe(g, np.c_[np.zeros_like(ys), ys, np.full_like(ys, z)])
        uy, uz = np.where(ok, u[:, 1], np.nan) * factor, np.where(ok, u[:, 2], np.nan) * factor
        behind = (ys > 14.5) & (ys < NY - .2) & ok
        neg = np.where(behind & (uy < 0))[0]
        out[label] = {"y": ys[::10].round(2).tolist(), "uy": np.round(uy[::10], 2).tolist(),
                      "uz": np.round(uz[::10], 2).tolist(),
                      "mean_uy_behind": float(np.nanmean(uy[behind])),
                      "stagnation_y": float(ys[neg[0]]) if len(neg) else None}
    gap = (BED + 1e-3, TIP)
    out["y_planes_gap"] = {f"{y:.1f}": plane_flux(g, factor, "y", y, (-6, 6), gap)
                           for y in (16.0, 18.0, 20.0, NY - 2.0, NY, NY + 2.0, NY + 4.0)}
    out["y_planes_tip_band"] = {f"{y:.1f}": plane_flux(g, factor, "y", y, (-6, 6), (BED + 1e-3, TIP + 2.0))
                                for y in (18.0, 20.0, NY - 2.0)}
    for side, x in (("left", -3.0), ("right", 3.0)):
        f = plane_flux(g, factor, "x", x, (14.5, NY), (BED + 1e-3, TIP + 2.0))
        sign = 1 if side == "left" else -1                        # inward = toward X 0
        out[f"side_inflow_behind_{side}"] = {"inward_lpm": f["forward_lpm"] if sign > 0 else f["reverse_lpm"],
                                             "outward_lpm": f["reverse_lpm"] if sign > 0 else f["forward_lpm"],
                                             "valid_fraction": f["valid_fraction"]}
    return out


if __name__ == "__main__":
    rows = [analyse(c) for c in sys.argv[1:]]
    for r in rows:
        (C.results_dir(r["case"]) / "flow_opposition.json").write_text(json.dumps(r, indent=2) + "\n")
        b, t = r["below_tip_0p1"], r["tip_plus_1"]
        print(f"\n{r['case']}")
        print(f"  centre Uy behind nozzle: below tip {b['mean_uy_behind']:.2f} m/s, stagnation Y {b['stagnation_y']};"
              f" tip+1 {t['mean_uy_behind']:.2f}, stagnation Y {t['stagnation_y']}")
        for k, v in r["y_planes_gap"].items():
            print(f"  gap Y {k}: net {v['net_lpm']:+.2f}  fwd {v['forward_lpm']:.2f}  rev {v['reverse_lpm']:.2f} L/min")
        for k, v in r["y_planes_tip_band"].items():
            print(f"  gap+2mm Y {k}: net {v['net_lpm']:+.2f}  fwd {v['forward_lpm']:.2f}  rev {v['reverse_lpm']:.2f}")
        for s in ("left", "right"):
            v = r[f"side_inflow_behind_{s}"]
            print(f"  {s} X+-3 behind nozzle: inward {v['inward_lpm']:.2f}  outward {v['outward_lpm']:.2f} L/min")
