"""Revision 41: fixes from the first physical build (parts in r41_parts.py).

Static checks:
- every revision-41 part is a single valid solid; P20, P21, P22, P02 and P03 change only inside their edit
  zones, and the CPAP parts don't grow;
- wall thickness, ray cast on the printed meshes: the CPAP joint walls, the outlet, P22's cheeks, all of P24,
  P02's servo recess and P03's magnet pockets;
- CPAP joints: radial slip of each sleeve in its socket, and the bore area through each sleeve;
- the outlet: the jets' open area against the released one, their height against both hotends' heaters, and
  P22's distance to both hotends;
- P22 on P01: no cheek material around P01's bosses, the face gap and bearing, the screws' engagement and
  clearance;
- P24: every EBB42 part and plug zone, the probe cable, hall leads, motor and motor connector clear; its
  bearing on P02's face and on P21; the inserts and screw engagement;
- P02: the MG90D body's fit in the tighter recess; P02 unchanged elsewhere;
- P03: each variant's magnets fit their pockets, stand 0.2 mm proud and clear both mounted tool bodies;
- every pair of carriage parts and fasteners (revision-31 core with the new P02 and P03, the servo, P20-P24,
  cable, Beacon, EBB42), the mounted tools, the Cartographer, the Beacon keepouts, the Monolith X gantry.
Then, on a revision-41 scene (WORK/r41_scene): the revision-36 full-rack requalification and a sweep of the
carriage at the rear travel limit against the flying gantry.

Run: python build_carriage_fixes_r41.py [--workers 10] [--static-only]
"""
import argparse
import json
import os
import time

import build_and_verify_accessories_v26 as acc
import build_inlet_screws_r40 as b40

os.environ["SPARKSHIFT_SCENE"] = str(acc.WORK / "r41_scene")

import cadquery as cq  # noqa: E402
import numpy as np  # noqa: E402
import trimesh  # noqa: E402
from OCP.Bnd import Bnd_Box  # noqa: E402
from OCP.BRepBndLib import BRepBndLib  # noqa: E402
from OCP.gp import gp_Dir, gp_Lin, gp_Pnt  # noqa: E402
from OCP.IntCurvesFace import IntCurvesFace_ShapeIntersector  # noqa: E402

import build_chute_chamfer_rack_r36 as r36  # noqa: E402
import build_probe_height_datum_dock_r37 as b37  # noqa: E402
import fast_geometry as fg  # noqa: E402
import r37_parts as P37  # noqa: E402
import r40_parts as P40  # noqa: E402
import r41_parts as R  # noqa: E402
from audit_tool_owned_2510 import bounds, compound, overlaps  # noqa: E402
from build_bambu_clean_r29 import sha  # noqa: E402
from build_carriage_lowered_mounts_r31 import NAMES as R31, confined  # noqa: E402
from build_fan_mounts_r33 import export_assembly, export_print  # noqa: E402
from build_modular_toolhead import ROOT, box, load  # noqa: E402
from build_p24_cable_entry_r35 import NAMES as R35  # noqa: E402
from build_refined_docking_review import translated_hits  # noqa: E402

REPORT = "verification_carriage_fixes_r41.json"
REVIEW_MAGNET = "15x5x3"                    # the P03 variant mounted in the carriage-wide checks
SERVO = "MG90D_Servo_Envelope"
CHANGED = ("P20", "P21", "P22", "P24", "P02", "P03")
ZONES = {
    "P20": [(-22.0, 22.0, -47.0, -24.0, -22.2, -12.5)],
    "P21": [(-22.0, 22.0, -47.0, -24.0, -21.7, -17.7), (-22.0, 22.0, -47.0, -24.0, -52.1, -43.9),
            (-4.7, 4.7, -39.2, -34.8, -52.1, -17.7)],
    "P22": [(-22.0, 22.0, -47.0, -24.0, -52.1, -48.9)]
           + [(x0, x1, 14.9, 30.1, -78.6, -73.4) for x0, x1 in ((8.3, 13.0), (-13.0, -8.3))]
           + [(x0, x1, 10.9, 21.6, -63.1, -49.4) for x0, x1 in ((13.8, 22.6), (-22.6, -13.8))],
    "P02": [(4.2, 16.8, -11.4, -6.6, 33.6, 57.1)],
    "P03": [(x0, x1, 27.4, 32.2, z0, z1) for x0, x1 in ((2.8, 10.2), (-10.2, -2.8)) for z0, z1 in ((18.2, 35.2), (-6.8, 10.2))],
}
# Wall checks: what revision 41 changed at the outlet (the duct-to-slot wall's new bottom, the floor's new inner
# end and the front wall's new end), then the whole outlet against the released part; P22's cheeks.
OUTLET_CHANGED = [(x0, x1, 15.0, 30.0, -78.2, -73.0) for x0, x1 in ((8.3, 13.0), (-13.0, -8.3))]
OUTLET_ALL = [(x0, x1, 15.0, 30.0, -78.2, -73.0) for x0, x1 in ((8.3, 21.5), (-21.5, -8.3))]
CHEEK_ZONES = [(x0, x1, 11.0, 21.0, -63.0, -49.4) for x0, x1 in ((13.8, 22.6), (-22.6, -13.8))]


def exact_bounds(s):
    """Bounds from the geometry, not from a mesh an STL export may have left on the shape."""
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(s.wrapped, b, False, False)
    x0, y0, z0, x1, y1, z1 = b.Get()
    return [x0, x1, y0, y1, z0, z1]


def key(s):
    return (round(s.Volume(), 0),) + tuple(round(v, 1) for v in bounds(s))


