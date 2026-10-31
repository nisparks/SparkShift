#!/bin/bash
set -euo pipefail
cd "$HOME/sparkshift_cfd"
c=r43directC28clean_bambu_bed
test -d "$c"
if docker container inspect "sfcfd_$c" >/dev/null 2>&1; then
    echo "Refusing to overwrite existing container sfcfd_$c" >&2
    exit 1
fi
docker run -d --name "sfcfd_$c" --shm-size=8g \
    -v "$PWD":/work --user "$(id -u):$(id -g)" -e HOME=/work \
    -e MPIBIND="--bind-to none" --entrypoint bash opencfd/openfoam-default:2512 \
    -c "ulimit -c 0; bash /work/run_case.sh /work/$c mesh && grep -q 'Mesh OK.' /work/$c/log.checkMesh && bash /work/run_case.sh /work/$c solve"
code=$(docker wait "sfcfd_$c")
echo "$c exit $code"
tail -n 10 "$c/log.run"
test "$code" = 0
grep -q 'Mesh OK.' "$c/log.checkMesh"
grep -q '^Time = 1200$' "$c/log.simpleFoam"
grep -q '^End$' "$c/log.simpleFoam"
tar -czf r43directC28clean_results.tgz "$c/VTK" "$c/postProcessing" \
    "$c/log.checkMesh" "$c/log.simpleFoam" "$c/log.run" "$c/stages.json" "$c/domain.json"
echo "Cleaned feed case complete and archived"
