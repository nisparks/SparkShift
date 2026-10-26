"""Red Lizard revision 30: trim the shelf strip behind the fan that crowds the active carriage.

The revision-22 Red Lizard body has the same leftover as the Bambu body: below the upper
shelf, a 1.25 mm strip behind the fan (Y11.5..12.75) runs out to X15, past the X11.45 fan
face. When this tool is parked one bay to the -X side of the active tool, that strip stops
0.10 mm from the carriage frame, inside the carriage's X footprint. This removal-only
revision aligns the strip with the fan face. Nothing else changes.
"""

import json

import cadquery as cq
import trimesh

from audit_tool_owned_2510 import bounds, compound
from build_bambu_clean_r29 import REFERENCES, sha, single
from build_bambu_clean_r30 import PITCH, min_distance
from build_modular_toolhead import ROOT, STEP, STL, box, load, volume

BASE = "RedLizard_Side2510_Shelf_Clearance_R22_REVIEW"
NAME = "RedLizard_Side2510_Strip_Trim_R30_REVIEW"
REPORT = "verification_redlizard_strip_trim_r30.json"
STRIP = (11.45, 15.1, 11.4, 12.75, -24.4, -22.5)


def main():
    # OCC Booleans here run in destructive mode: the first cut alters its input, after which
    # the same base reports a different volume and later Booleans fail. Every Boolean below
    # therefore starts from a fresh load, and the baseline volume is read before any of them.
    base_volume = volume(load(BASE))
    single(load(BASE), "revision-22 Red Lizard body")
    body = load(BASE).cut(box(*STRIP)).clean()
    single(body, "trimmed Red Lizard body")
    # Body is base minus the strip by construction; confirm the Boolean exactly.
    removed = load(BASE).intersect(box(*STRIP))
    in_strip = volume(removed)
    conservation_error = abs(base_volume - volume(body) - in_strip)
    left_in_strip = volume(body.copy().intersect(box(*STRIP)))
    if conservation_error > 1e-3 or left_in_strip > 1e-3:
        raise ValueError(f"Strip trim not exact: error {conservation_error}, left {left_in_strip}")
    if len(body.Shells()) != 1:
        raise ValueError("Trimmed body has internal voids")
    base = load(BASE)
    carriage = compound([load(n) for n in REFERENCES if n != "P18_Tool_docking_backplate_3010"])
    distances = {}
    for label, shape in (("before", base), ("after", body)):
        worst = None
        for dy in (0, -1, -3, -10, -30, -60):
            for dx in (-PITCH, PITCH):
                d = min_distance(carriage.translate((0, dy, 0)), shape.translate((dx, 0, 0)))
                if d is not None and (worst is None or d < worst["mm"]):
                    worst = {"mm": d, "neighbour_dx_mm": dx, "carriage_dy_mm": dy}
        distances[f"active_carriage_to_parked_redlizard_body_{label}"] = worst
        print(label, worst, flush=True)
    if distances["active_carriage_to_parked_redlizard_body_after"]["mm"] < 0.5:
        raise ValueError("Trim did not clear the active carriage")
    step, stl = STEP / f"{NAME}.step", STL / f"{NAME}.stl"
    cq.exporters.export(body, str(step))
    cq.exporters.export(body, str(stl), tolerance=0.03, angularTolerance=0.1)
    back = single(cq.importers.importStep(str(step)).val(), "STEP readback")
    mesh = trimesh.load_mesh(stl)
    if abs(volume(back) - volume(body)) > 1e-3 or not (
            mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split(only_watertight=False)) == 1):
        raise ValueError("Export readback failed")
    report = {
        "status": "LOCAL_CAD_REVIEW_NOT_PRINT_OR_MACHINE_QUALIFICATION",
        "baseline": {"file": f"{BASE}.step", "sha256": sha(STEP / f"{BASE}.step")},
        "change": "Removal only: shelf strip behind the fan beyond the X11.45 fan face (Y11.5..12.75, below Z-22.5).",
        "removed_mm3": volume(removed), "volume_conservation_error_mm3": conservation_error,
        "bounds_mm": bounds(body), "baseline_bounds_mm": bounds(base),
        "minimum_distances": distances,
        "note": "Body-only distances; the Red Lizard hotend, fan and hardware are unchanged. "
                "Removal cannot create new interference, so revision-22 motion checks still apply.",
        "exports": [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in (step, stl)],
    }
    (ROOT / REPORT).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
