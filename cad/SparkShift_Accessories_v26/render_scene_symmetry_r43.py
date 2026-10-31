"""Mirror the CFD scene onto itself and show what has no mirror partner (a Boolean), near the outlets.

Usage: python render_scene_symmetry_r43.py <case> <out.png>
Uses the case's domain.json to rebuild the same obstacles and duct parts as the CFD, inside the outlet zone
(the ambient box around the nozzle). Each solid minus the mirror image of all solids is what makes the scene
asymmetric. Prints the volumes; the image shows the scene translucent and the asymmetric pieces in red.
"""
import json
import sys
from pathlib import Path

import cadquery as cq
from PIL import Image, ImageDraw
import vtk

import cfd_cpap_r41 as C
import render_r43_public_comparison as V


def scene(case):
    dom = json.loads((C.results_dir(case) / "domain.json").read_text())
    o = list(C.OUTLET)
    o[4] = C.NOZZLE_TIP_Z - C.BED_GAP
    extra = [(Path(f).stem, cq.Shape.importBrep(f)) for f in dom.get("extra_obstacles", {}).values()]
    obs = C.obstacles(dom["duct"], dom["tool"], o, tuple(dom["left_out"]), extra)
    duct = C.duct_parts(dom["duct"], dom["p22_variant"], dom.get("p21_variant"))
    zone = C.box(*o)
    parts = [(n, s.intersect(zone)) for n, s in obs] + [(n, s.intersect(zone)) for n, s in zip(("P20", "P21", "P22"), duct)]
    return [(n, s) for n, s in parts if s.Volume() > 1e-6]


def asymmetric(parts):
    union = parts[0][1].fuse(*[s for _, s in parts[1:]])
    mirror = union.mirror("YZ")
    return [(n, a, a.Volume()) for n, s in parts if (a := s.cut(mirror)).Volume() > .01]


def view(items, target, direction, scale, path):
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.067, .129, .212)
    for body, color, opacity in items:
        actor = V.cad_actor(body, color)
        actor.GetProperty().SetOpacity(opacity)
        renderer.AddActor(actor)
    camera = renderer.GetActiveCamera()
    focus = cq.Vector(*target)
    camera.SetFocalPoint(*target)
    camera.SetPosition(*(focus + cq.Vector(*direction).normalized() * 200).toTuple())
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(scale)
    renderer.ResetCameraClippingRange()
    renderer.UseDepthPeelingOn()
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(True)
    window.SetAlphaBitPlanes(1)
    window.SetMultiSamples(0)
    window.SetSize(1300, 900)
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


def main():
    case, out = sys.argv[1], Path(sys.argv[2])
    parts = scene(case)
    asym = asymmetric(parts)
    for n, _, v in sorted(asym, key=lambda r: -r[2]):
        print(f"{n:40} {v:9.2f} mm3 without a mirror partner")
    names = {n for n, _, _ in asym}
    print("symmetric:", sorted(n for n, _ in parts if n not in names))
    items = [(s, (.12, .65, .76) if n in ("P20", "P21", "P22") else (.62, .65, .68), .22) for n, s in parts]
    items += [(a, (1.0, .25, .25), 1.0) for _, a, _ in asym]
    tiles = []
    for i, (direction, label) in enumerate((((.35, 1.0, .55), "from the front, above"),
                                            ((0.0, .0001, -1.0), "from below (print side)"))):
        path = out.with_name(out.stem + f"_{i}.png")
        view(items, (0, 18, -62), direction, 30, path)
        tiles.append((label, Image.open(path)))
    sheet = Image.new("RGB", (2700, 1110), V.BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((50, 25), "Scene mirrored onto itself: red = no mirror partner (Boolean)", fill=V.TEXT, font=V.font(44, True))
    for i, (label, image) in enumerate(tiles):
        draw.text((50 + i * 1340, 100), label, fill=V.MUTED, font=V.font(30))
        sheet.paste(image, (50 + i * 1340, 150))
    lines = "   ".join(f"{n.replace('Bambu:', 'hotend ')} {v:.0f} mm3" for n, _, v in sorted(asym, key=lambda r: -r[2])
                       if v >= .5)
    draw.text((50, 1060), "Duct parts P20 / P21 / P22: symmetric.   " + lines, fill=V.MUTED, font=V.font(24))
    sheet.save(out, optimize=True)
    for i in range(len(tiles)):
        out.with_name(out.stem + f"_{i}.png").unlink()
    print(out)


if __name__ == "__main__":
    main()
