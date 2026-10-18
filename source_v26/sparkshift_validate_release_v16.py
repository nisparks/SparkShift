"""Validate source-bound raw print exports without repairing their meshes."""

import hashlib
import json
from pathlib import Path
import struct

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components


OUT = Path(__file__).resolve().parent / "sparkshift_release_v16"
TRIANGLE = np.dtype([("normal", "<f4", (3,)), ("points", "<f4", (3, 3)), ("attr", "<u2")])


def check(path, expected):
    data = path.read_bytes()
    count = struct.unpack_from("<I", data, 80)[0]
    if len(data) != 84+50*count or not count:
        raise RuntimeError("Invalid raw binary STL: "+path.name)
    triangles = np.frombuffer(data, dtype=TRIANGLE, offset=84, count=count)
    points = triangles["points"].astype(np.float64)
    normals = triangles["normal"].astype(np.float64)
    if not np.isfinite(points).all() or not np.isfinite(normals).all():
        raise RuntimeError("Non-finite native mesh data: "+path.name)
    cross = np.cross(points[:, 1]-points[:, 0], points[:, 2]-points[:, 0])
    area2 = np.linalg.norm(cross, axis=1)
    degenerate = int(np.count_nonzero(area2 <= 1e-12))
    normal_lengths = np.linalg.norm(normals, axis=1)
    bad_normals = int(np.count_nonzero(
        (normal_lengths < .99) | (normal_lengths > 1.01)
        | (np.einsum("ij,ij->i", normals, cross) < .99*normal_lengths*area2)))
    tiny_zero_normals = int(np.count_nonzero(
        (normal_lengths == 0) & (area2 > 1e-12) & (area2 <= 1e-8)))
    unacceptable_normals = bad_normals-tiny_zero_normals
    vertices, ids = np.unique(triangles["points"].reshape(-1, 3), axis=0, return_inverse=True)
    ids = ids.reshape(-1, 3)
    directed = np.concatenate((ids[:, [0, 1]], ids[:, [1, 2]], ids[:, [2, 0]]))
    edges, inverse, edge_counts = np.unique(
        np.sort(directed, axis=1), axis=0, return_inverse=True, return_counts=True)
    balance = np.bincount(inverse, weights=np.where(directed[:, 0] < directed[:, 1], 1., -1.))
    edge_errors = int(np.count_nonzero(edge_counts != 2))
    winding_errors = int(np.count_nonzero(balance))
    graph = coo_matrix((np.ones(len(edges)), (edges[:, 0], edges[:, 1])),
                       shape=(len(vertices), len(vertices))).tocsr()
    components = connected_components(graph, directed=False, return_labels=False)
    signed_volume = float(np.einsum(
        "ij,ij->i", points[:, 0], np.cross(points[:, 1], points[:, 2])).sum()/6)
    native_volume = expected["native_volume_mm3"]
    relative_volume_error = abs(signed_volume-native_volume)/native_volume
    bounds = [vertices.min(axis=0).astype(float).tolist(), vertices.max(axis=0).astype(float).tolist()]
    bed_error = abs(bounds[0][2])
    negative_xy = max(0., -bounds[0][0], -bounds[0][1])
    report = {
        "path": str(path), "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data),
        "triangles": count, "closed_components": int(components),
        "nonmanifold_edges": edge_errors, "winding_errors": winding_errors,
        "degenerate_triangles": degenerate, "stored_normal_errors": bad_normals,
        "tiny_zero_stored_normals_retained_as_metadata_warnings": tiny_zero_normals,
        "unacceptable_stored_normals": unacceptable_normals,
        "signed_mesh_volume_mm3": signed_volume, "native_volume_mm3": native_volume,
        "relative_volume_error": relative_volume_error, "bounds_mm": bounds,
        "maximum_bed_origin_error_mm": bed_error,
        "negative_xy_extent_mm": negative_xy,
        "mesh_repair_or_facet_deletion_called": False,
    }
    valid = (not any((degenerate, unacceptable_normals, edge_errors, winding_errors))
             and components == 1 and signed_volume > 0
             and relative_volume_error <= .005 and bed_error <= .001 and negative_xy <= .001)
    report["passed"] = bool(valid)
    return report


def main():
    exports = json.loads((OUT / "mesh_export_receipt.json").read_text())
    rows = []
    for part, expected in exports.items():
        row = check(Path(expected["path"]), expected)
        row["part"] = part
        rows.append(row)
        (OUT / "diagnostics" / "raw_mesh_validation.json").write_text(
            json.dumps({"parts": rows}, indent=2)+"\n")
    if len(rows) != 17:
        raise RuntimeError("The matched print set must contain all 17 roles")
    failures = [row for row in rows if not row["passed"]]
    if failures:
        print(json.dumps({"failed_parts": failures}, indent=2))
        raise RuntimeError("Raw source-bound STL failed: "+", ".join(r["part"] for r in failures))
    print(json.dumps({
        "validated_meshes": len(rows), "native_facets": sum(r["triangles"] for r in rows),
        "all_closed_oriented_single_solids": True,
        "maximum_relative_volume_error": max(r["relative_volume_error"] for r in rows),
        "maximum_bed_origin_error_mm": max(r["maximum_bed_origin_error_mm"] for r in rows),
        "tiny_native_normal_metadata_warnings":
            sum(r["tiny_zero_stored_normals_retained_as_metadata_warnings"] for r in rows),
        "no_mesh_repair_or_facet_deletion": True,
    }, indent=2))


if __name__ == "__main__":
    main()
