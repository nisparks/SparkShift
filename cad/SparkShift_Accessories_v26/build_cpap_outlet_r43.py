"""Revision 43: P22's jets on a lower floor, with a larger bell-mouth (parts in r43_parts.py).

Static checks:
- P22: one valid solid inside revision 41's bounds, changed only under and over its jets;
- outlet: the jets' open area against revision 41's, the floor under them solid and at least 0.8 mm thick (exact
  vertical rays and the printed mesh), their top unchanged under both hotends' heaters, the r 2.4 bell-mouth's
  profile against its design (and its run-out into the front wall against the run-out's), and every other wall of
  the outlet no thinner than revision 41's;
- hotends: every part of the Bambu hotend (silicone sock, heater cradle, wire bail, nozzle...) and the Red Lizard
  against P22, mounted and along the 60 mm withdrawal (the carriage backs away in -Y and leaves the tool in its dock),
  none closer than to revision 41's P22;
- fit: P22 against the revision-41 carriage built with the Beacon and with the Cartographer (revision 42's P23,
  probe and screws), and both mounted tools: no new interference or contact;
- print: P22 on its back face, finely meshed: the area on the plate and the area that needs support against revision
  41's, split by whether a support from the plate could reach it; P22 stood on each of its other flat faces; the
  walls at the printing changes (the window notch, the back chamfer and corners; the review's rib is reported apart).
Then, on a revision-43 scene (WORK/r43_scene), the revision-36 full-rack requalification.

Run: python build_cpap_outlet_r43.py [--workers 10] [--static-only]
"""
import argparse
import json
import math
import os
import time

import build_and_verify_accessories_v26 as acc
import build_carriage_fixes_r41 as V      # points SPARKSHIFT_SCENE at r41_scene; this revision's scene follows

os.environ["SPARKSHIFT_SCENE"] = str(acc.WORK / "r43_scene")

import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt  # noqa: E402
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector  # noqa: E402

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import build_probe_height_datum_dock_r37 as b37  # noqa: E402
import fast_geometry as fg  # noqa: E402
import r37_parts as P37  # noqa: E402
import r41_parts as R41  # noqa: E402
import r42_parts as R42  # noqa: E402
import r43_parts as R  # noqa: E402
from audit_tool_owned_2510 import compound, overlaps  # noqa: E402
from build_bambu_clean_r29 import sha  # noqa: E402
from build_carriage_lowered_mounts_r31 import confined  # noqa: E402
from build_fan_mounts_r33 import export_assembly, export_print  # noqa: E402
from build_modular_toolhead import ROOT, STL, box  # noqa: E402

REPORT = "verification_cpap_outlet_r43.json"
SIDES = ((1, 10.1, 12.95), (-1, -12.95, -10.1))
# The lowered floor under each jet, with the underside below it, 0.8 mm by design. It starts 0.6 mm behind the pocket,
# where rays from the underside's upward curve reach the pocket's back end.
POCKET_ZONES = [(x0, x1, R.LOW_Y0 - 0.6, 28.0, R.UNDER - 0.05, -75.5) for _, x0, x1 in SIDES]
# The bell-mouth band: the wall's bottom, from the foot's run-out behind the heel to the front wall, its foot and chamfer
# included, and the round's run-out into the front wall (r43_parts.with_runout_bell). Its 90 degree edge on the slot
# side reads as thin to a ray cast (as revision 41's round did), so it is measured by its profile instead.
BELL_BAND = [(min(s * (R.WALL_X[0] - 0.05), s * (R.WALL_X[0] + R.BELL_R + 0.35)),
              max(s * (R.WALL_X[0] - 0.05), s * (R.WALL_X[0] + R.BELL_R + 0.35)),
              R.BELL_BACK - 0.1, 28.0, R.ROOF - 0.05, R.ROOF + max(R.BELL_R + 1.1, R.RUNOUT_H + 0.05)) for s, _, _ in SIDES]
ZONES = POCKET_ZONES + BELL_BAND
# For printing (r43_parts.printable): the notch at the window's front, the back face's chamfer and sharp corners, and
# the review's rib with its flares into the cable boss's nose and the island's trimmed back corners
PRINT_ZONES = [(-R.WINDOW_HALF - 0.05, R.WINDOW_HALF + 0.05, R.WINDOW_FRONT - R.NOTCH_STRIP - 0.1,
                R.WINDOW_FRONT + R.WINDOW_HALF + 0.1, R.BOTTOM_Z - 0.05, -57.0),
               (-18.0, 18.0, R.BACK_Y - 0.05, -40.6, R.BOTTOM_Z - 0.05, -48.95)]
