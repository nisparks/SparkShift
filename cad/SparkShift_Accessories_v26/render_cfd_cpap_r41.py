"""Revision 41 CPAP CFD figures (run after `cfd_cpap_r41.py analyse` for each case).

81: system curves against the blower, where the pressure goes, and convergence.
82: revision 41 (bell-mouth jets) with the Bambu: air speed across the nozzle, at jet height, at the fresh bead,
    and turbulence.
83: the released outlet, revision 41's square-edged jets and its bell-mouth jets at the same flow.
84: streamlines from the hose to the nozzle, and the outlet close up.
85: speed and pressure along a side channel.
86: the Red Lizard, a flat print surface 0.2 mm under the nozzle, and the air speed round the nozzle tip with
    square-edged and bell-mouth jets at their operating flows.

Run: python render_cfd_cpap_r41.py
"""
import json
import math

import numpy as np
import vtk
from PIL import Image

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.tri as mtri  # noqa: E402

import cfd_cpap_r41 as C  # noqa: E402
import cfd_cpap_r41_post as P  # noqa: E402
from build_modular_toolhead import ROOT  # noqa: E402

IMAGES = ROOT / "images"
FINAL, SQUARE, RELEASED, LABELS = P.FINAL, P.SQUARE, P.RELEASED, P.LABELS
REDLIZARD, BED, SQUARE_BED = "r41bm_redlizard", "r41bm_bambu_bed", "r41sq_bambu_bed"
COLOURS = {RELEASED: "tab:red", SQUARE: "tab:blue", FINAL: "tab:green", REDLIZARD: "tab:orange",
           BED: "tab:olive", SQUARE_BED: "tab:cyan", "r41lip_bambu": "tab:gray", "r41lip_bambu_rough": "tab:brown",
           "r41lip_bambu_rough3": "tab:pink", "r41_bambu_fine": "tab:purple"}
VMAX = 90.0
W_XZ, W_XY = (-24, 24, -92, -64), (-24, 24, 4, 42)
W_JET = (5.0, 19.0, -80.0, -67.0)       # the right-hand jet close up, across the nozzle
RADII = np.r_[0.6:2.0:0.2, 2.0:8.01:0.5]


def analysis(name):
    return json.loads((C.results_dir(name) / "analysis.json").read_text())


def stage(name, lpm):
    return min(P.stages(name), key=lambda s: abs(s["lpm"] - lpm))


# ------------------------------------------------------------------ sections
def section(ax, g, axis, at, window, field="speed", vmax=VMAX, arrows=True, cmap="turbo", title=""):
    h, v = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    sl = P.plane_slice(g, axis, at)
    pts, tris, _ = P.triangles(sl)
    if field == "speed":
        val, label = np.linalg.norm(P.point_array(sl, "U"), axis=1), "air speed (m/s)"
    elif field == "p":
        val, label = P.point_array(sl, "p") * C.RHO, "static pressure above the room (Pa)"
    else:
        val = np.sqrt(2 * np.clip(P.point_array(sl, "k"), 0, None) / 3)
        label = "turbulent fluctuation u' = sqrt(2k/3) (m/s)"
    ax.set_facecolor("#c8c8c8")
    pc = ax.tripcolor(mtri.Triangulation(pts[:, h], pts[:, v], tris), val, shading="gouraud", cmap=cmap,
                      vmin=0 if field != "p" else None, vmax=vmax, rasterized=True)
    if arrows:
        xs = np.linspace(window[0], window[1], 34)
        ys = np.linspace(window[2], window[3], int(34 * (window[3] - window[2]) / (window[1] - window[0])) + 2)
        X, Y = np.meshgrid(xs, ys)
        pt = np.zeros((X.size, 3))
        pt[:, h], pt[:, v], pt[:, "xyz".index(axis)] = X.ravel(), Y.ravel(), at
        u, ok = P.probe(g, pt)
        su, sv = np.where(ok, u[:, h], np.nan), np.where(ok, u[:, v], np.nan)
        mag = np.hypot(su, sv)
        keep = ok & (mag > 0.05 * np.nanmax(mag))
        ax.quiver(X.ravel()[keep], Y.ravel()[keep], (su / mag)[keep], (sv / mag)[keep], color="white", alpha=0.75,
                  scale=40, width=0.0022, headwidth=3.5, pivot="mid")
    ax.set_xlim(window[0], window[1])
    ax.set_ylim(window[2], window[3])
    ax.set_aspect("equal")
    ax.set_xlabel("XYZ"[h] + " (mm)")
    ax.set_ylabel("XYZ"[v] + " (mm)")
    ax.set_title(title, fontsize=10)
    plt.colorbar(pc, ax=ax, shrink=0.85, pad=0.02).set_label(label)


