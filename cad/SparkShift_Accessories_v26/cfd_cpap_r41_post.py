"""Revision 41 CPAP CFD: post-processing of the OpenFOAM results (VTK from foamToVTK, postProcessing/ from the run).

Per case and flow stage: the total pressure at P20's spigot (the duct's system curve), each jet's flow, area, speed,
direction and turbulence, the air passing down by the nozzle tip and its speed over the fresh bead, where the jets'
air leaves the space round the nozzle, and where the pressure goes along the duct (flux-weighted total pressure at
seven sections). Flows through slices use each cut cell's own value; points sampled off the cut planes use VTK's
interpolation.
"""
import json
import math

import numpy as np
import vtk
from vtk.util.numpy_support import vtk_to_numpy

import cfd_cpap_r41 as C

SECTIONS = [   # name, plane axis, position (mm), clip box (mm), flow direction
    ("hose section", "z", 80.0, (-9, 9, -58, -39, 79, 81), (0, 0, -1)),
    ("spigot (P20 top)", "z", 12.0, (-9, 9, -58, -39, 11, 13), (0, 0, -1)),
    ("trunk (P20 lower)", "z", -12.0, (-21, 21, -49, -35, -13, -11), (0, 0, -1)),
    ("trunk (P21)", "z", -35.0, (-21, 21, -46, -33, -36, -34), (0, 0, -1)),
    ("side channels after the elbow", "y", -25.0, (-23, 23, -26, -24, -73, -55), (0, 1, 0)),
    ("side channels beside the hotend", "y", 5.0, None, (0, 1, 0)),
    ("jet exits", "x", None, None, None),
]
FINAL, SQUARE, RELEASED = "r41bm_bambu", "r41_bambu", "released_bambu"
LABELS = {RELEASED: "Released duct (revision 40), Bambu",
          SQUARE: "Revision 41, square-edged jets, Bambu",
          FINAL: "Revision 41, bell-mouth jets, Bambu",
          "r41bm_redlizard": "Revision 41, bell-mouth jets, Red Lizard",
          "r41bm_bambu_bed": "Bell-mouth jets, Bambu, print surface 0.2 mm under the nozzle",
          "r41sq_bambu_bed": "Square-edged jets, Bambu, print surface 0.2 mm under the nozzle",
          "r41lip_bambu": "Study: bell-mouth over the whole jet, Bambu",
          "r41lip_bambu_rough": "Study, 0.1 mm rough walls",
          "r41lip_bambu_rough3": "Study, 0.3 mm rough walls",
          "r41_bambu_fine": "Square-edged jets, Bambu, finer mesh"}


# ------------------------------------------------------------------ reading
def vtk_dir(name, t):
    hits = sorted((C.results_dir(name) / "VTK").glob(f"*_{t}"))
    if not hits:
        raise FileNotFoundError(f"{name}: no VTK for time {t}")
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


def internal(name, t):
    return to_mm(read(vtk_dir(name, t) / "internal.vtu"))


def boundary(name, t, patch):
    return to_mm(read(vtk_dir(name, t) / "boundary" / f"{patch}.vtp"))


def inlet_history(name):
    f = sorted((C.results_dir(name) / "postProcessing" / "inletAvg").glob("*/surfaceFieldValue.dat"))[0]
    rows = [ln.split() for ln in f.read_text().splitlines() if ln and not ln.startswith("#")]
    return np.array([[float(v) for v in r[:3]] for r in rows])      # iteration, p, pTotal (kinematic)


def stages(name):
    return json.loads((C.results_dir(name) / "stages.json").read_text())["stages"]


def mesh_stats(name):
    text = (C.results_dir(name) / "log.checkMesh").read_text()
    out = {}
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("cells:"):
            out["cells"] = int(s.split()[1])
        elif s.startswith("Mesh non-orthogonality Max:"):
            out["max_non_orthogonality_deg"] = round(float(s.split()[3]), 1)
        elif s.startswith("Max skewness"):
            out["max_skewness"] = round(float(s.split()[3]), 2)
        elif "Total volume" in s:
            out["volume_mm3"] = round(float(s.split("Total volume =")[1].split(".  ")[0]) * 1e9, 0)
    out["mesh_ok"] = "Mesh OK." in text
    return out


# ------------------------------------------------------------------ slices
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


def plane_slice(grid, axis, at):
    o = [0.0, 0.0, 0.0]
    o["xyz".index(axis)] = at
    return cut(grid, o, {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis])


