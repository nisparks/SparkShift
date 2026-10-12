"""Validate raw Fusion tessellation and rigidly orient versioned STL files for printing."""

import argparse
import hashlib
import json
import struct
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parent / "sparkshift_ahg_min"
DTYPE = np.dtype([("normal", "<f4", (3,)), ("vertices", "<f4", (3, 3)), ("attribute", "<u2")])


def inspect(data):
    vertices = data["vertices"].astype(np.float64)
    points, index = np.unique(vertices.reshape(-1, 3), axis=0, return_inverse=True)
    triangles = index.reshape(-1, 3)
    directed = triangles[:, ((0, 1), (1, 2), (2, 0))].reshape(-1, 2)
    edges, inverse, counts = np.unique(np.sort(directed, axis=1), axis=0, return_inverse=True,
                                       return_counts=True)
    signs = np.where(directed[:, 0] < directed[:, 1], 1, -1)
    winding = np.bincount(inverse, weights=signs, minlength=len(edges))
    crosses = np.cross(vertices[:, 1] - vertices[:, 0], vertices[:, 2] - vertices[:, 0])
    area2 = np.linalg.norm(crosses, axis=1)
    volume = np.einsum("ij,ij->", vertices[:, 0], np.cross(vertices[:, 1], vertices[:, 2])) / 6
    parents = np.arange(len(points))

    def find(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i

    for a, b in edges:
        a, b = find(a), find(b)
        if a != b:
            parents[a] = b
    components = len({find(i) for i in range(len(points))})
    report = {
        "triangles": len(triangles),
        "connected_components": components,
        "non_manifold_edges": int(np.count_nonzero(counts != 2)),
        "inconsistent_winding_edges": int(np.count_nonzero(winding)),
        "degenerate_triangles": int(np.count_nonzero(area2 == 0)),
        "reversed_facet_normals": int(np.count_nonzero(np.einsum("ij,ij->i", crosses, data["normal"]) < 0)),
        "volume_mm3": float(volume),
        "bounds_mm": [points.min(axis=0).tolist(), points.max(axis=0).tolist()],
    }
    if (not np.isfinite(vertices).all() or components != 1 or volume <= 0 or
            any(report[k] for k in ("non_manifold_edges", "inconsistent_winding_edges",
                                   "degenerate_triangles", "reversed_facet_normals"))):
        raise RuntimeError("Native mesh failed validation: " + json.dumps(report))
    return report


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="AHG-min package directory")
    parser.add_argument("--revision", choices=("v7", "v8", "v9"), default="v7")
    parser.add_argument("--baseline", choices=("v6", "v7", "v8"), default="v6")
    args = parser.parse_args()
    ROOT = args.root.resolve()
    manifest = ROOT / (args.revision + "_mesh_export.json")
    if not manifest.exists():
        manifest = ROOT / "reports" / (args.revision + "_mesh_export.json")
    export = json.loads(manifest.read_text())
    target = ROOT / ("stl_" + args.revision)
    target.mkdir(exist_ok=True)
    report = {}
    for key, record in export.items():
        path = ROOT / ("stl_" + args.revision + "_assembly") / Path(record["path"]).name
        raw = path.read_bytes()
        count = struct.unpack_from("<I", raw, 80)[0]
        if len(raw) != 84 + count * DTYPE.itemsize:
            raise RuntimeError("Invalid binary STL size: " + path.name)
        data = np.frombuffer(raw, offset=84, count=count, dtype=DTYPE).copy()
        before = inspect(data)
        if abs(before["volume_mm3"] - record["native"]["volume_mm3"]) > max(.5, .001 * record["native"]["volume_mm3"]):
            raise RuntimeError("STL/native volume mismatch: " + key)
        build = np.array(record["build_direction"], dtype=float)
        build /= np.linalg.norm(build)
        anchor = np.array([1.,0.,0.]) if abs(build[0]) < .9 else np.array([0.,1.,0.])
        x_axis = anchor - build * np.dot(anchor,build)
        x_axis /= np.linalg.norm(x_axis)
        rotation = np.vstack((x_axis,np.cross(build,x_axis),build))
        if not np.isfinite(rotation).all() or not np.allclose(rotation @ rotation.T,np.eye(3),atol=1e-10):
            raise RuntimeError("Invalid measured print orientation: " + key)
        if not np.isclose(np.linalg.det(rotation),1.,atol=1e-10):
            raise RuntimeError("Print orientation is not a rigid rotation: " + key)
        vertices = data["vertices"].astype(float) @ rotation.T
        shift = -vertices.reshape(-1, 3).min(axis=0)
        data["vertices"] = vertices + shift
        data["normal"] = data["normal"].astype(float) @ rotation.T
        dest = target / path.name
        dest.write_bytes(raw[:84] + data.tobytes())
        reread = np.frombuffer(dest.read_bytes(), offset=84, dtype=DTYPE)
        after = inspect(reread)
        if abs(after["volume_mm3"] - before["volume_mm3"]) > .003 or min(after["bounds_mm"][0]) < -1e-6:
            raise RuntimeError("Rigid print orientation changed geometry: " + key)
        old = ROOT / ("stl_" + args.baseline + "_assembly") / path.name
        if not old.exists():
            old = ROOT / ("stl_" + args.baseline) / path.name
        report[key] = {"assembly_mesh": before, "print_mesh": after, "rotation": rotation.tolist(),
                       "translation_mm": shift.tolist(),
                       "unchanged_raw_from_" + args.baseline: old.exists() and raw == old.read_bytes(),
                       "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}
        print(key, len(data), "triangles, one closed shell,", round(after["volume_mm3"], 2), "mm3")
    (manifest.parent / (args.revision + "_stl_report.json")).write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
