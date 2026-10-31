"""Screen sampled support deposition against the narrow rear-air passage in assembly coordinates."""
import argparse
import json
import math
import re
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
import r43_swept_feed as R


def mesh(shape):
    v, f = shape.tessellate(.015, .08)
    return trimesh.Trimesh([p.toTuple() for p in v], f, process=True)


def support_segments(gcode):
    feature, relative = None, None
    x = y = e = height = 0.
    for line in gcode.splitlines():
        if line.startswith("; FEATURE:"):
            feature = line.split(":", 1)[1].strip()
        elif line.startswith("; Z_HEIGHT:"):
            height = float(line.split(":", 1)[1])
        code = line.split(";", 1)[0].strip()
        if not code:
            continue
        command = code.split()[0]
        if command in ("M82", "M83"):
            relative = command == "M83"
            continue
        v = {k: float(a) for k, a in re.findall(r"\b([XYEIJRZ])(-?(?:\d+(?:\.\d*)?|\.\d+))", code)}
        if command == "G92":
            x, y, e = v.get("X", x), v.get("Y", y), v.get("E", e)
            continue
        if command not in ("G0", "G1", "G2", "G3"):
            continue
        nx, ny = v.get("X", x), v.get("Y", y)
        if "E" in v:
            delta = v["E"] if relative else v["E"] - e
            if (feature and feature.startswith("Support") and delta > 0
                    and ((nx, ny) != (x, y) or command in ("G2", "G3"))):
                if relative is None:
                    raise ValueError("Unknown extrusion mode in support toolpath")
                if command in ("G2", "G3"):
                    if "R" in v or "Z" in v or not ("I" in v or "J" in v):
                        raise ValueError(f"Unsupported support arc representation: {code}")
                    centre = np.array([x + v.get("I", 0), y + v.get("J", 0)])
                    a = np.array([x, y]) - centre
                    b = np.array([nx, ny]) - centre
                    radius = np.linalg.norm(a)
                    if radius <= 0 or abs(np.linalg.norm(b) - radius) > .05:
                        raise ValueError(f"Inconsistent support arc radii: {code}")
                    start_angle, end_angle = math.atan2(a[1], a[0]), math.atan2(b[1], b[0])
                    sweep = ((end_angle-start_angle) % (2*math.pi) if command == "G3"
                             else -((start_angle-end_angle) % (2*math.pi)))
                    if abs(sweep) < 1e-10:
                        sweep = 2*math.pi if command == "G3" else -2*math.pi
                    count = max(1, int(math.ceil(abs(sweep)*radius/.25)))
                    angles = np.linspace(start_angle, start_angle+sweep, count+1)
                    points = np.column_stack((centre[0]+radius*np.cos(angles),
                                              centre[1]+radius*np.sin(angles),
                                              np.full(count+1, height-.1)))
                    points[0, :2], points[-1, :2] = [x, y], [nx, ny]
                    for start, end in zip(points[:-1], points[1:]):
                        yield start, end, delta/count
                else:
                    yield np.array([x, y, height-.1]), np.array([nx, ny, height-.1]), delta
            e = e + v["E"] if relative else v["E"]
        x, y = nx, ny


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tags", nargs="+", default=[
        "c28_baseline_auto", "c28_dfm_auto", "c28_dfm_rear_corner_v2",
        "c28_baseline_bridges", "c28_dfm_bridges"])
    parser.add_argument("--report", type=Path, default=CAD / "verification_swept_support_access_r43.json")
    args = parser.parse_args()
    passage = R.air(3, .9, 28).cut(R.main_channel_air()).intersect(R.mouth_keep(28))
    target = mesh(passage)
    assert target.is_watertight
    low, high = target.bounds
    reports = {}
    for tag in args.tags:
        folder = S / "printability_swept" / tag
        metrics = json.loads((folder / "support_metrics.json").read_text())
        placed = trimesh.load_mesh(str(folder / "model_print_oriented.stl"))
        if (folder / "placement.json").exists():
            transform = np.array(json.loads((folder / "placement.json").read_text())["assembly_to_print"])
            method = "Recorded placement matrix"
        else:
            original = mesh(cq.Shape.importBrep(metrics["input_brep"]))
            rotation = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])
            vertices = original.vertices @ rotation.T
            shift = placed.bounds.mean(axis=0) - (vertices.min(axis=0) + vertices.max(axis=0)) / 2
            transformed = trimesh.Trimesh(vertices + shift, original.faces, process=False)
            points = placed.vertices[::max(1, len(placed.vertices)//500)]
            _, distances, _ = transformed.nearest.on_surface(points)
            assert distances.max() < .05, float(distances.max())
            transform = np.eye(4)
            transform[:3, :3], transform[:3, 3] = rotation, shift
            method = f"Known back-face transform reconstructed and surface-checked; max error {distances.max():.6f} mm"
        with zipfile.ZipFile(folder / "sliced.3mf") as archive:
            code = archive.read(next(n for n in archive.namelist() if n.endswith(".gcode"))).decode()
        candidates, weights = [], []
        samples = 0
        for start, end, extrusion in support_segments(code):
            count = max(1, int(math.ceil(np.linalg.norm(end-start)/.5)))
            points = start + ((np.arange(count)+.5)/count)[:, None]*(end-start)
            assembly = (points-transform[:3, 3]) @ transform[:3, :3]
            take = np.all((assembly >= low) & (assembly <= high), axis=1)
            candidates.extend(assembly[take])
            weights.extend([extrusion * math.pi * 1.75**2 / 4 / count] * int(take.sum()))
            samples += count
        points = np.asarray(candidates).reshape(-1, 3)
        inside = target.contains(points) if len(points) else np.zeros(0, bool)
        hit = points[inside]
        if len(hit):
            witnesses = hit[::max(1, len(hit)//20)][:20]
            confirmed = [p.tolist() for p in witnesses
                         if any(s.isInside(cq.Vector(*p), 1e-6) for s in passage.Solids())]
            if not confirmed:
                raise ValueError(f"{tag}: mesh hits not confirmed by exact CAD")
        else:
            confirmed = []
        reports[tag] = {
            "coordinate_method": method, "sample_spacing_mm": .5,
            "total_support_samples": samples, "within_passage_bounds": len(points),
            "narrow_rear_passage_samples": int(inside.sum()),
            "estimated_support_in_passage_mm3": float(np.asarray(weights)[inside].sum()),
            "exact_cad_witnesses_mm": confirmed,
            "scope": "Dedicated rear passage only, excluding the main channels and open outlet extension.",
            "limitation": "Sampled deposition centerlines at layer mid-height, not bead-solid collision or "
                          "physical removability proof. Nonzero deposition here is a trapped-support warning.",
        }
        print(tag, json.dumps(reports[tag]), flush=True)
    args.report.write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
