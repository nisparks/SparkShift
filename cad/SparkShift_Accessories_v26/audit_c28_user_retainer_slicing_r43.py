"""Compare saved matched H2D slices of a C28 user-post retainer with the original and earlier retainer parts.

Run the matching geometry audit first (audit_c28_user_retainer_r43.py, or audit_c28_flow_neutral_retainer_r43.py
with --variant flow-neutral). Each sliced input is checked against the audited part.
"""
import argparse
import json
from pathlib import PureWindowsPath

import cadquery as cq

from audit_c28_mechanical_r43 import ROOT, acc, bounds, digest

FOLDER = acc.WORK / "printability_swept"
SETTINGS = ["machine.json", "process.json"] + [f"filament{i}.json" for i in range(1, 9)]
KEYS = ("support_deposition_volume_mm3", "total_estimated_time_s")
PART = {"P01_back_down": "p01", "P21_top_down": "p21", "P22_back_down": "p22"}
VARIANTS = {
    "sealed": {
        "output": "optC28_user_retainer", "screens": "userP21_matched_v4",
        "report": "verification_c28_user_retainer_slicing_r43.json",
        "versions": ("original", "fork_study", "user_post"), "previous": "fork_study",
        "runs": {
            "P01_back_down": ("c28_original_p01_back", "c28_mechanical_p01_back", "c28_mechanical_p01_back"),
            "P21_top_down": ("c28_original_p21_top", "c28_mechanical_p21_top", "c28_user_p21_top_v4"),
            "P22_back_down": ("c28_baseline_auto", "c28_mechanical_back", "c28_user_p21_receiver_back_v4"),
        },
    },
    "flow-neutral": {
        "output": "optC28_flow_neutral_retainer", "screens": "userP21_flow_neutral_v5d",
        "report": "verification_c28_flow_neutral_retainer_slicing_r43.json",
        "versions": ("original", "fork_study", "sealed_user_post", "flow_neutral"), "previous": "sealed_user_post",
        "runs": {
            "P01_back_down": ("c28_original_p01_back", "c28_mechanical_p01_back", "c28_mechanical_p01_back",
                              "c28_mechanical_p01_back"),
            "P21_top_down": ("c28_original_p21_top", "c28_mechanical_p21_top", "c28_user_p21_top_v4",
                             "c28_flow_neutral_v5d_p21_top"),
            "P22_back_down": ("c28_baseline_auto", "c28_mechanical_back", "c28_user_p21_receiver_back_v4",
                              "c28_flow_neutral_v5d_receiver_back"),
        },
    },
}


def work_path(recorded):
    """Recorded slicer inputs are absolute WORK paths from the original workstation, or WORK-relative."""
    parts = PureWindowsPath(recorded).parts
    if "files" not in parts:
        return acc.WORK.joinpath(*parts)
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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variant", choices=sorted(VARIANTS), default="sealed")
    config = VARIANTS[parser.parse_args().variant]
    output = acc.WORK / "swept_feed" / config["output"]
    screens = acc.WORK / "swept_feed" / config["screens"]
    runs_by_part, versions = config["runs"], config["versions"]
    subject, previous = versions[-1], config["previous"]
    reference = FOLDER / runs_by_part["P22_back_down"][0]
    comparisons = {}
    for label, runs in runs_by_part.items():
        rows = {}
        for version, run in zip(versions, runs):
            folder = FOLDER / run
            for filename in SETTINGS:
                assert json.loads((folder / filename).read_text()) == json.loads((reference / filename).read_text()), (
                    run, filename, "Settings changed")
            metrics = json.loads((folder / "support_metrics.json").read_text())
            rows[version] = {"run": run, **{k: metrics[k] for k in KEYS},
                             "support_metrics_sha256": digest(folder / "support_metrics.json"),
                             "input": metrics["input_brep"]}
        comparisons[label] = {
            **rows,
            "identical_machine_process_and_all_filaments": True,
            f"{subject}_vs_original_pct": pct(rows[subject], rows["original"]),
            f"{subject}_vs_{previous}_pct": pct(rows[subject], rows[previous]),
            "sliced_input_matches_audited_part": same_geometry(work_path(rows[subject]["input"]),
                                                               output / f"{PART[label]}.brep"),
        }
    totals = {v: {k: sum(comparisons[label][v][k] for label in runs_by_part) for k in KEYS} for v in versions}
    totals[f"{subject}_vs_original_pct"] = pct(totals[subject], totals["original"])
    totals[f"{subject}_vs_{previous}_pct"] = pct(totals[subject], totals[previous])
    back_runs = runs_by_part["P22_back_down"]
    rear = json.loads((screens / "rear_passage_support_screen.json").read_text())
    receiver = json.loads((screens / "receiver_support_screen.json").read_text())
    named = dict(zip(versions, back_runs))
    access = {
        "rear_passage_support_mm3": rear[back_runs[-1]]["estimated_support_in_passage_mm3"],
        "receiver_socket_support_mm3": {v: receiver[r]["receiver_socket"]["support_mm3"] for v, r in named.items()
                                        if "receiver_socket" in receiver.get(r, {})},
        "channel_air_near_receiver_support_mm3": {
            v: receiver[r]["remaining_channel_air_near_receiver"]["support_mm3"] for v, r in named.items()
            if r in receiver},
        "screens_sha256": {p.name: digest(p) for p in (screens / "rear_passage_support_screen.json",
                                                         screens / "receiver_support_screen.json")},
        "limitation": "Sampled support centrelines, not bead-solid collision or proof of physical removability.",
    }
    p21, p22 = (comparisons[k][f"{subject}_vs_original_pct"]["support_deposition_volume_mm3"]
                for k in ("P21_top_down", "P22_back_down"))
    total = totals[f"{subject}_vs_original_pct"]
    report = {
        "status": "MATCHED_SLICER_COMPARISON_COMPLETE_NOT_PRINT_QUALIFIED",
        "generator_sha256": digest(ROOT / "r43_c28_user_joint.py"),
        "printer": "H2D 0.4 mm, Generic ABS, Bambu Support for ABS interface, 0.2 mm layers, 5 walls",
        "poses": "P01 back down; P21 top down; P22 back down. The P22 inlet-face-down pose is not used.",
        "comparisons": comparisons, "three_separate_parts_total": totals, "support_access": access,
        "verdict": f"Against the original C28 parts: P21 support {p21:+.1f}%, P22 {p22:+.1f}%; the three-part set "
                   f"changes support by {total['support_deposition_volume_mm3']:+.1f}% and total time by "
                   f"{total['total_estimated_time_s']:+.1f}% while adding positive mid/lower retention.",
        "limitations": "Slicer prediction only. Support excludes prime tower/waste. No physical print or "
                       "machine G-code approval. Global profiles and printer were not changed.",
    }
    (ROOT / config["report"]).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"parts": {k: v[f"{subject}_vs_original_pct"] for k, v in comparisons.items()},
                      "total": totals, "access": {k: v for k, v in access.items() if k != "screens_sha256"}},
                     indent=2))


if __name__ == "__main__":
    main()
