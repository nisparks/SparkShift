"""Compare saved matched H2D slices, including support displaced into P01/P21."""
import json

from audit_c28_mechanical_r43 import ROOT, acc, digest

FOLDER = acc.WORK / "printability_swept"
PAIRS = {
    "P01_back_down": ("c28_original_p01_back", "c28_mechanical_p01_back"),
    "P21_top_down": ("c28_original_p21_top", "c28_mechanical_p21_top"),
    "P22_back_down": ("c28_baseline_auto", "c28_mechanical_back"),
    "P22_inlet_down": ("c28_inlet_face_baseline", "c28_mechanical_inlet_face"),
}


def main():
    comparisons = {}
    settings = ["machine.json", "process.json"] + [f"filament{i}.json" for i in range(1, 9)]
    for label, (old, new) in PAIRS.items():
        old, new = FOLDER / old, FOLDER / new
        for filename in settings:
            assert json.loads((old / filename).read_text()) == json.loads((new / filename).read_text()), (
                label, filename, "Settings changed")
        before, after = [json.loads((p / "support_metrics.json").read_text()) for p in (old, new)]
        row = {
            "before": {k: before[k] for k in ("support_deposition_volume_mm3", "total_estimated_time_s")},
            "after": {k: after[k] for k in ("support_deposition_volume_mm3", "total_estimated_time_s")},
            "identical_machine_process_and_all_filaments": True,
            "percent_change": {k: 100 * (after[k] / before[k] - 1)
                               for k in ("support_deposition_volume_mm3", "total_estimated_time_s")},
            "source_sha256": {f"{p.name}/{name}": digest(p / name) for p in (old, new)
                              for name in ("support_metrics.json", "model_print_oriented.stl", "sliced.3mf")},
        }
        comparisons[label] = row
    assembly = {}
    for version in ("before", "after"):
        assembly[version] = {
            k: sum(comparisons[label][version][k] for label in ("P01_back_down", "P21_top_down", "P22_back_down"))
            for k in ("support_deposition_volume_mm3", "total_estimated_time_s")}
    assembly["percent_change"] = {
        k: 100 * (assembly["after"][k] / assembly["before"][k] - 1) for k in assembly["before"]}
    report = {
        "status": "MATCHED_SLICER_COMPARISON_COMPLETE_NOT_PRINT_QUALIFIED",
        "generator_sha256": digest(ROOT / "r43_c28_mechanical.py"),
        "printer": "H2D 0.4 mm, Generic ABS, Bambu Support for ABS interface, 0.2 mm layers, 5 walls",
        "comparisons": comparisons, "three_separate_parts_total": assembly,
        "verdict": "Positive retention is added, but this is not yet a whole-assembly support reduction. "
                   "The mid-duct tongue adds more support than the inclined mounts save. "
                   "P22 back-down remains lower-support than inlet-face-down in these controlled runs.",
        "limitations": "Slicer prediction only. Support excludes prime tower/waste. No physical print or "
                      "machine G-code approval. Global profiles and printer were not changed.",
    }
    (ROOT / "verification_c28_mechanical_slicing_r43.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"parts": {k: v["percent_change"] for k, v in comparisons.items()},
                      "total": assembly}, indent=2))


if __name__ == "__main__":
    main()
