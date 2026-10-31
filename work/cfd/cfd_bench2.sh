#!/bin/bash
# Time a few simpleFoam iterations under different MPI settings.  Usage: cfd_bench.sh <case>
source /usr/lib/openfoam/openfoam2606/etc/bashrc
cd $HOME/sparkshift_cfd/$1 || exit 1
pkill -x simpleFoam; sleep 2
cp system/controlDict system/controlDict.bak
foamDictionary -entry endTime -set 12 system/controlDict > /dev/null
foamDictionary -entry writeInterval -set 100000 system/controlDict > /dev/null
run() {
    local tag=$1; shift
    timeout 150 "$@" > log.bench.$tag 2>&1
    grep ExecutionTime log.bench.$tag | awk -v tag=$tag 'NR==4{a=$3} NR==12{b=$3} END{printf "%s: iterations 4..12 took %.1f s\n", tag, b-a}'
    grep -iE "error|btl|vader" log.bench.$tag | head -3
}
run default        mpirun -np 10 simpleFoam -parallel
run noFO           mpirun -np 10 simpleFoam -parallel -noFunctionObjects
run vader          mpirun --mca btl self,vader --bind-to core -np 10 simpleFoam -parallel -noFunctionObjects
run tcp            mpirun --mca btl self,tcp -np 10 simpleFoam -parallel -noFunctionObjects
cp system/controlDict.bak system/controlDict