def clip_box(poly, b):
    bx = vtk.vtkBox()
    bx.SetBounds(*b)
    e = vtk.vtkExtractPolyDataGeometry()
    e.SetImplicitFunction(bx)
    e.SetExtractInside(True)
    e.SetExtractBoundaryCells(False)
    e.SetInputData(poly)
    e.Update()
    return e.GetOutput()


def point_array(poly, name):
    return vtk_to_numpy(poly.GetPointData().GetArray(name))


def cell_array(poly, name):
    return vtk_to_numpy(poly.GetCellData().GetArray(name))


def triangles(poly):
    pts = vtk_to_numpy(poly.GetPoints().GetData())
    tris = vtk_to_numpy(poly.GetPolys().GetConnectivityArray()).reshape(-1, 3)
    p0, p1, p2 = pts[tris[:, 0]], pts[tris[:, 1]], pts[tris[:, 2]]
    return pts, tris, 0.5 * np.linalg.norm(np.cross(p1 - p0, p2 - p0), axis=1)


def jet_flux(poly, normal):
    _, _, area = triangles(poly)
    u = cell_array(poly, "U")
    un = u @ np.array(normal)
    speed = np.linalg.norm(u, axis=1)
    k = np.clip(cell_array(poly, "k"), 0, None)
    q = float((un * area).sum()) * 1e-6 * 60000
    a = float(area.sum())
    w = un * area
    return {"lpm": round(q, 2), "area_mm2": round(a, 2), "mean_ms": round(q / 60000 / (a * 1e-6), 2),
            "max_ms": round(float(speed.max()), 2),
            "turbulence_intensity": round(float((np.sqrt(2 * k / 3) * area).sum() / (speed * area).sum()), 3),
            "angle_below_horizontal_deg": round(math.degrees(math.atan2(float((-u[:, 2] * w).sum()),
                                                                         float((np.hypot(u[:, 0], u[:, 1]) * w).sum()))), 1)}


def flux_weighted(poly, normal):
    _, _, area = triangles(poly)
    u = cell_array(poly, "U")
    p = cell_array(poly, "p")
    w = (u @ np.array(normal)) * area
    pt = p + 0.5 * (u * u).sum(axis=1)
    return {"lpm": float(w.sum()) * 1e-6 * 60000, "pt": float((pt * w).sum() / w.sum()) * C.RHO,
            "dyn": float((0.5 * (u * u).sum(axis=1) * w).sum() / w.sum()) * C.RHO, "area_mm2": float(area.sum())}


def jet_slices(g):
    return [(side, clip_box(cut(g, (x, 0, 0), (1, 0, 0)), (x - 1, x + 1) + C.JET_WINDOW), n)
            for side, x, n in (("left", -C.JET_X, (1, 0, 0)), ("right", C.JET_X, (-1, 0, 0)))]


def loss_breakdown(g):
    rows = []
    for name, axis, at, clip, normal in SECTIONS:
        if name == "side channels beside the hotend":
            parts = [flux_weighted(clip_box(plane_slice(g, "y", 5.0), b), (0, 1, 0))
                     for b in ((12.0, 21.6, 4, 6, -70.6, -57.6), (-21.6, -12.0, 4, 6, -70.6, -57.6))]
        elif name == "jet exits":
            parts = [flux_weighted(sl, n) for _, sl, n in jet_slices(g)]
        else:
            parts = [flux_weighted(clip_box(plane_slice(g, axis, at), clip), normal)]
        q = sum(p["lpm"] for p in parts)
        rows.append({"section": name, "lpm": round(q, 1),
                     "total_pressure_pa": round(sum(p["pt"] * p["lpm"] for p in parts) / q),
                     "dynamic_pa": round(sum(p["dyn"] * p["lpm"] for p in parts) / q),
                     "area_mm2": round(sum(p["area_mm2"] for p in parts), 1)})
    return rows


def probe(g, points):
    pts = vtk.vtkPoints()
    for p in points:
        pts.InsertNextPoint(*p)
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pr = vtk.vtkProbeFilter()
    pr.SetInputData(pd)
    pr.SetSourceData(g)
    pr.Update()
    out = pr.GetOutput()
    ok = vtk_to_numpy(out.GetPointData().GetArray("vtkValidPointMask")).astype(bool)
    return vtk_to_numpy(out.GetPointData().GetArray("U")), ok


