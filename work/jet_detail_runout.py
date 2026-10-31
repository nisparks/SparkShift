"""The proposed run-out P22 for the 43b Fusion review (session scratch): the whole part at X+340, and the left jet's
cut-away at X+280, cut exactly as jet_detail_steps.py cut the before (X+200) and full-round (X+240) ones."""
from pathlib import Path

import cadquery as cq

OUT = Path(__file__).parent / "fusion_user_edit"
s = cq.importers.importStep(str(OUT / "p22_final.step")).val()
box = cq.Solid.makeBox(13.4 - 9.0, 18.0, 13.0, cq.Vector(-13.4, 12.0, -79.0))   # X-13.4..-9, Y12..30, Z-79..-66
for tag, solid in (("Jet_Runout_Proposed", s.intersect(box).translate(cq.Vector(280.0, 0, 0))),
                   ("P22_R43_Runout_Proposed", s.translate(cq.Vector(340.0, 0, 0)))):
    cq.exporters.export(cq.Workplane().add(solid), str(OUT / f"{tag}.step"))
    print(tag, solid.isValid(), round(solid.Volume(), 2))
