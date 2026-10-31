# Swept-feed geometry cleanup and improvement review

**Review date:** 2026-10-30. **Scope:** the separate 28-degree, 3 mm raised-feed,
nominal 18 x 0.9 mm rear-slot variant, with cleaned direct mounts for Beacon and
Cartographer. Released R43, frozen candidate A and the previous C28 CFD geometry
remain unchanged. These are review parts, not print-qualified releases.

**Current user-directed hotend scope: Bambu Lab only.** Red Lizard clearances below
are historical comparison data, not selection criteria or a constraint on today's
optimization. Both probe mounting variants remain available. Printability and
positive duct retention are the current priorities.

**Latest share image, without branding:** [R43 vs cleaned C28 JPEG](images/r43_vs_latest_c28_share.jpg)
| [Full-size PNG](images/r43_vs_latest_c28.png).
Matched outlet views, 3D streamlines, near-bed and center-plane velocity maps, and
direct numerical comparison use the completed cleaned-geometry CFD.
The [earlier decision-summary image](images/sparkshift_c28_design_review_share.jpg)
is retained as a historical 32/28-degree comparison and explicitly labels its
pre-inlet-cleanup CFD.

## Mechanical review

**Separate matched P01/P21/P22 replacements, not a P22-only drop-in or a new
cooling winner.** The proposed angled tabs and underside-screwed tongue are now
modelled. Frozen cleaned C28 remains the airflow baseline; neither released R43
nor the user's existing Fusion documents are replaced.

**Live Fusion edits are preserved separately.** After this study was imported,
document **53 Bambu C28 - angled mounts and lower retainer** received additional
extrusions, sketches, a fillet and face deletions. Its edited state is **not
covered by the checks below**. It was left active and unchanged; a native snapshot
was saved as `53_C28_Live_Edits_Preserved.f3d` in the session artifacts. The checked
pre-edit STEP/STL files remain separate. Those edits must be reconciled before
adopting a new baseline; they were not overwritten or silently accepted.

**User P21 direction: adopted for development, not yet qualified.** The user then
confirmed the edited P21 (a sloped post retained by the underside M3 screw) as the
intended printable direction, with tweaks allowed. Its 25-feature native document
is archived in this repository as
[`53_C28_User_P21_Direction_FUSION_SNAPSHOT.f3d`](53_C28_User_P21_Direction_FUSION_SNAPSHOT.f3d)
(P21 12,160.35 mm3; the open document was unchanged when archived). A matched P22
receiver is being qualified with `r43_c28_user_joint.py` and
`audit_c28_user_retainer_r43.py`. The forked-tongue tables below do not describe it.

![Angled mounts, forked tongue and underside screw](images/r43_c28_mechanical_review_share.jpg)

[Share JPEG](images/r43_c28_mechanical_review_share.jpg) |
[Full-size PNG](images/r43_c28_mechanical_review.png) |
[Bambu mechanical assembly STEP](step/53_C28_Bambu_Angled_Mounts_And_Retainer_REVIEW.step).

| Interface | New review geometry | Reason |
| :--- | :--- | :--- |
| P01 to P22 | Matched 45-degree faces; X +/-18 mm spacing; new face centres Y17, Z-55.5 mm; two M3x8 button-head screws and M3x4 inserts | Both printed parts and fastener axes change together. Nozzle, probe and tool positions do not move. |
| P21 to P22 | Integral forked tongue, 7 mm lower barrel, M3x4 insert; one M3x10 button-head screw driven upward from P22 | Positively retains the mid/lower joint instead of relying on the sleeve fit and the separate carriage mounts. |
| Cable bend | Open 4 mm fork around the 3 mm cable reference | The S-shaped feature is the live cable, not disposable material. New tongue material clears it by 0.50 mm. The tighter inherited cable-groove fit is unchanged. |
| Retainer location | Screw axis X0, Y-28.2 mm, underside seat Z-70.8 mm | Slightly forward of the narrow solid core, still below the cable bend. This leaves 1.23 mm around the insert rather than forcing an insert, tongue, fit gap and two walls into the narrowest core. |
| Receiver | 0.25 mm radial and end clearance; approximately 1.19 mm minimum separation from the channel | The existing sleeve remains the main registration feature. Small rounded/chamfered floor reinforcements prevent thin root-pocket walls. |

