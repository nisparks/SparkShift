import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).parent
sys.path.insert(0, str(CAD))

import cadquery as cq
import r43_c28_mechanical as M
import r43_swept_feed as F
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box

scene = S / "r43_scene"
folder = S / "swept_feed" / "optC28_mechanical"
folder.mkdir(exist_ok=True)
manifest = json.loads((scene / "manifest.json").read_text())


def load(f):
    return cq.Shape.importBrep(str(scene / f))


def named(prefix):
    return load(next(f for n, f in manifest["carriage"] if n.startswith(prefix)))


def bounds(body):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(body.wrapped, b, False, False)
    x0, y0, z0, x1, y1, z1 = b.Get()
    return [x0, x1, y0, y1, z0, z1]


base = {"p01": named("P01_"), "p21": named("P21_"),
        "p22": cq.Shape.importBrep(str(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep"))}
parts = {"p01": M.p01(base["p01"]), "p21": M.p21(base["p21"]),
         "p22": M.retained_p22(M.angled_p22(base["p22"]))}
air = F.main_channel_air()
cable = named("Probe_Cable")
f = manifest["frames"]
gantry = load(manifest["fixed"]["xgantry"]).translate((0, f["x_gantry_y_shift_to_dock_mm"], 0))
gantry = gantry.rotate((0, 0, 0), (0, 0, 1), 180).translate(
    (175, f["world_y_offset_mm"], -f["world_z_offset_mm"]))
report = {"parts": {}, "contacts": [], "hardware": []}
for key, body in parts.items():
    added, removed = body.cut(base[key]), base[key].cut(body)
    body.exportBrep(str(folder / f"{key}.brep"))
    added.exportBrep(str(folder / f"{key}_added.brep"))
    removed.exportBrep(str(folder / f"{key}_removed.brep"))
    row = {
        "bounds_mm": bounds(body), "added_mm3": added.Volume(), "removed_mm3": removed.Volume(),
        "added_in_channel_air_mm3": added.intersect(air).Volume(),
        "cable_overlap_mm3": body.intersect(cable).Volume(),
        "added_cable_gap_mm": added.distance(cable),
        "gantry_overlap_mm3": body.intersect(gantry).Volume(),
        "added_gantry_gap_mm": added.distance(gantry),
    }
    report["parts"][key] = row
    print(key, json.dumps(row), flush=True)
for a, b in (("p01", "p21"), ("p01", "p22"), ("p21", "p22")):
    report["contacts"].append({"a": a, "b": b, "mm3": parts[a].intersect(parts[b]).Volume(),
                               "gap_mm": parts[a].distance(parts[b])})
hardware = M.hardware()
for name, body in hardware:
    body.exportBrep(str(folder / f"{name}.brep"))
    report["hardware"].append({"name": name, "part_overlap_mm3": {
        k: body.intersect(s).Volume() for k, s in parts.items()},
        "cable_gap_mm": body.distance(cable), "gantry_overlap_mm3": body.intersect(gantry).Volume()})
tools = [(n, load(p)) for n, p in manifest["variants"]["Bambu"]["parts"]]
report["tool_intersections"] = [
    {"changed": key, "tool": name, "mm3": v}
    for key, body in list(parts.items()) + hardware
    for name, tool in tools
    if (v := body.intersect(tool).Volume()) > .001]
print("interfaces", json.dumps(report["contacts"]), flush=True)
print("hardware", json.dumps(report["hardware"]), flush=True)
print("tools", json.dumps(report["tool_intersections"]), flush=True)
(folder / "prototype_checks.json").write_text(json.dumps(report, indent=2) + "\n")
