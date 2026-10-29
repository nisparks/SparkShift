#!/bin/bash
# Run cases in detached opencfd/openfoam-default containers on a Docker host (no OpenFOAM install needed).
# Usage: launch_docker.sh <work dir> <mode: all|solve|post|vtk> <np or -> <bind: core|none> <case> [<case> ...]
#   e.g. launch_docker.sh ~/sparkshift_cfd all 20 none released_bambu r41_redlizard
# First copy run_case.sh and each case (WORK/cfd/cases/<name> from cfd_cpap_r41.py) into the work dir.
# Progress: <case>/log.run. Afterwards copy <case>/VTK, postProcessing, log.checkMesh, stages.json and
# domain.json to WORK/cfd/results/<name> and run `cfd_cpap_r41.py analyse <name>`.
WORK=$(realpath "$1"); MODE=$2; NP=$3; BIND=$4; shift 4
IMAGE=${IMAGE:-opencfd/openfoam-default:2512}
cd "$WORK" || exit 1
for c in "$@"; do
    if [ "$NP" != "-" ]; then
        echo "$NP" > "$c/np.txt"
        sed -i "s/numberOfSubdomains [0-9]*;/numberOfSubdomains $NP;/" "$c/system/decomposeParDict"
    fi
    if [ "$BIND" = none ]; then B="--bind-to none"; else B="--bind-to core --map-by core"; fi
    docker rm -f "sfcfd_$c" > /dev/null 2>&1
    docker run -d --name "sfcfd_$c" --shm-size=8g -v "$WORK":/work --user "$(id -u):$(id -g)" -e HOME=/work \
        -e MPIBIND="$B" --entrypoint bash "$IMAGE" /work/run_case.sh "/work/$c" "$MODE" > /dev/null \
        && echo "launched $c ($MODE, np $(cat "$c/np.txt"), bind $BIND)"
done
docker ps --format '{{.Names}} {{.Status}}' | grep sfcfd