Nominal thread engagement is 4 mm for all three new screws. Each tongue root is
2 mm wide and 2.2 mm deep before its blend; the combined nominal section is
8.8 mm2. These are geometric dimensions, **not an allowable tightening torque or
strength rating**. Inserts must be installed before assembling the joint.

**Movement and service:** the added material and new hardware clear the actual
Monolith geometry over the checked X travel, rear limits, ten rack approaches,
both adjacent Bambu bays and 60 mm tool withdrawal. Closest sampled new-material
X-gantry clearance is **0.721 mm**, at the tongue-root blend. The exact-distance
translation checks include conservative between-sample clearance bounds; they
do not include printed distortion, cable dynamics or thermal growth. The new
underside screw remains **6.63 mm above the bed** with the nozzle at 0.2 mm;
the complete P22's original 1.23 mm minimum bed gap is unchanged. No new metal
occupies either probe's modelled sensing keepouts.

For service, park/remove the Bambu tool and raise Z for underside access. Free or
disconnect the probe lead, remove the two angled screws and the underside screw,
then lower P22 **18 mm** to release the tongue and sleeve. P21 and the EBB42 stay
on the carriage. The downward path clears P01, P21 and the rigid cable reference;
real connector access and cable slack still need a bench check.

### Printing result: retention improved, support reduction not solved

Matched H2D, ABS/Support for ABS, 0.20 mm, five-wall runs use identical machine,
process and all filament settings. Values below are deposited support, excluding
prime-tower/waste, not physical measurements.

| Part / pose | Original support, cm3 | Mechanical review, cm3 | Change |
| :--- | ---: | ---: | ---: |
| P01, back down | 4.808 | 4.775 | -0.7% |
| P21, top down | 0.643 | 1.318 | +105.0% |
| P22, back down | 9.524 | 9.136 | -4.1% |
| P22, inlet mating face down | 10.230 | 10.463 | +2.3% |
| Three-part set, using back-down P22 | 14.974 | 15.229 | **+1.7%** |

The tongue shifts support into P21. Total predicted time across the three
separate jobs rises **9.4%**. The angled tabs alone therefore do **not** make this
a whole-assembly printing improvement.

**Do not use the inlet-face-down P22 pose with this support setup.** The deposition
screen finds about **328 mm3 of support inside the narrow rear passage** in that
pose, with exact-CAD witness points. Back-down gives zero sampled deposition in
that passage. This is a trapped-support risk screen, not proof of physical
removability. The supplied P22 review STLs use **back down**; P21 uses its flat top
and P01 its back. No generated machine G-code is approved for printing.

### Remaining improvements and why

| Area | Next improvement | Why it remains necessary |
| :--- | :--- | :--- |
| Tongue printing | Rework the initial cantilever into a self-supporting ramp below the gantry, without weakening its roots or the receiver walls | The current tongue adds more support than the inclined mounts save. A preliminary alternative did not produce valid CAD and is not included in the review. |
| Inlet-down printing / curved fins | Redesign internal bridge support only after inspecting the actual deposition paths | The earlier two inlet fins did not reduce support, and this pose puts support in the rear branch. Neither two- nor three-fin trials are adopted here. |
| Cooling | Run fresh CFD with **all three revised P01/P21/P22 bodies** represented | The root-floor reinforcements add 5.01 mm3 inside the original main-channel air region, and external boundaries change. The swept feeds, 0.9 mm outlet, aim and probe seat remain unchanged, but old C28 CFD cannot be relabelled. |
| Fit and durability | Print a first article; check cable movement, insert pullout, seating/sealing and hot operation | The 0.50 mm added-part cable gap and 0.721 mm sampled gantry gap are small nominal clearances. Strength, tightening and thermal behaviour are unqualified. |

