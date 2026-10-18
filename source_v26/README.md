# v26 incremental authoring snapshot -- WIP, FIT PENDING, not ready for printing

This substantial, human-directed, AI-assisted **vibe developed** toolkit is
**not a clean-checkout, one-command rebuild**. The [v26 native F3D](../cad/SparkShift_AHG_min_v26.f3d)
is the directly editable source. These **13 exact sealed Python modules**
record incremental engineering work; filenames are not automatic build order.

| Module | Scope / limitation |
|---|---|
| [sparkshift_agreement_v26.py](sparkshift_agreement_v26.py) | Analytic case/arm agreement, bounded edits, capture, audits and export helpers; depends on prior initialized state. |
| [sparkshift_cleanup_v25.py](sparkshift_cleanup_v25.py) | Crown/slot/teardrop cleanup helpers, not a recipe to overwrite later manual edits. |
| [sparkshift_coupling_v24.py](sparkshift_coupling_v24.py) | YUDX-matched conformal Maxwell pin-seat construction and checks; not physical snap-force qualification. |
| [sparkshift_servo_plate_v23.py](sparkshift_servo_plate_v23.py) | MG90S/MG90D reference ear seats and self-tapper studies; later v26 manual window geometry is authoritative. |
| [sparkshift_blue_half_v22.py](sparkshift_blue_half_v22.py) | P01/arm candidate, motion and comparison helpers. |
| [sparkshift_front_half_only_v21.py](sparkshift_front_half_only_v21.py) | P03-only support/clearance and preservation tooling. |
| [sparkshift_shape_refinement_v20.py](sparkshift_shape_refinement_v20.py) | Historical shape/clamp candidates; rejected top-down clamps are not extra installed hardware. |
| [sparkshift_open_frame_v19.py](sparkshift_open_frame_v19.py) | Open-frame/7mm plate construction, live-state guards and export/readback helpers. |
| [sparkshift_slim_v18.py](sparkshift_slim_v18.py) | Historical slim-case, cam-clocking and hardware changes; source-input assumptions are not the current inventory. |
| [sparkshift_direct_mount_v16.py](sparkshift_direct_mount_v16.py) | Earlier direct 21T cam/hub/retainer operations, requiring earlier cam/controller context. |
| [sparkshift_surface_cleanup.py](sparkshift_surface_cleanup.py) | Shared analytic edits and export helpers; depends on unpublished predecessor helpers. |
| [sparkshift_render_v26.py](sparkshift_render_v26.py) | Offline VTK renderer, requires explicit scene/job inputs; not native CAD reconstruction or a physical photograph. |
| [sparkshift_validate_release_v16.py](sparkshift_validate_release_v16.py) | Historical NumPy/SciPy mesh-check utility. Its v16 naming/input paths are preserved; not a self-contained v26 build/validation command. |

## Deliberately incomplete execution context

The snapshot depends on previously initialized **`STATE` dictionaries,
`sys.modules` entries, native handles, controller objects and measurement
helpers**, plus frozen source archives, servo STEP inputs, scene/job data
and earlier comparison receipts that are **not included**.
Direct/dynamic predecessors such as `sparkshift_cam_v15.py`,
`sparkshift_opening_v14.py`, `sparkshift_ahg_min`, `pancake_paths_study`,
and the v17 playback context are absent. Static AST parsing does not
make those dependencies available or establish runnable source closure.

Private measurement inputs/history and intermediate/rejected studies
are intentionally not copied to fill the gaps. Do not fetch or reconstruct
them from private workbench history, bypass identity/hash checks, or invoke
builders simply to open this model. Later native user edits also are not
reconstructed merely by running the earlier functions in version order.
Historical document IDs and source hashes in the tools are preservation
guards, not identifiers for a user's newly opened inspection copy.

## Dependencies and safe scope

Native tools use Fusion's real **`adsk.core` / `adsk.fusion`** API; ordinary
CLI Python cannot execute them. The offline renderer needs **NumPy and VTK**.
The historical mesh checker uses **NumPy and SciPy** and expects external
receipts/data. Other absent predecessors can have further dependencies.
No packages are installed or CAD builders executed for this publication;
no complete or deterministic environment/rebuild is claimed.

Source bytes, including CRLF/mixed endings, are preserved with
`source_v26/*.py -text whitespace=cr-at-eol`. No semantic refactor, helper
substitution, or source-path rewriting accompanies migration. The approved
CAD/mesh/image bytes, not the result of an unreviewed replay, define v26.

The public package contains **no matched v26 standalone portable playback,
GIF, or fit-gauge STL**. Older playback/data are not silently reused with
the changed model. Native Drive Joint alone does not establish synchronized
cam/arm motion, spring forces, friction or real-time physics.

Mesh checks and native readback are digital inspection, not support,
spline, screw-depth, strength, thermal or endurance qualification. Keep
the [known servo-window exception and other gates](../PREVIEW.md),
[generic build inventory](../BOM.md), and
[next-session accessories plan](../ACCESSORIES_PLAN.md) explicit.

## Rights

See [mixed-scope attribution](../ATTRIBUTION.md). Published custom tooling
retains GPL-3.0 scope; P13/P14 GT2-derived liners retain CC BY-SA 3.0,
and purchased hardware/hotend references retain their respective rights.
Vibe-development disclosure does not replace upstream credit or certify
manufacturer dimensions, fitness, or redistribution permissions.
