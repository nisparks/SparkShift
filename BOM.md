# v9 modeled hardware and print roles

> [!WARNING]
> **WIP / NOT READY FOR PRINTING OR USE.** This is an inspection reference,
> **not an approved shopping list, complete build BOM, or assembly guide**.
> Exact supplier parts, printed fits, retention, torque, and thermal life are
> unqualified. No prices or AliExpress Choice/delivery claims are provided.

This human-directed, AI-assisted **vibe developed** revision supersedes the
earlier draft hardware tables. Quantities below identify modeled assemblies
and selected interfaces, not automatically verified purchases. The 143 native
bodies are not 143 purchases: the motor, servo, and hotend each have multiple
reference bodies. Credit only matching owned hardware before ordering.

## Current arm and cam references

| Item | Modeled qty | Reference / hold |
|---|---:|---|
| Upper arm clamp | 1 | M3x10 socket-head screw. |
| Lower arm clamp | 1 | M3x14 button-head screw into a backed heat-set; not the old through-bolt/loose nut. |
| Short M3 arm heat-sets | 2 | 4.6mm OD x 4mm long reference, one per clamp. Both pilots are 4.0mm with 0.4mm-long tapers to 4.4mm; printer/material/insert fit is unverified. |
| MG90S with its supplied matching horn | 1 assembly | Selected baseline; one needed, zero to order if owned stock matches. Actual ears, spline, retaining thread, travel, and loaded torque need verification. |
| Compact-cam center retainer | 1 reference | **M2x16 REFERENCE ONLY**. Actual servo thread, permissible engagement, and horn/printed-journal fit are **not verified**; do not order by the modeled thread. |
| Cam center washer | 1 reference | 2.2mm ID x 5mm OD x 0.3mm; actual retainer/journal stack requires fitting. |
| MF85ZZ cam bearing | 1 | 5x8x2.5mm flanged reference; the separate cam journal pin and old cam MF63 are not current items. |
| Integral printed cam journal | Part of P05 | Not a separately purchased shaft or a fabricated print-ready female spline. The supplied horn provides the actual servo spline connection. |

