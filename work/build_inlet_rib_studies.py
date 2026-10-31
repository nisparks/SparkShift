import json
import sys
from pathlib import Path

import os
CAD = Path(os.environ.get("SPARKSHIFT_CAD", r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"))
S = Path(__file__).parent
sys.path.insert(0, str(CAD))
import cadquery as cq
import numpy as np
import trimesh
import r43_swept_ribs as R
import r43_swept_feed as F
from audit_tool_owned_2510 import bounds

scene = S / "r43_scene"
manifest = json.loads((scene / "manifest.json").read_text())
load = lambda f: cq.Shape.importBrep(str(scene / f))
p21 = load(next(f for n, f in manifest["carriage"] if n.startswith("P21_")))
hotend = load(dict(manifest["variants"]["Bambu"]["parts"])["hotend"])
base = cq.Shape.importBrep(str(S / "swept_feed" / "optC28_clean" / "p22_swept_beacon.brep"))
reference_bounds = bounds(base)
x0, x1, y0, y1, z0, z1 = reference_bounds
reference_box = cq.Solid.makeBox(x1-x0, y1-y0, z1-z0, cq.Vector(x0, y0, z0))
rows = {}
for tag, rear in (("optC28_inlet_ribs", False), ("optC28_three_ribs", True)):
    folder = S / "swept_feed" / tag
    folder.mkdir(exist_ok=True)
    body = R.p22(base.copy(), include_rear_spine=rear)
    added, removed = body.cut(base), base.cut(body)
    assert removed.Volume() < 1e-4
    outside = body.cut(reference_box).Volume()
    assert outside < 1e-4
    vertices, triangles = body.tessellate(.005, .05)
    mesh = trimesh.Trimesh([v.toTuple() for v in vertices], triangles, process=True)
    assert mesh.is_watertight and mesh.is_winding_consistent
    assert added.intersect(hotend).Volume() < 1e-4
    fit = []
    for z in np.arange(0, 6.01, .5):
        moving = p21.translate((0, 0, float(z)))
        overlap = added.intersect(moving).Volume()
        assert overlap < 1e-4, (tag, z, overlap)
        fit.append({"p21_lift_z_mm": float(z), "added_material_gap_mm": added.distance(moving)})
    assert min(r["added_material_gap_mm"] for r in fit) > .15
    probes = []
    for label, probe in (("Beacon", F.P37.beacon()[3]), ("Cartographer", F.R42.cartographer())):
        overlap = added.intersect(probe).Volume()
        assert overlap < 1e-4, (tag, label, overlap)
        probes.append({"probe": label, "added_overlap_mm3": overlap})
    joint = F.R41.corridor(F.R41.SLEEVE_OUT, -51.4, -49).cut(
        F.R41.corridor(F.R41.BORE, -51.5, -48.9))
    assert added.intersect(joint).Volume() < 1e-4
    live = [cq.Solid.makeBox(7, 7, 8, cq.Vector(x-3.5, -3.8, -76)) for x in (-15.8,15.8)]
    live += [cq.Solid.makeBox(10,.3,17,cq.Vector(x,15.8,-65)) for x in (-23,13)]
    assert all(added.intersect(box).Volume()<1e-4 for box in live)
    z = -50
    window = F.R41.corridor(F.R41.BORE, z-.01, z+.01).cut(p21)
    before_open = window.cut(base).Volume()/.02
    after_open = window.cut(body).Volume()/.02
    row = {
        "label": "Bambu/Beacon-seat geometric rib study; airflow and slicing not yet qualified",
        "main_ribs": 2, "rear_spine": rear, "nominal_rib_thickness_mm": R.THICKNESS,
        "valid_single_solid_shell": True, "watertight_mesh": True,
        "added_mm3": added.Volume(), "removed_mm3": removed.Volume(),
        "same_outer_bounds": True, "unchanged_live_mount_regions": True,
        "material_outside_reference_box_mm3": outside,
        "reported_bbox_difference_mm": [a-b for a,b in zip(bounds(body), reference_bounds)],
        "p21_insertion_screen": fit, "probe_checks": probes,
        "joint_open_area_at_z-50_mm2": {"before":before_open,"after":after_open},
        "rear_air_components": len(F.air(3,.9,28).cut(body).Solids()),
        "construction": "0.8 mm constant-normal plan ribs with rounded ends, following the inlet bend; "
                        "socket-zone ends clipped 0.2 mm inside the P21 sleeve bore. Not fitted to "
                        "individual CFD trajectories; trial CFD is required.",
    }
    body.exportBrep(str(folder / "p22_swept_beacon.brep"))
    added.exportBrep(str(folder / "added_ribs.brep"))
    (folder / "checks.json").write_text(json.dumps(row,indent=2)+"\n")
    rows[tag] = row
    print(tag,json.dumps(row),flush=True)
(CAD / "verification_inlet_rib_geometry_r43.json").write_text(json.dumps(rows,indent=2)+"\n")
