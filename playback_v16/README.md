# v16 portable cam playback -- WIP, FIT PENDING, not ready for printing

This substantial, human-directed, AI-assisted **vibe developed** preview is
**checked contact-curve forward kinematics**, not spring-force, friction,
servo-current, simultaneous feed/release, or real-time physical simulation.
It is not printer/servo control or physical validation. See
[motion and fit limits](../PREVIEW.md).

## Folder contract

Open a separate copy of the [matching v16 F3D](../cad/SparkShift_AHG_min_v16.f3d)
and keep these three files together inside `SparkShiftCamPlayback`:

| File | Purpose |
|---|---|
| [SparkShiftCamPlayback.py](SparkShiftCamPlayback/SparkShiftCamPlayback.py) | Fusion script: cam-angle slider and one open/close cycle. |
| [SparkShiftCamPlayback.manifest](SparkShiftCamPlayback/SparkShiftCamPlayback.manifest) | Fusion script metadata. |
| [cam_motion.json](SparkShiftCamPlayback/cam_motion.json) | Matching checked cam/arm samples and fixed-transform guards. |

The data's SHA-256 is
`100dec3a81d56758229df0dd7274404e17a02910074c0f00b49994dda9033c38`.
It contains 701 ordered samples from cam 0 to 175 degrees. The helper checks
the model's `SparkShiftMotion` data-hash attribute and held input transforms;
do not edit or mix the files to bypass a mismatch.
The sampled guide has a recorded 0.008mm reference clearance margin and
bounded arm-angle approximation; it is not an exact force/contact solver.
Tiny numerical variation in the sampled dwell is distinct from the physical
cam's nominal concentric dwell.

The portable helper imports only Python standard-library modules and
Fusion's `adsk.core`/`adsk.fusion`. It needs **no authoring tools or private
inputs**, NumPy/SciPy, Shapely, OCP, Pillow, or external service. It runs
**inside Fusion**, not as an ordinary command-line Python program.
The helper uses **UUID-suffixed command IDs for each launched instance**.
Repeated Run while its own healthy preview is already open is idempotent;
close a failed or previous preview before starting another. Retained inactive
definitions are logged rather than reused as conflicting command IDs.
Some inherited v15 data-validation wording refers to the shared contact
curve, not the archive version; the matching F3D/data bytes establish use.

## Use on a separate inspection copy

1. Save/open a separate local inspection copy of the matching published v16 F3D.
2. In Fusion's **Scripts and Add-Ins** dialog, add/select the local `SparkShiftCamPlayback` script folder and run it.
3. Use **Cam angle (deg)** or **Play one open/close cycle**. The script drives cam and arm occurrence transforms together; **Drive Joint alone does not synchronize them**.
4. Choose **Done** when finished. Discard/reopen the inspection copy if the original display or pose is needed.

The script selects an inspection camera and hides some case/tool/coupling
geometry. Those display omissions are not new parts, an operating setup,
or physical absence of the enclosure. Playback changes CAD poses and display;
do not run it against an unrelated or concurrently edited document.
The helper reports and stops on validation/drive errors; do not bypass them.
No native playback or CAD-mutating script was executed to prepare this guide.

## Motion and physical limits

Cam commands are **0..175 degrees**. Nominal **2.50mm opening occurs at 170
degrees**, followed by **170..175 concentric open dwell**. A nominal 5-degree
upper margin assumes a stated 180-degree servo stroke; actual endpoints,
clocking, and hardware control limits still require calibration.

Native automatic tangency selected penetrating take-up poses and was removed.
No extra non-printing drive bodies are required or installed; one servo and
one printed cam/hub remain. Dwell removes ideal normal-force backdrive
torque, not spring/bearing loads or friction, and is **not a positive
power-off latch**. Unknown spring/preload/servo margins and real hardware
can invalidate a seemingly clean CAD cycle.

The 21T direct fit and M2.5 retaining screw are variant-specific fit-pending
references. Check actual spline, clocking, usable blind thread depth,
printed strength, and assembly before applying load or power. The preview
does not qualify hotend exchange, thermal use, supports, or endurance.
See [generic BOM](../BOM.md) and [licence/source attribution](../ATTRIBUTION.md).
