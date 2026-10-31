"""Unbranded CAD cutaways of the separate C28 mechanical review."""
import json

import cadquery as cq
from PIL import Image, ImageDraw
import vtk

from audit_c28_mechanical_r43 import OUTPUT, ROOT, SOURCE
import r43_c28_mechanical as M
import render_r43_public_comparison as V

COLORS = {"p01": (.42, .48, .57), "p21": (.94, .55, .18), "p22": (.12, .65, .76),
          "cable": (.79, .37, .64), "steel": (.65, .69, .74), "brass": (.85, .66, .3)}


def render(items, target, direction, scale, path, keep=None):
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.067, .129, .212)
    renderer.SetUseFXAA(True)
    renderer.AutomaticLightCreationOff()
    for body, color in items:
        if keep is None:
            renderer.AddActor(V.cad_actor(body, color))
        else:
            shown = body.intersect(keep)
            if shown.Faces():
                renderer.AddActor(V.cad_actor(shown, color))
    focus = cq.Vector(*target)
    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(*target)
    camera.SetPosition(*(focus + cq.Vector(*direction).normalized() * 200).toTuple())
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(scale)
    renderer.ResetCameraClippingRange()
    for actor in renderer.GetActors():
        prop = actor.GetProperty()
        prop.SetAmbient(.22)
        prop.SetDiffuse(.78)
        prop.SetSpecular(.18)
        prop.SetSpecularPower(45)
    for position, intensity in (((100, -90, 50), 1.), ((-60, -60, -100), .5), ((10, 90, 20), .65)):
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(*position)
        light.SetFocalPoint(*target)
        light.SetIntensity(intensity)
        renderer.AddLight(light)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(True)
    window.SetMultiSamples(8)
    window.SetSize(1300, 920)
    window.AddRenderer(renderer)
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.ReadFrontBufferOff()
    capture.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(path))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    window.Finalize()