def ring(g, z, r, n=72):
    pts = [(r * math.cos(2 * math.pi * i / n), C.NOZZLE_Y + r * math.sin(2 * math.pi * i / n), z) for i in range(n)]
    u, ok = probe(g, pts)
    s = np.linalg.norm(u, axis=1)[ok]
    return {"r_mm": r, "samples": int(ok.sum()), "mean_ms": round(float(s.mean()), 2) if len(s) else None,
            "min_ms": round(float(s.min()), 2) if len(s) else None, "max_ms": round(float(s.max()), 2) if len(s) else None}


def down_past_tip(g, z, radii=(1.5, 3.0, 5.0)):
    sl = clip_box(cut(g, (0, 0, z), (0, 0, 1)), (-12, 12, C.NOZZLE_Y - 12, C.NOZZLE_Y + 12, z - 1, z + 1))
    pts, tris, area = triangles(sl)
    cen = pts[tris].mean(axis=1)
    r = np.hypot(cen[:, 0], cen[:, 1] - C.NOZZLE_Y)
    down = np.clip(-cell_array(sl, "U")[:, 2], 0, None) * area
    return {f"r{rad:g}_mm": round(float(down[r <= rad].sum()) * 1e-6 * 60000, 2) for rad in radii}


NOZZLE_BOX = (-10.15, 10.15, 14.0, 29.5, -79.0, -72.0)   # around the nozzle, inside the hotend slot's walls


def box_outflow(g, b=NOZZLE_BOX):
    """Net outflow (L/min) through each face of box b. The jets come in through its X faces (negative)."""
    faces = {"x-": ("x", b[0], (-1, 0, 0), (b[0] - 0.5, b[0] + 0.5, b[2], b[3], b[4], b[5])),
             "x+": ("x", b[1], (1, 0, 0), (b[1] - 0.5, b[1] + 0.5, b[2], b[3], b[4], b[5])),
             "back": ("y", b[2], (0, -1, 0), (b[0], b[1], b[2] - 0.5, b[2] + 0.5, b[4], b[5])),
             "front": ("y", b[3], (0, 1, 0), (b[0], b[1], b[3] - 0.5, b[3] + 0.5, b[4], b[5])),
             "down": ("z", b[4], (0, 0, -1), (b[0], b[1], b[2], b[3], b[4] - 0.5, b[4] + 0.5)),
             "up": ("z", b[5], (0, 0, 1), (b[0], b[1], b[2], b[3], b[5] - 0.5, b[5] + 0.5))}
    out = {}
    for k, (axis, at, n, clip) in faces.items():
        sl = clip_box(plane_slice(g, axis, at), clip)
        if sl.GetNumberOfCells() == 0:
            out[k] = 0.0
            continue
        _, _, area = triangles(sl)
        out[k] = round(float(((cell_array(sl, "U") @ np.array(n)) * area).sum()) * 1e-6 * 60000, 2)
    leaving = sum(max(v, 0.0) for k, v in out.items() if k not in ("x-", "x+"))
    out["share_pct"] = {k: round(100 * max(out[k], 0.0) / leaving, 1) for k in ("down", "front", "up", "back")}
    return out


def analyse(name, t, lpm, bed=False):
    g = internal(name, t)
    jets = {side: jet_flux(sl, n) for side, sl, n in jet_slices(g)}
    hist = inlet_history(name)
    last = hist[(hist[:, 0] > t - 100) & (hist[:, 0] <= t)]
    bead_z = C.NOZZLE_TIP_Z - 0.1
    q_jets = jets["left"]["lpm"] + jets["right"]["lpm"]
    return {"iteration": t, "lpm": lpm,
            "inlet_total_pa": round(float(last[:, 2].mean()) * C.RHO, 1),
            "inlet_static_pa": round(float(last[:, 1].mean()) * C.RHO, 1),
            "inlet_total_relative_spread_last_100": round(float(last[:, 2].std() / abs(last[:, 2].mean())), 5),
            "jets": jets, "jets_sum_lpm": round(q_jets, 2), "split_left_pct": round(100 * jets["left"]["lpm"] / q_jets, 1),
            "bead_z_mm": round(bead_z, 2), "bead_rings": [ring(g, bead_z, r) for r in (0.8, 1.2, 2.0, 3.0, 5.0)],
            "below_tip_2mm_rings": [ring(g, C.NOZZLE_TIP_Z - 2.0, r) for r in (10.0, 15.0, 20.0)] if not bed else None,
            "down_past_tip_lpm": down_past_tip(g, bead_z) if not bed else None,
            "nozzle_box_outflow_lpm": box_outflow(g),
            "loss_breakdown": loss_breakdown(g)}


