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

## Current development: v26 open frame

The current snapshot preserves the latest manual refinements and the
v26 agreement/clearance pass:

- Open structural P01/P03 frame with **bilateral cam bearings**: rear
  **MR128ZZ 8x12x3.5mm** and front **MF85ZZ 5x8x2.5mm**.
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

## Matched inspection package

| File / guide | Scope |
|---|---|
| [v26 native F3D](cad/SparkShift_AHG_min_v26.f3d) | Directly editable snapshot: **135 native bodies**, timeline **1589**; native review reports 135/135 readback matches. |
| [v26 whole-assembly STEP](cad/SparkShift_AHG_min_v26.step) | 135 solid BREP records; neutral inspection export, not a manufacturing qualification. |
| [17 assembly STLs](stl_v26) | Complete matched inspection set, not print-ready or support-free. |
| [Changes, digital checks, and six renders](PREVIEW.md) | v26a-f change notes, current geometry, exceptions, and evidence limits. |
| [Generic per-build BOM](BOM.md) | Full reference inventory for one receiver plus one tool, not a personal shopping delta. |
| [Incremental authoring source](source_v26/README.md) | Exactly **13 sealed modules**; prior live state and missing inputs prevent a clean one-command rebuild. |
| [Next-session accessories plan](ACCESSORIES_PLAN.md) | EBB42 mounting/wiring, Beacon or Cartographer, CPAP duct/collar, hose, and stationary blower mount; **planned, not implemented**. |

The 17 raw native inspection meshes total **568,066 facets**. Each is one
closed, manifold, coherently wound, positive-volume component, with zero
degenerate facets and **no zero or inverted stored normals found** in this
set. Native bytes are unchanged. These digital checks do not establish
printability, deposition resolution, supports, fits, or safe use;
**inspect every mesh in a slicer** before any later fabrication decision.

Only the matched v26 CAD, meshes, six static renders, and authoring snapshot
are current. **No v26 portable playback, GIF, or calibration-gauge package
is supplied.** Older files remain in Git history, not as compatible v26 tools.
Drive Joint alone is not proof of synchronized cam/arm motion or force physics.

## Remaining work and next session

Actual servo body/spline fit, clocking, usable blind thread depth, spring
rate/preload, torque margin, heat-set pullout, snap retention, gear phase,
shaft sourcing, and thermal/endurance qualification remain open. Two rear
4x7x2mm bearing references and both standard compound-shaft lengths remain
**HOLD** in the [BOM](BOM.md). The bare Hall package still needs verified
support/wiring; neither pin-seat agreement nor bolt alignment completes
all coupling, magnet, or placement-grid checks.

The [accessories plan](ACCESSORIES_PLAN.md) is the clean-session handoff:
start from this **v26 / timeline 1589** F3D, confirm real board/probe/hose
variants, then co-design probe and cooling clearances without moving the
core datums by accident. No EBB42, probe, CPAP duct, hose, or blower mount
is represented as finished or included in the current build inventory.

## Licences and sources

The unchanged [LICENSE](LICENSE) retains GPL-3.0 for CxChanger/YUDX-derived
custom work. P13/P14 GT2 liners retain **CC BY-SA 3.0** credit. Vendor/hotend
references retain their respective rights; no blanket relicensing,
manufacturer certification, commercial validation, or official Voron
endorsement is asserted. See [mixed-scope attribution](ATTRIBUTION.md).
