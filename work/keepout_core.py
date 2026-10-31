import sys, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
import r37_parts as P
from audit_tool_owned_2510 import bounds
from build_modular_toolhead import load, primitives
from build_carriage_lowered_mounts_r31 import NAMES as R31
core = load(R31["core"]).Solids()
meta = json.loads((primitives.WORK / "v26_meta.json").read_text())
raw = primitives.load_brep_list(primitives.WORK / "v26_cache.brep")
print("v26 meta entries", len(meta), "keys", list(meta[0].keys()))
refs = []
for m, (s, bb) in zip(meta, raw):
    refs.append((m, bounds(cq.Shape.cast(s))))
for dz in (0.0, P.DZ):
    ko = P.beacon_top_keepout(P.beacon(dz))
    kb = bounds(ko)
    print(f"dz {dz}: top keepout bbox", [round(v, 3) for v in kb])
    for i, s in enumerate(core):
        b = bounds(s)
        if any(b[2*k+1] < kb[2*k] or kb[2*k+1] < b[2*k] for k in range(3)):
            continue
        v = s.intersect(ko).Volume()
        if v > 1e-3:
            best = min(refs, key=lambda r: sum(abs(p - q) for p, q in zip(r[1], b)))
            err = sum(abs(p - q) for p, q in zip(best[1], b))
            print(f"   core solid {i}: {v:.3f} mm3, bbox {[round(x, 2) for x in b]}, match {best[0]['name']!r} metal={best[0].get('is_metal')} (bbox err {err:.3f})")
