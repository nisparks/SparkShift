"""Centre/side outlet balance for a C28 CFD result: where each outlet's air goes and where the pressure goes.

Usage: python cfd_outlet_balance_r43.py <case> [--mean]
Run cfd_cpap_r43.py analyse <case> first. --mean uses the iteration-averaged fields (UMean, pMean) of a case
written with cfd_cpap_r41.py case --average-from; otherwise the final snapshot. Writes
results/<case>/outlet_balance[_mean].json and its streamlines (outlet_streamlines[_mean].vtp).

- Outlets: the two side jets (cut inside their exits, as cfd_cpap_r41_post) and the rear centre slot (a plane
  normal to its aim, just upstream of the whole curved mouth, restricted to the slot's own air).
- Pressure budget: flux-weighted total pressure at sections along the side path and the centre branch.
- Delivery: streamlines seeded in proportion to each outlet's flux; the share that passes within 1 mm of the
  print surface inside 5 / 10 mm of the nozzle axis, and where the rest leaves. Steady-field streamlines are
  a transport picture, not particle residence or heat transfer.
"""
import argparse
import json
import math

import cadquery as cq
import numpy as np
import trimesh
import vtk
from vtk.util.numpy_support import numpy_to_vtk, vtk_to_numpy

import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import cfd_cpap_r43 as A
import r43_swept_feed as F

ROOF_RAISE, MOUTH_HEIGHT, ANGLE = 3.0, 0.9, 28.0     # C28's centre slot, as built for the cleaned C28 baseline
BED_Z = C.NOZZLE_TIP_Z - C.BED_GAP
SEEDS = 600


def load(name, mean=False):
    grid = P.internal(name, 1200)
    if mean:
        for data in (grid.GetPointData(), grid.GetCellData()):
            for source, target in (("UMean", "U"), ("pMean", "p")):
                array = data.GetArray(source)
                if array is None:
                    raise ValueError(f"{name}: no {source}; write the case with --average-from")
                copy = array.NewInstance()
                copy.DeepCopy(array)
                copy.SetName(target)
                data.RemoveArray(target)
                data.AddArray(copy)
    return grid


def solid_mesh(shape):
    vertices, triangles = shape.tessellate(.02, .1)
    return trimesh.Trimesh([(v.x, v.y, v.z) for v in vertices], triangles, process=True)


def keep_inside(poly, solid):
    """The cut's triangles whose centroids lie inside a solid."""
    pts, tris, _ = P.triangles(poly)
    return select_cells(poly, solid.contains(pts[tris].mean(axis=1)))


def slot_section(g, passage):
    direction = np.array([0, math.cos(math.radians(ANGLE)), -math.sin(math.radians(ANGLE))])
    mouth = F.mouth(F.HALF_WIDTH)
    origin = np.array([mouth.x, mouth.y, mouth.z]) - .6 * direction
    cut = P.clip_box(P.cut(g, origin, direction), (-9.8, 9.8, 2, 16, -78, -66))
    return keep_inside(cut, passage), tuple(direction)


def flux_stats(poly, normal):
    row = P.jet_flux(poly, normal)
    row.update({k: v for k, v in P.flux_weighted(poly, normal).items() if k in ("pt", "dyn")})
    return row


def outlets(g, passage):
    slices = {side: (poly, n) for side, poly, n in P.jet_slices(g)}
    rows = {side: flux_stats(poly, n) for side, (poly, n) in slices.items()}
    slot, normal = slot_section(g, passage)
    rows["centre"] = flux_stats(slot, normal)
    pts, tris, area = P.triangles(slot)
    x = pts[tris].mean(axis=1)[:, 0]
    flux = (P.cell_array(slot, "U") @ np.array(normal)) * area * 1e-6 * 60000
    edges = np.arange(-10, 10.01, 2)
    rows["centre"]["spanwise_lpm_per_2mm"] = {f"{a:+.0f}..{b:+.0f}": round(float(flux[(x >= a) & (x < b)].sum()), 2)
                                               for a, b in zip(edges[:-1], edges[1:])}
    total = sum(rows[k]["lpm"] for k in ("left", "right", "centre"))
    for key in ("left", "right", "centre"):
        rows[key]["share_pct"] = round(100 * rows[key]["lpm"] / total, 1)
        rows[key]["momentum_mN"] = round(C.RHO * rows[key]["lpm"] / 60000 * rows[key]["mean_ms"] * 1000, 1)
    return rows, {"left": slices["left"][0], "right": slices["right"][0], "centre": slot}, normal


def section(g, axis, at, box, normal, solid=None):
    poly = P.clip_box(P.plane_slice(g, axis, at), box)
    if solid is not None:
        poly = keep_inside(poly, solid)
    return P.flux_weighted(poly, normal)