Review parts:
[P01](step/P01_C28_Bambu_45deg_Mounts_REVIEW.step) |
[P21](step/P21_C28_Bambu_Forked_Retainer_REVIEW.step) |
[P22 Beacon](step/P22_C28_Bambu_45deg_Mounts_Retainer_Beacon_REVIEW.step) |
[P22 Cartographer](step/P22_C28_Bambu_45deg_Mounts_Retainer_Cartographer_REVIEW.step).

Evidence:
[geometry, hardware and service](verification_c28_mechanical_geometry_r43.json) |
[real-scene movement](verification_c28_mechanical_motion_r43.json) |
[matched slicing](verification_c28_mechanical_slicing_r43.json) |
[support access](verification_c28_mechanical_support_access_r43.json) |
[delivery and preserved-edit provenance](verification_c28_mechanical_delivery_r43.json).
P01's frozen source also fails an exact OCC self-difference; the export audit
explicitly uses matching CAD properties, complete mesh vertices and sampled
retriangulation-patch agreement for that part, rather than trusting invalid
Boolean volumes.

## Finding and completed cleanup

**The circled feature really was unnecessary material in the airflow path.** The
previous identification from the selected Fusion face was incorrect: that face
defined the section plane, not the feature circled in the screenshot.

The new swept feed was clipped against `r43_rear_jet.duct_air()`, a helper intended
for the lower heel region and bounded above at Z -60 mm. Raising the feed roof put
part of its outer wall above that limit. This left a small roof-like obstruction
inside each existing side channel, with about 0.1 mm nominal clearance to the
original duct ceiling at its highest point.

The cleanup clips **only the added feed envelope** against the full-height original
channel. It does not indiscriminately hollow out P22. In particular, the original
cable-support rib, which has a printing purpose, stays in place.

![Matched section and close-up of the actual removed material](images/r43_swept_feed_cleanup_geometry.png)

| Completed change | Evidence | Why it is appropriate |
| :--- | :--- | :--- |
| Remove both feed-roof remnants | Approximately 23.96 mm3 each; only within X +/-12.85-18.9, Y -10.8 to -4.41, Z -60 to -58.7 mm | They occupy an intended main-channel air volume and have no mounting or required wall function there. |
| Restore the obstructed feed-entry section | At Y -10 mm: 78.84 to 85.07 mm2 open area per main side channel, a 7.9% local increase | Restores the original channel instead of enlarging the entire duct or redirecting the final jets. This is area recovery, not a 7.9% flow/cooling prediction. |
| Reduce unnecessary surface complexity | Both probe variants: 383 to 351 faces | Removes the actual redundant feature rather than deleting small faces solely because they look suspicious. |
| Preserve critical geometry | No added material; no released-duct or cable-rib material removed; changes confined to the two entry regions | Mounts, screw seats, cable route, side jets, rear slot, probe datums and the exterior envelope are outside the changed regions. |
| Improve the geometric support screen | Down-facing area requiring support: 519.3 to 510.2 mm2 in the established back-face-down orientation | Removes some internal overhang, but this modest 1.8% reduction is not slicer or print qualification. |

The nominal swept-air cutter itself is unchanged. **The connected fluid domain is
not unchanged:** removing the obstructions exposes additional main-channel air.
Accordingly, old CFD is not relabelled as a result for this cleanup.

## Follow-on trial: a larger slot without lowering its floor

**D11 was tested and not adopted; retain C28's 0.9 mm slot for Bambu.** The rear opening grows from nominal
0.9 to 1.1 mm by raising the upper lip only. The 28-degree aim, 3 mm raised feed,
cleaned entries, side jets and mounting datums remain fixed. The complete lower
air-wall surfaces coincide with the C28 baseline, not just their endpoints.

![Actual outlet views and fixed-floor section comparison](images/r43_slot_height_geometry.png)

| Geometry | Cleaned C28 baseline | D11 trial |
| :--- | ---: | ---: |
| Rear slot height | 0.9 mm | 1.1 mm |
| Nominal projected mouth area | 16.2 mm2 | 19.8 mm2 |
| Beacon / Cartographer outlet gaps | 0.593 / 0.445 mm | unchanged |
| Bambu hotend / sock gaps | 1.918 / 3.2 mm | unchanged |
| Red Lizard nominal hotend gap | 0.713 mm | 0.619 mm |
| Geometric support-screen area | 510.2 mm2 | 510.2 mm2 |