def core(p02, p03, magnets):
    """The revision-31 core, its P02 and P03 replaced and its four 15x5x3 receiver magnets swapped for the
    variant's own, plus the MG90D envelope (the core never carried the servo)."""
    meta = json.loads((acc.WORK / "v26_meta.json").read_text())
    v26 = {m["name"]: P37.shape(s) for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))}
    old_p02, old_p03 = key(load("P02_Motor_servo_plate_12p5mm")), key(load("P03_Front_case_COTS"))
    old_magnets = {key(v26[f"OCT_RECEIVER_MAGNET_{i}"]) for i in range(4)}
    out, swapped = [], []
    for i, s in enumerate(load(R31["core"]).Solids()):
        k = key(s)
        if k == old_p02:
            swapped.append("P02")
        elif k == old_p03:
            swapped.append("P03")
        elif k in old_magnets:
            swapped.append("magnet")
        else:
            out.append((f"Core_{i:03d}", s))
    if sorted(swapped) != ["P02", "P03", "magnet", "magnet", "magnet", "magnet"]:
        raise ValueError(f"Core swap found {swapped}")
    out += [(R.NAMES["p02"], p02), (R.NAMES[f"p03_{p03[0]}"], p03[1])]
    out += [(f"P03_Magnet_{i}", m) for i, m in enumerate(magnets)]
    out.append((SERVO, v26["HOBBY_SERVO_ENVELOPE"]))
    return out


def carriage(parts):
    b = parts["beacon"]
    out = list(parts["core"]) + [
        (R.NAMES["p22"], parts["p22"]), (R.NAMES["p20"], parts["p20"]), (R.NAMES["p21"], parts["p21"]),
        (P37.NAMES["p23"], parts["p23"]), (R.NAMES["p24"], parts["p24"]), (P37.NAMES["cable"], parts["cable"]),
        ("Beacon_RevH_Raised", compound(b[2:5])), ("EBB42", parts["ebb42"])]
    return out + list(parts["other_hardware"]) + list(parts["hardware"])


def build_parts():
    parts = b40.build_parts()
    parts["p20"], parts["p21"], parts["p22"] = R.p20(), R.p21(), R.p22()
    parts["p24"], parts["p02"] = R.p24(), R.p02()
    parts["p03"] = {k: R.p03(k) for k in R.MAGNETS}
    parts["magnets"] = {k: R.magnet(k) for k in R.MAGNETS}
    parts["other_hardware"] = R.other_hardware()
    parts["core"] = core(parts["p02"], (REVIEW_MAGNET, parts["p03"][REVIEW_MAGNET]), parts["magnets"][REVIEW_MAGNET])
    return parts


# --------------------------------------------------------------------------------------------
# Wall thickness on the printed meshes
# --------------------------------------------------------------------------------------------

def to_mesh(s, name):
    path = acc.WORK / f"r41_check_{name}.stl"
    cq.exporters.export(cq.Workplane().add(s), str(path), tolerance=0.01, angularTolerance=0.1)
    m = trimesh.load(str(path), force="mesh")
    path.unlink()
    return m


def thickness(mesh, n=90000, offset=0.01):
    """Distance from each sampled surface point straight inward to the opposite wall (exit face facing away)."""
    pts, fi = trimesh.sample.sample_surface_even(mesh, n, seed=1)
    nrm = mesh.face_normals[fi]
    origins = pts - nrm * offset
    t = np.full(len(pts), np.inf)
    loc, ri, tri = mesh.ray.intersects_location(origins, -nrm, multiple_hits=True)
    if len(ri):
        d = np.einsum("ij,ij->i", loc - origins[ri], -nrm[ri])
        ok = (d > 0.02) & (np.einsum("ij,ij->i", mesh.face_normals[tri], -nrm[ri]) > 0.5)
        for r, dd in zip(ri[ok], d[ok]):
            t[r] = min(t[r], dd + offset)
    return pts, t, mesh.area / len(pts)


def wall_report(mesh, zones=None, exclude=(), limits=(0.8, 1.0, 1.2)):
    pts, t, per = thickness(mesh)
    keep = np.ones(len(pts), bool)
    if zones:
        keep = np.zeros(len(pts), bool)
        for z in zones:
            keep |= np.all((pts >= np.array(z[0::2])) & (pts <= np.array(z[1::2])), axis=1)
    for z in exclude:
        keep &= ~np.all((pts >= np.array(z[0::2])) & (pts <= np.array(z[1::2])), axis=1)
    p, tt = pts[keep], t[keep]
    out = {"min_mm": round(float(tt.min()), 3) if len(tt) else None, "sampled_mm2": round(float(len(tt) * per), 1)}
    for lim in limits:
        out[f"below_{lim}_mm2"] = round(float((tt < lim).sum() * per), 1)
    if len(tt):
        worst = np.argsort(tt)[:5]
        out["thinnest_at"] = [[round(float(v), 2) for v in p[i]] + [round(float(tt[i]), 3)] for i in worst]
    return out


def meshes(parts):
    released = {"p20": load(P40.NAMES["p20"]), "p21": load(P40.NAMES["p21"]), "p22": P37.p22()[0],
                "p24": load(R35["p24"]), "p02": load("P02_Motor_servo_plate_12p5mm"), "p03": load("P03_Front_case_COTS")}
    new = {k: parts[k] for k in released if k != "p03"}
    new.update({f"p03_{k}": v for k, v in parts["p03"].items()})
    return {k: to_mesh(v, k) for k, v in new.items()}, {k: to_mesh(v, "old_" + k) for k, v in released.items()}


def slab(s, z, t=0.04, x0=-40.0, x1=40.0):
    return s.intersect(box(x0, x1, -70, 10, z - t / 2, z + t / 2))


