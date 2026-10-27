"""Export the dock's upper and lower snap jaws as printable parts.

Until now they existed only inside the dock assembly STEPs. The geometry is the current dock's (solids 1 and 2,
unchanged since revision 21), in the docked tool/dock frame; orient them in the slicer.
"""

import json

import r37_parts as P37
from build_bambu_clean_r29 import sha, single
from build_fan_mounts_r33 import export_print
from build_modular_toolhead import ROOT
from build_refined_docking_review import DOCK_NAMES

NAMES = {"Upper_Snap_Jaw": "Dock_Upper_Snap_Jaw_REVIEW", "Lower_Snap_Jaw": "Dock_Lower_Snap_Jaw_REVIEW"}
REPORT = "verification_dock_jaws_export.json"


def main():
    dock = dict(zip(DOCK_NAMES, P37.dock()))
    report = {"source": "36_RedLizard_Dock_Complete_REVIEW solids 1-2, the jaws of every revision-37/39 dock", "parts": {}}
    for key, name in NAMES.items():
        jaw = single(dock[key], key)
        if not jaw.isValid():
            raise ValueError(f"{key} is not a valid solid")
        files = export_print(name, jaw)
        b = jaw.BoundingBox()
        report["parts"][name] = {"volume_mm3": jaw.Volume(), "bounds_mm": [b.xmin, b.xmax, b.ymin, b.ymax, b.zmin, b.zmax],
                                 "files": [{"file": str(p.relative_to(ROOT)), "sha256": sha(p)} for p in files]}
    (ROOT / REPORT).write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