RIB_ZONE = (-R.NOSE_HALF - 0.45, R.NOSE_HALF + 0.45, R.RIB_BACK - 0.1, R.NOSE_C[1] + 0.05, -67.6, R.RIB_TOP + 0.01)
PRINT_ZONES.append(RIB_ZONE)
PRINT_WALL_ZONES = PRINT_ZONES[:1] + [PRINT_ZONES[1][:5] + (-52.0,)]   # below the socket (its walls are revision 41's)
FLOOR_MIN = 0.8                           # two 0.42 mm perimeters with P22 on its back face
BELL_PROFILE_Y = {16.9: 2.9, 17.8: 9.0, 19.0: 9.0, 22.2: 9.0, 24.4: 1.9}
# where the round is full; the heights over ROOF to check: behind Y17.5 the wall's duct face thickens outboard (so
# above the round's top the wall reads thicker than its 1.4 mm), and towards the front wall the duct's roof comes down
# (to ROOF+2.5 at Y24.4)
RUNOUT_PROFILE_Y = {R.RUNOUT_Y[0] + (R.RUNOUT_Y[1] - R.RUNOUT_Y[0]) * k / R.RUNOUT_N: top
                    for k, top in ((3, 1.4), (7, 1.0), (11, 0.7))}
# three of the run-out's lofted sections (Y25.18, 25.95, 26.72), where its surface is exactly runout_design; the roof
# is ROOF+2.05, 1.58 and 1.10 over them
BEACON_BUILD = ("Beacon_", P37.NAMES["p23"], "R37_PROBE_", "R37_REAR_")
WITHDRAWAL = (60.0, 0.5)                  # mm, step: the requalification's carriage retreat
BAMBU_PARTS = {0: "ceramic (zirconia) block", 1: "aluminium heater cradle", 2: "wire bail and latch",
               3: "hotend: nozzle, melt block, heatsink", 4: "silicone sock", 5: "retaining magnet"}
PRINT_TOL, PRINT_ANG = 0.002, 0.05        # the print-oriented STL: chord error (mm, absolute) and radians per facet,
                                          # on edges and inside faces (the run-out's lofted round needs the latter)
SUPPORT_DEG = 30.0                        # the user's Bambu preset: overhangs flatter than this get support
TEAL, ORANGE, GREY, BLUE, RED = (0.0, 0.64, 0.61), (0.95, 0.55, 0.12), (0.55, 0.57, 0.6), (0.2, 0.45, 0.9), (0.85, 0.2, 0.2)


def r3(values):
    return [round(v, 3) for v in values]


def build_parts():
    parts = V.build_parts()
    parts["p22_r41"], parts["p22"] = parts["p22"], R.p22()
    parts["cartographer"] = R42.cartographer()
    parts["p23c"], parts["carto_hardware"] = R42.p23(), R42.hardware()
    return parts


def carriage(parts):
    """The revision-41 carriage with this P22 (the Beacon build)."""
    return [(R.NAMES["p22"] if n == R41.NAMES["p22"] else n, s) for n, s in V.carriage(parts)]


def carriage_cartographer(parts):
    out = [(n, s) for n, s in carriage(parts) if not n.startswith(BEACON_BUILD)]
    return out + [(R42.NAMES["p23"], parts["p23c"]), ("Cartographer_V3_Raised", parts["cartographer"])] + \
        list(parts["carto_hardware"])


# --------------------------------------------------------------------------------------------
# Static checks
# --------------------------------------------------------------------------------------------

def check_p22(parts, report, failures):
    new, old = parts["p22"], parts["p22_r41"]
    nb, ob = V.exact_bounds(new), V.exact_bounds(old)
    c = confined(new.copy(), old.copy(), ZONES + PRINT_ZONES)
    row = {"valid": new.isValid(), "solids": len(new.Solids()), "volume_mm3": round(new.Volume(), 2),
           "r41_volume_mm3": round(old.Volume(), 2), "faces": len(new.Faces()), "r41_faces": len(old.Faces()),
           "bounds_mm": r3(nb), "r41_bounds_mm": r3(ob),
           "within_r41_bounds": all(nb[2 * i] >= ob[2 * i] - 1e-3 and nb[2 * i + 1] <= ob[2 * i + 1] + 1e-3 for i in range(3)),
           "unchanged_outside_edit_zones": c["unchanged_outside_zones"], "inside_zones_mm3": c["inside_zones_mm3"],
           "edit_zones_mm": {"jets": ZONES, "printing": PRINT_ZONES}}
    report["p22"] = row
    if not (row["valid"] and row["solids"] == 1):
        failures.append("P22 is not a single valid solid")
    if not row["within_r41_bounds"]:
        failures.append("P22 grew beyond revision 41's bounds")
    if not row["unchanged_outside_edit_zones"]:
        failures.append("P22 changed outside its edit zones")