def mark(ax, kind):
    ax.plot([0], [C.NOZZLE_TIP_Z if kind == "xz" else C.NOZZLE_Y], "w+", ms=10, mew=2)


def save(fig, name):
    out = IMAGES / name
    fig.savefig(out, dpi=100)
    plt.close(fig)
    return out


# ------------------------------------------------------------------ 81
def image_81(names):
    fig, axs = plt.subplots(1, 3, figsize=(24, 7.2))
    q = np.linspace(1, 360, 300)
    ax = axs[0]
    ax.plot(q, C.blower_pa(q), "k-", lw=2, label="WS7040 blower, 100 % PWM")
    ax.plot(q, C.blower_pa(q) - C.hose_pa(q), "k--", lw=1.4, label="... less 1 m of Ø19 CPAP hose")
    ops = {}
    for n in names:
        rows = analysis(n)
        qs, ps = [r["lpm"] for r in rows], [r["inlet_total_pa"] for r in rows]
        dashed = n == REDLIZARD
        ax.plot(qs, ps, ("x" if dashed else "o") if len(rows) > 1 else "D", color=COLOURS[n], label=LABELS[n])
        if len(rows) > 1:
            c, k = C.fit_power(rows)
            ax.plot(q, c * q ** k, "--" if dashed else "-", color=COLOURS[n], lw=1.5)
            op = C.operating_point(rows)
            ops[n] = op
            ax.plot([op["lpm"]], [op["duct_pa"]], "*", ms=17, color=COLOURS[n], mec="k")
            ax.annotate(f"{op['lpm']:.0f} L/min", (op["lpm"], op["duct_pa"]), textcoords="offset points",
                        xytext=(9, 6), color=COLOURS[n], fontsize=10, weight="bold")
    ax.set_xlim(0, 360)
    ax.set_ylim(0, 9000)
    ax.set_xlabel("air flow (L/min)")
    ax.set_ylabel("total pressure at P20's spigot (Pa)")
    ax.set_title("Duct system curves (CFD) against the blower; stars: where they meet")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8.5, loc="upper right")
    ax = axs[1]
    shown = [n for n in (RELEASED, SQUARE, FINAL) if n in ops]
    width = 0.8 / len(shown)
    for i, n in enumerate(shown):
        row = min(analysis(n), key=lambda r: abs(r["lpm"] - 180))
        lb = row["loss_breakdown"]
        drops = [lb[k]["total_pressure_pa"] - lb[k + 1]["total_pressure_pa"] for k in range(len(lb) - 1)]
        drops.append(lb[-1]["total_pressure_pa"])
        labels = [f"{lb[k]['section']} \u2192 {lb[k + 1]['section']}" for k in range(len(lb) - 1)] + ["carried out by the jets"]
        x = np.arange(len(drops)) + i * width
        ax.bar(x, drops, width, color=COLOURS[n], label=f"{LABELS[n]}, {row['lpm']:.0f} L/min")
    ax.set_xticks(np.arange(len(labels)) + width * (len(shown) - 1) / 2)
    ax.set_xticklabels(labels, rotation=30, ha="right", fontsize=8)
    ax.set_ylabel("total pressure lost (Pa)")
    ax.set_title("Where the pressure goes at 180 L/min, section by section")
    ax.grid(True, axis="y", alpha=0.3)
    ax.legend(fontsize=8.5)
    ax = axs[2]
    for n in names:
        h = P.inlet_history(n)
        ax.plot(h[:, 0], h[:, 2] * C.RHO, lw=1.1, color=COLOURS[n], label=LABELS[n])
    ax.set_xlabel("solver iteration (inlet flow steps 180 \u2192 120 \u2192 240 L/min)")
    ax.set_ylabel("total pressure at P20's spigot (Pa)")
    ax.set_ylim(0, 16000)
    ax.set_title("Convergence through each flow step (start-up transients clipped)")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8.5)
    fig.tight_layout()
    return save(fig, "81_cfd_r41_system_curves_losses.png"), ops


