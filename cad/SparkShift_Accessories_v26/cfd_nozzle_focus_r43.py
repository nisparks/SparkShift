"""Is the cooling air aimed at the fresh bead just below the nozzle tip? Aim, delivery and speed at the nozzle.

Usage: python cfd_nozzle_focus_r43.py <case> <out.png> [title]
       python cfd_nozzle_focus_r43.py --compare <out.png> <label=case> ...   (after the single-case run of each)
Needs an iteration-averaged case (cfd_cpap_r41.py case --average-from) and cfd_outlet_balance_r43.py <case> --mean,
whose flux-weighted streamlines it reuses (600 per outlet). Writes results/<case>/nozzle_focus.json and the figure.
Air values are at the case's blower operating point (WS7040, 1 m hose).

Definitions, around the nozzle axis (X 0, Y 22.7):
- Fresh bead: within 2 mm of the axis and 1 mm of the print surface.
- Aim: each streamline's initial direction (its first 0.5 mm) followed in a straight line through the CFD domain
  until it meets a wall: where the outlet points, before the jets bend or collide.
- Delivery: where the streamline itself goes (exclusive, in this order): through the fresh bead; within 1 mm of the
  print inside r 5 mm, then r 10 mm; otherwise it rises past the hotend (ends above Z -70) or leaves elsewhere.
- Hotend: every wall within X +-9, Y 16.5-30, from 1 mm above the print to Z -66 (nozzle body, heater block).
  A streamline scrubs it when it passes within 0.5 mm of those walls.
"""
import json
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import cfd_direct_mount_r43 as D
import cfd_outlet_balance_r43 as B
import render_outlet_balance_r43 as R

BED_Z = C.NOZZLE_TIP_Z - C.BED_GAP
NY = C.NOZZLE_Y
BEAD_R, LOW = 2.0, 1.0
HOTEND_BOX = (-9.0, 9.0, 16.5, 30.0, BED_Z + LOW, -66.0)
SCRUB_MM = 0.5
NU = 1.5e-5                                      # constant/transportProperties
SLOT_MM = {"left": (3.45, 11.5), "right": (3.45, 11.5), "centre": (0.9, 18.0)}   # height and width of each opening
KEYS = ("left", "right", "centre")
DELIVERY = (("bead", "fresh bead (r <= 2 mm)", "#ffd43b"), ("r5", "print, r 2-5 mm", "#63e6be"),
            ("r10", "print, r 5-10 mm", "#2f9e77"), ("up", "rises past the hotend", "#ff6b6b"),
            ("other", "leaves elsewhere", "#5c7080"))
AIM = (("bead", "the fresh bead or tip"), ("print5", "print, r 2-5 mm"), ("print10", "print, r 5-10 mm"),
       ("print_far", "print, beyond 10 mm"), ("hotend", "nozzle body or heater block"), ("duct", "the duct itself"),
       ("open", "nothing within 25 mm"))


