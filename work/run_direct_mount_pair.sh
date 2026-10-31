#!/bin/bash
set -euo pipefail
cd "$HOME/sparkshift_cfd"
cases=(r43directA_bambu_bed r43directA_redlizard_bed)
for c in "${cases[@]}"; do
    test -d "$c"
    if docker container inspect "sfcfd_$c" >/dev/null 2>&1; then
        echo "Refusing to overwrite existing container sfcfd_$c" >&2
        exit 1
    fi
    docker run -d --name "sfcfd_$c" --shm-size=8g \
        -v "$PWD":/work --user "$(id -u):$(id -g)" -e HOME=/work \
        -e MPIBIND="--bind-to none" --entrypoint bash opencfd/openfoam-default:2512 \
        -c "ulimit -c 0; bash /work/run_case.sh /work/$c mesh && grep -q 'Mesh OK.' /work/$c/log.checkMesh && bash /work/run_case.sh /work/$c solve"
done
failed=0
for c in "${cases[@]}"; do
    code=$(docker wait "sfcfd_$c")
    echo "$c exit $code"
    tail -n 8 "$c/log.run"
    if [ "$code" != 0 ]; then failed=1; fi
done
test "$failed" = 0
paths=()
for c in "${cases[@]}"; do
    grep -q 'Mesh OK.' "$c/log.checkMesh"
    grep -q '^Time = 1200$' "$c/log.simpleFoam"
    for f in VTK postProcessing log.checkMesh log.simpleFoam log.run stages.json domain.json; do
        paths+=("$c/$f")
    done
done
tar -czf r43directA_results.tgz "${paths[@]}"
echo "Direct-mount pair complete and archived"
