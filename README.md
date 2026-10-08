# SparkShift

> [!WARNING]
> **WORK IN PROGRESS / UNTESTED / NOT READY FOR USE**
>
> This is an evolving CAD-only design, not a tested working extruder or
> hotend-exchange assembly. **All files are for design review and contribution
> only**, not print-ready parts or installation/operation instructions.
>
> The design has **not been validated by complete physical assembly, functional
> hotend exchange, loaded actuation, reliability, thermal, or safety testing**.
> Do not treat it as ready to drop into a printer or operate heated/unattended.

**HGX quick-change hotend system**

*Same drive. New hotend.*

SparkShift is a provisional name for this YUDX-derived community design. The
concept keeps one permanent square NEMA14 motor and HGX drive on the carriage,
with an independent servo-cam release intended to open the swinging driven hob.
Ordinary forward or reverse extrusion must not open the arm.

This private repository is a **latest-only collaborator preview**, not a local
engineering archive, production product, or official Voron project.

![SparkShift CAD concept assembly and mechanism inset](images/SparkShift_preview.png)

CAD illustration, not a tested assembly or product photograph. Geometric,
native CAD-motion, and export checks exist, but they are **not hardware tests or
real-world qualification**. The presence of F3D/STEP/STL files and images does
not establish that the design works.

## Design-review files

| File / guide | Purpose |
|---|---|
| [SparkShift.f3d](cad/SparkShift.f3d) | Editable grouped/jointed CAD concept. |
| [SparkShift.step](cad/SparkShift.step) | Assembly geometry for design review. |
| [16 current STL parts](stl) | Millimeter, bed-oriented review meshes; not a print-ready release. |
| [SparkShift motion helper](scripts/SparkShift_motion/SparkShift_motion.py) | CAD-only demonstration; [usage](PREVIEW.md#coordinated-native-motion). No printer commands. |
| [Modeled hardware/BOM](BOM.md) | Current modeled quantities and fit caveats, not a complete or qualified build BOM. |
| [Preview notes](PREVIEW.md) | CAD demonstration scope and limitations, not installation/operation instructions. |

## Unresolved work

- Actual servo model/spline and the metal cam-drive interface remain unresolved;
  the torsion neck must be redesigned. MG90S is only an inventory candidate,
  **not torque-qualified**.
- Spring load and physical HGX gear mesh/fits need validation.
- Thermal behavior, cooling, and safe control remain unqualified. CPAP and
  sensor/probe accessories remain deferred.

Geometry, interfaces, and modeled hardware may change as development continues.
The files and notes are not a complete build guide or evidence of a usable
hotend-exchange system.

## Attribution

See [license and source attribution](ATTRIBUTION.md) and [LICENSE](LICENSE).
The CxChanger/YUDX-derived custom structure retains GPL-3.0 attribution; the
GT2 profile and derived toothed belt liners retain separate **CC BY-SA 3.0**
notices. Vendor hardware and hotend references retain their respective rights.
