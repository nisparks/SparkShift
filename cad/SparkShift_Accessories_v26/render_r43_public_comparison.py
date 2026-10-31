"""Render the public R43/candidate-A Bambu comparison from the saved CAD and CFD evidence.

Requires the session CFD artifacts used by cfd_cpap_r41.py, including the finer candidate-A
results. No synthetic flow field is used. Run with --design-only to regenerate just CAD views.
"""
import argparse
import gc
import hashlib
import json
from pathlib import Path

import cadquery as cq
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import vtk
from vtk.util.numpy_support import numpy_to_vtk

import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import render_cfd_cpap_r41 as F
import r43_swept_feed as R
from build_modular_toolhead import ROOT

S = C.CFD.parent
ASSETS = ROOT / ".cache" / "public_cfd"
IMAGES = ROOT / "images"
BG = "#091321"
PANEL = "#112136"
TEXT = "#f0f5fc"
MUTED = "#a9bbd1"
BLUE = "#62c5ff"
AMBER = "#ffbf69"
FONT_DIR = Path(r"C:\Windows\Fonts")
BASE = "r43_bambu_bed"
LATEST = "r43optAfine_bambu_bed"
WIDTH, HEIGHT = 3600, 5680


def font(size, bold=False):
    return ImageFont.truetype(str(FONT_DIR / ("segoeuib.ttf" if bold else "segoeui.ttf")), size)


def cad_actor(shape, colour, opacity=1.0):
    vertices, triangles = shape.tessellate(.035, .12)
    points = vtk.vtkPoints()
    points.SetData(numpy_to_vtk(np.asarray([v.toTuple() for v in vertices]), deep=True))
    cells = vtk.vtkCellArray()
    for triangle in triangles:
        cells.InsertNextCell(3, triangle)
    poly = vtk.vtkPolyData()
    poly.SetPoints(points)
    poly.SetPolys(cells)
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(poly)
    normals.SetFeatureAngle(45)
    normals.Update()
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputConnection(normals.GetOutputPort())
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(*colour)
    prop.SetOpacity(opacity)
    prop.SetInterpolationToPhong()
    prop.SetAmbient(.42)
    prop.SetDiffuse(.65)
    prop.SetSpecular(.22)
    prop.SetSpecularPower(45)
    return actor


def render_designs():
    ASSETS.mkdir(parents=True, exist_ok=True)
    scene = S / "r43_scene"
    manifest = json.loads((scene / "manifest.json").read_text())
    load = lambda file: cq.Shape.importBrep(str(scene / file))
    carriage = dict(manifest["carriage"])
    probe = load(next(file for name, file in carriage.items() if name.startswith("Beacon_")))
    mount = load(next(file for name, file in carriage.items() if name.startswith("P23_")))
    hotend = load(dict(manifest["variants"]["Bambu"]["parts"])["hotend"])
    base = cq.Shape.importBrep(str(C.CFD / "p22_r43.brep"))
    candidate = cq.Shape.importBrep(str(S / "swept_feed" / "optA" / "p22_swept_beacon.brep"))
    air = cq.Shape.importBrep(str(S / "swept_feed" / "optA" / "swept_air.brep"))
    crop = cq.Solid.makeBox(60, 58, 19, cq.Vector(-30, -22, -80))
    for label, part in (("r43", base), ("candidate_a", candidate)):
        renderer = vtk.vtkRenderer()
        renderer.SetBackground(.067, .129, .212)
        renderer.SetUseDepthPeeling(True)
        renderer.SetMaximumNumberOfPeels(100)
        renderer.SetOcclusionRatio(.1)
        renderer.AddActor(cad_actor(part.intersect(crop), (.68, .84, .93), .18))
        if label == "r43":
            renderer.AddActor(cad_actor(mount.intersect(crop), (.68, .84, .93), .65))
        else:
            actor = cad_actor(air, (1, .62, .20))
            actor.GetMapper().SetResolveCoincidentTopologyToPolygonOffset()
            actor.GetMapper().SetRelativeCoincidentTopologyPolygonOffsetParameters(-2, -2)
            renderer.AddActor(actor)
        renderer.AddActor(cad_actor(probe, (.48, .37, .68)))
        renderer.AddActor(cad_actor(hotend.intersect(crop), (.38, .52, .66)))
        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(0, 3, -68)
        camera.SetPosition(45, -65, 60)
        camera.SetViewUp(0, 0, 1)
        camera.ParallelProjectionOn()
        camera.SetParallelScale(28)
        renderer.ResetCameraClippingRange()
        window = vtk.vtkRenderWindow()
        window.SetOffScreenRendering(True)
        window.SetAlphaBitPlanes(1)
        window.SetMultiSamples(0)
        window.SetSize(1540, 760)
        window.AddRenderer(renderer)
        window.Render()
        capture = vtk.vtkWindowToImageFilter()
        capture.SetInput(window)
        capture.ReadFrontBufferOff()
        capture.Update()
        writer = vtk.vtkPNGWriter()
        writer.SetFileName(str(ASSETS / f"design_{label}.png"))
        writer.SetInputConnection(capture.GetOutputPort())
        writer.Write()
        window.Finalize()
        print("saved design", label, flush=True)


