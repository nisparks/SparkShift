#!/bin/bash
# Diagnose the start of a simpleFoam run.  Usage: cfd_diag.sh <case>
cd $HOME/sparkshift_cfd/$1 || exit 1
echo "=== running solver processes: $(pgrep -xc simpleFoam)"
echo "=== potentialFoam"
grep -iE "Interpolated|continuity|Calculating|End|Warn|error" log.potentialFoam | tail -8
echo "=== first iterations"
awk '/^Time = 1$/,/^Time = 3$/' log.simpleFoam | grep -vE '^$'
for t in 5 10 20 40 80; do
    echo "--- Time = $t"
    awk -v t="$t" '$0 == "Time = " t {f=1} f && /^Time = / && $0 != "Time = " t {exit} f' log.simpleFoam | \
        grep -E "continuity|bounding|Solving for (p|Ux)"
done
