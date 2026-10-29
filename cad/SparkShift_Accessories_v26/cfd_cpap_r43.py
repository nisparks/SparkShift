"""Revision 43 CPAP CFD: P22's jets on a lower floor with a larger bell-mouth against revision 41's, with the same
model, mesh and solver as cfd_cpap_r41.py (only P22 changes: the domain is built with `cfd_cpap_r41.py domain <name>
--p22 <brep>`), and the studies that led to them (jets run back to Y13, with and without their front 4 mm; the lower
floor alone and only where flat, with and without the bell-mouth; the bell-mouth alone; a first, unprintable flat
pocket; and, from the review in Fusion, the rib, the round's back and front ends, its foot faded, and the round at
full size to the front wall against its run-out: r43_parts.py).

What is compared, per case at 180 L/min (and the system curve where a case steps through 180/120/240 L/min):
- the total pressure at P20's spigot, the blower's operating point with 1 m of hose, and where the pressure goes;
- each jet's flow, area, speed and direction;
- the air at the nozzle: the mean speed round circles about the nozzle axis 0.1 mm under the tip, and the
  area-mean speed over a 1-5 mm annulus 0.1 mm under the tip and 0.3 mm over it, by quarter;
- over a print surface 0.2 mm under the tip: the air flowing out along it in its first 1 mm through cylinders about
  the nozzle axis, and the speed 0.3 mm over it;
- where the jets' air leaves the space round the nozzle (front, back, up, down).
Single-flow cases take the operating point from dP ~ Q^1.983 (revision 41's fit).

Usage (from this folder, after the runs; results in WORK/cfd/results/<case>):
  python cfd_cpap_r43.py brep                       write revision 43's P22 and the long-jets study for the domains
  python cfd_cpap_r43.py analyse <case> [<case>..]  one JSON per case (analysis_r43.json)
  python cfd_cpap_r43.py report                     verification_cfd_cpap_r43.json
"""
import argparse
import json
import math
import sys

import numpy as np

import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
from build_modular_toolhead import ROOT

REPORT = "verification_cfd_cpap_r43.json"
R41_WINDOW = C.JET_WINDOW
R43_WINDOW = (12.3, 29.0, -77.2, -73.3)          # the long jets at |X| 10.3 (the heel wall is solid at Y11.85-13.05)
NOZZLE_BOX = (-10.15, 10.15, 12.0, 29.5, -79.0, -72.0)
P22_BREP = C.CFD / "p22_r43.brep"
STUDY_BREP = C.CFD / "p22_r43_long_study.brep"
CASES = {   # name: (label, design)
    "r41bm_bambu": ("Revision 41, Bambu", "r41"),
    "r41bm_redlizard": ("Revision 41, Red Lizard", "r41"),
    "r41bm_bambu_bed": ("Revision 41, Bambu, print surface 0.2 mm under the nozzle", "r41"),
    "r43_bambu": ("Revision 43, Bambu", "r43"),
    "r43_redlizard": ("Revision 43, Red Lizard", "r43"),
    "r43_bambu_bed": ("Revision 43, Bambu, print surface 0.2 mm under the nozzle", "r43"),
    "r43pocket_bambu": ("Study: lower floor alone, Bambu", "study"),
    "r43pocket_redlizard": ("Study: lower floor alone, Red Lizard", "study"),
    "r43pocket_bambu_bed": ("Study: lower floor alone, print surface", "study"),
    "r43lowbell_bambu_bed": ("Study: lower floor and r 2.4 bell-mouth as simulated first (no taper), print surface", "study"),
    "r43front_bambu_bed": ("Study: floor 0.4 mm lower where flat only, print surface", "study"),
    "r43frontbell_bambu_bed": ("Study: floor lower where flat and r 2.4 bell-mouth, print surface", "study"),
    "r43bell_bambu_bed": ("Study: r 2.4 bell-mouth alone, print surface", "study"),
    "r43low_bambu_bed": ("Study: first, flat pocket under the jets (not printable), print surface", "study"),
    "r43combo_bambu": ("Study: flat pocket and r 2.4 bell-mouth (not printable), Bambu", "study"),
    "r43combo_bambu_bed": ("Study: flat pocket and r 2.4 bell-mouth (not printable), print surface", "study"),
    "r43long_bambu": ("Study: jets run back to Y13, Bambu", "long"),
    "r43long_bambu_bed": ("Study: jets run back to Y13, print surface", "long"),
    "r43rear_bambu": ("Study: jets run back to Y13, front 4 mm closed, Bambu", "long"),
    "r43rear_bambu_bed": ("Study: jets run back to Y13, front 4 mm closed, print surface", "long"),
    "r43v1_bambu_bed": ("Revision 43 before the review (round to Y26.2, tapered foot; strip under the notch), print "
                        "surface", "study"),
    "r43revrib_bambu_bed": ("Study: the review's rib alone, with the first version's round, print surface", "study"),
    "r43revback_bambu_bed": ("Study: the review's round, but ending square at Y26.2 as before, print surface", "study"),
    "r43full_bambu": ("Study: the review's first pass, the round at full size to the front wall, Bambu", "study"),
    "r43full_redlizard": ("Study: the review's first pass, the round at full size to the front wall, Red Lizard", "study"),
    "r43full_bambu_bed": ("Study: the review's first pass, the round at full size to the front wall, print surface",
                          "study"),
    "r43revfade_bambu_bed": ("Study: the full-length round with its foot faded out at both ends, print surface", "study"),
    "r43revrunout_bambu_bed": ("Study: the round running out over Y24.6-27.3, as adopted but cut from the heel, "
                               "print surface", "study"),
    "r43fullnp46_bambu_bed": ("Check: the full-round study meshed and run on 46 cores (r43full_bambu_bed: 30), print "
                              "surface", "study"),
    "r43np46_bambu_bed": ("Check: revision 43 meshed and run on 46 cores (r43_bambu_bed: 30), print surface", "study"),
    "r43revfocus_bambu_bed": ("Study: the round only where the jets face the nozzle, a sharp edge from the heel to "
                              "Y18.2, print surface (46 cores)", "study"),
}
N_EXP = 1.983                                    # dP ~ Q^n (revision 41's fit), for single-flow cases


