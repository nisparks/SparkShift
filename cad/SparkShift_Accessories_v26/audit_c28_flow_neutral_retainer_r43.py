"""Build and qualify the flow-neutral Bambu C28 user-post retainer (v5c), without changing R43 or earlier studies.

The user's Fusion P21 post is the input. It is trimmed to stay a skin plus slip inside the clean C28 duct walls,
except under P21's own cable boss (its wake) in the cable zone, where P22 adds a thin skin. P21's sleeve recess
is filled and P22's notch boss removed behind the sleeve face; P22's remaining bridge closes the sleeve slip.
For the back-down P22 print the skin carries a faired 45 deg keel behind the boss and the socket has 45 deg
bevels at the sleeve face (v5c); v5b, without them, needed support under those faces.
"""
import argparse
import json

import cadquery as cq
import numpy as np
import trimesh

import fast_geometry as fg
import r37_parts as P37
import r42_parts as P42
import r43_c28_mechanical as M
import r43_c28_user_joint as U
import r43_swept_feed as F
from audit_c28_mechanical_r43 import (
    BASELINE, REPLACED, ROOT, SOURCE, acc, bounds, carriage_step_roundtrip, compound, digest,
    driver_gauges, find, mesh_check, quick_overlap, read_source, require_no_overlap, ring_fraction)
from audit_c28_user_retainer_r43 import USER_STEP, USER_STEP_SHA256, step_roundtrip

OUTPUT = acc.WORK / "swept_feed" / "optC28_flow_neutral_retainer"
REPORT = ROOT / "verification_c28_flow_neutral_retainer_geometry_r43.json"
P01_STEP = ROOT / "step" / "P01_C28_Bambu_45deg_Mounts_REVIEW.step"
NAMES = {
    "p21": "P21_C28_Bambu_User_Post_Flow_Neutral_REVIEW",
    "p22": "P22_C28_Bambu_Flow_Neutral_Receiver_Beacon_REVIEW",
    "cartographer": "P22_C28_Bambu_Flow_Neutral_Receiver_Cartographer_REVIEW",
}
ASSEMBLY = ROOT / "step" / "55_C28_Bambu_User_Post_Flow_Neutral_REVIEW.step"


def p20():
    scene = dict(json.loads((acc.WORK / "r41_scene" / "manifest.json").read_text())["carriage"])
    return cq.Shape.importBrep(str(acc.WORK / "r41_scene" / scene["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW"]))


def build(carriage):
    assert digest(USER_STEP) == USER_STEP_SHA256, "User P21 snapshot changed"
    user, exchange = U.load_user_p21(USER_STEP)
    old21, inlet = find(carriage, "P21_"), p20()
    built = {}
    for probe in ("beacon", "cartographer"):
        angled = M.angled_p22(cq.Shape.importBrep(str(BASELINE / f"p22_swept_{probe}.brep")))
        air = U.clean_duct_air(inlet, old21, angled)
        built[probe] = (*U.flow_neutral_parts(user, old21, angled, air), air)
    p21, cart21 = built["beacon"][0], built["cartographer"][0]
    same = p21.cut(cart21).Volume() + cart21.cut(p21).Volume()
    assert same < 1e-4, ("Probe variants need different P21 posts", same)
    parts = {"p01": M.p01(find(carriage, "P01_")), "p21": p21, "p22": built["beacon"][1]}
    return parts, built["cartographer"][1], built["beacon"][2], {
        "user": user, "exchange": exchange, "clean_air": built["beacon"][3], "p20": inlet,
        "cartographer_clean_air": built["cartographer"][3]}


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


def post_sections(post):
    rows = {}
    for z in (-51.6, -52.5, -54.0, -55.5, -57.0, -58.0, -60.0, -63.0):
        rows[str(z)] = post.intersect(M.box(-12, 12, -45, -15, z - .01, z + .01)).Volume() / .02
    return rows


