# v26h inspection and change notes

> [!WARNING]
> **WIP / FIT PENDING / NOT READY FOR PRINTING OR USE.** This substantial,
> human-directed, AI-assisted **vibe developed** work is not professional
> engineering or physical qualification. Digital geometry and sampled
> clearances do not approve loaded operation, heat, strength, or endurance.

Use the matched [v26 F3D](cad/SparkShift_AHG_min_v26.f3d),
[whole-assembly STEP](cad/SparkShift_AHG_min_v26.step), and
[17 inspection STLs](stl_v26). The editable F3D is the **timeline 1632,
135-body v26h** snapshot, not the earlier timeline-1589 publication.
See [all print roles and orientation notes](PRINT_PARTS.md). Eight PNGs
and one GIF are approved render/preview assets, not physical tests.

## What changed

| Area | Current v26 state |
|---|---|
| P01/P03 structure | Contoured arm clearance remains, but the old square opening is closed by a **1.85mm continuous rear top bridge**, joining the upper bolt towers outside the MR128 bore. P03 retains its compact receiver cross-tie below the retainer. |
| Cam support | Rear MR128ZZ **8x12x3.5mm**, Y=-1.05..2.45 across P02/P01; front MF85ZZ **5x8x2.5mm**, Y=10.70..13.20 in the P03 cam tower. |
| P02 motor/servo plate | **7mm**, Y=-6.70..0.30. Continuous rear ear-seat frame reaches Y=-11.20; two **M2x8 self-tapping screws** use 1.7mm pilots. No servo-ear M2 nuts, washers, or M2 heat-sets. |
| Latest servo window | **11.60 x 22.56mm**, X=4.70..16.30, Z=34.06..56.62, Y=-11.20..-6.00. R5.800 tower clearance at (X10.500, Z50.721) is tangent to the sides; R3.000 bump clearance is centred at (X10.550, Z44.620), to Y=-2.00. |
| Motor entry | **11.5mm** notch, X=-6.998..4.502, approximately Z=21.5..27.4, with R1.5 bore-entry rounds. Preserve connector insertion/service clearance. |
| Case clamps | Four corner M3 button-head references have modelled **2.0mm AF x 0.9mm** hex sockets. Real heat-sets remain; see the exact lengths/hosts below and in the BOM. |
| Lower-left post | Screw axis moved to (X18.50, Z-14.60), with a concentric R2.7742 boss and R1.6922 tangent blend, replacing the thin offset corner/notch. Nominal screw-hole wall is 1.124mm; that is not a strength rating. |
| Maxwell interface | Six locating pins retain YUDX-matched axes; P03 uses full-length conformal **teardrop snap seats** instead of fragmented end-box seats. Balls and eight bar-magnet interfaces remain references needing real retention/fit checks. |
| P04R/P04F arms | P04R retains its **15mm shorter G1-tangent** lever. P04F now has one flat Y=26.850mm print-face reference, unified X19.830mm side wall, restored rear blind insert pocket, and cleaned R9.35 gear-clearance arc. |
| P03 magnet backing | Y=27.200..29.800mm reclaimed from the shortened P04F gives both +X receiver magnets **1.527mm continuous rear backing** and uninterrupted side walls. P03 gains **1,041.652mm3**; see the before/after comparison below. |
| Case agreement | Z48.700 decks, aligned lower wire-slot surfaces, and continuous **R1.5 rounds along all four longitudinal outer edges** of the P01/P02/P03 assembly. Cam, bearing, insert, magnet, and pin interfaces were not made arbitrarily symmetric. |

### v26a-h sequence, preserving manual edits

