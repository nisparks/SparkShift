# v10 modeled hardware and print roles

> [!WARNING]
> **WIP / NOT READY FOR PRINTING OR USE.** This is a partial inspection
> reference, **not shopping, fabrication, or assembly approval**. Supplier
> parts, printed fits, snap retention, load, torque, and thermal life are
> unqualified. No prices or AliExpress Choice/delivery guarantees are provided.

This substantial, human-directed, AI-assisted **vibe developed** revision keeps
purchased hardware positions unchanged from the captured user-edited assembly.
The 143 native bodies include assemblies and display references, not 143
purchases. Credit only matching owned hardware before ordering, and do not
reuse superseded candidate pin, bearing, or fastener proposals.

## Coupling pin and backing references

| Item | Modeled qty | Inspection reference / hold |
|---|---:|---|
| Steel coupling locating pins | 6 | Nominal 1.5x5mm bought pins; captured CAD length is 4.9mm. Verify actual stock before interpreting nominal geometry as fit. |
| Integral C capture bands | 2 per pin, part of P03 | Two short bands near each pin's ends with about 1.397mm nominal mouth. No separate keeper or glue is specified; actual insertion force, snap fit, pop-out retention, stiffness, and creep are unqualified. |
| Tool locating balls | 4 | 4mm reference; all four ball-socket backing footprints are checked complete in CAD. |
| Tool/receiver magnets | 8 | 5x15x3mm references; all four receiver magnet-pocket backing footprints are complete. Physical retention and polarity still need hardware checks. |

The exposed middle steel tracks, both seating rails/lips, and axial stops are
retained. Maxwell-style coupling contact geometry is not evidence of printed
capture strength or resistance to popping out. The pin bands are printed
features, not extra purchased parts or qualified material specifications.

## Arm and cam interfaces

| Item | Modeled qty | Reference / hold |
|---|---:|---|
| Upper arm clamp | 1 | M3x10 socket-head screw. |
| Lower arm clamp | 1 | M3x14 button-head into a backed short M3 heat-set, not a loose lower hex nut. |
| Short M3 arm heat-sets | 2 | 4.6mm OD x 4mm long reference. Both pilots are 4.0mm with short tapers to 4.4mm; actual insert family and printer/material fit require calibration. |
| MG90S and supplied matching horn | 1 assembly | Selected baseline; one needed, zero to order if owned stock matches. Actual ears, spline, retaining thread, travel, and loaded torque need verification. |
| Compact-cam center retainer | 1 reference | **M2x16 REFERENCE / VERIFY ACTUAL SERVO THREAD**. Permissible engagement, supplied horn, and printed-journal fit are not verified. Do not order or force the modeled thread. |
| Cam center washer | 1 reference | 2.2mm ID x 5mm OD x 0.3mm; actual retainer/journal stack needs fitting. |
| MF85ZZ cam bearing | 1 | 5x8x2.5mm flanged reference. Seat/journal fit and retention unqualified. |
| Integral printed cam journal | Part of P05 | Captures the supplied horn as the actual spline insert; no fabricated print-ready female spline or separately purchased cam journal pin. |

The outer 6.4mm cam-driver tunnel is closed. Internal inner-ring relief and
the 5.7mm blind head/washer cavity remain, with 0.35mm nominal head axial gap.
**Preassemble the cam/horn retainer before closing the case halves**; the local
tool-top passage is not an exterior driver-access substitute.

