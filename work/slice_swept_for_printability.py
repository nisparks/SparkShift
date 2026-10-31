"""Slice a separate swept P22 with saved H2D ABS presets; never edit global presets or send a print."""
import argparse
import json
import math
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).parent
sys.path.insert(0, str(CAD))
import cadquery as cq
import numpy as np
import trimesh
from build_cpap_outlet_r43 import print_oriented


def extrusion_by_feature(text):
    feature, relative = None, None
    x = y = e = 0.
    rows = {}
    for line in text.splitlines():
        if line.startswith("; FEATURE:"):
            feature = line.split(":", 1)[1].strip()
            continue
        code = line.split(";", 1)[0].strip()
        if not code:
            continue
        command = code.split()[0]
        if command in ("M82", "M83"):
            relative = command == "M83"
            continue
        values = {k: float(v) for k, v in re.findall(r"\b([XYE])(-?(?:\d+(?:\.\d*)?|\.\d+))", code)}
        if command == "G92":
            x, y, e = values.get("X", x), values.get("Y", y), values.get("E", e)
            continue
        if command not in ("G0", "G1", "G2", "G3"):
            continue
        nx, ny = values.get("X", x), values.get("Y", y)
        if "E" in values:
            if relative is None:
                if feature != "Custom":
                    raise ValueError("Extrusion mode is unknown outside startup custom G-code")
                x, y, e = nx, ny, values["E"]
                continue
            delta = values["E"] if relative else values["E"] - e
            moving = (nx, ny) != (x, y) or command in ("G2", "G3")
            if feature and delta > 0 and moving:
                row = rows.setdefault(feature, {"extrusion_mm": 0., "moves": 0})
                row["extrusion_mm"] += delta
                row["moves"] += 1
            e = e + values["E"] if relative else values["E"]
        x, y = nx, ny
    return rows


