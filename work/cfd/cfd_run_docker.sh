#!/bin/bash
# Run a case written by cfd_case.py inside the opencfd/openfoam-default container, case in /work/<name>.
# Usage (in the container): cfd_run_docker.sh <name> [mesh|solve|vtk|all]
source /usr/lib/openfoam/openfoam2512/etc/bashrc
set -e
NAME=$1; WHAT=${2:-all}
cd /work/$NAME
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
    cp system/fvSchemes.first system/fvSchemes 2>/dev/null || cp system/fvSchemes system/fvSchemes.first
    cp -r 0.orig 0
    stamp "decomposePar"; decomposePar -force > log.decomposePar 2>&1
    stamp "potentialFoam x$NP"; $MPIRUN potentialFoam -writephi -parallel > log.potentialFoam 2>&1
    # First-order upwind until UPWIND, then swap in the second-order schemes (re-read at run time).
    UPWIND=$(cat upwind.txt)
    ( while ! grep -q "^Time = $UPWIND\$" log.simpleFoam 2>/dev/null; do sleep 5; done
      cp system/fvSchemes.second system/fvSchemes; touch system/fvSchemes
      stamp "second-order schemes from iteration $UPWIND" ) &
    stamp "simpleFoam x$NP"; $MPIRUN simpleFoam -parallel > log.simpleFoam 2>&1
    wait
    stamp "reconstructPar"; reconstructPar -time "$(cat times.txt)" > log.reconstructPar 2>&1
fi

if [ "$WHAT" = all ] || [ "$WHAT" = solve ] || [ "$WHAT" = vtk ]; then
    for t in $(cat times.txt | tr ',' ' '); do
        stamp "foamToVTK $t"
        foamToVTK -time $t -fields '(U p k omega nut pTotal yPlus)' > log.foamToVTK.$t 2>&1
    done
fi
stamp "done"
