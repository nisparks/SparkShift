#!/bin/bash
# Run a case written by cfd_case.py inside WSL.  Usage: cfd_run.sh <case dir under /mnt/c> [mesh|solve|vtk|all]
source /usr/lib/openfoam/openfoam2606/etc/bashrc
set -e
SRC=$(realpath "$1"); NAME=$(basename "$SRC"); WHAT=${2:-all}
DST=$HOME/sparkshift_cfd/$NAME
NP=$(cat "$SRC/np.txt")
stamp() { echo "[$(date +%H:%M:%S)] $*"; }

if [ "$WHAT" = all ] || [ "$WHAT" = mesh ]; then
    rm -rf "$DST"; mkdir -p "$DST"; cp -r "$SRC"/. "$DST"/
    cd "$DST"
    stamp "surfaceCheck"; surfaceCheck constant/triSurface/domain.stl > log.surfaceCheck 2>&1 || true
    stamp "surfaceFeatureExtract"; surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
    stamp "blockMesh"; blockMesh > log.blockMesh 2>&1
    stamp "decomposePar (mesh)"; decomposePar -force > log.decomposePar.mesh 2>&1
    stamp "snappyHexMesh x$NP"; mpirun -np $NP snappyHexMesh -overwrite -parallel > log.snappyHexMesh 2>&1
    stamp "reconstructParMesh"; reconstructParMesh -constant > log.reconstructParMesh 2>&1
    rm -rf processor*
    stamp "checkMesh"; checkMesh -constant > log.checkMesh 2>&1 || true
    grep -E "cells:|faces:|points:|Max non-orth|Max skewness|Mesh OK|Failed|\*\*\*" log.checkMesh | head -20
fi

if [ "$WHAT" = all ] || [ "$WHAT" = solve ]; then
    cd "$DST"
    cp -r "$SRC"/system "$SRC"/0.orig "$DST"/
    cp "$SRC"/*.txt "$SRC"/*.json "$DST"/
    cp "$SRC"/constant/*Properties "$DST"/constant/
    rm -rf processor* 0 postProcessing log.simpleFoam log.potentialFoam
    find . -maxdepth 1 -regex './[0-9]+' -exec rm -rf {} +
    cp -r 0.orig 0
    stamp "decomposePar"; decomposePar -force > log.decomposePar 2>&1
    stamp "potentialFoam x$NP"; mpirun -np $NP potentialFoam -writephi -parallel > log.potentialFoam 2>&1
    # First-order upwind until UPWIND, then swap in the second-order schemes (re-read at run time).
    UPWIND=$(cat upwind.txt)
    ( while ! grep -q "^Time = $UPWIND\$" log.simpleFoam 2>/dev/null; do sleep 5; done
      cp system/fvSchemes.second system/fvSchemes; touch system/fvSchemes
      echo "[$(date +%H:%M:%S)] second-order schemes from iteration $UPWIND" ) &
    stamp "simpleFoam x$NP"; mpirun -np $NP simpleFoam -parallel > log.simpleFoam 2>&1
    wait
    stamp "reconstructPar"; reconstructPar -time "$(cat times.txt)" > log.reconstructPar 2>&1
fi

if [ "$WHAT" = all ] || [ "$WHAT" = solve ] || [ "$WHAT" = vtk ]; then
    cd "$DST"
    for t in $(cat times.txt | tr ',' ' '); do
        stamp "foamToVTK $t"
        foamToVTK -time $t -fields '(U p k omega nut pTotal yPlus)' > log.foamToVTK.$t 2>&1
    done
    rm -rf "$SRC/results"; mkdir -p "$SRC/results"
    cp -r VTK postProcessing log.* "$SRC/results/" 2>/dev/null || true
    stamp "copied results to $SRC/results"
fi
stamp "done"
