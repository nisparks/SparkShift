import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from OCP.BRepAdaptor import BRepAdaptor_Curve
from PIL import Image, ImageDraw
import vtk
import r43_swept_feed as R
import render_r43_public_comparison as V
from audit_swept_slot_height_r43 import BEFORE, AFTER

assert json.loads((AFTER / "qualification.json").read_text())["geometry_checks_pass"]
scene = V.S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
load = lambda f: cq.Shape.importBrep(str(scene / f))
probe = load(next(f for n, f in manifest["carriage"] if n.startswith("Beacon_")))
hotend = load(dict(manifest["variants"]["Bambu"]["parts"])["hotend"])
crop = cq.Solid.makeBox(60, 58, 19, cq.Vector(-30, -22, -80))
tip = hotend.intersect(cq.Solid.makeBox(60, 58, 2.8, cq.Vector(-30, -22, -80)))
sheet = Image.new("RGB", (2400, 2110), V.BG)
draw = ImageDraw.Draw(sheet)
draw.text((65, 35), "REAR SLOT / 0.9 vs 1.1 mm", font=V.font(64, True), fill=V.TEXT)
draw.text((65, 135), "Raise the upper lip only. Same lower wall, 28-degree aim, feeds and mounts.",
          font=V.font(33), fill=V.MUTED)
assembly = cq.Assembly(name="C28_D11_slot_height_comparison")
for i, (name, folder) in enumerate((("C28 / 0.9 mm BASELINE", BEFORE), ("D11 / 1.1 mm TRIAL", AFTER))):
    part = cq.Shape.importBrep(str(folder / "p22_swept_beacon.brep"))
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.067, .129, .212)
    renderer.AutomaticLightCreationOff()
    renderer.AddActor(V.cad_actor(part.intersect(crop), (.63, .76, .86)))
    renderer.AddActor(V.cad_actor(probe, (.40, .31, .56)))
    renderer.AddActor(V.cad_actor(tip, (.77, .62, .40)))
    camera = renderer.GetActiveCamera()
    camera.SetPosition(45, 55, -97)
    camera.SetFocalPoint(0, 17, -74.5)
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(18)
    renderer.ResetCameraClippingRange()
    for actor in renderer.GetActors():
        prop = actor.GetProperty()
        prop.SetAmbient(.15)
        prop.SetDiffuse(.80)
        prop.SetSpecular(.28)
        prop.SetSpecularPower(45)
    for position, intensity in (((45, 50, -100), 1.), ((-30, 30, -85), .45), ((5, -10, -40), .60)):
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(*position)
        light.SetFocalPoint(0, 18, -75)
        light.SetIntensity(intensity)
        renderer.AddLight(light)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(True)
    window.SetMultiSamples(8)
    window.SetSize(3080, 2000)
    window.AddRenderer(renderer)
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.ReadFrontBufferOff()
    capture.Update()
    path = AFTER / f"slot_outlets_{i}.png"
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    window.Finalize()
    pic = Image.open(path).crop((760, 660, 2640, 1600)).resize((1100, 550), Image.Resampling.LANCZOS)
    sheet.paste(pic, (65 + 1180*i, 330))
    draw.text((65 + 1180*i, 240), name, font=V.font(42, True), fill=V.BLUE if i == 0 else V.AMBER)
    for suffix, shape, colour in (("P22", part, cq.Color(.35,.65,.5)), ("Probe", probe, cq.Color(.45,.3,.6)),
                                   ("Hotend", hotend, cq.Color(.35,.5,.75))):
        assembly.add(shape.translate((i*70,0,0)), name=f"{'C28' if i == 0 else 'D11'}_{suffix}", color=colour)
fig, axes = plt.subplots(1, 2, figsize=(14.7, 4.7))
fig.patch.set_facecolor(V.PANEL)
for ax in axes:
    ax.set_facecolor(V.PANEL)
    for height, colour in ((.9, V.BLUE), (1.1, V.AMBER)):
        wire = R.profile(0, 0, 3, height, 28, .9)
        for edge in wire.Edges():
            curve = BRepAdaptor_Curve(edge.wrapped)
            pts = [curve.Value(t) for t in np.linspace(curve.FirstParameter(), curve.LastParameter(), 150)]
            ax.plot([p.Y() for p in pts], [p.Z() for p in pts], color=colour, lw=2,
                    ls="--" if height == .9 else "-")
    ax.tick_params(colors=V.MUTED)
    ax.set_xlabel("Y (mm)", color=V.MUTED)
    ax.set_ylabel("Z (mm)", color=V.MUTED)
    ax.set_aspect("equal")
    for spine in ax.spines.values():
        spine.set_color(V.MUTED)
axes[0].set_xlim(3.5, 14)
axes[0].set_ylim(-74, -67)
axes[0].set_title("Actual centre-section air profiles", color=V.TEXT)
axes[1].set_xlim(11.9, 14.8)
axes[1].set_ylim(-74.2, -72.3)
axes[1].set_title("Outlet enlarged above the same lower lip", color=V.TEXT)
direction, up = R.outlet_axes(28)
for height, shift, colour in ((.9, .45, V.BLUE), (1.1, 1.0, V.AMBER)):
    low = R.mouth(0) - up*.45 + direction*shift
    high = R.mouth(0) + up*(height-.45) + direction*shift
    axes[1].annotate("", (high.y, high.z), (low.y, low.z),
                     arrowprops={"arrowstyle":"<->", "color":colour, "lw":1.5})
    axes[1].text(high.y+.05, high.z+.05, f"{height:g} mm", color=colour)
fig.tight_layout()
profile = AFTER / "slot_profile_overlay.png"
fig.savefig(profile, dpi=150, facecolor=V.PANEL)
plt.close(fig)
pic = Image.open(profile)
pic.thumbnail((2250, 790), Image.Resampling.LANCZOS)
sheet.paste(pic, (75, 970))
draw.text((65, 1760), "Nominal opening area: 16.2 -> 19.8 mm2 (+22.2%). Same nominal 0.8 mm walls.",
          font=V.font(32), fill=V.TEXT)
draw.text((65, 1820), "Probe gaps retained: Beacon 0.593 mm; Cartographer 0.445 mm.",
          font=V.font(32), fill=V.MUTED)
draw.text((65, 1880), "Trade-off: Red Lizard nominal gap 0.713 -> 0.619 mm. Bambu clearances unchanged.",
          font=V.font(32), fill=V.AMBER)
draw.text((65, 1970), "Geometry-only trial. Heater block hidden only in outlet views; included in CFD and assembly STEP.",
          font=V.font(28), fill=V.MUTED)
sheet.save(CAD / "images" / "r43_slot_height_geometry.png", optimize=True)
assembly.save(str(CAD / "step" / "P22_C28_D11_Slot_Height_Comparison_REVIEW.step"), exportType="STEP")
print("Saved actual outlet views, exact section profiles and comparison assembly")