def probe(g, pts):
    vp = vtk.vtkPoints()
    vp.SetData(numpy_to_vtk(np.ascontiguousarray(pts, dtype=np.float64), deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(vp)
    pr = vtk.vtkProbeFilter()
    pr.SetInputData(pd)
    pr.SetSourceData(g)
    pr.Update()
    data = pr.GetOutput().GetPointData()
    return vtk_to_numpy(data.GetArray("vtkValidPointMask")).astype(bool), vtk_to_numpy(data.GetArray("U")).copy()


def hotend_walls(case):
    box = vtk.vtkBox()
    box.SetBounds(*HOTEND_BOX)
    ex = vtk.vtkExtractPolyDataGeometry()
    ex.SetInputData(P.boundary(case, 1200, "walls"))
    ex.SetImplicitFunction(box)
    ex.ExtractInsideOn()
    ex.ExtractBoundaryCellsOn()
    ex.Update()
    tri = vtk.vtkTriangleFilter()
    tri.SetInputData(ex.GetOutput())
    tri.Update()
    return tri.GetOutput()


def streamlines(case):
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(str(C.results_dir(case) / "outlet_streamlines_mean.vtp"))
    reader.Update()
    poly = reader.GetOutput()
    xyz = vtk_to_numpy(poly.GetPoints().GetData()).astype(float)
    cells = poly.GetLines()
    offsets = vtk_to_numpy(cells.GetOffsetsArray()).astype(np.int64)
    if np.any(np.diff(offsets) < 2):
        raise ValueError("streamline with fewer than two points")
    return xyz[vtk_to_numpy(cells.GetConnectivityArray())], offsets, vtk_to_numpy(poly.GetCellData().GetArray("outlet"))


def initial_rays(pts, offsets, ahead=.5):
    origin = pts[offsets[:-1]]
    dirs = np.empty_like(origin)
    for i, (s, e) in enumerate(zip(offsets[:-1], offsets[1:])):
        dist = np.linalg.norm(pts[s:e] - pts[s], axis=1)
        k = int(np.argmax(dist >= ahead)) if (dist >= ahead).any() else e - s - 1
        dirs[i] = (pts[s + k] - pts[s]) / dist[k]
    return origin, dirs


def march(g, origin, dirs, step=.05, length=25.0):
    """Follow straight rays until the first sample outside the fluid. Returns the last fluid point of each ray and
    whether it stopped at a wall."""
    s = np.arange(0, length + 1e-9, step)
    ends, stopped = np.empty_like(origin), np.zeros(len(origin), bool)
    for lo in range(0, len(origin), 200):
        o, d = origin[lo:lo + 200], dirs[lo:lo + 200]
        samples = o[:, None, :] + s[None, :, None] * d[:, None, :]
        ok, _ = probe(g, samples.reshape(-1, 3))
        ok = ok.reshape(len(o), len(s))
        ok[:, 0] = True
        first_bad = np.where(~ok.all(1), np.argmin(ok, 1), len(s))
        ends[lo:lo + 200] = samples[np.arange(len(o)), first_bad - 1]
        stopped[lo:lo + 200] = first_bad < len(s)
    return ends, stopped


def aim_category(ends, stopped):
    r = np.hypot(ends[:, 0], ends[:, 1] - NY)
    on_print = ends[:, 2] <= BED_Z + .15
    b = HOTEND_BOX
    in_hotend = ((ends[:, 0] >= b[0]) & (ends[:, 0] <= b[1]) & (ends[:, 1] >= b[2]) & (ends[:, 1] <= b[3])
                 & (ends[:, 2] > BED_Z + LOW))
    bead = (r <= BEAD_R) & (ends[:, 2] <= BED_Z + LOW)
    cat = np.full(len(ends), "duct", dtype=object)
    cat[~stopped] = "open"
    cat[stopped & in_hotend] = "hotend"
    cat[stopped & on_print & (r > 10)] = "print_far"
    cat[stopped & on_print & (r <= 10)] = "print10"
    cat[stopped & on_print & (r <= 5)] = "print5"
    cat[stopped & bead] = "bead"
    return cat


def delivery(pts, offsets, walls):
    starts = offsets[:-1]
    r = np.hypot(pts[:, 0], pts[:, 1] - NY)
    low = pts[:, 2] <= BED_Z + LOW
    b = HOTEND_BOX
    near = ((pts[:, 0] >= b[0] - SCRUB_MM) & (pts[:, 0] <= b[1] + SCRUB_MM) & (pts[:, 1] >= b[2] - SCRUB_MM)
            & (pts[:, 1] <= b[3] + SCRUB_MM) & (pts[:, 2] > b[4]) & (pts[:, 2] <= b[5] + SCRUB_MM))
    distance = vtk.vtkImplicitPolyDataDistance()
    distance.SetInput(walls)
    out = vtk.vtkDoubleArray()
    distance.FunctionValue(numpy_to_vtk(np.ascontiguousarray(pts[near]), deep=True), out)
    d = np.full(len(pts), np.inf)
    d[near] = np.abs(vtk_to_numpy(out))
    line_any = lambda mask: np.logical_or.reduceat(mask, starts)
    bead, r5, r10 = line_any(low & (r <= BEAD_R)), line_any(low & (r <= 5)), line_any(low & (r <= 10))
    up = pts[offsets[1:] - 1, 2] > -70
    return ({"bead": bead, "r5": r5 & ~bead, "r10": r10 & ~r5, "up": ~r10 & up, "other": ~r10 & ~up},
            line_any(d <= SCRUB_MM), r10)


def radial(g, factor, z):
    radii, angles = np.arange(.6, 10.01, .1), np.linspace(0, 2 * np.pi, 144, endpoint=False)
    rr, aa = np.meshgrid(radii, angles, indexing="ij")
    ok, u = probe(g, np.column_stack((rr.ravel() * np.cos(aa.ravel()), NY + rr.ravel() * np.sin(aa.ravel()),
                                      np.full(rr.size, z))))
    speed = np.where(ok, np.linalg.norm(u, axis=1) * factor, np.nan).reshape(rr.shape)
    return {"r_mm": radii.tolist(), "mean_ms": np.nanmean(speed, 1).tolist(), "min_ms": np.nanmin(speed, 1).tolist(),
            "max_ms": np.nanmax(speed, 1).tolist()}


def annulus_mean(profile, lo, hi):
    r, m = np.array(profile["r_mm"]), np.array(profile["mean_ms"])
    pick = (r >= lo - 1e-9) & (r <= hi + 1e-9) & np.isfinite(m)
    return float(np.average(m[pick], weights=r[pick]))


def section(g, factor, axis, lims, step=.08):
    a = np.arange(lims[0], lims[1] + 1e-9, step)
    z = np.arange(lims[2], lims[3] + 1e-9, step)
    A, Z = np.meshgrid(a, z)
    pts = (np.column_stack((A.ravel(), np.full(A.size, NY), Z.ravel())) if axis == "front"
           else np.column_stack((np.zeros(A.size), A.ravel(), Z.ravel())))
    ok, u = probe(g, pts)
    u = u * factor
    mask = ~ok.reshape(A.shape)
    inplane = u[:, 0] if axis == "front" else u[:, 1]
    return (a, z, np.ma.array(np.linalg.norm(u, axis=1).reshape(A.shape), mask=mask),
            np.ma.array(inplane.reshape(A.shape), mask=mask), np.ma.array(u[:, 2].reshape(A.shape), mask=mask))


def layer_rays(origin, dirs, ends, pick):
    """Bottom, middle and top quarter of an opening (by seed height): mean start and the mean ray's end."""
    idx = np.where(pick)[0]
    idx = idx[np.argsort(origin[idx, 2])]
    q = max(len(idx) // 4, 1)
    return [(origin[g].mean(0), np.median(ends[g], 0)) for g in (idx[:q], idx[len(idx) // 2 - q // 2:][:q], idx[-q:])]


def draw_section(ax, sec, title, xlabel, arrows, target):
    a, z, speed, ua, uz = sec
    R.style(ax, title)
    ax.set_facecolor("#55606e")
    im = ax.imshow(speed, origin="lower", extent=(a[0], a[-1], z[0], z[-1]), cmap="turbo", vmin=0, vmax=60,
                   interpolation="bilinear")
    ax.streamplot(a, z, ua, uz, density=1.6, color=(1, 1, 1, .5), linewidth=.6, arrowsize=.7)
    ax.add_patch(plt.Rectangle((target[0], BED_Z), target[1] - target[0], LOW, fill=False, ec="#ffd43b", lw=2,
                               ls="--", zorder=6))
    ax.text((target[0] + target[1]) / 2, BED_Z - .35, "fresh bead", color="#ffd43b", ha="center", va="top",
            fontsize=11, fontweight="bold", zorder=7)
    for (p0, p1), color in arrows:
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", color="w", lw=4.2, mutation_scale=16),
                    zorder=8)
        ax.annotate("", xy=p1, xytext=p0, arrowprops=dict(arrowstyle="-|>", color=color, lw=2.4, mutation_scale=14),
                    zorder=9)
    ax.set_xlim(a[0], a[-1])
    ax.set_ylim(z[0] - .8, z[-1])
    ax.set_aspect("equal")
    ax.set_xlabel(xlabel, color=R.MUTED)
    ax.set_ylabel("Z (mm)", color=R.MUTED)
    return im


def load_cached(case):
    result = json.loads((C.results_dir(case) / "nozzle_focus.json").read_text())
    data = np.load(C.results_dir(case) / "nozzle_focus_sections.npz")
    sections = {}
    for n in ("front", "side"):
        speed = data[f"{n}_speed"]
        mask = ~np.isfinite(speed)
        sections[n] = (data[f"{n}_a"], data[f"{n}_z"], *(np.ma.array(np.nan_to_num(data[f"{n}_{k}"]), mask=mask)
                                                         for k in ("speed", "ua", "uz")))
    return result, sections


def compare(out_png, specs):
    """Before/after: front sections with the side-jet aim, and the delivery, aim and near-nozzle numbers."""
    cases = [(s.split("=", 1)[0], *load_cached(s.split("=", 1)[1])) for s in specs]
    n = len(cases)
    fig = plt.figure(figsize=(12 * n, 15), dpi=100)
    fig.patch.set_facecolor(R.BG)
    grid = fig.add_gridspec(2, 3 * n, height_ratios=[1, 1.05], hspace=.3, wspace=.6)
    xy = lambda pair, i: [(p[i], p[2]) for p in pair]
    sections_ax = []
    for i, (label, res, sec) in enumerate(cases):
        rays = [((np.array(p), np.array(q)), R.COLORS[k]) for k in ("left", "right") for p, q in res["section_rays_mm"][k]]
        sections_ax.append(fig.add_subplot(grid[0, 3 * i:3 * i + 3]))
        im = draw_section(sections_ax[-1], sec["front"],
                          f"{label}: front section through the nozzle, side-jet aim (bottom / middle / top)", "X (mm)",
                          [(xy(pq, 0), c) for pq, c in rays], (-BEAD_R, BEAD_R))
    bar = fig.colorbar(im, ax=sections_ax, shrink=.6, pad=.01, fraction=.02)
    bar.set_label("m/s", color=R.MUTED)
    bar.ax.tick_params(colors=R.MUTED)
    w = 3 * n // 3
    x = np.arange(len(DELIVERY))
    width = .8 / n
    colors = ["#8fa3b8", "#ffd43b", "#ff922b", "#74c0fc"][:n]
    ax = fig.add_subplot(grid[1, :w])
    R.style(ax, "Where all the air goes (L/min at each design's blower point)")
    for i, (label, res, _) in enumerate(cases):
        vals = [res["totals_lpm"][f] for f, *_ in DELIVERY]
        ax.bar(x + (i - (n - 1) / 2) * width, vals, width, color=colors[i], label=f"{label} ({res['operating_point_lpm']:.0f} L/min)")
        for xi, v in zip(x, vals):
            ax.text(xi + (i - (n - 1) / 2) * width, v + 1, f"{v:.0f}", color=R.TEXT, ha="center", fontsize=9)
    ax.set_xticks(x, ["fresh bead\n(r <= 2 mm)", "print,\nr 2-5 mm", "print,\nr 5-10 mm", "rises past\nthe hotend",
                      "leaves\nelsewhere"], color=R.MUTED, fontsize=9)
    R.legend(ax, loc="upper left", fontsize=9)
    ax = fig.add_subplot(grid[1, w:2 * w])
    R.style(ax, "Where the side jets point (% of side-jet air)")
    x = np.arange(len(AIM))
    for i, (label, res, _) in enumerate(cases):
        o = res["outlets"]
        vals = [(o["left"]["aim_pct"][c] * o["left"]["lpm_at_operating_point"] + o["right"]["aim_pct"][c]
                 * o["right"]["lpm_at_operating_point"]) / (o["left"]["lpm_at_operating_point"]
                                                             + o["right"]["lpm_at_operating_point"]) for c, _ in AIM]
        ax.bar(x + (i - (n - 1) / 2) * width, vals, width, color=colors[i], label=label)
        for xi, v in zip(x, vals):
            ax.text(xi + (i - (n - 1) / 2) * width, v + 1, f"{v:.0f}", color=R.TEXT, ha="center", fontsize=9)
    ax.set_xticks(x, ["bead\nor tip", "print,\nr 2-5", "print,\nr 5-10", "print,\n> 10 mm", "nozzle or\nheater block",
                      "the duct\nitself", "nothing\nin 25 mm"], color=R.MUTED, fontsize=9)
    R.legend(ax, loc="upper right", fontsize=9)
    ax = fig.add_subplot(grid[1, 2 * w:])
    R.style(ax, "Air speed 0.3 mm above the print, mean around the nozzle (m/s)")
    ax.axvspan(0, BEAD_R, color="#ffd43b", alpha=.13)
    lines = []
    for i, (label, res, _) in enumerate(cases):
        p = res["radial_profiles"]["0.3 mm above the print"]
        ax.plot(p["r_mm"], p["mean_ms"], color=colors[i], lw=2.4, label=label)
        s = res["near_print_sectors_ms"]
        o = res["outlets"]
        sp = res.get("side_spill_lpm", {})
        under = sum(v["outward_under_p22_at_x13_lpm"] for v in sp.values())
        down = sum(v["down_through_lip_footprint_lpm"] for v in sp.values())
        lines.append(f"{label}: bead ring {res['near_print_ring_mean_ms']['r 0.6-2 mm']:.0f} m/s\n   sectors R/F/L/Re "
                     f"{s['right']:.0f}/{s['front']:.0f}/{s['left']:.0f}/{s['rear']:.0f} (ratio "
                     f"{res['weakest_to_strongest']:.2f})\n   side jets {o['left']['down_deg']:.0f} deg down, "
                     f"{o['left']['forward_deg']:.0f} deg forward\n   outward under P22 {under:.0f} L/min; "
                     f"down through the lip footprint {down:.0f} L/min")
    ax.text(.03, .97, "\n".join(lines), transform=ax.transAxes, color=R.TEXT, fontsize=9.5, va="top")
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 75)
    ax.set_xlabel("distance from the nozzle axis (mm)", color=R.MUTED)
    R.legend(ax, loc="lower right", fontsize=9)
    fig.suptitle("Side-jet floor lip: " + " vs ".join(c[0] for c in cases) + ". Iteration-mean CFD; air at each design's "
                 "own blower operating point (WS7040, 1 m hose). Airflow, not temperature.\nStreamline fates start at the "
                 "outlet sections; air that leaves through a trimmed floor before them is counted only as the spill "
                 "flux (right panel).", color=R.TEXT, fontsize=15)
    fig.savefig(out_png, facecolor=R.BG, bbox_inches="tight", pad_inches=.4)
    print(out_png)


def plane_flux(g, factor, axis, at, lo1, hi1, lo2, hi2, sign, d=.04):
    """L/min through an axis-normal rectangle (sign picks the direction counted as positive)."""
    a, b = np.arange(lo1 + d / 2, hi1, d), np.arange(lo2 + d / 2, hi2, d)
    A, Bb = np.meshgrid(a, b)
    pts = (np.column_stack((A.ravel(), Bb.ravel(), np.full(A.size, at))) if axis == "z"
           else np.column_stack((np.full(A.size, at), A.ravel(), Bb.ravel())))
    ok, u = probe(g, pts)
    comp = u[:, 2] if axis == "z" else u[:, 0]
    return float(np.sum(np.where(ok, sign * comp, 0)) * d * d * 1e-6 * 60000 * factor)


def spill(g, factor):
    """Side-jet air that leaves sideways: down through the floor-lip footprint (solid unless the lip is trimmed),
    and outward along the print under P22 (between the print and P22's underside, Z -79.08 to -77.85)."""
    out = {}
    for side, s in (("left", -1), ("right", 1)):
        x0, x1 = sorted((10.2 * s, 11.75 * s))
        out[side] = {"down_through_lip_footprint_lpm": plane_flux(g, factor, "z", -77.45, x0, x1, 21.4, 27.9, -1),
                     "outward_under_p22_at_x13_lpm": plane_flux(g, factor, "x", 13.0 * s, 14.0, 31.0, BED_Z, -77.85, s)}
    return out


def main():
    if sys.argv[1] == "--compare":
        compare(sys.argv[2], sys.argv[3:])
        return
    case, out_png = sys.argv[1], sys.argv[2]
    title = sys.argv[3] if len(sys.argv) > 3 else "current Bambu set"
    report = json.loads((C.results_dir(case) / "outlet_balance_mean.json").read_text())
    op = report["operating_point_1m_hose"]
    factor = op["lpm"] / 180
    g = B.load(case, True)
    pts, offsets, label = streamlines(case)
    walls = hotend_walls(case)
    fate, scrub, r10_any = delivery(pts, offsets, walls)
    origin, dirs = initial_rays(pts, offsets)
    ends, stopped = march(g, origin, dirs)
    aim = aim_category(ends, stopped)
    rows = {}
    for i, key in enumerate(KEYS):
        mine = label == i
        lpm = report["outlets"][key]["lpm"] * factor
        d = dirs[mine].mean(0)
        d /= np.linalg.norm(d)
        rows[key] = {"lines": int(mine.sum()), "lpm_at_operating_point": lpm,
                     "mean_initial_direction": d.tolist(),
                     "down_deg": float(np.degrees(np.arcsin(-d[2]))),
                     "forward_deg": float(np.degrees(np.arctan2(d[1], abs(d[0])))) if key != "centre" else None,
                     "aim_pct": {c: 100 * float((aim[mine] == c).mean()) for c, _ in AIM},
                     "delivery_pct": {f: 100 * float(m[mine].mean()) for f, m in fate.items()},
                     "scrubs_hotend_pct": 100 * float(scrub[mine].mean()),
                     "check_r10_pct_vs_balance_report": [100 * float(r10_any[mine].mean()),
                                                         report["delivery"][key]["r10_mm_pct"]]}
        h, w = SLOT_MM[key]
        mean = lpm / 60000 / (h * w * 1e-6)
        rows[key]["opening"] = {"height_width_mm": [h, w], "mean_speed_ms": mean, "reynolds_on_height": mean * h * 1e-3 / NU,
                                "turbulence_intensity_at_section": report["outlets"][key]["turbulence_intensity"]}
    total = {f: sum(rows[k]["lpm_at_operating_point"] * rows[k]["delivery_pct"][f] / 100 for k in KEYS)
             for f, *_ in DELIVERY}
    total["scrubs_hotend"] = sum(rows[k]["lpm_at_operating_point"] * rows[k]["scrubs_hotend_pct"] / 100 for k in KEYS)
    total["aimed_at_hotend"] = sum(rows[k]["lpm_at_operating_point"] * rows[k]["aim_pct"]["hotend"] / 100 for k in KEYS)
    total["aimed_at_bead"] = sum(rows[k]["lpm_at_operating_point"] * rows[k]["aim_pct"]["bead"] / 100 for k in KEYS)
    profiles = {"0.3 mm above the print": radial(g, factor, BED_Z + .3),
                "1.0 mm above the print": radial(g, factor, BED_Z + 1.0)}
    near = profiles["0.3 mm above the print"]
    rings = {"r 0.6-2 mm": annulus_mean(near, .6, 2), "r 2-5 mm": annulus_mean(near, 2, 5)}
    cov = D.coverage(g, factor)
    spills = spill(g, factor)
    centre_y = float(origin[label == 2, 1].mean())
    front = section(g, factor, "front", (-14, 14, BED_Z - .4, -66))
    side = section(g, factor, "side", (min(centre_y - 3, NY - 14), NY + 12, BED_Z - .4, -66))
    del g
    np.savez_compressed(C.results_dir(case) / "nozzle_focus_sections.npz",
                        **{f"{n}_{k}": (np.ma.filled(v.astype(float), np.nan) if np.ma.isMaskedArray(v) else v)
                           for n, sec in (("front", front), ("side", side))
                           for k, v in zip(("a", "z", "speed", "ua", "uz"), sec)})
    side_rays = {k: layer_rays(origin, dirs, ends, (label == i) & (np.abs(origin[:, 1] - NY) <= 1.5))
                 for i, k in enumerate(("left", "right"))}
    centre_rays = layer_rays(origin, dirs, ends, (label == 2) & (np.abs(origin[:, 0]) <= 1.5))
    result = {"case": case, "operating_point_lpm": op["lpm"], "outlets": rows, "totals_lpm": total,
              "near_print_ring_mean_ms": rings, "radial_profiles": profiles,
              "near_print_sectors_ms": cov["sector_area_mean_speed_ms"],
              "weakest_to_strongest": cov["weakest_to_strongest_sector_mean_ratio"],
              "side_spill_lpm": spills,
              "section_rays_mm": {k: [[p.tolist(), q.tolist()] for p, q in v] for k, v in
                                  {**side_rays, "centre": centre_rays}.items()},
              "hotend_walls": {"triangles": walls.GetNumberOfCells(), "bounds_mm": list(walls.GetBounds())},
              "definitions": __doc__.split("Definitions, ", 1)[1].strip()}
    (C.results_dir(case) / "nozzle_focus.json").write_text(json.dumps(result, indent=1) + "\n")

    fig = plt.figure(figsize=(24, 15.5), dpi=100)
    fig.patch.set_facecolor(R.BG)
    grid = fig.add_gridspec(2, 6, height_ratios=[1, 1.15], hspace=.28, wspace=.55)
    xy = lambda pair, i: [(p[i], p[2]) for p in pair]
    im = draw_section(fig.add_subplot(grid[0, :3]), front,
                      "Front section through the nozzle: side-jet aim, bottom / middle / top of each opening",
                      "X (mm)", [(xy(p, 0), R.COLORS[k]) for k, v in side_rays.items() for p in v],
                      (-BEAD_R, BEAD_R))
    ax = fig.add_subplot(grid[0, 3:])
    draw_section(ax, side, "Side section through the nozzle: centre-slot aim", "Y (mm), toward the front",
                 [(xy(p, 1), R.COLORS["centre"]) for p in centre_rays[1:2]], (NY - BEAD_R, NY + BEAD_R))
    bar = fig.colorbar(im, ax=ax, shrink=.75, pad=.02)
    bar.set_label("m/s", color=R.MUTED)
    bar.ax.tick_params(colors=R.MUTED)

    ax = fig.add_subplot(grid[1, :2])
    R.style(ax, "Where each opening points (initial direction, straight)")
    for i, key in enumerate(KEYS):
        mine = label == i
        hit = mine & (aim == "hotend")
        ax.scatter(ends[mine & ~hit, 0], ends[mine & ~hit, 1], s=5, color=R.COLORS[key], alpha=.45, lw=0,
                   label=f"{R.NAMES[key]}: {rows[key]['aim_pct']['bead']:.0f}% at the bead, "
                         f"{rows[key]['aim_pct']['hotend']:.0f}% at the hotend")
        ax.scatter(ends[hit, 0], ends[hit, 1], s=14, color=R.COLORS[key], marker="x", lw=.8, alpha=.7)
    ax.add_patch(plt.Circle((0, NY), BEAD_R, fill=False, ec="#ffd43b", lw=2, ls="--"))
    ax.add_patch(plt.Circle((0, NY), .5, color="#b8c2cc"))
    wb = walls.GetBounds()
    ax.add_patch(plt.Rectangle((wb[0], wb[2]), wb[1] - wb[0], wb[3] - wb[2], fill=False, ec="#c9d6e3", lw=1, ls=":"))
    ax.text(0, wb[3] + .5, "hotend outline (CFD walls)", color=R.MUTED, ha="center", fontsize=9)
    ax.set_xlim(-12, 12)
    ax.set_ylim(NY - 12, NY + 12)
    ax.set_aspect("equal")
    ax.set_xlabel("X (mm); dots land on the print, x = meets the nozzle or heater block", color=R.MUTED)
    ax.set_ylabel("Y (mm), toward the front", color=R.MUTED)
    R.legend(ax, loc="lower center", fontsize=8.5, markerscale=3)

    ax = fig.add_subplot(grid[1, 2:4])
    R.style(ax, "Air speed around the nozzle, mean around the circle (m/s)")
    ax.axvspan(0, BEAD_R, color="#ffd43b", alpha=.13)
    ax.text(BEAD_R / 2, 63, "fresh\nbead", color="#ffd43b", ha="center", va="top", fontsize=11)
    for (name, p), color in zip(profiles.items(), ("#ffffff", "#74c0fc")):
        r = np.array(p["r_mm"])
        if color == "#ffffff":
            ax.fill_between(r, p["min_ms"], p["max_ms"], color=color, alpha=.1, label="0.3 mm: slowest-fastest direction")
        ax.plot(r, p["mean_ms"], color=color, lw=2.4, label=f"{name}")
    ax.text(1.0, rings["r 0.6-2 mm"] + 9, f"{rings['r 0.6-2 mm']:.0f} m/s", color=R.TEXT, ha="center", fontsize=11)
    ax.text(3.5, rings["r 2-5 mm"] + 9, f"{rings['r 2-5 mm']:.0f} m/s\n(r 2-5)", color=R.TEXT, ha="center", fontsize=11)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 65)
    ax.set_xlabel("distance from the nozzle axis (mm)", color=R.MUTED)
    R.legend(ax, loc="lower right", fontsize=9)

    ax = fig.add_subplot(grid[1, 4:])
    R.style(ax, "Where the air actually goes (L/min)")
    y = np.arange(3)[::-1]
    left = np.zeros(3)
    for f, text, color in DELIVERY:
        vals = np.array([rows[k]["lpm_at_operating_point"] * rows[k]["delivery_pct"][f] / 100 for k in KEYS])
        ax.barh(y, vals, left=left, color=color, label=text, height=.62)
        for yi, l, v in zip(y, left, vals):
            if v >= 2.5:
                ax.text(l + v / 2, yi, f"{v:.0f}", color="#0f1d2e", ha="center", va="center", fontsize=10,
                        fontweight="bold")
        left += vals
    for yi, k, l in zip(y, KEYS, left):
        ax.text(l + 1.5, yi, f"{rows[k]['scrubs_hotend_pct']:.0f}% brushes\nthe nozzle or\nheater block", color=R.TEXT,
                va="center", fontsize=9)
    ax.set_yticks(y, [R.NAMES[k] for k in KEYS], color=R.MUTED)
    ax.set_xlim(0, 1.5 * left.max())
    R.legend(ax, loc="lower right", fontsize=9)
    bead_total = total["bead"]
    fig.suptitle(f"Is the air aimed at the fresh bead just below the nozzle tip? {title}. Iteration-mean CFD at the "
                 f"{op['lpm']:.0f} L/min blower point.\n{bead_total:.0f} L/min ({100 * bead_total / op['lpm']:.0f}%) "
                 f"passes through the fresh bead zone; {total['aimed_at_hotend']:.0f} L/min is aimed at the nozzle "
                 f"body or heater block; {total['up']:.0f} L/min rises past the hotend without reaching the print. "
                 "Airflow, not temperature.", color=R.TEXT, fontsize=15)
    fig.savefig(out_png, facecolor=R.BG, bbox_inches="tight", pad_inches=.4)
    print(json.dumps({k: {kk: vv for kk, vv in v.items() if kk not in ("mean_initial_direction",)}
                      for k, v in rows.items()}, indent=1, default=float))
    print(json.dumps({"totals_lpm": total, "rings": rings, "section_rays": result["section_rays_mm"]}, indent=1))
    print(out_png)


if __name__ == "__main__":
    main()
