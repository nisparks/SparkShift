# SparkShift working data: Beacon/Cartographer, CPAP and EBB42 C28 study

Working inputs for the code branch `nisparks-beacon-cpap-ebb42-integration`. This
data-only branch lets that work resume on another machine. It is not a release and
is not intended to be merged into `main`.

## Resume on another machine

```powershell
git clone https://github.com/nisparks/SparkShift.git
cd SparkShift
git checkout nisparks-beacon-cpap-ebb42-integration
git worktree add ..\SparkShift-workdata nisparks-beacon-cpap-ebb42-workdata

$env:SPARKSHIFT_WORK = (Resolve-Path ..\SparkShift-workdata\work).Path
$env:SPARKSHIFT_SENSOR_DIR = (Resolve-Path ..\SparkShift-workdata\sensor_sources).Path
$env:SPARKSHIFT_CAD = (Resolve-Path .\cad\SparkShift_Accessories_v26).Path

cd cad\SparkShift_Accessories_v26
python audit_c28_flow_neutral_retainer_r43.py    # current Bambu retainer (v5d)
python audit_c28_user_retainer_r43.py            # earlier sealed receiver (v4)
```

Before running probe checks, copy the vendor probe models listed under
`vendor_models_not_included` in `MANIFEST.json` into `sensor_sources/`, using the
same file names. They are not redistributed here. A different vendor revision
changes the SHA-256 and may change the probe-geometry results.

The Python package versions used are recorded in `MANIFEST.json`. Slicing used
Bambu Studio's command-line interface at its default Windows install path.

## Contents

- `work/` mirrors the original session working folder (`SPARKSHIFT_WORK`):
  frozen r41/r43 scene BREPs, carriage/gantry/EBB42 caches, the C28 study BREPs
  (cleaned feed, angled mounts, the user's P21 snapshot, the sealed receiver and the
  flow-neutral retainer builds v5b to v5d with their Fusion review archives),
  H2D slicer presets, slice metrics, CFD scripts with small P22 BREPs, and session
  tools.
- `sensor_sources/` holds probe measurements (`SPARKSHIFT_SENSOR_DIR`).
- `MANIFEST.json` lists every file with its size and SHA-256.

Not included: CFD case, domain and result folders (about 31 GB; summaries are in
the code branch's verification JSON files), G-code and sliced projects, large
review assemblies, and screenshots.

Current-workflow session tools honor `SPARKSHIFT_CAD` and locate `work/` from
their own path. Older one-off session scripts may still contain the original
workstation paths. CFD ran on a separate OpenFOAM Linux host; its run scripts
assume that host's layout.
