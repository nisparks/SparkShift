import sys, os
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
import cadquery as cq
import build_cpap_outlet_r43 as Bv
s = cq.Shape.importBrep(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\variants\p22_r43_printable.brep")
for y in Bv.BELL_PROFILE_Y:
    for side in (-1, 1):
        prof = Bv.bell_profile(s, side, y)
        errs = {k: round(v - Bv.bell_design(float(k)), 3) for k, v in prof.items()}
        bad = {k: (prof[k], Bv.bell_design(float(k))) for k, e in errs.items() if abs(e) > 0.02}
        print(f"y {y} side {side}: bad {bad}")
