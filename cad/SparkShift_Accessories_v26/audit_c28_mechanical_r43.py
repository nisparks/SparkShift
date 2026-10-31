"""Build and qualify the separate Bambu C28 mechanical review, without changing R43."""
import argparse
import hashlib
import json
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh
from OCP.BRepBndLib import BRepBndLib
from OCP.Bnd import Bnd_Box
from scipy.spatial import cKDTree

import build_and_verify_accessories_v26 as acc
import fast_geometry as fg
import r37_parts as P37
import r42_parts as P42
import r43_c28_mechanical as M
import r43_swept_feed as F
from build_modular_toolhead import ROOT

SOURCE = acc.WORK / "r43_scene"
BASELINE = acc.WORK / "swept_feed" / "optC28_clean"
OUTPUT = acc.WORK / "swept_feed" / "optC28_mechanical"
REPORT = ROOT / "verification_c28_mechanical_geometry_r43.json"
NAMES = {
    "p01": "P01_C28_Bambu_45deg_Mounts_REVIEW",
    "p21": "P21_C28_Bambu_Forked_Retainer_REVIEW",
    "p22": "P22_C28_Bambu_45deg_Mounts_Retainer_Beacon_REVIEW",
    "cartographer": "P22_C28_Bambu_45deg_Mounts_Retainer_Cartographer_REVIEW",
}
REPLACED = ("P01_", "P21_", "P22_", "P23_", "R37_REAR_", "ACC_CASE_BOSS_HEATSET_",
            "R41_P22_P01_M3x8_")


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def bounds(body):
    b = Bnd_Box()
    BRepBndLib.AddOptimal_s(body.wrapped, b, False, False)
    x0, y0, z0, x1, y1, z1 = b.Get()
    return [x0, x1, y0, y1, z0, z1]


def compound(parts):
    return cq.Compound.makeCompound(list(parts))


def read_source():
    manifest = json.loads((SOURCE / "manifest.json").read_text())
    carriage = {n: cq.Shape.importBrep(str(SOURCE / p)) for n, p in manifest["carriage"]}
    tools = {n: cq.Shape.importBrep(str(SOURCE / p)) for n, p in manifest["variants"]["Bambu"]["parts"]}
    return manifest, carriage, tools


def find(parts, prefix):
    return next(s for n, s in parts.items() if n.startswith(prefix))


