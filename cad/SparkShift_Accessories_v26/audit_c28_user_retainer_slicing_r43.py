"""Compare saved matched H2D slices of the C28 user-post retainer with the original and fork-study parts.

Run audit_c28_user_retainer_r43.py first. Each sliced input is checked against the audited part.
"""
import json
from pathlib import PureWindowsPath

import cadquery as cq

from audit_c28_mechanical_r43 import ROOT, acc, bounds, digest
from audit_c28_user_retainer_r43 import OUTPUT

FOLDER = acc.WORK / "printability_swept"
SCREENS = acc.WORK / "swept_feed" / "userP21_matched_v4"
RUNS = {
    "P01_back_down": ("c28_original_p01_back", "c28_mechanical_p01_back", "c28_mechanical_p01_back"),
    "P21_top_down": ("c28_original_p21_top", "c28_mechanical_p21_top", "c28_user_p21_top_v4"),
    "P22_back_down": ("c28_baseline_auto", "c28_mechanical_back", "c28_user_p21_receiver_back_v4"),
}
PART = {"P01_back_down": "p01", "P21_top_down": "p21", "P22_back_down": "p22"}
VERSIONS = ("original", "fork_study", "user_post")
SETTINGS = ["machine.json", "process.json"] + [f"filament{i}.json" for i in range(1, 9)]
KEYS = ("support_deposition_volume_mm3", "total_estimated_time_s")


def work_path(recorded):
    """Recorded slicer inputs use the original workstation's absolute WORK path."""
    parts = PureWindowsPath(recorded).parts
    return acc.WORK.joinpath(*parts[len(parts) - 1 - parts[::-1].index("files") + 1:])


def same_geometry(a_path, b_path):
    a, b = cq.Shape.importBrep(str(a_path)), cq.Shape.importBrep(str(b_path))
    row = {"faces": [len(a.Faces()), len(b.Faces())],
           "volume_mm3_difference": abs(a.Volume() - b.Volume()),
           "area_mm2_difference": abs(a.Area() - b.Area()),
           "bounds_mm_difference": max(abs(x - y) for x, y in zip(bounds(a), bounds(b)))}
    assert row["faces"][0] == row["faces"][1], row
    assert max(row[k] for k in ("volume_mm3_difference", "area_mm2_difference", "bounds_mm_difference")) < 1e-6, row
    return row


def pct(after, before):
    return {k: 100 * (after[k] / before[k] - 1) for k in KEYS}


def main():
    reference = FOLDER / RUNS["P22_back_down"][0]
    comparisons = {}
    for label, runs in RUNS.items():
        rows = {}
        for version, run in zip(VERSIONS, runs):
            folder = FOLDER / run
            for filename in SETTINGS:
                assert json.loads((folder / filename).read_text()) == json.loads((reference / filename).read_text()), (
                    run, filename, "Settings changed")
            metrics = json.loads((folder / "support_metrics.json").read_text())
            rows[version] = {"run": run, **{k: metrics[k] for k in KEYS},
                             "support_metrics_sha256": digest(folder / "support_metrics.json"),
                             "input": metrics["input_brep"]}
        user_input = work_path(rows["user_post"]["input"])
        comparisons[label] = {
            **rows,
            "identical_machine_process_and_all_filaments": True,
            "user_post_vs_original_pct": pct(rows["user_post"], rows["original"]),
            "user_post_vs_fork_study_pct": pct(rows["user_post"], rows["fork_study"]),
            "sliced_input_matches_audited_part": same_geometry(user_input, OUTPUT / f"{PART[label]}.brep"),
        }
    totals = {v: {k: sum(comparisons[label][v][k] for label in RUNS) for k in KEYS} for v in VERSIONS}
    totals["user_post_vs_original_pct"] = pct(totals["user_post"], totals["original"])
    totals["user_post_vs_fork_study_pct"] = pct(totals["user_post"], totals["fork_study"])
    rear = json.loads((SCREENS / "rear_passage_support_screen.json").read_text())
    receiver = json.loads((SCREENS / "receiver_support_screen.json").read_text())
    access = {
        "rear_passage_support_mm3": rear[RUNS["P22_back_down"][2]]["estimated_support_in_passage_mm3"],
        "receiver_socket_support_mm3": {
            "fork_study": receiver[RUNS["P22_back_down"][1]]["receiver_socket"]["support_mm3"],
            "user_post": receiver[RUNS["P22_back_down"][2]]["receiver_socket"]["support_mm3"]},
        "channel_air_near_receiver_support_mm3": {
            "fork_study": receiver[RUNS["P22_back_down"][1]]["remaining_channel_air_near_receiver"]["support_mm3"],
            "user_post": receiver[RUNS["P22_back_down"][2]]["remaining_channel_air_near_receiver"]["support_mm3"]},
        "screens_sha256": {p.name: digest(p) for p in (SCREENS / "rear_passage_support_screen.json",
                                                         SCREENS / "receiver_support_screen.json")},
        "limitation": "Sampled support centrelines, not bead-solid collision or proof of physical removability.",
    }
    p21, p22 = (comparisons[k]["user_post_vs_original_pct"]["support_deposition_volume_mm3"]
                for k in ("P21_top_down", "P22_back_down"))
    total = totals["user_post_vs_original_pct"]
    report = {
        "status": "MATCHED_SLICER_COMPARISON_COMPLETE_NOT_PRINT_QUALIFIED",
        "generator_sha256": digest(ROOT / "r43_c28_user_joint.py"),
        "printer": "H2D 0.4 mm, Generic ABS, Bambu Support for ABS interface, 0.2 mm layers, 5 walls",
        "poses": "P01 back down; P21 top down; P22 back down. The P22 inlet-face-down pose is not used.",
        "comparisons": comparisons, "three_separate_parts_total": totals, "support_access": access,
        "verdict": f"The user post moves support into P21 ({p21:+.1f}% vs the original P21) but the matched "
                   f"receiver lowers P22 support ({p22:+.1f}%). The three-part set changes support by "
                   f"{total['support_deposition_volume_mm3']:+.1f}% and total time by "
                   f"{total['total_estimated_time_s']:+.1f}% against the original C28 parts, while adding "
                   "positive mid/lower retention. It is not a whole-set support reduction.",
        "limitations": "Slicer prediction only. Support excludes prime tower/waste. No physical print or "
                       "machine G-code approval. Global profiles and printer were not changed.",
    }
    (ROOT / "verification_c28_user_retainer_slicing_r43.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"parts": {k: v["user_post_vs_original_pct"] for k, v in comparisons.items()},
                      "total": totals, "access": {k: v for k, v in access.items() if k != "screens_sha256"}},
                     indent=2))


if __name__ == "__main__":
    main()
