"""Post-process the CPAP duct CFD (session scratch; ported to the repo once settled).

For each case and stage time: inlet total pressure (system curve), the two jets' flows and speeds, air speed over
the fresh bead under the nozzle, turbulence in the jets; section plots, streamlines and the operating point
against the WS7040 blower curve.
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import matplotlib.tri as mtri  # noqa: E402

RHO, NU = 1.2, 1.5e-5
CASES = Path(__file__).parent / "results"
TIP_Z, NOZZLE_Y = -78.88, 22.7          # mm
JET_X = 10.3                            # just inside each jet's exit plane (|X| 10.2)
JET_WINDOW = (16.5, 29.0, -77.2, -73.3)  # Y and Z range of the jet passages at |X| 10.3 (no outside air)

# WS7040-24-V200 at 100 % PWM (Wonsmart P-Q curve): m3/h -> kPa
BLOWER = [(0, 6.75), (2, 6.4), (4, 6.0), (6, 5.45), (8, 4.5), (9, 4.25), (10, 4.0), (11, 3.6), (12, 3.3),
          (13, 3.05), (14, 2.6), (15, 2.3), (16, 2.0), (17, 1.75), (18, 1.45), (18.5, 1.0), (19, 0.6), (20, 0.25),
          (21.2, 0.0)]
HOSE = {"length_m": 1.0, "bore_mm": 19.0, "darcy_f": 0.06}   # 1 m standard corrugated CPAP hose


def blower_pa(lpm):
    q = np.array([p[0] for p in BLOWER]) * 1000 / 60
    return np.interp(lpm, q, np.array([p[1] for p in BLOWER]) * 1000)


def hose_pa(lpm, h=HOSE):
    a = math.pi / 4 * (h["bore_mm"] * 1e-3) ** 2
    v = lpm / 60000 / a
    return h["darcy_f"] * h["length_m"] / (h["bore_mm"] * 1e-3) * 0.5 * RHO * v * v


# ------------------------------------------------------------------ reading
def vtk_dir(case, t):
    hits = sorted((CASES / case / "VTK").glob(f"*_{t}"))
    if not hits:
        raise FileNotFoundError(f"{case} VTK for time {t}")
    return hits[0]


def read(path):
    r = vtk.vtkXMLUnstructuredGridReader() if str(path).endswith(".vtu") else vtk.vtkXMLPolyDataReader()
    r.SetFileName(str(path))
    r.Update()
    return r.GetOutput()


def to_mm(data):
    t = vtk.vtkTransform()
    t.Scale(1000, 1000, 1000)
    f = vtk.vtkTransformFilter()
    f.SetTransform(t)
    f.SetInputData(data)
    f.TransformAllInputVectorsOff()
    f.Update()
    return f.GetOutput()


def internal(case, t):
    return to_mm(read(vtk_dir(case, t) / "internal.vtu"))


def boundary(case, t, patch):
    return to_mm(read(vtk_dir(case, t) / "boundary" / f"{patch}.vtp"))


def inlet_history(case):
    f = sorted((CASES / case / "postProcessing" / "inletAvg").glob("*/surfaceFieldValue.dat"))[0]
    rows = [ln.split() for ln in f.read_text().splitlines() if ln and not ln.startswith("#")]
    return np.array([[float(v) for v in r[:3]] for r in rows])     # time, p, pTotal (kinematic)


# ------------------------------------------------------------------ geometry helpers
def cut(grid, origin, normal):
    plane = vtk.vtkPlane()
    plane.SetOrigin(*origin)
    plane.SetNormal(*normal)
    c = vtk.vtkCutter()
    c.SetCutFunction(plane)
    c.SetInputData(grid)
    c.Update()
    tri = vtk.vtkTriangleFilter()
    tri.SetInputData(c.GetOutput())
    tri.Update()
    return tri.GetOutput()


def clip_box(poly, b):
    box = vtk.vtkBox()
    box.SetBounds(*b)
    e = vtk.vtkExtractPolyDataGeometry()
    e.SetImplicitFunction(box)
    e.SetExtractInside(True)
    e.SetExtractBoundaryCells(False)
    e.SetInputData(poly)
    e.Update()
    return e.GetOutput()


def arrays(poly, name):
    return vtk_to_numpy(poly.GetPointData().GetArray(name))


def tri_arrays(poly):
    pts = vtk_to_numpy(poly.GetPoints().GetData())
    cells = vtk_to_numpy(poly.GetPolys().GetConnectivityArray()).reshape(-1, 3)
    return pts, cells


def cell_arrays(poly, name):
    return vtk_to_numpy(poly.GetCellData().GetArray(name))


def integrate_normal_flux(poly, normal):
    """Volume flow and area through a planar slice, from each cut cell's own value (not wall-interpolated)."""
    pts, tris = tri_arrays(poly)
    u = cell_arrays(poly, "U")
    p0, p1, p2 = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)          # mm2
    un = u @ np.array(normal)                                                  # m/s
    speed = np.linalg.norm(u, axis=1)
    k = cell_arrays(poly, "k")
    q = float((un * area).sum()) * 1e-6 * 60000                                 # L/min
    a = float(area.sum())
    down = -u[:, 2]
    horiz = np.hypot(u[:, 0], u[:, 1])
    return {"lpm": round(q, 2), "area_mm2": round(a, 2), "mean_ms": round(q / 60000 / (a * 1e-6), 2),
            "max_ms": round(float(speed.max()), 2),
            "turbulence_intensity": round(float((np.sqrt(2 * np.clip(k, 0, None) / 3) * area).sum()
                                                / max((speed * area).sum(), 1e-9)), 3),
            "mean_angle_below_horizontal_deg": round(math.degrees(math.atan2(float((down * un * area).sum()),
                                                                              float((horiz * un * area).sum()))), 1)}


