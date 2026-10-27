# SparkShift

> [!WARNING]
> **WORK IN PROGRESS / FIT PENDING / NOT READY FOR PRINTING OR USE**
>
> CAD, meshes, and renders are inspection references, not physical
> qualification. Servo fit, screw engagement, printed strength, loaded
> release, retention, thermal safety, and endurance remain unqualified.
> Do not install or operate heated or unattended on the strength of this model.

**HGX quick-change hotend system**

*Same drive. New hotend.*

SparkShift is a provisional name for a YUDX-derived community design. One
factory-10T LDO-36STH20-1004AHG(XH) pancake motor and the purchased HGX drive
stay on the carriage. An independent servo cam releases the swinging hob;
ordinary forward/reverse extrusion must not open the arm.

**Vibe developed:** substantial iterative CAD and tooling are AI-assisted
under human direction, not professionally engineered or physically validated.
This describes SparkShift's development, **not upstream CxChanger/YUDX
authorship or purchased hardware**. Their rights and credit remain in
[ATTRIBUTION.md](ATTRIBUTION.md).

## Current development: v26j triple-bridged ladder frame

The current **timeline 1648** snapshot connects both sides of the front
receiver at the bottom and middle. P03 is now a **triple-bridged closed-loop
ladder frame**, rather than an inverted U, nested into a matching P01 recess.

### See the changes with the toolhead hidden

The docked **P17 removable toolhead hides P03's centre slot and new bridges**
in the usual closed-assembly view. Here P17 is hidden for inspection so the
orange receiver's **mid-upper bridge, bottom closed-loop bridge, and +X
lower-foot extension** are visible:

![WIP v26j direct front view with P17 toolhead hidden to reveal P03 middle and bottom bridges](images_v26/v26_front_case_and_bolts.png)

![WIP four-panel v26h-before and v26j-after comparison with isolated P03 inside and P01 mating views](images_v26/v26_magnet_wall_reinforcement.png)

Read the annotated panels **left to right**: **v26h before** with the
toolhead hidden; **v26j after** with the middle/bottom bridges and lower
foot called out; **P03 rear/inside** showing the connections; and **P01
front mating face** showing the matching recess and four-zone shear keys.
These are inspection renders, not new parts, physical tests, or an
assembly sequence. The native CAD is still **v26j / timeline 1648**.

### Structural changes retained in this snapshot

- A **27.40 x 2.60 x 2.30mm bottom cross-bridge** and full-depth +X lower
  foot connect the receiver legs. P01 has a matching lower-front recess
  with **0.15mm nominal clearance**, not a forced fit.
- A **mid-upper cross-bridge** joins the inner walls behind the removable
  tool's tongue and ahead of the rear arm. The original upper connection
  and **four-zone mortise-and-tenon keys plus coaxial shear bosses** remain.
  Those keys register the lower
  legs, mid-column, and upper bolt interface with **0.15mm nominal mating
  clearance**. They add a geometric shear load path, not extra hardware.
- P01 now has a **continuous 1.85mm rear top bridge** joining the upper
  bolt towers, replacing the old square cutout while retaining the
  contoured arm clearance and **bilateral cam bearings**: rear
  **MR128ZZ 8x12x3.5mm**, front **MF85ZZ 5x8x2.5mm**.
- P04F has a single flat **Y=26.850mm** print-face reference and restored
  blind M3 insert pocket. P03 reclaims the freed space for **1.527mm
  continuous rear backing** behind both +X receiver magnets.
- **7mm P02** plate, rear MG90S/MG90D reference ear-seat frame,
  **11.60 x 22.56mm** tangent servo window, and **11.5mm** motor-entry notch.
- Mirrored upper case-bolt positions and lower X positions, with a deliberate
  **0.15mm lower-right Z offset**, four modelled hex sockets, and a thicker
  lower-left clamp post; this is not perfect all-feature symmetry.
- YUDX-matched **teardrop Maxwell pin seats**, a shortened **G1-tangent
  P04R manual lever**, aligned case decks, and continuous **R1.5 outer rounds**.

The tightened **11.6mm servo window still intersects the legacy 12.2mm
`HOBBY_SERVO_ENVELOPE` reference**. The selected real servo must be measured
and bench-fitted; neither MG90S/MG90D labels nor reference STEP fits guarantee
clone compatibility. The direct printed 21T cam/hub has **no OEM horn**.

