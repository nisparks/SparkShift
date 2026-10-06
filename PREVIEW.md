# Private preview notes

This is a **latest-only private collaborator handoff**, not a production or
qualified print release. The [Fusion native assembly](cad/SparkShift.f3d) is the
editable model; the [assembly STEP](cad/SparkShift.step) is a geometry exchange
reference, not a standalone parametric build environment.

The [16 current STLs](stl) are in millimeters, already bed-oriented and
translated to the bed origin individually. They are **not assembly-coordinate
meshes**; use native/STEP CAD for assembled placement. Keep the supplied
orientations, do not mirror or globally scale, and inspect supports and actual
fits with your calibrated material/profile. Bed placement is not support-free
or deposited-material qualification.

One permanent NEMA14/HGX drive remains on the carriage. One driven hob is fixed
and one swings with the arm. The independent servo cam and manual release are
separate from ordinary forward/reverse extrusion.

The stock steel hobs and original needles are unchanged. The current stack
uses direct drivers and ordinary 3x14mm hob pins. The aligned same-plane
37T hob-drive mesh remains a user-selected experiment, not a qualified mesh.

## Review and fit limits

Preassemble the motor on the separate spacer with its four M3x6 countersunk
screws before mating the backplate. Fit the captive servo nuts while their
guides are still accessible. Match the distinct screw heads and insert lengths
in the [current BOM](BOM.md); measure actual servo/horn, spring, and small
tool-interface insert fits rather than treating supplier envelopes as orders.

The shell is 45mm wide while the stock MGN12H is 45.4mm wide; the stock-envelope
issue remains unwaived. Geometry clearance does not establish thermal spacing,
material strength, bearing retention, or deposited-layer quality.

Continuous assembly/service, feed/reverse operation, manual release, complete
tool withdrawal, and hot-life qualification remain physical-development gates.
No heated-operation approval, G-code, machine profile, or printer-control
configuration is included.

CPAP and sensor development remain deferred apart from the six prepared
mounting pilots. Inherited sensor/presence references are not functional sensing
qualification. Full multi-tool dock integration is outside this preview.

Preserve the [mixed-scope attribution](ATTRIBUTION.md). Third-party reference
geometry is not covered by a blanket new redistribution grant.
