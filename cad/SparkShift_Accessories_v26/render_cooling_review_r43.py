"""Readable geometry and CFD comparisons for the audited cooling review.

python render_cooling_review_r43.py --geometry review_rvms_a40
python render_cooling_review_r43.py --flow "RVMS=r43auditRVMS28fine_bambu_bed" "40-degree=r43auditRVMS40fine_bambu_bed"
"""
import argparse
import gc
import json
from pathlib import Path

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
import numpy as np

import cfd_cpap_r41 as C
import cfd_bead_zones_r43 as Z
import cfd_direct_mount_r43 as D
import cfd_nozzle_focus_r43 as F
import cfd_outlet_balance_r43 as B
import cfd_provenance_r43 as V
import cfd_tip_approach_r43 as T
import render_outlet_balance_r43 as R
from build_modular_toolhead import ROOT


def section_triangles(body, at=0):
    face = cq.Face.makePlane(200, 200, cq.Vector(at, 0, -75), cq.Vector(1, 0, 0))
    section = body.copy().intersect(face)
    triangles = []
    for face in section.Faces():
        points, cells = face.tessellate(.005, .08)
        p = np.array([v.toTuple() for v in points])
        triangles.extend(p[list(t)][:, (1, 2)] for t in cells)
    return triangles


def draw_solid(ax, body, color, alpha=1):
    triangles = section_triangles(body)
    if triangles:
        ax.add_collection(PolyCollection(triangles, facecolor=color, edgecolor="none", linewidths=0,
                                         antialiased=False, alpha=alpha))


def outline(ax, body):
    face = cq.Face.makePlane(200, 200, cq.Vector(0, 0, -75), cq.Vector(1, 0, 0))
    for edge in body.copy().intersect(face).Edges():
        points = np.array([edge.positionAt(t).toTuple() for t in np.linspace(0, 1, 35)])
        ax.plot(points[:, 1], points[:, 2], color="#ffa34d", lw=1.1, ls="--")


def geometry(folder):
    root = C.CFD.parent / "swept_feed"
    old = cq.Shape.importBrep(str(root / "aim_v5d_RVMS" / "p22.brep"))
    new = cq.Shape.importBrep(str(root / folder / "p22.brep"))
    report = json.loads((root / folder / "checks.json").read_text())
    scene = C.CFD.parent / "r43_scene"
    manifest = json.loads((scene / "manifest.json").read_text())
    hotend = cq.Shape.importBrep(str(scene / dict(manifest["variants"]["Bambu"]["parts"])["hotend"]))
    angle = report["rear_slot"]["angle_deg"]
    height = report["rear_slot"]["mouth_height_mm"]
    fig, axes = plt.subplots(1, 2, figsize=(16, 6), dpi=135)
    fig.patch.set_facecolor(R.BG)
    for ax, body, title in zip(axes, (old, new), ("RVMS: 2.0 mm, 28-degree rear passage",
                                                f"Candidate: {height:g} mm, {angle:g}-degree rear passage")):
        R.style(ax, title)
        draw_solid(ax, body, "#8da9c0")
        for i, solid in enumerate(hotend.Solids()):
            draw_solid(ax, solid, "#37404b" if i == 4 else "#b8bec7")
        ax.axhline(C.NOZZLE_TIP_Z, color="#ffd43b", lw=1.3, ls="--")
        ax.axhline(F.BED_Z, color="#83dfba", lw=1.4)
        ax.fill_between([F.NY - 4, F.NY + 4], F.BED_Z, C.NOZZLE_TIP_Z, color="#ffd43b", alpha=.8)
        ax.annotate("nozzle tip", (F.NY, C.NOZZLE_TIP_Z), (25, -77.4), color=R.TEXT,
                    arrowprops=dict(arrowstyle="->", color=R.TEXT), fontsize=12)
        ax.text(4.5, F.BED_Z - .55, "print surface; target band is entirely below the tip",
                color="#ffd43b", fontsize=11)
        ax.set(xlim=(4, 30), ylim=(-80.1, -66), xlabel="Y (mm), rear to front", ylabel="Z (mm)")
        ax.xaxis.label.set_color(R.MUTED)
        ax.yaxis.label.set_color(R.MUTED)
        ax.set_aspect("equal")
        inset = ax.inset_axes([.03, .52, .43, .45])
        inset.set_facecolor("#14293c")
        draw_solid(inset, body, "#8da9c0")
        if body is new:
            outline(inset, old)
            inset.text(.02, .02, "dashed orange: old walls", transform=inset.transAxes,
                       color="#ffa34d", fontsize=9)
        inset.set(xlim=(9.8, 14.8), ylim=(-75, -70))
        inset.set_aspect("equal")
        inset.tick_params(colors=R.MUTED, labelsize=8)
        inset.set_title("Rear mouth: zoom", color=R.TEXT, fontsize=11)
    fig.suptitle(f"REAR OUTLET CHANGE | {height:g} mm opening, {angle:g}-degree terminal walls\n"
                 "Side jets, retainer and hardware unchanged. Wall angle is not a measured airflow angle.",
                 color=R.TEXT, fontsize=17)
    fig.subplots_adjust(left=.06, right=.985, bottom=.09, top=.80, wspace=.15)
    out = ROOT / "images" / "r43_cooling_review_geometry.png"
    fig.savefig(out, facecolor=R.BG)
    print(out, flush=True)