# ------------------------------------------------------------------ 82, 83, 85, 86
def image_82(lpm=180):
    s = stage(FINAL, lpm)
    g = P.internal(FINAL, s["end"])
    fig, axs = plt.subplots(2, 2, figsize=(15, 10.5))
    section(axs[0, 0], g, "y", C.NOZZLE_Y, W_XZ, title=f"Across the nozzle (Y {C.NOZZLE_Y}): both jets")
    section(axs[0, 1], g, "z", -75.1, W_XY, title="From above at jet mid-height (Z -75.1)")
    section(axs[1, 0], g, "z", C.NOZZLE_TIP_Z - 0.1, W_XY, vmax=VMAX / 2,
            title=f"At the fresh bead, 0.1 mm under the nozzle tip (Z {C.NOZZLE_TIP_Z - 0.1:.2f})")
    section(axs[1, 1], g, "y", C.NOZZLE_Y, W_XZ, field="k", vmax=20, cmap="magma", arrows=False,
            title="Turbulence across the nozzle (k-omega SST)")
    for ax, kind in zip(axs.ravel(), ("xz", "xy", "xy", "xz")):
        mark(ax, kind)
    fig.suptitle(f"{LABELS[FINAL]}, {s['lpm']:.0f} L/min (speeds scale with flow). Grey: solid", fontsize=13)
    fig.tight_layout()
    return save(fig, "82_cfd_r41_nozzle_bambu.png")


def image_83(lpm=180):
    shown = [n for n in (RELEASED, SQUARE, FINAL) if (C.results_dir(n) / "analysis.json").exists()]
    fig, axs = plt.subplots(3, len(shown), figsize=(7.4 * len(shown), 16), squeeze=False)
    for col, n in enumerate(shown):
        s = stage(n, lpm)
        g = P.internal(n, s["end"])
        p = min(analysis(n), key=lambda r: abs(r["lpm"] - lpm))["inlet_total_pa"]
        section(axs[0, col], g, "y", C.NOZZLE_Y, W_XZ,
                title=f"{LABELS[n]}\n{s['lpm']:.0f} L/min, {p / 1000:.2f} kPa at the spigot: across the nozzle")
        section(axs[1, col], g, "y", C.NOZZLE_Y, W_JET, title="The right-hand jet close up, same cut")
        section(axs[2, col], g, "z", -75.1, W_XY, title="From above at jet mid-height (Z -75.1)")
        mark(axs[0, col], "xz")
        mark(axs[2, col], "xy")
    fig.tight_layout()
    return save(fig, "83_cfd_r41_vs_released.png")


def image_85(lpm=180):
    s = stage(FINAL, lpm)
    g = P.internal(FINAL, s["end"])
    fig, axs = plt.subplots(2, 1, figsize=(15, 11))
    w = (-50, 34, -82, -44)
    section(axs[0], g, "x", 16.0, w, vmax=60, title="Air speed along the right-hand side channel (X 16)")
    section(axs[1], g, "x", 16.0, w, field="p", vmax=None, arrows=False, cmap="coolwarm",
            title="Static pressure along the same cut: the channel is a plenum; the drop is at the jets")
    fig.suptitle(f"{LABELS[FINAL]}, {s['lpm']:.0f} L/min", fontsize=13)
    fig.tight_layout()
    return save(fig, "85_cfd_r41_side_channel.png")


def radial_profile(ax, curves, title):
    """Mean air speed round circles about the nozzle axis, 0.1 mm under the tip, at each design's operating flow."""
    for name, g, scale, label in curves:
        ax.plot(RADII, [P.ring(g, C.NOZZLE_TIP_Z - 0.1, r)["mean_ms"] * scale for r in RADII], "o-", ms=3.5,
                color=COLOURS[name], label=label)
    ax.set_xlabel("distance from the nozzle axis (mm)")
    ax.set_ylabel("mean air speed (m/s)")
    ax.set_xlim(0, RADII[-1])
    ax.set_ylim(bottom=0)
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8.5)
    ax.set_title(title, fontsize=10)