def flow_area(solids, z):
    env = R.corridor((0.0, 3.5), z - 0.02, z + 0.02)
    return (env.Volume() - env.intersect(compound([slab(s, z) for s in solids])).Volume()) / 0.04


JOINTS = (("P20_in_P21", "p20", "p21", -19.70, (-22.0, 22.0, -47.0, -24.0, -21.6, -17.7)),
          ("P21_in_P22", "p21", "p22", -50.20, (-22.0, 22.0, -47.0, -24.0, -51.45, -48.9)))


def check_parts(parts, report, failures):
    released = {"P20": load(P40.NAMES["p20"]), "P21": load(P40.NAMES["p21"]), "P22": P37.p22()[0],
                "P24": load(R35["p24"]), "P02": load("P02_Motor_servo_plate_12p5mm"), "P03": load("P03_Front_case_COTS")}
    new = {"P20": parts["p20"], "P21": parts["p21"], "P22": parts["p22"], "P24": parts["p24"], "P02": parts["p02"],
           **{f"P03_{k}": v for k, v in parts["p03"].items()}}
    rows = {}
    for name, s in new.items():
        base = name.split("_")[0]
        old = released[base]
        row = {"valid": s.isValid(), "solids": len(s.Solids()), "volume_mm3": round(s.Volume(), 1),
               "released_volume_mm3": round(old.Volume(), 1), "bounds_mm": [round(v, 3) for v in exact_bounds(s)]}
        zones = ZONES.get(base, ZONES["P03"] if base == "P03" else None)
        if zones:
            c = confined(s.copy(), old.copy(), zones)
            row["unchanged_outside_edit_zones"] = c["unchanged_outside_zones"]
            if not c["unchanged_outside_zones"]:
                failures.append(f"{name} changed outside its edit zones")
        if base in ("P20", "P21", "P22"):
            nb, ob = exact_bounds(s), exact_bounds(old)
            row["outer_bounds_unchanged"] = max(abs(p - q) for p, q in zip(nb, ob)) < 1e-3
            row["within_released_bounds"] = all(nb[2 * i] >= ob[2 * i] - 1e-3 and nb[2 * i + 1] <= ob[2 * i + 1] + 1e-3
                                                for i in range(3))
            if not row["within_released_bounds"]:
                failures.append(f"{name} grew beyond its released bounds")
        if not (row["valid"] and row["solids"] == 1):
            failures.append(f"{name} is not a single valid solid")
        rows[name] = row
    report["parts"] = rows


def check_joints(parts, report, failures):
    released = {"p20": load(P40.NAMES["p20"]), "p21": load(P40.NAMES["p21"]), "p22": P37.p22()[0]}
    out = {}
    for label, up, low, z, zone in JOINTS:
        a_, b_ = parts[up], parts[low]
        clash = overlaps(a_, {low: b_})
        side = slab(a_, z, x0=8.0).distance(slab(b_, z, x0=8.0))
        boss = slab(a_, z, x0=-6.0, x1=6.0).distance(slab(b_, z, x0=-6.0, x1=6.0))
        out[label] = {"interference_mm3": clash, "radial_slip_mm": round(side, 3), "cable_boss_slip_mm": round(boss, 3),
                      "open_area_mm2": round(flow_area([a_, b_], z), 1),
                      "released_open_area_mm2": round(flow_area([released[up], released[low]], z), 1),
                      "note": "Open area at mid-sleeve, including the probe cable's 12 mm2 channel."}
        if clash or not 0.16 <= side <= 0.20 or not 0.05 <= boss <= 0.08:
            failures.append(f"{label}: sleeve fit")
    walls = {}
    for name, key_, zones in (("P20_sleeve", "p20", [JOINTS[0][4]]),
                              ("P21_socket_and_sleeve", "p21", [JOINTS[0][4], JOINTS[1][4]]),
                              ("P22_socket", "p22", [JOINTS[1][4]])):
        walls[name] = wall_report(parts["meshes"][key_], zones)
        walls[name]["released_min_mm"] = wall_report(parts["released_meshes"][key_], zones)["min_mm"]
        if walls[name]["min_mm"] < 1.1:
            failures.append(f"{name}: joint wall {walls[name]['min_mm']} mm")
    out["walls"] = walls
    report["joints"] = out


def open_area(p22, x, side):
    lo, hi = sorted((side * (x - 0.01), side * (x + 0.01)))
    window = box(lo, hi, 16.0, 29.5, -76.70, -73.0).intersect(HORN)
    return (window.Volume() - window.intersect(p22).Volume()) / 0.02


HORN = R.shape(R.a.prism_yz_r(R.HORN_OUT, R.HORN_OUT_R, -23.0, 23.0))   # P22's outer YZ profile: no air under its heel


def lowest_surface_z(shape, x0, x1, y0, y1, z0=-80.0, step=0.2):
    """Lowest point of `shape` over an XY rectangle, by vertical rays: the Red Lizard heater block's model
    doesn't survive a boolean with a partial box."""
    isect = IntCurvesFace_ShapeIntersector()
    isect.Load(shape.wrapped, 1e-6)
    nx, ny = max(1, round((x1 - x0) / step)), max(1, round((y1 - y0) / step))
    best = None
    for i in range(nx + 1):
        for j in range(ny + 1):
            isect.Perform(gp_Lin(gp_Pnt(x0 + i * (x1 - x0) / nx, y0 + j * (y1 - y0) / ny, z0), gp_Dir(0, 0, 1)), 0.0, 40.0)
            if isect.IsDone():
                for k in range(1, isect.NbPnt() + 1):
                    best = isect.Pnt(k).Z() if best is None else min(best, isect.Pnt(k).Z())
    return best


