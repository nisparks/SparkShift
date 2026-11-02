"""Shaded 3D views of the chosen part cooler A (FR1 + converging rear outlet) around the Bambu hotend.

python render_design_a_r43.py [--geom review_fr1_rc24m]
python render_design_a_r43.py --geom review_a_aftf --label "Aft F" --output r43_design_aft_f_views.png
Writes images/r43_design_a_views.png (VTK offscreen). Geometry only; airflow is in
images/r43_cooling_review_cfd_rear_converge.png.
"""
import argparse
import json
from pathlib import Path

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import vtk
from vtk.util.numpy_support import numpy_to_vtk, numpy_to_vtkIdTypeArray, vtk_to_numpy

import build_and_verify_accessories_v26 as acc
import build_rear_converge_r43 as RC
from build_modular_toolhead import ROOT

NOZZLE = (0.0, 22.7, -78.88)
DUCT, NEW, HOTEND = (.45, .63, .80), (1.0, .45, .12), (.70, .72, .76)


def polydata(shape, tol):
    v, t = shape.tessellate(tol, .2)
    pts = vtk.vtkPoints()
    pts.SetData(numpy_to_vtk(np.array([x.toTuple() for x in v]), deep=True))
    t = np.array(t, dtype=np.int64)
    cells = vtk.vtkCellArray()
    cells.SetCells(len(t), numpy_to_vtkIdTypeArray(np.c_[np.full(len(t), 3), t].ravel(), deep=True))
    pd = vtk.vtkPolyData()
    pd.SetPoints(pts)
    pd.SetPolys(cells)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(pd)
    normals.SetFeatureAngle(35)
    normals.Update()
    return normals.GetOutput()


def actor(pd, rgb, clip_x=None, opacity=1.0):
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(pd)
    if clip_x is not None:
        plane = vtk.vtkPlane()
        plane.SetOrigin(clip_x, 0, 0)
        plane.SetNormal(-1, 0, 0)  # keep X < clip_x, the half away from a +X camera
        mapper.AddClippingPlane(plane)
    a = vtk.vtkActor()
    a.SetMapper(mapper)
    p = a.GetProperty()
    p.SetColor(*rgb)
    p.SetOpacity(opacity)
    p.SetSpecular(.25)
    p.SetSpecularPower(25)
    p.BackfaceCullingOff()
    return a


def section_cap(shape, rgb):
    """Solid cap on the X = 0 cut so the half-section reads as material, not a hollow shell."""
    face = cq.Face.makePlane(200, 200, cq.Vector(0, 0, -60), cq.Vector(1, 0, 0))
    cut = shape.copy().intersect(face)
    if not cut.Faces():
        return None
    a = actor(polydata(cut, .02), rgb)
    a.GetProperty().SetAmbient(.35)
    return a


def snap(actors, pos, focal, up, scale, size=(1100, 900)):
    ren = vtk.vtkRenderer()
    ren.SetBackground(1, 1, 1)
    for a in actors:
        if a is not None:
            ren.AddActor(a)
    s = vtk.vtkSphereSource()
    s.SetCenter(*NOZZLE)
    s.SetRadius(.6)
    s.SetThetaResolution(24)
    s.SetPhiResolution(24)
    m = vtk.vtkPolyDataMapper()
    m.SetInputConnection(s.GetOutputPort())
    tip = vtk.vtkActor()
    tip.SetMapper(m)
    tip.GetProperty().SetColor(1, .83, .1)
    ren.AddActor(tip)
    cam = ren.GetActiveCamera()
    cam.SetPosition(*pos)
    cam.SetFocalPoint(*focal)
    cam.SetViewUp(*up)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(scale)
    ren.ResetCameraClippingRange()
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(1)
    win.SetSize(*size)
    win.SetMultiSamples(8)
    win.AddRenderer(ren)
    win.Render()
    grab = vtk.vtkWindowToImageFilter()
    grab.SetInput(win)
    grab.ReadFrontBufferOff()
    grab.Update()
    img = grab.GetOutput()
    w, h, _ = img.GetDimensions()
    arr = vtk_to_numpy(img.GetPointData().GetScalars()).reshape(h, w, -1)[::-1]
    win.Finalize()
    return arr


