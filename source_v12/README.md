# v12 CAD-tool source -- WIP, not ready for printing

The substantial **vibe developed** work is AI-assisted under human direction,
not professional engineering or physical qualification. This is an incremental
engineering/audit toolkit, **not a one-command replay** of the user's native
history or a printer controller. See [snapshot limits](../PREVIEW.md) and
[licence/source attribution](../ATTRIBUTION.md). The [current F3D](../cad/SparkShift_AHG_min_v12.f3d)
is directly editable; these eleven adjacent modules are not an automatic
rebuild of it.

| Module | Scope / limitation |
|---|---|
| [sparkshift_case_v10.py](sparkshift_case_v10.py) | Shared backing/pin/clearance checks and native capture, including disposable exploded displays. Historical initialization needs private captured inputs. |
| [sparkshift_corruption_v11.py](sparkshift_corruption_v11.py) | Source-bound face-recovery and case/insert operations. Retains rejected studies as historical functions, not the current native model or commands to replay. |
| [sparkshift_surface_cleanup.py](sparkshift_surface_cleanup.py) | Analytic edits, protected-interface checks, contacts, and tool withdrawal; checks freeze native inputs and reject changes during an audit. |
| [sparkshift_cam_v8.py](sparkshift_cam_v8.py) | Supplied-horn/integral-journal and hardware primitives; predecessor lower-nut builders are not current heat-set construction. |
| [sparkshift_strength_v7.py](sparkshift_strength_v7.py) | Retained structural primitives, not strength certification. |
| [sparkshift_ahg_min.py](sparkshift_ahg_min.py) | Datums/transforms/sweep helpers and predecessor mutations, not authority to replay old builders. |
| [pancake_paths_study.py](pancake_paths_study.py) | Native solids, booleans, measurements, transforms, and body traversal. |
| [ahg_placement.py](ahg_placement.py) | Historical LDO drawing-envelope placement, not supplier-fit certification. |
| [sparkshift_v7_meshes.py](sparkshift_v7_meshes.py) | Raw mesh checks and rigid bed placement; supports `--revision v12` / `--baseline v11`. |
| [sparkshift_v12_images.py](sparkshift_v12_images.py) | Current eight-panel captions from matching native captures; imports the shared v10 panel helper, not a renderer from the F3D alone. |
| [sparkshift_v10_images.py](sparkshift_v10_images.py) | Shared Pillow panel utility; its old capture names are not current v12 media. |

The virtual centering prototype and old v11 gallery builder are not supplied.
A model title or source function does not establish that a study/mutation
was applied to the approved native assembly.

Native helpers require real `adsk.core` and `adsk.fusion`; mesh checks need
NumPy, and panel utilities need Pillow and the Windows Segoe UI font.
Native API lengths use centimeters; helper datums/STLs use millimeters,
with +Y toward the tool and +Z upward.

Private initial snapshots, recovered inputs, reports, raw assembly meshes,
captures, session history, and app authentication are intentionally absent.
Live body handles, document IDs, proof flags, and runtime `STATE` dictionaries
do not survive reopening. Functions requiring those inputs are **not
standalone commands** for the shipped assembly. Mesh/panel CLIs expect
matching tessellation metadata or native captures, not only F3D.

The publication baseline freezes the approved geometry and rejects later
changes. Preserve user refinements and intentional suppressed operations.
Do not automatically replay old builders, rejected toolhead/nut candidates,
paused centering/Hall/mating work, or write generated output over deliverables.
Treat a failed boolean/volume measurement as an error, not zero overlap.

The requested step moves four heads/necessary seats to the fifth's flush
plane. A bounded native upper-pocket alignment then resolves a 0.000595mm
bore-axis offset; no mesh healing, facet repair, or deletion is used.
Original P17 and all four M2.5x8 mounts remain. FRAME_2 uses
rear loading before plate closure; FRAME_3 uses a bare-plate front-loaded
P02 insert captured by blue P01. The spring insert has its own bare-front
bench order. These geometric assembly references do not qualify actual
insert/printer/iron fits, thread engagement, torque, or load.

Four path-wall plane edits are applied, but complete paired docking symmetry
and the 0.05mm grid remain unfinished. The Hall cross-web does not form an
installed/qualified sensor package cradle or retainer. Do not force gear
internals symmetric or round vendor dimensions/fit clearances.

Eight labelled **native renders/cutaways, not photographs**, match the final
source. Exploded display translations are illustrative, not a validated
installation sequence or assembly/removal-path proof; F3D/STEP remain
assembled. Lower cutaways include original green P17 and mounting
references; the insert-stack left view is a native purple/gold/blue section,
not an iron-envelope illustration. Raw captures and private receipts are
not supplied.

Preserve exact sealed `.py` bytes, including CRLF/mixed endings, through
`source_v12/*.py -text whitespace=cr-at-eol`; no semantic change or silent
normalization is permitted during migration.

No qualified current motion helper, printer/heater commands, calibrated
offsets, or support-free printing approval is supplied. P01 `Extrude2` and
P03 `Extrude14` remain warnings; `Extrude33`, `DeleteFace29`, `DeleteFace30`,
`Extrude46`, `Extrude47`, and `DeleteFace46` are intentionally suppressed.
Full gear phase, native ratio, shaft lengths, horn/thread fits, snap
force/retention, strength, supports, and hot-life remain unqualified.
