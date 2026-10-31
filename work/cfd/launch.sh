#!/bin/bash
# Launch CFD cases in detached OpenFOAM containers on this host.
# Usage: launch.sh <mode: all|solve|post|vtk> <np or -> <bind: core|none> <case> [<case> ...]
cd $HOME/sparkshift_cfd || exit 1
MODE=$1; NP=$2; BIND=$3; shift 3
for c in "$@"; do
    if [ "$NP" != "-" ]; then
        echo $NP > $c/np.txt
        sed -i "s/numberOfSubdomains [0-9]*;/numberOfSubdomains $NP;/" $c/system/decomposeParDict
    fi
    if [ "$BIND" = none ]; then B="--bind-to none"; else B="--bind-to core --map-by core"; fi
    docker rm -f sfcfd_$c > /dev/null 2>&1
    docker run -d --name sfcfd_$c --shm-size=8g -v $HOME/sparkshift_cfd:/work --user $(id -u):$(id -g) \
        -e HOME=/work -e MPIBIND="$B" --entrypoint bash opencfd/openfoam-default:2512 \
        /work/cfd_run_docker2.sh $c $MODE > /dev/null && echo "launched $c ($MODE, np $(cat $c/np.txt), bind $BIND)"
done
docker ps --format '{{.Names}} {{.Status}}' | grep sfcfd
