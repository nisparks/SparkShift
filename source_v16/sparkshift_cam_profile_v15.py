"""Derive a smooth oscillating-roller cam, rather than rescale its animation."""

import json
import math
from pathlib import Path

import numpy as np
from numpy.polynomial import Polynomial
from scipy.interpolate import make_interp_spline
from shapely.geometry import Point, Polygon
from shapely.ops import nearest_points


OUT = Path(__file__).resolve().parent / "sparkshift_cam_v15"


def rotate(point, angle):
    c, s = math.cos(angle), math.sin(angle)
    return np.array((c*point[0]+s*point[1], -s*point[0]+c*point[1]))


def ease(value, ramp=.30):
    value = min(1., max(0., value))
    factor = 1/(1-ramp)
    if value < ramp:
        u = value/ramp
        return (factor*ramp*(2.5*u**4-3*u**5+u**6),
                factor*(10*u**3-15*u**4+6*u**5))
    if value > 1-ramp:
        position, speed = ease(1-value, ramp)
        return 1-position, speed
    return factor*(value-ramp/2), factor


def progressive_ease(launch, finish=.20):
    t = Polynomial((0., 1.))
    one = Polynomial((1.,))

    def smooth(u):
        return 10*u**3-15*u**4+6*u**5

    early = (one-t)*smooth(t/launch)
    middle = one-t
    late = (one-t)*smooth((one-t)/finish)
    integrals = [curve.integ() for curve in (early, middle, late)]
    early_area = integrals[0](launch)-integrals[0](0.)
    middle_area = integrals[1](1-finish)-integrals[1](launch)
    late_area = integrals[2](1.)-integrals[2](1-finish)
    area = early_area+middle_area+late_area

    def value(x):
        if x <= 0:
            return 0., 0.
        if x >= 1:
            return 1., 0.
        if x < launch:
            position, speed = integrals[0](x)-integrals[0](0.), early(x)
        elif x <= 1-finish:
            position = early_area+integrals[1](x)-integrals[1](launch)
            speed = middle(x)
        else:
            position = early_area+middle_area+integrals[2](x)-integrals[2](1-finish)
            speed = late(x)
        return position/area, max(0., speed/area)
    return value


