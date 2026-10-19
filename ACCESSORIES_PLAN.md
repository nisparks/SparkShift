# SparkShift v26j Accessories & 3010 Toolhead Suite — Architecture, Planning Datums & Verification

> [!WARNING]
> **WIP / DIGITAL VERIFICATION COMPLETE / BENCH-FIT PENDING.**
> All 8 pure-primitive printable parts (`P20`–`P24`, `P17_3010`, `P17_2510`, `P18_3010`) in [`cad/SparkShift_Accessories_v26/`](cad/SparkShift_Accessories_v26/README.md) pass 100% of 3D B-Rep boolean, manifold STL, thermal keepout, Beacon 20mm metal keepout, NEMA14 (`17.4–21.8 mm`) motor clearance, and Voron 350 multi-toolhead docking checks against the frozen **v26j / timeline 1648** baseline (`0.000 mm³` clash). Physical bench qualification of printed tolerances, thermal creep, and electrical/firmware setup remains required before heated or unattended operation.

| 360° Full Assembly Turntable | Exploded Assembly Sequence |
| :---: | :---: |
| ![360° Full Assembly Turntable](cad/SparkShift_Accessories_v26/images/anim_01_full_assembly_360_turntable.gif) | ![Exploded Assembly Sequence](cad/SparkShift_Accessories_v26/images/anim_02_exploded_assembly_sequence.gif) |
| **3010 Toolhead Docking & `17.4–21.8 mm` NEMA14 Clearance** | **All 8 Pure-Primitive Printable Parts (360° Showcase)** |
| ![3010 Toolhead Docking & NEMA14 Clearance](cad/SparkShift_Accessories_v26/images/anim_03_toolhead_3010_docking_and_nema14_clearance.gif) | ![All 8 Printable Parts Showcase](cad/SparkShift_Accessories_v26/images/anim_04_printable_parts_360_showcase.gif) |

👉 **[Complete Documentation, 3D CFD Analysis, STEP/STL Exports & 17-View Gallery (`cad/SparkShift_Accessories_v26/README.md`)](cad/SparkShift_Accessories_v26/README.md)**

## Start a clean session from the final snapshot

Use [SparkShift_AHG_min_v26.f3d](cad/SparkShift_AHG_min_v26.f3d),
**timeline 1648 / 135 native bodies**, SHA-256
`37e384e8fd53f517b94f7dba5751e773c36e82f79493535b5b7a12b53291631a`.
Do not restart from the older timeline-1570, timeline-1589, or v26h
timeline-1632 or v26i timeline-1644 snapshots, replay all
authoring scripts, or silently redesign the core to accommodate accessories.
Keep a separately owned working copy and compare changes against this baseline.

Read the [current geometry/exception notes](PREVIEW.md) and
[generic core BOM](BOM.md) first. Carry forward unresolved servo-window
fit, cam/retainer, Hall support, shafts/bearings, loads, and thermal gates.
Accessories must not obstruct release, tool withdrawal, belt travel,
motor/servo connectors, insert access, or hotend service.

Carry forward the **v26h rear top bridge** and the paired **v26g flat P04F /
P03 magnet-backing** changes, not the old square P01 cutout or thin P03 wall.
The rear bridge occupies Y=0.30..2.15, X=-11.00..14.00, Z=26.50..48.70
outside the MR128 bore; the contoured clearance extends across Y=0.30..7.45.
Do not route wires, a bracket, or hose through that former opening.
P03's backing lies at Y=27.200..28.727 behind the +X magnets; P04F's
native flat face is Y=26.850, with a rear blind insert pocket and 6.250mm
of backing. These are protected core interfaces, not unused accessory stock.
The [print-part notes](PRINT_PARTS.md) distinguish native datums from STL
placement: **both P01 and P03 are now native Fusion binary STL exports
in assembly coordinates**, not bed-oriented. Their intended bed-face
references are P01 Y=0.30mm rear and P03 Y=31.50mm front.

Also preserve the **v26i four-zone X-shear interlocks**. Do not use their
mating faces or sockets as spare wire/board/hose clearance. Their nominal
0.15mm clearance is a fit allowance, not physical creep or strength validation;
accessory loads still require a load-path and long-term-creep review.