def image_86(lpm=180):
    fig, axs = plt.subplots(2, 3, figsize=(22, 10.5))
    ops = {n: C.operating_point(analysis(n))["lpm"] for n in (SQUARE, FINAL)}
    grids = {}
    for n in (REDLIZARD, BED, SQUARE_BED, SQUARE, FINAL):
        s = stage(n, lpm)
        grids[n] = (P.internal(n, s["end"]), s["lpm"])
    g, q = grids[REDLIZARD]
    section(axs[0, 0], g, "y", C.NOZZLE_Y, W_XZ, title=f"{LABELS[REDLIZARD]}, {q:.0f} L/min")
    section(axs[0, 1], g, "z", -75.1, W_XY, title="Red Lizard: from above at jet mid-height (Z -75.1)")
    g, q = grids[BED]
    section(axs[1, 0], g, "y", C.NOZZLE_Y, (-24, 24, -80, -64), title=f"{LABELS[BED]}, {q:.0f} L/min")
    section(axs[1, 1], g, "z", C.NOZZLE_TIP_Z - 0.1, W_XY, vmax=VMAX / 2,
            title=f"Over the print surface, 0.1 mm above it (Z {C.NOZZLE_TIP_Z - 0.1:.2f})")
    for ax, kind in zip((axs[0, 0], axs[0, 1], axs[1, 0], axs[1, 1]), ("xz", "xy", "xz", "xy")):
        mark(ax, kind)
    lab = {SQUARE: "square-edged jets", FINAL: "bell-mouth jets"}
    radial_profile(axs[0, 2], [(n, grids[n][0], ops[n] / grids[n][1], f"{lab[n]}, {ops[n]:.0f} L/min") for n in (SQUARE, FINAL)],
                   "Open air under the nozzle (Bambu): speed 0.1 mm under the tip,\nat each design's operating flow (1 m hose)")
    radial_profile(axs[1, 2], [(b, grids[b][0], ops[n] / grids[b][1], f"{lab[n]}, {ops[n]:.0f} L/min")
                               for n, b in ((SQUARE, SQUARE_BED), (FINAL, BED))],
                   "Print surface 0.2 mm under the tip: speed 0.1 mm above it,\nat each design's operating flow (1 m hose)")
    fig.tight_layout()
    return save(fig, "86_cfd_r41_redlizard_print_surface.png")


# ------------------------------------------------------------------ 84: streamlines (VTK, off screen)
def lut(vmax, name="turbo", n=256):
    cm = plt.get_cmap(name)
    t = vtk.vtkLookupTable()
    t.SetNumberOfTableValues(n)
    t.SetRange(0, vmax)
    for i in range(n):
        r, g, b, _ = cm(i / (n - 1))
        t.SetTableValue(i, r, g, b, 1.0)
    t.Build()
    return t


def streamlines(g, seeds, max_len):
    pts = vtk.vtkPoints()
    for p in seeds:
        pts.InsertNextPoint(*p)
    sp = vtk.vtkPolyData()
    sp.SetPoints(pts)
    st = vtk.vtkStreamTracer()
    st.SetInputData(g)
    st.SetSourceData(sp)
    st.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "U")
    st.SetIntegratorTypeToRungeKutta45()
    st.SetIntegrationDirectionToForward()
    st.SetMaximumPropagation(max_len)
    st.SetInitialIntegrationStep(0.2)
    st.SetMinimumIntegrationStep(0.01)
    st.SetMaximumIntegrationStep(0.5)
    st.SetIntegrationStepUnit(vtk.vtkStreamTracer.CELL_LENGTH_UNIT)
    st.SetMaximumNumberOfSteps(20000)
    st.SetTerminalSpeed(0.05)
    st.Update()
    calc = vtk.vtkArrayCalculator()
    calc.SetInputData(st.GetOutput())
    calc.AddVectorArrayName("U")
    calc.SetFunction("mag(U)")
    calc.SetResultArrayName("speed")
    calc.Update()
    tf = vtk.vtkTubeFilter()
    tf.SetInputData(calc.GetOutput())
    tf.SetRadius(0.15 if max_len > 200 else 0.08)
    tf.SetNumberOfSides(8)
    tf.Update()
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(tf.GetOutput())
    m.SetScalarModeToUsePointFieldData()
    m.SelectColorArray("speed")
    m.SetLookupTable(lut(VMAX))
    m.SetScalarRange(0, VMAX)
    a = vtk.vtkActor()
    a.SetMapper(m)
    return a


