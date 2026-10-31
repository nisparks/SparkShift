#!/bin/bash
# Run a case written by cfd_cpap_r41.py with OpenFOAM (v2512 or later).
# Usage: run_case.sh <case dir> [mesh|solve|post|vtk|all]
#   FOAM_BASHRC  OpenFOAM's etc/bashrc (default /usr/lib/openfoam/openfoam2512/etc/bashrc)
#   MPIBIND      mpirun binding (default "--bind-to core --map-by core"; "--bind-to none" when sharing a host)
source "${FOAM_BASHRC:-/usr/lib/openfoam/openfoam2512/etc/bashrc}"
set -e
cd "$1"
WHAT=${2:-all}
NP=$(cat np.txt)
export OMPI_MCA_btl_vader_single_copy_mechanism=none
MPIRUN="mpirun ${MPIBIND:---bind-to core --map-by core} -np $NP"
stamp() { echo "[$(date +%H:%M:%S)] $*" | tee -a log.run; }

if [ "$WHAT" = all ] || [ "$WHAT" = mesh ]; then
    rm -rf processor* constant/polyMesh constant/extendedFeatureEdgeMesh
    stamp "surfaceCheck"; surfaceCheck constant/triSurface/domain.stl > log.surfaceCheck 2>&1 || true
    stamp "surfaceFeatureExtract"; surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
    stamp "blockMesh"; blockMesh > log.blockMesh 2>&1
    stamp "decomposePar (mesh)"; decomposePar -force > log.decomposePar.mesh 2>&1
    stamp "snappyHexMesh x$NP"; $MPIRUN snappyHexMesh -overwrite -parallel > log.snappyHexMesh 2>&1
    stamp "reconstructParMesh"; reconstructParMesh -constant > log.reconstructParMesh 2>&1
    rm -rf processor*
    stamp "checkMesh"; checkMesh -constant > log.checkMesh 2>&1 || true
    grep -E "cells:|Total volume|Max non-orth|Max skewness|Mesh OK|Failed|\*\*\*" log.checkMesh | tee -a log.run
fi

if [ "$WHAT" = all ] || [ "$WHAT" = solve ]; then
    rm -rf processor* 0 postProcessing log.simpleFoam log.potentialFoam
    find . -maxdepth 1 -regex './[0-9]+' -exec rm -rf {} +
    cp system/fvSchemes.first system/fvSchemes
    cp -r 0.orig 0
    stamp "decomposePar"; decomposePar -force > log.decomposePar 2>&1
    stamp "potentialFoam x$NP"; $MPIRUN potentialFoam -writephi -parallel > log.potentialFoam 2>&1
    # First-order upwind until UPWIND, then the second-order schemes (simpleFoam re-reads fvSchemes).
    UPWIND=$(cat upwind.txt)
    ( while ! grep -q "^Time = $UPWIND\$" log.simpleFoam 2>/dev/null; do sleep 5; done
      cp system/fvSchemes.second system/fvSchemes; touch system/fvSchemes
      stamp "second-order schemes from iteration $UPWIND" ) &
    stamp "simpleFoam x$NP"; $MPIRUN simpleFoam -parallel > log.simpleFoam 2>&1
    wait
fi

if [ "$WHAT" = all ] || [ "$WHAT" = solve ] || [ "$WHAT" = post ]; then
    stamp "reconstructPar"; reconstructPar -time "$(cat times.txt)" > log.reconstructPar 2>&1
fi

if [ "$WHAT" = all ] || [ "$WHAT" = solve ] || [ "$WHAT" = post ] || [ "$WHAT" = vtk ]; then
    # Optional per-case field list, e.g. with fieldAverage means; older cases keep the default.
    FIELDS='(U p k omega nut pTotal yPlus)'
    if [ -f vtkfields.txt ]; then FIELDS=$(cat vtkfields.txt); fi
    for t in $(tr ',' ' ' < times.txt); do
        stamp "foamToVTK $t"
        foamToVTK -time $t -fields "$FIELDS" > log.foamToVTK.$t 2>&1
    done
fi
stamp "done"
