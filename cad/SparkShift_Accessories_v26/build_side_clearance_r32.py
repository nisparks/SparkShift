"""Toolhead revision 32: flush -X side on both printed bodies, Red Lizard fan-recess skin removed.

With the revision-31 carriage, the closest approaches between the active carriage and the tools
parked beside it were:

1. 1.30 mm to a tool parked on the +X side. On both bodies the lower shelf layer (Z-26..-22.5) still
   reached X-13.5, 1.1 mm beyond everything else on that side (X-12.4, the original P17 carrier
   width). Revision 22 had already trimmed this edge from X-14 as unused stock. Its rear corner
   sat diagonally 1.3 mm from the P01 front corner. On the Red Lizard it also carried a 0.1-0.2 mm
   sliver beside the old Y-axis bore groove under the shelf.
2. 1.35 mm to a Red Lizard parked on the -X side: a 0.05 mm skin (Z-22.55..-22.5) under the Red
   Lizard upper shelf, 0.25 mm above its fan, reaching X15.0 and Y12.75. Revision 29 removed the
   same skin from the Bambu body.

Both changes only remove material, so every earlier interference and motion check still holds for
the smaller bodies. This script recomputes the clearances, checks the removals exactly and exports.
"""

import json

import cadquery as cq
import trimesh

from audit_low_z_bed_clearance import load_parked_variants
from audit_tool_owned_2510 import bounds, compound, overlaps
from build_bambu_clean_r29 import sha, single
from build_bambu_clean_r30 import PITCH, fan_parts
from build_carriage_lowered_mounts_r31 import MOUNT_DZ, NAMES as R31, carriage_parts, hardware, labelled, nearest
from build_modular_toolhead import ROOT, STEP, STL, box, load, volume

LIP = (-14.2, -12.4, 11.0, 38.6, -27.0, -22.5)
SKIN = (11.45, 15.1, 12.7, 32.05, -22.6, -22.5)
VARIANTS = {
    "Bambu": {"base": "Bambu_Compact_Fan_Closed_Bores_R30_REVIEW", "name": "Bambu_Compact_Flush_Side_R32_REVIEW",
              "cuts": {"-X lower shelf lip": LIP}},
    "RedLizard": {"base": "RedLizard_Side2510_Strip_Trim_R30_REVIEW", "name": "RedLizard_Side2510_Flush_Side_R32_REVIEW",
                  "cuts": {"-X lower shelf lip": LIP, "fan-recess skin": SKIN}},
}
REPORT = "verification_side_clearance_r32.json"
TOOLHEAD = "32_Bambu_Flush_Side_Toolhead_REVIEW"
COMPLETE = "32_Bambu_Flush_Side_Complete_REVIEW"
DY = (0, -1, -3, -10, -30)


def build(label):
    v = VARIANTS[label]
    # OCC Booleans on these STEP bodies can modify their inputs, so every Boolean starts from a
    # fresh load and the baseline volume is read first.
    base_volume = volume(load(v["base"]))
    removed = {name: volume(load(v["base"]).intersect(box(*b))) for name, b in v["cuts"].items()}
    body = single(load(v["base"]).cut(*[box(*b) for b in v["cuts"].values()]).clean(), f"{label} R32 body")
    left = {name: volume(body.copy().intersect(box(*b))) for name, b in v["cuts"].items()}
    error = abs(base_volume - volume(body) - sum(removed.values()))
    result = {
        "baseline": {"file": f"{v['base']}.step", "sha256": sha(STEP / f"{v['base']}.step")},
        "removed_mm3": removed, "left_in_cut_zones_mm3": left, "volume_conservation_error_mm3": error,
        "volume_mm3": volume(body), "baseline_volume_mm3": base_volume,
        "shells": len(body.Shells()), "valid": body.isValid(),
        "bounds_mm": bounds(body), "baseline_bounds_mm": bounds(load(v["base"])),
    }
    failures = []
    if error > 1e-3 or any(x > 1e-3 for x in left.values()):
        failures.append(f"{label}: removal not exact")
    if len(body.Shells()) != 1:
        failures.append(f"{label}: internal void")
    # Nothing on the non-fan side below the flange may reach past the original P17 width.
    below = body.copy().intersect(box(-20, 0, 0, 50, -66, -17.3))
    result["minus_x_extent_below_flange_mm"] = bounds(below)[0]
    if bounds(below)[0] < -12.4 - 1e-3:
        failures.append(f"{label}: -X side still beyond X-12.4")
    if label == "RedLizard":
        skin_band = body.copy().intersect(box(11.45, 30, 11, 32.05, -22.8, -22.5))
        result["material_over_fan_below_upper_shelf_mm3"] = volume(skin_band)
        # The flush face at X-12.4 sits over the old bore groove; report the material left there.
        slab = body.copy().intersect(box(-12.45, -12.35, 11.5, 29.0, -27.0, -19.0))
        result["material_at_new_face_over_groove_z_mm"] = [bounds(slab)[4], bounds(slab)[5]]
        if volume(skin_band) > 1e-3:
            failures.append("RedLizard: skin over the fan not fully removed")
    return body, result, failures


