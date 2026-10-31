"""R43 study: analyse the outlet variants' CFD (session scratch). Wraps cfd_cpap_r41_post with the jet window and
nozzle box widened for the longer jets, and adds ring speeds just above the fresh bead and an annulus mean.

Usage: python r43_analyse.py <case> [<case> ...]     (results in WORK/cfd/results/<case>)
"""
import json
import math
import sys
from pathlib import Path

HERE = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(HERE))
import os  # noqa: E402
os.chdir(HERE)

import numpy as np  # noqa: E402

import cfd_cpap_r41 as C  # noqa: E402
import cfd_cpap_r41_post as post  # noqa: E402

R41_WINDOW = C.JET_WINDOW
LONG_WINDOW = (12.3, 29.0, -77.2, -73.3)
BOX = (-10.15, 10.15, 12.0, 29.5, -79.0, -72.0)
N_EXP = 1.983                                    # R41's fitted exponent, dP ~ Q^n


def annulus(g, z, r0=1.0, r1=5.0, n_r=9, n_t=72):
    out = []
    for r in np.linspace(r0, r1, n_r):
        pts = [(r * math.cos(2 * math.pi * i / n_t), C.NOZZLE_Y + r * math.sin(2 * math.pi * i / n_t), z) for i in range(n_t)]
        u, ok = post.probe(g, pts)
        s = np.linalg.norm(u, axis=1)
        out.append((r, s, ok))
    num = sum((s[ok] * r).sum() for r, s, ok in out)
    den = sum(ok.sum() * r for r, s, ok in out)
    # sector means at r 2 mm: behind (-Y), in front (+Y), and either side (+-X)
    r2 = [o for o in out if abs(o[0] - 2.0) < 0.26][0]
    ang = np.array([i * 360 / n_t for i in range(n_t)])
    sect = {}
    for k, (a0, a1) in {"right": (-45, 45), "front": (45, 135), "left": (135, 225), "back": (225, 315)}.items():
        m = ((ang - a0) % 360 < (a1 - a0)) & r2[2]
        sect[k] = round(float(r2[1][m].mean()), 2) if m.any() else None
    return {"z_mm": round(z, 2), "area_mean_ms_r1_5": round(float(num / den), 2), "sectors_r2_ms": sect}


def operating(p180):
    rows = [{"lpm": 180.0, "inlet_total_pa": p180}, {"lpm": 120.0, "inlet_total_pa": p180 * (120 / 180) ** N_EXP}]
    return C.operating_point(rows)


def analyse(name):
    meta = json.loads((C.results_dir(name) / "domain.json").read_text())
    C.JET_WINDOW = LONG_WINDOW if name.startswith("r43") else R41_WINDOW
    st = [s for s in post.stages(name) if abs(s["lpm"] - 180.0) < 0.5][0]
    row = post.analyse(name, st["end"], st["lpm"], meta["bed"])
    row["nozzle_box_outflow_lpm"] = post.box_outflow(post.internal(name, st["end"]), BOX)
    g = post.internal(name, st["end"])
    row["annulus"] = [annulus(g, C.NOZZLE_TIP_Z - 0.1), annulus(g, C.NOZZLE_TIP_Z + 0.3)]
    row["operating_point_1m_hose"] = operating(row["inlet_total_pa"])
    (C.results_dir(name) / "analysis_r43.json").write_text(json.dumps(row, indent=1))
    return row


def brief(name, row):
    j = row["jets"]
    op = row["operating_point_1m_hose"]
    b = row["bead_rings"]
    sh = row["nozzle_box_outflow_lpm"]["share_pct"]
    an = row["annulus"]
    beads = "/".join("%.1f" % x["mean_ms"] for x in b)
    return (f"{name:22s} dP180 {row['inlet_total_pa']:7.0f} Pa | op {op['lpm']:5.1f} L/min | jets "
            f"{j['left']['area_mm2'] + j['right']['area_mm2']:5.1f} mm2 {j['left']['mean_ms']:5.1f}/{j['left']['max_ms']:5.1f} m/s "
            f"{j['left']['angle_below_horizontal_deg']:4.1f} deg | bead r.8/1.2/2/3/5 "
            f"{beads} | annulus z-0.1 {an[0]['area_mean_ms_r1_5']:.1f} "
            f"z+0.3 {an[1]['area_mean_ms_r1_5']:.1f} sectors {an[0]['sectors_r2_ms']} | out {sh}")


if __name__ == "__main__":
    for n in sys.argv[1:]:
        print(brief(n, analyse(n)), flush=True)
