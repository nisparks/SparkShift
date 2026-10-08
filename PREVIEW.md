# Private preview notes

This is a **latest-only private collaborator handoff**, not a production or
qualified print release. The [Fusion native assembly](cad/SparkShift.f3d) is the
editable model; the [assembly STEP](cad/SparkShift.step) is a geometry exchange
reference, not a standalone parametric build environment.

Open the current F3D in Fusion. It is saved visibly assembled with restored
colors and the motor, cam, and tool travel parked at zero. Use this model with
its matching script and exports, not an earlier native file.

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

## Selected servo and drive-interface limits

**MG90S is the selected baseline**, not just an inventory candidate. Reuse one
matching owned servo; order none if that stock matches. The
[BOM's manufacturer references and sourcing notes](BOM.md#mg90s-selection-and-reuse)
separate published body dimensions from unverified mounting/spline details.
Neither the manufacturer's stall torque nor an earlier superseded load estimate
establishes current cam torque headroom.

The mounting prototype uses the 22.8x12.2x28.5mm body envelope and adjustable
P02 slots/captive-nut channels. **27.8mm is the nominal mounting pitch, not an
official factory dimension**. +/-0.4mm per-ear travel gives a
27.0..28.6mm geometric pitch extent; that is **not universal case/ear/washer fit
qualification**. The modeled stack uses 2mm ears, two 0.3mm flat M2 washers,
two M2x6 socket-head screws replacing the former M2x5 screws, and two retained
M2 hex nuts. Nominal support/front nut-loading checks pass in CAD; actual owned
hardware still needs fitting. The [BOM](BOM.md) specifies the head and washer
dimensions.

The supplied MG90S-matched horn remains a **fit-check envelope**: its tooth
count and retaining thread are not independently verified. The prototype keeps
the existing cam profile, output axis, and HGX kinematics; it is not a completed
all-metal redesign. A generic H25T horn does not automatically fit an MG90S.
No MG90-specific off-the-shelf metal horn/shaft connection has been fully
verified yet, but that does not prevent the mounting prototype from proceeding.

The working printed cam/horn is retained as the user's observed-strong
prototype. Its long-term durability remains unproven; no immediate-failure
claim is made. The separate 3x12mm cam journal pin does not bridge the printed
neck's torque path.

TF-9512MG in its 180-degree version is an available backup, **not selected**.
An intermediate class such as MG92B is only a future mounting-swap option if
requested; neither is a substitute with demonstrated torque headroom here.

## Intentional features and current clearances

| Feature | Purpose / limit |
|---|---|
| Four front blind pilots | Optional future CPAP-adapter mounts, not missing frame screws. No CPAP adapter is supplied. |
| Two lower P01 blind pilots | Future Cartographer/Beacon adapter mounts. No adapter, probe-specific pattern, or sensing qualification is supplied. |
| Upper round P12 part | The functional spring pressure cup. It is retained unchanged, not obsolete geometry. |
| Shallow P01 shoulder recess | One continuous shallow recess replaces the stepped imprint while protecting the real frame bosses. |

Retired motor shaft/pinion bores in P01/P03, the former motor-relative P04
relief, and P01's obsolete fixed-hob rear-bearing cavity are removed; the
current fixed-hob bearing seats are in P03. Obsolete cartridge/frame cutouts
and the duplicate Hall slot are also removed. Motor/shaft/hob dimensions,
gear ratios, and cam/output-axis location are retained. The selected servo's
case/mounting update and screw/washer delta are described above, separately
from that earlier geometry cleanup.

The bottom hotend-to-P01 gap is increased to a **1.0mm native measured
heater-to-P01 minimum**. This is geometric clearance, **not thermal-spacing or
hot-life qualification**. All six accessory pilots are optional provisions;
their optional inserts are separate from the required frame hardware in the
[BOM](BOM.md).

## Coordinated native motion

The MG90S native model contains 138 modeled parts / 16 prints in 13 functional
groups, with 12 real joints and four native gear links. The
[standalone motion helper](scripts/SparkShift_motion/SparkShift_motion.py)
coordinates nonlinear cam/follower motion and the orbiting hob, and updates
the deforming spring/filament display references rather than hiding them.
**Driving `J_CAM` alone does not coordinate the follower/carrier.**

In Fusion, open **Utilities > Scripts and Add-Ins > Scripts**, add/select the
folder `scripts\SparkShift_motion`, and run `SparkShift_motion.py` with the
current `SparkShift.f3d` active. Run it again for each action and type the action
at its prompt:

| Action | CAD demonstration |
|---|---|
| Feed | Enter an absolute motor angle from -3600 to +3600 degrees, not an increment. Forward/reverse feed leaves the parked cam and closed arm unchanged. |
| Open | Coordinate cam, follower, carrier, and orbiting hob while holding the extrusion motor. |
| Remove tool | Withdraw the tool 35mm with the cam/carrier fully open. |
| Insert tool | Return the tool to its seated position while open. |
| Close | Close after the tool is fully inserted and the manual lever is released. |

For tool travel, use **Open -> Remove tool -> Insert tool -> Close**.
Feed requires the seated/latched tool, parked cam, and released manual lever.
The helper enforces those CAD state guards; do not bypass them with arbitrary
joint edits. It sends **no printer commands**. These guards are not physical
sensors, a physical latch, or assembly/thermal qualification.

## Review and fit limits

Preassemble the motor on the separate spacer with its four M3x6 countersunk
screws before mating the backplate. Fit the captive servo nuts while their
guides are still accessible. Match the distinct screw heads and insert lengths
in the [current BOM](BOM.md); measure actual servo/horn, spring, and small
tool-interface insert fits rather than treating supplier envelopes as orders.

The printed shells are 45.0mm wide; the carriage is nominally 45.4mm and the
stock-inclusive CAD width measures 45.44mm. The stock-envelope issue remains
unwaived. Geometry clearance does not establish thermal spacing, material
strength, bearing retention, or deposited-layer quality.

Continuous assembly/service, feed/reverse operation, manual release, complete
tool withdrawal, and hot-life qualification remain physical-development gates.
No heated-operation approval, G-code, machine profile, or printer-control
configuration is included.

Actual CPAP and probe-adapter development remains deferred apart from the six
prepared mounting pilots. Inherited sensor/presence references are not
functional sensing qualification. Full multi-tool dock integration is outside
this preview.

Preserve the [mixed-scope attribution](ATTRIBUTION.md). Third-party reference
geometry is not covered by a blanket new redistribution grant.