def tool_sets(bodies):
    fan, screws, _ = fan_parts()
    red = load_parked_variants()["RedLizard"]
    snap = red["tool"].Solids()
    if abs(volume(snap[0]) - 8352.19) > 0.5 or abs(bounds(snap[0])[5] - 48.74) > 0.01:
        raise ValueError("Red Lizard snapshot body is not solid 0")
    return {
        "Bambu": {"parts": [("body", bodies["Bambu"]),
                            ("fan inserts", load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW")),
                            ("fan", fan), ("fan screws", screws),
                            ("hotend", load("Tool2510_Reversed_Bambu_Reference_REVIEW")),
                            ("hotend hardware", load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW")),
                            ("P18", load("P18_Tool_docking_backplate_3010"))],
                  "fan": ("fan", "fan screws"), "dock": load("21_Bambu_Closed_Panel_Dock_Complete_REVIEW")},
        "RedLizard": {"parts": [("body", bodies["RedLizard"]), ("fan", snap[14]),
                                ("fan screws/inserts", compound(snap[15:19])),
                                ("hotend and hardware", compound(snap[1:14])),
                                ("P18 and magnets", compound(snap[19:]))],
                      "fan": ("fan", "fan screws/inserts"), "dock": red["dock"]},
    }


def as_dict(found, **extra):
    return None if found is None else {"mm": found[0], "a": found[1], "b": found[2], **extra}


def clearances(bodies):
    unchanged, changed = carriage_parts(load(R31["p01"]), load(R31["p22"]), hardware(MOUNT_DZ))
    carriage = labelled(unchanged + changed)
    sets = tool_sets(bodies)
    out = {}
    for label, t in sets.items():
        parked = labelled(t["parts"] + [("dock", t["dock"])])
        for dx in (PITCH, -PITCH):
            print(f"  active carriage vs {label} parked at {dx:+.1f}", flush=True)
            worst = None
            for dy in DY:
                found = nearest(carriage, parked, (0, dy, 0), (dx, 0, 0))
                if found and (worst is None or found[0] < worst["mm"]):
                    worst = as_dict(found, carriage_dy_mm=dy)
            out[f"active carriage | {label} parked at {dx:+.1f}"] = worst
        fan = labelled([(n, s) for n, s in t["parts"] if n in t["fan"]])
        out[f"own {label} fan | carriage"] = as_dict(nearest(carriage, fan, (0, 0, 0), (0, 0, 0)))
    for la, ta in sets.items():
        for lb, tb in sets.items():
            print(f"  parked {la} next to {lb}", flush=True)
            out[f"parked {la} fan side | {lb} at +37.3"] = as_dict(
                nearest(labelled(ta["parts"]), labelled(tb["parts"]), (0, 0, 0), (PITCH, 0, 0), cutoff=8.0))
    return out


def export_all(bodies, report):
    exports = []
    for label, body in bodies.items():
        name = VARIANTS[label]["name"]
        step, stl = STEP / f"{name}.step", STL / f"{name}.stl"
        cq.exporters.export(body, str(step))
        cq.exporters.export(body, str(stl), tolerance=0.03, angularTolerance=0.1)
        back = single(cq.importers.importStep(str(step)).val(), f"{label} STEP readback")
        mesh = trimesh.load_mesh(stl)
        if abs(volume(back) - volume(body)) > 1e-3 or not (
                mesh.is_watertight and mesh.is_winding_consistent and len(mesh.split(only_watertight=False)) == 1):
            raise ValueError(f"{label} export readback failed")
        exports += [step, stl]
    fan, screws, _ = fan_parts()
    tool = cq.Assembly(name="32 Bambu flush-side toolhead")
    for part, label, color in (
            (bodies["Bambu"], "R32_Bambu_Print", (0.95, 0.67, 0.1)),
            (load("Tool2510_Reversed_Bambu_Reference_REVIEW"), "Bambu_Hotend", (0.72, 0.72, 0.75)),
            (load("Tool2510_Existing_Tool_M2_5_Hardware_REVIEW"), "Hotend_M2p5_Hardware", (0.2, 0.7, 0.3)),
            (fan, "Fan_2510", (0.16, 0.18, 0.22)), (screws, "Fan_M2p5x14_Screws", (0.35, 0.35, 0.38)),
            (load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW"), "Fan_M2p5_L4_Inserts", (0.8, 0.55, 0.2))):
        tool.add(part, name=label, color=cq.Color(*color))
    tool_path = STEP / f"{TOOLHEAD}.step"
    tool.export(str(tool_path))
    if len(cq.importers.importStep(str(tool_path)).val().Solids()) != 20:
        raise ValueError("Toolhead STEP readback does not contain 20 solids")
    # Complete assembly: the revision-31 carriage, dock and toolhead with the Bambu print replaced.
    source = load(R31["complete"]).Solids()
    old = load(VARIANTS["Bambu"]["base"])
    same = lambda a, b: max(abs(p - q) for p, q in zip(bounds(a), bounds(b))) < 1e-3
    hit = [i for i, s in enumerate(source) if same(s, old) and abs(volume(s) - volume(old)) < 1e-3]
    if len(hit) != 1:
        raise ValueError(f"Ambiguous Bambu print in the revision-31 complete assembly: {hit}")
    print("Regression against unchanged complete-assembly solids", flush=True)
    worst = 0.0
    for i, s in enumerate(source):
        if i == hit[0]:
            continue
        increase = (sum(overlaps(bodies["Bambu"], {"S": s}).values())
                    - sum(overlaps(load(VARIANTS["Bambu"]["base"]), {"S": s}).values()))
        worst = max(worst, increase)
        if increase > 1e-3:
            raise ValueError(f"New intersection with complete-assembly solid {i}: {increase}")
    full = cq.Assembly(name="32 Bambu flush side - revision-31 carriage, toolhead and dock")
    full.add(bodies["Bambu"], name="R32_Bambu_Print", color=cq.Color(0.95, 0.67, 0.1))
    for i, s in enumerate(source):
        if i != hit[0]:
            full.add(s, name=f"Reference_{i}", color=cq.Color(0.55, 0.57, 0.6))
    full_path = STEP / f"{COMPLETE}.step"
    full.export(str(full_path))
    if len(cq.importers.importStep(str(full_path)).val().Solids()) != len(source):
        raise ValueError("Complete assembly readback solid count changed")
    report["complete_assembly"] = {"source": f"{R31['complete']}.step", "solids": len(source),
                                   "regression_checks": len(source) - 1, "max_increase_mm3": worst}
    exports += [tool_path, full_path]
    report["exports"] = [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in exports]


def main():
    bodies, failures, report = {}, [], {"status": "LOCAL_CAD_REVIEW_NOT_PRINT_OR_MACHINE_QUALIFICATION"}
    for label in VARIANTS:
        print(f"Building {label}", flush=True)
        body, result, fails = build(label)
        bodies[label] = body
        report[label] = result
        failures += fails
    report["static_failures"] = failures
    if failures:
        print(json.dumps(report, indent=1))
        raise ValueError(f"Static check failures: {failures}")
    print("Clearances before (revision-30 bodies)", flush=True)
    before = clearances({label: load(v["base"]) for label, v in VARIANTS.items()})
    print("Clearances after (revision-32 bodies)", flush=True)
    after = clearances({label: b.copy() for label, b in bodies.items()})
    report["clearances_mm"] = {k: {"r30_bodies": before[k], "r32_bodies": after[k]} for k in after}
    report["motion"] = ("Removal only: each revision-32 body is a subset of its revision-30 body, so the revision-30 "
                        "dock, carriage-retreat, service and neighbour sweeps and the revision-31 carriage sweeps "
                        "remain valid without re-running them.")
    export_all(bodies, report)
    report["not_changed"] = [
        "1.60 mm fan-to-carriage gap: the fan back face (Y13.0) to the P01 front face (Y11.4). Raising it means "
        "moving the fan forward, which thins the front fan insert wall (0.65 mm) and moves the airflow further off "
        "the heatsink.",
        "Rack pitch (37.3 mm) and the revision-31 carriage.",
    ]
    (ROOT / REPORT).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items()}, indent=1))


if __name__ == "__main__":
    main()
