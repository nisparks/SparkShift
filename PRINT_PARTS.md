# v26i print-part inspection notes

> [!WARNING]
> **WIP / FIT PENDING / NOT READY FOR PRINTING OR USE.**
> This human-directed, AI-assisted **vibe developed** model is not physically
> qualified. These are inspection meshes, not a slicer project, support plan,
> material recommendation, G-code, or approval for loaded/heated operation.

Use the complete [17-part v26 set](stl_v26) with
[the matching native F3D](cad/SparkShift_AHG_min_v26.f3d), **timeline 1644**,
SHA-256 `9d59eb88228c2efdfe6966537d10ed042603f9856a99ad3a6f20a11d0d12dcec`.
P04 is split into rear/front halves; P05 includes its direct servo hub,
not an extra horn. Use one of each role below, not mixed older P01/P03/P04F
parts. The [generic BOM](BOM.md) retains **15 bearings, 29 screws plus four
belt nuts, and 12 M3 heat-sets**; these geometry updates do not add hardware.

## Shear-keyed case pair and retained front arm

| Role | Current native geometry | Inspection / remaining gate |
|---|---|---|
| **P01 back case** | **33,982.970mm3 / 242 faces**, +225.68mm3 vs v26h. Adds four-zone tenons/coaxial bosses and retains the 1.85mm rear top bridge/contoured arm ramp. | Use only with the matching v26i P03 sockets. Preserve bearing/arm/bolt interfaces and shear contact faces; keys do not qualify strength or eliminate creep. Sealed mesh is in **assembly coordinates**. |
| **P03 front case** | **30,070.439mm3 / 232 faces**, -273.75mm3 vs v26h. Matching captured shear sockets complement the previous magnet-backing/shortened-arm changes. | Check the nominal **0.15mm mating clearance** against actual prints. Retain the existing clamp bolts; do not pull a binding keyed pair together with screw force. Mesh is now also in **assembly coordinates**, not the older bed placement. |
| **P04F front arm** | 3,854.094mm3, 83 faces. Face pulled back **2.550mm** to native Y=26.850mm, about 493mm2 flat area; X=19.830 outer wall and R9.35 gear clearance unified. | The **rear blind M3 pocket** at native (X14.950, Z31.400) runs Y=15.60..20.60 and leaves **6.250mm** wall to the front face. The existing 4mm M3 insert reference is retained, not an extra purchase. Confirm insertion access, pilot/knurl fit, screw engagement and material before use. |

These native dimensions are not STL-bed coordinates. The v26i interlocks
were reviewed across the 135-solid assembly and **71 cam poses**, 0..175
degrees in 2.5-degree steps, with no new static/dynamic clashes reported.
This is not continuous-motion or physical force/deflection qualification;
accepted reference overlaps, including the servo-envelope exception, remain
explicit in [inspection notes](PREVIEW.md). Archive readback reports all
135 bodies matching.

## Interlock fit is still a physical gate

P01 carries four shear-key zones captured by P03: the **+X lower keyhole
boss/foot/rib**, **-X lower inner block**, **-X mid-column key**, and **-X
upper bolt boss**. The [four-zone dimension table](PREVIEW.md) records
their exact assembly extents. Use the matched v26i pair; the added male
keys are not compatible by assumption with an older P03.

The **0.15mm nominal mating clearance** is not a validated print tolerance
or an interference fit. It allows movement before contact. The keys aim
to carry X shear through geometry, **not replace the clamp bolts** or
guarantee that the U legs cannot widen or creep. Layer orientation, material,
dimensions, preload, heat, cyclic loads and long-term creep remain unqualified.
Check clean engagement and full seating without forcing; **do not use bolt
force to pull binding interlocks together**. No extra metal key, bolt or insert
is added to the BOM.

## Mesh provenance and orientation

The 17 sealed files total **420,752 facets**. Each independently checks as
one closed, manifold, coherently wound, positive-volume component with
zero degenerate triangles and no zero/inverted stored normals found.
All bytes are retained without repair, facet deletion or normal rewriting.

**P01 and P03 are now native Fusion binary STL exports** of the v26i
parts, replacing the earlier P01 OpenCascade mesh and the older
bed-oriented P03 export. Native tessellation is approximate:

| Mesh | Facets | Mesh volume / analytic BRep volume | Approximate difference |
|---|---:|---|---|
| P01 | **12,064** | **33,997.081mm3 / 33,982.970mm3** | 14.11mm3 / **0.0415%** |
| P03 | **12,426** | **30,076.342mm3 / 30,070.439mm3** | 5.90mm3 / **0.0196%** |

