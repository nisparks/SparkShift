import sys, os
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
os.chdir(sys.path[0])
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import cfd_cpap_r41 as C
import cfd_cpap_r41_post as P
import render_cfd_cpap_r41 as F
cases = [("r41bm_bambu_bed", 1200, "R41"), ("r43low_bambu_bed", 600, "flawed flat pocket (study)"), ("r43_bambu_bed", 1200, "R43 corrected")]
fig, axs = plt.subplots(3, 3, figsize=(27, 17))
for col, (n, it, tag) in enumerate(cases):
    g = P.internal(n, it)
    F.section(axs[0, col], g, "y", C.NOZZLE_Y, (-16, 16, -79.3, -71), title=f"{tag}: XZ across the nozzle (Y{C.NOZZLE_Y})")
    F.section(axs[1, col], g, "x", 10.9, (14, 30, -79.3, -71), title=f"{tag}: YZ along the right jet (X10.9)")
    F.section(axs[2, col], g, "x", 4.0, (10, 34, -79.3, -71), title=f"{tag}: YZ at X4 (between jet and nozzle)")
fig.tight_layout()
out = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\r43\compare_sections.png"
fig.savefig(out, dpi=70)
print(out)
