# v10 CAD-tool source -- WIP, not ready for printing

These nine adjacent modules support the [current native review](../cad/SparkShift_AHG_min_v10.f3d)
as an incremental engineering/audit toolkit. The substantial **vibe developed**
work is AI-assisted under human direction, not professional engineering or a
one-command replay of the user's Delete Face/Extrude history.
See [inspection limits](../PREVIEW.md) and [licences](../ATTRIBUTION.md).

| Module | Scope / dependency |
|---|---|
| [sparkshift_case_v10.py](sparkshift_case_v10.py) | Source-bound user-input capture, local backing/pressed-pin/clearance operations, and native captures including translation-only exploded displays. Original initialization expects a privately captured pre-update input that is intentionally absent here. |
| [sparkshift_surface_cleanup.py](sparkshift_surface_cleanup.py) | Surface-family scans, deliberate analytic edits, protected-region checks, and export/build-face helpers used by the current driver. |
| [sparkshift_cam_v8.py](sparkshift_cam_v8.py) | Supplied-horn/integral-journal cam and hardware primitives. Old v8 lower-nut builders are not the current backed lower heat-set joint. |
| [sparkshift_strength_v7.py](sparkshift_strength_v7.py) | Earlier structural primitives retained as dependencies; its filename is not a physical-strength certification. |
| [sparkshift_ahg_min.py](sparkshift_ahg_min.py) | Shared assembly datums, transforms, and sweep helpers plus predecessor mutations; do not replay old builders on the current assembly. |
| [pancake_paths_study.py](pancake_paths_study.py) | Native solids, booleans, measurements, transforms, and body traversal. |
| [ahg_placement.py](ahg_placement.py) | Historical LDO drawing-envelope placement helpers, not supplier fit certification. |
| [sparkshift_v7_meshes.py](sparkshift_v7_meshes.py) | Raw-mesh checks and rigid bed placement, with v10 revision support. |
| [sparkshift_v10_images.py](sparkshift_v10_images.py) | Labels/panels from matching native captures; it does not fabricate model geometry or render from the F3D on its own. |

Fusion-dependent modules need the real `adsk.core` and `adsk.fusion` APIs.
The mesh utility needs NumPy; the panel utility needs Pillow and currently uses
the Windows Segoe UI font. Native API lengths are centimeters; helper datums
and STL coordinates use millimeters, with +Y toward the tool and +Z upward.

For a deliberate new review, start from a separate owned copy of the current
F3D and initialize a fresh evaluated baseline. Live body handles, document IDs,
proof flags, and runtime `STATE` dictionaries do not survive reopening.
The private input snapshots and engineering receipts are not publication assets.
Functions requiring those historical inputs are not standalone commands for
the shipped model.

The mesh CLI expects locally generated raw tessellation and export metadata;
the panel CLI expects the matching native source captures. Neither regenerates
the publication set from the F3D alone. The seven published panels are documents,
not those complete input captures. Select an explicit private scratch output,
review individual operations, and do not rerun predecessor mutation functions
or generate output over the current deliverables.

Exploded captures use disposable native copies and illustrative display
translations, not a validated installation sequence. The published F3D and
STEP remain assembled.

Treat a failed boolean/measurement as an error, not zero overlap. Press
references must be explicitly named; captured user input does not authorize
inheriting accidental clashes.

No qualified current motion helper or printer commands are supplied. Existing
native ratio/shaft-length issues, P01 `Extrude2`, P03 `Extrude14`, actual
thread/horn/printed fits, snap retention, load, and hot-life limitations remain.
