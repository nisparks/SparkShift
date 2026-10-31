"""Copy the working inputs needed to resume the Beacon/CPAP/EBB42 C28 study into a data-branch tree.

Usage: python build_resume_pack.py <dest>   (dest is an empty orphan worktree)
Layout: <dest>/work mirrors this session folder (SPARKSHIFT_WORK); <dest>/sensor_sources holds our
probe measurements (SPARKSHIFT_SENSOR_DIR). Vendor probe STEP models are listed, not copied.
"""
import hashlib
import importlib.metadata as md
import json
import platform
import shutil
import sys
from pathlib import Path

S = Path(__file__).resolve().parent
SENSOR_DIR = Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files"
                  r"\compact_direct_cam\accessory_sources")
TOP_FILES = [
    "v26_meta.json", "v26_cache.brep", "gantry_meta.json", "gantry_cache.brep", "ebb42_cache.brep",
    "frame_world_bodies.json", "rack_audit_frames.json", "rack_audit_Bed_world.json", "rack_audit_Bed_world.step",
    "rack_audit_crossbar_world.step", "rack_audit_Flying_Gantry_world.json", "rack_audit_Flying_Gantry_world.step",
    "rack_audit_X_Gantry_world.json", "rack_audit_X_Gantry_world.step", "rack_lift_carriage_withdrawn_bounds.json",
    "modular_audit_core_reference.step", "parked_intake_preflight.json", "parked_intake_sources.json",
    "parked_intake_T0_Bambu.step", "parked_intake_T1_RedLizard.step", "53_C28_Live_Edits_Preserved.f3d",
]
SWEPT = ["optC28_clean", "optC28_mechanical", "userP21_20261030_193918", "userP21_matched_v4",
         "optC28_user_retainer", "optC28_conformal", "optC28_dfm", "optD11_roof"]
MAX_MB = 20
PACKAGES = ["cadquery", "cadquery-ocp", "numpy", "trimesh", "scipy", "vtk", "pyvista", "matplotlib",
            "Pillow", "manifold3d", "rtree", "shapely"]


def digest(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def selection():
    for f in sorted(S.iterdir()):
        if f.is_file() and (f.suffix in (".py", ".sh", ".json") or f.name in TOP_FILES):
            yield f, Path("work") / f.name
    for scene in ("r41_scene", "r43_scene"):
        for f in sorted((S / scene).rglob("*")):
            if f.is_file():
                yield f, Path("work") / f.relative_to(S)
    for study in SWEPT:
        for f in sorted((S / "swept_feed" / study).rglob("*")):
            if f.is_file() and f.stat().st_size <= MAX_MB * 2**20:
                yield f, Path("work") / f.relative_to(S)
    for f in sorted((S / "cfd").iterdir()):
        if f.is_file() and f.suffix in (".py", ".sh", ".ps1", ".brep") and f.stat().st_size <= 5 * 2**20:
            yield f, Path("work") / f.relative_to(S)
    for f in sorted((S / "cfd" / "variants").rglob("*")):
        if f.is_file():
            yield f, Path("work") / f.relative_to(S)
    for f in sorted((S / "bs_r43").glob("*.json")):
        yield f, Path("work") / f.relative_to(S)
    for f in sorted((S / "printability_swept").rglob("*")):
        if f.is_file() and f.suffix in (".json", ".log"):
            yield f, Path("work") / f.relative_to(S)
    for f in sorted(SENSOR_DIR.glob("*.json")):
        yield f, Path("sensor_sources") / f.name


def environment():
    versions = {}
    for name in PACKAGES:
        try:
            versions[name] = md.version(name)
        except md.PackageNotFoundError:
            pass
    return {"python": sys.version.split()[0], "platform": platform.platform(), "packages": versions}


def main():
    dest = Path(sys.argv[1]).resolve()
    files = {}
    for src, rel in selection():
        out = dest / rel
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, out)
        files[rel.as_posix()] = {"bytes": src.stat().st_size, "sha256": digest(out)}
    biggest = max(v["bytes"] for v in files.values())
    assert biggest < 95 * 2**20, biggest
    vendor = {f.name: {"bytes": f.stat().st_size, "sha256": digest(f)}
              for f in sorted(SENSOR_DIR.iterdir()) if f.suffix.lower() in (".step", ".stp")}
    manifest = {
        "purpose": "Working inputs to resume the Beacon/CPAP/EBB42 C28 study on another machine.",
        "code_branch": "nisparks-beacon-cpap-ebb42-integration",
        "environment_variables": {"SPARKSHIFT_WORK": "work", "SPARKSHIFT_SENSOR_DIR": "sensor_sources",
                                  "SPARKSHIFT_CAD": "<code checkout>/cad/SparkShift_Accessories_v26"},
        "vendor_models_not_included": vendor,
        "vendor_models_note": "Vendor probe CAD is not redistributed. Place the published Beacon RevH and "
                              "Cartographer V3 STEP files in sensor_sources with these names. A different "
                              "vendor revision changes the hash and may change the probe geometry checks.",
        "not_included": ["CFD case/domain/result folders (about 31 GB; summaries are in the code branch)",
                         "Slicer G-code, sliced projects and print-oriented model copies",
                         "Large review assemblies (the code branch keeps the linked ones)",
                         "Screenshots and transcript images"],
        "python_environment": environment(),
        "file_count": len(files),
        "total_bytes": sum(v["bytes"] for v in files.values()),
        "files": files,
    }
    (dest / "MANIFEST.json").write_text(json.dumps(manifest, indent=1) + "\n")
    print(json.dumps({"files": len(files), "total_MB": round(manifest["total_bytes"] / 2**20, 1),
                      "largest_MB": round(biggest / 2**20, 1), "vendor_models": list(vendor)}))


if __name__ == "__main__":
    main()