![WIP v26 rendered closed assembly, not a photograph or print approval](images_v26/v26_assembly_closed_front_iso.png)

The bridges tie the front receiver sides together; retained interlocks
are intended to reduce reliance on bolt friction alone. These features
are **not a proven cure for creep or spreading**: clearance allows
some movement before contact, and printed fit, material, bolt preload,
temperature, cyclic load, and long-term creep still need physical checks.
Keep the **matched v26j P01/P03 pair** and existing case bolts; the keys do not
replace the clamps or certify a force-fit. See [the four zones](PREVIEW.md)
and [print-part fit/orientation notes](PRINT_PARTS.md).

## Exploded architecture and cam motion

![WIP v26j exploded assembly with triple-bridged P03 and recessed shear-keyed P01](images_v26/v26_exploded_assembly.png)

The colour-coded exploded layout separates the removable tool, P03 receiver,
split arm/gearing, connected P01 frame, and rear motor/servo plate.
Offsets and labels explain architecture, **not a validated assembly
sequence, continuous removal path, or physical fastener access**.

![WIP v26j dual-viewport cam and swing-arm animation, kinematics not force simulation](images_v26/v26_cam_opening_motion.gif)

The **71-frame, 1280x784** GIF shows an opening/return cycle in **3.44
seconds of rendered playback**, not real servo timing. Its full-open
labels show **175-degree cam / 7.87-degree swing arm / 2.73mm hob bite
release gap**; the captioned gap is a CAD-preview metric, not a measured
physical clearance or force result. Translucent/hidden parts expose the
mechanism; ordinary extrusion remains independent of release.

## Accessory, Dock, Crossbar Mount, Calibration Jig & COTS Core Upgrade Suite (`P20`–`P29_L/R`, `P17_3010`/`2510`, `P18_3010`, `P01_COTS`, `P02_COTS`, `P05_COTS`)

