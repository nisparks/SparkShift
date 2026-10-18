# v26 generic per-build BOM -- one receiver plus one tool

> [!WARNING]
> **WIP / FIT PENDING / NOT READY FOR PRINTING OR USE.** This substantial,
> human-directed, AI-assisted **vibe developed** design has not qualified
> physical fits, strength, torque, retention, thermal safety, or endurance.
> This full generic reference inventory is **not purchasing, fabrication,
> or assembly approval**. HOLD means the specification is unresolved.

Quantities include all current reference requirements for **one carriage
receiver and one removable tool**, regardless of personal stock. Optional
kit contents may cover rows; do not buy/count them twice. The **135 native
bodies = 17 printed solids + 118 hardware/reference bodies**, not 135 purchases.
The [current inspection notes](PREVIEW.md) distinguish the final v26
geometry from superseded fastener and servo-mount arrangements.

## Main purchased assemblies

| Item | Per build | Reference / verification hold |
|---|---:|---|
| Extrusion motor | 1 | LDO-36STH20-1004AHG(XH) factory-10T pancake reference; verify exact variant. No separate 20T pinion or pinion grub. |
| Release servo | 1 | MG90S/MG90D reference ear-seat arrangement, **not universal clone compatibility**. Latest 11.6mm P02 window intersects the old 12.2mm envelope; measure actual body/tower/ears/leads/output before purchasing or fitting. |
| HGX hobs | 2 | Matching unmodified purchased HGX steel hobs; verify kit coverage below. |
| Closing/preload spring | 1 | Matching envelope; actual rate, preload, solid height, force, and servo margin **HOLD**. |
| HF hotend | 1 complete assembly | Red Lizard HF/K1-heatsink/Volcano-envelope CAD references: eight reference bodies, **not eight purchases or a maker-certified mixed SKU**. Use a compatible supplier system and its ratings. |
| MGN12H carriage | 1 | Match actual rail/carriage and mounting envelope; rail length is printer-dependent. |
| 9mm GT2 belt interface | 4 ends | Four ends, **not four loops**; routing and total length are printer-dependent. |
| Bare A1104-family Hall sensor | 1 reference | Three-lead package, **not a PCB module**. Actual electrical variant, wiring, positive support, and retention remain **HOLD**. |

The direct printed cam/hub uses **no OEM horn**. The inspected reference
output was 21T, 4.86mm crest OD, 3.36mm exposed spline height, M2.5 centre
thread. The historical 4.62mm root/sinusoidal flank and +0.025mm normal
allowance are empirical trials, not manufacturer-standard teeth or a
universal fit. Measure the actual unit and final retainer stack.

## All 15 bearing references

Dimensions are ID x OD x width in millimetres. Match flange/shoulder
details as well as nominal dimensions. Internal motor/servo bearings
are not separate items in this count.

| Bearing / role | Per build | Reference / hold |
|---|---:|---|
| MF63ZZ flanged supports | 4 | 3x6x2.5mm; match flange and seat. |
| MF74ZZ flanged supports | 3 | 4x7x2.5mm. |
| 623ZZ cam follower | 1 | 3x10x4mm; separate from its pin and two inner-ring shims. |
| MR128ZZ rear cam support | 1 | **8x12x3.5mm**, Y=-1.05..2.45, captured across P02/P01; fit/retention unqualified. |
| MF85ZZ front cam support | 1 | **5x8x2.5mm**, Y=10.70..13.20, in P03's front cam tower. |
| 6700ZZ arm hinge | 1 | 10x15x4mm; loaded spacing/retention unqualified. |
| Matching HGX needle bearings | 2 | 3x5x7mm references; confirm actual hob kit needles. |
| Rear MR74-type supports | 2 | **HOLD: modelled 4x7x2mm. Common MR74ZZ is 2.5mm wide and is not drop-in.** |
| **Total, including needles** | **15** | Includes both external cam bearings; kit-supplied matching bearings satisfy rows, not an additional set. |

## HGX Lite kit: possible coverage, not extra inventory

The illustrated bundle contains two hobs, two needles, two loose ball
bearings, three pins, a spring, thumb adjuster, washer, and stock input gear.
It **may cover** corresponding hob/needle/support/pin/spring requirements
only after actual dimensions and quantities are checked. Do not assume
loose bearings or pins match a row. Kit and standalone items are not
double-counted. Its thumb adjuster/washer/input gear are not automatically
the printed preload assembly, cam washer, or factory-10T motor input.