The arm insert reference is [ruthex RX-M3Sx4.0 short M3](https://www.ruthex.de/en/products/ruthex-gewindeeinsatz-m3s-100stuck-rx-m3x4-0-short-messing-gewindebuchsen-fur-3d-druck).
That nominal pilot is not a universal M3 insert fit or pullout rating. The
[MF85ZZ manufacturer reference](https://www.lily-bearing.com/products/mf85zz/)
does not certify the printed seat or journal.

## Other unchanged modeled references

| Item | Modeled qty | Current caveat |
|---|---:|---|
| LDO-36STH20-1004AHG(XH) pancake | 1 assembly | Factory 10T input; no separate square motor, 20T pinion, or pinion grub purchase. Match the exact supplier variant. |
| HGX steel hobs / kit needles | 2 / 2 | Unmodified matching purchased geometry; physical mesh and fits unqualified. |
| Hob MF63-type supports | 4 | 3x6x2.5mm flanged references; the cam uses MF85ZZ, not a fifth MF63. |
| Remaining MF74-type supports | 3 | 4x7x2.5mm flanged references; not the earlier six-bearing proposal. |
| Rear MR74-type axle supports | 2 | Inherited bodies labelled `4x7x2`; supplier width/seat fit remains unresolved, not a verified catalog match. |
| 6700ZZ arm rear hinge | 1 | Modeled around the moving compound hub; loaded spacing and retention unqualified. |
| Compound axles | 2 references | Nonstandard modeled lengths remain open. Do not order or machine from `AXLE_4x25_fixed` / `AXLE_4x24_moving` names. |
| Hob pins | 2 | Ordinary 3x14mm reference; actual fits need calibration. |
| 623 follower / follower pin | 1 / 1 | 3x10x4mm bearing and inherited 3x10mm double-shear pin reference; distinct from the integral cam journal. |
| Closing/preload spring | 1 elastic reference | Actual rate, solid height, force, and servo/spring margin unverified. |
| Follower inner-ring shims | 2 | 3.2x5x0.5mm references; outer ring must remain free in actual hardware. |
| Preload thrust ball | 1 | 4mm reference, separate from the four tool-locating balls above. |
| PTFE inlet segment | 1 | 4mm OD x 2mm ID x 6mm reference; check the actual cold-side path. |
| HF hotend | 1 reference assembly | Eight bodies represent one hotend, including nominal nozzle/heater/thermistor references; not manufacturer-certified CAD or eight purchases. |
| MGN12H / GT2 belt interfaces | 1 carriage / 4 ends | Existing carriage and four unchanged 9mm belt ends, not four extra loops. Printed core is 45mm; real stock envelope and belt fit remain review items. |

## Selected fastener references

Different head styles and functions are not interchangeable. Modeled screw
engagement does not qualify torque, insert pullout, or assembly access.

| Location | Modeled qty | Reference |
|---|---:|---|
| Motor ears | 2 | M3x18 ISO7380 rear-entry references. |
| Motor/servo plate retainers | 2 | M3x14 socket-head references. |
| Clamshell frame | 4 + 1 | Four M3x20 references plus one M3x30 into P01. |
| Carriage / belt draw screws | 4 / 4 | M3x10 carriage and M3x16 belt references; four captive M3 belt nuts. |
| Servo mounting | 2 screws + 2 washers + 2 nuts | M2x6 socket-head, 2.2/5.0/0.3mm washers, M2 nuts; actual MG90S case/ear fit unverified. |
| Core/plate/preload heat-sets | 8 modeled entries | Legacy insert references need individual fit review; the two short-M3 arm inserts are listed separately. |
| Preload grub | 1 | M3x6 flat-point reference through pressure cup/ball/spring, not an opening stop. |
| Hotend / tool screws | 4 / 4 | M2.5x8 hotend and M3x6 tool references; follow actual supplier requirements. |
| Small tool heat-sets | 4 | Inherited tool-interface envelopes; supplier SKU and actual fit are a purchase hold. |

## 17 inspection meshes -- not ready for printing

One of each current shape; retained IDs intentionally have gaps.
**Bed orientation is not print-ready or support-free qualification.**
The arm remains two-piece P04R/P04F; no one-piece P04 is supplied.

| ID | Current review mesh | Licence scope |
|---|---|---|
| P01 | [Back case](stl_v10/P01_Back_case.stl) | GPL-3.0 custom work |
| P02 | [Motor/servo plate](stl_v10/P02_Motor_servo_plate.stl) | GPL-3.0 custom work |
| P03 | [Front case](stl_v10/P03_Front_case.stl) | GPL-3.0 custom work |
| P04R | [Swing-arm rear half](stl_v10/P04R_Swing_arm_rear_half.stl) | GPL-3.0 custom work |
| P04F | [Swing-arm front half](stl_v10/P04F_Swing_arm_front_half.stl) | GPL-3.0 custom work |
| P05 | [Servo cam](stl_v10/P05_Servo_cam.stl) | GPL-3.0 custom work |
| P06 | [Left 38T/14T compound](stl_v10/P06_Left_compound_38T_14T.stl) | GPL-3.0 custom work |
| P07 | [Right 38T/14T compound](stl_v10/P07_Right_compound_38T_14T.stl) | GPL-3.0 custom work |
| P08 | [Left 37T HGX drive](stl_v10/P08_Left_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P09 | [Right 37T HGX drive](stl_v10/P09_Right_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P12 | [Functional spring pressure cup](stl_v10/P12_Spring_pressure_cup.stl) | GPL-3.0 custom work |
| P13 | [Left GT2 tooth liner](stl_v10/P13_Left_tooth_liner.stl) | **CC BY-SA 3.0** |
| P14 | [Right GT2 tooth liner](stl_v10/P14_Right_tooth_liner.stl) | **CC BY-SA 3.0** |
| P15 | [Left belt arch](stl_v10/P15_Left_belt_arch.stl) | GPL-3.0 custom work |
| P16 | [Right belt arch](stl_v10/P16_Right_belt_arch.stl) | GPL-3.0 custom work |
| P17 | [HF tool carrier](stl_v10/P17_HF_tool_carrier.stl) | GPL-3.0 custom work |
| P18 | [Tool docking backplate](stl_v10/P18_Tool_docking_backplate.stl) | GPL-3.0 custom work |

Sensor/presence references and optional CPAP/probe provisions are not functional
accessory qualification or required purchases; those accessories stay deferred.
Generic H25T horns and alternative servos are not approved MG90S substitutes.
See [digital evidence and remaining limits](PREVIEW.md) and
[mixed-scope attribution](ATTRIBUTION.md). No physical snap retention,
strength/stiffness, loaded torque, safe operation, or hot-life claim is made.