def geometry():
    OUTPUT.mkdir(exist_ok=True)
    manifest, carriage, tools = read_source()
    parts, cart, construction, inputs = build(carriage)
    clean_air = inputs["clean_air"]
    base = {"p01": find(carriage, "P01_"), "p21": find(carriage, "P21_"),
            "p22": M.angled_p22(cq.Shape.importBrep(str(BASELINE / "p22_swept_beacon.brep")))}
    cable = find(carriage, "Probe_Cable")
    hardware = dict(M.hardware())
    user_post = inputs["user"].cut(base["p21"])
    added, removed = {}, {}
    report = {
        "status": "GEOMETRY_AUDIT_IN_PROGRESS",
        "scope": "Bambu only; separate flow-neutral user-post retainer review. R43, the fork study and the "
                 "first user-post receiver are unchanged.",
        "source_sha256": {p: digest(ROOT / p) for p in (
            "r43_c28_mechanical.py", "r43_c28_user_joint.py", "audit_c28_flow_neutral_retainer_r43.py")},
        "user_p21_snapshot": {"step": str(USER_STEP), "sha256": USER_STEP_SHA256,
                              "fusion_document": "53 Bambu C28 - angled mounts and lower retainer",
                              "exchange_repair": inputs["exchange"]},
        "frozen_scene_manifest_sha256": digest(SOURCE / "manifest.json"),
        "frozen_c28_beacon_sha256": digest(BASELINE / "p22_swept_beacon.brep"),
        "parameters": {"p22_skin_mm": U.SKIN, "slip_mm": U.SLIP, "cable_zone_bottom_z": U.TOP_ZONE_Z,
                       "socket_inside_boss_back_mm": U.BACK_MARGIN, "cable_axis_y": U.CABLE_AXIS_Y,
                       "print_bevels": construction["print_bevels"], "skin_keel_flank_deg": 45,
                       "skin_keel_top_fairing_deg": 45, "skin_keel_fairing_height_mm": U.KEEL_FAIRING,
                       "socket_sleeve_face_bevel_deg": 45},
        "user_post_changes_mm3": {
            "user_post": user_post.Volume(), "kept_post": construction["post"].Volume(),
            "trimmed_from_user_post": user_post.cut(construction["post"]).Volume(),
            "added_by_rounded_channel_back": construction["post"].cut(user_post).Volume(),
            "p21_recess_fill": construction["recess_fill"].Volume(),
            "p22_notch_boss_removed": base["p22"].intersect(construction["notch_removal"]).Volume(),
            "p22_skin_added_under_p21_boss": construction["boss_shadow_skin"].Volume(),
            "p22_skin_keel_beyond_boss_wake": construction["skin_keel_beyond_boss_wake"].Volume(),
        },
        "post_plan_section_mm2": post_sections(construction["post"]),
        "user_post_plan_section_mm2": post_sections(user_post),
        "parts": {}, "interfaces": [], "exports_sha256": {},
        "limitations": [
            "No physical strength, torque, heat, sealing or print-fit qualification. Snug the retainer screw; "
            "its smallest post section is reported, not rated.",
            "Seals are nominal face contacts in the existing sleeve-bottom plane and at the notch-boss bridge, "
            "as in the clean joint; printed fit needs a bench check.",
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
        if isinstance(body, cq.Shape):
            body.exportBrep(str(OUTPUT / f"construction_{key}.brep"))
    clean_air.exportBrep(str(OUTPUT / "clean_duct_air.brep"))
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

    after_air = U.duct_air(inputs["p20"], parts["p21"], parts["p22"])
    b = bounds(after_air)
    sealed = b[0] > -39 and b[1] < 39 and b[2] > -69 and b[5] < 44
    assert sealed, b
    cart_air = U.duct_air(inputs["p20"], parts["p21"], cart)
    cb = bounds(cart_air)
    assert cb[0] > -39 and cb[1] < 39 and cb[2] > -69 and cb[5] < 44, cb
    z0 = U.TOP_ZONE_Z - U.SLIP - U.SKIN
    shadow = U.boss_shadow(z0, U.SEAL_Z)
    recess = construction["notch_removal"]
    keel = U.shadow_keel(z0, U.SEAL_Z)
    in_air = {k: parts[k].intersect(clean_air) for k in ("p21", "p22")}

    def outside(shape, *zones):
        """Volume of shape outside the zones; intersect-and-subtract avoids OCCT's null result for empty cuts."""
        return shape.Volume() - shape.intersect(zones[0].fuse(*zones[1:])).Volume()

    report["air_changes"] = {
        "duct_cavity_after": {"volume_mm3": after_air.Volume(), "bounds_mm": b, "sealed_inside_carriage": sealed},
        "duct_cavity_baseline_mm3": clean_air.Volume(),
        "duct_air_change_mm3": after_air.Volume() - clean_air.Volume(),
        "cartographer_duct_cavity_after_mm3": cart_air.Volume(),
        "cartographer_duct_air_change_mm3": cart_air.Volume() - inputs["cartographer_clean_air"].Volume(),
        "new_material_in_clean_duct_mm3": {k: v.Volume() for k, v in in_air.items()},
        "joint_recess_slip_gap_filled_mm3": in_air["p21"].intersect(recess).Volume(),
        "p22_skin_keel_beyond_boss_wake_mm3": outside(in_air["p22"], shadow, recess),
        "new_material_outside_boss_wake_and_skin_keel_mm3": {
            k: outside(v, shadow, recess, keel) for k, v in in_air.items()},
        "socket_to_remaining_duct_min_mm": construction["socket"].distance(after_air),
        "note": "The clean reference is the inlet-connected duct of P20, the released P21 and the angled clean "
                "C28 P22. The new material in it is P22's thin skin and post material under P21's own cable "
                "boss in the cable zone (its wake), the skin's faired 45 deg keel behind the boss (so the "
                "back-down print needs no plenum support), and the filled 0.06 mm dead-end slip gap around the "
                "removed notch boss inside P21's recess. CFD is reported separately.",
    }
    for k, v in report["air_changes"]["new_material_outside_boss_wake_and_skin_keel_mm3"].items():
        assert v < .01, (k, v)
    assert report["air_changes"]["p22_skin_keel_beyond_boss_wake_mm3"] < 40, report["air_changes"]
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
    assembly = cq.Assembly(name="C28_Bambu_User_Post_Flow_Neutral_REVIEW")
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
