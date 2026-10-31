import sys
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
from OCP.Bnd import Bnd_Box
from OCP.BRepBndLib import BRepBndLib
import build_and_verify_accessories_v26 as acc
from build_modular_toolhead import box, primitives
from build_carriage_lowered_mounts_r31 import MOUNT_DZ
def zopt(s):
    b = Bnd_Box(); BRepBndLib.AddOptimal_s(s.wrapped, b, False, False); return b.Get()
beacon = [cq.Shape.cast(s).translate((0, 3.2, -75)) for s in primitives.load_step(primitives.SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")]
for i, s in enumerate(beacon):
    b = zopt(s)
    print("beacon", i, "solids", len(s.Solids()), "faces", len(s.Faces()), "bbox", [round(v, 3) for v in b], "vol", round(s.Volume(), 2))
dome = beacon[4]
for z0, z1 in ((-78.4, -77.9), (-77.9, -77.4), (-77.4, -76.62), (-76.62, -75.0), (-75.0, -70.0)):
    piece = dome.intersect(box(-30, 30, -30, 30, z0, z1))
    print(f"dome slab Z{z0}..{z1}: vol {piece.Volume():.3f}, bbox", [round(v, 2) for v in zopt(piece)] if piece.Volume() > 1e-6 else None)
hw = dict((n, cq.Shape.cast(s)) for n, s in acc.build_accessory_hardware(MOUNT_DZ))
for n in sorted(hw):
    b = zopt(hw[n])
    if b[2] < -76.0:
        print("hw", n, [round(v, 3) for v in b])
carto = [cq.Shape.cast(s).rotate((0, 0, 0), (0, 0, 1), 180).translate((0, -13.00701, -75)) for s in primitives.load_step(primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")[:100]]
low = sorted(((zopt(s)[2], i) for i, s in enumerate(carto)))[:4]
for z, i in low:
    print("carto", i, [round(v, 3) for v in zopt(carto[i])], "vol", round(carto[i].Volume(), 3))
