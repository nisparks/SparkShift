#!/bin/bash
source /usr/lib/openfoam/openfoam2512/etc/bashrc
set -euo pipefail
cd "/work/$1"
foamToVTK -time 1200 -poly-decomp -no-boundary -fields '(U p)' -name VTK_decomp > log.vtk_decomp 2>&1
