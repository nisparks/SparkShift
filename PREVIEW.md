# v9 inspection notes

> [!WARNING]
> **WIP / NOT READY FOR PRINTING OR USE.** Native CAD, STLs, and tool source are
> for inspection/development only. This **vibe developed** project uses
> AI-assisted mechanical CAD under human direction, not professional engineering
> validation or physical qualification.

## One current set

[SparkShift_AHG_min_v9.f3d](cad/SparkShift_AHG_min_v9.f3d) is the native review
assembly. [All 17 v9 STLs](stl_v9) are millimeter, bed-oriented inspection
exports, **not a printing recipe or support-free parts**. No older STEP/native
variant or qualified motion helper accompanies them.

The design retains purchased HGX steel hobs/needles without modification,
the factory-10T LDO pancake motor, independent MG90S cam, 45mm printed core,
and four 9mm belt interfaces. It has 143 modeled bodies and 17 prints.
Modeled bodies include purchased assemblies and display references; they are
not 143 separately orderable parts.

The previous one-piece-arm and separate-journal proposals are not this model.
Do not mix old meshes, pin lengths, mounting dimensions, or helper controls
with this set. The [source notes](scripts/README.md) explain why predecessor
mutation functions are not a replay of v9.

## Arm and cam interfaces

P04R/P04F form a **two-piece arm**. An upper M3x10 socket-head clamp and a
lower M3x14 button-head screw into a backed M3 heat-set keep the joint together;
there is no loose lower hex nut. The rounded central key registers the halves.
Its nominal 3.5x4.6mm section, 2.35mm engagement, and 0.15mm side/tip allowances
are geometric references, not a torsional-stiffness rating.

Both arm pilots are **4.0mm diameter**, with short 0.4mm tapers to 4.4mm for
the short-M3 **4.6mm OD x 4mm** insert reference. The lower host has a rear
backing shoulder. Actual insert family, printer/material fit, installation,
and pullout strength still need calibration; generic "M3" is not a fit match.

The compact printed cam captures the **supplied matching horn as the real
spline insert**. Its integral journal runs in an **MF85ZZ 5x8x2.5mm flanged
bearing**. No manufactured or printed female spline fit is claimed.
The center retainer is an **M2x16 reference only**: the actual MG90S retaining
thread, permitted engagement, horn, and printed-journal fit are unverified.
Do not order or force that assumed screw based on this drawing.

MG90S is the selected baseline: one needed, zero to order if owned stock
actually matches. Stall specifications do not prove working torque headroom.
The printed cam's observed strength is not evidence of long-term durability or
a verified all-metal torque path. See [hardware fit holds](BOM.md).

## Surface cleanup and preserved geometry

Translated cylinder/cone families and repeated planar ridge strips are healed
or replaced with continuous native surfaces, not hidden edges or smoothed meshes.
The case and arm cleanup retains the complete magnet backing, protected
bearing-seat support, working gear/cam profiles, and tool-interface references.
P17 uses one 2.7mm axial filament passage on the retained internal filament
datum; other nozzle/docking datums and purchased hotend shapes are unchanged.

The frozen lower/belt band has **zero added/removed material against the
captured input**. This is a comparison boundary, not a guarantee of calibrated
printer/tool/probe offsets or material strength. Prior prototype offsets and
stock envelopes must not be assumed correct for a printer installation.

## Digital evidence and its limit

| Saved source result | What it establishes, and what it does not |
|---|---|
| v9 native archive reopens with matching 17 prints and 143 bodies | Shape/inventory readback, not a complete working mechanism or healthy current drive-link ratio. |
| Raw and bed-oriented meshes are closed and consistently wound | Rigidly placed inspection exports without mesh repair; not printable deposition, support-free geometry, or hardware fit. |
| Protected-region and magnet-backing comparisons | Retained seat support, backed magnet footprint, and unchanged lower/belt band; not a load, fatigue, or thermal rating. |
| Sampled arm/cam and 35mm whole-tool travel | Clean checked samples, not continuous motion/full gear-phase coverage or physical service qualification. |

The saved P01 history retains the user's existing `Extrude2` warning. No new
feature errors are reported in this cleanup, but **the old warning is not fixed
or hidden**.

Unresolved items include small legacy gear gaps, the old native drive-link
ratio, nonstandard modeled compound-shaft lengths, axial retention under
vibration, loaded strength/torsional stiffness, spring/servo margin, hot
creep/life, cooling, and safe controls. The old motion helper has been removed:
native animation is not qualified current factory-10T behavior.

Complete physical assembly, loaded hotend exchange, actual FDM deposition,
reliability, thermal, and safety tests remain unperformed. No G-code, printer
profile, calibration offsets, heater operation, or unattended-use approval is
supplied. CPAP and sensor/probe accessories remain deferred.

Read [licence/source attribution](ATTRIBUTION.md) before redistribution.
Vibe-development acknowledgement does not replace upstream authorship or
extend rights over purchased-hardware/hotend reference geometry.
