"""Verify the D11 roof-only slot trial against frozen cleaned C28; export review CAD."""
import json

import cadquery as cq

import r43_swept_feed as R
from audit_swept_feed_cleanup_r43 import acc, digest, wall_screen
from build_modular_toolhead import ROOT

BEFORE = acc.WORK / "swept_feed" / "optC28_clean"
AFTER = acc.WORK / "swept_feed" / "optD11_roof"


def main():
    old_q = json.loads((BEFORE / "qualification.json").read_text())
    new_q = json.loads((AFTER / "qualification.json").read_text())
    assert new_q["geometry_checks_pass"]
    assert new_q["mouth_height_mm"] == 1.1 and new_q["mouth_floor_reference_height_mm"] == .9
    for probe in ("Beacon", "Cartographer"):
        assert new_q["nozzle_to_probe_gap_mm"][probe] >= old_q["nozzle_to_probe_gap_mm"][probe] - .001
    old_nozzle = R.nozzle(False, 3, .9, 28, True)
    new_nozzle = R.nozzle(False, 3, 1.1, 28, True, .9)
    floors = [cq.Compound.makeCompound([f for f in p.Faces() if f.normalAt().z < -.8])
              for p in (old_nozzle, new_nozzle)]
    floor_delta = {"old_only_mm2": floors[0].cut(floors[1]).Area(),
                   "new_only_mm2": floors[1].cut(floors[0]).Area()}
    assert max(floor_delta.values()) < 1e-6
    assert old_nozzle.cut(new_nozzle).Volume() < 1e-5
    air = cq.Shape.importBrep(str(AFTER / "swept_air.brep"))
    zone = cq.Solid.makeBox(20, 13, 10, cq.Vector(-10, 3, -75))
    channel = R.main_channel_air()
    report = {
        "status": "GEOMETRY_PASSED_OUTLET_HEIGHT_EXPERIMENT_NOT_ADOPTED_OR_PRINT_QUALIFIED",
        "parameters": {"mouth_height_mm": 1.1, "floor_reference_height_mm": .9,
                       "angle_deg": 28, "roof_raise_mm": 3},
        "lower_wall_surface_difference": floor_delta,
        "nominal_projected_mouth_area_mm2": {"before": 18 * .9, "trial": 18 * 1.1},
        "nozzle_air_volume_mm3": {"before": old_nozzle.Volume(), "trial": new_nozzle.Volume()},
        "probe_gaps_mm": new_q["nozzle_to_probe_gap_mm"],
        "withdrawal": new_q["withdrawal"],
        "tradeoff": "The lower wall and probe gaps stay fixed. Red Lizard nominal clearance "
                    "decreases from 0.713 to 0.619 mm; tolerance/thermal allowance is not qualified.",
        "variants": {}, "outputs_sha256": {},
        "generator_sha256": digest(ROOT / "r43_swept_feed.py"),
        "limitations": "Geometric sampling and export checks, not print, strength or thermal validation. "
                      "CFD ranking must use the trial's own accepted results.",
    }
    for probe in ("Beacon", "Cartographer"):
        filename = f"p22_swept_{probe.lower()}.brep"
        before = cq.Shape.importBrep(str(BEFORE / filename))
        after = cq.Shape.importBrep(str(AFTER / filename))
        added, removed = after.cut(before), before.cut(after)
        outside = added.cut(zone).Volume() + removed.cut(zone).Volume()
        assert outside < 1e-4, (probe, outside)
        assert after.isValid() and len(after.Solids()) == len(after.Shells()) == 1
        assert after.intersect(air).Volume() < 1e-4
        export = ROOT / "step" / f"P22_Swept_D11_Fixed_Floor_{probe}_REVIEW.step"
        cq.exporters.export(after, str(export))
        restored = cq.importers.importStep(str(export)).val()
        roundtrip = max(after.cut(restored).Volume(), restored.cut(after).Volume())
        assert restored.isValid() and len(restored.Solids()) == 1 and roundtrip < 1e-4
        report["variants"][probe] = {
            "added_mm3": added.Volume(), "removed_mm3": removed.Volume(),
            "difference_outside_nozzle_region_mm3": outside,
            "step_roundtrip_max_difference_mm3": roundtrip,
            "wall_screen": wall_screen(after, air, channel),
            "before_brep_sha256": digest(BEFORE / filename),
            "trial_brep_sha256": digest(AFTER / filename),
        }
        report["outputs_sha256"][str(export.relative_to(ROOT))] = digest(export)
        print(probe, json.dumps(report["variants"][probe]), flush=True)
    base = cq.Shape.importBrep(str(acc.WORK / "cfd" / "p22_r43.brep"))
    rebuilt = R.p22(base, roof_raise=3, mouth_height=.9, angle_deg=28,
                    remove_rear_mounts=True, conformal_outlet=True, clear_feed_intrusions=True)
    frozen = cq.Shape.importBrep(str(BEFORE / "p22_swept_beacon.brep"))
    regression = {"new_only_mm3": rebuilt.cut(frozen).Volume(),
                  "reference_only_mm3": frozen.cut(rebuilt).Volume()}
    assert max(regression.values()) < 1e-4
    report["historical_default_regression"] = regression
    report["audit_sha256"] = digest(ROOT / "audit_swept_slot_height_r43.py")
    (ROOT / "verification_slot_height_geometry_r43.json").write_text(json.dumps(report, indent=2) + "\n")
    print("Fixed-floor slot-height audit passed", flush=True)


if __name__ == "__main__":
    main()