Both probe variants pass the geometric checks, four wall-normal sampling offsets
and STEP round trips. The larger nominal opening is not evidence of easier printing:
the support screen is unchanged and no slice or coupon has been printed.
The reduced Red Lizard gap is an explicit disadvantage, not a released thermal allowance.

The matched Bambu CFD case `r43directD11_bambu_bed` completed against
`r43directC28clean_bambu_bed`, at 180 L/min and 1,200 iterations. Seventeen solver,
boundary, material and mesh dictionaries are identical; only a human-readable
refinement description differs in the stage metadata.

| Bambu airflow diagnostic | C28 / 0.9 mm | D11 / 1.1 mm |
| :--- | ---: | ---: |
| Pressure at 180 L/min | 1,408.2 Pa | 1,315.9 Pa |
| Estimated total flow, 1 m hose | 231.1 L/min | 234.4 L/min |
| Rear branch at 180 L/min | 39.95 L/min | 45.54 L/min (+14.0%) |
| Mean speed, radius 1-5 mm | 26.31 m/s | 22.67 m/s (-13.8%) |
| Mean speed, radius 1-10 mm | 30.95 m/s | 28.97 m/s (-6.4%) |
| Mean speed, radius 1-14 mm | 29.34 m/s | 27.28 m/s (-7.0%) |
| Weakest/strongest sector mean-speed ratio | 0.839 | 0.902 |
| Net radial flow, radius 8 mm | 45.45 L/min | 43.10 L/min |

Speed/coverage/radial values scale to estimated blower operation. D11 is more even
but weaker across these near-print speed measures; the lowest sector mean also falls
12.8%. Its lower restriction and extra rear flow are not enough to justify replacing
the C28 baseline for today's Bambu objective. This choice is based on Bambu airflow,
**not** the reduced Red Lizard clearance. Neither trial proves thermal superiority.
Last-500 pressure peak-to-peak is 2.02% / 3.19%; mesh/time sensitivity remains.

![Matched 0.9/1.1 mm CFD](images/r43_slot_height_cfd.png)

[Full slot-height CFD evidence](verification_slot_height_cfd_r43.json).

[Trial Beacon STEP](step/P22_Swept_D11_Fixed_Floor_Beacon_REVIEW.step) |
[Trial Cartographer STEP](step/P22_Swept_D11_Fixed_Floor_Cartographer_REVIEW.step) |
[C28/D11 comparison assembly](step/P22_C28_D11_Slot_Height_Comparison_REVIEW.step) |
[Geometry and invariant-floor audit](verification_slot_height_geometry_r43.json) |
[Matched numerical controls](verification_slot_height_controls_r43.json).
Fusion document **52 Slot-height study - 0.9 vs 1.1 mm** shows both variants.

## Bambu one-piece printability pass

A separate C28 candidate adds 45-degree ramps behind the direct-mount legs,
chamfers the relief steps, and replaces the seat's flat rear window edge with a
protected truncated-V notch. The original upper fillet remains: a smaller-fillet
trial produced a non-watertight tessellation and was rejected, not repaired by
filling arbitrary mesh holes.

Both probe variants preserve the 0.9 mm airway, original main-channel material,
live mount/inlet regions, outer bounds and previous Bambu/probe clearances.
They pass watertight STEP/STL round trips and the four-offset wall screen.

**Actual slicing gives a smaller improvement than the overhang map.** Assessment
uses the saved H2D 0.4 mm ABS / Support for ABS profiles, 0.2 mm layers, five walls,
automatic trees, support allowed on the part and small-overhang removal disabled.
These measurements are for the Beacon-seat model.

