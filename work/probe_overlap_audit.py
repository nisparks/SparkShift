import sys, json
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
import build_and_verify_accessories_v26 as acc
from build_modular_toolhead import load, primitives
from build_carriage_lowered_mounts_r31 import MOUNT_DZ, NAMES as R31
from build_p24_cable_entry_r35 import NAMES as R35
from audit_tool_owned_2510 import bounds

def beacon(dz):
    return [cq.Shape.cast(s).translate((0, 3.2, -75 + dz)) for s in primitives.load_step(primitives.SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")]
def carto(dz):
    return [cq.Shape.cast(s).rotate((0, 0, 0), (0, 0, 1), 180).translate((0, -13.00701, -75 + dz)) for s in primitives.load_step(primitives.SENSOR_DIR / "Cartographer_V3_RightAngle.step")[:100]]
def ov(a, b):
    ba, bb = bounds(a), bounds(b)
    if any(ba[2*i+1] < bb[2*i] or bb[2*i+1] < ba[2*i] for i in range(3)):
        return 0.0
    return a.intersect(b).Volume()
parts = {"P23": load("P23_Beacon_Cartographer_Mount"), "P22_R31": load(R31["p22"]), "P20": load("P20_CPAP_Hose_Inlet"),
         "P21": load("P21_CPAP_Gantry_Bridge"), "P24_R35": load(R35["p24"]), "Cable_R35": load(R35["cable"]), "Core_R31": load(R31["core"])}
hw = {n: cq.Shape.cast(s) for n, s in acc.build_accessory_hardware(MOUNT_DZ)}
out = {}
for dz in (0.0, 0.33):
    b = beacon(dz)
    c = carto(dz)
    probes = {"Beacon_2_rear_block": b[2], "Beacon_3_pcb": b[3], "Beacon_4_connector": b[4], "Cartographer": cq.Compound.makeCompound(c)}
    rows = []
    for pn, p in probes.items():
        for n, s in list(parts.items()) + list(hw.items()):
            v = sum(ov(x, p) for x in s.Solids()) if n == "Core_R31" else ov(s, p)
            if v > 1e-3:
                rows.append((pn, n, round(v, 3)))
    out[f"dz={dz}"] = rows
    for r in rows:
        print(f"dz {dz}: {r[0]:22s} x {r[1]:34s} {r[2]:9.3f} mm3")
print("Cartographer lowest 4 and top", [round(v, 2) for v in bounds(cq.Compound.makeCompound(carto(0)))])