def render_outlets(inspection=False):
    """Matched opaque views of the real exit openings, not highlighted air solids."""
    scene = S / "r43_scene"
    manifest = json.loads((scene / "manifest.json").read_text())
    carriage = dict(manifest["carriage"])
    load = lambda file: cq.Shape.importBrep(str(scene / file))
    probe = load(next(file for name, file in carriage.items() if name.startswith("Beacon_")))
    mount = load(next(file for name, file in carriage.items() if name.startswith("P23_")))
    hotend = load(dict(manifest["variants"]["Bambu"]["parts"])["hotend"])
    parts = {
        "r43": cq.Shape.importBrep(str(C.CFD / "p22_r43.brep")),
        "candidate_a": cq.Shape.importBrep(
            str(S / "swept_feed" / "optA" / "p22_swept_beacon.brep")),
    }
    crop = cq.Solid.makeBox(60, 58, 19, cq.Vector(-30, -22, -80))
    for tag, part in parts.items():
        renderer = vtk.vtkRenderer()
        renderer.SetBackground(.067, .129, .212)
        renderer.AutomaticLightCreationOff()
        renderer.SetUseFXAA(True)
        renderer.AddActor(cad_actor(part.intersect(crop), (.63, .76, .86)))
        if tag == "r43":
            renderer.AddActor(cad_actor(mount.intersect(crop), (.63, .76, .86)))
        renderer.AddActor(cad_actor(probe, (.40, .31, .56)))
        hotend_crop = crop
        if inspection:
            hotend_crop = cq.Solid.makeBox(60, 58, 2.8, cq.Vector(-30, -22, -80))
        renderer.AddActor(cad_actor(hotend.intersect(hotend_crop), (.77, .62, .40)))
        camera = renderer.GetActiveCamera()
        camera.SetFocalPoint(0, 17, -74.5)
        camera.SetPosition(*(45, 55, -97) if inspection else (0, 43, -125))
        camera.SetViewUp(*(0, 0, 1) if inspection else (0, -1, 0))
        camera.ParallelProjectionOn()
        camera.SetParallelScale(18)
        renderer.ResetCameraClippingRange()
        for actor in renderer.GetActors():
            prop = actor.GetProperty()
            prop.SetAmbient(.15)
            prop.SetDiffuse(.80)
            prop.SetSpecular(.28)
            prop.SetSpecularPower(45)
        for position, intensity in (
            ((45, 50, -100), 1.0), ((-30, 30, -85), .45), ((5, -10, -40), .60),
        ):
            light = vtk.vtkLight()
            light.SetLightTypeToSceneLight()
            light.SetPosition(*position)
            light.SetFocalPoint(0, 18, -75)
            light.SetIntensity(intensity)
            renderer.AddLight(light)
        steps = vtk.vtkRenderStepsPass()
        occlusion = vtk.vtkSSAOPass()
        occlusion.SetDelegatePass(steps)
        occlusion.SetRadius(2)
        occlusion.SetBias(.04)
        occlusion.SetKernelSize(128)
        occlusion.BlurOn()
        renderer.SetPass(occlusion)
        window = vtk.vtkRenderWindow()
        window.SetOffScreenRendering(True)
        window.SetMultiSamples(8)
        resolution_scale = 2 if inspection else 1
        window.SetSize(1540 * resolution_scale, 1000 * resolution_scale)
        window.AddRenderer(renderer)
        window.Render()
        capture = vtk.vtkWindowToImageFilter()
        capture.SetInput(window)
        capture.ReadFrontBufferOff()
        capture.Update()
        writer = vtk.vtkPNGWriter()
        prefix = "ports" if inspection else "outlets"
        writer.SetFileName(str(ASSETS / f"{prefix}_{tag}.png"))
        writer.SetInputConnection(capture.GetOutputPort())
        writer.Write()
        if inspection:
            Image.open(ASSETS / f"{prefix}_{tag}.png").crop((760, 660, 2640, 1600)).save(
                ASSETS / f"ports_closeup_{tag}.png")
        landmarks = {}
        for label, point in {
            "left": (-10.2, 22.7, -75.5), "right": (10.2, 22.7, -75.5),
            "rear": R.mouth(7).toTuple(), "nozzle": (0, 22.7, -78.88),
        }.items():
            renderer.SetWorldPoint(*point, 1)
            renderer.WorldToDisplay()
            x, y, _ = renderer.GetDisplayPoint()
            landmarks[label] = [x / resolution_scale, 1000 - y / resolution_scale]
        (ASSETS / f"{prefix}_{tag}.json").write_text(json.dumps(landmarks, indent=2))
        window.Finalize()
        print("saved", prefix, tag, flush=True)


