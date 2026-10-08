# Current hardware / BOM

Quantities are for one current assembly, including reused kit/printer parts,
not a shopping-cart recommendation. Dimensions are in millimeters. Check actual
supplier geometry and printed fits before ordering or assembling.

**MG90S is a dimensional-fit prototype, not a torque-qualified actuator.
The supplied-horn/printed-cam drive is retained, not an all-metal redesign.
This is not purchasing or build approval.**

## MG90S selection and reuse

The user selected **MG90S** and already owns multiple units: **one needed,
zero to order if a matching unit is available**. Credit only stock with verified
case/ears, output spline, horn-retaining thread, and travel. MG90S-labelled
variants must not be assumed dimensionally identical.

[TowerPro's MG90S page](https://towerpro.com.tw/product/mg90s-3/) specifies a
22.8x12.2x28.5mm body, 13.4g mass, and 1.8kg-cm **stall** torque at 4.8V.
It also lists 2.2kg-cm at 6.6V while stating a 4.8V operating voltage. That
inconsistency is **not permission to overvolt** or evidence of working torque
headroom. The page does not specify spline tooth count/diameter, retention
thread, ear-hole pitch, or output-axis coordinates. Measure the actual owned
unit before matching a horn or mounting pattern.

The P02 mounting prototype uses **27.8mm nominal pitch** and +/-0.4mm per-ear
slot travel, giving a **27.0..28.6mm geometric pitch extent**. This is **not
TowerPro's official mounting-hole pitch** or universal case/ear/washer fit
qualification. Nominal support and front nut-loading checks are geometric
checks only. The modeled 2mm ears use two M2x6 screws, two 0.3mm M2 washers,
and two captive M2 nuts. The supplied matched MG90S horn remains a fit-check
envelope; no verified metal spline replacement is selected.

Current cam/spring demand and durability are not physically qualified. Neither
stall torque nor the earlier superseded preload calculation establishes
continuous/loaded torque margin. TF-9512MG (180-degree version) is an available
backup, not selected. MG92B is only a possible future mounting-swap option,
not an approved replacement or a measured-headroom claim.

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
| MG90S servo assembly with matched supplied horn | 1 | Selected prototype baseline. Reuse credit: 1 if owned stock matches; to order: 0 in that case. Case/output/horn/retention hardware are one servo assembly. Verify actual ears, spline, retaining thread and travel. No all-metal interface is selected. |
| Closing/preload spring | 1 | Elastic reference, not a qualified spring SKU. Source name is 0.8x7x30; CAD OD is about 7.8mm. Measure delivered dimensions, rate, and solid height. |
| Steel balls | 5 | 4mm diameter: four tool locators and one preload thrust ball. |
| Follower inner-ring shims | 2 | 3.2x5x0.5mm steel; keep contact on the inner ring only. |
| Round tool-interface locating pins | 6 | 1.5x5mm; retain the current paired-top/single-bottom locating layout. |
| Tool/receiver magnets | 8 | 5x15x3mm: four in each half. Verify polarity and real pocket fit. |
| PTFE inlet segment | 1 | 4mm OD, 2mm ID, 6mm long; check the actual cold-side feed path. |
| HF hotend reference assembly | 1 | Eight CAD reference bodies describe one hotend, not eight purchases. Nominal nozzle/heater/thermistor envelopes are not manufacturer-certified drawings or a validated supplier fit. |
| MGN12H carriage | 1 | Existing nominal 45.4mm carriage. Stock-inclusive CAD width is 45.44mm versus 45.0mm printed shells; the envelope issue remains unwaived. |
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
| M2x6 servo mounting screws | 2 | Replaces the two M2x5 screws. ISO4762/DIN912 socket head: 3.8mm head OD, 2mm head height, 1.5mm hex AF. Check actual hardware against the modeled stack. |
| M2 flat washers | 2 | Ordinary flat washers: 2.2mm ID, 5.0mm OD, 0.3mm thickness, against the nominal 2mm mounting ears. |
| M2 hex nuts | 2 | Preload into their guides before the backplate closes access. |
| M1.6x4 self-tapping horn link screws | 2 | Retained supplied-horn/printed-cam prototype links. Check the actual supplied horn holes; not a future metal-horn thread specification. |
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

## Price-free sourcing

Checked 2026-10-08. Prefer an **AliExpress.us Choice** item only when its live
badge, exact variant, and delivery to the actual US address are verified.
Anonymous access redirected to login, so **Choice status and US shipping are
unverified for every search below**. These are discovery links, not checked
product endorsements or free-shipping claims. Credit matching owned hardware
before ordering; pack sizes are not assembly quantities.

| Assembly requirement | Needed | AliExpress.us search / critical selection |
|---|---:|---|
| MG90S servo | 1; order 0 if stock matches | [MG90S](https://www.aliexpress.us/w/wholesale-mg90s-servo.html); verify the actual unit against the dimensions/fit checks above. |
| MG90S mount hardware | 2 screws + 2 washers; retain 2 nuts | [M2x6 socket-head screws](https://www.aliexpress.us/w/wholesale-m2-6mm-machine-screw.html), ISO4762/DIN912; [M2 flat washers](https://www.aliexpress.us/w/wholesale-m2-flat-washer.html), 2.2mm ID / 5.0mm OD / 0.3mm thick. Verify actual hardware/ear fit. |
| Matching HGX steel hobs and kit needles | 2 hobs + 2 needles | [HGX gear kit](https://www.aliexpress.us/w/wholesale-hgx-extruder-gear-kit.html); kit variant and stock-shape fit must match. No extra rear extension bearings. |
| Motor and pinion | 1 each | [14HS13-0804S](https://www.aliexpress.us/w/wholesale-14hs13-0804s.html), factory 5x24mm D-shaft; [module-0.5 20T pinion](https://www.aliexpress.us/w/wholesale-module-0.5-20t-5mm-pinion.html), 5mm bore and correct hub/setscrew position. |
| MF74-type / MF63-type bearings | 6 / 5 | [MF74ZZ](https://www.aliexpress.us/w/wholesale-mf74zz.html), 4x7x2.5mm, 8.2mm flange; [MF63ZZ](https://www.aliexpress.us/w/wholesale-mf63zz.html), 3x6x2.5mm, 7.2mm flange. Verify flange profile, not name alone. |
| Follower bearing | 1 | [623 bearing](https://www.aliexpress.us/w/wholesale-623-bearing.html), 3x10x4mm. |
| Round hob / main / cam pins | 2 / 2 / 1 | [3x14mm ground pins](https://www.aliexpress.us/w/wholesale-3mm-14mm-ground-pin.html), [4x30mm shafts](https://www.aliexpress.us/w/wholesale-4mm-30mm-shaft.html), [3x12mm pins](https://www.aliexpress.us/w/wholesale-3mm-12mm-pin.html); ordinary round shafts, not oversized press-fit dowels. |
| Required frame/follower inserts | 7 long + 2 short | [M3 4.6mm OD inserts](https://www.aliexpress.us/w/wholesale-m3-4.6mm-heat-set-insert.html); separate 4mm and 3mm lengths. Six optional accessory inserts are not in these counts. |
| Small tool-interface inserts | 4; purchase hold | [Small M3 inserts](https://www.aliexpress.us/w/wholesale-m3-small-heat-set-insert.html); verify the smaller October envelope, not the frame inserts. |
| Locating balls / pins | 5 / 6 | [4mm steel balls](https://www.aliexpress.us/w/wholesale-4mm-steel-ball.html), [1.5x5mm pins](https://www.aliexpress.us/w/wholesale-1.5mm-5mm-pin.html); fit actual locating interfaces. |
| Tool/receiver magnets | 8 | [5x15x3mm magnets](https://www.aliexpress.us/w/wholesale-5x15x3mm-magnet.html); verify size, pockets, and polarity. |
| Spring and follower shims | 1 spring + 2 shims; spring hold | [Compression spring](https://www.aliexpress.us/w/wholesale-compression-spring-0.8-7-30.html) is discovery only, not a qualified SKU; [3.2x5x0.5mm shims](https://www.aliexpress.us/w/wholesale-3.2-5-0.5mm-shim.html) contact the follower inner ring. |
| Other fasteners | Per fastener table | [Metric screws](https://www.aliexpress.us/w/wholesale-metric-machine-screws.html); match each head, thread and length above. Do not substitute countersunk motor screws for tool screws. |
| Future MG90S metal horn / shaft interface | Unselected; purchase hold | [MG90S metal horn](https://www.aliexpress.us/w/wholesale-mg90s-metal-servo-horn.html); require actual spline/retention and horn-hole dimensions. A listing title is not a fit guarantee. |

## Metal drive-interface candidates: not approved purchases

No checked source establishes a complete off-the-shelf metal MG90S horn plus
stock-shaft connection for the user's actual servos. **Spline tooth count,
diameter, retention thread, and a compatible horn mounting pattern remain
unverified.** Do not infer them from standard H25T hardware or a generic
"micro-servo compatible" listing.

- [Pololu 1996](https://www.pololu.com/product/1996) is a downstream aluminum
  shaft hub, **not a servo spline adaptor**. Its [official drawing](https://www.pololu.com/file/0J661/1996-3mm-m3-hub-dimensions.pdf)
  gives a 3mm bore, 17.5mm OD, 5mm thickness, four threaded M3 holes at 6.35mm
  radius (12.7mm pitch-circle diameter), and an M3 radial setscrew. The missing
  servo-to-shaft connection and shaft/hub torque retention still need validation.
- [ServoCity 4001-0025-0006](https://www.servocity.com/4001-series-clamping-servo-to-shaft-coupler-25-tooth-spline-to-6mm-round-bore/)
  is H25T to a 6mm shaft, 17mm long with a 23.8mm rotating envelope. Its
  [C24T variant](https://www.servocity.com/4001-series-clamping-servo-to-shaft-coupler-24-tooth-spline-to-6mm-round-bore/)
  also specifies a different spline standard. **Neither is MG90S-fit verified**.
- [Adafruit 3837](https://www.adafruit.com/product/3837) is a 25-tooth aluminum
  arm whose supplier explicitly excludes micro/submicro servos. It is not an
  MG90S horn option.

The separate 3x12mm cam journal pin does not replace the old printed torsion
neck's torque path. Observed printed-part strength does not prove long-term
durability, and no immediate-failure claim is made. Do not order a metal horn,
coupler, replacement shaft, or changed cam fasteners from this candidate list
before the actual spline and matched native interface are verified. These
unselected durability-improvement candidates do not block the retained
supplied-horn/printed-cam mounting prototype.

## Reference-only provisions

The CAD retains one A1104 Hall-sensor reference and one 4x2mm presence-magnet
reference. These do not establish sensing functionality or accessory purchases.
The loaded 1.75mm filament reference is not an additional assembly component.
Servo/horn, spring, hotend, and small tool-insert envelopes require actual fits;
they are not order-ready supplier specifications.

See [preview limits](PREVIEW.md) and [mixed-scope attribution](ATTRIBUTION.md).