| Pass | Recorded change |
|---|---|
| v26a | Case/corner agreement, sliver/step cleanup, and analytic arm cam-clearance surfaces; retained the manual P04F/P03 edits. |
| v26b | Kept the manual bay-wall deletions, then re-cut P03's R6.9 boss bay and R4.4 lobe groove with nominal 0.4mm local clearance and a tangent ceiling junction. |
| v26c | Thickened the lower-left clamp load path and moved its screw/insert; preserved the manual P02 R1.5 corner round. |
| v26d | Moved right-side bolts and heat-set pockets, removed retired locating sockets, and completed matching modelled head sockets. |
| v26e | Kept the rear servo frame/motor-notch edits, shortened/blended the lever, unified the crown/deck, and cleaned P04F steps without closing functional arm clearance. |
| v26f | Preserved the 11.6mm tangent servo-window/keyhole edits and matching outer rounds; this was the previous timeline-1589 publication. |
| v26g | Kept the flat P04F face, restored the rear blind M3 insert/pocket, and reclaimed P03 magnet backing with full sampled cam clearance. |
| v26h | Replaced P01's square upper cutout with a continuous rear top bridge and extended analytical arm-relief ramp; refreshed the matched exports and visual set at timeline 1632. |

This is a change log, not instructions to replay older candidates. No
intermediate exports, raw reports, or private authoring inputs are shipped.

### Three revised printed parts

| Part | Current native review | Refinement / boundary |
|---|---|---|
| P04F | **3,854.094mm3 / 83 faces** | Front face pulled back **2.550mm** to Y=26.850mm, about 493mm2 flat contact area. Rear blind M3 pocket at native (X14.950, Z31.400), Y=15.60..20.60, retains **6.250mm** wall behind the print face; actual insert/material fit still needs checks. |
| P03 | **30,344.189mm3 / 209 faces** | Pocket floor Y=27.200mm is nominally 0.350mm ahead of the P04F plane. +X magnets at Y=28.727..31.500 retain backing Y=27.200..28.727; that local plane gap is not a global minimum clearance. |
| P01 | **33,757.291mm3 / 218 faces** | Extended the R9/sloped analytic ramp across Y=0.30..7.45. Rear bridge Y=0.30..2.15, X=-11.00..14.00, Z=26.50..48.70, outside the MR128 bore, connects the upper towers; no strength/deflection rating is implied. |

The P03 reinforcement review reports **0.000mm3 overlap across 71 cam
poses**, 0..175 degrees in 2.5-degree steps. Sampling is not proof of every
continuous pose, deflection, snap force, or a real-world removal procedure.

## Case bolts and assembly references

Pairs below are **(X, Z) in assembly millimetres**; each bolt runs along Y.
"Left/right" follows the recorded model names, not a viewer's screen.

| Location | Axis (X, Z) | Screw reference | Heat-set host / axial interval |
|---|---|---|---|
| Upper-left | (18.10, 41.72) | M3x30 button head | P01, Y=0.30..4.30 |
| Upper-right | (-18.10, 41.72) | M3x35 button head | Rear-loaded P02, Y=-6.50..-2.50 |
| Lower-left | (18.50, -14.60) | M3x25 button head | P01, Y=6.00..10.00 |
| Lower-right | (-18.50, -14.45) | M3x35 button head | Front-loaded P02, Y=-3.70..0.30 |

Upper axes mirror exactly; lower X positions mirror, but lower-right Z is
**0.15mm higher** to retain approximately 1.03mm wall to its heat-set knurl.
This is not complete geometric symmetry or a validated fastener specification.
The distinct plate retainer is **one M3x10 button head** at (17.25, 23.72)
into a P01 heat-set. Motor ears use **two M3x10 button heads** into the
motor flange, not the superseded M3x18 references.

Plan rear-bearing insertion before closing P02 around its seat, and
bench-check the cam, both bearings, servo, washer, and retainer stack.
Front-/rear-loaded insert pockets imply different access directions;
physical iron clearance, seating, pilot fit, screw engagement, torque,
and service access remain unqualified. Do not substitute case nuts.