def window_for(name):
    return R43_WINDOW if CASES.get(name, ("", ""))[1] == "long" else R41_WINDOW


def annulus(g, z, r0=1.0, r1=5.0, n_r=9, n_t=72):
    """Area-mean air speed over an annulus about the nozzle axis at height z, and quarter means at r 2 mm."""
    rings = []
    for r in np.linspace(r0, r1, n_r):
        pts = [(r * math.cos(2 * math.pi * i / n_t), C.NOZZLE_Y + r * math.sin(2 * math.pi * i / n_t), z) for i in range(n_t)]
        u, ok = P.probe(g, pts)
        rings.append((r, np.linalg.norm(u, axis=1), ok))
    num = sum((s[ok] * r).sum() for r, s, ok in rings)
    den = sum(ok.sum() * r for r, s, ok in rings)
    _, s2, ok2 = min(rings, key=lambda t: abs(t[0] - 2.0))
    ang = np.arange(n_t) * 360.0 / n_t
    quarters = {}
    for k, a0 in (("right", -45), ("front", 45), ("left", 135), ("back", 225)):
        m = ((ang - a0) % 360 < 90) & ok2
        quarters[k] = round(float(s2[m].mean()), 2) if m.any() else None
    return {"z_mm": round(z, 2), "mean_ms_r1_5": round(float(num / den), 2), "quarters_r2_ms": quarters}


def print_sweep(g):
    """Over a print surface: the radial outflow in the first 1 mm above it through cylinders about the nozzle axis
    (L/min), and the mean speed 0.3 mm above it round circles (m/s)."""
    surf = C.NOZZLE_TIP_Z - C.BED_GAP
    th = np.linspace(0, 2 * math.pi, 144, endpoint=False)
    flows = {}
    for r in (3.0, 5.0, 8.0, 12.0):
        zs = surf + (np.arange(6) + 0.5) / 6.0
        pts = [(r * math.cos(t), C.NOZZLE_Y + r * math.sin(t), z) for z in zs for t in th]
        u, ok = P.probe(g, pts)
        t6 = np.tile(th, 6)
        ur = np.where(ok, u[:, 0] * np.cos(t6) + u[:, 1] * np.sin(t6), 0.0)
        flows[f"r{r:g}_mm"] = round(float(ur.sum() * (2 * math.pi * r / 144) * (1.0 / 6) * 1e-6 * 60000), 1)
    speeds = {}
    for r in (2.0, 3.0, 5.0, 7.0, 10.0, 14.0):
        u, ok = P.probe(g, [(r * math.cos(t), C.NOZZLE_Y + r * math.sin(t), surf + 0.3) for t in th[::2]])
        speeds[f"r{r:g}_mm"] = round(float(np.linalg.norm(u[ok], axis=1).mean()), 1)
    rs, tt = np.arange(1.0, 14.01, 0.5), np.linspace(0, 2 * math.pi, 96, endpoint=False)
    u, ok = P.probe(g, [(r * math.cos(t), C.NOZZLE_Y + r * math.sin(t), surf + 0.3) for r in rs for t in tt])
    sp, okr = np.linalg.norm(u, axis=1).reshape(len(rs), len(tt)), ok.reshape(len(rs), len(tt))
    ring = np.array([sp[i][okr[i]].mean() if okr[i].any() else np.nan for i in range(len(rs))])
    disc = {}
    for R in (5.0, 10.0, 14.0):
        m = (rs <= R) & ~np.isnan(ring)
        disc[f"r{R:g}_mm"] = round(float((ring[m] * rs[m]).sum() / rs[m].sum()), 2)
    return {"outflow_within_1mm_lpm": flows, "speed_0.3mm_over_ms": speeds, "disc_mean_speed_0.3mm_over_ms": disc}