def open_area(p22, x, side, horn, y0):
    """Open area of a plane across one jet at |X| x, inside P22's outer YZ profile (no outside air under the heel)."""
    lo, hi = sorted((side * (x - 0.01), side * (x + 0.01)))
    window = box(lo, hi, y0, 29.5, -77.10, -73.0).intersect(horn)
    return (window.Volume() - window.intersect(p22).Volume()) / 0.02


def floor_rays(p22, xs=(10.3, 11.0, 12.0, 12.8), y0=R.LOW_Y0 + 0.05, y1=27.85, step=0.05):
    """Exact thickness of the floor under each jet, by vertical rays: from the underside to the first face above it."""
    isect = IntCurvesFace_ShapeIntersector()
    isect.Load(p22.wrapped, 1e-6)
    worst, n = None, 0
    for x in xs + tuple(-v for v in xs):
        for k in range(int(round((y1 - y0) / step)) + 1):
            y = y0 + k * step
            isect.Perform(gp_Lin(gp_Pnt(x, y, -79.0), gp_Dir(0, 0, 1)), 0.0, 6.0)
            z = sorted(isect.Pnt(i).Z() for i in range(1, isect.NbPnt() + 1))
            if len(z) < 2:
                continue
            n += 1
            if worst is None or z[1] - z[0] < worst[0]:
                worst = (z[1] - z[0], x, y)
    return {"rays": n, "min_mm": round(worst[0], 4), "at_xy_mm": [round(worst[1], 2), round(worst[2], 2)]}


def bell_profile(p22, side, y, heights=(0.1, 0.2, 0.42, 0.7, 1.0, 1.4, 1.9, 2.3, 2.6, 2.9, 3.2)):
    """Thickness across X of the wall and its foot, from the slot face out, at heights over ROOF, at one Y."""
    lo, hi = sorted((side * R.WALL_X[0], side * (R.WALL_X[0] + R.BELL_R + 0.6)))
    return {f"{h:g}": round(box(lo, hi, y - 0.01, y + 0.01, R.ROOF + h - 0.01, R.ROOF + h + 0.01).intersect(p22).Volume()
                            / 4e-4, 3) for h in heights}


def bell_design(h):
    """The round (r BELL_R, centred on the slot face BELL_R over ROOF), then the 45 degree chamfer back to the wall."""
    r, wall = R.BELL_R, R.WALL_X[1] - R.WALL_X[0]
    if h < r:
        return round(math.sqrt(2 * r * h - h * h), 3)
    return round(max(wall, r - (h - r)), 3)


def runout_design(y, h):
    """r43_parts.runout_section at Y: the wall's flat bottom out to the round's tangent point, the round (r BELL_R*s),
    then the foot's 45 degree chamfer, s mm deep, back to the wall's duct face."""
    s = min(max(R.runout_s(y), 0.02), 0.995)
    r, wall = R.BELL_R * s, R.WALL_X[1] - R.WALL_X[0]
    if h < r:
        return round((1.0 - s) * wall + math.sqrt(2 * r * h - h * h), 3)
    return round(max(wall, wall + s - (h - r)), 3)


