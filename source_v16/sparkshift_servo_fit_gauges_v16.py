"""Empirical spline-fit trials from user measurements, not a finished servo mount."""

from collections import Counter
import hashlib
import json
import math
from pathlib import Path
import struct

from PIL import Image, ImageDraw, ImageFont
from shapely.geometry import Polygon
from shapely.geometry.polygon import orient

from OCP.BRep import BRep_Builder, BRep_Tool
from OCP.BRepAlgoAPI import BRepAlgoAPI_Cut
from OCP.BRepBuilderAPI import BRepBuilderAPI_MakeFace, BRepBuilderAPI_MakePolygon
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform
from OCP.BRepCheck import BRepCheck_Analyzer
from OCP.BRepGProp import BRepGProp
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox, BRepPrimAPI_MakeCylinder
from OCP.BRepPrimAPI import BRepPrimAPI_MakePrism
from OCP.GProp import GProp_GProps
from OCP.IFSelect import IFSelect_RetDone
from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer
from OCP.TopAbs import TopAbs_FACE, TopAbs_REVERSED, TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer
from OCP.TopLoc import TopLoc_Location
from OCP.TopoDS import TopoDS, TopoDS_Compound
from OCP.gp import gp_Ax1, gp_Dir, gp_Pnt, gp_Trsf, gp_Vec


OUT = Path(__file__).resolve().parent / "sparkshift_direct_mount_v16"
MAJOR_DIAMETER = 4.86
EXPOSED_HEIGHT = 3.36
PHOTO_TOOTH_COUNT = 21
PHOTO_ROOT_ESTIMATE = 4.62
GAUGE_HEIGHT = 3.


def cut(first, tool):
    operation = BRepAlgoAPI_Cut(first, tool)
    operation.Build()
    if not operation.IsDone():
        raise RuntimeError("The calibration-gauge CAD cut failed")
    shape = operation.Shape()
    if not BRepCheck_Analyzer(shape).IsValid():
        raise RuntimeError("The calibration-gauge cut produced invalid geometry")
    return shape


def profile():
    major, minor = MAJOR_DIAMETER/2, PHOTO_ROOT_ESTIMATE/2
    points = []
    for index in range(PHOTO_TOOTH_COUNT*32):
        angle = 2*math.pi*index/(PHOTO_TOOTH_COUNT*32)
        radius = (major+minor)/2+(major-minor)/2*math.cos(PHOTO_TOOTH_COUNT*angle)
        points.append((radius*math.cos(angle), radius*math.sin(angle)))
    shape = Polygon(points)
    if not shape.is_valid:
        raise RuntimeError("The photo-inferred test profile is not valid")
    return shape


def prism(polygon, height):
    polygon = orient(polygon, sign=1.)
    wire = BRepBuilderAPI_MakePolygon()
    for x, y in list(polygon.exterior.coords)[:-1]:
        wire.Add(gp_Pnt(x, y, -.1))
    wire.Close()
    face = BRepBuilderAPI_MakeFace(wire.Wire()).Face()
    return BRepPrimAPI_MakePrism(face, gp_Vec(0, 0, height+.2)).Shape()


def volume(shape):
    properties = GProp_GProps()
    BRepGProp.VolumeProperties_s(shape, properties)
    value = properties.Mass()
    if not math.isfinite(value) or value <= 0:
        raise RuntimeError("The gauge must have positive solid volume")
    return value


def count_solids(shape):
    explorer = TopExp_Explorer(shape, TopAbs_SOLID)
    count = 0
    while explorer.More():
        count += 1
        explorer.Next()
    return count


