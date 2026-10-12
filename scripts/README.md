# CAD-tool source -- WIP, not ready for printing

These human-directed, AI-assisted **vibe developed** tools accompany the
[current v9 native review assembly](../cad/SparkShift_AHG_min_v9.f3d), not a
professional engineering workflow, printer controller, or one-command rebuild.
See [inspection limits](../PREVIEW.md) and [licences](../ATTRIBUTION.md).

The seven modules are kept together because their imports/loaders reuse
adjacent geometry helpers:

| Module | Scope / dependency |
|---|---|
| [sparkshift_surface_cleanup.py](sparkshift_surface_cleanup.py) | Native surface-family scans, deliberate cleanup operations, arm insert pilots, and export/travel helpers. Uses the adjacent AHG, cam, structural, and primitive helpers. |
| [sparkshift_cam_v8.py](sparkshift_cam_v8.py) | Compact supplied-horn cam primitives and predecessor arm-joint operations. Its v8 lower-nut mutation is **not** the current v9 lower heat-set joint. |
| [sparkshift_strength_v7.py](sparkshift_strength_v7.py) | Analytic structural primitives and predecessor review operations; the filename is not a physical-strength certification. |
| [sparkshift_ahg_min.py](sparkshift_ahg_min.py) | Shared geometry/transform helpers and incremental predecessor mutations. Do not rerun its old builders as the current design. |
| [pancake_paths_study.py](pancake_paths_study.py) | Temporary native solids, transforms, body traversal, and intersections reused by the approved tools. |
| [ahg_placement.py](ahg_placement.py) | LDO drawing-envelope helpers; reference geometry, not supplier fit certification. |
| [sparkshift_v7_meshes.py](sparkshift_v7_meshes.py) | NumPy mesh inspection and rigid bed-orientation processing. Its CLI needs locally generated raw tessellation and export metadata that are **not included here**. |

The native modules need Autodesk Fusion's `adsk.core` and `adsk.fusion`.
Ordinary Python cannot execute those native operations. The mesh module needs
NumPy. Imports are otherwise standard-library or these adjacent files; no
private predecessor archives or session caches are supplied. Functions expecting
historical inputs are not standalone current-model commands.

For a deliberate new CAD review, start from a **separate working copy** of the
current F3D. The surface toolkit's `initialize(app, output=...)` captures a fresh
review baseline and writes local reports; it is an engineering API, not a
safe automatic replay command. Select an explicit private scratch output
directory and review each operation rather than invoking predecessor `build`,
`apply_*`, or v7/v8 mutation functions against the current model.

The scripts retain predecessor guards, state, names, and default output folders.
The mesh CLI expects `<revision>_mesh_export.json` and
`stl_<revision>_assembly` from a deliberate native export. It cannot regenerate
the published mesh set from the shipped F3D alone. Reports, raw comparison
inputs, generated media, private input archives, and session material are not
part of this tree.

No qualified current motion helper is provided. The inherited native drive-link
ratio remains unresolved for the factory-10T input. These tools and digital
receipts do not establish loaded mechanics, continuous/full gear-phase
coverage, safe printer operation, material strength, or hot-life.
