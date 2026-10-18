# Next-session accessories plan -- v26h baseline

> [!WARNING]
> **PLAN ONLY / WIP / FIT PENDING / NOT READY FOR PRINTING OR USE.**
> This human-directed, AI-assisted **vibe developed** core is not physically
> qualified. No EBB42 mount, probe bracket, CPAP duct/collar, hose support,
> or blower mount is finished or included in the current print set/BOM.

## Start a clean session from the final snapshot

Use [SparkShift_AHG_min_v26.f3d](cad/SparkShift_AHG_min_v26.f3d),
**timeline 1632 / 135 native bodies**, SHA-256
`dda41c30d379930061c16e888b51b65f641c6bd47386086551236c59545db501`.
Do not restart from the older timeline-1570 or timeline-1589 snapshots, replay all
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
placement: P01's OpenCascade mesh is still in assembly coordinates.

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
| P01 / P03 depth | P01 Y=0.30..11.40, with +X cheek reaching Y=25.90; P03 Y=11.40..33.15; removable tool carrier front Y=45.02. |
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
new sources or reference CAD. This plan records next-session scope, not
completed accessory geometry or new purchasing requirements.