def mesh_check(body):
    vertices, triangles = body.tessellate(.015, .07)
    mesh = trimesh.Trimesh([v.toTuple() for v in vertices], triangles, process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent, (
        mesh.is_watertight, mesh.is_winding_consistent, len(mesh.faces))
    return {"watertight": True, "consistent_winding": True, "triangles": len(mesh.faces)}


def ring_fraction(body, outer, inner):
    ring = outer.cut(inner)
    return body.intersect(ring).Volume() / ring.Volume()


def carriage_step_roundtrip(before, after):
    # The inherited P01 also fails an exact self-cut. Require congruent complete
    # tessellations plus CAD properties instead of accepting an invalid Boolean.
    self_cut = before.copy().cut(before.copy())
    assert not self_cut.isValid(), "Revisit the inherited-P01 comparison if its Boolean behavior changes"
    meshes = []
    for body in (before, after):
        vertices, faces = body.tessellate(.015, .07)
        meshes.append(trimesh.Trimesh([v.toTuple() for v in vertices], faces, process=True))
    a, b = meshes
    assert a.is_watertight and b.is_watertight
    distance, mapping = cKDTree(a.vertices).query(b.vertices)
    assert len(a.vertices) == len(b.vertices) == len(np.unique(mapping))
    assert float(distance.max()) < 1e-5

    patch_errors, patch_counts = [], []
    for source, target, source_faces, target_faces in (
        (a, b, a.faces, mapping[b.faces]), (b, a, mapping[b.faces], a.faces),
    ):
        existing = set(map(tuple, np.sort(target_faces, axis=1)))
        changed = [i for i, face in enumerate(np.sort(source_faces, axis=1)) if tuple(face) not in existing]
        triangles = source.triangles[changed]
        points = np.vstack([triangles.mean(axis=1), (triangles[:, 0] + triangles[:, 1]) / 2,
                            (triangles[:, 0] + triangles[:, 2]) / 2,
                            (triangles[:, 1] + triangles[:, 2]) / 2])
        errors = trimesh.proximity.closest_point(target, points)[1] if len(points) else np.array([0.0])
        patch_errors.append(float(errors.max()))
        patch_counts.append(len(changed))
    assert max(patch_errors) < 1e-5, patch_errors
    differences = {
        "volume_mm3": abs(before.Volume() - after.Volume()),
        "area_mm2": abs(before.Area() - after.Area()),
        "centroid_mm": (before.Center() - after.Center()).Length,
        "bounds_mm": max(abs(x - y) for x, y in zip(bounds(before), bounds(after))),
    }
    assert differences["volume_mm3"] < 1e-3 and differences["area_mm2"] < 1e-3
    assert differences["centroid_mm"] < 1e-5 and differences["bounds_mm"] < 1e-5
    return {
        "method": "Complete watertight tessellations have one-to-one matching vertices. Alternate "
                  "triangulation patches agree at every centroid and edge midpoint in both directions. "
                  "CAD volume, area, centroid and bounds also match. P01's inherited "
                  "exact self-difference is invalid; its invalid Boolean volume is not used as evidence.",
        "maximum_vertex_difference_mm": float(distance.max()), "differences": differences,
        "triangles_per_representation": len(a.faces), "retriangulated_patch_triangles": patch_counts,
        "maximum_patch_sample_difference_mm": max(patch_errors), "inherited_self_boolean_valid": False,
    }


def quick_overlap(a, b, offset=(0, 0, 0)):
    ai, bi = fg.index_group([("a", a)]), fg.index_group([("b", b)])
    if not any(fg.touch_or_nest(x, y, offset) for x in ai for y in bi):
        return 0.0
    return a.translate(offset).intersect(b).Volume()


def require_no_overlap(a, b, label):
    value = quick_overlap(a, b)
    assert value < 1e-4, (label, value)
    return value


def driver_gauges():
    gauges = {}
    seat = M.MOUNT_GAP + M.MOUNT_GRIP
    for i, x in enumerate(M.MOUNT_X):
        gauges[f"inclined_mount_{i}"] = M.mount_cylinder(
            x, seat + M.BUTTON_H, seat + M.BUTTON_H + 35, 2.5)
    gauges["underside_retainer"] = M.cylinder(0, M.RETAINER_Y, M.SEAT_Z - 37,
                                            M.SEAT_Z - M.BUTTON_H, 2.5)
    return gauges


def export_prints(parts, report):
    report["print_orientations"] = {}
    for key, body in parts.items():
        angle = 180 if key == "p21" else 90
        oriented = body.rotate((0, 0, 0), (1, 0, 0), angle)
        bb = bounds(oriented)
        oriented = oriented.translate((-(bb[0] + bb[1]) / 2, -(bb[2] + bb[3]) / 2, -bb[4]))
        stl = ROOT / "stl" / f"{NAMES[key]}_PRINT_ORIENTED.stl"
        cq.exporters.export(oriented, str(stl), tolerance=.025, angularTolerance=.08)
        mesh = trimesh.load_mesh(str(stl))
        assert mesh.is_watertight and mesh.is_winding_consistent, stl
        report["exports_sha256"][str(stl.relative_to(ROOT))] = digest(stl)
        report["print_orientations"][key] = "Top face down" if key == "p21" else "Back face down"
    report["print_export_audit_sha256"] = digest(__file__)
    report["print_pose_warning"] = "Do not use the P22 inlet-face-down pose with the assessed supports: " \
                                  "the toolpath screen found support inside the narrow rear passage."


def geometry():
    OUTPUT.mkdir(exist_ok=True)
    manifest, carriage, tools = read_source()
    base = {"p01": find(carriage, "P01_"), "p21": find(carriage, "P21_"),
            "p22": cq.Shape.importBrep(str(BASELINE / "p22_swept_beacon.brep"))}
    parts = {"p01": M.p01(base["p01"]), "p21": M.p21(base["p21"]),
             "p22": M.retained_p22(M.angled_p22(base["p22"]))}
    cable = find(carriage, "Probe_Cable")
    hardware = dict(M.hardware())
    added, removed = {}, {}
    report = {
        "status": "GEOMETRY_AUDIT_IN_PROGRESS", "scope": "Bambu only; separate mechanical review",
        "source_sha256": {p: digest(ROOT / p) for p in ("r43_c28_mechanical.py", "audit_c28_mechanical_r43.py")},
        "frozen_scene_manifest_sha256": digest(SOURCE / "manifest.json"),
        "frozen_c28_beacon_sha256": digest(BASELINE / "p22_swept_beacon.brep"),
        "parts": {}, "interfaces": [], "exports_sha256": {},
        "limitations": [
            "No physical strength, torque, heat, sealing or print-fit qualification.",
            "Airflow boundaries change locally and externally; existing C28 CFD is not a result for this variant.",
            "Sampled service/movement paths are recorded separately from static fit.",
            "Fasteners use nominal conservative head/shank envelopes; heat-set knurls are not modelled.",
        ],
    }
    for key, body in parts.items():
        assert body.isValid() and len(body.Solids()) == len(body.Shells()) == 1, key
        added[key], removed[key] = body.cut(base[key]), base[key].cut(body)
        assert added[key].isValid() and removed[key].isValid(), (key, "Invalid change-region Boolean")
        row = {
            "valid_single_solid_shell": True, "volume_mm3": body.Volume(), "bounds_mm": bounds(body),
            "added_mm3": added[key].Volume(), "removed_mm3": removed[key].Volume(),
            "mesh": mesh_check(body),
            "cable_overlap_mm3": require_no_overlap(body, cable, f"{key}/cable"),
            "new_material_cable_gap_mm": added[key].distance(cable),
        }
        for suffix, shape in (("", body), ("_added", added[key]), ("_removed", removed[key])):
            shape.exportBrep(str(OUTPUT / f"{key}{suffix}.brep"))
        report["parts"][key] = row
        print("part", key, json.dumps(row), flush=True)
    build_manifest = {
        "generator_sha256": digest(ROOT / "r43_c28_mechanical.py"),
        "frozen_scene_manifest_sha256": digest(SOURCE / "manifest.json"),
        "body_sha256": {f"{k}{suffix}.brep": digest(OUTPUT / f"{k}{suffix}.brep")
                       for k in parts for suffix in ("", "_added", "_removed")},
    }
    (OUTPUT / "build_manifest.json").write_text(json.dumps(build_manifest, indent=2) + "\n")

    for a, b in (("p01", "p21"), ("p01", "p22"), ("p21", "p22")):
        report["interfaces"].append({
            "a": a, "b": b, "overlap_mm3": require_no_overlap(parts[a], parts[b], f"{a}/{b}"),
            "gap_mm": parts[a].distance(parts[b]),
        })
    assert abs(parts["p01"].distance(parts["p22"]) - M.MOUNT_GAP) < 1e-5
    report["hardware_in_plastic_mm3"] = {
        n: {k: require_no_overlap(h, s, f"{n}/{k}") for k, s in parts.items()}
        for n, h in hardware.items()}
    for name, body in hardware.items():
        body.exportBrep(str(OUTPUT / f"{name}.brep"))

    rings = {}
    for i, x in enumerate(M.MOUNT_X):
        rings[f"p01_insert_{i}_1p2mm_wall_fraction"] = ring_fraction(
            parts["p01"], M.mount_cylinder(x, -4, -.05, M.INSERT_R + 1.2),
            M.mount_cylinder(x, -4.01, 0, M.INSERT_R))
    rings["tongue_insert_1p2mm_wall_fraction"] = ring_fraction(
        parts["p21"], M.cylinder(0, M.RETAINER_Y, -64.95, -61.05, M.INSERT_R + 1.2),
        M.cylinder(0, M.RETAINER_Y, -65, -61, M.INSERT_R))
    assert min(rings.values()) > .999, rings
    report["insert_walls"] = rings
    report["fasteners"] = {
        "paired_mounts": {"face_angle_deg": 45, "axes_x_mm": list(M.MOUNT_X),
                          "face_center_yz_mm": [M.MOUNT_Y, M.MOUNT_Z], "face_gap_mm": M.MOUNT_GAP,
                          "grip_mm": M.MOUNT_GRIP, "bolt": "2 x M3x8 ISO 7380 button head",
                          "insert": "2 x M3x4, nominal OD 4.6 mm, pocket diameter 4.54 mm",
                          "thread_engagement_mm": 4.0, "tip_clearance_mm": .55,
                          "nominal_bearing_area_mm2": 64 - np.pi * M.HOLE_R**2},
        "retainer": {"bolt": "M3x10 ISO 7380 button head, inserted from underneath",
                     "insert": "M3x4, nominal OD 4.6 mm, pocket diameter 4.54 mm",
                     "axis_xy_mm": [0, M.RETAINER_Y], "head_seat_z_mm": M.SEAT_Z,
                     "thread_engagement_mm": 4.0, "tip_clearance_mm": .3,
                     "socket_radial_clearance_mm": M.SOCKET_CLEARANCE,
                     "socket_end_clearance_mm": M.SOCKET_CLEARANCE,
                     "insert_wall_mm": M.TONGUE_R - M.INSERT_R,
                     "nominal_root_section_both_arms_mm2": 2 * (M.ROOT_OUTER_X - M.FORK_INNER_X)
                                                            * (-49 - M.ROOT_BOTTOM),
                     "fork_inner_width_mm": 2 * M.FORK_INNER_X,
                     "minimum_added_cable_gap_mm": added["p21"].distance(cable)},
    }

    unchanged = {n: s for n, s in carriage.items() if not n.startswith(REPLACED)}
    hits = []
    for an, a in {**added, **hardware}.items():
        for bn, b in {**unchanged, **tools}.items():
            volume = quick_overlap(a, b)
            if volume > 1e-4:
                hits.append({"new": an, "other": bn, "mm3": volume})
    assert not hits, hits
    report["new_material_hardware_vs_unchanged_and_bambu_mm3"] = hits
    tool_index = fg.index_group(list(tools.items()))
    report["head_to_mounted_bambu_mm"] = {}
    for name, body in hardware.items():
        if "BUTTON" in name:
            hit = fg.min_distance(fg.index_group([(name, body)]), tool_index, cutoff=30)
            assert hit is None or hit[0] >= 3, (name, "Head/tool clearance below 3 mm", hit)
            report["head_to_mounted_bambu_mm"][name] = (
                {"mm": hit[0], "part": hit[2]} if hit else {"greater_than_mm": 30})
    report["driver_access"] = {}
    for name, gauge in driver_gauges().items():
        checked = {**parts, **unchanged, **tools}
        collisions = {n: v for n, b in checked.items() if (v := quick_overlap(gauge, b)) > 1e-4}
        assert not collisions, (name, collisions)
        report["driver_access"][name] = {
            "clear": True, "shaft_diameter_mm": 5, "straight_reach_mm": 35,
            "limitation": "Shaft envelope, not a particular handle. Underside service requires bed clearance.",
        }

    probes = {"Beacon": P37.beacon()[3], "Cartographer": P42.cartographer()}
    beacon = P37.beacon()
    keepouts = {"Beacon": {"bottom": beacon[0], "top": P37.beacon_top_keepout(beacon)},
                "Cartographer": P42.keepouts()}
    report["probes"] = {}
    for name, probe in probes.items():
        ko = keepouts[name]
        report["probes"][name] = {
            "new_material_overlap_mm3": require_no_overlap(compound(added.values()), probe, f"{name}/additions"),
            "metal_in_top_keepout_mm3": require_no_overlap(compound(hardware.values()), ko["top"], f"{name}/top"),
            "metal_in_bottom_keepout_mm3": require_no_overlap(compound(hardware.values()), ko["bottom"], f"{name}/bottom"),
            "new_plastic_in_bottom_keepout_mm3": require_no_overlap(compound(added.values()), ko["bottom"],
                                                                   f"{name}/plastic-bottom"),
        }
    protected = M.box(-24, 24, -23, 31, -79, -66)
    protected_diff = added["p22"].intersect(protected).Volume() + removed["p22"].intersect(protected).Volume()
    assert protected_diff < 1e-4, protected_diff
    envelope = F.R41.fuse(F.nozzle(True, 3, .9, 28, conformal_outlet=True),
                          F.feed(-1, True, 3), F.feed(1, True, 3))
    feed_diff = added["p22"].intersect(envelope).Volume() + removed["p22"].intersect(envelope).Volume()
    assert feed_diff < 1e-4, feed_diff
    report["lower_jets_and_probe_seat_changes_mm3"] = protected_diff
    report["c28_swept_feed_and_outlet_changes_mm3"] = feed_diff
    mount_zones = compound([M.box(x - 4.5, x + 4.5, 11.19, 20, -58.5, -49)
                            for x in M.MOUNT_X])
    p01_outside = added["p01"].cut(mount_zones).Volume() + removed["p01"].cut(mount_zones).Volume()
    assert p01_outside < 1e-4, p01_outside
    report["p01_changes_outside_mount_zones_mm3"] = p01_outside
    airway = F.main_channel_air().cut(base["p22"])
    new_air = airway.cut(parts["p22"])
    pockets = compound(M.root_slots() + [
        M.cylinder(0, M.RETAINER_Y, -65.25, -48, M.TONGUE_R + M.SOCKET_CLEARANCE)])
    report["air_changes"] = {
        "new_material_in_original_channel_mm3": added["p22"].intersect(airway).Volume(),
        "root_pockets_to_remaining_channel_mm": compound(M.root_slots()).distance(new_air),
        "circular_socket_to_remaining_channel_mm": M.cylinder(
            0, M.RETAINER_Y, -65.25, -48, M.TONGUE_R + M.SOCKET_CLEARANCE).distance(new_air),
        "pockets_open_to_original_air_mm3": pockets.intersect(airway).Volume(),
        "note": "Two small rounded root-floor reinforcements, not new flow-guiding ribs. "
                "Their cooling effect is unmeasured; C28 CFD remains baseline-only.",
    }
    assert report["air_changes"]["pockets_open_to_original_air_mm3"] < 1e-4
    assert min(report["air_changes"][k] for k in (
        "root_pockets_to_remaining_channel_mm", "circular_socket_to_remaining_channel_mm")) >= 1.15
    print("air", json.dumps(report["air_changes"]), flush=True)

    service = []
    for dz in np.arange(0, 18.01, .25):
        moving = parts["p22"].translate((0, 0, -float(dz)))
        hits = {n: v for n, b in {"P01": parts["p01"], "P21": parts["p21"], "cable": cable}.items()
                if (v := quick_overlap(moving, b)) > 1e-4}
        if hits:
            service.append({"lowering_mm": float(dz), "hits": hits})
    assert not service, service[:10]
    report["lower_duct_service"] = {
        "downward_release_mm": 18, "sample_step_mm": .25, "samples": 73,
        "collisions": service,
        "sequence": "Park/remove Bambu tool, raise assembly clear of bed, unplug/free probe lead, "
                    "remove both angled mount screws and the underside retainer screw, lower P22 18 mm. "
                    "P21 and EBB42 stay on the carriage. Reverse to assemble; install inserts before assembly.",
        "note": "Rigid cable reference checked; cable slack and connector access still require bench verification.",
    }

    cart_base = cq.Shape.importBrep(str(BASELINE / "p22_swept_cartographer.brep"))
    cart = M.retained_p22(M.angled_p22(cart_base))
    report["cartographer_mesh"] = mesh_check(cart)
    require_no_overlap(cart, probes["Cartographer"], "Cartographer-seat P22/probe")
    cart.exportBrep(str(OUTPUT / "p22_cartographer.brep"))
    report["cartographer_brep_sha256"] = digest(OUTPUT / "p22_cartographer.brep")
    report["status"] = "STATIC_AND_SERVICE_VERIFIED_EXPORTS_PENDING"
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    return export_review(parts, cart, hardware, cable, carriage, tools, report)


def export_review(parts, cart, hardware, cable, carriage, tools, report):
    report["step_roundtrips"] = {}
    for key, body in {**parts, "cartographer": cart}.items():
        step = ROOT / "step" / f"{NAMES[key]}.step"
        cq.exporters.export(body, str(step))
        restored = cq.importers.importStep(str(step)).val()
        assert restored.isValid() and len(restored.Solids()) == 1, key
        if key == "p01":
            comparison = carriage_step_roundtrip(body, restored)
        else:
            removed_step, added_step = body.cut(restored), restored.cut(body)
            assert removed_step.isValid() and added_step.isValid(), (key, "Invalid STEP comparison")
            difference = max(removed_step.Volume(), added_step.Volume())
            assert difference < 1e-3, (key, difference)
            comparison = {"maximum_exact_difference_mm3": difference}
        report["step_roundtrips"][key] = comparison
        print("STEP", key, json.dumps(comparison), flush=True)
        report["exports_sha256"][str(step.relative_to(ROOT))] = digest(step)
    export_prints({**parts, "cartographer": cart}, report)

    assembly = cq.Assembly(name="C28_Bambu_Mechanical_Study_REVIEW")
    colors = {"p01": (.36, .44, .54), "p21": (.94, .55, .18), "p22": (.08, .58, .72)}
    for n, p in parts.items():
        assembly.add(p, name=NAMES[n], color=cq.Color(*colors[n]))
    for n, p in hardware.items():
        assembly.add(p, name=n, color=cq.Color(*((.72, .52, .23) if "HEATSET" in n else (.42, .45, .49))))
    assembly.add(cable, name="Probe_cable_reference", color=cq.Color(.65, .25, .48))
    assembly.add(find(carriage, "Beacon_"), name="Beacon_reference", color=cq.Color(.2, .22, .25))
    for n, p in tools.items():
        assembly.add(p, name=f"Bambu_{n.replace(' ', '_')}", color=cq.Color(.53, .55, .57))
    step = ROOT / "step" / "53_C28_Bambu_Angled_Mounts_And_Retainer_REVIEW.step"
    assembly.save(str(step))
    report["exports_sha256"][str(step.relative_to(ROOT))] = digest(step)
    report["exports_audit_sha256"] = digest(__file__)
    report["status"] = "STATIC_GEOMETRY_EXPORT_AND_SERVICE_PATH_VERIFIED_REVIEW_ONLY"
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--print-exports-only", action="store_true")
    modes.add_argument("--exports-only", action="store_true")
    args = parser.parse_args()
    if not (args.print_exports_only or args.exports_only):
        geometry()
        return
    report = json.loads(REPORT.read_text())
    assert report["status"] in ("STATIC_GEOMETRY_EXPORT_AND_SERVICE_PATH_VERIFIED_REVIEW_ONLY",
                                "STATIC_AND_SERVICE_VERIFIED_EXPORTS_PENDING")
    assert report["source_sha256"]["r43_c28_mechanical.py"] == digest(ROOT / "r43_c28_mechanical.py")
    manifest = json.loads((OUTPUT / "build_manifest.json").read_text())
    assert all(digest(OUTPUT / path) == sha for path, sha in manifest["body_sha256"].items())
    parts = {k: cq.Shape.importBrep(str(OUTPUT / f"{k}.brep")) for k in ("p01", "p21", "p22")}
    if args.exports_only:
        _, carriage, tools = read_source()
        cart_base = cq.Shape.importBrep(str(BASELINE / "p22_swept_cartographer.brep"))
        cart = M.retained_p22(M.angled_p22(cart_base))
        report["cartographer_mesh"] = mesh_check(cart)
        require_no_overlap(cart, P42.cartographer(), "Cartographer-seat P22/probe")
        cart.exportBrep(str(OUTPUT / "p22_cartographer.brep"))
        report["cartographer_brep_sha256"] = digest(OUTPUT / "p22_cartographer.brep")
        export_review(parts, cart, dict(M.hardware()), find(carriage, "Probe_Cable"), carriage, tools, report)
        return
    assert report["status"] == "STATIC_GEOMETRY_EXPORT_AND_SERVICE_PATH_VERIFIED_REVIEW_ONLY"
    parts["cartographer"] = cq.Shape.importBrep(str(OUTPUT / "p22_cartographer.brep"))
    assert digest(OUTPUT / "p22_cartographer.brep") == report["cartographer_brep_sha256"]
    export_prints(parts, report)
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print("Print-oriented exports refreshed without changing qualified CAD.")


if __name__ == "__main__":
    main()
