# v16 authoring toolkit -- WIP, FIT PENDING, not ready for printing

This substantial **vibe developed** work is AI-assisted under human direction,
not professional engineering or physical qualification. The authoring code
is an **incremental, live-state toolkit, not a one-command rebuild** from a
clean checkout. The native F3D is the directly editable source.

## Fifteen adjacent modules, not automatic build order

| Authoring module | Role / limitation |
|---|---|
| [sparkshift_direct_mount_v16.py](sparkshift_direct_mount_v16.py) | Direct spline/cam, retainer, washer, and blind-pocket operations; expects initialized prior cam/controller state. Historical body names are not purchasing specifications. |
| [sparkshift_servo_fit_gauges_v16.py](sparkshift_servo_fit_gauges_v16.py) | Empirical fit-trial geometry, not universal MG90S teeth or fit qualification. |
| [sparkshift_cam_v15.py](sparkshift_cam_v15.py) | Physical cam and contact-curve playback preparation, plus superseded tangent/reference experiments; do not replay the latter. |
| [sparkshift_cam_profile_v15.py](sparkshift_cam_profile_v15.py) | Smooth progressive roller-cam profile, not spring/torque physics. |
| [sparkshift_opening_v14.py](sparkshift_opening_v14.py) | Native opening, source-preservation, boolean, and measurement helpers requiring prior inputs/state. |
| [sparkshift_motion_guide_profile.py](sparkshift_motion_guide_profile.py) | Numerical curve/reference tooling; historical guide output is not installed hardware. |
| [sparkshift_swingarm_motion_v13.py](sparkshift_swingarm_motion_v13.py) | Historical preview/rigidity and snapshot guards; rejected extra drivers are not the model. |
| [pancake_paths_study.py](pancake_paths_study.py) | Native solids, booleans, transforms, and traversal. |
| [ahg_placement.py](ahg_placement.py) | Historical motor-envelope/datums, not supplier fit certification. |
| [sparkshift_ahg_min.py](sparkshift_ahg_min.py) | Shared datums/transforms and predecessor mutation helpers, not an automatic rebuild. |
| [sparkshift_cam_v8.py](sparkshift_cam_v8.py) | Shared cam/hardware primitives; predecessor horn/nut builders are not the direct mount. |
| [sparkshift_strength_v7.py](sparkshift_strength_v7.py) | Retained structural primitives, not strength certification. |
| [sparkshift_surface_cleanup.py](sparkshift_surface_cleanup.py) | Analytic edits, protected-interface checks, contacts, and withdrawal helpers. |
| [sparkshift_case_v10.py](sparkshift_case_v10.py) | Shared case/pin/backing/capture helpers, not authority to restore old geometry. |
| [sparkshift_corruption_v11.py](sparkshift_corruption_v11.py) | Historical case-recovery and live-state measurement support; contains rejected candidates, not a replay recipe. |

Static adjacent-module closure does not make missing historical inputs,
saved native handles, or earlier private measurement helpers appear.
Some authoring paths still expect unpublished exact-measurement routines,
frozen input archives, receipt data, and initialized `STATE`/controller
objects. Those inputs, rejected studies, and private source history are
intentionally absent. Functions requiring them are **not standalone
commands** for the shipped F3D. No legacy `CAD.*` package replay or automatic
private-workbench import is claimed.

## Dependencies and safe scope

Fusion-dependent tools require real `adsk.core`/`adsk.fusion`.
Numerical/profile tools use **NumPy, SciPy, and Shapely**; the empirical
gauge generator also requires **OpenCascade Python bindings (`OCP`)**.
Image utilities use **Pillow** and Windows **Segoe UI** font paths.
These are authoring prerequisites, not requirements for portable playback;
versions and deterministic rebuilding are not qualified by this bundle.
Native API lengths are centimeters; helper datums/meshes use millimeters.

Do not execute builders simply to open or inspect the model. Any later
engineering needs a separately owned model, deliberate state/input setup,
fresh geometry comparison, and explicit output paths outside deliverables.
Do not change old rejected candidates, force gears symmetric, round vendor
fits, or regenerate final assets over the sealed set. Failed booleans or
measurements are errors, not zero overlap.

Native meshes are **best-effort inspection exports**. Microscopic,
nondegenerate facets can retain zero stored STL normal vectors; a topology/
winding pass is not an all-clean normal-metadata claim. Preserve native
bytes with **no facet deletion or normal rewriting**, report those warnings
per file, and reject geometry/topology, degenerate-facet, inverted-normal,
or non-microscopic normal failures. Inspect outputs and warnings in a slicer;
do not describe slicer handling as print, fit, or load qualification.

Source curation preserves **exact sealed bytes**, including CRLF/mixed
endings, with narrow `source_v16/*.py -text whitespace=cr-at-eol` attributes.
No semantic/source-path edits are implied by migration. An inherited v15
identifier or function does not relabel old media or prove it belongs to
the current matched native model.

## Standalone playback is a different surface

See [portable playback](../playback_v16/README.md). Its three-file script
folder and matching F3D/data do **not** require the authoring toolkit,
private historical inputs, NumPy, SciPy, Shapely, OCP, or Pillow.
The runtime needs Fusion's real API; it is CAD kinematics, not an external
Python viewer, hardware controller, or force/real-time physical simulation.

No extra non-printing drive bodies or active tangent-follow substitute
are installed. Direct Drive Joint alone does not synchronize cam and arm.
The checked contact curve and explicit forward kinematics are the intended
preview, not proof of force, friction, spring preload, torque, or endurance.

## Rights and limitations

The direct tooth fit, blind depth, clocking, printed hub/journal strength,
insert fits, snap retention, full gear phase, predecessor native ratio,
shaft lengths, supports, hot-life, and Hall package cradle remain unqualified.
Paired Maxwell/magnet symmetry and the 0.05mm placement grid are unfinished.
P01 `Extrude2`/P03 `Extrude14` and six intentional history suppressions
must not be described as an all-healthy feature tree.

See [inspection notes](../PREVIEW.md), [generic per-build BOM](../BOM.md),
and [mixed-scope attribution](../ATTRIBUTION.md). Vibe-development credit
does not replace upstream authorship, separate CC BY-SA liner notices,
or vendor-reference rights.