def sample_map(grid, axis, at, window, nx=600):
    h, v = {"x": (1, 2), "z": (0, 1)}[axis]
    ny = round(nx * (window[3] - window[2]) / (window[1] - window[0]))
    x = np.linspace(window[0], window[1], nx)
    y = np.linspace(window[2], window[3], ny)
    xx, yy = np.meshgrid(x, y)
    points = np.zeros((xx.size, 3))
    points[:, h], points[:, v] = xx.ravel(), yy.ravel()
    points[:, "xyz".index(axis)] = at
    velocity, valid = P.probe(grid, points)
    speed = np.linalg.norm(velocity, axis=1).reshape(xx.shape)
    return x, y, np.ma.array(speed, mask=~valid.reshape(xx.shape)), velocity, valid


def render_streamline_view(grid, name, tag):
    seeds = np.asarray([
        (side * x, -12, z) for side in (-1, 1)
        for x in np.linspace(13.3, 20.6, 8) for z in np.linspace(-68.5, -59, 8)
    ])
    _, valid = P.probe(grid, seeds)
    actor = F.streamlines(grid, seeds[valid], 180)
    bounds = vtk.vtkBox()
    bounds.SetBounds(-22, 22, 10, 36, -79.08, -70)
    clip = vtk.vtkClipPolyData()
    clip.SetInputData(actor.GetMapper().GetInput())
    clip.SetClipFunction(bounds)
    clip.InsideOutOn()
    clip.Update()
    tubes = clip.GetOutput()
    if not tubes.GetNumberOfCells():
        raise ValueError(f"{name}: no traced outlet flow; refusing an empty visual")
    actor.GetMapper().SetInputData(tubes)
    actor.GetMapper().SetLookupTable(F.lut(65))
    actor.GetMapper().SetScalarRange(0, 65)
    actor.GetProperty().SetAmbient(.5)
    walls = P.boundary(name, 1200, "walls")
    renderer = vtk.vtkRenderer()
    renderer.SetBackground(.067, .129, .212)
    renderer.SetUseDepthPeeling(True)
    renderer.SetMaximumNumberOfPeels(100)
    renderer.SetOcclusionRatio(.01)
    renderer.AddActor(F.surface(walls, (-23, 23, 6, 36, -79.08, -67), .13))
    renderer.AddActor(actor)
    camera = renderer.GetActiveCamera()
    camera.SetPosition(45, 55, -97)
    camera.SetFocalPoint(0, 17, -74.5)
    camera.SetViewUp(0, 0, 1)
    camera.ParallelProjectionOn()
    camera.SetParallelScale(18)
    renderer.ResetCameraClippingRange()
    window = vtk.vtkRenderWindow()
    window.SetOffScreenRendering(True)
    window.SetAlphaBitPlanes(1)
    window.SetMultiSamples(0)
    window.SetSize(2200, 1450)
    window.AddRenderer(renderer)
    window.Render()
    capture = vtk.vtkWindowToImageFilter()
    capture.SetInput(window)
    capture.ReadFrontBufferOff()
    capture.Update()
    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(ASSETS / f"streamlines_{tag}.png"))
    writer.SetInputConnection(capture.GetOutputPort())
    writer.Write()
    window.Finalize()
    print("saved streamlines", name, "valid seeds", int(valid.sum()), flush=True)


