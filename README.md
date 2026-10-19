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

## Accessory & 3010 Toolhead Suite (`P20`–`P24`, `P17_3010`/`2510`, `P18_3010`)

Building directly on the frozen **v26j / timeline 1648** carriage with **zero modifications (`0.000 mm³` clash)** to any of the 133 non-replaced core bodies, the **[SparkShift v26 Accessory & 3010 Toolhead Suite](cad/SparkShift_Accessories_v26/README.md)** adds **8 pure-primitive printable parts** (`0` BSpline/mesh/sphere faces, `0` sliver faces `< 0.15 mm²`, `100%` watertight manifold STLs):

- **`P20_CPAP_Hose_Inlet`**, **`P21_CPAP_Gantry_Bridge`**, **`P22_CPAP_Lower_Plenum`:** 3-part directional-shingle CPAP cooling duct (`353.40 mm²` trunk behind the **Monolith 2WD 9mm gantry**, `0.000 mm³` X-limit gantry clash, `0.00 mm` internal shingle bore steps, sweeping `R = 61.0 mm` inner / `R = 50.0 mm` outer elbow curve immediately under the 2020 X-axis extrusion at `Z = -49.00 mm`, flat obstacle-free `Z = -68.90 mm` plenum floor, `≥ 4.65 mm` 3D thermal keepout around the Volcano silicone sock, `≥ 5.90 mm` from the bare `350 °C` heatblock) with a dual-barb (`Ø21.6 / Ø21.8 mm`) spigot for the **Trianglelab Supercharged 7040 Blower (`21.5 mm` ID cuff)**.
- **`P23_Beacon_Cartographer_Mount`:** Shared forward-facing mount (`(±15.80, -0.30, -75.00) mm`) for **Beacon RevH Normal** (`Y = -19.50 mm`, `2.269 mm` above nozzle tip) and **Cartographer Probe V3 Flat Pack (`CAN & USB`, with ADXL345)** (`Y = -19.82 mm`, `2.279 mm` above nozzle tip), with `0.000 mm³` metal inside the `20 mm` probe sensing keepout.
- **`P24_EBB42_Controller_Mount`:** Co-bolted rear mount for the **BTT EBB42 CAN V1.2** (`Y_pcb = -31.63 mm`), leaving **`+2.20 mm` to `+6.60 mm` axial clearance** behind **`17.4–21.8 mm` thick NEMA14 pancake motors** and 100% open access to top `CAN/24V/USB-C/HE0`, right `FAN0/FAN1/TH0`, and left **`3-pin RGB/Neopixel LED (`PD3`) / I2C / Probe`** headers.
- **`P17_HF_tool_carrier_3010`**, **`P17_HF_tool_carrier_2510`**, **`P18_Tool_docking_backplate_3010`:** Pure-primitive high-flow toolhead carriers with a converging bellmouth, rear V-splitter wedge, **quad lateral exhaust windows (`265.7 mm²`)**, and **partitioned vertical heater/thermistor wire chimneys (`18.5 mm²` per side)**, supporting up to **9 toolheads (`35.0–37.3 mm` pitch)** on a standard `350 mm` Voron 2.4R2 (`10` toolheads if usable X-stroke `≥ 315 mm`).

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

👉 **[Full Accessory & 3010 Toolhead Documentation, B-Rep Audit, CFD Analysis, STEP & STL Files (`cad/SparkShift_Accessories_v26/README.md`)](cad/SparkShift_Accessories_v26/README.md)**

## Matched inspection package

| File / guide | Scope |
|---|---|
| [v26 native F3D](cad/SparkShift_AHG_min_v26.f3d) | Directly editable **v26j** snapshot: **135 native bodies**, timeline **1648**; native review reports 135/135 readback matches. |
| [v26 whole-assembly STEP](cad/SparkShift_AHG_min_v26.step) | 135 solid BREP records; neutral inspection export, not a manufacturing qualification. |
| [25 assembly & accessory STLs](stl_v26) | Complete matched 17-part core set plus 8 pure-primitive accessory & `3010`/`2510` toolhead STLs (`P20`–`P24`, `P17_3010`/`2510`, `P18_3010`). |
| [Accessory & 3010 Toolhead Suite](cad/SparkShift_Accessories_v26/README.md) | Parametric `OCP` generator, 3D CFD solver, STEP/STL exports, 17 multi-angle renders, and 4 animated GIFs for `P20`–`P24` and `P17`/`P18` (`3010`/`2510`). |
| [Print-part inspection notes](PRINT_PARTS.md) | All 17 core roles + 8 accessory/3010 roles, bridge-support review, interlock fit, current meshes, and case orientations. |
| [Changes, digital checks, and gallery](PREVIEW.md) | v26a-j notes, new cross-bridges/recess, retained four-zone dimensions, six gallery views, exploded layout, GIF, and annotated v26h/v26j comparison. |
| [Generic per-build BOM](BOM.md) | Full reference inventory for one receiver, one tool, and the `P20`–`P24` / `3010` accessory suite. |
| [Incremental authoring source](source_v26/README.md) | Exactly **13 sealed modules**; prior live state and missing inputs prevent a clean one-command rebuild. |
| [Accessories architecture & verification](ACCESSORIES_PLAN.md) | Frozen v26j planning datums and complete verification summary for `P20`–`P24`, `P17_3010`/`2510`, and `P18_3010`. |

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

## Remaining work and next session

Actual servo body/spline fit, clocking, usable blind thread depth, spring
rate/preload, torque margin, heat-set pullout, snap retention, gear phase,
shaft sourcing, and thermal/endurance qualification remain open. Two rear
4x7x2mm bearing references and both standard compound-shaft lengths remain
**HOLD** in the [BOM](BOM.md). The bare Hall package still needs verified
support/wiring; neither pin-seat agreement nor bolt alignment completes
all coupling, magnet, or placement-grid checks.

The [accessories architecture & verification guide](ACCESSORIES_PLAN.md) and [SparkShift v26 Accessory & 3010 Toolhead Suite](cad/SparkShift_Accessories_v26/README.md) document the completed pure-primitive `P20`–`P24` and `P17_3010`/`P18_3010` package built against this **v26j / timeline 1648** baseline (`0.000 mm³` clash across all core bodies and Monolith 2WD 9mm gantry keepouts). Physical bench-testing of printed fits, thermal margins, blower backpressure, and sensor offsets remains required before heated or unattended operation.

## Licences and sources

The unchanged [LICENSE](LICENSE) retains GPL-3.0 for CxChanger/YUDX-derived
custom work. P13/P14 GT2 liners retain **CC BY-SA 3.0** credit. Vendor/hotend
references retain their respective rights; no blanket relicensing,
manufacturer certification, commercial validation, or official Voron
endorsement is asserted. See [mixed-scope attribution](ATTRIBUTION.md).
