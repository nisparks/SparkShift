# v16 generic per-build BOM -- one receiver plus one tool

> [!WARNING]
> **WIP / FIT PENDING / NOT READY FOR PRINTING OR USE.** This substantial,
> human-directed, AI-assisted **vibe developed** design has not qualified
> physical fits, strength, torque, retention, thermal safety, or endurance.
> This is a full generic reference inventory, **not purchasing, fabrication,
> or assembly approval**. HOLD means the specification is unresolved.

Quantities include every modeled requirement for **one carriage receiver
and one removable tool**, regardless of parts a particular builder has.
Optional kit contents are possible coverage of these rows, not additional
parts to buy twice. The 142-body prototype includes multi-body references,
not 142 purchases. Actual supplier variants and head styles must match.

## Main purchased assemblies

| Item | Per build | Specification / verification hold |
|---|---:|---|
| Extrusion motor | 1 | LDO-36STH20-1004AHG(XH) factory-10T pancake reference; exact variant required. No separate 20T pinion or pinion grub. |
| Release servo | 1 | MG90S-family reference, **not all clones interchangeable**. Independently verify 21T, 4.86mm crest OD, 3.36mm exposed height, M2.5 thread, ears/boss datum, stroke, and clocking. |
| HGX hobs | 2 | Matching, unmodified purchased HGX steel hobs; kit coverage below. Needles and supports remain separate inventory rows. |
| Closing/preload spring | 1 | Matching mechanical envelope required; actual rate, preload, solid height, force, and servo margin **HOLD**. |
| HF hotend | 1 complete assembly | Eight CAD reference bodies, **not eight purchases** or a maker-certified mixed SKU. Select compatible heater, temperature sensor, nozzle, heatbreak, and ratings as a complete supplier system. |
| MGN12H carriage | 1 | Match the actual rail/carriage and mounting envelope; linear rail length is printer-dependent. |
| 9mm GT2 belt interface | 4 ends | Four ends, **not four loops**; routing and total belt length are printer-dependent. |
| Bare A1104-family Hall sensor | 1 reference | Three-lead package, not a PCB module. Electrical variant/lead wiring and positive package cradle/retention **HOLD**; cross-web is not a qualified holder. |

The 21T count/crest OD/exposed height/thread describe the inspected reference
unit only. Root diameter 4.62mm and sinusoidal flank form are photo-estimated
fit trials with +0.025mm normal clearance, not certified teeth or universal
printed fits. There is **no OEM horn**; P05 is one printed cam plus hub.

## All 14 bearing references

Dimensions below are ID x OD x width in millimeters; flange/shoulder details
also need matching. Bearings inside supplied motor/servo assemblies are not
separate service items in this count.

| Bearing / role | Per build | Reference / hold |
|---|---:|---|
| MF63ZZ flanged supports | 4 | 3x6x2.5mm; match flange and seat. |
| MF74ZZ flanged supports | 3 | 4x7x2.5mm; do not reuse an earlier six-bearing count. |
| 623ZZ cam follower | 1 | 3x10x4mm; distinct from its pin and two shims. |
| MF85ZZ cam journal | 1 | 5x8x2.5mm; printed 4.95mm journal and fit/retention unqualified. |
| 6700ZZ arm hinge | 1 | 10x15x4mm reference; loaded spacing/retention unqualified. |
| Matching HGX needle bearings | 2 | 3x5x7mm references; confirm the actual hob kit needles. |
| Rear MR74-type supports | 2 | **HOLD: modeled 4x7x2mm. Common MR74ZZ is 2.5mm wide and is not drop-in.** Supplier width/seat compatibility remains unresolved. |
| **Total, including needles** | **14** | Kit-supplied matching items satisfy rows above; they do not increase this total. |

## HGX Lite kit: possible coverage, not extra inventory

The illustrated bundle contains two hobs, two needles, two loose ball
bearings, three pins, a spring, thumb adjuster, washer, and stock input gear.
It **may cover** corresponding hob/needle/support/pin/spring requirements
only after dimensions and quantities are checked. Do not assume the loose
bearings or pins match any specific row, or count kit items and standalone
items twice. Thumb adjuster/washer/input gear are not automatically the
current printed preload assembly, M2.5 cam washer, or factory-10T input.

