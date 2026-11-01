"""Prepare an immutable, hash-identified case using exactly the accepted RVMS solver settings.

python prepare_cooling_review_r43.py r43auditRVMS40_bambu_bed review_rvms_a40
--fine adds the same 0.0625 mm below-tip refinement slab to either comparison geometry.
"""
import argparse
import json
import shutil
import tarfile
from pathlib import Path

import cfd_cpap_r41 as C
from cfd_provenance_r43 import digest

TEMPLATE = "r43avgV5dRVMS_bambu_bed"


def prepare(name, geometry, fine=False):
    if not name.startswith("r43") or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in name):
        raise ValueError("Invalid new case name")
    if Path(geometry).name != geometry:
        raise ValueError("Geometry must be a named experiment, not a path")
    source = C.CFD.parent / "swept_feed" / geometry
    template = C.CFD / "cases" / TEMPLATE
    out, domain = C.CFD / "cases" / name, C.CFD / "domains" / name
    if out.exists() or domain.exists():
        raise FileExistsError(f"Refusing to overwrite case or domain {name}")
    old_meta = json.loads((template / "domain.json").read_text())
    checks_file = source / "checks.json"
    checks = json.loads(checks_file.read_text()) if checks_file.exists() else {}
    if "rear_slot" in checks:
        params = checks["rear_slot"]
    elif "mouth_height_mm" in checks:
        params = {k: checks[k] for k in ("mouth_height_mm", "angle_deg", "floor_reference_height_mm")}
        params["roof_raise_mm"] = 3.0
    else:
        from cfd_outlet_balance_r43 import slot_parameters
        references = {"aim_v5d_RVM": "r43avgV5dRVM_bambu_bed",
                      "userP21_flow_neutral_v5d": "r43avgV5d_bambu_bed"}
        if geometry not in references:
            raise ValueError(f"{geometry}: no qualified rear-slot parameters")
        params = slot_parameters(references[geometry])
    # This experiment changes P22 only. Re-exported P21 BREPs need not be byte-identical.
    # Hold the exact bridge input fixed instead of relying on coincident Boolean comparisons.
    p22, p21 = source / "p22.brep", Path(old_meta["p21_variant"])
    extras = list(old_meta["extra_obstacles"].values())
    metadata = C.build_domain(name, old_meta["duct"], old_meta["tool"], old_meta["bed"], p22=p22,
                              p21=p21, leave_out=old_meta["left_out"], extra_files=extras)
    metadata["rear_slot"] = params
    metadata["geometry_sha256"] = {"p22": digest(p22), "p21": digest(p21)}
    metadata["fixed_p21_reference_case"] = TEMPLATE
    metadata["scene_manifest_sha256"] = digest(C.SCENE / "manifest.json")
    metadata["extra_obstacle_sha256"] = {Path(p).name: digest(p) for p in extras}
    metadata["domain_surface_sha256"] = digest(domain / "domain.stl")
    metadata["generator_sha256"] = {p.name: digest(p) for p in (Path(__file__), Path(C.__file__))}
    (domain / "domain.json").write_text(json.dumps(metadata, indent=2) + "\n")
    shutil.copytree(template, out)
    shutil.copyfile(domain / "domain.json", out / "domain.json")
    shutil.copyfile(domain / "domain.stl", out / "constant" / "triSurface" / "domain.stl")
    control = out / "system" / "controlDict"
    text = control.read_text()
    if "writeInterval   600;" not in text or "writeCompression off;" not in text:
        raise ValueError("Unexpected output policy in reference case")
    control.write_text(text.replace("writeInterval   600;", "writeInterval   1200;")
                       .replace("writeCompression off;", "writeCompression on;"), newline="\n")
    stages_path = out / "stages.json"
    stages = json.loads(stages_path.read_text())
    stages["output_policy"] = {"write_interval": 1200, "compression": "on",
                               "reason": "Reduce storage on shared CFD host; no solver/physics change"}
    stages_path.write_text(json.dumps(stages, indent=2) + "\n")
    if fine:
        path = out / "system" / "snappyHexMeshDict"
        text = path.read_text()
        marker = "\n}\n\ncastellatedMeshControls"
        region = "        nozzleZone { mode inside; levels ((1e15 2)); }"
        if text.count(marker) != 1 or text.count(region) != 1:
            raise ValueError("Unexpected refinement dictionary")
        text = text.replace(marker, "\n    belowTipAudit { type box; min (-0.006 0.0167 -0.0791); "
                            "max (0.006 0.0287 -0.0778); }" + marker)
        text = text.replace(region, region + "\n        belowTipAudit { mode inside; levels ((1e15 4)); }")
        path.write_text(text, newline="\n")
        stages_path = out / "stages.json"
        stages = json.loads(stages_path.read_text())
        stages["below_tip_refinement"] = {"box_mm": [-6, 6, 16.7, 28.7, -79.1, -77.8],
                                         "level": 4, "nominal_cell_mm": .0625,
                                         "purpose": "Sensitivity of the 0.2 mm below-tip target, not thermal validation"}
        stages_path.write_text(json.dumps(stages, indent=2) + "\n")
    manifest = {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*")) if p.is_file()}
    (out / "input_hashes.json").write_text(json.dumps(manifest, indent=2) + "\n")
    with tarfile.open(C.CFD / "cases" / f"{name}.tgz", "w:gz") as archive:
        archive.add(out, arcname=name)
    print(json.dumps({"case": name, "rear_slot": params, "geometry_sha256": metadata["geometry_sha256"],
                      "domain_surface_sha256": metadata["domain_surface_sha256"],
                      "fluid_volume_mm3": metadata["volume_mm3"],
                      "archive": str(C.CFD / "cases" / f"{name}.tgz")}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    parser.add_argument("geometry")
    parser.add_argument("--fine", action="store_true")
    args = parser.parse_args()
    prepare(args.case, args.geometry, args.fine)
