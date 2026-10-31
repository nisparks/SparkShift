import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
sys.path.insert(0, str(CAD))
import cadquery as cq
import cfd_cpap_r41 as C
import r43_swept_feed as R
import r37_parts as P

folder = C.CFD.parent / "swept_feed"
report = {}
for label, name in (("Beacon", "beacon"), ("Cartographer", "cartographer")):
    old = cq.Shape.importBrep(str(folder / "optA" / f"p22_swept_{name}.brep"))
    new = cq.Shape.importBrep(str(folder / "optA_direct" / f"p22_swept_{name}.brep"))
    removed, added = old.cut(new), new.cut(old)
    zone = cq.Compound.makeCompound([
        cq.Solid.makeBox(9.7, 10.2, 6, cq.Vector(x, -24.3, P.Z_SEAT - 1.1))
        for x in (-20.5, 10.8)
    ])
    outside = removed.cut(zone).Volume() + added.cut(zone).Volume()
    assert outside < .001, (label, "Unexpected change outside obsolete mount regions", outside)
    for x, y in P.REAR_XY:
        assert not new.isInside(cq.Vector(x, y, -73.5)), (label, "Rear ear remains")
        assert new.isInside(cq.Vector(x, y, -70.4)), (label, "Rear insert hole remains open")
    for x, y in P.PROBE_XY:
        assert not new.isInside(cq.Vector(x, y, -72)), (label, "Probe mounting bore filled")
    airway = R.R41.fuse(R.RJ.duct_air(), R.air(3, .9, 32))
    old_obstruction = old.intersect(airway).Volume()
    new_obstruction = new.intersect(airway).Volume()
    assert abs(new_obstruction - old_obstruction) < .001, (label, "Air passage changed")
    again = R.clean_direct_mount(new)
    delta = again.cut(new).Volume() + new.cut(again).Volume()
    assert delta < .001, (label, "Cleanup not idempotent", delta)
    assert new.isValid() and len(new.Solids()) == len(new.Shells()) == 1
    report[label] = {
        "removed_mm3": removed.Volume(), "added_bore_plug_mm3": added.Volume(),
        "changes_outside_obsolete_rear_mount_regions_mm3": outside,
        "airway_obstruction_change_mm3": new_obstruction - old_obstruction,
        "idempotence_difference_mm3": delta,
        "rear_ears_absent_and_insert_holes_closed": True,
        "probe_mounting_bores_retained": True,
    }
    print(label, report[label], flush=True)
path = folder / "optA_direct" / "cleanup_checks.json"
path.write_text(json.dumps(report, indent=2) + "\n")