def select_cells(poly, keep):
    ids = vtk.vtkIdTypeArray()
    for i in np.flatnonzero(keep):
        ids.InsertNextValue(int(i))
    node = vtk.vtkSelectionNode()
    node.SetFieldType(vtk.vtkSelectionNode.CELL)
    node.SetContentType(vtk.vtkSelectionNode.INDICES)
    node.SetSelectionList(ids)
    selection = vtk.vtkSelection()
    selection.AddNode(node)
    extract = vtk.vtkExtractSelection()
    extract.SetInputData(0, poly)
    extract.SetInputData(1, selection)
    extract.Update()
    surface = vtk.vtkGeometryFilter()
    surface.SetInputData(extract.GetOutput())
    surface.Update()
    return surface.GetOutput()


def budget(g, feeds, outlet_rows):
    side = [
        ("hose", ("z", 80.0, (-9, 9, -58, -39, 79, 81), (0, 0, -1))),
        ("P20 spigot", ("z", 12.0, (-9, 9, -58, -39, 11, 13), (0, 0, -1))),
        ("P20 lower", ("z", -12.0, (-21, 21, -49, -35, -13, -11), (0, 0, -1))),
        ("P21 trunk", ("z", -35.0, (-21, 21, -46, -33, -36, -34), (0, 0, -1))),
        ("P21 above joint", ("z", -46.0, (-23, 23, -47, -26, -46.5, -45.5), (0, 0, -1))),
        ("P22 lobes", ("z", -56.0, (-23, 23, -47, -26, -56.5, -55.5), (0, 0, -1))),
        ("after elbow", ("y", -25.0, (-23, 23, -26, -24, -73, -55), (0, 1, 0))),
        ("before centre take-off", ("y", -12.0, (-23, 23, -13, -11, -75, -55), (0, 1, 0))),
    ]
    rows = []
    for name, (axis, at, box, normal) in side:
        rows.append({"station": name, **section(g, axis, at, box, normal)})
    parts = [P.flux_weighted(P.clip_box(P.plane_slice(g, "y", 5.0), b), (0, 1, 0))
             for b in ((12.0, 21.6, 4, 6, -70.6, -57.6), (-21.6, -12.0, 4, 6, -70.6, -57.6))]
    rows.append({"station": "side channels beside hotend", **merge(parts)})
    rows.append({"station": "side jet exits", **merge([outlet_rows["left"], outlet_rows["right"]],
                                                      keys=("lpm", "pt", "dyn"))})
    centre = [{"station": "centre feeds (Y -2)", **section(g, "y", -2.0, (-14, 14, -3, -1, -75, -58), (0, 1, 0),
                                                           solid=feeds)},
              {"station": "centre trunk (Y 4.25)", **P.flux_weighted(
                  P.clip_box(P.plane_slice(g, "y", 4.25), (-9.2, 9.2, 4.15, 4.35, -72.8, -67)), (0, 1, 0))},
              {"station": "centre slot exit", **{k: outlet_rows["centre"][k] for k in ("lpm", "pt", "dyn")}}]
    return {"side_path": clean(rows), "centre_branch": clean(centre)}


def merge(parts, keys=("lpm", "pt", "dyn", "area_mm2")):
    q = sum(p["lpm"] for p in parts)
    out = {"lpm": q, "pt": sum(p["pt"] * p["lpm"] for p in parts) / q, "dyn": sum(p["dyn"] * p["lpm"] for p in parts) / q}
    if "area_mm2" in keys:
        out["area_mm2"] = sum(p["area_mm2"] for p in parts)
    return out


def clean(rows):
    return [{k: (round(v, 2) if isinstance(v, float) else v) for k, v in r.items()} for r in rows]


def seeds_for(poly, normal, n, rng):
    pts, tris, area = P.triangles(poly)
    flux = np.clip((P.cell_array(poly, "U") @ np.array(normal)) * area, 0, None)
    pick = rng.choice(len(tris), size=n, p=flux / flux.sum())
    a, b = rng.random((2, n))
    flip = a + b > 1
    a[flip], b[flip] = 1 - a[flip], 1 - b[flip]
    corners = pts[tris[pick]]
    return corners[:, 0] + a[:, None] * (corners[:, 1] - corners[:, 0]) + b[:, None] * (corners[:, 2] - corners[:, 0])