| Candidate / print pose | Deposited support | Estimated total time | Narrow rear-passage support |
| :--- | ---: | ---: | :--- |
| Original C28, back face down | 9.524 cm3 | 3.11 h | None in sampled toolpaths |
| Printability C28, back face down | 9.208 cm3 (-3.3%) | 2.90 h (-6.8%) | None in sampled toolpaths |
| Printability C28, rear-corner face down | 5.570 cm3 (-41.5%) | 3.69 h | Approximately 30 mm3 detected; reject for the current ABS support-body setup |

Geometric overhang area falls from 510.2 to 369.7 mm2 (-27.5%), but that is not
the same as support material saved. The remaining support trees are dominated by
other cantilevers, particularly the mounting faces. Disabling support for recognized
bridges made no meaningful change in either geometry. The angled pose is not an
acceptable shortcut if it leaves support inside the narrow passage.

The exterior-flow recheck also shows a trade-off: pressure changes +0.46%, rear
branch flow is essentially unchanged, and within-5-mm mean speed changes +2.35%.
However, the weakest/strongest sector ratio falls from 0.839 to 0.642, the weakest
sector mean falls 15.4%, and radius-8-mm net radial flow falls from 45.45 to
41.82 L/min. These are single oscillating steady snapshots, not thermal results.
The low-support candidate is therefore a manufacturing study, not a proven overall
upgrade over the airflow baseline.

[Beacon review STEP](step/P22_C28_Bambu_Low_Support_Beacon_REVIEW.step) |
[Beacon back-face-down STL](stl/P22_C28_Bambu_Low_Support_Beacon_REVIEW_PRINT_ORIENTED.stl) |
[Cartographer review STEP](step/P22_C28_Bambu_Low_Support_Cartographer_REVIEW.step) |
[Cartographer back-face-down STL](stl/P22_C28_Bambu_Low_Support_Cartographer_REVIEW_PRINT_ORIENTED.stl).

[Geometry audit](verification_swept_printable_geometry_r43.json) |
[Slicer comparison](verification_swept_printable_slicing_r43.json) |
[Sampled support-access check](verification_swept_support_access_r43.json) |
[Airflow recheck](verification_printability_cfd_r43.json) |
[Matched CFD fields](images/r43_printability_cfd.png).

The slicer outputs are analysis artifacts, **not approved machine G-code**; generate
printing instructions with the user's validated printer startup/nozzle settings.
No physical print has been performed. A larger reduction without inaccessible
supports may require a split, sealed construction rather than further cosmetic
chamfers on the same one-piece topology.

## Areas still needing improvement

Priorities below are engineering recommendations. Except for the feed-roof removal
and the D11/one-piece printability trials above, they have **not** been implemented
or claimed as performance improvements.

