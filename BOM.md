# Current hardware / BOM

Quantities are for one current assembly, including reused kit/printer parts,
not a shopping-cart recommendation. Dimensions are in millimeters. Check actual
supplier geometry and printed fits before ordering or assembling.

## Hardware and fit-sensitive assemblies

| Item | Qty | Current requirement / fit caveat |
|---|---:|---|
| NEMA14 motor, 14HS13-0804S reference | 1 | Motor case and factory 5x24mm D-shaft represent one motor. No stock-shaft machining. |
| 20T input pinion | 1 | Module 0.5, 5mm bore; nominal 5.1mm face and 10.1mm overall length. Confirm real hub and setscrew fit. |
| Matching HGX steel hob wheels | 2 | Unmodified stock wheels; use the matching HGX kit variant. |
| Original HGX hob needle bearings | 2 | Retained matching kit needles, not extra rear extensions. |
| MF74-type flanged bearings | 6 | 4x7x2.5mm; current flange OD is 8.2mm. Match the delivered flange profile. |
| MF63-type flanged bearings | 5 | 3x6x2.5mm; current flange OD is 7.2mm. Four hob supports and one outboard cam support. |
| 623 follower bearing | 1 | 3x10x4mm; clamp its inner ring without locking the outer ring. |
| Round main axles | 2 | Ordinary 4x30mm ground shafts. |
| Round hob pins | 2 | Ordinary 3x14mm ground pins; no flats or extensions. |
| Cam journal pin | 1 | Ordinary 3x12mm ground pin; calibrate the printed pilot to actual hardware. |
| Servo assembly with supplied horn | 1 | Case, output spline, horn, and retention screw are one assembly. Generic 23x12x28mm case reference only; actual case/horn/spline fit is a purchase hold. |
| Closing/preload spring | 1 | Elastic reference, not a qualified spring SKU. Source name is 0.8x7x30; CAD OD is about 7.8mm. Measure delivered dimensions, rate, and solid height. |
| Steel balls | 5 | 4mm diameter: four tool locators and one preload thrust ball. |
| Follower inner-ring shims | 2 | 3.2x5x0.5mm steel; keep contact on the inner ring only. |
| Round tool-interface locating pins | 6 | 1.5x5mm; retain the current paired-top/single-bottom locating layout. |
| Tool/receiver magnets | 8 | 5x15x3mm: four in each half. Verify polarity and real pocket fit. |
| PTFE inlet segment | 1 | 4mm OD, 2mm ID, 6mm long; check the actual cold-side feed path. |
| HF hotend reference assembly | 1 | Eight CAD reference bodies describe one hotend, not eight purchases. Nominal nozzle/heater/thermistor envelopes are not manufacturer-certified drawings or a validated supplier fit. |
| MGN12H carriage | 1 | Existing carriage; stock 45.4mm width remains an unwaived envelope issue. |
| GT2 9mm belt ends | 4 | Ends of the printer's existing belts, not four extra belt loops. Confirm real folds/contact and preload. |

There are no added rear extension bearings or separate printed hob spacers.
The steel hobs and original needles remain unchanged.

## Fasteners and inserts

Keep screws with different heads/functions separate even when their nominal
thread and length match. Engagement values in the model are not torque ratings.

| Item | Qty | Location / requirement |
|---|---:|---|
| M3x6 countersunk motor screws | 4 | Preassemble motor on the separate spacer before mating the backplate. |
| M3x6 countersunk spacer retainers | 2 | Separate backplate-to-spacer retainers; 3mm nominal insert engagement. |
| M3x6 tool screws | 4 | Match the current tool screw-head profile; do not substitute the countersunk motor screws. |
| M3x20 clamshell screws | 4 | Match the recessed front-half head profile. |
| M3x40 button-head frame tie | 1 | Fifth, rear-loaded spacer tie; distinct from the shorter clamshell screws. |
| M3x10 carriage screws | 4 | Direct backplate-to-carriage attachment; match the recessed head profile. |
| M3x16 button-head belt draw screws | 4 | Cartridge/arch fastening, not carriage attachment. |
| M3 hex nuts | 4 | Captive belt-cartridge nuts. |
| M3x12 follower axle screw | 1 | Inner-ring clamp with the two steel shims. |
| M2x5 servo mounting screws | 2 | Rear-facing servo mounting heads. |
| M2 hex nuts | 2 | Preload into their guides before the backplate closes access. |
| M1.6x4 self-tapping horn link screws | 2 | Into the supplied plastic horn; verify the actual horn holes. |
| M2.5x8 hotend mounting screws | 4 | 3mm nominal heatsink engagement; confirm with the actual hotend. |
| M3x3 flat-point pinion grub screw | 1 | Contact the factory D-flat, not the round shaft. |
| M3x6 flat-point preload grub screw | 1 | Thrust through the steel ball and printed spring pressure cup. |
| M3 heat-set inserts, 4.6mm OD x 4mm long | 7 | Frame, spacer, and spring-preload locations. |
| M3 heat-set inserts, 4.6mm OD x 3mm long | 2 | Follower cheek and short upper spacer-retainer location. |
| Small M3 tool-interface inserts | 4 | Match the smaller October reference envelope. Supplier/actual fit is a purchase hold; do not substitute the 4.6mm OD frame inserts blindly. |