def check_outlet(parts, report, failures):
    new, old = parts["p22"], parts["p22_r41"]
    xs = (10.3, 10.6, 10.9, 11.15, 11.5)
    throat = {f"x{x}": {"r43_mm2": round(sum(open_area(new, x, s, V.HORN, 16.0) for s in (-1, 1)), 1),
                        "r41_mm2": round(sum(open_area(old, x, s, V.HORN, 16.0) for s in (-1, 1)), 1)} for x in xs}
    narrowest = {k: min(v[k] for v in throat.values()) for k in ("r43_mm2", "r41_mm2")}
    floor = [box(*sorted((s * 10.3, s * 15.0)), 22.5, 27.5, R.UNDER + 0.05, R.LOW_FLOOR - 0.05) for s in (-1, 1)]
    floor_solid = round(sum(f.intersect(new).Volume() for f in floor) / sum(f.Volume() for f in floor), 6)
    heaters = {}
    for label, v in parts["tools"].items():
        hot = compound([s for n, s in v["parts"] if "hotend" in n])
        bottom = min(V.lowest_surface_z(hot, lo, hi, R41.THROAT_Y[0], R41.THROAT_Y[1])
                     for lo, hi in ((4.0, R.WALL_X[0]), (-R.WALL_X[0], -4.0)))
        heaters[label] = {"heater_bottom_z": round(bottom, 2), "jet_top_z": R.ROOF, "jet_floor_z": R.LOW_FLOOR,
                          "margin_mm": round(bottom - R.ROOF, 2)}
    rays = floor_rays(new)
    mesh = V.to_mesh(new, "p22_r43")
    pocket = V.wall_report(mesh, POCKET_ZONES)
    others = V.JET_LIP_BAND + ZONES
    whole = V.wall_report(mesh, V.OUTLET_ALL, exclude=others)
    whole_old = V.wall_report(V.to_mesh(old, "p22_r41"), V.OUTLET_ALL, exclude=others)
    lips = {}
    for y, top in BELL_PROFILE_Y.items():
        prof = [bell_profile(new, s, y) for s in (-1, 1)]
        lips[f"y{y:g}"] = round(max(abs(val - bell_design(float(k))) for p in prof for k, val in p.items()
                                    if float(k) <= top), 4)
    for y, top in RUNOUT_PROFILE_Y.items():
        prof = [bell_profile(new, s, y) for s in (-1, 1)]
        lips[f"y{y:.2f} (run-out)"] = round(max(abs(val - runout_design(y, float(k))) for p in prof
                                                for k, val in p.items() if float(k) <= top), 4)
    report["outlet"] = {
        "jets": f"Horizontal, one each side of the nozzle as in revision 41: the slot under the duct-to-slot wall "
                f"(|X| {R.WALL_X[0]}), from the floor to the wall's flat bottom (Z{R.ROOF}, unchanged). The floor is "
                f"{R.DROP} mm lower from Y{R.LOW_Y0} forward (Z{R.LOW_FLOOR} where flat, was {R.FLOOR}; the same "
                f"{R.DROP} mm lower where it climbs the heel), out to |X| {R.LOW_X[1]}, rising at 45 degrees into the "
                f"front wall; it is still solid, so no air blows down at the bed. The wall's duct side is rounded "
                f"r {R.BELL_R} (was {R41.JET_LIP_R}) from the heel (Y{R.BELL_HEEL:.2f}) to Y{R.RUNOUT_Y[0]}, on a foot "
                f"out to |X| {R.WALL_X[0] + R.BELL_R:.1f} with a 45 degree chamfer above; from there the round and its "
                f"foot ease out together, along a cosine, to the wall's sharp corner by Y{R.RUNOUT_Y[1]}, as the "
                f"duct's roof comes down over them. Behind the heel the round runs into the heel's ramp, and the "
                f"rounded foot runs on in the duct's air until the ramp and the wall's thickening duct face take it in.",
        "open_area_both_sides": throat, "narrowest_mm2": narrowest,
        "area_ratio_vs_r41": round(narrowest["r43_mm2"] / narrowest["r41_mm2"], 3),
        "floor_under_jets_solid_fraction": floor_solid, "floor_under_jets_rays": rays, "heaters": heaters,
        "walls_floor_under_jets": pocket, "walls_rest_of_outlet": whole, "r41_walls_rest_of_outlet": whole_old,
        "bell_mouth_profile_error_mm_by_y": lips,
        "note": f"Open area in planes across the jets (|X| 10.3-11.5), inside P22's outer profile. Floor thickness by "
                f"vertical rays on the exact solid ({FLOOR_MIN} mm by design: two perimeters) and by ray cast along the "
                "surface normal on the printed mesh. The bell-mouth band is measured by its profile against the "
                "design (thickness across X at heights over ROOF, both sides), and the rest of the outlet against "
                "revision 41's, less the same bands."}
    if narrowest["r43_mm2"] < 1.08 * narrowest["r41_mm2"] or floor_solid < 0.999:
        failures.append("Outlet area or floor")
    if heaters["RedLizard"]["margin_mm"] < 0.25:
        failures.append("Jets reach the Red Lizard heater block")
    if rays["min_mm"] < FLOOR_MIN - 1e-3 or pocket["min_mm"] < FLOOR_MIN - 0.02:
        failures.append("Floor under the jets thinner than 0.8 mm")
    if whole["min_mm"] < whole_old["min_mm"] - 0.02:
        failures.append("Thin wall at the outlet")
    if max(lips.values()) > 0.02:
        failures.append("Bell-mouth profile")


def hotend_solids(parts, label):
    out = []
    for n, s in parts["tools"][label]["parts"]:
        if "hotend" not in n:
            continue
        for i, so in enumerate(s.Solids()):
            out.append((BAMBU_PARTS.get(i, f"{n} [{i}]") if (label == "Bambu" and n == "hotend") else f"{n} [{i}]", so))
    return out


