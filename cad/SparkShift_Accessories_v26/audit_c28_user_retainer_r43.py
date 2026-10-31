"""Build and qualify the Bambu C28 user-post retainer study, without changing R43 or the fork study.

The user's Fusion P21 post is the input. This adds only: the confined lower rear/side relief,
a 45 deg rear seal skirt, and the matched P22 receiver (open front, sleeve dam, rear keel).
"""
import argparse
import json

import cadquery as cq
import numpy as np
import trimesh
from scipy.spatial import cKDTree

import fast_geometry as fg
import r37_parts as P37
import r42_parts as P42
import r43_c28_mechanical as M
import r43_c28_user_joint as U
import r43_swept_feed as F
from audit_c28_mechanical_r43 import (
    BASELINE, REPLACED, ROOT, SOURCE, acc, bounds, carriage_step_roundtrip, compound, digest,
    driver_gauges, find, mesh_check, quick_overlap, read_source, require_no_overlap, ring_fraction)

USER = acc.WORK / "swept_feed" / "userP21_20261030_193918"
USER_STEP = USER / "p21_user_snapshot.step"
USER_STEP_SHA256 = "1924a9adcdbded32578c2ae548e22acad8503a6dda8709281e6154e825e8ca62"
OUTPUT = acc.WORK / "swept_feed" / "optC28_user_retainer"
REPORT = ROOT / "verification_c28_user_retainer_geometry_r43.json"
P01_STEP = ROOT / "step" / "P01_C28_Bambu_45deg_Mounts_REVIEW.step"
NAMES = {
    "p21": "P21_C28_Bambu_User_Post_Sealed_REVIEW",
    "p22": "P22_C28_Bambu_User_Post_Receiver_Beacon_REVIEW",
    "cartographer": "P22_C28_Bambu_User_Post_Receiver_Cartographer_REVIEW",
}
ASSEMBLY = ROOT / "step" / "54_C28_Bambu_User_Post_Retainer_REVIEW.step"
BASELINE_DUCT_AIR_MM3 = 27775.6
STEP_PROPERTY_TOLERANCE = 5e-3


def congruent_step_roundtrip(before, after):
    """STEP check for exchange-derived bodies whose own exact self-difference is invalid, as P01's is."""
    assert not before.copy().cut(before.copy()).isValid(), "Use the exact Boolean comparison"
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
                            (triangles[:, 0] + triangles[:, 2]) / 2, (triangles[:, 1] + triangles[:, 2]) / 2])
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
    assert differences["volume_mm3"] < STEP_PROPERTY_TOLERANCE and differences["area_mm2"] < STEP_PROPERTY_TOLERANCE
    assert differences["centroid_mm"] < 1e-5 and differences["bounds_mm"] < 1e-5
    return {
        "method": "This exchange-derived body's own exact self-difference is invalid, so Boolean volumes are "
                  "not used. Complete watertight tessellations have one-to-one matching vertices; alternate "
                  "triangulation patches agree at every centroid and edge midpoint in both directions; CAD "
                  "centroid and bounds match within 1e-5 mm and volume/area within the recorded differences.",
        "property_tolerance_mm3_mm2": STEP_PROPERTY_TOLERANCE,
        "maximum_vertex_difference_mm": float(distance.max()), "differences": differences,
        "triangles_per_representation": len(a.faces), "retriangulated_patch_triangles": patch_counts,
        "maximum_patch_sample_difference_mm": max(patch_errors), "self_boolean_valid": False,
    }


def step_roundtrip(before, after):
    removed, added = before.cut(after), after.cut(before)
    if removed.isValid() and added.isValid():
        difference = max(removed.Volume(), added.Volume())
        assert difference < 1e-3, difference
        return {"method": "Exact Boolean difference in both directions.", "maximum_exact_difference_mm3": difference}
    return congruent_step_roundtrip(before, after)