def main():
    parts = {k: cq.Shape.importBrep(str(OUTPUT / f"{k}.brep")) for k in ("p01", "p21", "p22")}
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    cable = cq.Shape.importBrep(str(SOURCE / next(p for n, p in manifest["carriage"] if n.startswith("Probe_Cable"))))
    hotend = cq.Shape.importBrep(str(SOURCE / dict(manifest["variants"]["Bambu"]["parts"])["hotend"]))
    hardware = M.hardware()
    cropped = M.box(-30, 30, -48, 34, -80, -40)
    items = [(p.intersect(cropped), COLORS[k]) for k, p in parts.items()]
    items += [(cable.intersect(cropped), COLORS["cable"]), (hotend, (.62, .65, .68))]
    items += [(p, COLORS["brass" if "HEATSET" in n else "steel"]) for n, p in hardware]
    render(items, (0, -7, -59), (1, -.9, .35), 34, OUTPUT / "mechanical_assembly.png")

    local = M.box(-7, 7, -39, -22, -74, -41)
    retainer_hw = [(p, COLORS["brass" if "HEATSET" in n else "steel"])
                   for n, p in hardware if "P21_P22" in n]
    joint = [(parts["p21"].intersect(local), COLORS["p21"]),
             (parts["p22"].intersect(local), COLORS["p22"]),
             (cable.intersect(local), COLORS["cable"])] + retainer_hw
    render(joint, (0, -30.4, -57.0), (1, .2, .15), 16.8, OUTPUT / "mechanical_retainer.png",
           M.box(-40, 0, -60, 40, -100, 0))

    isolated = [(parts["p21"].intersect(local), COLORS["p21"])]
    isolated += [(p, COLORS["brass"]) for n, p in hardware if "P21_P22" in n and "HEATSET" in n]
    isolated += [(cable.intersect(local), COLORS["cable"])]
    render(isolated, (0, -29.8, -54.7), (.5, 1, -.1), 14.5, OUTPUT / "mechanical_fork.png")

    mount_window = M.box(13.5, 23, 8, 24, -67, -46)
    mount = [(parts[k].intersect(mount_window), COLORS[k]) for k in ("p01", "p22")]
    mount += [(p, COLORS["brass" if "HEATSET" in n else "steel"])
              for n, p in hardware if "P22_P01" in n and n.endswith("_1")]
    render(mount, (18, 15.8, -55.9), (1, 0, 0), 11.6, OUTPUT / "mechanical_angled_pair.png",
           M.box(-40, 18, -60, 50, -100, 0))

    sheet = Image.new("RGB", (2800, 2760), V.BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((65, 35), "ANGLED MOUNTS + POSITIVE DUCT RETENTION", fill=V.TEXT, font=V.font(62, True))
    draw.text((65, 125), "Bambu / C28 mechanical study. Orange: mid duct. Teal: lower duct. Pink: cable.",
              fill=V.MUTED, font=V.font(36))
    panels = [
        ("ASSEMBLED / ORIGINAL DATUMS", "mechanical_assembly.png", "Duct outlets, hotend and probe stay in place."),
        ("UNDERSIDE M3 RETAINER / CUTAWAY", "mechanical_retainer.png", "M3x10 + 4 mm insert; head remains above the low jets."),
        ("FORK AROUND THE LIVE CABLE", "mechanical_fork.png", "0.50 mm added-part cable gap; 0.25 mm socket fit."),
        ("MATCHED 45-DEGREE FACES", "mechanical_angled_pair.png", "Both parts change. M3x8 screws follow the new axis."),
    ]
    for i, (title, filename, caption) in enumerate(panels):
        x, y = 65 + (i % 2) * 1380, 240 + (i // 2) * 1090
        draw.text((x, y), title, fill=V.TEXT, font=V.font(37, True))
        sheet.paste(Image.open(OUTPUT / filename), (x, y + 65))
        draw.text((x, y + 990), caption, fill=V.MUTED, font=V.font(29))
    draw.text((65, 2450), "Support is NOT solved by the angled mounts alone.", fill=V.TEXT, font=V.font(43, True))
    draw.text((65, 2520), "H2D ABS / same settings: back-down support 9.52 -> 9.14 cm3. Inlet-down 10.23 -> 10.46 cm3.",
              fill=V.MUTED, font=V.font(32))
    draw.text((65, 2590), "Whole set: support +1.7%; estimated time +9.4%. Tongue printing still needs work.",
              fill=V.MUTED, font=V.font(33))
    draw.text((65, 2650), "Inlet-down: rear-passage support risk. New CFD and physical fit/strength checks are still required.",
              fill=V.MUTED, font=V.font(33))
    png = ROOT / "images" / "r43_c28_mechanical_review.png"
    jpg = ROOT / "images" / "r43_c28_mechanical_review_share.jpg"
    sheet.save(png, optimize=True)
    sheet.resize((1920, round(sheet.height * 1920 / sheet.width)), Image.Resampling.LANCZOS).save(
        jpg, quality=93, subsampling=0)
    sections = cq.Assembly(name="C28_Inspection_Sections_NOT_PRINT_PARTS")
    for label, group, keep, offset in (
        ("Retainer", joint, M.box(-40, 0, -60, 40, -100, 0), (120, 120, 0)),
        ("Angled_mount", mount, M.box(-40, 18, -60, 50, -100, 0), (240, 200, 0)),
        ("Fork_and_cable", isolated, None, (-160, 0, 0)),
    ):
        for i, (body, color) in enumerate(group):
            part = body if keep is None else body.intersect(keep)
            if part.Solids():
                sections.add(part.translate(offset), name=f"{label}_{i}", color=cq.Color(*color))
    sections.save(str(OUTPUT / "mechanical_inspection_sections.step"))
    print(png, jpg, sep="\n")


if __name__ == "__main__":
    main()