def downflow_near_tip(g, z, radii=(1.5, 3.0, 5.0)):
    """Air passing down through a disc under the nozzle tip, by radius (L/min and share of the inlet flow)."""
    sl = clip_box(cut(g, (0, 0, z), (0, 0, 1)), (-12, 12, NOZZLE_Y - 12, NOZZLE_Y + 12, z - 1, z + 1))
    pts, tris = tri_arrays(sl)
    cen = pts[tris].mean(axis=1)
    r = np.hypot(cen[:, 0], cen[:, 1] - NOZZLE_Y)
    p0, p1, p2 = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
    uz = cell_arrays(sl, "U")[:, 2]
    return {f"r{rad:g}": round(float((np.clip(-uz, 0, None) * area)[r <= rad].sum()) * 1e-6 * 60000, 2) for rad in radii}


def probe(grid, points_mm):
    pts = vtk.vtkPoints()
    for p in points_mm:
        pts.InsertNextPoint(*p)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pr = vtk.vtkProbeFilter()
    pr.SetInputData(pd)
    pr.SetSourceData(grid)
    pr.Update()
    out = pr.GetOutput()
    valid = vtk_to_numpy(out.GetPointData().GetArray("vtkValidPointMask")).astype(bool)
    return vtk_to_numpy(out.GetPointData().GetArray("U")), valid


def ring(grid, z, r, n=72, centre=(0.0, NOZZLE_Y)):
    pts = [(centre[0] + r * math.cos(2 * math.pi * i / n), centre[1] + r * math.sin(2 * math.pi * i / n), z) for i in range(n)]
    u, ok = probe(grid, pts)
    s = np.linalg.norm(u, axis=1)[ok]
    return {"r_mm": r, "mean_ms": round(float(s.mean()), 2) if len(s) else None,
            "min_ms": round(float(s.min()), 2) if len(s) else None, "max_ms": round(float(s.max()), 2) if len(s) else None,
            "samples": int(ok.sum())}


# ------------------------------------------------------------------ analysis
SECTIONS = [   # name, plane axis, position, clip box (mm), flow direction normal
    ("hose", "z", 80.0, (-9, 9, -58, -39, 79, 81), (0, 0, -1)),
    ("spigot (P20 top)", "z", 12.0, (-9, 9, -58, -39, 11, 13), (0, 0, -1)),
    ("trunk (P20 lower)", "z", -12.0, (-21, 21, -49, -35, -13, -11), (0, 0, -1)),
    ("trunk (P21)", "z", -35.0, (-21, 21, -46, -33, -36, -34), (0, 0, -1)),
    ("side channels after the elbow", "y", -25.0, (-23, 23, -26, -24, -73, -55), (0, 1, 0)),
    ("side channels beside the hotend", "y", 5.0, None, (0, 1, 0)),
    ("jet exits", "x", None, None, None),
]


def total_pressure_section(g, axis, at, clip, normal):
    o = [0.0, 0.0, 0.0]
    o["xyz".index(axis)] = at
    sl = clip_box(cut(g, o, {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]), clip)
    return flux_weighted(sl, normal)


def flux_weighted(sl, normal):
    pts, tris = tri_arrays(sl)
    p0, p1, p2 = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)
    u = cell_arrays(sl, "U")
    p = cell_arrays(sl, "p")
    un = u @ np.array(normal)
    w = un * area
    pt = p + 0.5 * (u * u).sum(axis=1)
    return {"lpm": float(w.sum()) * 1e-6 * 60000, "pt": float((pt * w).sum() / w.sum()) * RHO,
            "dyn": float((0.5 * (u * u).sum(axis=1) * w).sum() / w.sum()) * RHO, "area_mm2": float(area.sum())}