| Protected interlock region | Assembly envelope / relationship |
|---|---|
| +X lower keyhole boss/foot/rib | Bolt (X18.50, Z-14.60); male stock X=15.35..21.00, Z=-19.25..-12.10, Y=25.90..29.00; P03 socket to Y=29.15. |
| -X lower inner key | X=-13.50..-9.90, Z=-17.80..-12.00, Y=11.40..14.20; socket to Y=14.35. Preserve the neighbouring lower-right bolt/boss too. |
| -X mid-column key | X=-19.00..-15.60, Z=21.50..28.50, Y=11.40..14.20; socket to Y=14.35. |
| -X upper boss | R2.50 at (X-18.10, Z41.72), Y=11.40..14.20; R2.65 P03 socket to Y=14.35. |

These core-interface regions need access and engagement, not just collision
clearance. The existing case bolts remain necessary; adding an accessory
must not prevent the P01/P03 pair fully seating.

Preserve the **v26j triple-bridged P03 ladder frame and matching P01
lower-front recess** as well. Formerly open lower/middle space is not
available for cable ties, probe hardware or duct routing by assumption:

| New protected connection | Assembly envelope / boundary |
|---|---|
| P03 bottom cross-bridge | X=-13.70..13.70, Z=-19.08..-16.48, Y=9.35..11.65; 27.40 x 2.60 x 2.30mm overall. |
| P03 full-depth +X foot | X=9.20..22.50, Z=-20.40..-17.50, Y=9.35..26.00; nests in P01's matching 0.15mm-clearance recess. Do not consume the remaining blue-housing wall for accessories. |
| P03 mid-upper bridge | X=-3.50..3.50, Z=18.50..27.11, Y=16.01..19.50; behind the tool tongue (Y>=19.95) and in front of the rear arm (Y<=15.60). |

Recheck bracket/hose insertion and removable-tool paths around those
connections, not only the older shear-key envelope. The bridge changes
do not qualify structural creep, printer supports, or accessory load capacity;
the [print-part notes](PRINT_PARTS.md) keep support review separate.

## Frozen planning datums

All dimensions below are **assembly millimetres**, not print-bed coordinates.
Coordinate pairs explicitly use **(X, Z)**; triples use **(X, Y, Z)**.
These are CAD planning references, not supplier or printer-calibration values.

| Datum / envelope | Current reference |
|---|---|
| Filament/nozzle axis | X=0.00, Y=22.70; nozzle tip Z=-78.88. |
| Heater-block envelope | X=-9.50..9.50, Y=14.20..37.20, Z=-73.28..-53.28. |
| K1-heatsink reference | X=-11.00..11.00, Y=13.45..31.95, Z=-50.28..-24.28. These mixed hotend references do not certify a purchased assembly. |
| Overall case width | X=-22.50..22.50, 45.0mm. |
| P02 / rear servo frame | Plate Y=-6.70..0.30; frame extends to Y=-11.20. Preserve 11.60mm servo window and 11.5mm motor-entry notch for real-part fit/service review. |
| P01 / P03 depth | P01 base Y=0.30..11.40, +X cheek to Y=25.90 and shear key to Y=29.00, now relieved for the lower P03 beam/foot; P03 main joint Y=11.40..33.15, with lower bridge/foot reaching rearward to Y=9.35; removable tool carrier front Y=45.02. These are interlocking extents, not disjoint slab envelopes. |
| Deck / crown / lever | Deck Z=48.700; rear bearing/servo crown to Z=62.221; lever tip approximately Z=58.78 open / 60.72 closed. Preserve its swept envelope, not only endpoints. |
| Rear motor keep-out | Axis (X-1.248, Z4.251), R18.25, Y=-16.70..0.30. Motor ears at (X-16.75, Z19.75) and (X14.25, Z-11.25). |
| Motor XH2.54-4P exit | X=-19.35..-10.94, Y=-16.95..-11.45, Z=-13.85..-5.44; retain bend/plug-removal space beyond the CAD box. |
| Legacy servo keep-out | X=4.40..16.60, Y=-30.90..-2.66, Z=29.26..61.57. This 12.2mm reference intersects the latest 11.6mm window; replace assumptions with actual selected-servo measurements before design acceptance. |
| Lower P01 spine | Central X=-13.88..13.88, Y=0.30..11.40, Z=-57.279..-18.379; outer features reach X=+-22.50. |
| Four carriage holes | (X+-10.00, Z-27.779) and (X+-10.00, Z-47.779), 20x20mm pattern. Along Y: R1.65 bore 0.30..7.80, R3.00 counterbore 7.80..11.40. Do not consume carriage screw access. |
| Lower front accessory bosses | (X+-18.00, Z-52.780), 36.0mm span; R4.00 bosses extend to Y=15.900; 4.54mm heat-set-pocket references Y=11.40..15.90. Not already populated accessory hardware. |
| X-axis cross-bores | Y=5.300, Z=-22.479 and -53.079; R1.65 through central X=+-13.88; nut slots X=+-4.10..+-6.70. |
| Belt scallops | R4.70, X=+-19.00 / Y=4.94; Z=-48.979..-26.579. Keep the belt's moving/deflected path clear. |
| Right-side case-bolt anchors | Upper (X-18.10, Z41.72), lower (X-18.50, Z-14.45). These are upper **and lower**, not two upper bolts; extra bracket thickness/load needs fresh engagement and access checks. |

