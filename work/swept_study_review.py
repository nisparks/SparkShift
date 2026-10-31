import argparse
import json
import os
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).resolve().parent
OUT = S / "swept_feed"
parser = argparse.ArgumentParser()
parser.add_argument("--roof-raise", type=float, default=0.0)
parser.add_argument("--tag")
args = parser.parse_args()
RAISE = args.roof_raise
if args.tag:
    OUT = OUT / args.tag
elif RAISE:
    OUT = OUT / f"roof{RAISE:g}"
sys.path.insert(0, str(CAD))
os.chdir(CAD)
import cadquery as cq
import build_and_verify_accessories_v26 as acc
import r37_parts as B
import r42_parts as C
from audit_tool_owned_2510 import compound

report = json.loads((OUT / "qualification.json").read_text())
assert report["geometry_checks_pass"]
part = cq.Shape.importBrep(str(OUT / "p22_swept_beacon.brep"))
carto = cq.Shape.importBrep(str(OUT / "p22_swept_cartographer.brep"))
air = cq.Shape.importBrep(str(OUT / "swept_air.brep"))
manifest = json.loads((acc.WORK / "r43_scene" / "manifest.json").read_text())
tools = {}
for label in ("Bambu", "RedLizard"):
    tools[label] = [cq.Shape.importBrep(str(acc.WORK / "r43_scene" / f))
                    for n, f in manifest["variants"][label]["parts"] if n in ("hotend", "hotend and hardware")]
region = cq.Solid.makeBox(60, 85, 40, cq.Vector(-30, -48, -80))
half = cq.Solid.makeBox(35, 85, 40, cq.Vector(-35, -48, -80))
assembly = cq.Assembly(name="swept_island_geometry_checked_study")
for tag, dx, p, sensor, tool, keep, show_air in (
    ("Bambu_Beacon", 0, part, compound(B.beacon()[2:5]), "Bambu", region, False),
    ("RedLizard_Carto", 65, carto, C.cartographer(), "RedLizard", region, False),
    ("Air_route", 130, part, compound(B.beacon()[2:5]), "Bambu", region, True),
    ("Cutaway_X0", 195, part, compound(B.beacon()[2:5]), "Bambu", half, True),
):
    assembly.add(p.intersect(keep).translate((dx, 0, 0)), name=tag+"_P22", color=cq.Color(.1, .6, .3))
    assembly.add(sensor.intersect(keep).translate((dx, 0, 0)), name=tag+"_probe", color=cq.Color(.45, .25, .65))
    for i, hotend in enumerate(tools[tool]):
        assembly.add(hotend.intersect(keep).translate((dx, 0, 0)), name=f"{tag}_hotend_{i}",
                     color=cq.Color(.2, .45, .9) if tool == "Bambu" else cq.Color(.85, .2, .2))
    if show_air:
        assembly.add(air.intersect(keep).translate((dx, 0, 0)), name=tag+"_AIR_not_material",
                     color=cq.Color(1, .5, .05))
assembly.save(str(OUT / "swept_island_review_final.step"), exportType="STEP")
print("saved", OUT / "swept_island_review_final.step", flush=True)