def loss_breakdown(g):
    rows = []
    for name, axis, at, clip, normal in SECTIONS:
        if name == "side channels beside the hotend":
            parts = [total_pressure_section(g, "y", 5.0, clip, (0, 1, 0))
                     for clip in ((12.0, 21.6, 4, 6, -70.6, -57.6), (-21.6, -12.0, 4, 6, -70.6, -57.6))]
        elif name == "jet exits":
            parts = [flux_weighted(clip_box(cut(g, (x, 0, 0), (1, 0, 0)), (x - 1, x + 1) + JET_WINDOW), n)
                     for x, n in ((-JET_X, (1, 0, 0)), (JET_X, (-1, 0, 0)))]
        else:
            parts = [total_pressure_section(g, axis, at, clip, normal)]
        q = sum(p["lpm"] for p in parts)
        rows.append({"section": name, "lpm": round(q, 1),
                     "total_pressure_pa": round(sum(p["pt"] * p["lpm"] for p in parts) / q, 0),
                     "dynamic_pa": round(sum(p["dyn"] * p["lpm"] for p in parts) / q, 0),
                     "area_mm2": round(sum(p["area_mm2"] for p in parts), 1)})
    return rows


def analyse(case, t, lpm):
    g = internal(case, t)
    jets = {}
    for side, x, n in (("left", -JET_X, (1, 0, 0)), ("right", JET_X, (-1, 0, 0))):
        sl = clip_box(cut(g, (x, 0, 0), (1, 0, 0)), (x - 1, x + 1) + JET_WINDOW)
        jets[side] = integrate_normal_flux(sl, n)
    bead_z = TIP_Z - 0.1
    bead = [ring(g, bead_z, r) for r in (0.8, 1.2, 2.0, 3.0, 5.0)]
    far = [ring(g, TIP_Z - 2.0, r) for r in (10.0, 15.0, 20.0)]
    hist = inlet_history(case)
    last = hist[(hist[:, 0] > t - 100) & (hist[:, 0] <= t)]
    pt = float(last[:, 2].mean()) * RHO
    drift = float(last[:, 2].std() / max(abs(last[:, 2].mean()), 1e-9))
    return {"time": t, "lpm": lpm, "inlet_total_pa": round(pt, 1), "inlet_static_pa": round(float(last[:, 1].mean()) * RHO, 1),
            "inlet_total_rel_std_last100": round(drift, 5), "jets": jets,
            "jets_sum_lpm": round(jets["left"]["lpm"] + jets["right"]["lpm"], 2),
            "split_left_pct": round(100 * jets["left"]["lpm"] / max(jets["left"]["lpm"] + jets["right"]["lpm"], 1e-9), 1),
            "bead_ring_z_mm": bead_z, "bead_rings": bead, "far_rings_z_mm": TIP_Z - 2.0, "far_rings": far,
            "down_past_tip_lpm": downflow_near_tip(g, TIP_Z - 0.1),
            "loss_breakdown": loss_breakdown(g)}


# ------------------------------------------------------------------ operating point
def fit_power(rows):
    q = np.array([r["lpm"] for r in rows])
    p = np.array([r["inlet_total_pa"] for r in rows])
    n, lnc = np.polyfit(np.log(q), np.log(p), 1)
    return math.exp(lnc), n


def operating_point(rows, hose=True):
    c, n = fit_power(rows)
    lo, hi = 1.0, 354.0
    f = lambda q: blower_pa(q) - (hose_pa(q) if hose else 0.0) - c * q ** n   # noqa: E731
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if f(mid) > 0 else (lo, mid)
    q = 0.5 * (lo + hi)
    return {"lpm": round(q, 1), "duct_pa": round(c * q ** n, 0), "hose_pa": round(hose_pa(q) if hose else 0.0, 0),
            "blower_pa": round(float(blower_pa(q)), 0), "fit": {"c": c, "n": round(n, 3)}}


# ------------------------------------------------------------------ plots
def plane_slice(g, axis, at):
    n = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    o = [0.0, 0.0, 0.0]
    o["xyz".index(axis)] = at
    return cut(g, o, n)


