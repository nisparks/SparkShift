# SparkShift

> [!WARNING]
> **WORK IN PROGRESS / NOT READY FOR PRINTING OR USE**
>
> All files are for **inspection, design review, and development only**.
> Bed-oriented STLs, native renders, and successful digital checks are not a
> print-ready release or proof of a tested hotend-exchange mechanism.
>
> Complete physical assembly, loaded actuation, snap retention, reliability,
> thermal, and safety testing have not qualified this design. Do not treat it
> as ready to install in a printer or operate heated/unattended.

**HGX quick-change hotend system**

*Same drive. New hotend.*

SparkShift is a provisional name for an original-inspired, YUDX-derived
community design. The factory-10T LDO-36STH20-1004AHG(XH) pancake motor and
unmodified purchased HGX drive stay on the carriage; an independent MG90S cam
releases the swinging driven hob. Forward/reverse extrusion must remain
independent of arm opening.

**Vibe developed:** substantial iterative mechanical CAD and tooling were
AI-assisted under human direction, not professionally engineered or physically
validated. This describes SparkShift's development process, **not the authorship
of upstream CxChanger/YUDX work or purchased parts**. Their credit and rights
remain in [ATTRIBUTION.md](ATTRIBUTION.md).

## Current v10 inspection files

**WIP / NOT READY FOR PRINTING:** use this one matched set for review only.

| File / guide | Inspection purpose |
|---|---|
| [v10 F3D](cad/SparkShift_AHG_min_v10.f3d) | User-edited native assembly: 143 modeled bodies, 11 inherited joints, and 17 print shapes. |
| [v10 assembly STEP](cad/SparkShift_AHG_min_v10.step) | Matched geometry exchange; not native feature history or qualified motion. |
| [17 v10 STLs](stl_v10) | Millimeter, bed-oriented review exports; **not ready for printing or support-free**. |
| [Visual notes and limitations](PREVIEW.md) | WIP native renders/cutaways, current changes, and bounded digital checks. |
| [Modeled hardware / print roles](BOM.md) | Partial, unqualified references; not shopping or fabrication approval. |
| [Current CAD-tool source notes](source_v10/README.md) | Nine adjacent engineering tools, not a one-command replay or printer controller. |

## Exploded native view

![WIP v10 illustrative exploded native CAD renders from the front and rear, not photographs](images_v10/v10_exploded.png)

**Illustrative display translations only:** these native renders are not
physical photographs, a validated installation sequence, or installation-path
proof. The authoritative F3D and STEP above remain **assembled**, not exploded
models. The [seven-panel gallery](PREVIEW.md) also shows the current assembly,
case faces, and inspection cutaways.

## Latest case changes

The latest user cleanup and history are retained. A small P03 lower-corner
swept cut fixes a mid-stroke clash without moving the arm, hardware, or datums.
The six nominal 1.5x5mm coupling pins have two short integral C capture bands
each, while their steel contact tracks, seating rails/lips, and axial stops
remain. Printed press/snap insertion and resistance to popping out are **not
physically qualified**; no glue or separate keeper is specified.

All four magnet and four ball-socket backing footprints are complete in the
checked geometry. The exterior cam-driver tunnel is closed; a blind internal
head/washer cavity remains. **Preassemble the cam/horn retainer before closing
the case halves.** The M2x16 center screw is still a reference: verify the actual
servo thread, horn, and printed-journal fit.

![WIP v10 native closed/open render panel, not photographs or print qualification](images_v10/v10_overview.png)

**WIP native renders, not photos.** Detail panels and cutaway limitations are
in [PREVIEW.md](PREVIEW.md); colours identify parts, not required filament.

## Still unresolved

The two-piece P04R/P04F arm retains its upper M3x10 clamp, lower M3x14-to-backed
short-M3 heat-set, and central key. The supplied horn provides the real spline;
the short integral cam journal uses MF85ZZ. No printed female spline, loose
lower nut, or separate cam journal pin is supplied.

Sampled clearance and shape readbacks do not qualify physical fit/retention,
strength/torsional stiffness, spring/servo margin, hot creep/life, or continuous
full gear-phase motion. Small legacy gear gaps, the predecessor native
drive-link ratio, and nonstandard modeled compound-shaft lengths remain open.
P01 `Extrude2` and P03 `Extrude14` remain **inherited warnings**.

MG90S is selected with reuse of matching owned stock, not a torque-headroom
guarantee. Cooling, safe controls, CPAP, and sensor/probe accessories remain
unqualified or deferred. Geometry and hardware may change before a usable
assembly or print package exists.

## Licences and sources

The unchanged [LICENSE](LICENSE) retains GPL-3.0 for the CxChanger/YUDX-derived
custom work. P13/P14 GT2 tooth liners retain **CC BY-SA 3.0** credit.
Vendor hardware and hotend references are not blanket relicensed or
manufacturer-certified. See [mixed-scope attribution](ATTRIBUTION.md).