## Optional adapter provisions

These blind pilots are intentional future mounts, **not missing frame screws**.
No adapters or sensor-specific hardware are supplied.

| Location | Optional insert quantity | Future use |
|---|---:|---|
| Four front blind pilots | 4 | CPAP adapter |
| Two lower P01 blind pilots | 2 | Cartographer/Beacon adapter |

All six optional inserts are M3, 4.6mm OD x 4mm long. They are **not included**
in the seven required 4mm inserts or the two required 3mm inserts listed above.
Actual CPAP/probe-adapter design and sensing remain deferred.

## Current printed parts

One of each: **16 parts**. Retained identifiers intentionally have gaps.
The linked STLs are millimeter, bed-oriented exports of the current geometry,
not a qualified printing recipe.

| ID | Part | Qty | License scope |
|---|---|---:|---|
| P01 | [Flat backplate](stl/P01_Flat_backplate.stl) | 1 | GPL-3.0 custom structure |
| P02 | [Motor/servo spacer](stl/P02_Motor_servo_spacer.stl) | 1 | GPL-3.0 custom structure |
| P03 | [Front clamshell](stl/P03_Front_clamshell.stl) | 1 | GPL-3.0 custom structure |
| P04 | [Swing arm](stl/P04_Swing_arm.stl) | 1 | GPL-3.0 custom structure |
| P05 | [Servo cam](stl/P05_Servo_cam.stl) | 1 | GPL-3.0 custom structure |
| P06 | [Left 38T/14T compound gear](stl/P06_Left_compound_38T_14T.stl) | 1 | GPL-3.0 custom structure |
| P07 | [Right 38T/14T compound gear](stl/P07_Right_compound_38T_14T.stl) | 1 | GPL-3.0 custom structure |
| P08 | [Left 37T HGX drive](stl/P08_Left_HGX_drive_37T.stl) | 1 | GPL-3.0 custom structure |
| P09 | [Right 37T HGX drive](stl/P09_Right_HGX_drive_37T.stl) | 1 | GPL-3.0 custom structure |
| P12 | [Spring pressure cup](stl/P12_Spring_pressure_cup.stl) | 1 | GPL-3.0 custom structure |
| P13 | [Left toothed belt liner](stl/P13_Left_tooth_liner.stl) | 1 | CC BY-SA 3.0 |
| P14 | [Right toothed belt liner](stl/P14_Right_tooth_liner.stl) | 1 | CC BY-SA 3.0 |
| P15 | [Left belt arch](stl/P15_Left_belt_arch.stl) | 1 | GPL-3.0 custom structure |
| P16 | [Right belt arch](stl/P16_Right_belt_arch.stl) | 1 | GPL-3.0 custom structure |
| P17 | [HF tool carrier](stl/P17_HF_tool_carrier.stl) | 1 | GPL-3.0 custom structure |
| P18 | [Tool docking backplate](stl/P18_Tool_docking_backplate.stl) | 1 | GPL-3.0 custom structure |

P12 is the functional spring pressure cup; its upper round appearance does not
make it a remnant. It remains an unchanged required print.

## Reference-only provisions

The CAD retains one A1104 Hall-sensor reference and one 4x2mm presence-magnet
reference. These do not establish sensing functionality or accessory purchases.
The loaded 1.75mm filament reference is not an additional assembly component.
Servo/horn, spring, hotend, and small tool-insert envelopes require actual fits;
they are not order-ready supplier specifications.

See [preview limits](PREVIEW.md) and [mixed-scope attribution](ATTRIBUTION.md).