The printed cam/hub remains direct to the reference **21T servo output**,
with **no OEM horn**, one **M2.5x16** retainer and **2.7/6/0.5mm** washer.
The reference crest OD 4.86mm / exposed spline height 3.36mm / M2.5 thread
do not certify another servo. Historical 4.62mm root/sinusoidal flank and
+0.025mm normal allowance are empirical trials, not maker-standard teeth.
**Measure actual usable blind depth and the final stack before tightening**;
exposed shaft height is not thread depth. Do not force a bottomed retainer.
An earlier assembly's nominal engagement is not a v26 fit certificate.

## Digital checks and their limits

| Check on this source-bound package | Result / boundary |
|---|---|
| Native archive | **33,216,081 bytes; timeline 1632**; native review reports **135/135 body readback matches**, maximum difference 0.000mm3. This is not a physical fit/load test. |
| Whole STEP | **21,706,844 bytes; 135/135 valid solid readbacks reported**, with 135 solid BREP records. Structural completeness does not claim independent STEP/native shape or scalar-mass equality. |
| Inspection mesh set | **17 parts / 482,686 facets**; each one closed, manifold, coherently wound, positive-volume component; zero degenerate triangles. |
| P01 tessellation | **11,578 facets**, generated directly from the v26h BRep using OpenCascade. Mesh volume 33,771.359mm3 vs analytic 33,757.291mm3: **0.0416741%** chordal approximation, not an exact volume/shape match. |
| Stored STL normals | **Zero zero-length or inverted stored normals found** in the current 17-part set. The older P01 metadata warning count is not carried into v26. |
| Tool withdrawal | Native review reports **36/36 sampled offsets clear**. This does not prove every continuous path or a real removal procedure. |
| Filament feed | Native review reports **48/48 sampled pairs clear**. This is not extrusion/load/thermal qualification. |
| Cam motion | Final source-bound review reports **zero cam-motion overlaps**. This is sampled geometry, not force, spring, or torque qualification; retain the servo-envelope exception below. |

**Known servo-envelope exception:** the legacy **12.2mm**
`HOBBY_SERVO_ENVELOPE` intersects the tightened **11.6mm** P02 window.
Earlier MG90S/MG90D STEP ear-seat studies do not prove the latest opening
fits any purchased variant. Measure body, tower, ears, output, and lead
exit on the selected unit; do not describe this model as collision-free
without that exception.

The mesh bytes are preserved without repair, facet deletion, or normal
rewriting. **P01 remains in assembly coordinates**, including negative Z,
not on the print bed. Its tessellation is OpenCascade, not a Fusion native
STL export. Other inspection orientations also require deliberate review;
none is support-free/print-ready approval. Small tessellation/float residues
remain possible.
**Inspect each mesh in a slicer**, including thin walls, surfaces, supports,
and actual material/nozzle resolution.

The underlying cam work uses contact-curve kinematics, not spring-force,
friction, torque, servo-current, or real-time physical simulation. The
current GIF labels a **0..175-degree cam**, reaching **7.87 degrees of arm
rotation and 2.73mm hob bite release gap** at full open. The labelled gap
is a CAD-preview metric, not a measured physical clearance. Do not mix it
with older nominal opening metrics or convert the animation into servo
pulse-width commands; actual clocking/endpoints require calibration.
Concentric dwell removes ideal normal-force backdrive torque, **not
spring/bearing load or friction**, and is **not a positive power-off latch**.
Drive Joint alone does not establish synchronized cam/arm motion.
The GIF is a rendered preview; **no matched v26 standalone portable
playback script is supplied**.

Source tools are an [incremental live-state snapshot](source_v26/README.md),
not a complete clean-checkout rebuild. Native timeline readback and healthy
appended features do not establish that all inherited history is warning-free.

## Current rendered gallery