def render_maps():
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 18,
                         "text.color": TEXT, "axes.labelcolor": MUTED,
                         "xtick.color": MUTED, "ytick.color": MUTED, "axes.edgecolor": "#3c5069"})
    for name, tag in ((BASE, "r43"), (LATEST, "candidate_a")):
        if not P.mesh_stats(name)["mesh_ok"]:
            raise ValueError(f"{name}: failed mesh cannot appear in public comparison")
        if not any(stage["lpm"] == 180 and stage["end"] == 1200 for stage in P.stages(name)):
            raise ValueError(f"{name}: missing the matched 180 L/min, iteration-1200 stage")
        grid = P.internal(name, 1200)
        render_streamline_view(grid, name, tag)
        for axis, at, limits, label in (
            ("z", -78.78, (-14, 14, 8.7, 36.7), "plan"),
            ("x", 0, (-8, 36, -79.8, -63.8), "side"),
        ):
            x, y, speed, velocity, valid = sample_map(grid, axis, at, limits)
            fig, ax = plt.subplots(figsize=(11, 10.1) if axis == "z" else (11, 4.7))
            fig.patch.set_facecolor(PANEL)
            ax.set_facecolor("#a9b5c3")
            ax.imshow(speed, origin="lower", extent=limits, cmap="turbo", vmin=0, vmax=65,
                      interpolation="nearest", aspect="equal")
            if axis == "z":
                for radius in (5, 10):
                    ax.add_patch(plt.Circle((0, 22.7), radius, fill=False, color="white",
                                           lw=1.1, alpha=.5, linestyle="--"))
                ax.plot(0, 22.7, marker="+", color="white", markersize=13, markeredgewidth=2)
                ax.annotate("nozzle", (0, 22.7), (4.8, 25.2), color="white", fontsize=17,
                            arrowprops={"arrowstyle": "-", "color": "white", "lw": 1})
                ax.set_xlabel("X (mm)")
                ax.set_ylabel("Y (mm)  |  front at top")
                ax.set_xticks((-10, -5, 0, 5, 10))
                ax.set_yticks((10, 15, 20, 25, 30, 35))
            else:
                # Arrows show normalized projected direction, not proportional speed.
                xx, yy = np.meshgrid(np.linspace(-7, 35, 29), np.linspace(-79, -65, 11))
                pts = np.column_stack((np.zeros(xx.size), xx.ravel(), yy.ravel()))
                u, ok = P.probe(grid, pts)
                mag = np.hypot(u[:, 1], u[:, 2])
                keep = ok & (mag > 2)
                ax.quiver(xx.ravel()[keep], yy.ravel()[keep],
                          u[keep, 1] / mag[keep], u[keep, 2] / mag[keep],
                          color="white", alpha=.7, scale=37, width=.0024, headwidth=3.5)
                ax.axhline(-79.08, color=AMBER, lw=1.6)
                ax.plot(22.7, -78.88, "+", color="white", markersize=11)
                ax.set_xlabel("Y (mm)  |  probe left / nozzle right")
                ax.set_ylabel("Z (mm)")
                ax.set_xticks((0, 10, 20, 30))
                ax.set_yticks((-78, -74, -70, -66))
            ax.set_xlim(limits[:2])
            ax.set_ylim(limits[2:])
            fig.tight_layout(pad=1.3)
            fig.savefig(ASSETS / f"map_{tag}_{label}.png", dpi=150, facecolor=PANEL)
            plt.close(fig)
        del grid
        gc.collect()
    fig, ax = plt.subplots(figsize=(20, .95))
    fig.patch.set_facecolor(PANEL)
    bar = fig.colorbar(plt.cm.ScalarMappable(norm=plt.Normalize(0, 65), cmap="turbo"),
                       cax=ax, orientation="horizontal", ticks=(0, 10, 20, 30, 40, 50, 60, 65),
                       extend="max")
    bar.ax.set_xticklabels(("0", "10", "20", "30", "40", "50", "60", "65+"))
    bar.ax.tick_params(labelsize=17, colors=TEXT)
    fig.tight_layout(pad=.4)
    fig.savefig(ASSETS / "speed_scale.png", dpi=150, facecolor=PANEL)
    plt.close(fig)


def annotate_ports(image, tag, box):
    draw = ImageDraw.Draw(image)
    scale = min((box[2] - box[0]) / 940, (box[3] - box[1]) / 470)
    ox = box[0] + (box[2] - box[0] - round(940 * scale)) // 2
    oy = box[1] + (box[3] - box[1] - round(470 * scale)) // 2
    points = json.loads((ASSETS / f"ports_{tag}.json").read_text())
    labels = [
        ("left", "SIDE OUTLET", (box[0] + 1080, box[1] + 55), BLUE),
        ("rear", "REAR OUTLET" if tag == "candidate_a" else "NO REAR OUTLET",
         (box[0] + 70, box[3] - 95), AMBER if tag == "candidate_a" else MUTED),
        ("nozzle", "NOZZLE TIP", (box[0] + 985, box[3] - 95), TEXT),
    ]
    for key, label, (x, y), colour in labels:
        px, py = points[key]
        point = (ox + (px - 380) * scale, oy + (py - 330) * scale)
        label_width = draw.textlength(label, font=font(30, True))
        draw.rounded_rectangle((x - 10, y - 5, x + label_width + 10, y + 45),
                               radius=8, fill=PANEL)
        start = (x + label_width / 2, y + 45 if y < point[1] else y - 5)
        draw.line((start, point), fill=colour, width=3)
        draw.ellipse((point[0] - 5, point[1] - 5, point[0] + 5, point[1] + 5),
                     outline=colour, width=2)
        draw.text((x, y), label, font=font(30, True), fill=colour)


