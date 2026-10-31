"""Audit the separate C28 feed-roof cleanup against its frozen CFD predecessor.

Requires saved session geometry under WORK/swept_feed. Does not modify reference
BREPs or the released R43. Produces review STEP files and a geometric audit, not
manufacturing, strength or thermal qualification.
"""
import hashlib
import json

import cadquery as cq
import numpy as np
import trimesh

import build_and_verify_accessories_v26 as acc
import r43_swept_feed as R
from audit_tool_owned_2510 import bounds
from build_modular_toolhead import ROOT

BEFORE = acc.WORK / "swept_feed" / "optC28_conformal"
AFTER = acc.WORK / "swept_feed" / "optC28_clean"
REPORT = ROOT / "verification_swept_feed_cleanup_r43.json"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def mesh(shape):
    vertices, triangles = shape.tessellate(.005, .05)
    return trimesh.Trimesh([v.toTuple() for v in vertices], triangles, process=True)


def inside(shape, point):
    return any(s.isInside(cq.Vector(*point), 1e-6) for s in shape.Solids())


def wall_screen(part, air, channel):
    material, passage = mesh(part), mesh(air)
    keep = R.mouth_keep(28)
    centres = passage.triangles_center
    endpoints = np.array([R.mouth(float(np.clip(p[0], -10, 10))).toTuple() for p in centres])
    open_end = np.einsum(
        "ij,j->i", centres - endpoints, R.outlet_axes(28)[0].toTuple()) > -.02
    channel_mesh, keep_mesh = mesh(channel), mesh(keep)
    rows = []
    for offset in (.1, .35, .6, .75):
        samples = centres + passage.face_normals * offset
        eligible = (~open_end & keep_mesh.contains(samples) & ~channel_mesh.contains(samples)
                    & ~passage.contains(samples))
        suspects = samples[eligible][~material.contains(samples[eligible])]
        failures = [p.tolist() for p in suspects
                    if inside(keep, p) and not inside(channel, p)
                    and not inside(air, p) and not inside(part, p)]
        if failures:
            raise ValueError(f"Missing material {offset} mm from air surface: {failures[:10]}")
        rows.append({"offset_mm": offset, "samples": int(eligible.sum()),
                     "mesh_suspects": len(suspects), "exact_failures": len(failures)})
    if not material.is_watertight or not material.is_winding_consistent:
        raise ValueError("Export tessellation is not watertight with consistent winding")
    return {"watertight": True, "winding_consistent": True, "normal_samples": rows,
            "limitation": "Sampled wall-normal material, not a continuous minimum-thickness proof. "
                          "Open main-channel connections and the outlet are excluded by exact CAD."}


def section_areas(before, after, channel):
    rows = []
    for y in (-10.0, -9.0, -8.0, -7.0, -6.0, -5.0, -4.0):
        for side in (-1, 1):
            x0, x1 = (-23, 0) if side < 0 else (0, 23)
            slab = cq.Solid.makeBox(x1 - x0, .02, 33, cq.Vector(x0, y - .01, -80))
            intended = channel.intersect(slab)
            area = intended.Volume() / .02
            old = area - intended.intersect(before).Volume() / .02
            new = area - intended.intersect(after).Volume() / .02
            rows.append({"side": side, "y_mm": y, "original_channel_mm2": area,
                         "before_open_mm2": old, "after_open_mm2": new,
                         "area_recovered_mm2": new - old})
    return rows