def check_hotends(parts, report, failures):
    travel, step = WITHDRAWAL
    p22 = {"r43": fg.index_group([("P22", parts["p22"])]), "r41": fg.index_group([("P22", parts["p22_r41"])])}
    out = {}
    for label in parts["tools"]:
        rows = {}
        for name, so in hotend_solids(parts, label):
            hot = fg.index_group([(name, so)])
            row = {}
            for tag, group in p22.items():
                mounted = fg.min_distance(group, hot, cutoff=8.0)
                best = None
                for k in range(int(travel / step) + 1):
                    hit = fg.min_distance(group, hot, offset_a=(0.0, -k * step, 0.0), cutoff=8.0)
                    if hit and (best is None or hit[0] < best[0]):
                        best = (hit[0], k * step, [round(float(v), 2) for v in hit[4]])
                row[tag] = {"mounted_mm": round(mounted[0], 3) if mounted else None,
                            "withdrawal_min_mm": round(best[0], 3) if best else None,
                            "at_withdrawal_mm": best[1] if best else None, "hotend_point_mm": best[2] if best else None}
            if row["r41"]["withdrawal_min_mm"] is None and row["r43"]["withdrawal_min_mm"] is None:
                continue
            rows[name] = row
            n_, o_ = row["r43"]["withdrawal_min_mm"], row["r41"]["withdrawal_min_mm"]
            if n_ is not None and (o_ is None or n_ < o_ - 1e-3):
                failures.append(f"P22 closer to the {label} hotend's {name}")
        out[label] = rows
    out["note"] = ("Exact distances (cutoff 8 mm). The carriage backs 60 mm away in -Y in 0.5 mm steps with the tool left in "
                   "its dock, as in the requalification; every smallest gap is at the mounted position.")
    report["hotends"] = out


def check_fit(parts, report, failures):
    """P22 against every other part of both builds and the mounted tools: interference and face contact, against
    revision 41's P22 in the same place."""
    new, old = parts["p22"], parts["p22_r41"]
    others = {}
    for n, s in carriage(parts) + carriage_cartographer(parts):
        if n != R.NAMES["p22"]:
            others[n] = s
    for label, v in parts["tools"].items():
        for n, s in v["parts"]:
            others[f"{label}:{n}"] = s
    near = {n: s for n, s in others.items()
            if fg.axis_gap(fg.index_of(new), fg.index_of(s)) < 1.5 and (new.distance(s) < 1.0 or old.distance(s) < 1.0)}
    rows, new_issues = {}, []
    for n, s in near.items():
        r = {"r43_overlap_mm3": round(overlaps(new, {n: s}).get(n, 0.0), 4), "r41_overlap_mm3": round(overlaps(old, {n: s}).get(n, 0.0), 4),
             "r43_gap_mm": round(new.distance(s), 3), "r41_gap_mm": round(old.distance(s), 3)}
        rows[n] = r
        if r["r43_overlap_mm3"] > r["r41_overlap_mm3"] + 1e-4 or (r["r43_gap_mm"] < 1e-3 and r["r41_gap_mm"] >= 1e-3):
            new_issues.append(n)
    p23 = {}
    notch = R.window_notch()
    for tag, label in (("beacon", P37.NAMES["p23"]), ("cartographer", R42.NAMES["p23"])):
        s = others[label]
        bb = s.BoundingBox()
        slab = box(bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmax - 0.01, bb.zmax + 0.01)
        top = s.intersect(box(bb.xmin, bb.xmax, bb.ymin, bb.ymax, bb.zmax - 0.01, bb.zmax)).translate(cq.Vector(0, 0, 0.01))
        row = {"r43_contact_mm2": round(new.intersect(top).Volume() / 0.01, 1),
               "r41_contact_mm2": round(old.intersect(top).Volume() / 0.01, 1),
               "notch_footprint_mm2": round(old.intersect(top).intersect(notch).Volume() / 0.01, 1),
               "r43_over_bbox_mm2": round(new.intersect(slab).Volume() / 0.01, 1),
               "r41_over_bbox_mm2": round(old.intersect(slab).Volume() / 0.01, 1)}
        row["r43_share_of_r41"] = round(row["r43_contact_mm2"] / row["r41_contact_mm2"], 3)
        p23[tag] = row
        if row["r43_contact_mm2"] < row["r41_contact_mm2"] - row["notch_footprint_mm2"] - 1.0:
            new_issues.append(f"less of P22 on {label}'s top than the window notch takes")
    report["fit"] = {"within_1mm": rows, "new_interference_or_contact": new_issues, "p22_over_p23_top": p23,
                     "note": "Gap 0 with no overlap is face contact (P22 seated on P23, the screws in their holes). "
                             "'p22_over_p23_top': where P23 bears on P22, P22's area on P23's top face (the 'contact' "
                             "figures) and over its bounding box; the window notch runs through P22's underside, so "
                             "the contact may drop by the notch's footprint and no more. P23's four screws clamp it at "
                             "the bosses, |X| 15.8, at least 9 mm from the notch."}
    if new_issues:
        failures.append(f"New interference or contact: {new_issues}")