def main():
    source = json.loads((OUT / "physical_opening_design_input.json").read_text())
    centre = np.array(source["cam_centre_xz_mm"])
    pivot = np.array(source["pivot_xz_mm"])
    follower = np.array(source["follower_xz_mm"])
    moving = np.array(source["moving_hob_xz_mm"])
    fixed = np.array(source["fixed_hob_xz_mm"])
    radius = source["follower_radius_mm"]
    original = Polygon(source["outline_xz_mm"])
    if not original.is_valid:
        raise RuntimeError("The frozen physical cam outline is invalid")

    def rim(theta):
        position = pivot+rotate(moving-pivot, math.radians(theta))
        return np.linalg.norm(position-fixed)-2*source["hob_rim_radius_mm"]

    def gap(polygon, phi, theta):
        position = pivot+rotate(follower-pivot, math.radians(theta))
        local = centre+rotate(position-centre, -math.radians(phi))
        point = Point(local)
        distance = polygon.boundary.distance(point)
        return (-distance if polygon.contains(point) else distance)-radius

    lo, hi = 0., 10.
    for _ in range(60):
        mid = (lo+hi)/2
        if rim(-mid) < 2.5:
            lo = mid
        else:
            hi = mid
    opening = (lo+hi)/2
    rest_gap = gap(original, 0., 0.)
    base_radius = np.linalg.norm(follower-centre)-radius-rest_gap
    lo, hi = 0., 1.
    for _ in range(60):
        mid = (lo+hi)/2
        world = pivot+rotate(follower-pivot, math.radians(mid))
        if np.linalg.norm(world-centre)-radius > base_radius:
            lo = mid
        else:
            hi = mid
    takeup = (lo+hi)/2

    def actual_pose(shape, phi):
        if gap(shape, phi, 0.) >= -1e-9:
            return 0.
        lo, hi = -8., 0.
        if gap(shape, phi, lo) < 0:
            raise RuntimeError("The smooth cam exceeds the retained arm clearance range")
        for _ in range(42):
            mid = (lo+hi)/2
            if gap(shape, phi, mid) >= 0:
                lo = mid
            else:
                hi = mid
        return lo

    def profile_for(law):
        def contact(phi):
            theta, speed = law(float(phi))
            lever = rotate(follower-pivot, math.radians(theta))
            relative = pivot+lever-centre
            derivative = rotate(
                np.array((lever[1], -lever[0]))*speed
                - np.array((relative[1], -relative[0])), -math.radians(phi))
            local = rotate(relative, -math.radians(phi))
            normal = np.array((derivative[1], -derivative[0]))
            normal /= np.linalg.norm(normal)
            return centre+local-radius*normal

        curves, samples, curvature_radii = [], [], []
        for start, end, kind in ((0., 170., "spline"), (170., 190., "arc"),
                                 (190., 350., "spline"), (350., 360., "arc")):
            fine = np.arange(start, end+.0001, .125)
            if kind == "spline":
                parameters = np.arange(start, end+.0001, .5)
                data = np.array([contact(phi) for phi in parameters])
                derivatives = []
                for point in (data[0], data[-1]):
                    radial = point-centre
                    derivatives.append([
                        (1, np.array((-radial[1], radial[0]))*math.pi/180),
                        (2, -radial*(math.pi/180)**2),
                    ])
                fit = make_interp_spline(parameters, data, k=5,
                                        bc_type=tuple(derivatives))
                points = fit(fine)
                first, second = fit(fine, 1), fit(fine, 2)
                cross = first[:, 0]*second[:, 1]-first[:, 1]*second[:, 0]
                curvature_radii.extend(
                    np.linalg.norm(first, axis=1)**3/np.maximum(abs(cross), 1e-15))
                curves.append({"kind": kind, "degree": 5,
                               "controls_xz_mm": fit.c.tolist(), "knots": fit.t.tolist()})
            else:
                radial = contact(start)-centre
                r = float(np.linalg.norm(radial))
                angle = math.atan2(radial[1], radial[0])
                angles = angle+np.radians(fine-start)
                points = centre+r*np.column_stack((np.cos(angles), np.sin(angles)))
                curvature_radii.append(r)
                curves.append({"kind": kind, "centre_xz_mm": centre.tolist(),
                               "radius_mm": r, "start_angle_rad": angle,
                               "end_angle_rad": angle+math.radians(end-start),
                               "full_open_dwell": start == 170})
            samples.extend(points[:-1])
        outline = np.array([*samples, samples[0]])
        return curves, outline, min(curvature_radii)

    candidates = []
    chosen = None
    for launch in (.20, .22, .24, .26, .28, .30, .32, .34):
        progressive = progressive_ease(launch)

        def law(phi):
            if phi < 170:
                position, speed = progressive(phi/170)
                return takeup-(opening+takeup)*position, -(opening+takeup)*speed/170
            if phi <= 190:
                return -opening, 0.
            if phi < 350:
                position, speed = ease((phi-190)/160)
                return -opening+(opening+takeup)*position, (opening+takeup)*speed/160
            return takeup, 0.

        curves, outline, minimum_curvature = profile_for(law)
        polygon = Polygon(outline)
        valid = polygon.is_valid and polygon.contains(Point(centre))
        reason = ("valid" if valid else "self-intersecting roller envelope")
        if valid and minimum_curvature < 2.5:
            valid, reason = False, "working-profile radius below the 2.5 mm smoothness bound"
        if valid and polygon.exterior.distance(Point(centre)) < 4.2:
            valid, reason = False, "protected journal core would be compromised"
        trial = {"launch_fraction": launch, "minimum_profile_curvature_radius_mm":
                 float(minimum_curvature), "accepted": valid, "reason": reason}
        candidates.append(trial)
        if valid:
            chosen = (launch, progressive, law, curves, outline, polygon, minimum_curvature)
            break
    (OUT / "progressive_profile_candidates.json").write_text(
        json.dumps(candidates, indent=2)+"\n")
    if chosen is None:
        raise RuntimeError("No bounded progressive profile meets the native geometry constraints")
    launch, progressive, law, curves, outline, polygon, minimum_curvature = chosen
    minimum_radius = min(polygon.exterior.distance(Point(centre)), base_radius)

    def pressure_angle(shape, phi, theta):
        world = pivot+rotate(follower-pivot, math.radians(theta))
        local = centre+rotate(world-centre, -math.radians(phi))
        on_cam = np.array(nearest_points(shape.boundary, Point(local))[0].coords[0])
        normal = rotate(local-on_cam, math.radians(phi))
        normal /= np.linalg.norm(normal)
        lever = world-pivot
        tangent = np.array((-lever[1], lever[0]))
        tangent /= np.linalg.norm(tangent)
        return math.degrees(math.acos(min(1., abs(float(np.dot(normal, tangent))))))

    rows = []
    for phi in np.arange(0., 175.0001, .25):
        desired = min(0., law(float(phi))[0])
        actual = actual_pose(polygon, float(phi))
        if abs(actual-desired) > .002:
            raise RuntimeError("The generated physical cam does not reproduce its motion law")
        rows.append({"cam_deg": float(phi), "arm_deg": actual,
                     "designed_arm_deg": desired, "rim_gap_mm": float(rim(actual)),
                     "actual_cam_roller_gap_mm": gap(polygon, float(phi), actual),
                     "pressure_angle_deg": pressure_angle(polygon, float(phi), actual)
                     if actual < -.001 else None})
    old_rows = []
    for phi in np.arange(0., 180.0001, .25):
        actual = actual_pose(original, float(phi))
        old_rows.append({"cam_deg": float(phi), "arm_deg": actual,
                         "rim_gap_mm": float(rim(actual))})
    new_speed = np.gradient([r["arm_deg"] for r in rows], .25)
    old_speed = np.gradient([r["arm_deg"] for r in old_rows], .25)
    new_rest_gap = gap(polygon, 0., 0.)
    if abs(new_rest_gap-rest_gap) > .001:
        raise RuntimeError("The new cam changed the intentional closed-position clearance")
    if min(r["rim_gap_mm"] for r in rows if r["cam_deg"] >= 170) < 2.49995:
        raise RuntimeError("The new full-open dwell loses the 2.5 mm minimum rim gap")
    if max(abs(new_speed)) >= max(abs(old_speed)):
        raise RuntimeError("The new cam does not reduce the peak opening rate")
    leverage = []
    for fraction in (.25, .50, .75, .90, .98):
        lo, hi = 0., 170.
        for _ in range(60):
            mid = (lo+hi)/2
            if -law(mid)[0]/opening < fraction:
                lo = mid
            else:
                hi = mid
        phi = (lo+hi)/2
        rate = abs(law(phi)[1])
        leverage.append({"opened_fraction": fraction, "cam_deg": phi,
                         "arm_travel_deg_per_cam_deg": rate,
                         "ideal_cam_to_arm_torque_multiplication": 1/rate})
    if any(b["arm_travel_deg_per_cam_deg"] >= a["arm_travel_deg_per_cam_deg"]
           for a, b in zip(leverage, leverage[1:])):
        raise RuntimeError("Mechanical advantage does not increase through the loaded stroke")
    peak_index = int(np.argmin(new_speed))
    report = {
        "source_sha256": source["source_sha256"],
        "cam_centre_xz_mm": centre.tolist(),
        "curves": curves, "outline_xz_mm": outline.tolist(),
        "new_cam_limit_deg": 175, "nominal_servo_limit_deg": 180,
        "upper_command_margin_deg": 5,
        "entry_takeup_deg": [0, next(r["cam_deg"] for r in rows if r["arm_deg"] < -.0001)],
        "physical_opening_rise_deg": [
            next(r["cam_deg"] for r in rows if r["arm_deg"] < -.0001), 170],
        "open_dwell_in_commanded_range_deg": [170, 175],
        "geometric_open_dwell_deg": [170, 190],
        "motion_law": "Soft launch, progressively declining lift rate, and an exact concentric open dwell",
        "selected_launch_fraction": launch,
        "mechanical_advantage_progression": leverage,
        "open_dwell_is_exact_circular_geometry": True,
        "spring_remains_loaded_at_dwell": True,
        "zero_ideal_dwell_backdrive_torque_not_zero_contact_force": True,
        "roller_radius_mm": radius, "base_radius_mm": float(base_radius),
        "virtual_closed_takeup_arm_deg": takeup,
        "target_open_arm_deg": -opening, "target_rim_gap_mm": 2.5,
        "physical_motion": rows, "previous_motion": old_rows,
        "metrics": {
            "previous_peak_arm_rate_deg_per_cam_deg": float(max(abs(old_speed))),
            "new_peak_arm_rate_deg_per_cam_deg": float(max(abs(new_speed))),
            "peak_arm_rate_reduction_percent":
                float(100*(1-max(abs(new_speed))/max(abs(old_speed)))),
            "closed_cam_clearance_before_mm": rest_gap,
            "closed_cam_clearance_after_mm": new_rest_gap,
            "new_open_dwell_min_rim_gap_mm":
                min(r["rim_gap_mm"] for r in rows if r["cam_deg"] >= 170),
            "previous_rim_gap_at_155_deg": old_rows[620]["rim_gap_mm"],
            "previous_rim_gap_at_180_deg": old_rows[-1]["rim_gap_mm"],
            "maximum_working_pressure_angle_deg":
                max(r["pressure_angle_deg"] for r in rows
                    if r["pressure_angle_deg"] is not None),
            "minimum_profile_curvature_radius_mm": float(minimum_curvature),
            "peak_rate_cam_deg": rows[peak_index]["cam_deg"],
            "opened_fraction_at_peak_rate": -rows[peak_index]["arm_deg"]/opening,
            "maximum_profile_radius_mm":
                float(np.max(np.linalg.norm(outline-centre, axis=1))),
            "minimum_profile_radius_mm": float(minimum_radius),
            "servo_actual_endpoints_and_force_not_qualified": True,
        },
    }
    (OUT / "smooth_cam_profile.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("curves", "outline_xz_mm",
                                   "physical_motion", "previous_motion")}, indent=2))


if __name__ == "__main__":
    main()
