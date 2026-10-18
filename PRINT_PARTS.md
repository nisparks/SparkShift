# v26h print-part inspection notes

> [!WARNING]
> **WIP / FIT PENDING / NOT READY FOR PRINTING OR USE.**
> This human-directed, AI-assisted **vibe developed** model is not physically
> qualified. These are inspection meshes, not a slicer project, support plan,
> material recommendation, G-code, or approval for loaded/heated operation.

Use the complete [17-part v26 set](stl_v26) with
[the matching native F3D](cad/SparkShift_AHG_min_v26.f3d), **timeline 1632**,
SHA-256 `dda41c30d379930061c16e888b51b65f641c6bd47386086551236c59545db501`.
P04 is split into rear/front halves; P05 includes its direct servo hub,
not an extra horn. Use one of each role below, not mixed older P01/P03/P04F
parts. The [generic BOM](BOM.md) retains **15 bearings, 29 screws plus four
belt nuts, and 12 M3 heat-sets**; these geometry updates do not add hardware.

## Three revised parts

| Role | Current native geometry | Inspection / remaining gate |
|---|---|---|
| **P01 back case** | 33,757.291mm3, 218 faces. The old square upper opening is replaced by a **1.85mm rear top bridge** across the bolt towers, outside the MR128 bore; contoured arm relief is extended across Y=0.30..7.45. | Preserve the bearing bore, arm ramp, bridge, bolt paths, and carriage/belt interfaces. The sealed STL is in **assembly coordinates**, not print orientation; see below. Bridge dimensions do not prove strength or deflection. |
| **P03 front case** | 30,344.189mm3, 209 faces; **+1,041.652mm3**. Reclaimed Y=27.200..29.800 volume gives both +X receiver magnets **1.527mm rear backing** and continuous side walls. | Match the shortened P04F; the nominal 0.350mm plane gap is not every moving clearance. Magnet retention, print resolution, polarity and loaded snap behaviour remain unqualified. |
| **P04F front arm** | 3,854.094mm3, 83 faces. Face pulled back **2.550mm** to native Y=26.850mm, about 493mm2 flat area; X=19.830 outer wall and R9.35 gear clearance unified. | The **rear blind M3 pocket** at native (X14.950, Z31.400) runs Y=15.60..20.60 and leaves **6.250mm** wall to the front face. The existing 4mm M3 insert reference is retained, not an extra purchase. Confirm insertion access, pilot/knurl fit, screw engagement and material before use. |

These native dimensions are not STL-bed coordinates. The P03/P04F pair
was reviewed at **71 cam poses**, 0..175 degrees in 2.5-degree steps, with
no sampled overlaps reported; this is not continuous-motion or physical
force/deflection qualification. The final archive readback reports all
135 bodies matching. See [geometry and visual evidence limits](PREVIEW.md).

## Mesh provenance and orientation

The 17 sealed files total **482,686 facets**. Each independently checks as
one closed, manifold, coherently wound, positive-volume component with
zero degenerate triangles and no zero/inverted stored normals found.
All bytes are retained without repair, facet deletion or normal rewriting.

**P01 is an OpenCascade tessellation directly from the v26h BRep**, not a
Fusion-native STL export. It has **11,578 facets** and mesh volume
**33,771.359mm3**, versus analytic BRep volume **33,757.291mm3**:
approximately **14.07mm3 / 0.0416741%** chordal-tessellation difference,
not an exact mesh/native shape or mass match.

P01's sealed STL bounds are approximately **X=-22.50..22.50,
Y=0.30..25.90, Z=-57.279..62.221mm**. It is deliberately **not on the
print bed**. The intended flat rear-face reference is **Y=0.30mm**;
orient that face toward the bed and verify the result in a slicer. Do not
assume Z=0, auto-use the old P01 orientation, or treat a flat visible face
as proof that no supports are required. Other files retain their sealed
inspection placements, which also need review rather than blind printing.

**Inspect every mesh in a slicer** for units/scale, thin walls, surface
faceting, contact area, bridges, support access, and actual nozzle/material
resolution. A topology pass does not qualify the 21T fit, heat-set pullout,
magnet backing, bearing fits, strength, hot creep or safe loaded motion.
No slicer profile, machine settings, or G-code is included.

## Complete 17-role set

| ID | Inspection mesh | Quantity | Licence scope |
|---|---|---:|---|
| P01 | [Top-connected back case and carriage spine](stl_v26/P01_Back_case.stl) | 1 | GPL-3.0 custom work |
| P02 | [7mm motor/servo plate and rear ear-seat frame](stl_v26/P02_Motor_servo_plate.stl) | 1 | GPL-3.0 custom work |
| P03 | [Magnet-backed front receiver and cam tower](stl_v26/P03_Front_case.stl) | 1 | GPL-3.0 custom work |
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