def export_binary_stl(shape, path):
    mesher = BRepMesh_IncrementalMesh(shape, .002, False, .07, False)
    if not mesher.IsDone():
        raise RuntimeError("Calibration-gauge tessellation failed")
    records = []
    explorer = TopExp_Explorer(shape, TopAbs_FACE)
    while explorer.More():
        face = TopoDS.Face_s(explorer.Current())
        location = TopLoc_Location()
        triangulation = BRep_Tool.Triangulation_s(face, location)
        if triangulation is None:
            raise RuntimeError("A gauge face has no native triangulation")
        for index in range(1, triangulation.NbTriangles()+1):
            ids = list(triangulation.Triangle(index).Get())
            if face.Orientation() == TopAbs_REVERSED:
                ids[1], ids[2] = ids[2], ids[1]
            points = []
            for vertex in ids:
                point = triangulation.Node(vertex).Transformed(location.Transformation())
                points.append(struct.unpack("<3f", struct.pack(
                    "<3f", point.X(), point.Y(), point.Z())))
            a, b, c = points
            u, v = [b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)]
            n = (u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0])
            length = math.sqrt(sum(value*value for value in n))
            if length <= 1e-12:
                raise RuntimeError("A generated gauge facet is degenerate")
            normal = [value/length for value in n]
            records.append(struct.pack("<12fH", *normal, *a, *b, *c, 0))
        explorer.Next()
    data = b"MG90S PHOTO-INFERRED FIT GAUGES - NOT A FINISHED MOUNT".ljust(80, b" ")
    path.write_bytes(data+struct.pack("<I", len(records))+b"".join(records))
    return len(records)


def verify_stl(path):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84+50*count:
        raise RuntimeError("The gauge STL byte count is invalid")
    edges, direction = Counter(), Counter()
    parent = {}
    volumes = []

    def find(point):
        if point not in parent:
            parent[point] = point
        while parent[point] != point:
            parent[point] = parent[parent[point]]
            point = parent[point]
        return point

    for index in range(count):
        row = struct.unpack_from("<12fH", data, 84+50*index)
        points = (row[3:6], row[6:9], row[9:12])
        a, b, c = points
        cross = (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2],
                 b[0]*c[1]-b[1]*c[0])
        volumes.append((a, sum(a[i]*cross[i] for i in range(3))/6))
        for a, b in ((points[0], points[1]), (points[1], points[2]), (points[2], points[0])):
            edge = tuple(sorted((a, b)))
            edges[edge] += 1
            direction[edge] += 1 if a < b else -1
            parent[find(a)] = find(b)
    if any(v != 2 for v in edges.values()) or any(direction.values()):
        raise RuntimeError("The gauge STL is not closed and coherently oriented")
    components = len({find(point) for point in parent})
    if components != 5:
        raise RuntimeError("Exactly five separate gauge collars are required")
    signed = Counter()
    for point, value in volumes:
        signed[find(point)] += value
    if any(value <= 0 for value in signed.values()):
        raise RuntimeError("A gauge STL component is inside-out")
    return {"triangles": count, "closed_components": components,
            "nonmanifold_edges": 0, "orientation_errors": 0,
            "positive_component_volumes_mm3": sorted(signed.values())}


def overview(rows, path):
    image = Image.new("RGB", (1300, 500), "#f4f5f7")
    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 20)
    title = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 26)
    draw.text((28, 20), "MG90S spline-fit trials - NOT a finished mount", font=title, fill="#202630")
    draw.text((28, 60), "Measured: crest OD 4.86 mm; exposed height 3.36 mm. Gauge depth: 3.00 mm.",
              font=font, fill="#202630")
    for index, row in enumerate(rows):
        cx, cy, scale = 140+index*255, 240, 17
        draw.ellipse((cx-5*scale, cy-5*scale, cx+5*scale, cy+5*scale),
                     fill="#5292bf", outline="#202630", width=2)
        points = [(cx+x*scale, cy-y*scale) for x, y in row["outline"]]
        draw.polygon(points, fill="#f4f5f7", outline="#202630")
        draw.text((cx-100, 345), "Gauge "+str(index+1), font=title, fill="#202630")
        draw.text((cx-100, 383), row["label"], font=font, fill="#202630")
    draw.text((28, 438), "21T is user-confirmed. Root/flank shape is approximate; check fit on the actual shaft.",
              font=font, fill="#9c332e")
    image.save(path)


