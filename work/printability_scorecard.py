"""Where the slicer puts support on the current C28 duct parts: inside the airway or outside, and how much.

Usage: python printability_scorecard.py
Reads printability_swept/<run>/ (sliced.3mf + placement.json) and the audited v5d parts; writes
printability_swept/scorecard/{scorecard.json, support_map.png}.
"""
import json
import math
import sys
import zipfile
from pathlib import Path

S = Path(__file__).resolve().parent
sys.path.insert(0, str(S))
from inspect_swept_support_paths import CAD, mesh, support_segments  # noqa: E402
import cadquery as cq  # noqa: E402
import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PolyCollection  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

import r43_c28_user_joint as U  # noqa: E402

PARTS = S / "swept_feed" / "optC28_flow_neutral_retainer"
OUT = S / "printability_swept" / "scorecard"
RUNS = {   # label: (part, run)
    "P22 breakaway interface": ("p22", "c28_flow_neutral_v5d_receiver_back"),
    "P22 ABS interface": ("p22", "c28_v5d_receiver_back_absif"),
    "P21 breakaway interface": ("p21", "c28_flow_neutral_v5d_p21_top"),
    "P21 ABS interface": ("p21", "c28_v5d_p21_top_absif"),
    "P01 breakaway interface": ("p01", "c28_mechanical_p01_back"),
    "P01 ABS interface": ("p01", "c28_p01_back_absif"),
}


def samples(run, part):
    folder = S / "printability_swept" / run
    transform = np.array(json.loads((folder / "placement.json").read_text())["assembly_to_print"])
    with zipfile.ZipFile(folder / "sliced.3mf") as archive:
        code = archive.read(next(n for n in archive.namelist() if n.endswith(".gcode"))).decode()
    pts, weights = [], []
    for start, end, extrusion in support_segments(code):
        count = max(1, int(math.ceil(np.linalg.norm(end - start) / .5)))
        at = start + ((np.arange(count) + .5) / count)[:, None] * (end - start)
        pts.extend((at - transform[:3, 3]) @ transform[:3, :3])
        weights.extend([extrusion * math.pi * 1.75 ** 2 / 4 / count] * count)
    return np.asarray(pts), np.asarray(weights)


def inside(target, pts):
    low, high = target.bounds
    near = np.all((pts >= low) & (pts <= high), axis=1)
    flags = np.zeros(len(pts), bool)
    if near.any():
        flags[np.flatnonzero(near)] = target.contains(pts[near])
    return flags


def silhouette(ax, body, axes):
    tri = mesh(body)
    ax.add_collection(PolyCollection(tri.vertices[tri.faces][:, :, axes], facecolors="#2c4a66",
                                     edgecolors="none", alpha=.35))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    parts = {k: cq.Shape.importBrep(str(PARTS / f"{k}.brep")) for k in ("p01", "p21", "p22")}
    scene = dict(json.loads((S / "r41_scene" / "manifest.json").read_text())["carriage"])
    p20 = cq.Shape.importBrep(str(S / "r41_scene" / scene["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))
    air_path = OUT / "v5d_duct_air.brep"
    if not air_path.exists():
        U.duct_air(p20, parts["p21"], parts["p22"]).exportBrep(str(air_path))
    air = mesh(cq.Shape.importBrep(str(air_path)))
    report, clouds = {}, {}
    for label, (part, run) in RUNS.items():
        metrics = json.loads((S / "printability_swept" / run / "support_metrics.json").read_text())
        result = json.loads((S / "printability_swept" / run / "result.json").read_text())["sliced_plates"][0]
        pts, w = samples(run, part)
        internal = inside(air, pts) if part != "p01" else np.zeros(len(pts), bool)
        times = result["feature_type_times"]
        report[label] = {
            "run": run, "support_mm3": metrics["support_deposition_volume_mm3"],
            "sampled_support_mm3": float(w.sum()),
            "inside_airway_mm3": float(w[internal].sum()),
            "inside_airway_fraction": float(w[internal].sum() / w.sum()) if len(w) else 0.0,
            "total_h": result["total_predication"] / 3600,
            "prime_tower_h": times.get("Prime tower", 0) / 3600, "flush_h": times.get("Flush", 0) / 3600,
            "support_h": sum(v for k, v in times.items() if k.startswith("Support")) / 3600,
            "abs_used_g": next(f["total_used_g"] for f in result["filaments"] if f["id"] == 1),
            "abs_in_part_g": next(f["main_used_g"] for f in result["filaments"] if f["id"] == 1),
            "interface_material_g": sum(f["total_used_g"] for f in result["filaments"] if f["id"] != 1),
        }
        if part == "p22":
            for name, box in (("plenum/lobes Y<-26", (-30, 30, -60, -26, -90, -40)),
                              ("side channels -26<=Y<11", (-30, 30, -26, 11, -90, -40)),
                              ("jets/outlets Y>=11", (-30, 30, 11, 40, -90, -40))):
                m = internal & np.all((pts >= box[::2]) & (pts <= box[1::2]), axis=1)
                report[label].setdefault("inside_airway_by_region_mm3", {})[name] = float(w[m].sum())
        clouds[label] = (pts, w, internal)
        print(label, json.dumps({k: (round(v, 3) if isinstance(v, float) else v) for k, v in report[label].items()}),
              flush=True)

    fig, axes = plt.subplots(2, 3, figsize=(19, 12), dpi=110)
    fig.patch.set_facecolor("#0f1d2e")
    panels = [("P22 breakaway interface", (0, 1), "plan (X-Y)"), ("P22 breakaway interface", (1, 2), "side (Y-Z)"),
              ("P21 breakaway interface", (1, 2), "side (Y-Z)"), ("P22 ABS interface", (0, 1), "plan (X-Y)"),
              ("P22 ABS interface", (1, 2), "side (Y-Z)"), ("P21 ABS interface", (1, 2), "side (Y-Z)")]
    for ax, (label, ij, view) in zip(axes.ravel(), panels):
        ax.set_facecolor("#0f1d2e")
        part = RUNS[label][0]
        silhouette(ax, parts[part], list(ij))
        pts, w, internal = clouds[label]
        step = max(1, len(pts) // 60000)
        for mask, color, name in ((~internal, "#f2c14e", "outside airway"), (internal, "#ff4d6d", "inside airway")):
            sel = np.flatnonzero(mask)[::step]
            ax.scatter(pts[sel, ij[0]], pts[sel, ij[1]], s=.6, c=color, alpha=.5, linewidths=0,
                       label=f"{name}: {w[mask].sum() / 1000:.2f} cm3")
        r = report[label]
        ax.set_title(f"{label}, {view}\n{r['support_mm3'] / 1000:.2f} cm3 support, {r['total_h']:.2f} h, "
                     f"prime tower {r['prime_tower_h']:.2f} h", color="#e6eef6", fontsize=12)
        ax.set_aspect("equal")
        ax.autoscale_view()
        ax.tick_params(colors="#9fb3c8", labelsize=9)
        for spine in ax.spines.values():
            spine.set_color("#4b6584")
        legend = ax.legend(loc="lower left", fontsize=9, markerscale=12, facecolor="#1b2f47", edgecolor="#4b6584")
        for text in legend.get_texts():
            text.set_color("#e6eef6")
    fig.suptitle("Where the slicer puts support (H2D, ABS, matched settings except the interface)", color="#e6eef6",
                 fontsize=16)
    fig.tight_layout()
    fig.savefig(OUT / "support_map.png", facecolor=fig.get_facecolor())
    (OUT / "scorecard.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