def print_oriented(s):
    """P22 on its back face (revision 41's print orientation), centred on the plate."""
    s = s.rotate(cq.Vector(0, 0, 0), cq.Vector(1, 0, 0), 90)
    bb = s.BoundingBox()
    return s.translate(cq.Vector(-(bb.xmin + bb.xmax) / 2, -(bb.ymin + bb.ymax) / 2, -bb.zmin))


def overhang(mesh, up=(0.0, 0.0, 1.0)):
    """With `up` the build direction: area on the plate, and facets facing down more steeply than the preset's threshold
    (and than 45 degrees), split by whether a support from the plate can reach them (a ray straight down misses P22)."""
    up = np.asarray(up, float) / np.linalg.norm(up)
    n, area, c = mesh.face_normals, mesh.area_faces, mesh.triangles_center
    h = c @ up
    bed = (n @ up < -0.999) & (h - h.min() < 0.02)
    d30 = (n @ up < -math.sin(math.radians(90 - SUPPORT_DEG))) & ~bed
    d45 = (n @ up < -math.sin(math.radians(45))) & ~bed
    idx = np.nonzero(d30)[0]
    hit = mesh.ray.intersects_any(c[idx] - up * 0.02, np.tile(-up, (len(idx), 1))) if len(idx) else np.zeros(0, bool)
    return {"on_plate_mm2": round(float(area[bed].sum()), 1), "needs_support_mm2": round(float(area[d30].sum()), 1),
            "over_the_part_mm2": round(float(area[idx[hit]].sum()), 1),
            "reachable_from_plate_mm2": round(float(area[idx[~hit]].sum()), 1),
            "steeper_than_45_mm2": round(float(area[d45].sum()), 1)}


def orientation_sweep(mesh, min_plate=50.0):
    """Every way to stand P22 on a flat face (each facet normal with 50 mm2 or more of P22 on the plate), and the
    support each needs."""
    nn, area, c = mesh.face_normals, mesh.area_faces, mesh.triangles_center
    groups = {}
    for i, v in enumerate(np.round(nn, 3)):
        groups.setdefault(tuple(v), []).append(i)
    rows = []
    for k, idx in groups.items():
        if area[idx].sum() < min_plate:
            continue
        d = -np.asarray(k, float) / np.linalg.norm(k)
        h = c @ d
        bed = (nn @ d < -0.999) & (h - h.min() < 0.02)
        if area[bed].sum() < min_plate:
            continue
        down = (nn @ d < -math.sin(math.radians(90 - SUPPORT_DEG))) & ~bed
        rows.append((round(float(area[down].sum()), 1), round(float(area[bed].sum()), 1), [round(float(v), 3) for v in d]))
    rows.sort()
    return {"flat_faces_tried": len(rows),
            "best": [{"needs_support_mm2": r[0], "on_plate_mm2": r[1], "up_in_assembly": r[2]} for r in rows[:4]]}