def analyse_case(name):
    meta = json.loads((C.results_dir(name) / "domain.json").read_text())
    out = [analyse(name, s["end"], s["lpm"], meta["bed"]) for s in stages(name)]
    (C.results_dir(name) / "analysis.json").write_text(json.dumps(out, indent=1))
    return out


def scaled(row, q):
    """A stage's jet figures carried to flow q: at these Reynolds numbers speeds scale with flow."""
    f = q / row["lpm"]
    return {"from_stage_lpm": row["lpm"], "jet_mean_ms": round(row["jets"]["left"]["mean_ms"] * f, 1),
            "jet_max_ms": round(max(row["jets"]["left"]["max_ms"], row["jets"]["right"]["max_ms"]) * f, 1),
            "bead_speed_ms_r1.2": round(row["bead_rings"][1]["mean_ms"] * f, 1)}


def report(names):
    cases, ops = {}, {}
    for name in names:
        rows = json.loads((C.results_dir(name) / "analysis.json").read_text())
        meta = json.loads((C.results_dir(name) / "domain.json").read_text())
        st = json.loads((C.results_dir(name) / "stages.json").read_text())
        entry = {"label": LABELS.get(name, name), "duct": meta["duct"], "tool": meta["tool"],
                 "print_surface": meta["bed"], "mesh": mesh_stats(name),
                 "wall_levels": st.get("wall_levels"), "wall_roughness_mm": st.get("wall_roughness_mm", 0.0),
                 "stages": rows}
        if len(rows) >= 2:
            op = C.operating_point(rows)
            op_free = C.operating_point(rows, hose=False)
            near = min(rows, key=lambda r: abs(r["lpm"] - op["lpm"]))
            entry["operating_point_1m_hose"] = dict(op, **scaled(near, op["lpm"]))
            entry["operating_point_no_hose"] = op_free
            ops[name] = op["lpm"]
        cases[name] = entry
    out = {"method": {
        "solver": "OpenFOAM v2512 simpleFoam (steady, incompressible), meshed with snappyHexMesh",
        "turbulence": "RANS k-omega SST; inlet 5 % intensity, mixing length 0.07 x the 16.4 mm bore; "
                      "nutUSpalding and blended omega wall functions",
        "schemes": "300 iterations first-order upwind, then linearUpwindV for U and limitedLinear for k and omega",
        "air": {"nu_m2s": C.NU, "rho_kgm3": C.RHO},
        "domain": "P20-P22 air from the hose spigot to the jets, a 4-bore hose section, and the open air around "
                  "the nozzle (X +-30, Y -20..50, Z -95..-45 mm) with the tool, P01, P23, the Beacon and screws as "
                  "obstacles; its faces are open to the room (total pressure 0)",
        "blower": "WS7040-24-V200 at 100 % PWM, Wonsmart's published P-Q curve",
        "hose_allowance": C.HOSE},
        "cases": cases, "operating_points": ops}
    gains = {"bell_mouth_vs_square_edged": (FINAL, SQUARE), "bell_mouth_vs_released": (FINAL, RELEASED),
             "square_edged_vs_released": (SQUARE, RELEASED)}
    out["flow_gain_pct"] = {k: round(100 * (ops[a] / ops[b] - 1), 1) for k, (a, b) in gains.items()
                            if a in ops and b in ops}

    def at_180(n):
        return next(r for r in cases[n]["stages"] if r["lpm"] == 180.0)["inlet_total_pa"]
    for key, (a, b) in (("mesh_check_180lpm", (SQUARE, "r41_bambu_fine")),
                        ("roughness_0.1mm_check_180lpm", ("r41lip_bambu", "r41lip_bambu_rough")),
                        ("roughness_0.3mm_check_180lpm", ("r41lip_bambu", "r41lip_bambu_rough3")),
                        ("bell_mouth_length_study_180lpm", (FINAL, "r41lip_bambu"))):
        if a in cases and b in cases:
            out[key] = {"base_pa": at_180(a), "variant_pa": at_180(b),
                        "difference_pct": round(100 * (at_180(b) / at_180(a) - 1), 2)}
    return out
