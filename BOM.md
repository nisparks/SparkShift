# v12 modeled hardware and print roles

> [!WARNING]
> **WIP / NOT READY FOR PRINTING OR USE.** This is a partial inspection
> reference, **not shopping, fabrication, or assembly approval**. Supplier
> parts, printed fits, snap retention, load, torque, and thermal life are
> unqualified. No prices or AliExpress Choice/delivery guarantees are provided.

This substantial, human-directed, AI-assisted **vibe developed** revision
retains the original toolhead and all four M2.5x8 hotend mounts. The approved
143-body assembly includes references and purchased assemblies, not 143
purchases. The matched v12 inspection set has fresh native/STEP readbacks
and 17 mesh gates; all quantities below are modeled references, not
supplier, fit, torque, or buying approval.

## Flush heads and distinct insert hosts

| Item | Modeled qty | Inspection reference / hold |
|---|---:|---|
| Four case-clamp screws | 3 + 1 | **Three M3x25 (FRAME_0/1/2) and one M3x40 (FRAME_3)**. No current M3x20 case-clamp or 35mm lower-left trial. |
| Separate upper frame screw | 1 | **M3x35** into P01's frame insert; actual head and hex socket are present. Not an additional case clamp. |
| Case-clamp M3 heat-sets | 4 | Real heat-sets, no captive-nut substitution. FRAME_3's host is purple P02, not blue P01; count the relocated insert once. |
| Lower-right FRAME_2 screw / insert | 1 of the four above | Unchanged fifth head reference; M3x25 on X18.2/Z-13.7, seat Y31.5, tip Y6.5; 4.6mm OD x 4mm insert at Y6..10 in P01. |
| Rear-loaded backed insert seat | Printed case feature | 4.0mm pilot / 4.8mm outside-rear counterbore; 1.6mm prepared radial wall, 1.6mm forward backing, and 2.0mm material outside the full insert. Native footprint missing volume 0. |
| Lower-left FRAME_3 screw / insert | 1 of the four above | M3x40, insert in P02 at X-16/Z-13, Y-3.7..0.3; blue P01 is the through-clearance sandwiched member. Raised axis does not extend purple lower bound Z-17.78. |
| FRAME_3 front capture / pilot stock | Printed stack features | Blue annulus 1.6mm deep, 3.3mm through diameter below insert OD 4.6mm, missing material 0; purple radial stock 1.6mm, missing material 0. Not insert-fit, pullout, or load certification. |
| Spring-preload M3 heat-set | 1, included below | Original insert, grub/ball, axis, and backing retained; distinct from the lower-right case clamp and arm inserts. |
| Original HF hotend mounting screws | 4 | Original M2.5x8 references and axes/tips exactly restored; no shorter-screw substitution or lowered P17 shelf/counterbores. Actual supplier threads and torque unverified. |

Four targeted heads move +1.70mm to **Y33.15 flush plane / Y31.5 seats**,
matching the unchanged FRAME_2 fifth. Their standard lengths/blind-tip
clearances preserve full 4mm nominal target-insert engagement; FRAME_2's
separate nominal 3.5mm reference remains. No vendor thread/torque claim.

**FRAME_2:** rear-load the bare P01 insert before actuator/motor plate closure.
**FRAME_3:** front-load the bare purple P02 insert before blue P01 assembly.
**Spring adjuster:** bench-install in the bare front case before case and
arm/spring/ball closure. The 10mm-heater / 7mm-shaft / 4.6mm-end envelope
is a stated reference, not universal actual-iron compatibility. Actual
heat-staking, pilot/printer fit, and physical retention remain unqualified. See
[snapshot and assembly-order limits](PREVIEW.md).

## Coupling pin and backing references

| Item | Modeled qty | Inspection reference / hold |
|---|---:|---|
| Steel coupling locating pins | 6 | Nominal 1.5x5mm bought pins; captured CAD length is 4.9mm. Verify actual stock before interpreting nominal geometry as fit. |
| Integral C capture bands | 2 per pin, part of P03 | Two short bands near each pin's ends with about 1.397mm nominal mouth. No separate keeper or glue is specified; actual insertion force, snap fit, pop-out retention, stiffness, and creep are unqualified. |
| Tool locating balls | 4 | 4mm references; complete shared-datum paired docking symmetry and 0.05mm grid are unfinished, not placement approval. |
| Tool/receiver magnets | 8 | 5x15x3mm references; exact paired placement symmetry, polarity, and physical retention remain unqualified. No mirrored/centered result is claimed from a model title. |

