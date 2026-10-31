import sys, math, time
sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
import cadquery as cq
import build_and_verify_accessories_v26 as acc
from build_modular_toolhead import load
from build_carriage_lowered_mounts_r31 import MOUNT_DZ, NAMES as R31, mass_properties, same_properties
from audit_tool_owned_2510 import bounds
t = time.perf_counter()
d0 = cq.Shape.cast(acc.build_p22_lower_plenum()[0])
d1 = cq.Shape.cast(acc.build_p22_lower_plenum(MOUNT_DZ)[0])
print("default == released:", same_properties(mass_properties(d0), mass_properties(load("P22_CPAP_Lower_Plenum"))))
print("mount_dz == R31:", same_properties(mass_properties(d1), mass_properties(load(R31["p22"]))))
new = cq.Shape.cast(acc.build_p22_lower_plenum(MOUNT_DZ, ((15.8, -0.3), (-15.8, -0.3), (15.8, -19.5), (-15.8, -19.5)), (-73.0, -70.0), (-73.4, -70.0))[0])
print("R37 P22 valid", new.isValid(), "solids", len(new.Solids()), "vol", round(new.Volume(), 3), "vs R31", round(d1.Volume(), 3), "bbox", [round(v, 3) for v in bounds(new)])
# Bambu tip repair prototype
TIP = -78.8794047847718
APEX = -79.7952
sol = load("Tool2510_Reversed_Bambu_Reference_REVIEW").Solids()
nz = sol[3]
tan = math.tan(math.radians(31.004))
r_tip = (TIP - APEX) * tan
z_plug = -77.30
r_plug = (z_plug - APEX) * tan
frustum = cq.Solid.makeCone(r_tip, r_plug, z_plug - TIP, cq.Vector(0, 22.7, TIP), cq.Vector(0, 0, 1))
fixed = nz.fuse(frustum).clean()
drill_h = (1.0 - 0.2) / math.tan(math.radians(59))
drill = cq.Solid.makeCone(0.2, 1.0, drill_h, cq.Vector(0, 22.7, z_plug - drill_h), cq.Vector(0, 0, 1))
orifice = cq.Solid.makeCylinder(0.2, z_plug - drill_h - TIP + 0.2, cq.Vector(0, 22.7, TIP - 0.1), cq.Vector(0, 0, 1))
fixed = fixed.cut(drill).cut(orifice).clean()
print(f"r_tip {r_tip:.4f} (face dia {2*r_tip:.3f}), r at plug top {r_plug:.4f}, drill depth {drill_h:.3f}, orifice length {z_plug - drill_h - TIP:.3f}")
print("repaired valid", fixed.isValid(), "solids", len(fixed.Solids()), "faces", len(fixed.Faces()), "vol", round(fixed.Volume(), 4), "orig", round(nz.Volume(), 4), "added", round(fixed.Volume() - nz.Volume(), 4))
print("repaired bbox", [round(v, 4) for v in bounds(fixed)])
above = cq.Solid.makeBox(40, 40, 60, cq.Vector(-20, 2.7, -77.29))
print("unchanged above Z-77.29:", abs(fixed.intersect(above).Volume() - nz.intersect(above).Volume()) < 1e-6, round(fixed.intersect(above).Volume(), 4), round(nz.intersect(above).Volume(), 4))
print("t", round(time.perf_counter() - t, 1))