def check_outlet(parts, report, failures):
    new, old = parts["p22"], P37.p22()[0]
    xs = (10.3, 10.6, 10.9, 11.15, 11.5)
    throat = {f"x{x}": {"r41_mm2": round(sum(open_area(new, x, s) for s in (-1, 1)), 1),
                        "released_mm2": round(sum(open_area(old, x, s) for s in (-1, 1)), 1)} for x in xs}
    narrowest = {k: min(v[k] for v in throat.values()) for k in ("r41_mm2", "released_mm2")}
    floor = [box(*sorted((s * 10.3, s * 15.0)), 22.5, 27.5, -77.80, -76.70) for s in (-1, 1)]
    floor_solid = round(sum(f.intersect(new).Volume() for f in floor) / sum(f.Volume() for f in floor), 6)
    tools, heaters = {}, {}
    for label, v in parts["tools"].items():
        hot = compound([s for n, s in v["parts"] if "hotend" in n])
        tools[label] = {"r41_mm": round(new.distance(hot), 3), "released_mm": round(old.distance(hot), 3)}
        if tools[label]["r41_mm"] < tools[label]["released_mm"] - 1e-3:
            failures.append(f"P22 closer to the {label} hotend")
        bottom = min(lowest_surface_z(hot, lo, hi, R.THROAT_Y[0], R.THROAT_Y[1])
                     for lo, hi in ((4.0, R.WALL_X[0]), (-R.WALL_X[0], -4.0)))
        heaters[label] = {"heater_bottom_z": round(bottom, 2), "jet_top_z": R.ROOF, "jet_floor_z": -76.65,
                          "jet_below_heater_mm": round(min(bottom, R.ROOF) - (-76.65), 2),
                          "margin_mm": round(bottom - R.ROOF, 2),
                          "released_jet_top_z": -74.85}
    walls = wall_report(parts["meshes"]["p22"], OUTLET_CHANGED)
    whole = wall_report(parts["meshes"]["p22"], OUTLET_ALL)
    whole_old = wall_report(parts["released_meshes"]["p22"], OUTLET_ALL)
    report["outlet"] = {
        "jets": "Horizontal, one each side of the nozzle, between the channel floor (Z-76.65) and the flat bottom of the "
                f"duct-to-slot wall (Z{R.ROOF}); the floor under them is solid, so no air blows down at the bed.",
        "open_area_both_sides": throat, "narrowest_mm2": narrowest,
        "area_ratio": round(narrowest["r41_mm2"] / narrowest["released_mm2"], 2),
        "floor_under_jets_solid_fraction": floor_solid,
        "heaters": heaters,
        "upstream_mm2": {"hose_bore": 211.2, "p22_side_channels_min": 153.7},
        "walls_changed_regions": walls, "released_walls_changed_regions": wall_report(parts["released_meshes"]["p22"], OUTLET_CHANGED),
        "walls_whole_outlet": whole, "released_walls_whole_outlet": whole_old,
        "note": "Open area in planes across the jets (|X| 10.3-11.5), inside P22's outer profile. The revision-41 "
                "review's first figure (41.8 mm2 released) also counted open air under P22's heel; this one doesn't.",
        "hotend_gap": tools}
    if narrowest["r41_mm2"] < 1.5 * narrowest["released_mm2"] or floor_solid < 0.999:
        failures.append("Outlet area")
    if any(h["margin_mm"] < 0.25 for k, h in heaters.items() if k == "RedLizard"):
        failures.append("Jets reach the Red Lizard heater block")
    if walls["min_mm"] < 1.0:
        failures.append("Thin wall at the outlet")
    if whole["below_0.8_mm2"] > whole_old["below_0.8_mm2"] or whole["min_mm"] < whole_old["min_mm"] - 0.02:
        failures.append("Outlet thinner than released")


def check_p22_mounts(parts, report, failures):
    """P22's cheeks bear on P01's bosses face to face; nothing of P22 wraps them."""
    p22, old, p01 = parts["p22"], P37.p22()[0], load(R31["p01"])
    hw = dict(R.p22_mount_hardware())
    rows = {}
    for i, x in enumerate(R.P01_BOSS_X):
        s = 1 if x > 0 else -1
        lo, hi = sorted((s * R.CHEEK_X[0], s * R.CHEEK_X[1]))
        behind = box(lo, hi, R.P01_BOSS_Y[0] - 0.4, R.P01_BOSS_Y[1], -58.0, -49.5)
        screw = hw[f"R41_P22_P01_M3x8_BUTTON_{i}"]
        tip = bounds(screw)[2]
        face22 = p22.intersect(box(lo, hi, R.CHEEK_FACE, R.CHEEK_FACE + 0.05, -60.0, -49.0)).translate((0, -0.1, 0))
        face01 = p01.intersect(box(lo, hi, R.P01_BOSS_Y[1] - 0.05, R.P01_BOSS_Y[1], -60.0, -49.0))
        rows[f"x{x:+.0f}"] = {
            "p22_around_boss_mm3": round(p22.intersect(behind).Volume(), 3),
            "released_p22_around_boss_mm3": round(old.intersect(behind).Volume(), 3),
            "face_gap_mm": round(p22.distance(p01), 3),
            "bearing_on_boss_mm2": round(face22.intersect(face01).Volume() / 0.05, 1),
            "screw": "M3x8 ISO 7380 button head on the cheek's front face",
            "screw_tip_y_mm": round(tip, 2), "thread_in_insert_mm": round(R.P01_BOSS_Y[1] - tip, 2),
            "head_to_mounted_tool_mm": {label: round(screw.distance(compound([p for _, p in v["parts"]])), 3)
                                        for label, v in parts["tools"].items()},
            "screw_in_p22_or_p01_mm3": round(screw.intersect(p22).Volume() + screw.intersect(p01).Volume(), 4)}
    walls = wall_report(parts["meshes"]["p22"], CHEEK_ZONES)
    report["p22_mounts"] = {"bosses": rows, "walls": walls,
                            "released_walls": wall_report(parts["released_meshes"]["p22"], CHEEK_ZONES)}
    for r in rows.values():
        if r["p22_around_boss_mm3"] > 1e-3 or not 0.04 <= r["face_gap_mm"] <= 0.06 or r["bearing_on_boss_mm2"] < 25 \
                or r["thread_in_insert_mm"] < 3.5 or min(r["head_to_mounted_tool_mm"].values()) < 3.0 \
                or r["screw_in_p22_or_p01_mm3"] > 1e-3:
            failures.append("P22 face mount on P01")
            break
    if walls["min_mm"] < 1.2:
        failures.append(f"P22 cheek wall {walls['min_mm']} mm")