def section_plot(ax, g, axis, at, window, field="speed", vmax=None, arrows=True, cmap="turbo", title=""):
    h, v = {"x": (1, 2), "y": (0, 2), "z": (0, 1)}[axis]
    sl = plane_slice(g, axis, at)
    pts, tris = tri_arrays(sl)
    if field == "speed":
        val = np.linalg.norm(arrays(sl, "U"), axis=1)
        label = "air speed (m/s)"
    elif field == "p":
        val = arrays(sl, "p") * RHO
        label = "static pressure (Pa)"
    elif field == "ti":
        val = np.sqrt(2 * np.clip(arrays(sl, "k"), 0, None) / 3)
        label = "turbulent velocity fluctuation u' = sqrt(2k/3) (m/s)"
    elif field == "k":
        val = np.clip(arrays(sl, "k"), 0, None)
        label = "turbulent kinetic energy k (m2/s2)"
    ax.set_facecolor("#c8c8c8")
    tr = mtri.Triangulation(pts[:, h], pts[:, v], tris)
    pc = ax.tripcolor(tr, val, shading="gouraud", cmap=cmap, vmin=0 if field != "p" else None, vmax=vmax,
                      rasterized=True)
    if arrows:
        xs = np.linspace(window[0], window[1], 34)
        ys = np.linspace(window[2], window[3], int(34 * (window[3] - window[2]) / (window[1] - window[0])) + 2)
        X, Y = np.meshgrid(xs, ys)
        P = np.zeros((X.size, 3))
        P[:, h], P[:, v], P[:, "xyz".index(axis)] = X.ravel(), Y.ravel(), at
        u, ok = probe(g, P)
        su = np.where(ok, u[:, h], np.nan)
        sv = np.where(ok, u[:, v], np.nan)
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
    cb = plt.colorbar(pc, ax=ax, shrink=0.85, pad=0.02)
    cb.set_label(label)
    return pc



# ------------------------------------------------------------------ 3D streamlines (VTK, off screen)
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


def streamlines(g, seeds_mm, max_len=600.0):
    pts = vtk.vtkPoints()
    for p in seeds_mm:
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
    return calc.GetOutput()


def render(actors, eye, focus, up, out, size=(1500, 1100), parallel_scale=None, bar=None):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for a in actors:
        ren.AddActor(a)
    if bar is not None:
        ren.AddActor2D(bar)
    cam = ren.GetActiveCamera()
    cam.SetPosition(*eye)
    cam.SetFocalPoint(*focus)
    cam.SetViewUp(*up)
    if parallel_scale:
        cam.ParallelProjectionOn()
        cam.SetParallelScale(parallel_scale)
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
    wr.SetFileName(str(out))
    wr.SetInputConnection(w2i.GetOutputPort())
    wr.Write()


def tube_actor(lines, table, radius=0.12):
    tf = vtk.vtkTubeFilter()
    tf.SetInputData(lines)
    tf.SetRadius(radius)
    tf.SetNumberOfSides(8)
    tf.Update()
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(tf.GetOutput())
    m.SetScalarModeToUsePointFieldData()
    m.SelectColorArray("speed")
    m.SetLookupTable(table)
    m.SetScalarRange(table.GetRange())
    m.ScalarVisibilityOn()
    a = vtk.vtkActor()
    a.SetMapper(m)
    return a


def surface_actor(poly, colour=(0.75, 0.75, 0.78), opacity=0.18, clip=None):
    if clip is not None:
        poly = clip_box(poly, clip)
    m = vtk.vtkPolyDataMapper()
    m.SetInputData(poly)
    m.ScalarVisibilityOff()
    a = vtk.vtkActor()
    a.SetMapper(m)
    a.GetProperty().SetColor(*colour)
    a.GetProperty().SetOpacity(opacity)
    return a


def scalar_bar(table, title):
    b = vtk.vtkScalarBarActor()
    b.SetLookupTable(table)
    b.SetTitle(title)
    b.SetNumberOfLabels(6)
    b.SetWidth(0.07)
    b.SetHeight(0.5)
    b.SetPosition(0.9, 0.25)
    for tp in (b.GetTitleTextProperty(), b.GetLabelTextProperty()):
        tp.SetColor(0, 0, 0)
        tp.ShadowOff()
        tp.ItalicOff()
    return b


def inlet_seeds(meta, n_rings=6, per_ring=18, depth=2.0):
    cx, cy, ztop = meta["inlet"]["centre_mm"]
    r = meta["inlet"]["radius_mm"] * 0.9
    seeds = [(cx, cy, ztop - depth)]
    for i in range(1, n_rings + 1):
        rr = r * i / n_rings
        m = per_ring * i // 2 + 4
        seeds += [(cx + rr * math.cos(2 * math.pi * j / m), cy + rr * math.sin(2 * math.pi * j / m), ztop - depth)
                  for j in range(m)]
    return seeds


def main(case):
    stages = json.loads((CASES / case / "stages.json").read_text())["stages"]
    out = [analyse(case, s["end"], s["lpm"]) for s in stages]
    (CASES / case / "analysis.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