**Current side-fan mechanical review: CAD review; the bed collision is resolved by a
required bed change (revision 34).** See
[revision 34: rigid rack, bed front edge behind the docks](cad/SparkShift_Accessories_v26/README.md#33-one-piece-bambu-toolhead-with-side-2510).
The current Bambu printed body is **revision 30**, rebuilt from revision 22.
It encloses the filament path at the hotend inlet, restores the solid front
neck under P18, fills the old fan-insert grooves, closes the lower P18 insert
pockets inside the flange, and seats the fan on two round heat-set bosses
with a 1.5 mm air gap to the heatsink. The fan is 1.65 mm closer to the
hotend than in revision 29, and a shelf strip that sat 0.10 mm from the
active carriage at the dock is removed (also on the Red Lizard body).
A revision-31 carriage review lowers the P22-to-P01 front mounts 1.5 mm,
raising the gap under every tool's side fan from 0.98 mm to 2.48 mm; it
needs the same boss move in the native P01 before use. Revision 32 trims
both printed bodies to the original ±12.40 mm width on the non-fan side
and removes a 0.05 mm Red Lizard skin, raising the closest side clearance
to the active carriage from 1.30 mm to 1.73 mm. Revision 33 adds a third
fan screw on the Bambu and replaces the Red Lizard's thin fan column with a
fan wall tied into a restored neck under P18.
Revisions 25-29 are superseded. It remains a review candidate, not print or
machine approval.
The dock rack stays rigidly bolted across the open front of the gantry U, so
the parked tools ride at the active tool's height. Their chutes, pads and
wipers hang about 14 mm below the nozzle, and revision 22 found them inside
the bed's front strip at first-layer height. The active nozzle cannot print
forward of Y63.21 mm anyway, so revision 34 records the printer change instead
of moving the rack: the bed's front edge goes to Y40 mm or further back (the
stock bed moved back 31 mm, or a 350 × 319 mm bed). All 80 first-layer and
contact-touch cases then clear by 4.59 mm, and the print area is unchanged.
The ten front docks cost about 54 mm of print depth: the printable area is
about 350 × 296 mm (350 × 301 mm with the stock bed moved back, using the
Monolith's rear overtravel to Y364). Revision 35 cuts a cable slot through
P24's bottom so the Beacon/Cartographer cable enters the EBB42 wiring bay
without passing through the part. A suspected 0.28 mm P22 clearance over
the Bambu nozzle turned out to be an artifact of the synthetic Bambu
nozzle model, and the probe `y_offset` sign is corrected to +19.50 mm.
The earlier independent-rack-lift study (revision 23) is not pursued.
Ten tools fit laterally, but the full rack has not been re-audited with the
revision-33 toolheads, and nothing is **build-approved**.
Revision 21 supersedes the front-fan toolhead/dock geometry described below, adds a
6.5 mm forward dock standoff and requires straight-Y withdrawal before X
travel. The Klipper file below is a historical **nine-bay** template, not a
commissioned configuration for these ten side-fan tools. Its lateral wipes
must not be used with the current rack.

Building directly on the frozen **v26j / timeline 1648** carriage with **zero unintended modifications (`0.000 mm³` clash)** to any of the 135 core bodies, the **[SparkShift v26 Accessory & 3010 Toolhead Suite](cad/SparkShift_Accessories_v26/README.md)** and **[Klipper Toolchanger Macro Suite (`klipper/sparkshift_toolchanger.cfg`)](klipper/sparkshift_toolchanger.cfg)** add **14 pure-primitive accessory/dock/rack/jig parts** (`0` BSpline/mesh/sphere faces, `0` sliver faces `< 0.15 mm²`, `100%` watertight manifold STLs) plus **3 COTS-qualified core drop-in parts**:

- **`P20_CPAP_Hose_Inlet`**, **`P21_CPAP_Gantry_Bridge`**, **`P22_CPAP_Lower_Plenum`:** 3-part directional-shingle CPAP cooling duct (`353.40 mm²` trunk behind the **Monolith 2WD 9mm gantry**, `0.000 mm³` X-limit gantry clash, `0.00 mm` internal shingle bore steps, sweeping `R = 61.0 mm` inner / `R = 50.0 mm` outer elbow curve, inward-curving tapered volute gooseneck (`Y_max = 29.43 mm`, `0.0 mm³` dead-end pocket) feeding a `35°` sub-sock nozzle louver throat, `≥ 4.65 mm` 3D thermal keepout around the Volcano silicone sock, `≥ 5.90 mm` from the bare `350 °C` heatblock) with a dual-barb (`Ø21.6 / Ø21.8 mm`) spigot for the **Trianglelab Supercharged 7040 Blower (`21.5 mm` ID cuff)**.
- **`P23_Beacon_Cartographer_Mount`:** Shared forward-facing mount (`(±15.80, -0.30, -75.00) mm`) for **Beacon RevH Normal** (`Y = -19.50 mm`, `2.269 mm` above nozzle tip) and **Cartographer Probe V3 Flat Pack (`CAN & USB`, with ADXL345)** (`Y = -19.82 mm`, `2.279 mm` above nozzle tip), with `0.000 mm³` metal inside the `20 mm` probe sensing keepout.
- **`P24_EBB42_Controller_Mount`:** Co-bolted rear mount for the **BTT EBB42 CAN V1.2** (`Y_pcb = -31.63 mm`), leaving **`+2.20 mm` to `+6.60 mm` axial clearance** behind **`17.4–21.8 mm` thick NEMA14 pancake motors**, 100% open access to top `CAN/24V/USB-C/HE0`, right `FAN0/FAN1/TH0`, and left **`3-pin RGB/Neopixel LED (`PD3`) / I2C / Probe`** headers, plus an integrated **3-channel `A1104` Hall-sensor lead insulator & strain-relief comb (`Y = -6.75..-2.50 mm`)**.
- **`P17_HF_tool_carrier_3010`**, **`P17_HF_tool_carrier_2510`**, **`P17_Bambu_P2S_tool_carrier_3010`**, **`P17_Bambu_P2S_tool_carrier_2510`**, **`P18_Tool_docking_backplate_3010`:** Pure-primitive high-flow toolhead carriers with a converging bellmouth, rear V-splitter wedge, **quad lateral exhaust windows (`265.7 mm²`)**, and **partitioned vertical heater/thermistor wire chimneys (`18.5 mm²` per side)**, supporting up to **9–10 toolheads (`35.0–37.3 mm` pitch)** on a `350 mm` Voron 2.4R2. Includes the **`P17_Bambu_P2S`** variants with an integral rear vertical **`3 × M3` triangular mounting wall** (`(X = ±6.00, Z = -40.13 mm)` + `(X = 0.00, Z = -50.63 mm)`) and upper `Ø5.10 mm` filament guide boss (`Z = -32.38..-19.28 mm`) for the bolt-on **Bambu Lab H2C / H2D / P2S / A1 Hotend Heating Assembly (Zirconia ceramic block + aluminum heater cradle + front wire bail latch)** and **snap-in 7-fin Bambu nozzle** (`Z_tip = -78.88 mm`).
- **`P25_SparkShift_3010_Dock`**, **`P26_Dock_Nozzle_Wiper_and_Purge_Chute`**, **`P27_CPAP_7040_Blower_Frame_Mount`**, **`P28_Dock_and_Probe_Calibration_Jig`**, **`P29_Dock_Rack_Gantry_Mount_L/R`:** Compact stilt-free `34.00 mm` modular toolhead dock (`P25`, `Z = -86.08..+37.22 mm`, `220` faces) with a compliant spring-leaf **Silicone Ooze Stopper Pad** (`Z = -78.88 mm`), flush under-slung **Purge Pellet Chute & Dual V-Notched Silicone Nozzle Wiper (`P26`, `Z = -92.08..-78.80 mm`, `69` faces)**, left/right **Gantry-Mounted `2020` Dock Crossbar Support Brackets (`P29_L/R`, `66` faces each)** bolting the `420 mm` front `2020` dock crossbar (`Y = -22..-2 mm, Z = 182..202 mm`) directly to the flying-gantry Y-rail `2020` extrusions (`X = -55` and `X = +405 mm, Z = 180 mm`) via a 3-side pocket and `24 mm` diagonal gusset (`6× M5×10 BHCS + T-nuts` per side, `0.000 mm³` clash with Monolith front idlers), stationary **`2020` Frame Mount (`P27`)** for the Trianglelab 7040 blower + CAN umbilical strain-relief clamp, **4-in-1 Dock Pitch / `2.27 mm` Probe Feeler / `25 mm` Shaft / `21.4 mm` Spring Calibration Jig (`P28`)**, and **[`klipper/sparkshift_toolchanger.cfg`](klipper/sparkshift_toolchanger.cfg)** macros for pre-drop Volcano melt-zone decompression, standby temperature management, purge-chute priming, multi-pass silicone wiping, per-tool **Pressure Advance / Thermal Z-Offset / Input Shaper** switching, and dry-run commissioning (`SPARKSHIFT_TEST_SERVO_CAM`, `SPARKSHIFT_VERIFY_DOCK_ALIGNMENT`, `SPARKSHIFT_CALIBRATE_SHAPER_ALL`, `SPARKSHIFT_PA_TUNING_TOWER`).
- **COTS-Qualified Core Drop-In Trio (`P01_Back_case_COTS_MR74`, `P02_Motor_servo_plate_12p5mm`, `P05_Servo_cam_COTS`):** Drop-in alternatives in [`stl_v26/`](stl_v26) that accept standard **`MR74ZZ (4×7×2.5 mm)`** rear bearings + **`4 × 25.0 mm`** dowel pins (`P01_COTS`), full **`12.20 mm` MG90S/MG90D** servo bodies with **`0.000 mm³` interference** (`P02_COTS`), and a **100% pure-primitive watertight eccentric cam (`P05_COTS`, `0` BSplines, `0` non-manifold edges)** paired with a **`0.90 × 7.50 × 30.0 mm` (`k = 3.25 N/mm`)** closing spring (`28.0 N` preload / `40.7 N` hob bite / `3.05×` MG90D servo torque margin).

![Dock P25 + P26 Ooze Wiper & P27 Blower Frame Mount](cad/SparkShift_Accessories_v26/images/25_dock_p25_p26_ooze_wiper_and_p27_blower.png)

![COTS Core Upgrades (P01, P02, P05, P24 Hall Comb) & P28 4-in-1 Calibration Jig](cad/SparkShift_Accessories_v26/images/26_cots_upgrades_and_p28_calibration_jig.png)

![Bambu Lab Quick-Swap Hotend Heating Assembly & Snap-In 7-Fin Nozzle Toolhead (`P17_Bambu_P2S`)](cad/SparkShift_Accessories_v26/images/27_bambu_p2s_quick_release_toolhead.png)

| 360° Full Assembly Turntable | Exploded Assembly Sequence |
| :---: | :---: |
| ![360° Full Assembly Turntable](cad/SparkShift_Accessories_v26/images/anim_01_full_assembly_360_turntable.gif) | ![Exploded Assembly Sequence](cad/SparkShift_Accessories_v26/images/anim_02_exploded_assembly_sequence.gif) |
| **3010 Toolhead Docking & `17.4–21.8 mm` NEMA14 Clearance** | **All 8 Pure-Primitive Printable Parts (360° Showcase)** |
| ![3010 Toolhead Docking & NEMA14 Clearance](cad/SparkShift_Accessories_v26/images/anim_03_toolhead_3010_docking_and_nema14_clearance.gif) | ![All 8 Printable Parts Showcase](cad/SparkShift_Accessories_v26/images/anim_04_printable_parts_360_showcase.gif) |

![Live Fusion 360 Verified Geometry](cad/SparkShift_Accessories_v26/images/17_fusion360_live_verified_geometry.png)

| 3D CFD Internal Streamlines & Velocity (`Q = 18 CFM`) | 3010 Toolhead Lateral Exhaust & Partitioned Wire Tunnels |
| :---: | :---: |
| ![3D CFD Streamlines](cad/SparkShift_Accessories_v26/images/08_cpap_cfd_streamlines_and_velocity.png) | ![3010 Toolhead Side Exhaust on Carriage](cad/SparkShift_Accessories_v26/images/16_toolhead_side_exhaust_on_carriage.png) |
| **Full-System Exploded View with Monolith 2WD 9mm Gantry (Front-Right Iso)** | **Full-System Exploded View with Monolith 2WD 9mm Gantry (Rear-Left Iso)** |
| ![Full System Exploded Front Iso](cad/SparkShift_Accessories_v26/images/18_full_exploded_with_gantry_front_iso.png) | ![Full System Exploded Rear Iso](cad/SparkShift_Accessories_v26/images/19_full_exploded_with_gantry_rear_iso.png) |
| **Live Fusion 360 Section (`X = ±15.80 mm`) — Smooth `R = 61 mm` Sweep & Flat Floor** | **Dual Crescent Nozzle Jets & Thermal Keepout (`≥ 4.65 mm`)** |
| ![Live Fusion 360 Section Wall Integrity](cad/SparkShift_Accessories_v26/images/20_p22_section_wall_integrity.png) | ![Nozzle Jet Impingement](cad/SparkShift_Accessories_v26/images/09_cpap_nozzle_jet_impingement_closeup.png) |

### Modular Nested-XRef Complete Voron 2.4 350mm Printer Project (`SparkShift_Voron350_Master`)

In Fusion 360, the complete printer is structured as a multi-level, externally referenced (**XRef**) cloud project (**`SparkShift_Voron350_Master`**) across **3 nested folders and 9 modular cloud documents (`00`–`08`)**, allowing any individual sub-assembly (`Toolhead`, `Accessories`, `Core Carriage`, `Dock Unit`, `Gantry`, or `Frame`) to be toggled **Editable**, modified independently, marked **Read-Only** (staying within Fusion 360's 10-document Personal Use limit), and propagated up to the master printer via **Get All Latest**:

| Master Printer Assembly (`00_Complete_Printer_Voron24_350_SparkShift`) | Front 10-Dock Array (`T0`–`T9`) & Active SparkShift at Bay `T3` |
| :---: | :---: |
| ![Complete Printer Master XRef](cad/SparkShift_Accessories_v26/images/21_fusion360_complete_printer_master_xref.png) | ![Master Docks and SparkShift Closeup](cad/SparkShift_Accessories_v26/images/22_fusion360_master_docks_and_sparkshift_closeup.png) |
| **Rear-Interior View (Monolith 2WD 9mm Gantry + 10 Parked Toolheads)** | **Modular Primary SparkShift Assembly (`04_Assembled_SparkShift_Primary`)** |
| ![Master Rear Interior Iso](cad/SparkShift_Accessories_v26/images/23_fusion360_master_rear_interior_iso.png) | ![Assembled SparkShift Primary XRef](cad/SparkShift_Accessories_v26/images/24_fusion360_assembled_sparkshift_primary_xref.png) |

👉 **[Full Accessory & 3010 Toolhead Documentation, Modular Fusion 360 Project Architecture (`00`–`08`), B-Rep Audit, CFD Analysis, STEP & STL Files (`cad/SparkShift_Accessories_v26/README.md`)](cad/SparkShift_Accessories_v26/README.md)**

## Matched inspection package

| File / guide | Scope |
|---|---|
| [v26 native F3D](cad/SparkShift_AHG_min_v26.f3d) | Directly editable **v26j** snapshot: **135 native bodies**, timeline **1648**; native review reports 135/135 readback matches. |
| [v26 whole-assembly STEP](cad/SparkShift_AHG_min_v26.step) | 135 solid BREP records; neutral inspection export, not a manufacturing qualification. |
| [36 assembly, accessory, dock, rack & COTS STLs](stl_v26) | Complete matched 17-part core set plus 14 pure-primitive accessory/dock/rack/jig STLs (`P20`–`P29_L/R`, `P17_3010`/`2510`, `P18_3010`) and 5 COTS-qualified core drop-ins (`P01_COTS`, `P02_COTS`, `P03_COTS`, `P04F_COTS`, `P05_COTS`). |
| [Accessory, Dock & 3010 Toolhead Suite](cad/SparkShift_Accessories_v26/README.md) | Parametric `OCP` generator, 3D boundary-layer CFD solver, STEP/STL exports, 26 multi-angle renders, and 4 animated GIFs for `P20`–`P29_L/R`, `P17`/`P18`, and COTS drop-ins. |
| [Klipper Toolchanger & Commissioning Suite](klipper/sparkshift_toolchanger.cfg) | 5-stage anti-ooze toolchange, purge-chute prime, dual-blade silicone wipe, per-tool PA/Input Shaper/Thermal Z-Offset, and dry-run commissioning macros. |
| [Print-part inspection notes](PRINT_PARTS.md) | All 17 core roles + 14 accessory/dock/rack/jig roles + 3 COTS core drop-ins, bridge-support review, interlock fit, current meshes, and case orientations. |
| [Changes, digital checks, and gallery](PREVIEW.md) | v26a-j notes, new cross-bridges/recess, retained four-zone dimensions, six gallery views, exploded layout, GIF, and annotated v26h/v26j comparison. |
| [Generic per-build BOM](BOM.md) | Full reference inventory for one receiver, one tool, COTS bearing/shaft/spring specs, and the `P20`–`P29_L/R` / `3010` accessory suite. |
| [Incremental authoring source](source_v26/README.md) | Exactly **13 sealed modules**; prior live state and missing inputs prevent a clean one-command rebuild. |
| [Accessories architecture & verification](ACCESSORIES_PLAN.md) | Frozen v26j planning datums and complete verification summary for `P20`–`P29_L/R`, `P17_3010`/`2510`, `P18_3010`, and `P01`/`P02`/`P05` COTS drop-ins. |

The 17 inspection meshes total **420,820 facets**. Each is one
closed, manifold, coherently wound, positive-volume component, with zero
degenerate facets and **no zero or inverted stored normals found** in this
set. All sealed bytes are preserved. **P01 and P03 are now native Fusion
binary STL exports in assembly coordinates**, including negative Z, not
bed-oriented exports. Their intended bed-face references are **P01
Y=0.30mm rear / P03 Y=31.50mm front**; check orientation in a slicer.
Mesh/native volume differences are approximately **0.04235% / 0.01785%**,
not exact shape or mass equality. These digital checks do not establish
printability, deposition resolution, supports, fits, or safe use;
**inspect every mesh in a slicer** before any later fabrication decision.

For face-down P03, review the **6.40mm middle free span** and **18.40mm
bottom free span**. The latter is a candidate for optional build-plate-only
support; neither span is guaranteed to print cleanly on every setup.
See [orientation and support limits](PRINT_PARTS.md).

The current set contains matched CAD/meshes, **eight PNGs and one GIF**,
and the unchanged 13-module authoring snapshot. **No v26 standalone
portable playback or calibration-gauge package is supplied.**
Older files remain in Git history, not as compatible v26 tools.
Drive Joint alone is not proof of synchronized cam/arm motion or force physics.

## COTS Qualification & Physical Commissioning

To resolve the historical v26j hardware holds without altering the sealed baseline files, drop-in COTS alternatives and a physical calibration gauge are included in [`stl_v26/`](stl_v26) and [`cad/SparkShift_Accessories_v26/step/`](cad/SparkShift_Accessories_v26/step):
- **`P01_Back_case_COTS_MR74`** resolves the `4×7×2 mm` rear bearing and `26.3 / 24.9 mm` custom shaft holds by deepening the rear `MR74` seats by `0.50 mm` (`Y = 2.80..5.30 mm`), accepting standard **`MR74ZZ (4×7×2.5 mm)`** bearings and standard **`4 × 25.0 mm`** dowel pins on both compound axles.
- **`P02_Motor_servo_plate_12p5mm`** widens the servo pocket to `12.30 × 23.16 mm`, eliminating the `114.71 mm³` interference with standard `12.20 mm` MG90S/MG90D servo bodies (`0.000 mm³` clash).
- **`P03_Front_case_COTS`** and **`P17_HF_tool_carrier_3010` / `2510`** add dual-compatible figure-8 magnet pockets at `(X = ±6.50 mm, Z = [30.50, 23.00, 5.50, -2.00] mm)` that natively accept **either `8× Ø6×4 mm / Ø6×3 mm` N52 cylindrical magnets** (`8× Ø6×4 mm` or `Ø6×3 mm` in `P03_COTS` + `8× Ø6×3 mm` in `P17`) **or `4× 15×5×3 mm` rectangular bar magnets**, while **`P18_Tool_docking_backplate_3010`** and **`P25_SparkShift_3010_Dock`** integrate **StealthChanger `2× Ø5×12 mm` rounded dowel pins + `2× Ø5 mm` (`5×7×5.5 mm`) bushings** at `(X = ±6.00, Z = +22.00 mm)` and **close-gap (`0.16 mm` air gap) `4× Ø6×4 mm` (or `Ø6×3 mm`) N52 dock retention magnets** at `(X = ±6.00, Z = -2.00 mm)`.
- **`P04F_Swing_arm_front_half_COTS`** adds a **Cam-Actuated Positive Toolhead Locking Hook** (`Z = -15.00..-10.00 mm, Y = 23.65..26.85 mm`, flush with the `Y = 26.850 mm` bed face) that swings `-3.51 mm` inward in `-X` when `Cam = 0°` (Closed) to engage `P17`'s `4.00 mm` rear locking shoulder (`22.77 mm³` / `14.2 mm²` positive shear lock, `> 250 N` hold even with an unloaded hotend, `0.000 mm³` over-constraint at `dy = 0`) and retracts `+3.51 mm` clear in `+X` when `Cam = 175°` (Open, `0.000 mm³` clash across the entire `35 mm` pure-`Y` withdrawal stroke) — achieving **100% deterministic, zero-Z-lift, 10-toolhead docking and undocking**.
- **`P05_Servo_cam_COTS`** replaces the B-Spline cam (`1,080` non-manifold edges) with a 100% pure-primitive (`49` faces, `0` BSplines, `100%` watertight) cam and 4-keyed COTS spline socket, paired with a **`0.90 × 7.50 × 30.0 mm` (`k = 3.25 N/mm`)** stainless closing spring (`28.0 N` preload / `40.7 N` hob bite / `3.05×` MG90D torque margin).
- **`P24_EBB42_Controller_Mount`** integrates a 3-channel `A1104` Hall-sensor lead insulator and strain-relief comb (`Y = -6.75..-2.50 mm`), and **`P28_Dock_and_Probe_Calibration_Jig`** provides a 4-in-1 physical gauge for `37.30 / 35.00 mm` M5 dock pitch, `2.270 mm` Beacon/Cartographer nozzle-to-coil step height, `25.00 mm` shaft length, and `21.40 mm` spring preload length.

Physical bench-testing of printed fits, heat-set pullout, thermal margins, blower backpressure, and sensor offsets (using the dry-run macros in [`klipper/sparkshift_toolchanger.cfg`](klipper/sparkshift_toolchanger.cfg)) remains required before heated or unattended operation.

## Licences and sources

The unchanged [LICENSE](LICENSE) retains GPL-3.0 for CxChanger/YUDX-derived
custom work. P13/P14 GT2 liners retain **CC BY-SA 3.0** credit. Vendor/hotend
references retain their respective rights; no blanket relicensing,
manufacturer certification, commercial validation, or official Voron
endorsement is asserted. See [mixed-scope attribution](ATTRIBUTION.md).