def contact_area(a_, b_, axis, at, t=0.05):
    """Area where a_'s face at `at` meets b_'s face there (axis 'y' or 'z')."""
    if axis == "y":
        sa = a_.intersect(box(-40, 40, at - t, at, -40, 80)).translate((0, t, 0))
        sb = b_.intersect(box(-40, 40, at, at + t, -40, 80))
    else:
        sa = a_.intersect(box(-40, 40, -60, 10, at, at + t)).translate((0, 0, -t))
        sb = b_.intersect(box(-40, 40, -60, 10, at - t, at))
    return round(sa.intersect(sb).Volume() / t, 1)


def check_p24(parts, report, failures):
    p24, old = parts["p24"], load(R35["p24"])
    rig = dict(carriage(parts))
    near = {}
    for name, s in rig.items():
        if name in (R.NAMES["p24"],) or not name.startswith(("Core", "P0", "P2", "MG90D", "EBB42", "Probe", "R41", "ACC")):
            continue
        d = p24.distance(s)
        if d < 3.0:
            near[name] = round(d, 3)
    comps = [round(p24.distance(s), 3) for s in parts["ebb42"].Solids() if s.BoundingBox().ymax > R.Y_SEAT - 0.3]
    plugs = {f"zone_{i}": round(p24.intersect(box(*z)).Volume(), 3) for i, z in enumerate(R.PLUG_ZONES)}
    out = {
        "volume_mm3": {"r41": round(p24.Volume(), 1), "released": round(old.Volume(), 1)},
        "faces": {"r41": len(p24.Faces()), "released": len(old.Faces())},
        "min_gap_to_ebb42_parts_mm": min(comps), "plug_zones_mm3": plugs,
        "nearest_parts_mm": dict(sorted(near.items(), key=lambda kv: kv[1])[:16]),
        "bearing_on_p02_mm2": contact_area(p24, parts["p02"], "y", R.Y_FRONT),
        "bearing_on_p21_mm2": contact_area(p24, parts["p21"], "z", R.Z_BASE),
        "inserts": {"pocket_y_mm": R.INSERT[:2], "hole_diameter_mm": 2 * R.INSERT[2],
                    "insert": "M3 x 4, OD 4.2 (modelled at the Ø4.0 hole it melts into)",
                    "clearance_hole_diameter_mm": 2 * R.CLEAR_R, "pressing_channel_diameter_mm": 2 * R.PRESS_R,
                    "screws": {"upper": "M3x18 through P20's wings, tip at Y-17.8, through the whole insert",
                               "lower": "M3x14 from behind the board, tip at Y-18.25, through the whole insert"}},
        "walls": wall_report(parts["meshes"]["p24"]),
        "released_walls": wall_report(parts["released_meshes"]["p24"])}
    report["p24"] = out
    if out["min_gap_to_ebb42_parts_mm"] < 0.2 or any(v > 0.001 for v in plugs.values()):
        failures.append("P24 too close to the EBB42 or in a plug zone")
    if out["bearing_on_p02_mm2"] < 200 or out["bearing_on_p21_mm2"] < 100:
        failures.append("P24 bearing")
    if out["walls"]["min_mm"] < 0.8:
        failures.append(f"P24 wall {out['walls']['min_mm']} mm")


