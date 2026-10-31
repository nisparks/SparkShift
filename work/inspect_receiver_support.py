"""Locate sampled support deposition in the receiver socket and nearby remaining channel air."""
import argparse
import json
import math
import sys
import zipfile
from pathlib import Path

S = Path(__file__).parent
sys.path.insert(0, str(S))
from inspect_swept_support_paths import CAD, mesh, support_segments  # noqa: E402
import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402
import r43_c28_mechanical as M  # noqa: E402
import r43_swept_feed as F  # noqa: E402

FORK = S / "swept_feed" / "optC28_mechanical"
VARIANTS = {
    "c28_mechanical_back": FORK,
    "c28_user_p21_receiver_back_v1": S / "swept_feed" / "userP21_matched_v1",
    "c28_user_p21_receiver_back_v2": S / "swept_feed" / "userP21_matched_v2",
    "c28_user_p21_receiver_back_v4": S / "swept_feed" / "userP21_matched_v4",
}


def socket_for(folder):
    if folder == FORK:
        return M.cylinder(0, M.RETAINER_Y, -65.25, -48, M.TONGUE_R + M.SOCKET_CLEARANCE).fuse(*M.root_slots())
    return cq.Shape.importBrep(str(folder / "socket.brep"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    old22 = cq.Shape.importBrep(str(FORK / "p22.brep"))
    region = M.box(-12, 12, -47, -18, -68, -48)
    reports = {}
    for tag, folder in VARIANTS.items():
        p22 = cq.Shape.importBrep(str(folder / "p22.brep"))
        targets = {
            "receiver_socket": socket_for(folder).intersect(region).cut(p22),
            "remaining_channel_air_near_receiver": F.main_channel_air().cut(p22).cut(
                cq.Shape.importBrep(str(folder / "p21.brep"))).intersect(region),
        }
        run = S / "printability_swept" / tag
        transform = np.array(json.loads((run / "placement.json").read_text())["assembly_to_print"]) \
            if (run / "placement.json").exists() else None
        if transform is None:
            transform = np.eye(4)
            transform[:3, :3] = [[1, 0, 0], [0, 0, -1], [0, 1, 0]]
            placed = __import__("trimesh").load_mesh(str(run / "model_print_oriented.stl"))
            original = mesh(p22)
            vertices = original.vertices @ transform[:3, :3].T
            transform[:3, 3] = placed.bounds.mean(axis=0) - (vertices.min(axis=0) + vertices.max(axis=0)) / 2
        with zipfile.ZipFile(run / "sliced.3mf") as archive:
            code = archive.read(next(n for n in archive.namelist() if n.endswith(".gcode"))).decode()
        points, weights = [], []
        for start, end, extrusion in support_segments(code):
            count = max(1, int(math.ceil(np.linalg.norm(end - start) / .5)))
            samples = start + ((np.arange(count) + .5) / count)[:, None] * (end - start)
            assembly = (samples - transform[:3, 3]) @ transform[:3, :3]
            points.extend(assembly)
            weights.extend([extrusion * math.pi * 1.75**2 / 4 / count] * count)
        points, weights = np.asarray(points), np.asarray(weights)
        row = {}
        for name, shape in targets.items():
            target = mesh(shape)
            low, high = target.bounds
            near = np.all((points >= low) & (points <= high), axis=1)
            inside = np.zeros(len(points), bool)
            if near.any():
                inside[np.flatnonzero(near)] = target.contains(points[near])
            row[name] = {"target_volume_mm3": shape.Volume(), "samples": int(inside.sum()),
                         "support_mm3": float(weights[inside].sum())}
        reports[tag] = row
        print(tag, json.dumps(row), flush=True)
    reports["scope"] = ("Sampled support centrelines in assembly coordinates. Socket support is open to the "
                        "socket mouth; channel-air support near the receiver indicates possible trapped support.")
    args.report.write_text(json.dumps(reports, indent=2) + "\n")


if __name__ == "__main__":
    main()
