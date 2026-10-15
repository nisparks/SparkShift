"""Build a non-printing, smooth cam guide from the frozen physical cam."""

import json
import math
from pathlib import Path

import numpy as np
from scipy.interpolate import BSpline, CubicSpline, make_interp_spline
from scipy.ndimage import gaussian_filter1d
from shapely.geometry import Point, Polygon


OUT = Path(__file__).resolve().parent / "sparkshift_swingarm_motion_v13"


def rotate(point, angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array((c * point[0] + s * point[1],
                     -s * point[0] + c * point[1]))


def radial_distances(points, centre, angles):
    starts = points[:-1] - centre
    edges = np.diff(points, axis=0)
    result = []
    for angle in angles:
        direction = np.array((math.cos(angle), math.sin(angle)))
        den = direction[0] * edges[:, 1] - direction[1] * edges[:, 0]
        valid = np.abs(den) > 1e-12
        radius = np.full(len(edges), -math.inf)
        along = np.full(len(edges), -math.inf)
        radius[valid] = (
            starts[valid, 0] * edges[valid, 1]
            - starts[valid, 1] * edges[valid, 0]
        ) / den[valid]
        along[valid] = (
            starts[valid, 0] * direction[1]
            - starts[valid, 1] * direction[0]
        ) / den[valid]
        hits = radius[(radius > 0) & (along >= -1e-9) & (along <= 1 + 1e-9)]
        if not len(hits):
            raise RuntimeError("A frozen cam profile ray did not hit the outline")
        result.append(float(hits.max()))
    return np.array(result)


def curve_point(curve, parameter):
    if curve["kind"] == "arc":
        angle = curve["start_angle_rad"] + parameter * (
            curve["end_angle_rad"] - curve["start_angle_rad"])
        return np.array(curve["centre_xz_mm"]) + curve["radius_mm"] * np.array(
            (math.cos(angle), math.sin(angle)))
    degree = curve["degree"]
    lo, hi = curve["knots"][degree], curve["knots"][-degree-1]
    return BSpline(curve["knots"], curve["controls_xz_mm"], degree)(
        lo + parameter * (hi - lo))


def main():
    source = json.loads((OUT / "frozen_cam_profile.json").read_text())
    points = np.array(source["outline_xz_mm"], dtype=float)
    centre = np.array(source["cam_centre_xz_mm"])
    pivot = np.array(source["pivot_xz_mm"])
    follower = np.array(source["follower_xz_mm"])
    radius = source["follower_radius_mm"]
    physical = Polygon(points)
    if not physical.is_valid or not physical.contains(Point(centre)):
        raise RuntimeError("The frozen physical cam outline is not valid")

    base_radius = float(np.linalg.norm(follower - centre) - radius)
    start = math.atan2(*(follower - centre)[::-1]) - math.radians(10)
    count = 1440
    angles = start + np.arange(count) * 2 * math.pi / count
    raw = np.maximum(radial_distances(points, centre, angles), base_radius)
    smooth = gaussian_filter1d(raw, sigma=2, mode="wrap", truncate=4)
    margin = .008
    activation = np.clip((smooth - base_radius) / .05, 0, 1)
    activation = activation * activation * (3 - 2 * activation)
    guide_radius = smooth + margin * activation
    guide_radius[np.abs(smooth - base_radius) < 1e-11] = base_radius
    spline = CubicSpline(
        np.r_[angles, start + 2 * math.pi],
        np.r_[guide_radius, guide_radius[0]],
        bc_type="periodic",
    )

    nodes = start + np.arange(361) * math.pi / 180
    values = spline(nodes)
    slopes = spline(nodes, 1)
    for i, angle in enumerate(nodes):
        sample = np.mod(
            angle + np.linspace(-math.pi / 180, math.pi / 180, 9) - start,
            2 * math.pi) + start
        if np.max(np.abs(spline(sample) - base_radius)) < 1e-10:
            values[i], slopes[i] = base_radius, 0.

    positions = centre + values[:, None] * np.column_stack(
        (np.cos(nodes), np.sin(nodes)))
    tangents = np.column_stack((
        slopes * np.cos(nodes) - values * np.sin(nodes),
        slopes * np.sin(nodes) + values * np.cos(nodes),
    ))
    curves = []
    h = math.pi / 180
    for i in range(360):
        middle = float(spline((nodes[i] + nodes[i + 1]) / 2))
        is_arc = (values[i] == base_radius == values[i + 1]
                  and slopes[i] == slopes[i + 1] == 0
                  and abs(middle - base_radius) < 1e-10)
        if is_arc:
            if curves and curves[-1]["kind"] == "arc":
                curves[-1]["end_angle_rad"] = float(nodes[i + 1])
            else:
                curves.append({
                    "kind": "arc", "centre_xz_mm": centre.tolist(),
                    "radius_mm": base_radius,
                    "start_angle_rad": float(nodes[i]),
                    "end_angle_rad": float(nodes[i + 1]),
                })
            continue
        controls = [positions[i], positions[i] + h * tangents[i] / 3,
                    positions[i + 1] - h * tangents[i + 1] / 3, positions[i + 1]]
        if curves and curves[-1]["kind"] == "spline":
            curves[-1]["controls_xz_mm"].extend(p.tolist() for p in controls[1:])
        else:
            curves.append({"kind": "spline",
                           "controls_xz_mm": [p.tolist() for p in controls]})

    outline = []
    for curve in curves:
        if curve["kind"] == "spline":
            controls = np.array(curve["controls_xz_mm"])
            data = controls[::3]
            spans = len(data) - 1
            fit = make_interp_spline(
                np.arange(spans + 1, dtype=float), data, k=5,
                bc_type=(
                    [(1, 3 * (controls[1] - controls[0])),
                     (2, -h * h * (data[0] - centre))],
                    [(1, 3 * (controls[-1] - controls[-2])),
                     (2, -h * h * (data[-1] - centre))],
                ),
            )
            curve["degree"] = 5
            curve["controls_xz_mm"] = fit.c.tolist()
            curve["knots"] = fit.t.tolist()
            curve["source_span_count"] = spans
            samples = spans * 16
        else:
            samples = math.ceil(
                (curve["end_angle_rad"] - curve["start_angle_rad"])
                * 180 / math.pi * 16)
        outline.extend(curve_point(curve, t) for t in np.linspace(
            0, 1, samples + 1)[:-1])
    guide = Polygon(outline)
    if not guide.is_valid or not guide.contains(Point(centre)):
        raise RuntimeError("The smooth non-printing guide is not a valid outline")
    periodic_points = np.asarray(outline[::8])
    periodic_points = np.vstack((periodic_points, periodic_points[0]))
    continuous = make_interp_spline(
        np.arange(len(periodic_points), dtype=float), periodic_points,
        k=5, bc_type="periodic")
    continuous_outline = continuous(np.linspace(
        0., len(periodic_points)-1, len(outline)+1))
    continuous_polygon = Polygon(continuous_outline)
    continuous_error = guide.hausdorff_distance(continuous_polygon)
    if not continuous_polygon.is_valid or continuous_error > .00005:
        raise RuntimeError("The single-face reference curve changed the reviewed guide")

    def gap(polygon, phi, theta):
        world = pivot + rotate(follower - pivot, math.radians(theta))
        local = centre + rotate(world - centre, -math.radians(phi))
        point = Point(local)
        distance = polygon.boundary.distance(point)
        return (-distance if polygon.contains(point) else distance) - radius

    def pose(polygon, phi):
        if gap(polygon, phi, 0) >= -1e-10:
            return 0.
        lo, hi = float(source.get("arm_range_deg", [-7., .3])[0]), 0.
        if gap(polygon, phi, lo) < 0:
            raise RuntimeError("The cam guide exceeds the approved arm travel")
        for _ in range(42):
            mid = (lo + hi) / 2
            if gap(polygon, phi, mid) >= 0:
                lo = mid
            else:
                hi = mid
        return lo

    poses = []
    minimum, maximum = source.get("cam_range_deg", [0., 155.])
    for phi in np.arange(float(minimum), float(maximum)+.0001, .25):
        ideal, guided = pose(physical, phi), pose(guide, phi)
        poses.append({"cam_deg": float(phi), "physical_contact_arm_deg": ideal,
                      "guided_arm_deg": guided,
                      "physical_clearance_mm": gap(physical, phi, guided),
                      "arm_error_deg": guided - ideal})
    max_error = max(abs(p["arm_error_deg"]) for p in poses)
    minimum_gap = min(p["physical_clearance_mm"] for p in poses)
    if max_error > .03 or minimum_gap < -.0001:
        raise RuntimeError(
            f"Non-printing guide fit failed: error={max_error}, gap={minimum_gap}")
    result = {
        "source_sha256": source["source_sha256"],
        "purpose": "NON-PRINTING animation reference, not a replacement physical cam",
        "curves": curves, "base_radius_mm": base_radius,
        "source_follower_radius_mm": radius,
        "radial_margin_mm": margin,
        "radial_smoothing_deviation_mm": float(np.abs(raw - smooth).max()),
        "single_face_reference_curve": {
            "kind": "spline", "degree": 5,
            "controls_xz_mm": continuous.c.tolist(), "knots": continuous.t.tolist(),
            "maximum_sampled_outline_deviation_mm": continuous_error},
        "sampled_motion": poses,
        "validation": {
            "sample_count": len(poses), "cam_step_deg": .25,
            "maximum_arm_error_deg": max_error,
            "minimum_physical_clearance_mm": minimum_gap,
            "maximum_guide_opening_deg": -min(p["guided_arm_deg"] for p in poses),
            "closed_pose_unchanged": poses[0]["guided_arm_deg"] == 0,
            "spring_force_simulated": False,
        },
    }
    destination = OUT / "motion_guide_profile.json"
    destination.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"file": str(destination), "curve_count": len(curves),
                      "validation": result["validation"]}, indent=2))


if __name__ == "__main__":
    main()