def check_p02(parts, report, failures):
    """P02's tighter recess against the MG90D's datasheet body and the v26 STEP envelope."""
    p02, servo = parts["p02"], dict(parts["core"])[SERVO]
    old = load("P02_Motor_servo_plate_12p5mm")
    body = R.shape(R.pocket_box(R.SERVO_DATASHEET, R.PLATE_REAR)).intersect(box(-50, 50, -12.0, R.POCKET_FLOOR - 0.05, 0, 100))
    (w, length), (dw, dl) = R.SERVO_POCKET, R.SERVO_DATASHEET
    released = (R.POCKET[1] - R.POCKET[0], R.POCKET[3] - R.POCKET[2])
    env = p02.intersect(servo)
    ends = (R.SERVO_CENTRE[1] - length / 2, R.SERVO_CENTRE[1] + length / 2)
    at_ends = all(min(abs(bb[4] - e) for e in ends) < 0.1 and min(abs(bb[5] - e) for e in ends) < 0.1
                  for bb in [bounds(s) for s in env.Solids()])
    rig = dict(carriage(parts))
    others = {n: round(p02.distance(rig[n]), 3) for n in rig
              if n.startswith(("P24", "EBB42", "P20", "MG90_M2x8", "Core")) and p02.distance(rig[n]) < 3.0}
    out = {
        "recess_mm": {"r41": [w, length], "released": [round(released[0], 2), round(released[1], 2)], "depth": 4.5},
        "mg90d_datasheet_body_mm": [dw, dl],
        "play_per_side_mm": {"r41": {"across": round((w - dw) / 2, 3), "along": round((length - dl) / 2, 3)},
                             "released": {"across": round((released[0] - dw) / 2, 3),
                                          "along": round((released[1] - dl) / 2, 3)}},
        "datasheet_body_interference_mm3": round(p02.intersect(body).Volume(), 4),
        "step_envelope_overlap_mm3": round(env.Volume(), 2),
        "step_envelope_overlap_only_at_the_ends": at_ends,
        "note": "The v26 servo envelope is 22.96 mm long, 0.16 mm over TowerPro's 22.8 mm; it overlaps each end of "
                "the recess by 0.03 mm. The two ear screws and everything else on P02 are unchanged.",
        "nearest_mm": others,
        "walls": wall_report(parts["meshes"]["p02"], ZONES["P02"]),
        "released_walls": wall_report(parts["released_meshes"]["p02"], ZONES["P02"])}
    report["p02"] = out
    if out["datasheet_body_interference_mm3"] > 1e-3 or not at_ends or w < dw or length < dl \
            or w > released[0] - 0.05 or length > released[1] - 0.1:
        failures.append("Servo fit")
    if out["walls"]["min_mm"] < out["released_walls"]["min_mm"] - 0.01:
        failures.append(f"P02 recess wall {out['walls']['min_mm']} mm")


def check_p03(parts, report, failures):
    tools = {label: dict(v["parts"])["body"] for label, v in parts["tools"].items()}
    limits = (0.4, 0.6, 0.8)
    released = wall_report(parts["released_meshes"]["p03"], ZONES["P03"], limits=limits)
    out = {"released_walls": released,
           "note": "The released pockets' inner walls were 0.2 mm from P03's centre slot and the Ø6×4 floors 0.27 mm. "
                   "In revision 41 the 6 mm magnets' pockets open into the slot wherever the wall would be under 0.6 mm; "
                   "the Ø6×4 floor is 0.5 mm at the three +X discs at Z 30.5, 5.5 and -2.0 (P03's wall is 4.3 mm thick "
                   "there, with carriage parts right behind it). The thinnest wall left in every variant is P03's own "
                   "notch above the upper pockets."}
    for kind in R.MAGNETS:
        p03, mags = parts["p03"][kind], parts["magnets"][kind]
        lifted = [m.translate((0, 0.05, 0)) for m in mags]
        row = {"magnets": len(mags), "spec": R.MAGNET_SPECS[kind],
               "interference_mm3": round(sum(m.intersect(p03).Volume() for m in mags), 4),
               "side_clearance_mm": round(min(m.distance(p03) for m in lifted), 3),
               "proud_of_front_face_mm": round(max(bounds(m)[3] for m in mags) - R.P03_FACE_Y, 3),
               "gap_to_mounted_tool_mm": {label: round(min(m.distance(b) for m in mags), 3) for label, b in tools.items()},
               "walls": wall_report(parts["meshes"][f"p03_{kind}"], ZONES["P03"], limits=limits)}
        out[kind] = row
        if row["interference_mm3"] > 0.001 or row["side_clearance_mm"] > 0.1 or min(row["gap_to_mounted_tool_mm"].values()) <= 0:
            failures.append(f"P03 {kind} magnet fit")
        if row["walls"]["min_mm"] < released["min_mm"] or row["walls"]["below_0.4_mm2"] > released["below_0.4_mm2"]:
            failures.append(f"P03 {kind}: thinner walls than the released P03")
    report["p03"] = out


def core_side(name):
    return name.startswith(("Core_", "P02_", "P03_", SERVO))


def released_counterpart(name, magnets):
    if name == R.NAMES["p02"]:
        return load("P02_Motor_servo_plate_12p5mm")
    if name.startswith("P03_Front_Case"):
        return load("P03_Front_case_COTS")
    if name.startswith("P03_Magnet_"):
        return magnets[int(name.rsplit("_", 1)[1])]
    return None


def standoff_only(screw, ebb):
    """A P24 screw against the EBB42 model: it passes through the model's solid corner standoff (3.2 x 6 mm);
    anything else it meets is reported. The released, coaxial Ø3.0 shanks matched the standoffs exactly, which
    OCC's common returns as empty."""
    other = 0.0
    for e in ebb.Solids():
        v = screw.intersect(e).Volume()
        b = bounds(e)
        if v > 1e-6 and not (b[2] > -32.0 and b[3] < -25.0 and b[3] - b[2] > 5.5 and b[1] - b[0] < 3.3 and b[5] - b[4] < 3.3):
            other += v
    return other


