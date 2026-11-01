"""Content fingerprints for CFD inputs and derived results; never trust a cache by filename alone."""
import hashlib
import json
from pathlib import Path

import cfd_cpap_r41 as C


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def field_inputs(case):
    from cfd_cpap_r41_post import vtk_dir

    root = C.results_dir(case)
    paths = [root / "domain.json", root / "stages.json", vtk_dir(case, 1200) / "internal.vtu"]
    return {str(p.relative_to(root)): digest(p) for p in paths}


def focus_inputs(case):
    root = C.results_dir(case)
    return {
        **field_inputs(case),
        **{name: digest(root / name) for name in ("outlet_balance_mean.json", "outlet_streamlines_mean.vtp")},
        "cfd_nozzle_focus_r43.py": digest(Path(__file__).with_name("cfd_nozzle_focus_r43.py")),
    }


def require_current(stored, current, label):
    if stored != current:
        raise ValueError(f"{label}: missing or stale input fingerprints; regenerate this analysis")


def read_balance(case):
    root = C.results_dir(case)
    report = json.loads((root / "outlet_balance_mean.json").read_text())
    if report.get("analysis_version") != 2:
        raise ValueError(f"{case}: rerun cfd_outlet_balance_r43.py --mean with the geometry-aware outlet mask")
    require_current(report.get("analyser_sha256"), digest(Path(__file__).with_name("cfd_outlet_balance_r43.py")),
                    f"{case} outlet analysis code")
    require_current(report.get("field_inputs_sha256"), field_inputs(case), f"{case} outlet analysis")
    require_current(report.get("streamlines_sha256"), digest(root / "outlet_streamlines_mean.vtp"),
                    f"{case} streamlines")
    return report