def sample_plan(g, factor):
    x = np.arange(-8, 8.001, .08)
    y = F.NY + x
    xx, yy = np.meshgrid(x, y)
    z = F.BED_Z + .1
    ok, u = F.probe(g, np.column_stack((xx.ravel(), yy.ravel(), np.full(xx.size, z))))
    u *= factor
    valid = ok.reshape(xx.shape)
    speed = np.where(ok, np.linalg.norm(u, axis=1), np.nan).reshape(xx.shape)
    vx = np.ma.array(u[:, 0].reshape(xx.shape), mask=~valid)
    vy = np.ma.array(u[:, 1].reshape(xx.shape), mask=~valid)
    radius = np.hypot(xx, yy - F.NY)
    angle = np.degrees(np.arctan2(yy - F.NY, xx)) % 360
    metrics = {}
    for name, lo, hi in (("r0p6_2", .6, 2), ("r2_4", 2, 4)):
        mask = valid & (radius >= lo) & (radius < hi)
        if not mask.any():
            raise ValueError(f"No valid samples in {name}")
        means = {}
        for label, centre in (("right", 0), ("front", 90), ("left", 180), ("rear", 270)):
            pick = mask & ((angle - centre + 45) % 360 < 90)
            means[label] = float(speed[pick].mean())
        metrics[name] = {"mean_ms": float(speed[mask].mean()), "sectors_ms": means,
                         "valid_fraction": float(mask.sum() / ((radius >= lo) & (radius < hi)).sum())}
    return x, y, speed, vx, vy, metrics