| Priority / area | Current evidence or concern | How I would improve it | Why / acceptance evidence |
| :--- | :--- | :--- | :--- |
| High: printed rear slot and internal finish | Nominal 0.9 mm slot; 0.8 mm new passage walls; internal access is limited. Neither variant is sliced or printed. | Slice the cleaned part in the intended material/profile and inspect every slot/bridge layer. Print a representative outlet coupon before a complete part. Avoid inaccessible internal support; tune bridging/flow or reshape the local roof only if the coupon requires it. | A sagged or over-extruded slot can change the effective area more than a small CAD optimization. Require an open, continuous slot with measured dimensions and no trapped support. |
| High: clearance and thermal/tolerance allowance | Minimum new outlet-to-probe gaps: Beacon 0.593 mm, Cartographer 0.445 mm. Red Lizard gap: 0.713 mm. These are nominal CAD clearances. | Measure actual boards, installed fasteners and hotends; define a tolerance/thermal stack. If inadequate, reroute or locally relieve the duct away from the constraint while retaining the sensor datum and a justified wall thickness. | Collision-free CAD is not a safe operating allowance for print error, warpage and hot components. Do not solve a duct conflict by moving the probe without requalifying its sensing height. |
| High: reliable cooling comparison | Existing results are steady, oscillating airflow fields, not temperature or heat-transfer measurements. | First repeat the cleaned geometry at additional local resolutions and examine several late fields. For thermal ranking, use a controlled heated-bead/coupon test or a thermal model with realistic material, temperatures and boundary conditions. | More speed, a better sector ratio or lower inlet pressure alone does not establish better part cooling. Require repeatable temperature/print outcomes, not a single velocity snapshot. |
| Medium: branch take-off and merge | The caps are removed, but the main-channel-to-branch intersection still has a distinct lip and curved turn. | Inspect velocity and total-pressure changes across that junction; test a smooth entry blend or a gentler take-off in one controlled variant. Keep the final slot and aim fixed. | Reduce separation/turning loss without simply drawing more air away from the side jets. Retain only a change that improves delivery/coverage at comparable blower conditions and passes walls/keepouts. |
| Medium: rear/side flow balance and aim | The previous 28-degree case improved sector evenness relative to 32 degrees but reduced radius-8-mm signed net outflow. | Use the cleaned geometry as the new baseline. If its branch balance still warrants it, compare 0.9 mm against one modest 1.1 mm slot variant at the same aim; change only one variable. | A larger rear outlet lowers that branch's resistance and changes the entire flow split. It is not automatically better cooling. Compare total pressure, rear/side flow, weak sectors and near-print transport together. |
| Medium: entry-region CFD resolution | The old cap-to-ceiling clearance was about 0.1 mm; matching mesh settings does not prove this small gap was resolved. | Add the same focused entry refinement to both geometries for a follow-up sensitivity study. Keep quality limits unchanged and monitor section closure as well as near-print results. | The cleanup's geometric benefit is clear, but a CFD percentage can contain both physical and under-resolution effects. A passing `checkMesh` is necessary, not a mesh-independence certificate. |
| Medium: tool/probe coverage | Current-angle airflow evidence is for Bambu with the Beacon scene. Red Lizard and Cartographer have geometry checks, not all corresponding CFD combinations. | Cross-check the leading cleaned geometry with the other hotend and the actual alternative probe envelope before making a shared performance claim. | The hotend and probe influence impingement, recirculation and blocked paths. A common mounting interface does not guarantee common cooling behavior. |
| Low: tiny residual CAD faces | Eighteen faces below 0.01 mm2 remain in each variant; the count is unchanged by the cleanup. The bodies are valid and watertight. | Investigate only those that produce thin material, bad export, poor meshing or slicer defects. Merge equivalent faces only with shape-equivalence checks. | Small trimmed faces are not the same as detached debris. Blanket healing or deletion risks moving the narrow slot or changing walls. |

**Opening-size recommendation:** retain the 0.9 mm final slot as the Bambu baseline.
The controlled 1.1 mm trial increased rear flow but reduced the near-print speed and
radius-8-mm transport diagnostics. The printability pass will preserve the selected
0.9 mm airway instead of enlarging the outlet as a shortcut.

## Geometry and export evidence

Both probe variants are one valid solid with one shell. Their tessellations are
watertight with consistent winding. Wall-normal material checks at 0.1, 0.35, 0.6
and 0.75 mm pass; suspect tessellation classifications are resolved against exact
CAD, excluding deliberate main-channel connections and the open outlet.

The sampled 60 mm -Y withdrawal retains the previous minimum clearances: Bambu
1.918 mm, Red Lizard 0.713 mm; the Bambu silicone-sock gap remains 3.2 mm. The
sampling step is 0.5 mm, not a continuous-motion guarantee. Probe sensing keepouts
and modeled mounting hardware remain clear. Removal inside the channel cannot
enlarge the gantry envelope; this does not replace an actual machine fit test.

The standalone STEP round trips have no detected geometric difference under the
audit's comparison tolerance. Fusion document **51 Cleaned C28 feed - both probes -
REVIEW** contains the new assembly; the previous documents were preserved.

[Beacon STEP](step/P22_Swept_C28_Clean_Feed_Beacon_REVIEW.step) |
[Cartographer STEP](step/P22_Swept_C28_Clean_Feed_Cartographer_REVIEW.step) |
[Assembly and air-route cutaway STEP](step/P22_Swept_C28_Clean_Feed_Assembly_REVIEW.step).

## Matched CFD pass

