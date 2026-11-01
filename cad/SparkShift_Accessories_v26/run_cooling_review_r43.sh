#!/bin/bash
# Run inside the existing OpenFOAM image on a NEW, verified review case only.
if ! source /usr/lib/openfoam/openfoam2512/etc/bashrc; then
    echo "OpenFOAM environment setup failed" >&2
    exit 1
fi
set -euo pipefail
command -v simpleFoam >/dev/null
command -v mpirun >/dev/null
case_dir=$(realpath "${1:?new case directory required}")
[[ "$case_dir" =~ ^/work/r43audit[A-Za-z0-9_]+$ ]]
cd "$case_dir"
test ! -e log.run
test ! -d constant/polyMesh
test ! -d 0
sha256sum --quiet -c input_hashes.sha256
echo "Case input hashes verified inside the solver container"
np=$(cat np.txt)
[[ "$np" =~ ^[0-9]+$ ]]
export OMPI_MCA_btl_vader_single_copy_mechanism=none
mpi=(mpirun --bind-to none -np "$np")
stamp() { echo "[$(date -u +%T)] $*" | tee -a log.run; }
printf 'OpenFOAM=%s\nprocessors=%s\n' "$WM_PROJECT_VERSION" "$np" > runtime.txt
stamp surfaceCheck
surfaceCheck constant/triSurface/domain.stl > log.surfaceCheck 2>&1
stamp surfaceFeatureExtract
surfaceFeatureExtract > log.surfaceFeatureExtract 2>&1
stamp blockMesh
blockMesh > log.blockMesh 2>&1
stamp decomposePar-mesh
decomposePar > log.decomposePar.mesh 2>&1
stamp snappyHexMesh
"${mpi[@]}" snappyHexMesh -overwrite -parallel > log.snappyHexMesh 2>&1
stamp reconstructParMesh
reconstructParMesh -constant > log.reconstructParMesh 2>&1
stamp checkMesh
checkMesh -constant > log.checkMesh 2>&1
grep -q 'Mesh OK.' log.checkMesh
cp -r 0.orig 0
cp system/fvSchemes.first system/fvSchemes
stamp decomposePar-solve
decomposePar -force > log.decomposePar 2>&1
stamp potentialFoam
"${mpi[@]}" potentialFoam -writephi -parallel > log.potentialFoam 2>&1
stamp simpleFoam
"${mpi[@]}" simpleFoam -parallel > log.simpleFoam 2>&1 &
solver_pid=$!
upwind=$(cat upwind.txt)
while kill -0 "$solver_pid" 2>/dev/null; do
    if grep -q "^Time = ${upwind}$" log.simpleFoam; then
        cp system/fvSchemes.second system/fvSchemes
        observed=$(awk '/^Time = / {t=$3} END {print t}' log.simpleFoam)
        stamp "second-order schemes; observed iteration $observed"
        break
    fi
    sleep .2
done
wait "$solver_pid"
grep -q '^Time = 1200$' log.simpleFoam
grep -q '^End$' log.simpleFoam
stamp reconstructPar
reconstructPar -time 1200 > log.reconstructPar 2>&1
stamp foamToVTK
foamToVTK -time 1200 -fields "$(cat vtkfields.txt)" > log.foamToVTK 2>&1
test -s VTK/"$(basename "$case_dir")"_1200/internal.vtu
stamp complete