These differences are not exact mesh/native shape or mass equality,
strength qualification, or a reason to repair/rewrite the sealed mesh.

P01's sealed STL bounds are approximately **X=-22.50..22.50,
Y=0.30..29.00, Z=-57.279..62.221mm**; the new +X key extends the depth.
P03's bounds are approximately **X=-22.50..22.50, Y=10.50..33.150,
Z=-20.400..57.021mm**. **Both remain in assembly coordinates, not on the
print bed**. The intended flat rear-face reference is **Y=0.30mm**;
use that face for **P01**, and the **Y=31.50mm front face for P03**.
Orient the selected face toward the bed and verify the result in a slicer;
P03's largest Y bound is not its intended face plane. Do not assume Z=0,
reuse the older P03 placement, or treat a flat visible face as support-free
approval. Other files retain their sealed inspection placements and still
need review rather than blind printing.

**Inspect every mesh in a slicer** for units/scale, thin walls, surface
faceting, contact area, bridges, support access, and actual nozzle/material
resolution. A topology pass does not qualify the 21T fit, heat-set pullout,
magnet backing, bearing fits, strength, hot creep or safe loaded motion.
No slicer profile, machine settings, or G-code is included.

## Complete 17-role set

| ID | Inspection mesh | Quantity | Licence scope |
|---|---|---:|---|
| P01 | [Top-connected back case with shear keys and carriage spine](stl_v26/P01_Back_case.stl) | 1 | GPL-3.0 custom work |
| P02 | [7mm motor/servo plate and rear ear-seat frame](stl_v26/P02_Motor_servo_plate.stl) | 1 | GPL-3.0 custom work |
| P03 | [Magnet-backed front receiver with shear sockets and cam tower](stl_v26/P03_Front_case.stl) | 1 | GPL-3.0 custom work |
| P04R | [Rear swing arm and shortened manual lever](stl_v26/P04R_Swing_arm_rear_half.stl) | 1 | GPL-3.0 custom work |
| P04F | [Flat-faced front arm with blind insert pocket](stl_v26/P04F_Swing_arm_front_half.stl) | 1 | GPL-3.0 custom work |
| P05 | [One-piece direct cam/hub, FIT PENDING](stl_v26/P05_Servo_cam.stl) | 1 | GPL-3.0 custom work |
| P06 | [Left 38T/14T compound](stl_v26/P06_Left_compound_38T_14T.stl) | 1 | GPL-3.0 custom work |
| P07 | [Right 38T/14T compound](stl_v26/P07_Right_compound_38T_14T.stl) | 1 | GPL-3.0 custom work |
| P08 | [Left 37T HGX drive](stl_v26/P08_Left_HGX_drive_37T.stl) | 1 | GPL-3.0 custom work |
| P09 | [Right 37T HGX drive](stl_v26/P09_Right_HGX_drive_37T.stl) | 1 | GPL-3.0 custom work |
| P12 | [Spring pressure cup](stl_v26/P12_Spring_pressure_cup.stl) | 1 | GPL-3.0 custom work |
| P13 | [Left GT2 tooth liner](stl_v26/P13_Left_tooth_liner.stl) | 1 | **CC BY-SA 3.0** |
| P14 | [Right GT2 tooth liner](stl_v26/P14_Right_tooth_liner.stl) | 1 | **CC BY-SA 3.0** |
| P15 | [Left belt arch](stl_v26/P15_Left_belt_arch.stl) | 1 | GPL-3.0 custom work |
| P16 | [Right belt arch](stl_v26/P16_Right_belt_arch.stl) | 1 | GPL-3.0 custom work |
| P17 | [HF tool carrier](stl_v26/P17_HF_tool_carrier.stl) | 1 | GPL-3.0 custom work |
| P18 | [Tool docking backplate](stl_v26/P18_Tool_docking_backplate.stl) | 1 | GPL-3.0 custom work |

The [exploded diagram and GIF](README.md) are architecture/kinematics aids,
not assembly-path or print-process validation. Reference hardware and the
hotend remain separately licensed vendor geometry, not printed parts.
Preserve [mixed GPL / CC BY-SA / vendor attribution](ATTRIBUTION.md).
Accessories remain [next-session plans](ACCESSORIES_PLAN.md), not extra
current print roles.