[AliExpress item 3256808598360212](https://www.aliexpress.com/item/3256808598360212.html)
is an illustration/variant reference, **not a verified buy link**: anonymous
variant dimensions were login-blocked. No prices, Choice status, dimensions,
availability, delivery, or complete-kit compatibility are guaranteed.

## Shafts, pins, balls, magnets, and spacers

| Item | Per build | Reference / hold |
|---|---:|---|
| 4mm compound shafts | 2 | **HOLD: standard lengths unresolved.** Modeled 26.3mm / 24.9mm lengths and old `4x25` / `4x24` names are **not buy/cut dimensions**. No shaft-machining instructions. |
| HGX hob pins | 2 | Ordinary 3x14mm reference; verify actual kit stock and fits. |
| Follower pin | 1 | 3x10mm reference for 623ZZ; not a cam journal pin. |
| Coupling locating pins | 6 | Steel nominal 1.5x5mm; CAD length 4.9mm. Printed lips/rails/stops need actual snap-force/fit/retention qualification. |
| Steel 4mm balls | 5 | Four tool locating balls plus one spring thrust ball; not two extra sets. |
| Bar magnets | 8 | 5x15x3mm, four receiver plus four tool. Actual grade, polarity, retention, and paired placement require checks. |
| Hall trigger disc magnet | 1 | 4x2mm reference; distinct from the eight coupling bars. |
| Follower inner-ring shims | 2 | 3.2mm ID / 5mm OD / 0.5mm thick; keep outer ring free. |
| Cam retainer washer | 1 | 2.7mm ID / 6mm OD / 0.5mm thick, not the servo-ear washer. |
| Servo-ear washers | 2 | 2.2mm ID / 5mm OD / 0.3mm thick. |
| PTFE inlet segment | 1 | 4mm OD / 2mm ID / 6mm length reference; actual cold-side path fit unqualified. |

Disc magnets 6x3/6x4 are **research only**, not redesigned pockets or build
defaults. The public reference remains eight bars plus the separate trigger
disc. Paired Maxwell/magnet centering and the 0.05mm placement grid are
unfinished; do not round vendor fits or gear internals to that grid.

## Full fastener inventory

Different head styles/functions are not interchangeable. Lengths are nominal
CAD references, not verified screw engagement, torque, or actual supplier fit.

| Location | Per build | Reference |
|---|---:|---|
| Cam center retainer | 1 | **M2.5x16 socket-head** envelope; coarse 0.45mm pitch assumed. Check actual thread and usable blind depth below. |
| Servo ears | 2 | M2x6 socket-head, with two M2 nuts and two ear washers above. |
| Motor ears | 2 | M3x18 ISO7380 button-head references. |
| Motor/actuator plate retainers | 2 | M3x14 socket-head. |
| Case clamps FRAME_0/1/2 | 3 | M3x25 socket-head. |
| Case clamp FRAME_3 | 1 | M3x40 socket-head into P02 insert, not a 35mm trial. |
| Separate upper frame | 1 | M3x35 into P01 insert; not an extra case-clamp row. |
| Upper arm clamp | 1 | M3x10 socket-head. |
| Lower arm clamp | 1 | M3x14 button-head into backed short M3 insert, not a loose nut. |
| Carriage mount | 4 | M3x10. |
| Belt draw screws | 4 | M3x16, with four captive M3 belt nuts. |
| Spring preload | 1 | M3x6 flat-point grub through pressure cup/ball/spring. |
| Hotend mount | 4 | Original M2.5x8; P17 shelf/counterbores retained, no short-bolt proposal. |
| Tool screws | 4 | M3x6. |
| Servo-ear nuts | 2 | M2, already paired with the two M2x6 screws above. |
| Belt nuts | 4 | M3, already paired with four belt draw screws above; not case nuts. |

With the selected center screw and washer, nominal retainer thread
engagement is **2.96mm**. **Measure actual usable blind depth >=3.16mm
before tightening**; external 3.36mm spline height is not blind depth.
Do not force a bottomed screw. The 2.9mm passage leaves a 1.025mm radial
wall in the 4.95mm journal; printed loaded strength remains unqualified.

## Full heat-set inventory -- do not double-count hosts

| Location | Per build | Reference / hold |
|---|---:|---|
| Case clamp inserts | 4 | Real M3 heat-sets; FRAME_3 is in P02, other case hosts retained. No case nut substitution. |
| Separate upper frame insert | 1 | M3 reference in P01. |
| Plate-retainer inserts | 2 | M3 reference family; actual pilot/stock/insert fit needs individual review. |
| Spring-preload insert | 1 | M3 reference; retains its own axis/backing. |
| Arm inserts | 2 | Short M3, 4.6mm OD x 4mm reference; 4.0mm pilots/4.4mm tapered entries, not universal fit/pullout approval. |
| Small tool inserts | 4 | Inherited tool-interface envelopes; actual family, supplier SKU, and pilot fit **HOLD**. |
| **Total modeled insert entries** | **14** | Eight core/plate/preload, two arm, four tool; not fourteen interchangeable inserts. |

Bench-fit the cam/servo/bearing/washer/retainer before closing the front
case: straight front-driver access is blocked. Rear-load FRAME_2's P01
insert before plate closure; front-load FRAME_3's bare P02 insert before
blue P01 captures it; bench-install the spring insert before case closure.
These are geometric assembly-order references, not physical staking,
thread, strength, or access qualification. See [inspection notes](PREVIEW.md).

## Printed and printer-dependent requirements

Use one of each of the **17 print roles** after reviewing the complete
matched v16 set. P04 is split; P05 includes the direct hub, not an extra
horn print. **NOT READY FOR PRINTING**;
bed placement does not qualify supports, deposition, spline resolution,
material choice, loaded strength, or hot creep.

The [five-collar fit gauges](calibration_v16/README.md) are **optional
calibration, not an 18th assembly part** or additional production cam.
Their approximate tooth trials do not qualify real spline fit or torque.

Meshes are **best-effort native inspection exports**, not guaranteed-clean
STL normal metadata. Microscopic nondegenerate facets can have **zero stored
STL normal vectors**. **Inspect each mesh and its warnings in a slicer**;
the current set retains only three such P01 metadata warnings. Native bytes are not
patched by facet deletion or normal rewriting to imply print readiness.

| ID | Print role | Licence scope |
|---|---|---|
| P01 | [Back case](stl_v16/P01_Back_case.stl) | GPL-3.0 custom work |
| P02 | [Motor/actuator plate](stl_v16/P02_Motor_servo_plate.stl) | GPL-3.0 custom work |
| P03 | [Front case with M2.5 blind pockets](stl_v16/P03_Front_case.stl) | GPL-3.0 custom work |
| P04R | [Swing-arm rear half](stl_v16/P04R_Swing_arm_rear_half.stl) | GPL-3.0 custom work |
| P04F | [Swing-arm front half](stl_v16/P04F_Swing_arm_front_half.stl) | GPL-3.0 custom work |
| P05 | [One-piece direct-output cam/hub, FIT PENDING](stl_v16/P05_Servo_cam.stl) | GPL-3.0 custom work |
| P06 | [Left 38T/14T compound](stl_v16/P06_Left_compound_38T_14T.stl) | GPL-3.0 custom work |
| P07 | [Right 38T/14T compound](stl_v16/P07_Right_compound_38T_14T.stl) | GPL-3.0 custom work |
| P08 | [Left 37T HGX drive](stl_v16/P08_Left_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P09 | [Right 37T HGX drive](stl_v16/P09_Right_HGX_drive_37T.stl) | GPL-3.0 custom work |
| P12 | [Spring pressure cup](stl_v16/P12_Spring_pressure_cup.stl) | GPL-3.0 custom work |
| P13 | [Left GT2 tooth liner](stl_v16/P13_Left_tooth_liner.stl) | **CC BY-SA 3.0** |
| P14 | [Right GT2 tooth liner](stl_v16/P14_Right_tooth_liner.stl) | **CC BY-SA 3.0** |
| P15 | [Left belt arch](stl_v16/P15_Left_belt_arch.stl) | GPL-3.0 custom work |
| P16 | [Right belt arch](stl_v16/P16_Right_belt_arch.stl) | GPL-3.0 custom work |
| P17 | [Original HF tool carrier](stl_v16/P17_HF_tool_carrier.stl) | GPL-3.0 custom work |
| P18 | [Tool docking backplate](stl_v16/P18_Tool_docking_backplate.stl) | GPL-3.0 custom work |

Wiring, connectors, strain relief, control interface, and adequately sized
regulated **5V servo power/common ground** are printer-dependent; verify
actual servo requirements and supply margins. Do not assume a controller's
signal pin supplies suitable motor power. Hotend heater/sensor wiring and
thermal protections follow the actual compatible supplier/printer system.
No generic harness, controller configuration, or heater-use approval is supplied.

CPAP and Beacon/probe accessories are deferred, not mandatory purchases.
Positive bare-Hall-package support, loaded release, spring margin, thermal
life, and endurance remain open. Read [mixed-scope attribution](ATTRIBUTION.md):
original authorship and GPL/CC BY-SA notices are retained; vendor/hotend
references keep their respective rights, not blanket certification or
redistribution permission. No personal purchase list, prices, or stock
deductions are part of this per-build BOM.