The **six refreshed gallery PNGs**, exploded architecture PNG, reinforcement
comparison PNG, and dual-viewport GIF are **source-bound rendered inspection
assets**, not native-UI screenshots, photographs, physical tests, or an
accessory design. The before/after panel labels the retained v26g change;
its earlier view is explicitly historical, not the current P03 geometry.
Colours, offsets, transparency, and hidden bodies are inspection aids.

![WIP v26h exploded architecture, diagram offsets are not validated assembly paths](images_v26/v26_exploded_assembly.png)

The corrected exploded layout separates all 17 printed roles and selected
hardware/hotend references. Separation arrows do not qualify assembly
order, access tools, or a collision-free continuous withdrawal path.

![WIP v26h dual-viewport cam opening and return, rendered kinematics only](images_v26/v26_cam_opening_motion.gif)

**71 frames / 1280x784 / 3.44 seconds**, fully decoded during publication
checks. The GIF's frame count is not the 71-pose geometry sampling grid.
Its playback rate is not physical servo speed, spring return, force,
friction, thermal, or simultaneous feed/release simulation.

![WIP retained v26g P04F and P03 magnet-wall before-and-after comparison](images_v26/v26_magnet_wall_reinforcement.png)

The two after-panels show P03 reinforcement and the shortened P04F together,
not an additional printed part. The P01 top bridge is the subsequent v26h change.

![WIP v26 rendered closed assembly with removable tool, not a physical build](images_v26/v26_assembly_closed_front_iso.png)

Closed view with the reference tool carrier and hotend. Vendor geometry
does not establish a certified hotend assembly or safe thermal use.

![WIP v26 rendered open assembly pose, not force or spring-return simulation](images_v26/v26_assembly_open_front_iso.png)

Open cam/arm pose, not calibrated servo endpoints or a full-motion recording.

![WIP v26 rendered rear assembly and open motor-servo plate](images_v26/v26_assembly_rear_iso.png)

Rear view exposes the plate, motor, and ear-seat frame. The servo envelope
is hidden for inspection; its absence from the render is not a fit pass.

![WIP v26 rendered front case with four socketed bolt heads and Maxwell pin seats](images_v26/v26_front_case_and_bolts.png)

Tool/interface bodies are selectively hidden to show the teardrop pin seats,
bar-magnet pockets, and case bolts; this is not a physical operating setup.

![WIP v26 rendered rear ear-seat frame, tangent window and motor-entry notch](images_v26/v26_rear_servo_and_motor_plate.png)

The tightened window must be checked against the selected real servo.

![WIP v26 rendered rounded crown, opposite-side cam support and shortened manual lever](images_v26/v26_upper_crown_and_lever.png)

Deck/round agreement and lever clearance are geometric, not loaded strength
or hand-access qualification.

## Remaining gates and next-session scope

Real spline/body fit, clocking, retainer bottoming margin, spring/preload,
servo torque, snap force, insert retention, full gear phase, shaft sourcing,
hot creep, wiring/controls, and endurance remain open. The two rear
4x7x2mm supports and both standard compound-shaft lengths remain **HOLD**.
The bare Hall package still needs verified support and electrical integration.
YUDX pin-seat agreement does not finish all magnet/Maxwell alignment or
the broader 0.05mm placement-grid goal.

The lower arm/magnet region retains functional clearance details; it was
not indiscriminately filled or rounded. P03's new magnet backing is
deliberately paired with the shortened P04F and checked sampled motion.
Broad symmetry, accessory holes,
or vendor envelopes must not be changed merely to make a render look clean.

The next session should follow the [accessories plan](ACCESSORIES_PLAN.md):
EBB42, Beacon/Cartographer, CPAP lower plenum/collar, hose/strain relief, and
stationary blower mounting are **planned only**, with real-part and thermal/
electrical checks before design acceptance. See the [generic BOM](BOM.md)
and [mixed-scope attribution](ATTRIBUTION.md). GPL-3.0 custom work, separate
CC BY-SA 3.0 P13/P14 liners, and vendor-reference rights are preserved.
