"""Retrospective source -> domain -> solve provenance audit. Does not alter historical CFD inputs."""
import json
from pathlib import Path

import cadquery as cq

import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
from build_modular_toolhead import ROOT
from cfd_provenance_r43 import digest


def main():
    base_path = C.CFD.parent / "swept_feed" / "userP21_flow_neutral_v5d" / "p22.brep"
    base = cq.Shape.importBrep(str(base_path))
    folders = sorted((C.CFD / "results").glob("r43avgV5d*"))
    base_meta = json.loads((C.results_dir("r43avgV5d_bambu_bed") / "domain.json").read_text())
    base_settings = json.loads((C.results_dir("r43avgV5d_bambu_bed") / "stages.json").read_text())
    rows = []
    for folder in folders:
        meta = json.loads((folder / "domain.json").read_text())
        case = C.CFD / "cases" / folder.name
        path = Path(meta["p22_variant"])
        part = cq.Shape.importBrep(str(path))
        if not part.isValid() or len(part.Solids()) != 1:
            raise ValueError(f"{folder.name}: invalid frozen P22")
        added, removed = part.copy().cut(base.copy()), base.copy().cut(part.copy())
        delta_valid = all(s.isValid() and all(v.Volume() >= -1e-5 for v in s.Solids()) for s in (added, removed))
        # Whole-solid volumes remain usable even when OCC cannot reliably subtract coincident detail.
        # Never pass off an invalid signed boolean delta as added/removed material.
        delta = base.Volume() - part.Volume()
        domain_delta = meta["volume_mm3"] - base_meta["volume_mm3"]
        log = (folder / "log.simpleFoam").read_text()
        row = {
            "case": folder.name, "geometry": path.parent.name, "p22_sha256": digest(path),
            "p21_sha256": digest(Path(meta["p21_variant"])),
            "surface_sha256": digest(case / "constant" / "triSurface" / "domain.stl"),
            "result_field_sha256": digest(P.vtk_dir(folder.name, 1200) / "internal.vtu"),
            "p22_valid_single_solid": True,
            "boolean_delta_valid": delta_valid,
            "added_mm3": added.Volume() if delta_valid else None,
            "removed_mm3": removed.Volume() if delta_valid else None,
            "p22_volume_mm3": part.Volume(), "baseline_p22_volume_mm3": base.Volume(),
            "expected_fluid_delta_mm3": delta, "recorded_fluid_delta_mm3": domain_delta,
            "fluid_delta_error_mm3": domain_delta - delta,
            "same_case_and_result_metadata": json.loads((case / "domain.json").read_text()) == meta,
            "same_solver_settings": json.loads((folder / "stages.json").read_text()) == base_settings,
            "mesh": P.mesh_stats(folder.name),
            "completed": "\nTime = 1200\n" in log and "\nEnd\n" in log,
        }
        if abs(row["fluid_delta_error_mm3"]) > .15 or not row["same_case_and_result_metadata"]:
            raise ValueError(f"{folder.name}: geometry/domain provenance mismatch {row}")
        if not row["mesh"]["mesh_ok"] or not row["completed"]:
            raise ValueError(f"{folder.name}: unaccepted or incomplete simulation")
        rows.append(row)
        print(folder.name, round(row["fluid_delta_error_mm3"], 4), flush=True)
    groups = {}
    for row in rows:
        groups.setdefault(row["surface_sha256"], []).append(row["case"])
    report = {
        "status": "HISTORICAL_GEOMETRY_AND_SOLVE_IDENTITY_AUDITED_POSTPROCESSING_CORRECTED_SEPARATELY",
        "case_count": len(rows), "distinct_surfaces": len(groups),
        "duplicate_surfaces": [names for names in groups.values() if len(names) > 1],
        "unreliable_boolean_deltas": [r["case"] for r in rows if not r["boolean_delta_valid"]],
        "cases": rows,
        "limitations": [
            "Historical case archives did not record source hashes at generation time. These are retrospective "
            "hashes, supported by matching CAD fluid-volume differences and case/result metadata, not an "
            "unbroken historical chain of custody.",
            "Mesh OK does not prove mesh independence. Steady SIMPLE iteration averaging is not transient "
            "URANS and does not resolve physical unsteadiness.",
            "This is isothermal airflow over a flat print plane, not a bead thermal or unsupported-bridge model.",
            "The old duct_air_mm3 field covers the enclosed upstream cavity only. Constant values do not mean "
            "the lower plenum or surrounding-air domain is unchanged.",
            "Coincident-detail boolean failures are recorded, not silently repaired or treated as valid deltas. "
            "The fluid-volume comparison uses independently valid whole-solid volumes; it is not proof of "
            "local shape equality.",
        ],
        "confirmed_corrections": [
            "Rear outlet clipping used 0.9 mm geometry regardless of the actual 1.1/2.0 mm opening.",
            "Historical 'bead' delivery included air up to 0.8 mm ABOVE the nozzle tip.",
            "A peak-speed scan followed negative-Y return flow, not an identified rear-jet streamline.",
            "Fuzzy OCC boolean operations can mutate shared in-memory topology; candidate builds now isolate "
            "references with deep copies and reject invalid differences.",
            "New angle builder initially omitted the angle argument (32-degree default); failed experiments "
            "did not enter the CFD case set.",
        ],
        "audit_source_sha256": digest(Path(__file__)),
    }
    (ROOT / "verification_cooling_rd_audit_r43.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