The arm insert reference is [ruthex RX-M3Sx4.0 short M3](https://www.ruthex.de/en/products/ruthex-gewindeeinsatz-m3s-100stuck-rx-m3x4-0-short-messing-gewindebuchsen-fur-3d-druck).
Match the actual insert family; do not apply its nominal hole to every legacy
core pilot or claim pullout strength from CAD wall thickness. The
[MF85ZZ manufacturer reference](https://www.lily-bearing.com/products/mf85zz/)
does not certify the printed seat or journal.

## Other modeled hardware references

| Item | Modeled qty | Current caveat |
|---|---:|---|
| LDO-36STH20-1004AHG(XH) pancake motor | 1 assembly | Factory 10T input. No separate square NEMA14, factory 5x24mm shaft, 20T pinion, or pinion grub purchase. Match the exact supplier variant. |
| Purchased HGX steel hobs / kit needles | 2 / 2 | Unmodified matching kit geometry; physical mesh and bearing fits unqualified. |
| Hob support MF63-type bearings | 4 | 3x6x2.5mm flanged references. The cam uses MF85ZZ, not a fifth MF63. |
| Remaining MF74-type supports | 3 | 4x7x2.5mm flanged references; do not reuse an old six-bearing count. |
| Rear MR74-type axle supports | 2 | The inherited bodies are labelled `4x7x2`; actual supplier width/seat fit is unresolved, not an approved catalog match or four-rotor-bearing proposal. |
| 6700ZZ arm rear hinge | 1 | Modeled around the moving compound hub; loaded spacing and retention need physical validation. |
| Compound axles | 2 references | Nonstandard modeled lengths remain unresolved. Do not order or machine from internal `AXLE_4x25_fixed` / `AXLE_4x24_moving` names. |
| Hob pins | 2 | Ordinary 3x14mm reference; calibrate actual fits. |
| 623 follower / follower pin | 1 / 1 | 3x10x4mm bearing and inherited 3x10mm double-shear pin reference, distinct from the compact cam's integral journal. Physical capture/retention unqualified. |
| Closing/preload spring | 1 elastic reference | Actual rate, solid height, grip force, and spring/servo margin unverified. |
| Follower inner-ring shims | 2 | 3.2x5x0.5mm reference; actual stack must allow the outer ring to turn. |
| Steel balls / locating pins | 5 / 6 | 4mm balls and 1.5x5mm pins; actual tool/preload fits need validation. |
| Tool/receiver magnets | 8 | 5x15x3mm references with retained backing; size, retention, and polarity require hardware checks. |
| PTFE inlet segment | 1 | 4mm OD x 2mm ID x 6mm reference; check the actual cold-side path. |
| HF hotend | 1 reference assembly | Eight CAD bodies represent one hotend, including nominal nozzle/heater/thermistor references; not eight purchases or manufacturer-certified CAD. |
| MGN12H / GT2 belt interfaces | 1 carriage / 4 ends | Existing carriage and four unchanged 9mm belt ends, not four extra loops. Printed core is 45mm; stock-inclusive envelope and real belt fit remain review items. |

## Selected fastener references

Keep different head styles and functions separate. These current native names
do not qualify screw engagement, torque, insert pullout, or assembly access.

| Location | Modeled qty | Reference |
|---|---:|---|
| Motor ears | 2 | M3x18 ISO7380 rear-entry references. |
| Motor/servo plate retainers | 2 | M3x14 socket-head references, not the earlier three M3x10 plate-retainer proposal. |
| Clamshell frame | 4 + 1 | Four M3x20 references plus one M3x30 into P01. |
| Carriage / belt draw screws | 4 / 4 | M3x10 carriage and M3x16 belt references; four captive M3 belt nuts. |
| Servo mounting | 2 screws + 2 washers + 2 nuts | M2x6 socket-head, 2.2/5.0/0.3mm washers, M2 nuts. Actual MG90S case/ear fit remains unverified. |
| Core/plate/preload heat-sets | 8 modeled entries | Legacy insert references require their own fit review; the two short-M3 arm inserts are listed separately above. |
| Preload grub | 1 | M3x6 flat-point reference acting through the pressure cup/ball/spring, not an arm-closing stop. |
| Hotend / tool screws | 4 / 4 | M2.5x8 hotend and M3x6 tool references; follow actual supplier requirements. |
| Small tool heat-sets | 4 | Smaller inherited tool-interface references; supplier SKU and actual fit are a purchase hold. |

Sensor/presence references and optional CPAP/probe-adapter provisions do not
establish accessory functionality or required purchases. Those accessories
remain deferred. A higher-torque alternative servo or generic H25T metal horn
is not an approved MG90S substitute. The retained supplied-horn/printed-cam
path is not a durability-qualified all-metal design.

## 17 inspection meshes -- not ready for printing

One of each current shape; retained IDs intentionally have gaps.
**Bed orientation is not support-free or print-ready qualification.**
The arm is split into P04R/P04F; no one-piece P04 mesh is included.

| ID | Current review mesh | Licence scope |
|---|---|---|
| P01 | [Back case](stl_v9/P01_Back_case.stl) | GPL-3.0 custom work |
| P02 | [Motor/servo plate](stl_v9/P02_Motor_servo_plate.stl) | GPL-3.0 custom work |
| P03 | [Front case](stl_v9/P03_Front_case.stl) | GPL-3.0 custom work |
| P04R | [Swing-arm rear half](stl_v9/P04R_Swing_arm_rear_half.stl) | GPL-3.0 custom work |
| P04F | [Swing-arm front half](stl_v9/P04F_Swing_arm_front_half.stl) | GPL-3.0 custom work |
| P05 | [Servo cam](stl_v9/P05_Servo_cam.stl) | GPL-3.0 custom work |
| P06 | [Left 38T/14T compound](stl_v9/P06_Left_compound_38T_14T.stl) | GPL-3.0 custom work |
| P07 | [Right 38T/14T compound](stl_v9/P07_Right_compound_38T_14T.stl) | GPL-3.0 custom work |
| P08 | [Left 37T HGX drive](stl_v9/P08_Left_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P09 | [Right 37T HGX drive](stl_v9/P09_Right_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P12 | [Functional spring pressure cup](stl_v9/P12_Spring_pressure_cup.stl) | GPL-3.0 custom work |
| P13 | [Left GT2 tooth liner](stl_v9/P13_Left_tooth_liner.stl) | **CC BY-SA 3.0** |
| P14 | [Right GT2 tooth liner](stl_v9/P14_Right_tooth_liner.stl) | **CC BY-SA 3.0** |
| P15 | [Left belt arch](stl_v9/P15_Left_belt_arch.stl) | GPL-3.0 custom work |
| P16 | [Right belt arch](stl_v9/P16_Right_belt_arch.stl) | GPL-3.0 custom work |
| P17 | [HF tool carrier](stl_v9/P17_HF_tool_carrier.stl) | GPL-3.0 custom work |
| P18 | [Tool docking backplate](stl_v9/P18_Tool_docking_backplate.stl) | GPL-3.0 custom work |

See [digital evidence and limitations](PREVIEW.md) and
[mixed-scope attribution](ATTRIBUTION.md). This inspection BOM is not proof of
physical strength, loaded torque, retention, thermal safety, or hot-life.