def analyse_saved(out, brep):
    process = json.loads((out / "process.json").read_text())
    first = json.loads((out / "filament1.json").read_text())
    interface = json.loads((out / "filament5.json").read_text())
    result = json.loads((out / "result.json").read_text())
    if result["return_code"]:
        raise ValueError(f"Cannot analyze a failed slice: {result}")
    with zipfile.ZipFile(out / "sliced.3mf") as archive:
        gcode = archive.read(next(n for n in archive.namelist() if n.endswith(".gcode"))).decode("utf-8")
    roles = extrusion_by_feature(gcode)
    support = {k: v for k, v in roles.items() if k.startswith("Support")}
    if not support:
        raise ValueError("Automatic support run produced no labeled support extrusion")
    diameter = float(first["filament_diameter"][0])
    area = math.pi * diameter**2 / 4
    report = {
        "input_brep": str(brep), "printer": "Bambu Lab H2D 0.4 nozzle",
        "material": first["name"], "interface_material": interface["name"],
        "layer_height_mm": process["layer_height"], "wall_loops": process["wall_loops"],
        "support_policy": "tree(auto), allow support on the part, small-overhang removal disabled; "
                          "identical assessment policy for before/after, not a support-free claim",
        "support_recognized_bridges": process.get("bridge_no_support", "0") == "0",
        "support_extrusion_by_role": support,
        "support_deposition_volume_mm3": sum(v["extrusion_mm"] for v in support.values()) * area,
        "support_feature_time_s": {k: v for k, v in result["sliced_plates"][0]["feature_type_times"].items()
                                  if k.startswith("Support")},
        "total_estimated_time_s": result["sliced_plates"][0]["total_predication"],
        "warnings": result["sliced_plates"][0]["warning_message"],
        "limitations": "Slicer prediction only; no physical print. Deposited support excludes prime-tower/waste, "
                      "startup custom G-code before explicit extrusion-mode initialization, and extrusion-only "
                      "pressure recovery. The generated startup G-code is not approved for printing. "
                      "Global presets and printer were not modified.",
    }
    if (out / "placement.json").exists():
        report["placement"] = json.loads((out / "placement.json").read_text())
    (out / "support_metrics.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brep", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--analyse-only", action="store_true")
    parser.add_argument("--orientation", choices=("back", "rear-corner", "inlet-face"), default="back")
    parser.add_argument("--no-support-bridges", action="store_true")
    parser.add_argument("--abs-interface", action="store_true",
                        help="single-material supports: ABS interface with a 0.2 mm top gap, no breakaway filament")
    args = parser.parse_args()
    out = args.output
    if args.analyse_only:
        print(json.dumps(analyse_saved(out, args.brep), indent=2))
        return
    if out.exists():
        raise ValueError(f"Refusing to overwrite an existing slicing run: {out}")
    out.mkdir(parents=True)
    source = S / "bs_r43"
    machine = out / "machine.json"
    shutil.copyfile(source / "machine.json", machine)
    process = json.loads((source / "process.json").read_text())
    process.update({"support_type": "tree(auto)", "support_on_build_plate_only": "0",
                    "support_remove_small_overhang": "0", "support_interface_filament": "5",
                    "wipe_tower_x": ["165"], "wipe_tower_y": ["250"]})
    if args.no_support_bridges:
        process["bridge_no_support"] = "1"
    if args.abs_interface:
        process.update({"support_interface_filament": "0", "support_top_z_distance": "0.2",
                        "support_interface_spacing": "0.5"})
    process_path = out / "process.json"
    process_path.write_text(json.dumps(process, indent=2))
    filaments = []
    for i in range(1, 9):
        destination = out / f"filament{i}.json"
        shutil.copyfile(source / f"filament{i}.json", destination)
        filaments.append(destination)
    first = json.loads(filaments[0].read_text())
    interface = json.loads(filaments[4].read_text())
    assert first["name"] == "Generic ABS @BBL H2D"
    assert interface["name"] == "Bambu Support for ABS @BBL H2D"
    diameter = float(first["filament_diameter"][0])
    assert all(float(json.loads(p.read_text())["filament_diameter"][0]) == diameter for p in filaments)
    original = cq.Shape.importBrep(str(args.brep))
    transform = np.eye(4)
    if args.orientation == "back":
        part = print_oriented(original)
        transform[:3, :3] = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
        rotated = original.rotate((0, 0, 0), (1, 0, 0), 90).BoundingBox()
        transform[:3, 3] = [-(rotated.xmin + rotated.xmax)/2,
                            -(rotated.ymin + rotated.ymax)/2, -rotated.zmin]
    elif args.orientation == "rear-corner":
        angle = math.atan2(-.6877446479107829, .7259526839058268)
        c, s = math.cos(angle), math.sin(angle)
        transform[:3, :3] = [[c, -s, 0], [0, 0, -1], [s, c, 0]]
        part = original.rotate((0, 0, 0), (0, 0, 1), math.degrees(angle))
        part = part.rotate((0, 0, 0), (1, 0, 0), 90)
    else:
        transform[:3, :3] = [[1, 0, 0], [0, -1, 0], [0, 0, -1]]
        part = original.rotate((0, 0, 0), (1, 0, 0), 180)
    stl = out / "model_print_oriented.stl"
    cq.exporters.export(part, str(stl), tolerance=.025, angularTolerance=.08)
    mesh = trimesh.load_mesh(str(stl))
    low, high = mesh.bounds
    shift = np.array([175 - (low[0] + high[0])/2, 160 - (low[1] + high[1])/2, -low[2]])
    mesh.apply_translation(shift)
    transform[:3, 3] += shift
    assert mesh.is_watertight
    on_bed = (mesh.face_normals[:, 2] < -.999) & (mesh.triangles_center[:, 2] < .02)
    contact = float(mesh.area_faces[on_bed].sum())
    if contact < 50:
        raise ValueError(f"Insufficient flat bed contact for this orientation screen: {contact} mm2")
    mesh.export(str(stl))
    (out / "placement.json").write_text(json.dumps({
        "orientation": args.orientation, "assembly_to_print": transform.tolist(),
        "bed_contact_mm2": contact, "print_bounds_mm": mesh.bounds.tolist(),
        "note": "Geometric plate contact only; brim and warpage need physical validation.",
    }, indent=2) + "\n")
    cmd = [r"C:\Program Files\Bambu Studio\bambu-studio.exe",
           "--debug", "2", "--orient", "0", "--arrange", "0", "--allow-mix-temp",
           "--curr-bed-type", "Textured PEI Plate", "--load-settings", f"{machine};{process_path}",
           "--load-filaments", ";".join(str(p) for p in filaments), "--slice", "0",
           "--outputdir", str(out), "--export-3mf", "sliced.3mf", str(stl)]
    print("Slicing", args.brep, flush=True)
    run = subprocess.run(cmd, capture_output=True, timeout=1200)
    (out / "cli.stdout.log").write_bytes(run.stdout)
    (out / "cli.stderr.log").write_bytes(run.stderr)
    result = json.loads((out / "result.json").read_text()) if (out / "result.json").exists() else None
    if run.returncode or not result or result["return_code"]:
        raise RuntimeError(f"Slicer failed: exit {run.returncode}, result {result}")
    print(json.dumps(analyse_saved(out, args.brep), indent=2), flush=True)


if __name__ == "__main__":
    main()
