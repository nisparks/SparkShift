"""Fusion review STEP for the centre-feed variant (session scratch). Side by side along X: revision 43 with P23 and the
Bambu (X-55), the centre feed with the Bambu (X0) and with the Red Lizard (X55); cut-aways of the centre feed with the
Bambu: along the slot's centre (keeping X <= 0, at X110) and a plan cut through the plenum (keeping Z <= -72.3, at X165)."""
import json, os, sys
CAD = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, CAD); os.chdir(CAD)
import cadquery as cq
import build_and_verify_accessories_v26 as acc
import r37_parts as P37
S = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
SCENE = acc.WORK / "r43_scene"
man = json.loads((SCENE / "manifest.json").read_text())
carriage = dict(man["carriage"])
br = lambda f: cq.Shape.importBrep(str(SCENE / f))
p22_final = cq.Shape.importBrep(os.path.join(S, "cfd", "p22_r43.brep"))
p22_cf = cq.Shape.importBrep(os.path.join(S, "cfd", "p22_r43_centre.brep"))
p23 = br(carriage[P37.NAMES["p23"]])
b = P37.beacon()
probe = [b[2], b[3], b[4]]
screws = [br(carriage[n]) for n in carriage if n.startswith("R37_PROBE_M3x6")]
tools = {}
for label in ("Bambu", "RedLizard"):
    tools[label] = [br(f) for n, f in man["variants"][label]["parts"] if n in ("hotend", "hotend hardware", "hotend and hardware")]
REG = cq.Solid.makeBox(60, 80, 40, cq.Vector(-30, -48, -80))
C22, C23, CPR, CBA, CRL, CSC = (cq.Color(0.15, 0.6, 0.3), cq.Color(0.95, 0.55, 0.12), cq.Color(0.42, 0.25, 0.6),
                                cq.Color(0.2, 0.45, 0.9), cq.Color(0.85, 0.2, 0.2), cq.Color(0.3, 0.3, 0.3))
asm = cq.Assembly(name="centre_feed_review")

def add(shape, name, color, dx, keep=None):
    s = shape.intersect(REG) if keep is None else shape.intersect(REG).intersect(keep)
    if s is None or s.Volume() < 1e-6:
        return
    asm.add(s.translate((dx, 0, 0)), name=name, color=color)

def build(tag, dx, p22, with_p23, tool, keep=None):
    add(p22, f"{tag}_P22", C22, dx, keep)
    if with_p23:
        add(p23, f"{tag}_P23", C23, dx, keep)
    for i, s in enumerate(probe):
        add(s, f"{tag}_Beacon_{i}", CPR, dx, keep)
    for i, s in enumerate(screws):
        add(s, f"{tag}_probe_screw_{i}", CSC, dx, keep)
    for i, s in enumerate(tools[tool]):
        add(s, f"{tag}_{tool}_{i}", CBA if tool == "Bambu" else CRL, dx, keep)

build("R43", -55.0, p22_final, True, "Bambu")
build("CentreFeed_Bambu", 0.0, p22_cf, False, "Bambu")
build("CentreFeed_RedLizard", 55.0, p22_cf, False, "RedLizard")
build("CutX0", 110.0, p22_cf, False, "Bambu", keep=cq.Solid.makeBox(40, 100, 60, cq.Vector(-40, -50, -90)))
build("CutZ", 165.0, p22_cf, False, "Bambu", keep=cq.Solid.makeBox(80, 100, 20, cq.Vector(-40, -50, -92.3)))
out = os.path.join(S, "center_feed", "centre_feed_review.step")
asm.save(out, exportType="STEP")
print(out, os.path.getsize(out) // 1024, "kB")