The new case is `r43directC28clean_bambu_bed`, compared against the frozen
`r43directC28q_bambu_bed`. It retains 180 L/min, the 1,200-iteration schedule,
46-way decomposition, original obstacle exclusions and local refinement. Seventeen
meshing, solver, transport and initial-boundary dictionaries were compared byte for
byte; the stage metadata and ambient-domain controls also match.

**Completed:** the cleaned mesh passes with 2,479,266 cells and maximum skewness
3.32; the solver reached iteration 1,200 normally.

| Same 28-degree aim | Before inlet cleanup | After inlet cleanup |
| :--- | ---: | ---: |
| Pressure at 180 L/min | 1,461.4 Pa | 1,408.2 Pa (-3.64%) |
| Estimated blower flow, 1 m hose | 229.4 L/min | 231.1 L/min |
| Rear branch at 180 L/min | 39.45 L/min | 39.95 L/min |
| Mean speed, radius 1-5 mm | 24.20 m/s | 26.31 m/s (+8.70%) |
| Mean speed, radius 1-10 mm | 28.50 m/s | 30.95 m/s (+8.63%) |
| Weakest/strongest sector mean-speed ratio | 0.883 | 0.839 |
| Net radial flow, radius 8 mm | 33.14 L/min | 45.45 L/min |

Speed, sector and radial-flow values scale to estimated blower operation, not measured
blower performance. The cleanup reduces modeled restriction and improves these speed/
transport diagnostics; its sector ratio is slightly less even than the prior C28
snapshot. Pressure peak-to-peak over the last 500 iterations is 2.02%; approximate
side-plus-rear section closure is +0.24%. The entry's former sub-cell ceiling gap,
oscillating steady fields and resolution limits still prevent a thermal conclusion.

Against accepted released R43, cleaned C28 has 35.8% lower pressure at 180 L/min,
11.4% more estimated blower flow, 21.1% lower within-5-mm mean speed, 10.7% higher
within-14-mm mean speed and 4.5% lower radius-8-mm net radial flow. The sector ratio
is 0.839 versus 0.672. This is a trade-off, not an overall cooling winner. The direct
R43 comparison has different local mesh refinement/decomposition (1.64M vs 2.48M
cells), unlike the matched C28 before/after cleanup pair.

[Cleaned-feed CFD report](verification_feed_cleanup_cfd_r43.json) |
[Matched entry/nozzle/near-bed fields](images/r43_feed_cleanup_cfd.png).

## Reproducibility and records

Generate the cleaned geometry with
`r43_swept_feed.p22(base, probe, roof_raise=3, mouth_height=0.9, angle_deg=28,
remove_rear_mounts=True, conformal_outlet=True, clear_feed_intrusions=True)`.
The new flag defaults to false, preserving historical variant geometry.
For the D11 trial, use `mouth_height=1.1, floor_reference_height=0.9` with the same
other arguments. Omitting `floor_reference_height` preserves the old centered-slot
behavior; its default regression against frozen C28 is recorded in the trial audit.

- [Confined-removal, wall and STEP audit](verification_swept_feed_cleanup_r43.json)
- [Assembly, probe and withdrawal qualification](verification_swept_feed_optC28_clean_r43.json)
- [Matched CFD controls](verification_feed_cleanup_controls_r43.json)
- [New Fusion review record](verification_clean_feed_fusion_r43.json)
- `python audit_swept_feed_cleanup_r43.py` and
  `python render_swept_feed_cleanup_r43.py` reproduce the audit/visuals when the
  frozen session inputs are available.
- After the accepted result is retrieved and analyzed:
  `python cfd_direct_mount_r43.py --feed-cleanup`.
- **On another machine:** builders read frozen working inputs from `acc.WORK` and
  vendor probe models from `acc.SENSOR_DIR`. Set `SPARKSHIFT_WORK` and
  `SPARKSHIFT_SENSOR_DIR` to copies of those folders; the defaults are this
  workstation's session paths. A copy of the working inputs is in the data-only
  branch `nisparks-beacon-cpap-ebb42-workdata`; its README lists the setup and the
  vendor probe models to add.
