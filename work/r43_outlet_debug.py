import sys, json, os
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
import build_cpap_outlet_r43 as B
import build_carriage_fixes_r41 as V
import r41_parts as R41
import r43_parts as R
new, old = R.p22(), R41.p22()
print("rays", B.floor_rays(new))
mn, mo = V.to_mesh(new, "dbg_new"), V.to_mesh(old, "dbg_old")
others = V.JET_LIP_BAND + B.ZONES
print("pocket", json.dumps(V.wall_report(mn, B.ZONES)))
print("rest r43", json.dumps(V.wall_report(mn, V.OUTLET_ALL, exclude=others)))
print("rest r41", json.dumps(V.wall_report(mo, V.OUTLET_ALL, exclude=others)))
