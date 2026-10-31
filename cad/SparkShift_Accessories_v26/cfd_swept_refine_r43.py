"""Reproduce the candidate-A local outlet-resolution check after writing a fresh CFD case.

Run cfd_cpap_r41.py case with --interval 600 (the first stage is twice that interval),
then this script with the case name. Geometry and solver schemes are not changed.
This is a local sensitivity check, not a formal mesh-independence study.
"""
import argparse
import json

import cfd_cpap_r41 as C


HOTEND_BOXES = {
    "Bambu": [
        (4.0, 8.5, 19.5, 23.0, -66.0, -62.0),
        (-8.5, -4.5, 18.0, 22.0, -57.0, -53.0),
    ],
    "RedLizard": [(-8.0, -4.0, 23.0, 27.0, -47.0, -44.0)],
}
FEED_BOXES = [
    (8.0, 10.5, 3.0, 6.0, -69.0, -66.0),
    (-10.5, -8.0, 3.0, 6.0, -69.0, -66.0),
]
OUTLET_BOX = (-10.0, 10.0, 3.0, 15.0, -75.0, -66.0)


def refine(name, cleaned_bambu=False, symmetric=False):
    """symmetric: add the mirror image of every box that has no mirror partner (for a mirror-symmetric scene)."""
    case = C.CFD / "cases" / name
    metadata = json.loads((case / "domain.json").read_text())
    stages_path = case / "stages.json"
    stages = json.loads(stages_path.read_text())
    if stages.get("additional_refinement"):
        raise ValueError(f"{name}: start from a freshly generated case, not an already refined one")
    boxes = HOTEND_BOXES[metadata["tool"]] + FEED_BOXES + [OUTLET_BOX]
    if cleaned_bambu:
        if metadata["tool"] != "Bambu":
            raise ValueError("Cleaned-Bambu hotend refinement requires the Bambu tool")
        boxes += [(5.0, 8.0, 19.0, 22.0, -56.0, -53.0),
                  (-8.0, -5.0, 19.0, 22.0, -56.0, -53.0)]
    if symmetric:
        boxes += [m for m in [(-b[1], -b[0], *b[2:]) for b in boxes] if m not in boxes]
    path = case / "system" / "snappyHexMeshDict"
    text = path.read_text()
    geometry, regions = [], []
    for i, box in enumerate(boxes):
        x0, x1, y0, y1, z0, z1 = (v / 1000 for v in box)
        geometry.append(
            f"    candidateDetail{i} {{ type box; min ({x0:g} {y0:g} {z0:g}); "
            f"max ({x1:g} {y1:g} {z1:g}); }}")
        regions.append(f"        candidateDetail{i} {{ mode inside; levels ((1e15 3)); }}")
    geometry_marker = "\n}\n\ncastellatedMeshControls"
    region_marker = "    refinementRegions { nozzleZone { mode inside; levels ((1e15 2)); } }"
    if text.count(geometry_marker) != 1 or text.count(region_marker) != 1:
        raise ValueError(f"{name}: unexpected snappyHexMeshDict structure")
    text = text.replace(geometry_marker, "\n" + "\n".join(geometry) + geometry_marker)
    text = text.replace(region_marker, "    refinementRegions\n    {\n"
                        "        nozzleZone { mode inside; levels ((1e15 2)); }\n"
                        + "\n".join(regions) + "\n    }")
    stages["additional_refinement"] = {
        "reason": "Swept-outlet local resolution; inherited hotend/feed-junction details "
                  "plus a level-3 box around the merged feed and rear outlet. Quality limits unchanged.",
        "boxes_mm": boxes,
        "level": 3,
        "nominal_cell_mm": 0.125,
        "limitation": "Local two-resolution sensitivity only; not global or thermal mesh independence.",
        "cleaned_bambu_hotend_fix": cleaned_bambu,
    }
    if symmetric:
        stages["additional_refinement"]["mirror_symmetric_boxes"] = True
    path.write_text(text, newline="\n")
    stages_path.write_text(json.dumps(stages, indent=2) + "\n", newline="\n")
    return stages["additional_refinement"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("names", nargs="+")
    parser.add_argument("--cleaned-bambu", action="store_true")
    parser.add_argument("--symmetric", action="store_true", help="mirror-pair every refinement box")
    args = parser.parse_args()
    for name in args.names:
        print(name, json.dumps(refine(name, cleaned_bambu=args.cleaned_bambu, symmetric=args.symmetric)))
