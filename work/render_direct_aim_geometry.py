import hashlib
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
import r43_swept_feed as G

out = R.S / "swept_feed" / "optC28_conformal"
qualified = json.loads((out / "qualification.json").read_text())
assert qualified["geometry_checks_pass"]
scene = R.S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
load = lambda f: cq.Shape.importBrep(str(scene / f))
probe = load(next(f for n, f in manifest["carriage"] if n.startswith("Beacon_")))
hotend = load(dict(manifest["variants"]["Bambu"]["parts"])["hotend"])
tip_crop = cq.Solid.makeBox(60, 58, 2.8, cq.Vector(-30, -22, -80))
crop = cq.Solid.makeBox(60, 58, 19, cq.Vector(-30, -22, -80))
sheet = Image.new("RGB", (3000, 1740), R.BG)
draw = ImageDraw.Draw(sheet)
draw.text((75, 35), "DIRECT MOUNT / REAR-AIM STUDY", font=R.font(68, True), fill=R.TEXT)
draw.text((75, 140), "Same 18 x 0.9 mm mouth and raised feed. Change the aim, not the flow target.",
          font=R.font(39), fill=R.MUTED)
for i, (label, folder) in enumerate((
    ("A / 32 DEG BASELINE", R.S / "swept_feed" / "optA_direct"),
    ("C / 28 DEG CANDIDATE", out),
)):
    part = cq.Shape.importBrep(str(folder / "p22_swept_beacon.brep"))
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.067, .129, .212)
    renderer.AutomaticLightCreationOff()
    renderer.SetUseFXAA(True)
    renderer.AddActor(R.cad_actor(part.intersect(crop), (.63, .76, .86)))
    renderer.AddActor(R.cad_actor(probe, (.40, .31, .56)))
    renderer.AddActor(R.cad_actor(hotend.intersect(tip_crop), (.77, .62, .40)))
    camera = renderer.GetActiveCamera()
    camera.SetPosition(45, 55, -97)
    camera.SetFocalPoint(0, 17, -74.5)
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(18)
    renderer.ResetCameraClippingRange()
    for actor in renderer.GetActors():
        p = actor.GetProperty()
        p.SetAmbient(.15)
        p.SetDiffuse(.80)
        p.SetSpecular(.28)
        p.SetSpecularPower(45)
    for position, intensity in (((45, 50, -100), 1.), ((-30, 30, -85), .45), ((5, -10, -40), .60)):
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(*position)
        light.SetFocalPoint(0, 18, -75)
        light.SetIntensity(intensity)
        renderer.AddLight(light)
    ao = vtk.vtkSSAOPass()
    ao.SetDelegatePass(vtk.vtkRenderStepsPass())
    ao.SetRadius(2)
    ao.SetBias(.04)
    ao.SetKernelSize(128)
    ao.BlurOn()
    renderer.SetPass(ao)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(True)
    window.SetSize(3080, 2000)
    window.AddRenderer(renderer)
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.ReadFrontBufferOff()
    capture.Update()
    path = out / f"aim_outlets_{i}.png"
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    landmarks = {}
    for key, point in (("rear", G.mouth(7).toTuple()), ("side", (-10.2, 22.7, -75.5))):
        renderer.SetWorldPoint(*point, 1)
        renderer.WorldToDisplay()
        x, y, _ = renderer.GetDisplayPoint()
        landmarks[key] = (65 + i * 1490 + (x - 760) * 1390 / 1880,
                          365 + (2000 - y - 660) * 1390 / 1880)
    window.Finalize()
    image = Image.open(path).crop((760, 660, 2640, 1600))
    image.thumbnail((1390, 1000), Image.Resampling.LANCZOS)
    sheet.paste(image, (65 + i * 1490, 365))
    draw.text((80 + i * 1490, 270), label, font=R.font(48, True), fill=R.TEXT)
    for key, text, dx, colour in (("rear", "Curved rear slot", 80, R.AMBER),
                                  ("side", "Side outlet", 1000, R.BLUE)):
        x = dx + i * 1490
        draw.text((x, 1200), text, font=R.font(42, True), fill=colour)
        point = landmarks[key]
        draw.line(((x + 100, 1185), point), fill=colour, width=3)
        draw.ellipse((point[0] - 6, point[1] - 6, point[0] + 6, point[1] + 6),
                     outline=colour, width=3)
draw.text((75, 1370), "Geometry-only inspection: one side outlet and rear slot are exposed; opposite side is symmetrical.",
          font=R.font(36), fill=R.TEXT)
draw.text((75, 1440), "Heater block omitted here only. Real nozzle tip retained; hotend and sock retained in CFD.",
          font=R.font(36), fill=R.MUTED)
draw.text((75, 1520), "Both probes retain mounting datums and sensing keepouts. No print or thermal qualification.",
          font=R.font(36), fill=R.MUTED)
image_path = CAD / "images" / "r43_direct_aim_geometry.png"
sheet.save(image_path, optimize=True)
paths = [image_path]
roundtrips = {}
for probe_name in ("Beacon", "Cartographer"):
    part = cq.Shape.importBrep(str(out / f"p22_swept_{probe_name.lower()}.brep"))
    path = CAD / "step" / f"P22_Swept_C28_Direct_Mount_{probe_name}_REVIEW.step"
    cq.exporters.export(part, str(path))
    restored = cq.importers.importStep(str(path)).val()
    difference = max(part.cut(restored).Volume(), restored.cut(part).Volume())
    assert restored.isValid() and len(restored.Solids()) == 1 and difference < 1e-4
    roundtrips[probe_name] = {"valid_single_solid": True, "max_difference_mm3": difference}
    paths.append(path)
report = {
    "qualification": "verification_swept_feed_optC28_conformal_r43.json",
    "geometry_only": True, "thermal_or_print_qualification": False,
    "camera": {"eye": [45, 55, -97], "focus": [0, 17, -74.5], "up": [0, 0, 1]},
    "step_roundtrip": roundtrips,
    "outputs_sha256": {str(p.relative_to(CAD)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
}
(CAD / "verification_direct_aim_exports_r43.json").write_text(json.dumps(report, indent=2) + "\n")
print("Saved matched outlet views and standalone review STEP files")