The exposed middle steel tracks, both seating rails/lips, and axial stops are
retained. Maxwell-style coupling contact geometry is not evidence of printed
capture strength or resistance to popping out. The pin bands are printed
features, not extra purchased parts or qualified material specifications.
Four central path-wall plane edits are applied, not verification that every
contact/pocket is centered. Do not round vendor gears or fit clearances to
the nominal placement grid or force gear internals symmetric.

| Sensor reference | Current limitation |
|---|---|
| Hall sensor / lead slot | Old package slot and lead geometry retained. Actual case cross-web is not a positive package cradle or retainer; no such holder is installed or qualified. |

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
| Carriage / belt draw screws | 4 / 4 | M3x10 carriage and M3x16 belt references; four captive M3 belt nuts. |
| Servo mounting | 2 screws + 2 washers + 2 nuts | M2x6 socket-head, 2.2/5.0/0.3mm washers, M2 nuts; actual MG90S case/ear fit unverified. |
| Core/plate/preload heat-sets | 8 modeled entries | Four case-clamp, upper-frame, two plate, and spring-preload references; FRAME_3's relocation does not add an insert. Two short-M3 arm inserts are separate; actual fits unqualified. |
| Preload grub | 1 | M3x6 flat-point reference through pressure cup/ball/spring, not an opening stop. |
| Tool screws | 4 | Retained M3x6 references; four original hotend M2.5x8 mounts are listed above. Follow actual supplier requirements. |
| Small tool heat-sets | 4 | Inherited tool-interface envelopes; supplier SKU and actual fit are a purchase hold. |

## 17 inspection meshes -- not ready for printing

One of each current shape; retained IDs intentionally have gaps.
**Bed orientation is not print-ready or support-free qualification.**
The arm remains two-piece P04R/P04F; no one-piece P04 is supplied.

| ID | Current review mesh | Licence scope |
|---|---|---|
| P01 | [Back case](stl_v12/P01_Back_case.stl): rear-loaded FRAME_2, through-clearance FRAME_3 | GPL-3.0 custom work |
| P02 | [Motor/actuator plate](stl_v12/P02_Motor_servo_plate.stl) with captured front-loaded FRAME_3 insert | GPL-3.0 custom work |
| P03 | [User-refined front case](stl_v12/P03_Front_case.stl) and functional openings | GPL-3.0 custom work |
| P04R | [Swing-arm rear half](stl_v12/P04R_Swing_arm_rear_half.stl) | GPL-3.0 custom work |
| P04F | [Swing-arm front half](stl_v12/P04F_Swing_arm_front_half.stl) | GPL-3.0 custom work |
| P05 | [Servo cam](stl_v12/P05_Servo_cam.stl) | GPL-3.0 custom work |
| P06 | [Left 38T/14T compound](stl_v12/P06_Left_compound_38T_14T.stl) | GPL-3.0 custom work |
| P07 | [Right 38T/14T compound](stl_v12/P07_Right_compound_38T_14T.stl) | GPL-3.0 custom work |
| P08 | [Left 37T HGX drive](stl_v12/P08_Left_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P09 | [Right 37T HGX drive](stl_v12/P09_Right_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P12 | [Spring pressure cup](stl_v12/P12_Spring_pressure_cup.stl) | GPL-3.0 custom work |
| P13 | [Left GT2 tooth liner](stl_v12/P13_Left_tooth_liner.stl) | **CC BY-SA 3.0** |
| P14 | [Right GT2 tooth liner](stl_v12/P14_Right_tooth_liner.stl) | **CC BY-SA 3.0** |
| P15 | [Left belt arch](stl_v12/P15_Left_belt_arch.stl) | GPL-3.0 custom work |
| P16 | [Right belt arch](stl_v12/P16_Right_belt_arch.stl) | GPL-3.0 custom work |
| P17 | [Original HF tool carrier](stl_v12/P17_HF_tool_carrier.stl); unchanged shelf/counterbores | GPL-3.0 custom work |
| P18 | [Tool docking backplate](stl_v12/P18_Tool_docking_backplate.stl) | GPL-3.0 custom work |

CPAP/probe provisions remain deferred, not required purchases. The existing
Hall slot/lead reference still needs positive package-support qualification.
Generic H25T horns and alternative servos are not approved MG90S substitutes.
See [snapshot and remaining limits](PREVIEW.md) and
[mixed-scope attribution](ATTRIBUTION.md). No physical snap retention,
strength/stiffness, loaded torque, safe operation, or hot-life claim is made.