def main(geom, label="A", output="r43_design_a_views.png"):
    root = acc.WORK / "swept_feed"
    checks = json.loads((root / geom / "checks.json").read_text())
    p22 = cq.Shape.importBrep(str(root / geom / "p22.brep"))
    source_checks = checks
    if "side_aft" in checks:
        source_checks = json.loads((root / checks["source"] / "checks.json").read_text())
    src = cq.Shape.importBrep(str(root / source_checks["source"] / "p22.brep"))
    rc = checks["rear_converge"]
    right, left = RC.fill(src, checks["rear_slot"], rc["exit_abs_x_mm"], rc["yaw_deg"])
    scene = acc.WORK / "r43_scene"
    manifest = json.loads((scene / "manifest.json").read_text())
    hotend = cq.Shape.importBrep(str(scene / dict(manifest["variants"]["Bambu"]["parts"])["hotend"]))

    duct, he = polydata(p22, .03), polydata(hotend, .05)
    fills = [polydata(right, .01), polydata(left, .01)]

    def whole(op=1.0):
        return [actor(duct, DUCT), actor(he, HOTEND, opacity=op)] + [actor(f, NEW) for f in fills]

    halved = [actor(duct, DUCT, clip_x=0), actor(he, HOTEND, clip_x=0), actor(fills[1], NEW, clip_x=0),
              section_cap(p22, (.25, .38, .52)), section_cap(hotend, (.45, .47, .52))]

    nz = np.array(NOZZLE)
    views = [
        ("Rear-left, from above", whole(), nz + (-60, -90, 70), nz + (0, -2, 12), (0, 0, 1), 30),
        ("From below (front at top): side jets left/right, rear slot under the hotend", whole(),
         nz + (0, -40, -120), nz + (0, -6, 4), (0, 1, 0), 19),
        ("Half-section on the centreline (rear left, front right)", halved,
         nz + (150, 0, 0), nz + (0, -8, 6), (0, 0, 1), 16),
        ("Looking back into the rear mouth from in front of the nozzle (hotend see-through)",
         [actor(duct, DUCT), actor(he, HOTEND, opacity=.18)] + [actor(f, NEW) for f in fills],
         nz + (0, 70, -25), (0, 11, -73), (0, 0, 1), 11),
    ]
    fig, axes = plt.subplots(2, 2, figsize=(16, 13.5), dpi=110)
    for ax, (title, actors, pos, focal, up, scale) in zip(axes.ravel(), views):
        ax.imshow(snap(actors, pos, focal, up, scale))
        ax.set_title(title, fontsize=13)
        ax.axis("off")
    sides = "aft-shifted side jets" if "side_aft" in checks else "FR1 side jets"
    fig.suptitle(f"Design {label} = {sides} + converging rear outlet. Blue: duct. Orange: rear end walls "
                 f"({rc['yaw_deg']} deg yaw, merge at the nozzle).\nGrey: Bambu hotend. Yellow: nozzle tip. "
                 "Geometry only; not an airflow or temperature plot.", fontsize=14)
    fig.subplots_adjust(left=.01, right=.99, bottom=.01, top=.92, wspace=.02, hspace=.07)
    if output != Path(output).name or not output.endswith(".png"):
        raise ValueError("Output must be a PNG filename")
    out = ROOT / "images" / output
    fig.savefig(out, facecolor="white")
    print(out)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--geom", default="review_fr1_rc24m")
    p.add_argument("--label", default="A")
    p.add_argument("--output", default="r43_design_a_views.png")
    args = p.parse_args()
    main(args.geom, args.label, args.output)
