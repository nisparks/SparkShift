"""Offline VTK renderer for v26 audit scenes (no Fusion UI involvement).

Usage: python sparkshift_render_v26.py job.json
job = {"scenes": [paths], "parts": {name: {"rgb": [r,g,b], "opacity": 1.0, "edges": true}},
       "views": [{"name", "target", "direction", "up", "extent", "size": [w, h],
                  "markers": [{"at": [x,y,z], "label": "1", "rgb": [r,g,b]}],
                  "clip": {"origin": [...], "normal": [...]}}],
       "out": folder, "prefix": "name"}
Coordinates are assembly millimetres.  Orthographic camera, extent = visible height.
"""

import json
import sys
from pathlib import Path

import numpy as np
import vtk
from vtk.util import numpy_support as ns


def mesh_poly(nodes, tris):
    points = vtk.vtkPoints()
    points.SetData(ns.numpy_to_vtk(np.asarray(nodes, float).reshape(-1, 3), deep=True))
    tri = np.asarray(tris, np.int64).reshape(-1, 3)
    conn = np.hstack([np.full((len(tri), 1), 3, np.int64), tri]).ravel()
    cells = vtk.vtkCellArray()
    cells.SetCells(len(tri), ns.numpy_to_vtkIdTypeArray(conn, deep=True))
    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(cells)
    return poly


def clipped(algorithm_output_or_poly, clip):
    if not clip:
        return algorithm_output_or_poly
    plane = vtk.vtkPlane()
    plane.SetOrigin(*clip["origin"])
    plane.SetNormal(*clip["normal"])
    f = vtk.vtkClipPolyData()
    if isinstance(algorithm_output_or_poly, vtk.vtkPolyData):
        f.SetInputData(algorithm_output_or_poly)
    else:
        f.SetInputConnection(algorithm_output_or_poly)
    f.SetClipFunction(plane)
    f.Update()
    return f.GetOutput()


def mesh_actor(nodes, tris, rgb, opacity, clip=None):
    poly = mesh_poly(nodes, tris)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(poly)
    normals.SetFeatureAngle(20)
    normals.SplittingOn()
    normals.ConsistencyOn()
    normals.Update()
    out = clipped(normals.GetOutput(), clip)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(out)
    mapper.SetResolveCoincidentTopologyToPolygonOffset()
    mapper.SetRelativeCoincidentTopologyPolygonOffsetParameters(1.5, 1.5)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    p = actor.GetProperty()
    p.SetColor(*[c / 255 for c in rgb])
    p.SetOpacity(opacity)
    p.SetAmbient(0.22)
    p.SetDiffuse(0.78)
    p.SetSpecular(0.12)
    p.SetSpecularPower(25)
    return actor


def lines_actor(polylines, rgb=(0, 0, 0), width=1.3, clip=None):
    points = vtk.vtkPoints()
    lines = vtk.vtkCellArray()
    for pl in polylines:
        line = vtk.vtkPolyLine()
        line.GetPointIds().SetNumberOfIds(len(pl))
        for k, p in enumerate(pl):
            line.GetPointIds().SetId(k, points.InsertNextPoint(p))
        lines.InsertNextCell(line)
    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetLines(lines)
    out = clipped(poly, clip)
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(out)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    actor.GetProperty().SetColor(*[c / 255 for c in rgb])
    actor.GetProperty().SetLineWidth(width)
    actor.GetProperty().LightingOff()
    return actor


def marker_actors(markers, extent):
    actors = []
    r = extent * 0.018
    for m in markers:
        rgb = [c / 255 for c in m.get("rgb", (255, 40, 40))]
        ring = vtk.vtkRegularPolygonSource()
        ring.SetNumberOfSides(40)
        ring.SetRadius(r)
        ring.GeneratePolygonOff()
        ring.SetCenter(0, 0, 0)
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(ring.GetOutputPort())
        follower = vtk.vtkFollower()
        follower.SetMapper(mapper)
        follower.SetPosition(*m["at"])
        follower.GetProperty().SetColor(*rgb)
        follower.GetProperty().SetLineWidth(3)
        follower.GetProperty().LightingOff()
        actors.append(("follower", follower))
        if m.get("label"):
            text = vtk.vtkBillboardTextActor3D()
            text.SetInput(str(m["label"]))
            text.SetPosition(m["at"][0], m["at"][1], m["at"][2])
            text.SetDisplayOffset(14, 10)
            tp = text.GetTextProperty()
            tp.SetFontSize(26)
            tp.SetBold(True)
            tp.SetColor(*rgb)
            tp.SetBackgroundColor(0, 0, 0)
            tp.SetBackgroundOpacity(0.55)
            actors.append(("text", text))
    return actors


def render(job):
    scenes = {}
    for path in job["scenes"]:
        scenes.update(json.loads(Path(path).read_text(encoding="utf-8")))
    out = Path(job["out"])
    out.mkdir(parents=True, exist_ok=True)
    files = []
    for view in job["views"]:
        w, h = view.get("size", (1400, 1050))
        ren = vtk.vtkRenderer()
        ren.SetBackground(46 / 255, 52 / 255, 64 / 255)
        clip = view.get("clip")
        for name, spec in job["parts"].items():
            if name not in scenes or name in view.get("hide", []):
                continue
            data = scenes[name]
            opacity = view.get("opacity", {}).get(name, spec.get("opacity", 1.0))
            ren.AddActor(mesh_actor(data["nodes"], data["tris"], spec["rgb"], opacity, clip))
            if spec.get("edges", True) and opacity > 0.3:
                ren.AddActor(lines_actor(data["edges"], (10, 10, 14), view.get("line_width", 1.3), clip))
        for overlay in view.get("overlays", []):
            ren.AddActor(lines_actor(overlay["poly"], overlay.get("rgb", (255, 30, 30)), overlay.get("width", 3.5)))
        cam = ren.GetActiveCamera()
        t = np.asarray(view["target"], float)
        d = np.asarray(view["direction"], float)
        d /= np.linalg.norm(d)
        cam.ParallelProjectionOn()
        cam.SetFocalPoint(*t)
        cam.SetPosition(*(t - d * 400.0))
        cam.SetViewUp(*view["up"])
        cam.SetParallelScale(view["extent"] / 2.0)
        for kind, actor in marker_actors(view.get("markers", []), view["extent"]):
            if kind == "follower":
                actor.SetCamera(cam)
            ren.AddActor(actor)
        kit = vtk.vtkLightKit()
        kit.AddLightsToRenderer(ren)
        ren.ResetCameraClippingRange(-1e4, 1e4, -1e4, 1e4, -1e4, 1e4)
        cam.SetClippingRange(1.0, 2000.0)
        win = vtk.vtkRenderWindow()
        win.SetOffScreenRendering(1)
        win.SetMultiSamples(8)
        win.AddRenderer(ren)
        win.SetSize(w, h)
        win.Render()
        grab = vtk.vtkWindowToImageFilter()
        grab.SetInput(win)
        grab.Update()
        path = out / ("%s_%s.png" % (job.get("prefix", "v26"), view["name"]))
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(path))
        writer.SetInputConnection(grab.GetOutputPort())
        writer.Write()
        win.Finalize()
        files.append(str(path))
    return files


if __name__ == "__main__":
    print("\n".join(render(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")))))
