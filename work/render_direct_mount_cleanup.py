import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import cadquery as cq
from PIL import Image, ImageDraw
import vtk
import render_r43_public_comparison as R

out = R.S / "swept_feed" / "optA_direct"
scene = R.S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
load = lambda file: cq.Shape.importBrep(str(scene / file))
probe = load(next(f for n, f in manifest["carriage"] if n.startswith("Beacon_")))
body = cq.Shape.importBrep(str(out / "p22_swept_beacon.brep"))
old = cq.Shape.importBrep(str(R.S / "swept_feed" / "optA" / "p22_swept_beacon.brep"))
sheet = Image.new("RGB", (2400, 1550), R.BG)
draw = ImageDraw.Draw(sheet)
draw.text((65, 30), "DIRECT MOUNT / OBSOLETE BRACKET EARS REMOVED", font=R.font(50, True), fill=R.TEXT)
for i, (name, part) in enumerate((("BEFORE", old), ("CLEANED DIRECT MOUNT", body))):
    ren = vtk.vtkRenderer()
    ren.SetBackground(.067, .129, .212)
    ren.AddActor(R.cad_actor(part, (.40, .72, .59)))
    ren.AddActor(R.cad_actor(probe, (.48, .36, .65)))
    cam = ren.GetActiveCamera()
    cam.SetPosition(0, 0, -180)
    cam.SetFocalPoint(0, -3, -73)
    cam.SetViewUp(0, 1, 0)
    cam.ParallelProjectionOn()
    cam.SetParallelScale(35)
    ren.ResetCameraClippingRange()
    steps = vtk.vtkRenderStepsPass()
    ao = vtk.vtkSSAOPass()
    ao.SetDelegatePass(steps)
    ao.SetRadius(2)
    ao.SetBias(.04)
    ao.SetKernelSize(128)
    ao.BlurOn()
    ren.SetPass(ao)
    win = vtk.vtkRenderWindow()
    win.SetOffScreenRendering(True)
    win.SetSize(1120, 1150)
    win.AddRenderer(ren)
    win.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(win)
    capture.ReadFrontBufferOff()
    capture.Update()
    path = out / f"cleanup_{i}.png"
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    win.Finalize()
    sheet.paste(Image.open(path), (50 + i * 1180, 200))
    draw.text((75 + i * 1180, 130), name, font=R.font(42, True), fill=R.AMBER if i else R.MUTED)
draw.text((65, 1390), "Retained: probe's two mounting holes, sensor datum, cable relief and all air passages.",
          font=R.font(36), fill=R.TEXT)
draw.text((65, 1450), "Geometry-only cleanup. Prior CFD describes the untrimmed candidate A; released R43 unchanged.",
          font=R.font(32), fill=R.MUTED)
sheet.save(CAD / "images" / "r43_direct_mount_cleanup.png", optimize=True)
print("saved direct-mount comparison")
