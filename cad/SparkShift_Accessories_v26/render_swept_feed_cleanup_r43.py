"""Render the cleaned C28 entry against the frozen C28 geometry, without changing Fusion."""
import json

import cadquery as cq
from PIL import Image, ImageDraw
import vtk

from audit_swept_feed_cleanup_r43 import AFTER, BEFORE, ROOT, acc
import render_r43_public_comparison as V


def section_actor(renderer, part, keep, origin, normal, colour):
    clipped = part.intersect(keep)
    renderer.AddActor(V.cad_actor(clipped, colour))
    cut = []
    for face in clipped.Faces():
        centre = face.Center()
        if face.geomType() == "PLANE" and abs((centre - origin).dot(normal)) < 1e-4:
            cut.append(face)
    if cut:
        actor = V.cad_actor(cq.Compound.makeCompound(cut), (.89, .84, .54))
        actor.GetMapper().SetResolveCoincidentTopologyToPolygonOffset()
        actor.GetMapper().SetRelativeCoincidentTopologyPolygonOffsetParameters(-1, -1)
        renderer.AddActor(actor)


def render(part, removed, probe, hotend, keep, origin, normal, close, path):
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.067, .129, .212)
    renderer.AutomaticLightCreationOff()
    renderer.SetUseFXAA(True)
    shown_part = part.cut(removed) if removed is not None else part
    section_actor(renderer, shown_part, keep, origin, normal, (.35, .63, .47))
    renderer.AddActor(V.cad_actor(probe.intersect(keep), (.45, .32, .57)))
    renderer.AddActor(V.cad_actor(hotend.intersect(keep), (.32, .48, .69)))
    if removed is not None:
        renderer.AddActor(V.cad_actor(removed.intersect(keep), (.95, .29, .20)))
    focus = cq.Vector(16, -7, -61.6) if close else cq.Vector(0, -8, -64)
    camera = renderer.GetActiveCamera()
    camera.SetFocalPoint(*focus.toTuple())
    camera.SetPosition(*(focus + cq.Vector(130, -130, 0)).toTuple())
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(5.4 if close else 25)
    renderer.ResetCameraClippingRange()
    for actor in renderer.GetActors():
        p = actor.GetProperty()
        p.SetAmbient(.18)
        p.SetDiffuse(.8)
        p.SetSpecular(.22)
        p.SetSpecularPower(45)
    for position, intensity in (((100, -100, -20), 1.), ((-60, -60, -100), .45),
                                ((10, 40, -20), .65)):
        light = vtk.vtkLight()
        light.SetLightTypeToSceneLight()
        light.SetPosition(*position)
        light.SetFocalPoint(*focus.toTuple())
        light.SetIntensity(intensity)
        renderer.AddLight(light)
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(True)
    window.SetMultiSamples(8)
    window.SetSize(1300, 820 if close else 930)
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
    before = cq.Shape.importBrep(str(BEFORE / "p22_swept_beacon.brep"))
    after = cq.Shape.importBrep(str(AFTER / "p22_swept_beacon.brep"))
    removed = before.cut(after)
    scene = acc.WORK / "r43_scene"
    manifest = json.loads((scene / "manifest.json").read_text())
    load = lambda p: cq.Shape.importBrep(str(scene / p))
    probe = load(next(p for n, p in manifest["carriage"] if n.startswith("Beacon_")))
    hotend = load(dict(manifest["variants"]["Bambu"]["parts"])["hotend"])
    hotend = hotend.intersect(cq.Solid.makeBox(65, 90, 33, cq.Vector(-30, -48, -80)))
    normal = cq.Vector(.6877446479108108, -.7259526839058004, 0)
    origin = cq.Vector(19.507106267688, -39.23537300955, -78) - normal * 21
    plane = cq.Plane(origin=origin, xDir=(0, 0, 1), normal=normal)
    keep = cq.Workplane(plane).rect(200, 200).extrude(-200).val()
    sheet = Image.new("RGB", (2800, 2580), V.BG)
    draw = ImageDraw.Draw(sheet)
    draw.text((65, 35), "SWEPT FEED / INTERNAL GEOMETRY CLEANUP", fill=V.TEXT, font=V.font(62, True))
    draw.text((65, 135), "Same 28-degree aim, 0.9 mm slot, mounts and sensing keepouts.", fill=V.MUTED,
              font=V.font(40))
    for i, (label, part, highlight) in enumerate((
        ("BEFORE / FEED-WALL REMNANTS", before, removed),
        ("AFTER / CLEAR MAIN CHANNEL", after, None),
    )):
        x = 65 + i * 1380
        draw.text((x, 250), label, fill=V.TEXT, font=V.font(42, True))
        for close, y in ((False, 335), (True, 1310)):
            path = AFTER / f"cleanup_{i}_{'detail' if close else 'section'}.png"
            render(part, highlight, probe, hotend, keep, origin, normal, close, path)
            sheet.paste(Image.open(path), (x, y))
    draw.text((65, 2200), "Red: two unnecessary feed roofs, 23.96 mm3 each. Gold: sectioned material.",
              fill=V.TEXT, font=V.font(38))
    draw.text((65, 2280), "Cause: the old clearance ended at Z -60 mm, below the raised feed's outer roof.",
              fill=V.MUTED, font=V.font(37))
    draw.text((65, 2360), "The cable-support rib, original duct walls and final jet openings are retained.",
              fill=V.MUTED, font=V.font(37))
    draw.text((65, 2440), "Geometry inspection only. Airflow requires its own matched run; no thermal/print release.",
              fill=V.MUTED, font=V.font(36))
    output = ROOT / "images" / "r43_swept_feed_cleanup_geometry.png"
    sheet.save(output, optimize=True)
    print(output)


if __name__ == "__main__":
    main()
