#!/bin/bash
# Progress of a running simpleFoam case: last iteration, inlet pressures and residuals.  Usage: cfd_progress.sh <case>
D=$HOME/sparkshift_cfd/$1
L=$D/log.simpleFoam
[ -f "$L" ] || { echo "no simpleFoam log yet"; tail -3 $D/log.potentialFoam 2>/dev/null; exit 0; }
echo "iteration: $(grep -E '^Time = ' $L | tail -1)   ExecutionTime: $(grep ExecutionTime $L | tail -1)"
F=$(ls $D/postProcessing/inletAvg/*/surfaceFieldValue.dat 2>/dev/null | head -1)
[ -n "$F" ] && { echo "inlet areaAverage (time p pTotal), every 100 iterations:"; awk 'NR>5 && $1 % 100 == 0' $F | tail -${2:-12}; }
grep -E "^(smoothSolver|GAMG).*Solving for (Ux|p|k|omega)" $L | tail -5 | sed 's/, No Iterations.*//'
grep -iE "nan|error|bounding" $L | tail -3