def main():
    qualification = json.loads((AFTER / "qualification.json").read_text())
    if not qualification["geometry_checks_pass"] or not qualification["full_height_feed_clearance"]:
        raise ValueError("The cleaned variant has not passed its geometry qualification")
    channel = R.main_channel_air()
    old_air = cq.Shape.importBrep(str(BEFORE / "swept_air.brep"))
    air = cq.Shape.importBrep(str(AFTER / "swept_air.brep"))
    air_change = {"added_mm3": air.cut(old_air).Volume(), "removed_mm3": old_air.cut(air).Volume()}
    if max(air_change.values()) > 1e-5:
        raise ValueError(f"Cleanup unexpectedly changed the nominal swept-air cutter: {air_change}")
    base = cq.Shape.importBrep(str(acc.WORK / "cfd" / "p22_r43.brep"))
    frozen = cq.Shape.importBrep(str(BEFORE / "p22_swept_beacon.brep"))
    historical = R.p22(base, "Beacon", roof_raise=3, mouth_height=.9, angle_deg=28,
                       remove_rear_mounts=True, conformal_outlet=True)
    default_difference = {"new_only_mm3": historical.cut(frozen).Volume(),
                          "reference_only_mm3": frozen.cut(historical).Volume()}
    if max(default_difference.values()) > 1e-4:
        raise ValueError(f"The default flag changed historical C28 geometry: {default_difference}")
    zones = cq.Compound.makeCompound([
        cq.Solid.makeBox(8, 8, 2, cq.Vector(x, -12, -60.01)) for x in (-20, 12)])
    report = {
        "status": "SEPARATE_GEOMETRY_CLEANUP_VERIFIED_NOT_PRINT_OR_THERMALLY_QUALIFIED",
        "parameters": {"roof_raise_mm": 3, "mouth_height_mm": .9, "angle_deg": 28,
                       "remove_rear_mounts": True, "conformal_outlet": True,
                       "clear_feed_intrusions": True},
        "root_cause": "The inherited rear-jet duct_air() clearance was limited to Z-80..-60. "
                      "Raised swept feeds extend above Z-60, leaving their outer roofs in the "
                      "existing side channels. Clip only the new envelope against full-height "
                      "channel air; preserve the original duct and its cable-support rib.",
        "nominal_swept_air_cutter_difference": air_change,
        "historical_default_regression": default_difference,
        "frozen_c28_geometry_unchanged": True,
        "released_r43_brep_sha256": digest(acc.WORK / "cfd" / "p22_r43.brep"),
        "variants": {}, "inputs_sha256": {}, "outputs_sha256": {},
        "limitations": "The connected fluid domain changes even though the nominal swept-air "
                      "cutter does not. Old CFD cannot be relabelled as cleaned-geometry CFD. "
                      "Mount strength, tolerances, thermal behavior and slicing are not qualified.",
    }
    for name in ("Beacon", "Cartographer"):
        filename = f"p22_swept_{name.lower()}.brep"
        before = cq.Shape.importBrep(str(BEFORE / filename))
        after = cq.Shape.importBrep(str(AFTER / filename))
        removed, added = before.cut(after), after.cut(before)
        if not after.isValid() or len(after.Solids()) != 1 or len(after.Shells()) != 1:
            raise ValueError(f"{name}: not one valid solid/shell")
        if added.Volume() > 1e-4 or removed.cut(zones).Volume() > 1e-4:
            raise ValueError(f"{name}: modification escaped the two feed-entry regions")
        if not 47.8 < removed.Volume() < 48.1 or len(removed.Solids()) != 2:
            raise ValueError(f"{name}: unexpected feed-roof removal")
        if removed.intersect(base).Volume() > 1e-4:
            raise ValueError(f"{name}: cleanup removed released duct material")
        if removed.cut(channel).Volume() > 1e-4:
            raise ValueError(f"{name}: cleanup removed material outside original channel air")
        if after.intersect(zones).intersect(channel).Volume() > 1e-4:
            raise ValueError(f"{name}: a feed-roof remnant is still in the channel")
        if after.intersect(air).Volume() > 1e-4:
            raise ValueError(f"{name}: swept passage obstruction")
        rib = R.R43.cable_rib()
        rib_difference = before.intersect(rib).cut(after).Volume()
        if rib_difference > 1e-4:
            raise ValueError(f"{name}: original cable-support rib was modified")
        removed.exportBrep(str(AFTER / f"removed_feed_roofs_{name.lower()}.brep"))
        export = ROOT / "step" / f"P22_Swept_C28_Clean_Feed_{name}_REVIEW.step"
        cq.exporters.export(after, str(export))
        restored = cq.importers.importStep(str(export)).val()
        roundtrip = max(after.cut(restored).Volume(), restored.cut(after).Volume())
        if not restored.isValid() or len(restored.Solids()) != 1 or roundtrip > 1e-4:
            raise ValueError(f"{name}: STEP round trip changed the part")
        report["variants"][name] = {
            "before_volume_mm3": before.Volume(), "after_volume_mm3": after.Volume(),
            "removed_mm3": removed.Volume(), "added_mm3": added.Volume(),
            "removed_regions": [{"volume_mm3": s.Volume(), "bounds_mm": bounds(s)}
                                for s in removed.Solids()],
            "valid_single_solid_shell": True,
            "faces_before_after": [len(before.Faces()), len(after.Faces())],
            "small_faces_under_0_01_mm2_before_after": [
                sum(f.Area() < .01 for f in p.Faces()) for p in (before, after)],
            "released_material_removed_mm3": removed.intersect(base).Volume(),
            "cable_support_rib_removed_mm3": rib_difference,
            "step_roundtrip_max_difference_mm3": roundtrip,
            "wall_screen": wall_screen(after, air, channel),
        }
        if name == "Beacon":
            report["main_channel_cross_sections"] = section_areas(before, after, channel)
        for folder in (BEFORE, AFTER):
            path = folder / filename
            report["inputs_sha256"][str(path)] = digest(path)
        report["outputs_sha256"][str(export.relative_to(ROOT))] = digest(export)
        print(name, json.dumps(report["variants"][name]), flush=True)
    report["generator_sha256"] = digest(ROOT / "r43_swept_feed.py")
    report["audit_sha256"] = digest(ROOT / "audit_swept_feed_cleanup_r43.py")
    REPORT.write_text(json.dumps(report, indent=2) + "\n")
    print(REPORT, flush=True)


if __name__ == "__main__":
    main()