def analyse(name):
    meta = json.loads((C.results_dir(name) / "domain.json").read_text())
    C.JET_WINDOW = window_for(name)
    rows = []
    for st in P.stages(name):
        row = P.analyse(name, st["end"], st["lpm"], meta["bed"])
        g = P.internal(name, st["end"])
        row["nozzle_box_outflow_lpm"] = P.box_outflow(g, NOZZLE_BOX)
        row["annulus"] = {"under_tip_0.1": annulus(g, C.NOZZLE_TIP_Z - 0.1), "over_tip_0.3": annulus(g, C.NOZZLE_TIP_Z + 0.3)}
        if meta["bed"]:
            row["over_print"] = print_sweep(g)
        rows.append(row)
    (C.results_dir(name) / "analysis_r43.json").write_text(json.dumps(rows, indent=1))
    return rows


def rows_of(name):
    return json.loads((C.results_dir(name) / "analysis_r43.json").read_text())


def operating(rows, hose=True):
    if len(rows) < 2:
        r = rows[0]
        rows = [r, dict(r, lpm=120.0, inlet_total_pa=r["inlet_total_pa"] * (120.0 / r["lpm"]) ** N_EXP)]
    return C.operating_point(rows, hose)


def report():
    cases = {}
    for name, (label, design) in CASES.items():
        if not (C.results_dir(name) / "analysis_r43.json").exists():
            continue
        rows = rows_of(name)
        meta = json.loads((C.results_dir(name) / "domain.json").read_text())
        at180 = next(r for r in rows if r["lpm"] == 180.0)
        op = operating(rows)
        f = op["lpm"] / at180["lpm"]
        cases[name] = {
            "label": label, "design": design, "tool": meta["tool"], "print_surface": meta["bed"],
            "mesh": P.mesh_stats(name), "flows_lpm": [r["lpm"] for r in rows],
            "at_180_lpm": {"inlet_total_pa": at180["inlet_total_pa"], "jets": at180["jets"],
                           "bead_rings": at180["bead_rings"], "annulus": at180["annulus"],
                           "over_print": at180.get("over_print"),
                           "nozzle_box_outflow_lpm": at180["nozzle_box_outflow_lpm"],
                           "loss_breakdown": at180["loss_breakdown"], "iteration": at180["iteration"]},
            "operating_point_1m_hose": dict(op, system_curve="fitted" if len(rows) > 1 else f"180 L/min, dP ~ Q^{N_EXP}",
                                            jet_mean_ms=round(at180["jets"]["left"]["mean_ms"] * f, 1),
                                            over_bead_mean_ms=round(at180["annulus"]["over_tip_0.3"]["mean_ms_r1_5"] * f, 1)),
            "operating_point_no_hose": operating(rows, hose=False)}
    out = {"method": "As verification_cfd_cpap_r41.json: OpenFOAM v2512 simpleFoam, k-omega SST, the same domain, mesh "
                     "settings and blower curve; only P22 changes. Speeds scale with flow at these Reynolds numbers.",
           "cases": cases}
    pairs = {"bambu": ("r43_bambu", "r41bm_bambu"), "redlizard": ("r43_redlizard", "r41bm_redlizard"),
             "bambu_print_surface": ("r43_bambu_bed", "r41bm_bambu_bed")}
    out["r43_vs_r41"] = {}
    for k, (a, b) in pairs.items():
        if a in cases and b in cases:
            ca, cb = cases[a], cases[b]
            fa = ca["operating_point_1m_hose"]["lpm"] / 180.0
            fb = cb["operating_point_1m_hose"]["lpm"] / 180.0
            row = {
                "pressure_at_180_pct": round(100 * (ca["at_180_lpm"]["inlet_total_pa"] / cb["at_180_lpm"]["inlet_total_pa"] - 1), 1),
                "blower_flow_pct": round(100 * (fa / fb - 1), 1),
                "over_bead_speed_at_operating_flow_pct": round(100 * (ca["operating_point_1m_hose"]["over_bead_mean_ms"]
                                                                      / cb["operating_point_1m_hose"]["over_bead_mean_ms"] - 1), 1)}
            po_a, po_b = ca["at_180_lpm"].get("over_print"), cb["at_180_lpm"].get("over_print")
            if po_a and po_b:
                row["over_print_at_operating_flow_pct"] = {
                    "outflow_within_1mm_r8": round(100 * (po_a["outflow_within_1mm_lpm"]["r8_mm"] * fa
                                                          / (po_b["outflow_within_1mm_lpm"]["r8_mm"] * fb) - 1), 1),
                    **{f"speed_0.3mm_over_{r}": round(100 * (po_a["speed_0.3mm_over_ms"][r] * fa / (po_b["speed_0.3mm_over_ms"][r] * fb) - 1), 1)
                       for r in ("r3_mm", "r5_mm", "r10_mm")},
                    **{f"disc_mean_0.3mm_over_within_{r}": round(100 * (po_a["disc_mean_speed_0.3mm_over_ms"][r] * fa
                                                                        / (po_b["disc_mean_speed_0.3mm_over_ms"][r] * fb) - 1), 1)
                       for r in ("r5_mm", "r10_mm", "r14_mm")}}
            out["r43_vs_r41"][k] = row
    base = cases.get("r41bm_bambu_bed")
    if base:
        fb = base["operating_point_1m_hose"]["lpm"] / 180.0
        pb = base["at_180_lpm"]["over_print"]
        search = {}
        for name, c in cases.items():
            if not c["print_surface"] or name == "r41bm_bambu_bed":
                continue
            fa, pa = c["operating_point_1m_hose"]["lpm"] / 180.0, c["at_180_lpm"]["over_print"]
            search[name] = {
                "label": c["label"], "iterations": c["at_180_lpm"]["iteration"],
                "pressure_at_180_pct": round(100 * (c["at_180_lpm"]["inlet_total_pa"] / base["at_180_lpm"]["inlet_total_pa"] - 1), 1),
                "blower_flow_pct": round(100 * (fa / fb - 1), 1),
                **{f"air_over_print_within_{r[1:-3]}mm_pct": round(100 * (pa["disc_mean_speed_0.3mm_over_ms"][r] * fa
                                                                        / (pb["disc_mean_speed_0.3mm_over_ms"][r] * fb) - 1), 1)
                   for r in ("r5_mm", "r10_mm", "r14_mm")},
                "outflow_along_print_r8_pct": round(100 * (pa["outflow_within_1mm_lpm"]["r8_mm"] * fa
                                                           / (pb["outflow_within_1mm_lpm"]["r8_mm"] * fb) - 1), 1),
                "air_leaving_upward_pct": c["at_180_lpm"]["nozzle_box_outflow_lpm"]["share_pct"]["up"]}
        out["design_search_vs_r41"] = {
            "note": "Print surface 0.2 mm under the tip, Bambu tool. Each design at its own blower flow (1 m hose): the "
                    "duct's pressure at 180 L/min, the flow the blower then gives, the area-mean air speed 0.3 mm over "
                    "the print within 5, 10 and 14 mm of the nozzle, the air flowing out along the print within 1 mm of "
                    "it through r 8 mm, and the share of the jets' air leaving the space round the nozzle upward. "
                    "Most studies ran 600 iterations (within 1 % of 1200 on revision 41; 1-2 points of the near-nozzle "
                    "air on revision 43's); each case's count is listed.",
            "revision_41": {"pressure_at_180_pa": base["at_180_lpm"]["inlet_total_pa"],
                            "blower_flow_lpm": base["operating_point_1m_hose"]["lpm"],
                            "air_leaving_upward_pct": base["at_180_lpm"]["nozzle_box_outflow_lpm"]["share_pct"]["up"]},
            "cases": search}
    (ROOT / REPORT).write_text(json.dumps(out, indent=2, default=str) + "\n")
    return out


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("brep")
    a_ = sub.add_parser("analyse")
    a_.add_argument("names", nargs="+")
    sub.add_parser("report")
    a = p.parse_args()
    if a.cmd == "brep":
        import r43_parts
        C.CFD.mkdir(parents=True, exist_ok=True)
        r43_parts.p22().exportBrep(str(P22_BREP))
        r43_parts.long_jets_study().exportBrep(str(STUDY_BREP))
        print(P22_BREP, STUDY_BREP)
    elif a.cmd == "analyse":
        for n in a.names:
            rows = analyse(n)
            print(json.dumps([{"lpm": r["lpm"], "inlet_total_pa": r["inlet_total_pa"],
                               "over_bead_ms": r["annulus"]["over_tip_0.3"]["mean_ms_r1_5"]} for r in rows]), flush=True)
    else:
        print(json.dumps(report()["r43_vs_r41"], indent=1))


if __name__ == "__main__":
    sys.exit(main())
