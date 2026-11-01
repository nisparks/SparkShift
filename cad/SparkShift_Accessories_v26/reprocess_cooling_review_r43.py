"""Recompute the compared CFD cases, preserving historical JSON before the measurement corrections."""
import argparse
import json
import subprocess
import sys
import zipfile
from pathlib import Path

import cfd_cpap_r41 as C

DEFAULT_CASES = ["r43avgV5d_bambu_bed", "r43avgV5dRep_bambu_bed", "r43avgV5dRVM_bambu_bed",
                 "r43avgV5dRVMS_bambu_bed", "r43avgV5dRS20_bambu_bed", "r43avgV5dCH_bambu_bed"]


def reprocess(cases, seeds):
    root = Path(__file__).parent
    out = C.CFD.parent / "cooling_review"
    out.mkdir(exist_ok=True)
    for case in cases:
        results = C.results_dir(case)
        backup = results / "analysis_before_rd_review.zip"
        if not backup.exists():
            with zipfile.ZipFile(backup, "x", zipfile.ZIP_DEFLATED) as archive:
                for path in results.glob("*.json"):
                    archive.write(path, path.name)
        commands = []
        if not (results / "analysis_r43.json").exists():
            commands.append(["cfd_cpap_r43.py", "analyse", case])
        commands += [
            ["cfd_outlet_balance_r43.py", case, "--mean", "--seeds", str(seeds)],
            ["cfd_nozzle_focus_r43.py", case, str(out / f"{case}_focus.png")],
            ["cfd_tip_approach_r43.py", case, str(out / f"{case}_tip.png")],
            ["cfd_bead_zones_r43.py", case],
        ]
        for command in commands:
            print(case, command[0], flush=True)
            log = out / f"{case}_{Path(command[0]).stem}.log"
            with log.open("w") as stream:
                subprocess.run([sys.executable, *command], cwd=root, stdout=stream, stderr=subprocess.STDOUT,
                               check=True)
        report = json.loads((results / "outlet_balance_mean.json").read_text())
        zones = json.loads((results / "bead_zones.json").read_text())["zones"]["r 4 mm"]
        print(json.dumps({"case": case, "closure": report["measurement_closure"],
                          "outlets_at_180": {k: v["lpm"] for k, v in report["outlets"].items()},
                          "below_tip_own_zone_lpm": zones["all_path_in_zone_lpm"],
                          "all_air_path_score": zones["all_path_score"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("cases", nargs="*", default=DEFAULT_CASES)
    parser.add_argument("--seeds", type=int, default=1800)
    args = parser.parse_args()
    reprocess(args.cases, args.seeds)
