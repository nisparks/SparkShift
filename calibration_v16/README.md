# Optional 21T fit gauges -- WIP, FIT PENDING, not ready for printing or use

> [!WARNING]
> [Servo_21T_fit_gauges.stl](Servo_21T_fit_gauges.stl) is **optional calibration,
> not an 18th assembly part**, a final cam, or a load/torque/retention
> qualification. It remains a fit trial, not printing or use approval.

These small trials are part of the substantial, human-directed, AI-assisted
**vibe developed** prototype workflow, not manufacturer-approved metrology.
Use them to investigate the required interface before committing to a full
cam print; no gauge outcome makes the mechanism print-ready or safe to use.

## Reference sample and limits

The reference servo output was counted/measured as **21T, 4.86mm crest OD,
3.36mm exposed height, and an M2.5 center thread**. The **4.62mm root diameter
and sinusoidal flank form are photo-estimated approximations**, not a
certified tooth standard. Other MG90S clones may have different splines,
threads, boss datums, or usable blind depths and are **not universally
compatible** with these trials or the full direct-output cam.

Confirm the actual required interface independently. A matching CAD male
reference and CAD socket do not prove fit on a real servo shaft. External
spline height does not establish blind thread depth.

## Five collars in one STL

The existing STL contains **five separate 10mm-OD x 3mm-high collars**,
identified by one through five outside notches. Its 19,336 triangles form
five closed positive-volume components; no zero stored normals are
reported. Those digital checks are not printer resolution, actual fit,
loaded strength, or support-strategy qualification.

| Outside notch count | Trial bore | Meaning |
|---|---|---|
| 1 | Approximate 21T, +0.000mm normal offset | Baseline photo-approximate profile, not certified teeth. |
| 2 | Approximate 21T, +0.025mm normal offset | Current starting allowance reference, not a universal fit recommendation. |
| 3 | Approximate 21T, +0.050mm normal offset | Additional fit trial, not a new final cam design. |
| 4 | Approximate 21T, +0.075mm normal offset | Additional fit trial, not torque/retention approval. |
| 5 | Round 4.96mm control | Round comparison only; **not a toothed drive interface**. |

The 21T count in collars 1..4 comes from the inspected sample. Root/flank
geometry remains approximate at every allowance. The collar depth differs
from the full hub/entry geometry, so a collar fit alone cannot qualify
full-depth engagement or final assembly.

## Gentle unpowered fit check only

1. Inspect the STL in a slicer. Use the intended full-cam material, nozzle,
   orientation, and process conditions; a **0.2mm nozzle is favored** for
   resolving the fine profile, but is not a guarantee of adequate detail.
2. Keep the notch identities intact and inspect the printed bores for
   burrs, support residue, and malformed teeth before approaching the shaft.
3. With the servo **unpowered**, try the collar by **fingertip pressure only**.
   If it does not enter gently, stop; do not force, hammer, heat, or power it.
4. **Do not use a bolt to pull a gauge onto the spline.** These collars have
   **no retaining-head seat** and are not intended for screw clamping,
   torque transmission, powered cycling, or load testing.

Do not ream, melt, or force a collar to turn a failed trial into apparent
compatibility. No press force, interference, pullout, or torque rating is
established by these trials. Record the actual sample, measured dimensions,
material/process, and observed fit rather than treating a notch number as
a supplier specification.

Before any eventual full-cam assembly, separately verify shaft clocking,
safe endpoints, final hub/lead engagement, printed journal strength, actual
thread/pitch, and **usable blind depth >=3.16mm** for the M2.5x16 reference
stack. A collar has no such retention/depth check and must not be used as
one. See [direct-mount limits](../PREVIEW.md), [generic per-build BOM](../BOM.md),
and [source/licence attribution](../ATTRIBUTION.md).