[AliExpress item 3256808598360212](https://www.aliexpress.com/item/3256808598360212.html)
is an illustration/variant reference, **not a verified buy link**: anonymous
variant dimensions were login-blocked. No pricing, availability, delivery,
dimension, or complete-kit compatibility is guaranteed.

## Shafts, pins, balls, magnets, and spacers

| Item | Per build | Reference / hold |
|---|---:|---|
| 4mm compound shafts | 2 | **HOLD: standard lengths unresolved.** Modelled 26.3mm / 24.9mm and inherited `4x25` / `4x24` names are **not buy/cut dimensions**. No shaft-machining recipe. |
| HGX hob pins | 2 | 3x14mm reference; verify kit stock and fits. |
| Follower pin | 1 | 3x10mm for 623ZZ; not a cam journal pin. |
| Coupling locating pins | 6 | Steel nominal 1.5x5mm; CAD length 4.9mm, in YUDX-matched teardrop snap seats. Actual press/snap force and retention unqualified. |
| Steel 4mm balls | 5 | Four tool locating balls plus one spring thrust ball. |
| Bar magnets | 8 | 15x5x3mm, four receiver plus four tool; grade, polarity, retention, and paired placement require checks. |
| Hall trigger disc magnet | 1 | 4x2mm reference, distinct from the eight coupling bars. |
| Follower inner-ring shims | 2 | M3-size reference, approximately 3.2mm ID / 5mm OD / 0.5mm thick; keep outer ring free. |
| Cam retainer washer | 1 | 2.7mm ID / 6mm OD / 0.5mm thick, Y=13.70..14.20. No servo-ear washer row. |
| PTFE inlet segment | 1 | 4mm OD / 2mm ID / 6mm length reference; actual path fit unqualified. |

Disc magnets 6x3/6x4 remain **research only**; they are not redesigned
default pockets. YUDX-matched pin seats do not certify every magnet/coupling
alignment or the unfinished broader 0.05mm placement grid.

## Full fastener inventory

Lengths and head styles are CAD references, not approved thread engagement
or supplier specifications. There are **29 screw references**, plus four
belt nuts; do not add retired v16 rows.

| Location | Per build | Reference |
|---|---:|---|
| Cam centre retainer | 1 | **M2.5x16 socket-head**, with the cam washer above; verify actual thread, stack, and blind depth. |
| Servo rear ears | 2 | **M2x8 self-tapping**, into P02's 1.7mm pilots at X10.50 / Z59.04 and Z31.54; ear seats Y=-11.20. Not M2x6 machine screws. |
| Motor ears | 2 | **M3x10 button head**, threads into motor flange ears; not old M3x18. |
| Plate-to-P01 retainer | 1 | **M3x10 button head**, (X17.25, Z23.72), into P01 heat-set. |
| Upper-left case clamp | 1 | **M3x30 button head**, (X18.10, Z41.72), into P01 heat-set. |
| Upper-right case clamp | 1 | **M3x35 button head**, (X-18.10, Z41.72), into rear-loaded P02 heat-set. |
| Lower-left case clamp | 1 | **M3x25 button head**, (X18.50, Z-14.60), into P01 heat-set. |
| Lower-right case clamp | 1 | **M3x35 button head**, (X-18.50, Z-14.45), into front-loaded P02 heat-set. |
| Upper arm clamp | 1 | M3x10 socket-head, into backed M3 heat-set. |
| Lower arm clamp | 1 | M3x14 button head, into backed M3 heat-set, not a loose nut. |
| Carriage mount | 4 | M3x10 socket-head. |
| Belt draw screws | 4 | M3x16, paired with four captive M3 belt nuts. |
| Spring preload | 1 | M3x6 flat-point grub through pressure cup/ball/spring. |
| Hotend mount | 4 | Original M2.5x8 reference; P17 interface retained. |
| Tool screws | 4 | M3x6. |
| Belt nuts | 4 | M3 hex nuts, already paired with belt draw screws; **not case nuts**. |

All four case-bolt heads have modelled **2.0mm AF x 0.9mm** hex sockets;
verify real head/tool access rather than treating simplified CAD as a
supplier drawing. The lower-right axis is intentionally **0.15mm higher**
than an exact lower mirror to preserve heat-set wall thickness.

**No servo-ear M2 nuts, M2 washers, or M2 heat-sets** are required by the
current reference; two self-tappers replace that old arrangement.
**No separate upper-frame screw**, second plate retainer, M3x40 case
bolt, or top-down clamp trial is added to the four current corner clamps.
Historical functions/body names are not additional purchases.

The exposed **3.36mm spline height is not usable blind thread depth**.
Measure the actual M2.5 screw/thread and the final cam/bearing/washer stack
before tightening; do not force a bottomed screw or reuse an old nominal
engagement calculation as v26 fit approval.

## Full heat-set inventory -- 12 M3 references

| Location | Per build | Reference / host |
|---|---:|---|
| Four corner case clamps | 4 | M3, 4mm long / 4.6mm OD reference; upper-left and lower-left in P01, upper-right rear-loaded and lower-right front-loaded in P02. |
| Plate-to-P01 retainer | 1 | M3, 4mm long / 4.6mm OD, P01 Y=0.30..4.30. |
| Spring preload | 1 | M3, 4mm long / 4.6mm OD reference; retains separate axis/backing. |
| Arm split clamps | 2 | M3, 4mm long / 4.6mm OD references; verify pilot/material and loaded retention. |
| Small tool inserts | 4 | Inherited small M3 envelopes; supplier family/SKU and pilot compatibility **HOLD**. |
| **Total M3 insert entries** | **12** | Six core/plate/preload, two arm, four tool; not twelve interchangeable inserts. |

No M2 servo heat-sets are added. Lower accessory bosses are **future mounting
interfaces**, not extra installed insert purchases in this core count.
Actual pilot/knurl fit, access, seating, torque, and pullout are unqualified.
Plan insert/bearing installation before closing their respective covers;
see [case-stack inspection notes](PREVIEW.md).

## Printed and printer-dependent requirements

One of each **17 print roles** belongs to the matched v26 set. P04 is split;
P05 includes the direct hub, not an extra horn. The raw native inspection
meshes total **568,066 facets**, with one closed/wound/manifold positive
component each, no degenerates, and no zero/inverted stored normals found.
Bytes are not repaired or rewritten. **Inspect each mesh in a slicer**;
digital topology does not qualify supports, material, spline resolution,
hot creep, loaded strength, or safe use. **NOT READY FOR PRINTING.**

| ID | Print role | Licence scope |
|---|---|---|
| P01 | [Open-frame back case and carriage spine](stl_v26/P01_Back_case.stl) | GPL-3.0 custom work |
| P02 | [7mm motor/servo plate and rear ear-seat frame](stl_v26/P02_Motor_servo_plate.stl) | GPL-3.0 custom work |
| P03 | [Open receiver/front case and cam tower](stl_v26/P03_Front_case.stl) | GPL-3.0 custom work |
| P04R | [Swing-arm rear half with shortened manual lever](stl_v26/P04R_Swing_arm_rear_half.stl) | GPL-3.0 custom work |
| P04F | [Swing-arm front half](stl_v26/P04F_Swing_arm_front_half.stl) | GPL-3.0 custom work |
| P05 | [Direct-output cam/hub, FIT PENDING](stl_v26/P05_Servo_cam.stl) | GPL-3.0 custom work |
| P06 | [Left 38T/14T compound](stl_v26/P06_Left_compound_38T_14T.stl) | GPL-3.0 custom work |
| P07 | [Right 38T/14T compound](stl_v26/P07_Right_compound_38T_14T.stl) | GPL-3.0 custom work |
| P08 | [Left 37T HGX drive](stl_v26/P08_Left_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P09 | [Right 37T HGX drive](stl_v26/P09_Right_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P12 | [Spring pressure cup](stl_v26/P12_Spring_pressure_cup.stl) | GPL-3.0 custom work |
| P13 | [Left GT2 tooth liner](stl_v26/P13_Left_tooth_liner.stl) | **CC BY-SA 3.0** |
| P14 | [Right GT2 tooth liner](stl_v26/P14_Right_tooth_liner.stl) | **CC BY-SA 3.0** |
| P15 | [Left belt arch](stl_v26/P15_Left_belt_arch.stl) | GPL-3.0 custom work |
| P16 | [Right belt arch](stl_v26/P16_Right_belt_arch.stl) | GPL-3.0 custom work |
| P17 | [HF tool carrier](stl_v26/P17_HF_tool_carrier.stl) | GPL-3.0 custom work |
| P18 | [Tool docking backplate](stl_v26/P18_Tool_docking_backplate.stl) | GPL-3.0 custom work |

Wiring, connectors, strain relief, signal/control interface, and adequately
sized regulated **5V servo power/common ground** are printer-dependent;
verify the selected servo and supply. A controller signal pin is not a motor
power supply. Heater/sensor wiring and thermal protection follow the actual
compatible supplier/printer system, not the reference geometry.

**EBB42, Beacon/Cartographer, CPAP duct/collar, hose, and blower mounting are
next-session plans**, not mandatory core purchases or included finished
prints. Select actual revisions and dimensions before adding accessory
hardware to this BOM; see the [accessories plan](ACCESSORIES_PLAN.md).

Read [mixed-scope attribution](ATTRIBUTION.md): GPL/CC BY-SA notices and
upstream authorship remain intact, and vendor/hotend references retain
their respective rights. No personal owned/order quantities, prices, or
remaining-shopping deductions are part of this generic inventory.