def check_print(parts, report, failures):
    rows, meshes = {}, {}
    for tag, s in (("r43", parts["p22"]), ("r41", parts["p22_r41"])):
        path = acc.WORK / f"r43_print_{tag}.stl"
        cq.exporters.export(print_oriented(s), str(path), tolerance=0.03, angularTolerance=0.1)
        meshes[tag] = trimesh.load_mesh(str(path))
        path.unlink()
        rows[tag] = overhang(meshes[tag])
    asm = V.to_mesh(parts["p22"], "p22_r43_orient")
    sweep = orientation_sweep(asm)
    walls = V.wall_report(asm, PRINT_WALL_ZONES, exclude=[RIB_ZONE])
    rib = V.wall_report(asm, [RIB_ZONE])
    report["print"] = {
        "orientation": "back face down", "support_threshold_deg": SUPPORT_DEG, **rows, "orientation_sweep_r43": sweep,
        "walls_printing_changes": walls, "rib_walls": rib,
        "rib": f"From the review: {2 * R.RIB_HALF:.1f} mm thick (three perimeters), in the plane of symmetry from the "
               f"plenum's back wall (Y{R.RIB_BACK}) to the cable boss's nose, up to the socket's floor (Z{R.RIB_TOP}); "
               f"each side flares into the nose along the 45 degree tangent to its r {R.NOSE_R:g} round, blended "
               f"r {R.RIB_BLEND_R:g}. In print the nose stands on it instead of arching over 7 mm.",
        "still_needs_support": "The cheeks' bearing faces, where P22 seats on P01's bosses: in print, ceilings 8.5 mm wide "
                               "cantilevered 10 mm from the duct, over P22 itself, so the support stands on P22's top. "
                               "And the undersides of the two 6.1 mm bosses that locate P23's rear ears, which stand "
                               "2.2 mm proud and print lying on their side (the area a support from the plate can reach): "
                               "they would print unsupported, but they fit P23's sockets with 0.10 mm of radial "
                               "clearance, so a droop would make the ears tight.",
        "bridges": f"The socket's front lip (15.4 mm) and the jets' front lips (3.7 mm). The window notch's apex is "
                   f"rounded r {R.NOTCH_R:g}: in print a 7.1 mm arch, like the top of a 10 mm hole.",
        "note": "Facets facing down more steeply than the preset's 30 degree threshold, split by whether a support "
                "from the plate can reach them. With P22 on its back face, revision 43's new faces stand vertical or "
                "face up, or overhang at 45 degrees (the window notch and its rounds where it leaves the window, the "
                "back chamfer, the floor's front chamfers, the rib's flares); the bell-mouth's foot runs back into the "
                "heel's ramp, which faces up. The sweep stands P22 on each of its flat faces with 50 mm2 or more on "
                "the plate."}
    if rib["min_mm"] is None or rib["min_mm"] < 2 * R.RIB_HALF - 0.05:
        failures.append("The rib is thinner than designed")
    if rows["r43"]["needs_support_mm2"] > rows["r41"]["needs_support_mm2"] + 2.0:
        failures.append("P22 needs more support than revision 41's")
    if rows["r43"]["on_plate_mm2"] < rows["r41"]["on_plate_mm2"]:
        failures.append("P22 stands on less of the plate than revision 41's")
    if sweep["best"] and sweep["best"][0]["needs_support_mm2"] < rows["r43"]["needs_support_mm2"] - 1.0:
        failures.append("Another orientation needs less support")
    if walls["min_mm"] is not None and walls["min_mm"] < 1.35:
        failures.append("Thin wall at the printing changes")


# --------------------------------------------------------------------------------------------
# Exports
# --------------------------------------------------------------------------------------------

def export_print_oriented(name, s):
    from OCP.BRepMesh import BRepMesh_IncrementalMesh
    from OCP.BRepTools import BRepTools
    from OCP.IMeshTools import IMeshTools_Parameters
    from OCP.StlAPI import StlAPI_Writer
    out = STL / f"{name}_PRINT_ORIENTED.stl"
    final = print_oriented(s)
    BRepTools.Clean_s(final.wrapped)
    params = IMeshTools_Parameters()
    params.Deflection = params.DeflectionInterior = PRINT_TOL
    params.Angle = params.AngleInterior = PRINT_ANG
    params.Relative, params.InParallel = False, True
    BRepMesh_IncrementalMesh(final.wrapped, params)
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    writer.Write(final.wrapped, str(out))
    m = trimesh.load_mesh(str(out))
    ok = m.is_watertight and m.is_winding_consistent and len(m.split(only_watertight=False)) == 1
    bend = np.degrees(m.face_adjacency_angles)
    smooth = bend[bend < 20.0]
    row = {"file": str(out.relative_to(ROOT)), "triangles": int(len(m.faces)), "watertight_one_body": bool(ok),
           "mesh_volume_mm3": round(float(m.volume), 2), "solid_volume_mm3": round(s.Volume(), 2),
           "p99_bend_on_curves_deg": round(float(np.percentile(smooth, 99)), 2), "height_mm": round(float(m.extents[2]), 2)}
    if not ok or abs(float(m.volume) - s.Volume()) > 5e-4 * s.Volume() or abs(m.bounds[0][2]) > 1e-6:
        raise ValueError(f"{name}: print-oriented export check failed: {row}")
    return out, row


def review_items(parts):
    """For Fusion, four columns 60 mm apart: revision 41's P22 and this one, each with the Bambu hotend (its silicone
    sock included) and with the Red Lizard; every column has P23 and the Beacon. At X+150, the left half of each P22
    (revision 41's, and revision 43's 40 mm above it), to look at the left-hand jet from the hotend slot, from +X,
    with nothing in the way."""
    items = []
    columns = ((-90.0, "R41_Bambu", parts["p22_r41"], "Bambu"), (-30.0, "R43_Bambu", parts["p22"], "Bambu"),
               (30.0, "R41_RedLizard", parts["p22_r41"], "RedLizard"), (90.0, "R43_RedLizard", parts["p22"], "RedLizard"))
    for dx, tag, p22, label in columns:
        hot = compound([s for n, s in parts["tools"][label]["parts"] if "hotend" in n])
        items += [(p22.translate((dx, 0, 0)), f"{tag}_P22", TEAL),
                  (parts["p23"].translate((dx, 0, 0)), f"{tag}_P23", ORANGE),
                  (compound(parts["beacon"][2:5]).translate((dx, 0, 0)), f"{tag}_Beacon", (0.1, 0.1, 0.12)),
                  (hot.intersect(box(-15.0, 15.0, 5.0, 40.0, -80.0, -50.0)).translate((dx, 0, 0)), f"{tag}_hotend",
                   BLUE if label == "Bambu" else RED)]
    for dz, tag, p22 in ((0.0, "R41_Cutaway", parts["p22_r41"]), (40.0, "R43_Cutaway", parts["p22"])):
        items.append((p22.intersect(box(-30.0, 0.0, -50.0, 35.0, -80.0, -40.0)).translate((150.0, 0, dz)), f"{tag}_P22", TEAL))
    return items