def flow(specs):
    rows = [s.split("=", 1) for s in specs]
    settings = [json.loads((C.results_dir(case) / "stages.json").read_text()) for _, case in rows]
    if any(s != settings[0] for s in settings[1:]):
        raise ValueError("Compare cases with matched solver and mesh settings, not mixed resolutions")
    fig, axes = plt.subplots(len(rows), 2, figsize=(16, 6.6 * len(rows)), dpi=130, squeeze=False)
    fig.patch.set_facecolor(R.BG)
    summaries = {}
    for row, (label, case) in enumerate(rows):
        report = V.read_balance(case)
        if abs(report["measurement_closure"]["inlet_lpm"] / report["flow_lpm"] - 1) > .01:
            raise ValueError(f"{case}: measured inlet does not match the solved flow; check units and fields")
        if not report["measurement_closure"]["within_3pct"]:
            raise ValueError(f"{case}: incomplete outlet accounting cannot be used for this comparison")
        root = C.results_dir(case)
        metadata = json.loads((root / "domain.json").read_text())
        V.require_current(report["p22_sha256"], V.digest(Path(metadata["p22_variant"])),
                          f"{case} frozen P22")
        zones = json.loads((root / "bead_zones.json").read_text())
        V.require_current(zones["inputs_sha256"], V.focus_inputs(case), f"{case} target metrics")
        V.require_current(zones["analyser_sha256"], V.digest(Path(Z.__file__)), f"{case} target scoring code")
        z4 = zones["zones"]["r 4 mm"]
        g = B.load(case, True)
        factor = report["operating_point_1m_hose"]["lpm"] / 180
        sec = F.section(g, factor, "side", (8, 29, F.BED_Z - .3, -69.5))
        x, y, speed, vx, vy, below = sample_plan(g, factor)
        hot = T.hot_walls(case, g, factor)
        yy, zz, ss, _, _ = sec
        pick = np.ix_((zz >= -78) & (zz <= -76), (yy >= 19) & (yy <= 21))
        pocket = float(ss[pick].mean())
        del g
        gc.collect()
        op = report["operating_point_1m_hose"]["lpm"]
        split = {k: v["lpm"] * factor for k, v in report["outlets"].items()}
        im = F.draw_section(axes[row, 0], sec, f"{label} | centre section (X = 0)", "Y (mm), rear to front",
                            [], (F.NY - 4, F.NY + 4))
        axes[row, 0].annotate(f"circled-region mean: {pocket:.1f} m/s", (20, -77), (8.5, -70.3),
                              color=R.TEXT, fontsize=12,
                              arrowprops=dict(arrowstyle="->", color=R.TEXT))
        ax = axes[row, 1]
        R.style(ax, f"{label} | plan: 0.1 mm BELOW the nozzle tip")
        ax.set_facecolor("#55606e")
        ax.imshow(np.ma.masked_invalid(speed), origin="lower", extent=(x[0], x[-1], y[0], y[-1]),
                  vmin=0, vmax=60, cmap="turbo", interpolation="nearest")
        ax.streamplot(x, y, vx, vy, density=1.3, color=(1, 1, 1, .6), linewidth=.65, arrowsize=.75)
        ax.add_patch(plt.Circle((0, F.NY), 4, ec="#ffd43b", fill=False, lw=1.8, ls="--"))
        ax.axvline(0, color="#ffd43b", lw=.65, alpha=.5)
        ax.plot(0, F.NY, marker="+", color="white", ms=9)
        ax.set(xlabel="X (mm)", ylabel="Y (mm); front is up")
        ax.xaxis.label.set_color(R.MUTED)
        ax.yaxis.label.set_color(R.MUTED)
        ax.set_aspect("equal")
        ax.text(.02, .02, f"below-tip target: {z4['all_path_in_zone_lpm']:.1f} L/min\n"
                f"model blower estimate: {op:.0f} L/min", transform=ax.transAxes, color="white", fontsize=12,
                bbox=dict(facecolor=R.BG, alpha=.85, edgecolor="none", pad=5))
        summaries[label] = {
            "case": case, "blower_estimate_lpm": op, "outlets_estimate_lpm": split,
            "outlet_accounting": report["measurement_closure"], "rear_slot": report["rear_slot"],
            "own_side_below_tip_r4": z4, "below_tip_ring_speed": below,
            "circled_pocket_mean_ms": pocket, "hot_part_speed_proxies": hot,
            "arriving_on_print": zones["arriving_on_the_print"],
            "traced_streamlines_by_outlet": {k: report["delivery"][k]["traced_lines"]
                                             for k in ("left", "right", "centre")},
            "numerical_quality": D.metrics(case),
            "inputs_sha256": V.focus_inputs(case),
        }
    fig.subplots_adjust(left=.055, right=.92, bottom=.06, top=.92, hspace=.23, wspace=.23)
    bar = fig.colorbar(im, cax=fig.add_axes([.945, .20, .012, .55]))
    bar.set_label("air speed (m/s), common scale", color=R.MUTED)
    bar.ax.tick_params(colors=R.MUTED)
    fig.suptitle("AUDITED AIRFLOW | complete rear-outlet accounting, own-side below-tip targets\n"
                 "Steady RANS at 180 L/min, velocities scaled to estimated blower points. Lines are in-plane "
                 "projections; not heat-transfer results.", color=R.TEXT, fontsize=14)
    out = ROOT / "images" / "r43_cooling_review_cfd.png"
    fig.savefig(out, facecolor=R.BG)
    result = {"cases": summaries, "matched_solver_and_mesh_settings": True, "settings": settings[0],
              "image_sha256": V.digest(out), "renderer_sha256": V.digest(Path(__file__)),
              "cautions": ["The target is clipped by the modeled bed 0.2 mm below the tip.",
                           "A low velocity stagnation region is not proof of poor heat transfer.",
                           "Scaled velocities assume similar flow topology at the estimated blower point."]}
    (ROOT / "verification_cooling_review_r43.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: {n: v[n] for n in ("case", "blower_estimate_lpm", "outlets_estimate_lpm",
                                           "circled_pocket_mean_ms", "below_tip_ring_speed")}
                      for k, v in summaries.items()}, indent=2), flush=True)
    print(out, flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--geometry")
    group.add_argument("--flow", nargs="+")
    args = parser.parse_args()
    if args.geometry:
        geometry(args.geometry)
    else:
        flow(args.flow)
