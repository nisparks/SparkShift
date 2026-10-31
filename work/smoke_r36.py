import sys, time, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import build_chute_chamfer_rack_r36 as r36
t = time.perf_counter()
chute, rep, fails = r36.build_chute()
print("chute", json.dumps({k: rep[k] for k in ("removed_mm3", "added_mm3", "wall_to_m3_head_channel_mm")}), rep["confinement"]["unchanged_outside_zones"], fails, round(time.perf_counter() - t, 1), flush=True)
docks = r36.dock_sets(chute)
m = r36.write_scene(chute, docks)
print("scene written", len(m["carriage"]), {k: len(v["parts"]) for k, v in m["variants"].items()}, round(time.perf_counter() - t, 1), flush=True)
s = r36.scene()
print("scene loaded", round(time.perf_counter() - t, 1), flush=True)
from audit_tool_owned_2510 import bounds
for label, v in s["variants"].items():
    print(label, "tool bounds", [round(x, 2) for x in bounds(v["tool"])], "solids", len(v["tool"].Solids()))
print("carriage bounds", [round(x, 2) for x in bounds(s["carriage"])], "solids", len(s["carriage"].Solids()))
for version in ("r21", "r36"):
    c = r36.task_clearances(s, version)
    for k, row in c.items():
        print(version, k, None if row is None else (round(row["mm"], 3), row["moving"], row["parked"], row["carriage_dy_mm"]))
    print("t", round(time.perf_counter() - t, 1), flush=True)