def check_carriage(parts, report, failures):
    rig = dict(carriage(parts))
    servo_pair = {R.NAMES["p02"], SERVO}
    skip = lambda a_, b_: b37.beacon_internal(a_, b_) or {a_, b_} == servo_pair
    rows, contacts = b40.split_contacts(b37.overlap_rows(rig, rig, skip=skip), rig)
    meta = json.loads((acc.WORK / "v26_meta.json").read_text())
    v26 = {m["name"]: P37.shape(s) for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))}
    old_magnets = [v26[f"OCT_RECEIVER_MAGNET_{i}"] for i in range(4)]
    released_core, standoffs, new = [], [], []
    for r in rows:
        a_, b_ = r["a"], r["b"]
        if core_side(a_) and core_side(b_):
            sa = released_counterpart(a_, old_magnets) or rig[a_]
            sb = released_counterpart(b_, old_magnets) or rig[b_]
            old = sa.intersect(sb).Volume()
            if abs(r["mm3"] - old) <= 0.02 + 0.01 * old:
                released_core.append(dict(r, released_mm3=round(old, 3)))
                continue
        pair = {a_, b_}
        if "EBB42" in pair:
            screw = (pair - {"EBB42"}).pop()
            if screw.startswith("R41_EBB42_M3x") and standoff_only(rig[screw], rig["EBB42"]) <= 0.06:
                standoffs.append(r)
                continue
        new.append(r)
    report["carriage_internal"] = {
        "checked": "Every pair of carriage parts and fasteners: the revision-31 core with the new P02, P03 and "
                   f"{REVIEW_MAGNET} magnets, the MG90D envelope, P20-P24, cable, Beacon, EBB42, all fasteners. "
                   "P02 against the servo envelope is the snug recess, reported under p02.",
        "new_intersections_mm3": new,
        "released_core_overlaps_mm3": released_core,
        "screws_through_ebb42_standoffs_mm3": standoffs,
        "face_contacts": contacts,
        "note": "Revision 40 checked the core as one body. Split here so P02, P03 and the magnets could be swapped, "
                "its own fasteners show their modelled overlaps (screws in inserts and self-tapping holes); each "
                "matches the same pair with the released P02, P03 and receiver magnets."}
    if new:
        failures.append("Carriage-internal intersection")
    changed = {n: s for n, s in rig.items() if n.startswith(CHANGED) or n.startswith("R41_")}
    report["cartographer_vs_changed_mm3"] = b37.overlap_rows({"Cartographer": parts["cartographer"]}, changed)
    mounted = []
    for label, v in parts["tools"].items():
        for name, s in v["parts"]:
            mounted += [{"tool": label, "part": name, "b": t, "mm3": m} for t, m in overlaps(s, changed).items()]
    report["mounted_tools_vs_changed_mm3"] = mounted
    b = parts["beacon"]
    metal = {n: s for n, s in parts["other_hardware"] if n.startswith("R41_")}
    report["beacon_keepouts_metal_mm3"] = {k: overlaps(ko, metal) for k, ko in
                                          (("top", P37.beacon_top_keepout(b)), ("bottom", b[0]))}
    if report["cartographer_vs_changed_mm3"] or mounted or any(report["beacon_keepouts_metal_mm3"].values()):
        failures.append("Cartographer, mounted tool or Beacon keepout")


def check_gantry(parts, report, failures):
    new = {"P20": parts["p20"], "P21": parts["p21"], "P22": parts["p22"], "P24": parts["p24"], "P02": parts["p02"]}
    old = {"P20": load(P40.NAMES["p20"]), "P21": load(P40.NAMES["p21"]), "P22": P37.p22()[0], "P24": load(R35["p24"]),
           "P02": load("P02_Motor_servo_plate_12p5mm")}
    rows = {}
    for c in b40.GANTRY_CENTERS:
        beam, ends = b40.gantry_groups(c)
        for kind, group in (("beam_and_rail", beam), ("end_joints", ends)):
            n_, o_ = b40.nearest(new, group), b40.nearest(old, group)
            for part in new:
                r = rows.setdefault(f"{part}_{kind}_mm", {"r41": None, "released": None})
                for tag, hit in (("r41", n_[part]), ("released", o_[part])):
                    if hit and (r[tag] is None or hit["mm"] < r[tag]):
                        r[tag] = round(hit["mm"], 3)
    for name, r in rows.items():
        if r["r41"] is not None and r["r41"] < min(r["released"] if r["released"] is not None else 6.0, 0.5) - 1e-6:
            failures.append(f"{name}: closer to the X gantry than released")
    report["x_gantry_min_distance"] = rows


def rear_group(name):
    for k in ("P20", "P21", "P22", "P23", "P24", "P02", "P03", "EBB42", "Beacon", "Probe_Cable", "MG90D"):
        if name.startswith(k):
            return k
    return "Core"


def task_rear_travel(s, nozzle_y, xs):
    f, groups = s["frames"], {}
    for n, p in s["carriage_parts"]:
        groups.setdefault(rear_group(n), []).append(p)
    world = {k: r36.world(compound(v), 0, f) for k, v in groups.items()}
    flying = s["fixed"]["Flying_Gantry"]
    dy, hits = nozzle_y - b40.DOCK_NOZZLE_Y, []
    for x in xs:
        for k, w in world.items():
            h = translated_hits(w, {"Flying_Gantry": flying}, (x, dy, 0))
            if h:
                hits.append({"x_mm": x, "part": k, "mm3": h["Flying_Gantry"]})
    near, fly = {}, fg.index_group([("Flying_Gantry", flying)])
    for x in (xs[0], xs[-1]):
        for k in ("P20", "P21", "P22", "P24", "P02", "MG90D", "Core"):
            if k not in world:
                continue
            hit = fg.min_distance(fg.index_group([(k, world[k])]), fly, (x, dy, 0), (0, 0, 0), cutoff=30.0)
            if hit and (k not in near or hit[0] < near[k]["mm"]):
                near[k] = {"mm": hit[0], "x_mm": x}
    return {"nozzle_y_mm": nozzle_y, "x_mm": [xs[0], xs[-1]], "samples": len(xs), "hits": hits, "nearest": near}


def run_task(spec):
    if spec["kind"] == "rear_travel":
        started = time.perf_counter()
        result = task_rear_travel(r36.scene(), **spec["args"])
        return {**spec, "result": result, "seconds": time.perf_counter() - started}
    return r36.run_task(spec)