## Workstreams and acceptance gates

| Workstream | Intended next step | Required before accepting a design |
|---|---|---|
| **Beacon or Cartographer eddy-current probe** | Select one actual module/revision. Explore a low-profile bracket behind/below the lower spine, using lower accessory bosses and/or the Z=-53.079 cross-bore/bottom Z=-57.279 datum. Provide slotted or shimmed Z adjustment and a protected cable path. | Obtain the selected probe's PCB/coil/hole/connector drawings and required sensing height. A preliminary coil-plane envelope Z=-76.3..-75.8 is roughly 2.6..3.1mm above the reference nozzle, **not a universal sensor specification**. Check bed/nozzle reach, metal/magnet/thermal effects, withdrawal, crashes, and repeatability. |
| **CPAP lower part-cooling plenum and collar** | Co-package the probe and a split/dual-outlet duct around the lower spine and hotend, aiming airflow near (0, 22.70, -78.88) without changing the core axis. Keep nozzle, heater, thermistor, wiring, and tool removal serviceable. | Choose real hose/coupler dimensions, available pressure/flow and material/thermal constraints. Evaluate jet direction, pressure loss/leaks, nozzle/block clearance, probe airflow/inductive interference, and hot creep; zero thermal/inductive interference is a goal to test, not an achieved result. |
| **CPAP hose intake and strain relief** | Explore routing behind/beside P02/P01, avoiding servo, motor plug and lever. Consider a separate spine bracket or the documented upper/lower right bolt interfaces only after evaluating the load path. | Verify hose OD/ID, bend radius, coupler retention, moving-axis/umbilical sweep, pull loads, access, and screw engagement. Do not spend case-clamp engagement or twist the removable tool with hose load. |
| **CPAP blower mount** | Design a stationary printer-frame/gantry bracket and hose-whip route, separate from the lower duct. | Select actual blower, inlet/filter, supply/controller and mounting pattern. Check vibration, noise, strain relief, travel clearance, airflow, wiring protection and service. No generic blower or power stage is selected yet. |
| **BTT EBB42 CAN board and wire management** | Select the actual board revision. Explore behind-motor mounting (planning region Y<-17) or an angled rear bracket, avoiding servo/lead exits and preserving the motor-entry notch and case-bolt access. | Treat the earlier 40x40mm board / 31x31mm M3 pattern as **unverified planning placeholders**, not a manufacturer drawing. Confirm board outline, mounting holes, component/connector heights, insulation/standoffs, USB/CAN/tool umbilical, airflow and service access from the chosen revision. |

## Suggested clean-session order

1. Confirm the physical core/servo exception and inventory actual board,
   probe, hose/coupler and blower variants; preserve the frozen core datums.
2. Lay out probe plus lower duct together, including sensing-height adjustment,
   heater/service exclusions and removable-tool motion, before detailed brackets.
3. Route hose/strain relief and the stationary blower mount through full printer
   travel; keep those loads out of the detachable tool where possible.
4. Package the EBB42 and harness against actual connectors and service tools.
   Define receiver-versus-removable-tool wiring and disconnection intentionally.
5. Review full-stroke geometry and access, then independently check real fits,
   loads, sensing, cooling and electrical/thermal behaviour before expanding the
   BOM or describing any accessory as print/use-ready.

Board power, heater/servo/fan ratings, fusing, grounding, CAN termination,
cable flex and firmware configuration depend on selected hardware.
Provide adequately sized servo power/common ground; do not assume a board's
signal or fan pin can supply a servo or CPAP blower. No wiring diagram,
firmware setup, electrical certification, or heated-use approval is implied.

Preserve [GPL / CC BY-SA / vendor attribution](ATTRIBUTION.md) when adding
new sources or reference CAD.

---

## Implemented Pure-Primitive Accessory & 3010 Toolhead Package (`cad/SparkShift_Accessories_v26`)

