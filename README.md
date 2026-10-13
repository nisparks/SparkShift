# SparkShift

> [!WARNING]
> **WORK IN PROGRESS / NOT READY FOR PRINTING OR USE**
>
> Files are for **inspection, design review, and development only**.
> Native renders, bed-oriented STLs, and digital checks do not qualify
> physical assembly, loaded actuation, retention, thermal life, or safe
> printer operation. This is not a print-ready or support-free release;
> do not install or operate it heated/unattended on that basis.

**HGX quick-change hotend system**

*Same drive. New hotend.*

SparkShift is a provisional name for an original-inspired, YUDX-derived
community design. The factory-10T LDO-36STH20-1004AHG(XH) pancake motor and
unmodified purchased HGX stay on the carriage; an independent MG90S cam
releases the swinging driven hob. Forward/reverse extrusion must remain
independent of arm opening.

**Vibe developed:** substantial iterative mechanical CAD and tooling are
AI-assisted under human direction, not professionally engineered or physically
validated. This describes SparkShift's process, **not the authorship of
upstream CxChanger/YUDX work or purchased parts**. Their credit and rights
remain in [ATTRIBUTION.md](ATTRIBUTION.md).

## Current v12 inspection files

**WIP / NOT READY FOR PRINTING:** one matched set for review only.

| File / guide | Inspection purpose |
|---|---|
| [v12 F3D](cad/SparkShift_AHG_min_v12.f3d) | Preserved user-edited assembly: 143 modeled bodies, 11 inherited joints, 17 print shapes. |
| [v12 assembled STEP](cad/SparkShift_AHG_min_v12.step) | Matching geometry exchange, not native history or qualified motion. |
| [17 v12 STLs](stl_v12) | Millimeter, bed-oriented review exports; **not print-ready or support-free**. |
| [Visual notes and digital limits](PREVIEW.md) | Eight labelled native panels, current changes, and bounded evidence. |
| [Modeled hardware / print roles](BOM.md) | Partial references, not purchasing or fabrication approval. |
| [Current source-tool guide](source_v12/README.md) | Eleven adjacent engineering tools, not one-command replay or printer control. |

## Exploded native view

![WIP v12 native exploded front and rear renders, illustrative display placement only](images_v12/v12_exploded.png)

**Native renders, not photographs.** Exploded display translations are
illustrative, not a validated installation sequence or assembly/removal-path
proof. Authoritative F3D/STEP remain assembled, not exploded exports.

## Approved v12 snapshot

The latest user face/fillet/chamfer/extrude edits are retained. The requested
head-alignment step moves only four selected case heads and necessary seats,
preserving the fifth and all other geometry. All five heads share the
**Y33.15 flush plane / Y31.5 seats**. The four targeted heads move +1.70mm,
with standard screw lengths and blind-tip clearances arranged to retain
full 4mm nominal engagement in their target inserts.

Modeled case hardware is **three M3x25 and one M3x40**, plus the separate
upper **M3x35** frame screw. These are partial CAD references, not purchasing,
torque, or fabrication approval. Lower-right FRAME_2 uses a rear-loaded P01
heat-set; lower-left FRAME_3 uses a front-loaded P02 insert captured by the
blue P01 annulus. No captive nut substitutes for either heat-set.

**P17 and all four original M2.5x8 hotend mounts remain unaltered**. There
is no lowered shelf/counterbore design or shorter hotend-screw substitution.
Required tool-withdrawal and tool-top/cam passages remain functional
clearance, not an obsolete full screwdriver tunnel.

A microscopic native alignment of the upper head pocket then corrected a
0.000595mm legacy bore-axis offset, removing a tessellation defect without
mesh repair. All five flush head planes and the insert engagements remain.
See the [bounded native/export correction](PREVIEW.md).

Read [snapshot and assembly-order notes](PREVIEW.md),
[partial hardware / print roles](BOM.md), and
[source-tool limitations](source_v12/README.md). Fresh native/STEP readbacks
match the source, and all 17 raw/bed meshes pass their digital gates.
Nine case/arm/cam samples and ten whole-tool positions through 35mm have
no unexpected overlaps or errors. These are bounded digital findings,
not continuous gear-phase or physical qualification.

![WIP v12 closed and open native assembly renders with five flush heads and original toolhead](images_v12/v12_overview.png)

Colours identify parts, not required filament or material choices.

## Explicitly unfinished

Four central path-wall analytic-plane edits and later user refinements are
applied. **Exact paired docking symmetry and the 0.05mm placement grid remain
unfinished**; not all contacts, pockets, or magnets are verified centered.
Gear internals need not be symmetric, and vendor dimensions/fit clearances
must not be rounded to that grid.

The case has a Hall cross-web, but the sensor retains its old slot/lead
geometry. **No positive Hall package cradle or retainer is installed or
qualified**. A model title mentioning centering or Hall support does not
establish those stopped studies as completed features.

P01 `Extrude2` and P03 `Extrude14` remain active inherited warnings.
`Extrude33`, `DeleteFace29`, `DeleteFace30`, `Extrude46`, `Extrude47`, and
`DeleteFace46` are intentionally suppressed, not healthy-feature claims.
Full gear phase, predecessor native ratio, compound-shaft lengths, actual
insert/iron/horn/thread fits, snap force/retention, strength/torsional
stiffness, servo/spring margin, supports, and hot-life remain unqualified.
The cam's **M2x16 REFERENCE / VERIFY ACTUAL SERVO THREAD** is not buying
approval; preassemble its retainer before case closure.

## Licences and sources

The unchanged [LICENSE](LICENSE) retains GPL-3.0 for CxChanger/YUDX-derived
custom work. P13/P14 GT2 liners retain **CC BY-SA 3.0** credit. Vendor hardware
and hotend references retain their respective rights, not blanket relicensing
or manufacturer certification. See [mixed-scope attribution](ATTRIBUTION.md).
