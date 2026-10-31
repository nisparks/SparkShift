#!/bin/bash
# Progress of remote CFD cases.  Usage: cfd_status.sh <case> [<case> ...]
for NAME in "$@"; do
    D=$HOME/sparkshift_cfd/$NAME
    echo "===== $NAME  (container: $(docker inspect -f '{{.State.Status}}' sfcfd_$NAME 2>/dev/null))"
    tail -n 4 $D/log.run 2>/dev/null
    L=$D/log.simpleFoam
    if [ -f "$L" ]; then
        echo "  $(grep -E '^Time = ' $L | tail -1)   $(grep ExecutionTime $L | tail -1)"
        F=$(ls $D/postProcessing/inletAvg/*/surfaceFieldValue.dat 2>/dev/null | head -1)
        [ -n "$F" ] && awk 'NR>5 && $1 % 100 == 0 {printf "  it %5d  p %10.1f  pTotal %10.1f  (Pa: %7.1f)\n", $1, $2, $3, 1.2*$3}' $F | tail -6
        grep -iE "nan|fatal|error" $L | tail -2
    fi
    grep -E "cells:|Total volume|Max non-orth|Mesh OK|Failed" $D/log.checkMesh 2>/dev/null | head -4
done