def surface(poly, clip, opacity):
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(P.clip_box(poly, clip))
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(0.72, 0.72, 0.76)
    a.GetProperty().SetOpacity(opacity)
    return a


def render(actors, eye, focus, scale, size, path, title):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for a in actors:
        ren.AddActor(a)
    bar = vtk.vtkScalarBarActor()
    bar.SetLookupTable(lut(VMAX))
    bar.SetTitle("air speed (m/s)")
    bar.SetNumberOfLabels(6)
    bar.SetWidth(0.07)
    bar.SetHeight(0.45)
    bar.SetPosition(0.9, 0.3)
    for tp in (bar.GetTitleTextProperty(), bar.GetLabelTextProperty()):
        tp.SetColor(0, 0, 0)
        tp.ShadowOff()
        tp.ItalicOff()
    ren.AddActor2D(bar)
    txt = vtk.vtkTextActor()
    txt.SetInput(title)
    txt.GetTextProperty().SetColor(0, 0, 0)
    txt.GetTextProperty().SetFontSize(22)
    txt.SetPosition(20, size[1] - 40)
    ren.AddActor2D(txt)
    cam = ren.GetActiveCamera()
    cam.SetPosition(*eye)
    cam.SetFocalPoint(*focus)
    cam.SetViewUp(0, 0, 1)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(scale)
    ren.ResetCameraClippingRange()
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.AddRenderer(ren)
    win.SetSize(*size)
    win.SetMultiSamples(8)
    win.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(win)
    w2i.Update()
    wr = vtk.vtkPNGWriter()
    wr.SetFileName(str(path))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()


def image_84(lpm=180):
    s = stage(FINAL, lpm)
    g = P.internal(FINAL, s["end"])
    walls = P.boundary(FINAL, s["end"], "walls")
    meta = json.loads((C.results_dir(FINAL) / "domain.json").read_text())
    cx, cy, ztop = meta["inlet"]["centre_mm"]
    rr = meta["inlet"]["radius_mm"] * 0.9
    seeds = [(cx, cy, ztop - 2.0)] + [(cx + rr * i / 6 * math.cos(2 * math.pi * j / (9 * i + 4)),
                                       cy + rr * i / 6 * math.sin(2 * math.pi * j / (9 * i + 4)), ztop - 2.0)
                                      for i in range(1, 7) for j in range(9 * i + 4)]
    tmp = [ROOT / "images" / f"_cfd84_{k}.png" for k in (0, 1)]
    render([streamlines(g, seeds, 700), surface(walls, (-24, 24, -62, 31, -80, 96), 0.10)],
           (-250, 230, 140), (0, -18, 2), 104, (1150, 1500), tmp[0], f"Hose to nozzle, {s['lpm']:.0f} L/min")
    near = [(sx * x, 5.0, z) for sx in (-1, 1) for x in np.linspace(13.2, 20.6, 6) for z in np.linspace(-69.8, -58.6, 7)]
    render([streamlines(g, near, 120), surface(walls, (-24, 24, 10, 34, -82, -62), 0.16)],
           (0, 200, -110), (0, 22, -76), 15, (1500, 1500), tmp[1],
           "Outlet from the front: the two jets meet at the nozzle")
    a, b = Image.open(tmp[0]), Image.open(tmp[1])
    sheet = Image.new("RGB", (a.width + b.width, max(a.height, b.height)), "white")
    sheet.paste(a, (0, 0))
    sheet.paste(b, (a.width, 0))
    out = IMAGES / "84_cfd_r41_streamlines.png"
    sheet.save(out)
    for t in tmp:
        t.unlink()
    return out


def main():
    names = [n for n in LABELS if (C.results_dir(n) / "analysis.json").exists() and n not in (BED, SQUARE_BED)]
    out, ops = image_81(names)
    print(out, json.dumps({k: v["lpm"] for k, v in ops.items()}))
    for f in (image_82, image_83, image_84, image_85, image_86):
        print(f())


if __name__ == "__main__":
    main()