def duct_cavity(p21, p22):
    """Inlet-connected duct air with the CFD outlet box removed. A leak reaches the outer box."""
    scene = dict(json.loads((acc.WORK / "r41_scene" / "manifest.json").read_text())["carriage"])
    p20 = cq.Shape.importBrep(str(acc.WORK / "r41_scene" / scene["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))
    cap = cq.Solid.makeCylinder(8.2 + 2.5, 2.0, cq.Vector(0, -48.5, 29.0))
    space = M.box(-40, 40, -70, 60, -110, 45).cut(p20.fuse(p21).fuse(p22)).cut(cap).cut(
        M.box(-30, 30, -20, 50, -79.08, -45))
    cavity = next(s for s in space.Solids() if s.isInside(cq.Vector(0, -48.5, 20.0)))
    b = bounds(cavity)
    return {"volume_mm3": cavity.Volume(), "bounds_mm": b,
            "sealed_inside_carriage": b[0] > -39 and b[1] < 39 and b[2] > -69 and b[5] < 44}


def build(carriage):
    assert digest(USER_STEP) == USER_STEP_SHA256, "User P21 snapshot changed"
    user, exchange = U.load_user_p21(USER_STEP)
    relieved = U.refine_lower_support(user)
    cable, old21 = find(carriage, "Probe_Cable"), find(carriage, "P21_")
    bases = {probe: U.receiver_base(M.angled_p22(cq.Shape.importBrep(str(BASELINE / f"p22_swept_{probe}.brep"))))
             for probe in ("beacon", "cartographer")}
    built = {probe: U.matched_receiver(relieved, old21, base, cable, lower_relief=True,
                                       open_front=True, sealed=True)
             for probe, base in bases.items()}
    parts = {"p01": M.p01(find(carriage, "P01_")), "p21": U.sealed_p21(relieved), "p22": built["beacon"][0]}
    return parts, built["cartographer"][0], built["beacon"][1], {
        "user": user, "relieved": relieved, "exchange": exchange}


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
    report["print_pose_warning"] = "Do not use the P22 inlet-face-down pose with the assessed supports."


def geometry():
    OUTPUT.mkdir(exist_ok=True)
    manifest, carriage, tools = read_source()
    parts, cart, construction, inputs = build(carriage)
    base = {"p01": find(carriage, "P01_"), "p21": find(carriage, "P21_"),
            "p22": cq.Shape.importBrep(str(BASELINE / "p22_swept_beacon.brep"))}
    cable = find(carriage, "Probe_Cable")
    hardware = dict(M.hardware())
    added, removed = {}, {}
    report = {
        "status": "GEOMETRY_AUDIT_IN_PROGRESS",
        "scope": "Bambu only; separate user-post retainer review. R43 and the fork study are unchanged.",
        "source_sha256": {p: digest(ROOT / p) for p in (
            "r43_c28_mechanical.py", "r43_c28_user_joint.py", "audit_c28_user_retainer_r43.py")},
        "user_p21_snapshot": {"step": str(USER_STEP), "sha256": USER_STEP_SHA256,
                              "fusion_document": "53 Bambu C28 - angled mounts and lower retainer",
                              "exchange_repair": inputs["exchange"]},
        "frozen_scene_manifest_sha256": digest(SOURCE / "manifest.json"),
        "frozen_c28_beacon_sha256": digest(BASELINE / "p22_swept_beacon.brep"),
        "user_p21_tweaks_mm3": {
            "lower_rear_side_relief_removed": inputs["user"].cut(inputs["relieved"]).Volume(),
            "rear_seal_skirt_added": parts["p21"].cut(inputs["relieved"]).Volume(),
            "upper_post_unchanged_above_z": U.RELIEF_TOP,
        },
        "parts": {}, "interfaces": [], "exports_sha256": {},
        "limitations": [
            "No physical strength, torque, heat, sealing or print-fit qualification.",
            "The seal is nominal face contact in the existing sleeve-bottom plane; the printed fit needs a bench check.",
            "Sampled service/movement paths are recorded separately from static fit.",
            "Fasteners use nominal head/shank envelopes; heat-set knurls are not modelled.",
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
        assert row["new_material_cable_gap_mm"] >= .45 - 1e-6, (key, row["new_material_cable_gap_mm"])
        for suffix, shape in (("", body), ("_added", added[key]), ("_removed", removed[key])):
            shape.exportBrep(str(OUTPUT / f"{key}{suffix}.brep"))
        report["parts"][key] = row
        print("part", key, json.dumps(row), flush=True)
    for key, body in construction.items():
        body.exportBrep(str(OUTPUT / f"construction_{key}.brep"))
    build_manifest = {
        "generator_sha256": digest(ROOT / "r43_c28_user_joint.py"),
        "mechanical_generator_sha256": digest(ROOT / "r43_c28_mechanical.py"),
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
    rings["post_insert_1p2mm_wall_fraction"] = ring_fraction(
        parts["p21"], M.cylinder(0, M.RETAINER_Y, -64.95, -61.05, M.INSERT_R + 1.2),
        M.cylinder(0, M.RETAINER_Y, -65, -61, M.INSERT_R))
    assert min(rings.values()) > .999, rings
    report["insert_walls"] = rings

    unchanged = {n: s for n, s in carriage.items() if not n.startswith(REPLACED)}
    hits = []
    for an, a in {**added, **hardware}.items():
        for bn, b in {**unchanged, **tools}.items():
            if (volume := quick_overlap(a, b)) > 1e-4:
                hits.append({"new": an, "other": bn, "mm3": volume})
    assert not hits, hits
    report["new_material_hardware_vs_unchanged_and_bambu_mm3"] = hits
    tool_index = fg.index_group(list(tools.items()))
    report["head_to_mounted_bambu_mm"] = {}
    for name, body in hardware.items():
        if "BUTTON" in name:
            hit = fg.min_distance(fg.index_group([(name, body)]), tool_index, cutoff=30)
            assert hit is None or hit[0] >= 3, (name, hit)
            report["head_to_mounted_bambu_mm"][name] = (
                {"mm": hit[0], "part": hit[2]} if hit else {"greater_than_mm": 30})
    report["driver_access"] = {}
    for name, gauge in driver_gauges().items():
        checked = {**parts, **unchanged, **tools}
        collisions = {n: v for n, b in checked.items() if (v := quick_overlap(gauge, b)) > 1e-4}
        assert not collisions, (name, collisions)
        report["driver_access"][name] = {"clear": True, "shaft_diameter_mm": 5, "straight_reach_mm": 35}

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
            "metal_in_bottom_keepout_mm3": require_no_overlap(compound(hardware.values()), ko["bottom"],
                                                              f"{name}/bottom"),
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
    mount_zones = compound([M.box(x - 4.5, x + 4.5, 11.19, 20, -58.5, -49) for x in M.MOUNT_X])
    p01_outside = added["p01"].cut(mount_zones).Volume() + removed["p01"].cut(mount_zones).Volume()
    assert p01_outside < 1e-4, p01_outside
    report["p01_changes_outside_mount_zones_mm3"] = p01_outside

    clean_air = F.main_channel_air().cut(base["p22"]).cut(base["p21"])
    after_air = F.main_channel_air().cut(parts["p22"]).cut(parts["p21"])
    cavity = duct_cavity(parts["p21"], parts["p22"])
    assert cavity["sealed_inside_carriage"], cavity
    report["air_changes"] = {
        "duct_cavity_after": cavity, "duct_cavity_baseline_mm3": BASELINE_DUCT_AIR_MM3,
        "duct_air_change_mm3": cavity["volume_mm3"] - BASELINE_DUCT_AIR_MM3,
        "new_material_in_clean_c28_channel_mm3": {
            "p21": parts["p21"].intersect(clean_air).Volume(), "p22": parts["p22"].intersect(clean_air).Volume()},
        "front_opening_gap_to_remaining_channel_mm": construction["front_opening"].distance(after_air),
        "front_opening_overlap_with_original_channel_corridor_mm3":
            construction["front_opening"].intersect(F.main_channel_air()).Volume(),
        "note": "The post and receiver occupy part of the clean C28 channel. The duct remains closed: "
                "the skirt lands on the receiver top in the original sleeve-bottom plane and a dam closes "
                "the sleeve slot beside the socket. CFD is reported separately.",
    }
    assert report["air_changes"]["front_opening_overlap_with_original_channel_corridor_mm3"] < 1e-4
    assert report["air_changes"]["front_opening_gap_to_remaining_channel_mm"] >= 1.0
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
        "downward_release_mm": 18, "sample_step_mm": .25, "samples": 73, "collisions": service,
        "sequence": "Park/remove the Bambu tool, raise clear of the bed, free the probe lead, remove both "
                    "angled mount screws and the underside retainer screw, lower P22 18 mm. P21 and EBB42 stay.",
    }
    report["cartographer_mesh"] = mesh_check(cart)
    require_no_overlap(cart, probes["Cartographer"], "Cartographer-seat P22/probe")
    require_no_overlap(cart, parts["p21"], "Cartographer P22/P21")
    cart.exportBrep(str(OUTPUT / "p22_cartographer.brep"))
    report["cartographer_brep_sha256"] = digest(OUTPUT / "p22_cartographer.brep")
    report["status"] = "STATIC_AND_SERVICE_VERIFIED_EXPORTS_PENDING"
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    return export_review(parts, cart, hardware, cable, carriage, tools, report)


def export_review(parts, cart, hardware, cable, carriage, tools, report):
    report["step_roundtrips"] = {"p01_existing_export": carriage_step_roundtrip(
        parts["p01"], cq.importers.importStep(str(P01_STEP)).val())}
    report["exports_sha256"][str(P01_STEP.relative_to(ROOT))] = digest(P01_STEP)
    for key, body in {"p21": parts["p21"], "p22": parts["p22"], "cartographer": cart}.items():
        step = ROOT / "step" / f"{NAMES[key]}.step"
        cq.exporters.export(body, str(step))
        restored = cq.importers.importStep(str(step)).val()
        assert restored.isValid() and len(restored.Solids()) == 1, key
        report["step_roundtrips"][key] = step_roundtrip(body, restored)
        report["exports_sha256"][str(step.relative_to(ROOT))] = digest(step)
        print("STEP", key, json.dumps({k: v for k, v in report["step_roundtrips"][key].items()
                                       if k != "method"}), flush=True)
    export_prints({"p21": parts["p21"], "p22": parts["p22"], "cartographer": cart}, report)
    assembly = cq.Assembly(name="C28_Bambu_User_Post_Retainer_REVIEW")
    colors = {"p01": (.36, .44, .54), "p21": (.94, .55, .18), "p22": (.08, .58, .72)}
    labels = {"p01": "P01_C28_Bambu_45deg_Mounts_REVIEW", **NAMES}
    for n, p in parts.items():
        assembly.add(p, name=labels[n], color=cq.Color(*colors[n]))
    for n, p in hardware.items():
        assembly.add(p, name=n, color=cq.Color(*((.72, .52, .23) if "HEATSET" in n else (.42, .45, .49))))
    assembly.add(cable, name="Probe_cable_reference", color=cq.Color(.65, .25, .48))
    assembly.add(find(carriage, "Beacon_"), name="Beacon_reference", color=cq.Color(.2, .22, .25))
    for n, p in tools.items():
        assembly.add(p, name=f"Bambu_{n.replace(' ', '_')}", color=cq.Color(.53, .55, .57))
    assembly.save(str(ASSEMBLY))
    report["exports_sha256"][str(ASSEMBLY.relative_to(ROOT))] = digest(ASSEMBLY)
    report["exports_audit_sha256"] = digest(__file__)
    report["status"] = "STATIC_GEOMETRY_SEAL_EXPORT_AND_SERVICE_PATH_VERIFIED_REVIEW_ONLY"
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(report["status"], flush=True)
    return report


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    geometry()


if __name__ == "__main__":
    main()
