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
ladder frame**, rather than an inverted U, nested into a matching P01 recess:

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

![WIP historical v26g P04F flat-face and P03 magnet-backing comparison, before later shear sockets and bridges](images_v26/v26_magnet_wall_reinforcement.png)

The comparison records the **earlier v26g reinforcement**:
P04F's shortened flat face allows **+1,041.652mm3** of P03 backing/side-wall
material. The backing concept is retained, but this panel predates the
v26i shear sockets and v26j cross-bridges; it is not an exact view or volume
delta of the current P03. None of these changes proves retention strength.

## Matched inspection package

| File / guide | Scope |
|---|---|
| [v26 native F3D](cad/SparkShift_AHG_min_v26.f3d) | Directly editable **v26j** snapshot: **135 native bodies**, timeline **1648**; native review reports 135/135 readback matches. |
| [v26 whole-assembly STEP](cad/SparkShift_AHG_min_v26.step) | 135 solid BREP records; neutral inspection export, not a manufacturing qualification. |
| [17 assembly STLs](stl_v26) | Complete matched inspection set, not print-ready or support-free. |
| [Print-part inspection notes](PRINT_PARTS.md) | All 17 roles, bridge-support review, interlock fit, current meshes, and both case orientations. |
| [Changes, digital checks, and gallery](PREVIEW.md) | v26a-j notes, new cross-bridges/recess, retained four-zone dimensions, six refreshed views, exploded layout, GIF, and historical comparison. |
| [Generic per-build BOM](BOM.md) | Full reference inventory for one receiver plus one tool, not a personal shopping delta. |
| [Incremental authoring source](source_v26/README.md) | Exactly **13 sealed modules**; prior live state and missing inputs prevent a clean one-command rebuild. |
| [Next-session accessories plan](ACCESSORIES_PLAN.md) | EBB42 mounting/wiring, Beacon or Cartographer, CPAP duct/collar, hose, and stationary blower mount; **planned, not implemented**. |

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

The [accessories plan](ACCESSORIES_PLAN.md) is the clean-session handoff:
start from this **v26j / timeline 1648** F3D, confirm real board/probe/hose
variants, then co-design probe and cooling clearances without moving the
core datums by accident. No EBB42, probe, CPAP duct, hose, or blower mount
is represented as finished or included in the current build inventory.

## Licences and sources

The unchanged [LICENSE](LICENSE) retains GPL-3.0 for CxChanger/YUDX-derived
custom work. P13/P14 GT2 liners retain **CC BY-SA 3.0** credit. Vendor/hotend
references retain their respective rights; no blanket relicensing,
manufacturer certification, commercial validation, or official Voron
endorsement is asserted. See [mixed-scope attribution](ATTRIBUTION.md).
