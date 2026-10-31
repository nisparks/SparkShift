"""Verify the Bambu-focused low-support C28 against the frozen airflow baseline."""
import json

import cadquery as cq
import trimesh

import r43_swept_feed as R
from audit_swept_feed_cleanup_r43 import acc, digest, wall_screen
from audit_tool_owned_2510 import bounds
from build_cpap_outlet_r43 import print_oriented
from build_modular_toolhead import ROOT

BEFORE = acc.WORK / "swept_feed" / "optC28_clean"
AFTER = acc.WORK / "swept_feed" / "optC28_dfm"


def main():
    qualification = json.loads((AFTER / "qualification.json").read_text())
    assert qualification["geometry_checks_pass"] and qualification["hotend_scope"] == "Bambu only"
    old_air = cq.Shape.importBrep(str(BEFORE / "swept_air.brep"))
    air = cq.Shape.importBrep(str(AFTER / "swept_air.brep"))
    assert max(old_air.cut(air).Volume(), air.cut(old_air).Volume()) < 1e-5
    channel = R.main_channel_air()
    report = {
        "status": "GEOMETRY_VERIFIED_LOW_SUPPORT_C28_REVIEW",
        "hotend_scope": "Bambu only",
        "airflow_geometry": "0.9 mm rear slot, 28-degree aim, roof raised 3 mm, cleaned main-channel entries",
        "changes": ["45-degree rear-leg ramps", "45-degree relief-step chamfers",
                    "protected truncated-V notch in the direct-mount seat"],
        "rejected_change": "Reducing the existing upper-notch radius from 5 to 2 mm caused non-watertight "
                           "tessellation at its feed-envelope intersection. It is not in this candidate.",
        "nominal_air_cutter_unchanged": True, "variants": {}, "outputs_sha256": {},
        "source_sha256": {p: digest(ROOT / p) for p in ("r43_swept_feed.py", "r43_swept_printable.py")},
        "limitations": "Geometry and sampling only. External air boundaries change, so the existing CFD is "
                      "not automatically a result for this variant. Slicing and physical print checks are separate.",
    }
    for probe in ("Beacon", "Cartographer"):
        filename = f"p22_swept_{probe.lower()}.brep"
        before = cq.Shape.importBrep(str(BEFORE / filename))
        after = cq.Shape.importBrep(str(AFTER / filename))
        added, removed = after.cut(before), before.cut(after)
        assert after.isValid() and len(after.Solids()) == len(after.Shells()) == 1
        assert max(abs(a - b) for a, b in zip(bounds(before), bounds(after))) < 1e-4
        assert after.intersect(air).Volume() < 1e-4
        old_internal, new_internal = before.intersect(channel), after.intersect(channel)
        assert max(old_internal.cut(new_internal).Volume(), new_internal.cut(old_internal).Volume()) < 1e-4
        zones = [cq.Solid.makeBox(7, 7, 8, cq.Vector(x - 3.5, -.3 - 3.5, -76))
                 for x in (-15.8, 15.8)]
        zones += [cq.Solid.makeBox(10, .3, 17, cq.Vector(x, 15.8, -65))
                  for x in (-23, 13)]
        zones += [cq.Solid.makeBox(48, 16, 5, cq.Vector(-24, -46, -53))]
        interface_changes = [added.intersect(z).Volume() + removed.intersect(z).Volume() for z in zones]
        assert max(interface_changes) < 1e-4, (probe, interface_changes)
        outputs = {
            "step": ROOT / "step" / f"P22_C28_Bambu_Low_Support_{probe}_REVIEW.step",
            "stl": ROOT / "stl" / f"P22_C28_Bambu_Low_Support_{probe}_REVIEW_PRINT_ORIENTED.stl",
        }
        cq.exporters.export(after, str(outputs["step"]))
        restored = cq.importers.importStep(str(outputs["step"])).val()
        difference = max(after.cut(restored).Volume(), restored.cut(after).Volume())
        assert restored.isValid() and len(restored.Solids()) == 1 and difference < 1e-4
        cq.exporters.export(print_oriented(after), str(outputs["stl"]), tolerance=.025, angularTolerance=.08)
        mesh = trimesh.load_mesh(str(outputs["stl"]))
        assert mesh.is_watertight and mesh.is_winding_consistent
        row = {
            "added_mm3": added.Volume(), "removed_mm3": removed.Volume(),
            "same_outer_bounds": True, "main_channel_material_unchanged": True,
            "live_mount_and_inlet_region_changes_mm3": interface_changes,
            "step_roundtrip_max_difference_mm3": difference,
            "print_stl_watertight": True, "print_stl_triangles": len(mesh.faces),
            "wall_screen": wall_screen(after, air, channel),
            "before_brep_sha256": digest(BEFORE / filename),
            "after_brep_sha256": digest(AFTER / filename),
        }
        report["variants"][probe] = row
        report["outputs_sha256"].update({str(p.relative_to(ROOT)): digest(p) for p in outputs.values()})
        print(probe, json.dumps(row), flush=True)
    report["audit_sha256"] = digest(ROOT / "audit_swept_printable_r43.py")
    (ROOT / "verification_swept_printable_geometry_r43.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Low-support C28 geometry audit passed", flush=True)


if __name__ == "__main__":
    main()