def delivery(g, sections, normal_by_outlet, outlet_rows, n_seeds=SEEDS):
    rng = np.random.default_rng(28)
    seeds, labels = [], []
    for key in ("left", "right", "centre"):
        s = seeds_for(sections[key], normal_by_outlet[key], n_seeds, rng)
        seeds.append(s)
        labels += [key] * len(s)
    seeds = np.vstack(seeds)
    points = vtk.vtkPoints()
    points.SetData(numpy_to_vtk(seeds.astype(np.float64), deep=True))
    source = vtk.vtkPolyData()
    source.SetPoints(points)
    tracer = vtk.vtkStreamTracer()
    tracer.SetInputData(g)
    tracer.SetSourceData(source)
    tracer.SetInterpolatorTypeToCellLocator()
    tracer.SetInputArrayToProcess(0, 0, 0, vtk.vtkDataObject.FIELD_ASSOCIATION_POINTS, "U")
    tracer.SetIntegratorTypeToRungeKutta45()
    tracer.SetIntegrationDirectionToForward()
    tracer.SetIntegrationStepUnit(vtk.vtkStreamTracer.LENGTH_UNIT)
    tracer.SetInitialIntegrationStep(.05)
    tracer.SetMinimumIntegrationStep(.01)
    tracer.SetMaximumIntegrationStep(.25)
    tracer.SetMaximumPropagation(120)
    tracer.SetMaximumNumberOfSteps(6000)
    tracer.SetTerminalSpeed(.05)
    tracer.Update()
    lines = tracer.GetOutput()
    seed_ids = vtk_to_numpy(lines.GetCellData().GetArray("SeedIds"))
    xyz = vtk_to_numpy(lines.GetPoints().GetData())
    fate = {k: {"r5_mm": 0, "r10_mm": 0, "up": 0, "front": 0, "back": 0, "sideways": 0, "stalled": 0, "traced": 0}
            for k in ("left", "right", "centre")}
    source_label = np.empty(lines.GetNumberOfCells(), dtype=object)
    for cell in range(lines.GetNumberOfCells()):
        ids = lines.GetCell(cell).GetPointIds()
        path = xyz[[ids.GetId(i) for i in range(ids.GetNumberOfIds())]]
        key = labels[int(seed_ids[cell])]
        source_label[cell] = key
        r = np.hypot(path[:, 0], path[:, 1] - C.NOZZLE_Y)
        low = path[:, 2] <= BED_Z + 1.0
        row = fate[key]
        row["traced"] += 1
        row["r5_mm"] += bool(np.any(low & (r <= 5)))
        row["r10_mm"] += bool(np.any(low & (r <= 10)))
        end = path[-1]
        if end[2] > -70:
            row["up"] += 1
        elif end[1] > C.NOZZLE_Y + 12:
            row["front"] += 1
        elif end[1] < C.NOZZLE_Y - 14:
            row["back"] += 1
        elif abs(end[0]) > 14:
            row["sideways"] += 1
        else:
            row["stalled"] += 1
    out = {}
    for key, row in fate.items():
        n = max(row["traced"], 1)
        q = outlet_rows[key]["lpm"]
        out[key] = {"traced_lines": row["traced"],
                    **{f"{k}_pct": round(100 * row[k] / n, 1) for k in ("r5_mm", "r10_mm", "up", "front", "back",
                                                                          "sideways", "stalled")},
                    "lpm_reaching_r5": round(q * row["r5_mm"] / n, 1), "lpm_reaching_r10": round(q * row["r10_mm"] / n, 1)}
    label_array = vtk.vtkIntArray()
    label_array.SetName("outlet")
    for value in source_label:
        label_array.InsertNextValue({"left": 0, "right": 1, "centre": 2}[value])
    lines.GetCellData().AddArray(label_array)
    return out, lines


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("--mean", action="store_true")
    parser.add_argument("--seeds", type=int, default=SEEDS, help="streamlines per outlet")
    args = parser.parse_args()
    C.JET_WINDOW = A.window_for(args.case)
    g = load(args.case, args.mean)
    passage = solid_mesh(F.nozzle(False, ROOF_RAISE, MOUTH_HEIGHT, ANGLE))
    feeds = solid_mesh(F.feed(-1, roof_raise=ROOF_RAISE).fuse(F.feed(1, roof_raise=ROOF_RAISE)))
    outlet_rows, sections, normal = outlets(g, passage)
    normals = {"left": (1, 0, 0), "right": (-1, 0, 0), "centre": normal}
    report = {"case": args.case, "fields": "iteration mean (UMean, pMean)" if args.mean else "snapshot at 1200",
              "flow_lpm": 180, "outlets": outlet_rows, "pressure_budget": budget(g, feeds, outlet_rows)}
    rows = A.rows_of(args.case)
    report["operating_point_1m_hose"] = A.operating(rows)
    report["delivery"], lines = delivery(g, sections, normals, outlet_rows, args.seeds)
    suffix = "_mean" if args.mean else ""
    writer = vtk.vtkXMLPolyDataWriter()
    writer.SetFileName(str(C.results_dir(args.case) / f"outlet_streamlines{suffix}.vtp"))
    writer.SetInputData(lines)
    writer.Write()
    (C.results_dir(args.case) / f"outlet_balance{suffix}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("outlets", "delivery", "operating_point_1m_hose")}, indent=1))
    for path, rows_ in report["pressure_budget"].items():
        for r in rows_:
            print(path, r["station"], round(r["lpm"], 1), "L/min", round(r["pt"]), "Pa total", round(r["dyn"]), "dyn")


if __name__ == "__main__":
    main()
