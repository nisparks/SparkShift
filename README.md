# SparkShift

> [!WARNING]
> **WORK IN PROGRESS / NOT READY FOR PRINTING OR USE**
>
> This is an evolving, untested mechanical CAD concept. All files are for
> **inspection, design review, and development only**. Bed-oriented STLs and
> successful digital checks do not make this a print-ready release.
>
> Complete physical assembly, functional hotend exchange, loaded actuation,
> reliability, thermal, and safety testing have not qualified the design.
> Do not treat it as ready to install in a printer or operate heated/unattended.

**HGX quick-change hotend system**

*Same drive. New hotend.*

SparkShift is a provisional name for an original-inspired, YUDX-derived
community design. One permanent LDO-36STH20-1004AHG(XH) factory-10T pancake motor
and unmodified purchased HGX drive stay on the carriage; an independent MG90S
cam releases the swinging driven hob. Ordinary forward/reverse extrusion must
remain independent of arm opening.

**Vibe developed:** this project's iterative mechanical CAD and tooling were
AI-assisted under human direction, not professionally engineered or validated.
That describes the SparkShift development process, **not the authorship of the
upstream CxChanger/YUDX design or vendor parts**. Their credit and rights remain
in [ATTRIBUTION.md](ATTRIBUTION.md).

## Current v9 inspection files

**WIP / NOT READY FOR PRINTING:** use this one matched set for review only.
There are no preview images, videos, alternate native models, assembly STEP,
or qualified motion helper in the current tree.

| File / guide | Inspection purpose |
|---|---|
| [SparkShift AHG-min v9 F3D](cad/SparkShift_AHG_min_v9.f3d) | Current native assembly: 143 modeled bodies and 17 printed-part shapes. |
| [17 v9 STLs](stl_v9) | Millimeter, bed-oriented review exports; **not ready for printing**, not support-free. |
| [Preview and limitations](PREVIEW.md) | Current geometry, bounded digital evidence, unresolved issues. |
| [Modeled hardware / print roles](BOM.md) | Reference quantities and fit holds, **not an approved shopping list or build guide**. |
| [CAD-tool source notes](scripts/README.md) | Required adjacent Python tools and dependency/usage limits; not a one-command rebuild or printer controller. |

## What v9 contains

The 45mm printed core and four unchanged 9mm belt interfaces are retained.
Translated circle/cone bands and planar ridge strips are consolidated while
protecting bearing-seat support, full magnet backing, and the captured lower/
belt band.

The arm is **two-piece P04R/P04F**, with an upper M3x10 clamp, a lower M3x14
button-head screw into a backed short M3 heat-set, and a rounded central key.
The compact cam captures the supplied matching horn as its real spline insert
and uses a short integral journal with an MF85ZZ bearing. No fabricated
print-ready female spline teeth are supplied.

## Still unresolved

Actual servo retaining thread/horn fit, printed-journal and insert fits, spring/
servo margin, loaded strength and torsional stiffness, retention, hot creep/life,
cooling, and safe controls are unqualified. The M2x16 cam center retainer is
**reference only**, not a verified purchase.

Small legacy gear gaps, the old native drive-link ratio, and nonstandard
modeled compound-shaft lengths remain open. Sampled arm/cam and 35mm whole-tool
travel checks are not continuous/full gear-phase or physical qualification.
The user's pre-existing P01 `Extrude2` warning is preserved; this cleanup does
not conceal it or claim a completely healthy feature history.

CPAP and sensor/probe accessories remain deferred. MG90S is selected with reuse
of matching owned stock, not a torque-headroom guarantee. Geometry and hardware
may change before any usable design or print package exists.

## Licences and sources

The unchanged [LICENSE](LICENSE) retains GPL-3.0 for the CxChanger/YUDX-derived
custom work. P13/P14 GT2 tooth liners retain separate **CC BY-SA 3.0** credit.
Vendor hardware and hotend references are not blanket relicensed or
manufacturer-certified. See [mixed-scope attribution](ATTRIBUTION.md).
