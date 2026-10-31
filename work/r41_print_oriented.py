"""Print-oriented STLs of the CPAP parts (P20 standing, P21 top face down, P22 on its back face), finely tessellated,
with a mesh check: watertight, one body, volume, and how smooth the curved surfaces are (the angle between
neighbouring facets that are not on a modelled edge)."""
import json
import math
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402

import r41_parts as R  # noqa: E402
from build_modular_toolhead import load  # noqa: E402

STL = REPO / "stl"
TMP = Path(__file__).resolve().parent
TOL, ANG = 0.005, 0.05                    # mm chord error, radians per facet (2.9 deg)
FEATURE_DEG = 20.0                        # facet pairs bent more than this are modelled edges, not curvature
# rotations about the origin that put each candidate face on the bed (rotation axis, degrees)
CANDIDATES = {"back face down (-Y)": ((1, 0, 0), 90), "front down (+Y)": ((1, 0, 0), -90),
              "top down (+Z)": ((1, 0, 0), 180), "bottom down (-Z)": ((1, 0, 0), 0),
              "left side down (-X)": ((0, 1, 0), -90), "right side down (+X)": ((0, 1, 0), 90)}
CHOSEN = {"p20": "bottom down (-Z)", "p21": "top down (+Z)", "p22": "back face down (-Y)"}


def oriented(shape, axis, deg):
    s = shape.rotate(cq.Vector(0, 0, 0), cq.Vector(*axis), deg) if deg else shape
    bb = s.BoundingBox()
    return s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def mesh_of(shape, path, tol=TOL, ang=ANG):
    cq.exporters.export(shape, str(path), tolerance=tol, angularTolerance=ang)
    return trimesh.load_mesh(str(path))


def stats(m):
    n, area = m.face_normals, m.area_faces
    z = m.triangles_center[:, 2]
    bed = (n[:, 2] < -0.999) & (z < 0.01)
    down = (n[:, 2] < -math.cos(math.radians(45))) & ~bed     # needs support at a 45 degree limit
    ext = m.extents
    return {"bed_contact_mm2": round(float(area[bed].sum()), 1), "overhang_mm2": round(float(area[down].sum()), 1),
            "footprint_mm": [round(float(ext[0]), 1), round(float(ext[1]), 1)], "height_mm": round(float(ext[2]), 1)}


def smoothness(m):
    """Facet-to-facet bend across every mesh edge that is not a modelled edge: how faceted the curves look."""
    ang = np.degrees(m.face_adjacency_angles)
    smooth = ang[ang < FEATURE_DEG]
    return {"triangles": int(len(m.faces)), "smallest_triangle_mm2": float(m.area_faces.min()),
            "degenerate_triangles": int((m.area_faces < 1e-10).sum()),
            "max_bend_on_curves_deg": round(float(smooth.max()), 2) if len(smooth) else 0.0,
            "p99_bend_on_curves_deg": round(float(np.percentile(smooth, 99)), 2) if len(smooth) else 0.0}


def main():
    parts = {"p20": R.p20(), "p21": R.p21(), "p22": R.p22()}
    report = {}
    for key, shape in parts.items():
        rows = {}
        for label, (axis, deg) in CANDIDATES.items():
            m = mesh_of(oriented(shape, axis, deg), TMP / f"_orient_{key}.stl", 0.03, 0.1)
            rows[label] = stats(m)
        (TMP / f"_orient_{key}.stl").unlink()
        axis, deg = CANDIDATES[CHOSEN[key]]
        final = oriented(shape, axis, deg)
        out = STL / f"{R.NAMES[key]}_PRINT_ORIENTED.stl"
        coarse = smoothness(mesh_of(final, TMP / f"_coarse_{key}.stl", 0.03, 0.1))
        (TMP / f"_coarse_{key}.stl").unlink()
        m = mesh_of(final, out)
        ok = m.is_watertight and m.is_winding_consistent and len(m.split(only_watertight=False)) == 1
        if not ok or abs(final.Volume() - shape.Volume()) > 1e-3 or abs(m.bounds[0][2]) > 1e-6 \
                or abs(float(m.volume) - shape.Volume()) > 5e-4 * shape.Volume():
            raise ValueError(f"{key}: print-oriented export check failed")
        report[key] = {"file": str(out.relative_to(REPO)), "orientation": CHOSEN[key], "volume_mm3": round(shape.Volume(), 2),
                       "mesh_volume_mm3": round(float(m.volume), 2), "watertight": ok, "mb": round(out.stat().st_size / 1e6, 2),
                       "smoothness": smoothness(m), "smoothness_previous_export": coarse, "chosen": stats(m),
                       "all_candidates": rows}
        print(key, json.dumps({k: report[key][k] for k in ("volume_mm3", "mesh_volume_mm3", "watertight", "mb",
                                                            "smoothness", "smoothness_previous_export")}), flush=True)
    (TMP / "r41_print_oriented.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