def exports(parts, report):
    files = export_print(R.NAMES["p22"], parts["p22"])
    path, row = export_print_oriented(R.NAMES["p22"], parts["p22"])
    files.append(path)
    report["print_oriented"] = row
    items = review_items(parts)
    files.append(export_assembly(R.NAMES["review"], items, sum(len(s.Solids()) for s, _, _ in items)))
    colours = [(s, n, TEAL if n == R.NAMES["p22"] else GREY) for n, s in carriage(parts)]
    expected = sum(len(s.Solids()) for s, _, _ in colours)
    files.append(export_assembly(R.NAMES["assembly"], colours, expected))
    report["assembly_bodies"] = expected
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p), "mb": round(p.stat().st_size / 1e6, 1)}
                         for p in files]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--workers", type=int, default=10)
    parser.add_argument("--static-only", action="store_true", help="stop after the static checks")
    args = parser.parse_args()
    started = time.perf_counter()
    failures, report = [], {"status": "PENDING"}
    print("Building", flush=True)
    parts = build_parts()
    print("Static checks", flush=True)
    for check in (check_p22, check_outlet, check_hotends, check_fit, check_print):
        t0 = time.perf_counter()
        check(parts, report, failures)
        print(f"  {check.__name__}: {time.perf_counter() - t0:.0f} s, failures {failures}", flush=True)
    report["static_failures"] = list(failures)
    if failures or args.static_only:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        if failures:
            raise SystemExit(f"Static failures: {failures}")
        return

    print("Writing the revision-43 scene", flush=True)
    b37.carriage = carriage
    manifest = b37.write_scene(parts)
    report["sources"] = manifest["sources"]
    specs = r36.specs()
    print(f"Requalification: {len(specs)} cases on {args.workers} workers", flush=True)
    results = fg.run_parallel(r36.run_task, specs, workers=args.workers)
    rack = {}
    r36.summarise(results, rack, failures)
    r36.rack_geometry(r36.scene(), rack, failures)
    rack["clearances_mm"] = {"r36_docks": rack["clearances_mm"]["r21"], "r39_dock": rack["clearances_mm"]["r36"]}
    report["requalification"] = rack

    print("Exports", flush=True)
    exports(parts, report)
    report["hardware"] = "Unchanged: P22's inserts, the P22-to-P01 button heads and the probe screws stay as in revisions 41 and 42."
    report["limitations"] = [
        "Rigid CAD and sampled straight paths. Airflow is simulated separately (cfd_cpap_r43.py, "
        "verification_cfd_cpap_r43.json), not measured.",
        "The Bambu hotend and its silicone sock are this project's model of the P2S hotend; a real sock up to the "
        "margins in 'hotends' still clears. Measure yours if it differs.",
        "The floor under the jets is 0.8 mm, two perimeters with P22 on its back face, under the 1.0 mm minimum used "
        "elsewhere on the CPAP parts; it carries no load, and the jets keep it cool.",
        "Printability is judged on the meshes (overhang angle, rays to the plate), not on a print: the cheeks' "
        "bearing faces and the undersides of P23's two locating bosses still need support, and the bridges listed "
        "under 'print' are left to the slicer."]
    report["failures"] = failures
    report["status"] = "P22_LOWER_BELL_MOUTH_JETS_VERIFIED_RACK_REQUALIFIED_CAD_REVIEW_NOT_MACHINE_QUALIFICATION" if not failures \
        else "FAILED_SEE_FAILURES"
    report["runtime_s"] = round(time.perf_counter() - started, 1)
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    brief = {k: report[k] for k in ("status", "failures", "runtime_s")}
    brief["outlet"] = report["outlet"]["narrowest_mm2"]
    brief["bed"] = rack["bed"]["summary"]
    print(json.dumps(brief, indent=1, default=str))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