| Part | STEP / STL Files | Solids / Shells | Volume (`mm³`) | Analytical Face Breakdown (`0` BSpline) | Min Face Area (`mm²`) | Bounding Box (`[Xmin, Ymin, Zmin] .. [Xmax, Ymax, Zmax]`) | Watertight Manifold / v26j Clash |
| :--- | :--- | :---: | :---: | :--- | :---: | :--- | :---: |
| **`P20`** | [`P20_CPAP_Hose_Inlet`](cad/SparkShift_Accessories_v26/step/P20_CPAP_Hose_Inlet.step) ([STL](stl_v26/P20_CPAP_Hose_Inlet.stl)) | `1 / 1` | `7,900.98` | `172` (`86` Plane, `75` Cyl, `11` Cone) | `0.4721` | `[-20.60, -59.35, -21.58] .. [20.60, -27.60, 30.00]` | `True` / `0.000 mm³` |
| **`P21`** | [`P21_CPAP_Gantry_Bridge`](cad/SparkShift_Accessories_v26/step/P21_CPAP_Gantry_Bridge.step) ([STL](stl_v26/P21_CPAP_Gantry_Bridge.stl)) | `1 / 1` | `9,969.26` | `143` (`79` Plane, `64` Cyl) | `0.5508` | `[-21.00, -45.40, -61.00] .. [21.00, 0.30, -17.78]` | `True` / `0.000 mm³` |
| **`P22`** | [`P22_CPAP_Lower_Plenum`](cad/SparkShift_Accessories_v26/step/P22_CPAP_Lower_Plenum.step) ([STL](stl_v26/P22_CPAP_Lower_Plenum.stl)) | `1 / 1` | `11,529.16` | `267` (`146` Plane, `121` Cyl) | `0.2506` | `[-22.42, -45.40, -77.85] .. [22.42, 35.20, -48.00]` | `True` / `0.000 mm³` |
| **`P23`** | [`P23_Beacon_Cartographer_Mount`](cad/SparkShift_Accessories_v26/step/P23_Beacon_Cartographer_Mount.step) ([STL](stl_v26/P23_Beacon_Cartographer_Mount.stl)) | `1 / 1` | `2,397.87` | `56` (`34` Plane, `22` Cyl) | `3.2287` | `[-19.20, -14.20, -75.00] .. [19.20, 11.55, -70.80]` | `True` / `0.000 mm³` |
| **`P24`** | [`P24_EBB42_Controller_Mount`](cad/SparkShift_Accessories_v26/step/P24_EBB42_Controller_Mount.step) ([STL](stl_v26/P24_EBB42_Controller_Mount.stl)) | `1 / 1` | `8,762.85` | `196` (`107` Plane, `89` Cyl) | `0.1702` | `[-21.80, -25.40, -18.40] .. [22.10, -2.50, 51.20]` | `True` / `0.000 mm³` |
| **`P17 (3010)`** | [`P17_HF_tool_carrier_3010`](cad/SparkShift_Accessories_v26/step/P17_HF_tool_carrier_3010.step) ([STL](stl_v26/P17_HF_tool_carrier_3010.stl)) | `1 / 1` | `11,656.13` | `270` (`164` Plane, `102` Cyl, `4` Cone) | `0.2752` | `[-15.00, 11.50, -52.50] .. [15.00, 35.93, 48.74]` | `True` / `0.000 mm³` |
| **`P17 (2510)`** | [`P17_HF_tool_carrier_2510`](cad/SparkShift_Accessories_v26/step/P17_HF_tool_carrier_2510.step) ([STL](stl_v26/P17_HF_tool_carrier_2510.stl)) | `1 / 1` | `11,098.13` | `245` (`142` Plane, `99` Cyl, `4` Cone) | `0.4088` | `[-12.40, 11.50, -51.80] .. [12.40, 35.93, 48.74]` | `True` / `0.000 mm³` |
| **`P18 (3010)`** | [`P18_Tool_docking_backplate_3010`](cad/SparkShift_Accessories_v26/step/P18_Tool_docking_backplate_3010.step) ([STL](stl_v26/P18_Tool_docking_backplate_3010.stl)) | `1 / 1` | `2,718.87` | `70` (`52` Plane, `18` Cyl) | `1.4000` | `[-10.01, 35.93, -22.45] .. [10.03, 45.02, 48.75]` | `True` / `0.000 mm³` |

See [`cad/SparkShift_Accessories_v26/README.md`](cad/SparkShift_Accessories_v26/README.md) and [`cad/SparkShift_Accessories_v26/verification_accessories_v26.json`](cad/SparkShift_Accessories_v26/verification_accessories_v26.json) for full engineering details.

