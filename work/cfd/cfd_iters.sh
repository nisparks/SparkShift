#!/bin/bash
# Solver iteration counts and timing per SIMPLE iteration.  Usage: cfd_iters.sh <case>
L=$HOME/sparkshift_cfd/$1/log.simpleFoam
grep -E '^Time = ' "$L" | tail -1
awk '/^Time = /{t=$3} /No Iterations/{sub(/Initial residual.*No Iterations/, "iters"); print t, $0}' "$L" | tail -8
grep ExecutionTime "$L" | tail -4
grep -c "^Time = " "$L"