def main():
    OUT.mkdir(exist_ok=True)
    base = profile()
    builder = BRep_Builder()
    layout = TopoDS_Compound()
    builder.MakeCompound(layout)
    rows = []
    for index, allowance in enumerate((0., .025, .05, .075, None), start=1):
        body = BRepPrimAPI_MakeCylinder(5., GAUGE_HEIGHT).Shape()
        if allowance is None:
            hole = BRepPrimAPI_MakeCylinder(
                2.48, GAUGE_HEIGHT+.2).Shape()
            shape = cut(body, hole)
            outline = [(2.48*math.cos(t*math.pi/180), 2.48*math.sin(t*math.pi/180))
                       for t in range(360)]
            label = "Round 4.96 mm control"
        else:
            polygon = base if allowance == 0 else base.buffer(allowance, quad_segs=8)
            shape = cut(body, prism(polygon, GAUGE_HEIGHT))
            outline = list(polygon.exterior.coords)
            label = "21T +"+format(allowance, ".3f")+" mm radial"
        for notch in range(index):
            tool = BRepPrimAPI_MakeBox(gp_Pnt(4.4, -.35, -.1), 1.2, .7,
                                      GAUGE_HEIGHT+.2).Shape()
            rotation = gp_Trsf()
            rotation.SetRotation(gp_Ax1(gp_Pnt(), gp_Dir(0, 0, 1)),
                                 math.radians((notch-(index-1)/2)*15))
            shape = cut(shape, BRepBuilderAPI_Transform(tool, rotation, True).Shape())
        if count_solids(shape) != 1 or not BRepCheck_Analyzer(shape).IsValid():
            raise RuntimeError("A gauge collar is not one valid solid")
        translation = gp_Trsf()
        translation.SetTranslation(gp_Vec(5+(index-1)*12, 5, 0))
        builder.Add(layout, BRepBuilderAPI_Transform(shape, translation, True).Shape())
        rows.append({"gauge": index, "outer_notches": index, "label": label,
                     "radial_clearance_mm": allowance, "volume_mm3": volume(shape),
                     "outline": outline})
    if count_solids(layout) != 5 or not BRepCheck_Analyzer(layout).IsValid():
        raise RuntimeError("The five-collar calibration layout is invalid")
    step = OUT / "MG90S_photo21T_fit_trials_NOT_FINAL.step"
    writer = STEPControl_Writer()
    if writer.Transfer(layout, STEPControl_AsIs) != IFSelect_RetDone:
        raise RuntimeError("The gauge STEP transfer failed")
    if writer.Write(str(step)) != IFSelect_RetDone:
        raise RuntimeError("The gauge STEP export failed")
    stl = step.with_suffix(".stl")
    export_binary_stl(layout, stl)
    mesh = verify_stl(stl)
    if abs(sum(mesh["positive_component_volumes_mm3"])
           - sum(row["volume_mm3"] for row in rows)) > 1.:
        raise RuntimeError("The raw gauge mesh volume does not match its CAD")
    image = OUT / "MG90S_photo21T_fit_trials_NOT_FINAL.png"
    overview(rows, image)
    report = {
        "status": "FIT TRIALS ONLY - no finished cam interface claimed",
        "measured_spline_major_diameter_mm": MAJOR_DIAMETER,
        "measured_exposed_spline_height_mm": EXPOSED_HEIGHT,
        "nominal_final_boss_clearance_mm": .2, "nominal_final_engagement_mm": 3.16,
        "user_confirmed_tooth_count": PHOTO_TOOTH_COUNT,
        "photo_estimated_root_diameter_mm": PHOTO_ROOT_ESTIMATE,
        "profile_is_sinusoidal_approximation_not_a_manufacturer_spline": True,
        "gauge_height_mm": GAUGE_HEIGHT,
        "gauges": [{k: v for k, v in row.items() if k != "outline"} for row in rows],
        "mesh": mesh, "step": str(step), "stl": str(stl), "overview": str(image),
        "stl_sha256": hashlib.sha256(stl.read_bytes()).hexdigest(),
        "retainer_thread_user_confirmed": "M2.5",
        "retainer_thread_pitch_and_usable_depth_pending": True,
        "actual_tooth_profile_and_printed_torque_fit_pending": True,
        "current_v15_assembly_modified": False,
    }
    (OUT / "fit_trial_receipt.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: v for k, v in report.items() if k != "gauges"}, indent=2))


if __name__ == "__main__":
    main()