def rear_specs():
    return [{"kind": "rear_travel", "args": {"nozzle_y": y, "xs": list(range(a_, b_, 2))}}
            for y in b40.REAR_LIMITS for a_, b_ in ((0, 60), (60, 120), (120, 180), (180, 240), (240, 300), (300, 352))]


def summarise_rear(results, report, failures):
    rows = [r for r in results if r["kind"] == "rear_travel"]
    out = {}
    for y in b40.REAR_LIMITS:
        mine = [r["result"] for r in rows if r["args"]["nozzle_y"] == y]
        near = {}
        for m in mine:
            for k, v in m["nearest"].items():
                if k not in near or v["mm"] < near[k]["mm"]:
                    near[k] = v
        out[f"nozzle_y{y}"] = {"samples": sum(m["samples"] for m in mine), "hits": [h for m in mine for h in m["hits"]],
                               "nearest_mm": {k: round(v["mm"], 2) for k, v in sorted(near.items())}}
        if out[f"nozzle_y{y}"]["hits"]:
            failures.append(f"Carriage hits the flying gantry at nozzle Y{y}")
    report["rear_travel"] = out


def exports(parts, report):
    files = []
    for k in ("p20", "p21", "p22", "p24", "p02"):
        files += export_print(R.NAMES[k], parts[k])
    for k in R.MAGNETS:
        files += export_print(R.NAMES[f"p03_{k}"], parts["p03"][k])
    brass, steel = (0.8, 0.55, 0.2), (0.35, 0.35, 0.38)
    hw = R.p24_hardware() + R.p22_mount_hardware()
    files.append(export_assembly(R.NAMES["hardware"], [(s, n, brass if "HEATSET" in n else steel) for n, s in hw], len(hw)))
    items, expected = [], 0
    for n, s in carriage(parts):
        color = ((0.75, 0.75, 0.78) if "Magnet" in n else (0.95, 0.55, 0.12) if n.startswith(CHANGED) else
                 (0.15, 0.35, 0.85) if n == P37.NAMES["cable"] else (0.1, 0.1, 0.12) if n.startswith(("Beacon", "MG90D"))
                 else (0.13, 0.45, 0.2) if n == "EBB42" else brass if "HEATSET" in n else
                 steel if n.startswith(("ACC_", "R37_", "R40_", "R41_")) else (0.55, 0.57, 0.6))
        items.append((s, n, color))
        expected += len(s.Solids())
    files.append(export_assembly(R.NAMES["assembly"], items, expected))
    report["review_bodies"] = expected
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
    parts["meshes"], parts["released_meshes"] = meshes(parts)
    print("Static checks", flush=True)
    for check in (check_parts, check_joints, check_outlet, check_p22_mounts, check_p24, check_p02, check_p03,
                  check_carriage, check_gantry):
        t0 = time.perf_counter()
        check(parts, report, failures)
        print(f"  {check.__name__}: {time.perf_counter() - t0:.0f} s, failures {failures}", flush=True)
    report["static_failures"] = list(failures)
    if failures or args.static_only:
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        if failures:
            raise SystemExit(f"Static failures: {failures}")
        return

    print("Writing the revision-41 scene", flush=True)
    b37.carriage = carriage
    manifest = b37.write_scene(parts)
    report["sources"] = manifest["sources"]
    specs = r36.specs() + rear_specs()
    print(f"Requalification and rear travel: {len(specs)} cases on {args.workers} workers", flush=True)
    results = fg.run_parallel(run_task, specs, workers=args.workers)
    rack = {}
    r36.summarise([r for r in results if r["kind"] != "rear_travel"], rack, failures)
    r36.rack_geometry(r36.scene(), rack, failures)
    rack["clearances_mm"] = {"r36_docks": rack["clearances_mm"]["r21"], "r39_dock": rack["clearances_mm"]["r36"]}
    report["requalification"] = rack
    summarise_rear(results, report, failures)

    print("Exports", flush=True)
    exports(parts, report)
    report["hardware"] = {
        "changed": "P24: the four M3 x 4 heat-set inserts (OD 4.2) go in Ø4.0 pockets at Y-22.6..-18.6, pressed in "
                   "from the side that faces P02; the upper EBB42 screws through P20's wings stay M3x18, now through "
                   "the whole insert, and the lower ones become M3x14 (were M3x12). P22 to P01: 2x M3x8 ISO 7380 "
                   "button heads on the cheeks' front faces (were M3x10 socket heads in counterbores), into the same "
                   "inserts in P01's bosses. P03: the magnets of the chosen variant.",
        "unchanged": "Everything else, including P20, P21 and P02's screws and inserts."}
    report["failures"] = failures
    report["status"] = ("BUILD_FIXES_VERIFIED_RACK_REQUALIFIED_CAD_REVIEW_NOT_MACHINE_QUALIFICATION"
                        if not failures else "FAILED_SEE_FAILURES")
    report["limitations"] = [
        "Rigid CAD and sampled straight paths. Airflow is compared by open area, not simulated.",
        "P02's recess is sized for TowerPro's MG90D body, 12.2 x 22.8 mm; a servo that measures differently needs "
        "SERVO_POCKET in r41_parts.py changed.",
        "Insert pull-out, printed-part creep and magnet glue joints are not qualified."]
    report["runtime_s"] = round(time.perf_counter() - started, 1)
    (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
    brief = {k: report[k] for k in ("status", "failures", "runtime_s")}
    brief["rear_travel"] = {k: {"hits": len(v["hits"]), "nearest": v["nearest_mm"]} for k, v in report["rear_travel"].items()}
    brief["bed"] = rack["bed"]["summary"]
    print(json.dumps(brief, indent=1, default=str))
    if failures:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
