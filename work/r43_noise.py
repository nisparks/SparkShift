import sys, os, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
import cfd_cpap_r41_post as P
import cfd_cpap_r43 as A
out = {}
for n in ("r41bm_bambu_bed", "r43_bambu_bed"):
    for it in (600, 1200):
        g = P.internal(n, it)
        s = A.print_sweep(g)
        a = A.annulus(g, A.C.NOZZLE_TIP_Z + 0.3)
        out[f"{n}@{it}"] = s
        print(n, it, json.dumps(s), "over-tip annulus", a["mean_ms_r1_5"], flush=True)
json.dump(out, open(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\noise_600_1200.json", "w"), indent=1)