def poster(report):
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    def text(x, y, value, size=44, colour=TEXT, bold=False):
        draw.text((x, y), value, font=font(size, bold), fill=colour)

    def paragraph(x, y, value, width, size=37, colour=MUTED, leading=1.4, bold=False):
        words = value.split()
        line = ""
        for word in words:
            candidate = (line + " " + word).strip()
            if draw.textlength(candidate, font=font(size, bold)) > width:
                if not line:
                    raise ValueError(f"Unbreakable text: {word}")
                text(x, y, line, size, colour, bold)
                y += round(size * leading)
                line = word
            else:
                line = candidate
        if line:
            text(x, y, line, size, colour, bold)
            y += round(size * leading)
        return y

    def card(box):
        draw.rounded_rectangle(box, radius=28, fill=PANEL)

    def asset(name, box):
        picture = Image.open(ASSETS / name).convert("RGB")
        scale = min((box[2] - box[0]) / picture.width, (box[3] - box[1]) / picture.height)
        picture = picture.resize((round(picture.width * scale), round(picture.height * scale)),
                                 Image.Resampling.LANCZOS)
        image.paste(picture, (box[0] + (box[2] - box[0] - picture.width) // 2,
                              box[1] + (box[3] - box[1] - picture.height) // 2))

    a, b = report["cases"][BASE], report["cases"][LATEST]
    resolution = report["candidate_a_local_resolution_check"]
    text(120, 70, "SPARKSHIFT  /  OPEN DESIGN STUDY", 39, BLUE, True)
    text(120, 145, "Where does the air go?", 112, TEXT, True)
    text(125, 290, "R43 vs. swept-feed candidate A  |  Bambu Lab hotend assembly", 48, MUTED)
    draw.rounded_rectangle((120, 385, 3480, 475), radius=20, fill="#223246")
    text(155, 402, "AIRFLOW SIMULATION  /  NOT A PROVEN COOLING UPGRADE  /  FEEDBACK WELCOME",
         37, AMBER, True)

    text(120, 530, "01  THE OUTLET OPENINGS", 47, TEXT, True)
    text(120, 610, "R43  /  BASELINE", 55, BLUE, True)
    text(1910, 610, "CANDIDATE A  /  LATEST STUDY", 55, AMBER, True)
    left, right = (120, 700, 1690, 1460), (1910, 700, 3480, 1460)
    card(left)
    card(right)
    asset("ports_closeup_r43.png", left)
    asset("ports_closeup_candidate_a.png", right)
    annotate_ports(image, "r43", left)
    annotate_ports(image, "candidate_a", right)
    paragraph(150, 1490, "Existing side jets. Separate probe bracket. No rear-feed outlet.",
              1490, 39, TEXT)
    paragraph(1940, 1490, "Swept takeoffs merge above the probe. Roof +3 mm; curved rear slot "
              "18 mm wide x 0.9 mm high, aimed 32 degrees down.", 1490, 39, TEXT)
    text(150, 1640, "Opaque duct = pale blue   |   Probe = violet   |   Nozzle tip = gold",
         36, MUTED)
    text(150, 1695, "Same diagonal camera and scale. Heater block omitted to expose ports; nozzle tip retained.",
         34, MUTED)

    text(120, 1800, "02  MATCHED-FLOW CFD", 47, TEXT, True)
    text(120, 1880, "Both at 180 L/min. Colour = SPEED, not temperature.", 37, MUTED)
    text(1910, 1805, "SHARED AIR-SPEED SCALE (m/s)", 35, MUTED, True)
    asset("speed_scale.png", (1910, 1855, 3480, 1950))
    text(120, 1960, "From above: 0.3 mm above the bed", 45, TEXT, True)
    card((120, 2040, 1690, 3495))
    card((1910, 2040, 3480, 3495))
    asset("map_r43_plan.png", (125, 2045, 1685, 3490))
    asset("map_candidate_a_plan.png", (1915, 2045, 3475, 3490))
    text(150, 3520, "Dashed circles: 5 and 10 mm radius. White cross: nozzle axis. Grey: outside sampled fluid.",
         35, MUTED)
    text(120, 3610, "Centre cut: probe left, nozzle right", 45, TEXT, True)
    card((120, 3685, 1690, 4350))
    card((1910, 3685, 3480, 4350))
    asset("map_r43_side.png", (125, 3690, 1685, 4345))
    asset("map_candidate_a_side.png", (1915, 3690, 3475, 4345))
    text(150, 4375, "Arrows: projected direction, not speed. Amber horizontal line: bed, 0.2 mm below nozzle tip.",
         34, MUTED)
    # Continue on a second metrics panel beside no cropped or selectively rescaled CFD fields.
    card((120, 4460, 3480, 5560))
    text(165, 4500, "03  NUMBERS, CONDITIONS & LIMITS", 45, TEXT, True)
    pressure_change = 100 * (b["pressure_at_180_pa"] / a["pressure_at_180_pa"] - 1)
    text(165, 4590, f"{pressure_change:+.1f}% inlet pressure at matched flow", 49, AMBER, True)
    text(165, 4660, "Lower resistance is not, by itself, better cooling.", 38, TEXT)
    rows = [
        ("Inlet total pressure at 180 L/min", f"{a['pressure_at_180_pa']:,.0f} Pa", f"{b['pressure_at_180_pa']:,.0f} Pa"),
        ("Rear branch at 180 L/min", "none", f"{b['branch']['merged_trunk_y4.25']['flow_lpm']:.1f} L/min"),
        ("Estimated blower flow*", f"{a['estimated_blower_lpm_1m_hose']:.1f} L/min",
         f"{b['estimated_blower_lpm_1m_hose']:.1f} L/min"),
        ("Mean speed, radius 1-5 / 1-10 / 1-14 mm*",
         " / ".join(f"{a['near_print_mean_speed_ms_at_estimated_blower'][k]:.1f}" for k in ("r5_mm", "r10_mm", "r14_mm")) + " m/s",
         " / ".join(f"{b['near_print_mean_speed_ms_at_estimated_blower'][k]:.1f}" for k in ("r5_mm", "r10_mm", "r14_mm")) + " m/s"),
        ("Net near-bed radial flow at radius 8 mm*",
         f"{a['near_print_net_radial_outflow_within_1mm_lpm_at_estimated_blower']['r8_mm']:.1f} L/min",
         f"{b['near_print_net_radial_outflow_within_1mm_lpm_at_estimated_blower']['r8_mm']:.1f} L/min"),
    ]
    text(1960, 4745, "R43", 34, BLUE, True)
    text(2700, 4745, "CANDIDATE A", 34, AMBER, True)
    for i, (label, av, bv) in enumerate(rows):
        y = 4805 + i * 75
        draw.line((165, y - 10, 3435, y - 10), fill="#2a3e55", width=2)
        text(165, y, label, 33, TEXT)
        text(1960, y, av, 35, BLUE, True)
        text(2700, y, bv, 35, AMBER, True)
    foot = (
        "*Estimated WS7040 operation, 100% PWM + 1 m hose; single-flow pressure-law extrapolation "
        "(exponent 1.983). Speeds sampled 0.3 mm above bed; radial flow is net through the first "
        "1 mm above bed, not a fresh-air tracer. Maps above remain at 180 L/min."
    )
    end = paragraph(165, 5205, foot, 3210, 29, MUTED, 1.3)
    end = paragraph(165, end + 14,
                    f"LOCAL RESOLUTION CHECK: A outlet cells nominally 0.25 -> 0.125 mm; "
                    f"pressure {resolution['pressure_at_180_pct']:+.1f}%, "
                    f"rear flow {resolution['rear_branch_at_180_pct']:+.1f}%, within-5-mm mean speed "
                    f"{resolution['near_print_mean_speed_at_estimated_blower_pct']['r5_mm']:+.1f}%. "
                    "Not a global mesh-independence result.", 3210, 29, AMBER, 1.3)
    if end > 5535:
        raise RuntimeError(f"Poster footer overflow: {end}")
    text(130, 5600, "nisparks / SparkShift   |   OpenFOAM v2512, steady k-omega SST, 1,200 iterations   |   Study, not release",
         29, MUTED)
    # Save the initial layout; add the complete evidence strip on a separate extension below.
    evidence_height = 700
    extended = Image.new("RGB", (WIDTH, HEIGHT + evidence_height), BG)
    extended.paste(image, (0, 0))
    image = extended
    draw = ImageDraw.Draw(image)
    card((120, 5720, 3480, 6270))
    text(165, 5750, "WHAT THIS IMAGE DOES NOT PROVE", 40, AMBER, True)
    notes = [
        "No temperature/heat-transfer solution, deposited bead, moving tool or physical cooling test. "
        "Mean air speed is a diagnostic, not a cooling score; stagnation can transfer heat well.",
        f"R43: {a['mesh']['cells']:,} cells / 30 cores. A: {b['mesh']['cells']:,} cells / 46 cores. "
        "Both pass checkMesh; baseline and candidate have different local refinement. "
        "No formal mesh independence. VTK contour warnings affect approximate section-flow integrals. "
        f"Last 500 iterations: inlet-pressure peak-to-peak R43 "
        f"{100 * a['pressure_history_last_500']['relative_peak_to_peak']:.1f}%, A "
        f"{100 * b['pressure_history_last_500']['relative_peak_to_peak']:.1f}%. "
        "Residuals still oscillate; pressure entries average the last 100 iterations, fields are iteration 1200.",
        "Geometry: Beacon scene in CFD. Cartographer checked geometrically only. Same Bambu hotend "
        "and modelled sock, flat bed 0.2 mm below tip, room-temperature incompressible airflow.",
        "Candidate A is not print-qualified. 0.9 mm slot and internal bridges need slicer review; "
        "minimum Red Lizard gap 0.638 mm needs heat/tolerance allowance. Released R43 is unchanged.",
    ]
    y = 5825
    for note in notes:
        y = paragraph(165, y, note, 3220, 29, MUTED, 1.3) + 10
    if y > 6250:
        raise RuntimeError(f"Evidence strip overflow: {y}")
    text(165, 6300, "FEEDBACK: flow direction & coverage  /  printable passage geometry  /  useful physical cooling tests", 30, TEXT)
    output = IMAGES / "sparkshift_r43_vs_candidate_a_technical.png"
    image.save(output, optimize=True)
    return output


def public_sheet(report):
    image = Image.new("RGB", (3600, 3900), BG)
    draw = ImageDraw.Draw(image)

    def text(x, y, value, size=38, colour=TEXT, bold=False):
        draw.text((x, y), value, font=font(size, bold), fill=colour)

    def asset(name, box):
        picture = Image.open(ASSETS / name).convert("RGB")
        scale = min((box[2] - box[0]) / picture.width, (box[3] - box[1]) / picture.height)
        picture = picture.resize((round(picture.width * scale), round(picture.height * scale)),
                                 Image.Resampling.LANCZOS)
        draw.rounded_rectangle(box, radius=24, fill=PANEL)
        image.paste(picture, (box[0] + (box[2] - box[0] - picture.width) // 2,
                              box[1] + (box[3] - box[1] - picture.height) // 2))

    a, b = report["cases"][BASE], report["cases"][LATEST]
    text(120, 65, "SPARKSHIFT  /  BAMBU LAB HOTEND  /  OPEN DESIGN STUDY", 36, BLUE, True)
    text(115, 135, "Two side jets. Add a rear jet?", 104, TEXT, True)
    text(120, 280, "Real geometry. Matched-flow CFD. No claimed cooling winner.", 46, MUTED)
    text(120, 410, "RELEASED R43", 54, BLUE, True)
    text(1910, 410, "CANDIDATE A  /  NOT RELEASED", 54, AMBER, True)
    asset("ports_closeup_r43.png", (120, 510, 1690, 1300))
    asset("ports_closeup_candidate_a.png", (1910, 510, 3480, 1300))
    annotate_ports(image, "r43", (120, 510, 1690, 1300))
    annotate_ports(image, "candidate_a", (1910, 510, 3480, 1300))
    text(150, 1330, "Side outlet + existing probe bracket; no rear slot.", 36)
    text(1940, 1330, "Side outlet + curved 18 x 0.9 mm rear slot, 32 deg down.", 36)
    text(150, 1400, "Same diagonal camera and scale. The opposite side outlet is symmetrical.", 35, MUTED)
    text(150, 1455, "Heater block hidden ONLY in these CAD views; gold nozzle tip retained. Violet = probe.", 35, MUTED)
    text(120, 1560, "THE SIMULATED AIR PATHS", 47, TEXT, True)
    text(120, 1630, "Both at 180 L/min. Full modelled hotend/sock remain in the CFD.", 37, MUTED)
    asset("streamlines_r43.png", (120, 1720, 1690, 2755))
    asset("streamlines_candidate_a.png", (1910, 1720, 3480, 2755))
    asset("speed_scale.png", (120, 2795, 1910, 2900))
    text(2000, 2785, "AIR SPEED (m/s), NOT TEMPERATURE", 34, TEXT, True)
    text(2000, 2840, "128 identical upstream seeds. Density is NOT flow rate.", 30, MUTED)
    text(2000, 2885, "Walls ghosted/cropped to reveal the paths; no bed shown.", 30, MUTED)
    draw.rounded_rectangle((120, 2980, 3480, 3525), radius=24, fill=PANEL)
    text(170, 3010, "AIRFLOW DIAGNOSTICS, NOT A COOLING SCORE", 35, TEXT, True)
    text(2160, 3010, "R43", 35, BLUE, True)
    text(2800, 3010, "CANDIDATE A", 35, AMBER, True)
    rows = [
        ("Inlet total pressure at 180 L/min",
         f"{a['pressure_at_180_pa']:,.0f} Pa", f"{b['pressure_at_180_pa']:,.0f} Pa"),
        ("Rear branch at 180 L/min", "none",
         f"{b['branch']['merged_trunk_y4.25']['flow_lpm']:.1f} L/min"),
        ("Estimated total blower flow*", f"{a['estimated_blower_lpm_1m_hose']:.1f} L/min",
         f"{b['estimated_blower_lpm_1m_hose']:.1f} L/min"),
        ("Mean speed, radius 1-5 mm, 0.3 mm above bed*",
         f"{a['near_print_mean_speed_ms_at_estimated_blower']['r5_mm']:.1f} m/s",
         f"{b['near_print_mean_speed_ms_at_estimated_blower']['r5_mm']:.1f} m/s"),
    ]
    for i, (label, av, bv) in enumerate(rows):
        y = 3090 + i * 100
        draw.line((170, y - 10, 3430, y - 10), fill="#2a3e55", width=2)
        text(170, y + 10, label, 36)
        text(2160, y, av, 48, BLUE, True)
        text(2800, y, bv, 48, AMBER, True)
    resolution = report["candidate_a_local_resolution_check"]
    lines = [
        "*WS7040 100% PWM + 1 m hose: estimated operating points, not measured flow. Pressure-law exponent 1.983.",
        "OpenFOAM v2512 / steady k-omega SST / 1,200 iterations / bed 0.2 mm below nozzle / Beacon CFD scene.",
        f"Both meshes pass checkMesh. A local outlet refinement 0.25 -> 0.125 mm: pressure "
        f"{resolution['pressure_at_180_pct']:+.1f}%, rear flow {resolution['rear_branch_at_180_pct']:+.1f}%, "
        f"within-5-mm speed {resolution['near_print_mean_speed_at_estimated_blower_pct']['r5_mm']:+.1f}%.",
        f"Pressure oscillation, last 500 iterations: R43 "
        f"{100 * a['pressure_history_last_500']['relative_peak_to_peak']:.1f}% / A "
        f"{100 * b['pressure_history_last_500']['relative_peak_to_peak']:.1f}% peak-to-peak. "
        "Not fully residual-converged or mesh-independent.",
        "No heat-transfer solution, deposited bead or physical cooling test. Candidate A is not print-qualified.",
        "Detailed plane maps, mesh counts, integration caveats and source data: companion technical graphic + repository.",
    ]
    for i, line in enumerate(lines):
        text(130, 3570 + i * 42, line, 29, MUTED)
    text(130, 3845, "nisparks/SparkShift  /  Feedback: outlet geometry, flow distribution & meaningful physical tests",
         31, TEXT, True)
    output = IMAGES / "sparkshift_r43_vs_candidate_a_public.png"
    image.save(output, optimize=True)
    share = image.resize((2160, 2340), Image.Resampling.LANCZOS)
    share.save(IMAGES / "sparkshift_r43_vs_candidate_a_public_share.jpg", quality=94, subsampling=0)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--design-only", action="store_true")
    args = parser.parse_args()
    ASSETS.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(exist_ok=True)
    render_designs()
    render_outlets()
    render_outlets(inspection=True)
    if args.design_only:
        return
    report_path = ROOT / "verification_swept_feed_cfd_r43.json"
    report = json.loads(report_path.read_text())
    if LATEST not in report["cases"] or "candidate_a_local_resolution_check" not in report:
        raise ValueError("Public graphic requires completed finer-mesh analysis, not preliminary data")
    render_maps()
    technical = poster(report)
    output = public_sheet(report)
    def digest(path):
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    manifest = {
        "output": output.name,
        "technical_companion": technical.name,
        "report": report_path.name,
        "report_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest(),
        "renderer_sha256": digest(Path(__file__)),
        "output_sha256": {
            path.name: digest(path) for path in (
                output, technical, IMAGES / "sparkshift_r43_vs_candidate_a_public_share.jpg")
        },
        "geometry_sha256": {
            "released_p22": digest(C.CFD / "p22_r43.brep"),
            "candidate_a_p22": digest(S / "swept_feed" / "optA" / "p22_swept_beacon.brep"),
        },
        "cases": [BASE, LATEST], "iteration": 1200, "maps_flow_lpm": 180,
        "maps_speed_scale_ms": [0, 65],
        "upper_speed_colour_saturates_at_ms": 65,
        "candidate_geometry": {"roof_raise_mm": 3, "mouth_height_mm": .9, "angle_deg": 32},
        "images_are_airflow_not_temperature": True,
        "cad_view_heater_block_omitted_but_nozzle_tip_retained": True,
        "streamlines_seed_count": 128,
        "streamlines_density_is_not_flow_rate": True,
        "published_camera": {
            "eye_mm": [45, 55, -97], "focus_mm": [0, 17, -74.5],
            "up": [0, 0, 1], "parallel_scale_mm": 18,
        },
    }
    (ROOT / "verification_public_cfd_graphic_r43.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
