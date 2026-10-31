import sys
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
import build_and_verify_accessories_v26 as acc
from build_modular_toolhead import load, box
from build_carriage_lowered_mounts_r31 import MOUNT_DZ, NAMES as R31
def bb(s):
    b = Bnd_Box(); BRepBndLib.AddOptimal_s(s.wrapped, b, False, False); return [round(v, 3) for v in b.Get()]
hw = [(n, cq.Shape.cast(s)) for n, s in acc.build_accessory_hardware(MOUNT_DZ)]
for n, s in hw:
    b = bb(s)
    if b[2] < -69 and b[5] > -80 and abs(b[0]) < 25:
        print("hw", n, b)
p23 = load("P23_Beacon_Cartographer_Mount"); print("P23", bb(p23), "vol", round(p23.Volume(), 2))
p22 = load(R31["p22"]); print("P22", bb(p22))
# P22 material just above the P23 seat plane (Z-70.80) inside P23's footprint
for z0, z1 in ((-70.80, -70.47), (-70.47, -70.0), (-70.0, -69.0), (-69.0, -68.0)):
    piece = p22.intersect(box(-19.2, 19.2, -14.2, 11.55, z0, z1))
    print(f"P22 over P23 footprint Z{z0}..{z1}: vol {piece.Volume():.2f}", bb(piece) if piece.Volume() > 1e-6 else "")
