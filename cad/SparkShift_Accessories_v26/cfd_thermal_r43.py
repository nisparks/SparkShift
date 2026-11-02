"""Temperature analysis on a converged R43 airflow case (forced-convection heat transfer, not a thermal model
of the hotend itself).

Each case restarts from its converged 180 L/min airflow and solves compressible air with energy
(buoyantSimpleFoam, kOmegaSST, Jayatilleke thermal wall functions, Sutherland air, gravity on):
  * blower air enters at 35 C (enclosed chamber);
  * the bare nozzle below the sock (Z < -75.45 mm, within 4 mm of the axis) is held at 250 C;
  * the print surface is held at 210 C for r < 2 mm (fresh bead), falling linearly to 60 C at r 5 mm and
    60 C beyond (older layers);
  * every other wall, including the sock, is adiabatic.
The same temperatures are used for every design, so the comparison is like for like.

python cfd_thermal_r43.py prepare r43auditRC24fine_bambu_bed
python cfd_thermal_r43.py run r43auditRC24fine_bambu_bed --host user@host
Use --remote-root /mnt/models/sparkshift_cfd_thermal to run on the larger volume.
Up to two thermal jobs may overlap; non-thermal CFD jobs still block a new launch.
python cfd_thermal_r43.py analyse r43auditRC24fine_bambu_bed [more cases]
python cfd_thermal_r43.py render --tag TAG "Label=case" ...
"""
import argparse
import hashlib
import json
import shlex
import shutil
import subprocess
import tarfile
from pathlib import Path, PurePosixPath

import numpy as np

import cfd_cpap_r41 as C

ROOT = C.CFD / "thermal"
NOZZLE = (0.0, 0.0227)          # m
BED_Z, SOCK_Z = -0.07908, -0.07545
T_AIR, T_NOZZLE, T_BEAD, T_OLD = 308.15, 523.15, 483.15, 333.15
END, AVG_FROM, NP = 1400, 800, 46
SET = "SparkShift R43 thermal pass, written by cfd_thermal_r43.py"


def tname(case):
    return "r43therm_" + case.replace("r43audit", "").replace("_bambu_bed", "")


def foam(cls, obj, body):
    return (f"/* {SET} */\nFoamFile {{ version 2.0; format ascii; class {cls}; object {obj}; }}\n\n"
            + body.strip() + "\n")


R_EXPR = 'variables ( "r = sqrt(sqr(pos().x() - 0) + sqr(pos().y() - 0.0227))" );'

FIELDS = {
    "T": ("volScalarField", f"""
dimensions [0 0 0 1 0 0 0];
internalField uniform {T_AIR};
boundaryField
{{
    inlet {{ type fixedValue; value uniform {T_AIR}; }}
    ambient {{ type inletOutlet; inletValue uniform {T_AIR}; value uniform {T_AIR}; }}
    walls
    {{
        type exprMixed;
        {R_EXPR}
        valueExpr "{T_NOZZLE}";
        gradientExpr "0";
        fractionExpr "(pos().z() < {SOCK_Z} && r < 0.004) ? 1 : 0";
        value uniform {T_AIR};
    }}
    bed
    {{
        type exprFixedValue;
        {R_EXPR}
        valueExpr "(r < 0.002) ? {T_BEAD} : ((r < 0.005) ? ({T_BEAD} - {T_BEAD - T_OLD}*(r - 0.002)/0.003) : {T_OLD})";
        value uniform {T_OLD};
    }}
}}"""),
    "p": ("volScalarField", """
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 1e5;
boundaryField { ".*" { type calculated; value uniform 1e5; } }"""),
    "p_rgh": ("volScalarField", """
dimensions [1 -1 -2 0 0 0 0];
internalField uniform 1e5;
boundaryField
{
    inlet { type fixedFluxPressure; value uniform 1e5; }
    ambient { type prghTotalPressure; p0 uniform 1e5; value uniform 1e5; }
    "(walls|bed)" { type fixedFluxPressure; value uniform 1e5; }
}"""),
    "alphat": ("volScalarField", """
dimensions [1 -1 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{
    "(inlet|ambient)" { type calculated; value uniform 0; }
    "(walls|bed)" { type compressible::alphatJayatillekeWallFunction; Prt 0.85; value uniform 0; }
}"""),
}

CONTROL = f"""
application buoyantSimpleFoam;
startFrom latestTime; startTime 0; stopAt endTime; endTime {END}; deltaT 1;
writeControl timeStep; writeInterval {END}; purgeWrite 0; writeFormat binary; writePrecision 8;
writeCompression off; timeFormat general; timePrecision 6; runTimeModifiable false;
functions
{{
    residuals {{ type solverInfo; libs (utilityFunctionObjects); fields (U p_rgh h k omega); }}
    wallHeatFlux {{ type wallHeatFlux; libs (fieldFunctionObjects); patches (walls bed);
                   executeControl timeStep; writeControl writeTime; }}
    meanFields {{ type fieldAverage; libs (fieldFunctionObjects); timeStart {AVG_FROM}; restartOnRestart false;
                 writeControl writeTime;
                 fields ( U {{ mean on; prime2Mean off; base iteration; }}
                          T {{ mean on; prime2Mean off; base iteration; }}
                          wallHeatFlux {{ mean on; prime2Mean off; base iteration; }} ); }}
    sections
    {{
        type surfaces; libs (sampling); writeControl writeTime; surfaceFormat vtk;
        fields (TMean UMean); interpolationScheme cellPoint;
        surfaces
        {{
            bedPlus05 {{ type cuttingPlane; planeType pointAndNormal;
                        pointAndNormalDict {{ point (0 0.0227 {BED_Z + 0.0005}); normal (0 0 1); }}
                        bounds (-0.012 0.010 -0.0792) (0.012 0.036 -0.070); interpolate true; }}
            xSection  {{ type cuttingPlane; planeType pointAndNormal;
                        pointAndNormalDict {{ point (0 0.0227 0); normal (1 0 0); }}
                        bounds (-0.001 0.006 -0.0792) (0.001 0.040 -0.068); interpolate true; }}
            ySection  {{ type cuttingPlane; planeType pointAndNormal;
                        pointAndNormalDict {{ point (0 0.0227 0); normal (0 1 0); }}
                        bounds (-0.016 0.021 -0.0792) (0.016 0.024 -0.068); interpolate true; }}
        }}
    }}
}}"""

SCHEMES = """
ddtSchemes { default steadyState; }
gradSchemes { default cellLimited Gauss linear 1; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss linearUpwindV grad(U);
    turbulence bounded Gauss limitedLinear 1;
    div(phi,k) $turbulence;
    div(phi,omega) $turbulence;
    div(phi,h) bounded Gauss limitedLinear 1;
    div(phi,K) bounded Gauss linear;
    div(phi,Ekp) bounded Gauss linear;
    div(((rho*nuEff)*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited corrected 0.5; }
wallDist { method meshWave; }"""

SOLUTION = """
solvers
{
    p_rgh { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.01; }
    "(U|h|k|omega)" { solver smoothSolver; smoother GaussSeidel; tolerance 1e-8; relTol 0.1; nSweeps 1; }
}
SIMPLE { momentumPredictor yes; nNonOrthogonalCorrectors 1; }
relaxationFactors { fields { p_rgh 0.3; rho 1; } equations { U 0.7; h 0.5; k 0.5; omega 0.5; } }"""

THERMO = """
thermoType { type heRhoThermo; mixture pureMixture; transport sutherland; thermo hConst;
             equationOfState perfectGas; specie specie; energy sensibleEnthalpy; }
mixture
{
    specie { molWeight 28.96; }
    thermodynamics { Cp 1007; Hf 0; }
    transport { As 1.458e-06; Ts 110.4; }
}"""

RUNNER = r"""#!/bin/bash
source /usr/lib/openfoam/openfoam2512/etc/bashrc || exit 1
set -euo pipefail
case_dir=$(realpath "${1:?case}")
[[ "$case_dir" =~ ^/work/r43therm_[A-Za-z0-9_]+$ ]]
cd "$case_dir"
test ! -e log.run
sha256sum --quiet -c input_hashes.sha256
export OMPI_MCA_btl_vader_single_copy_mechanism=none
stamp() { echo "[$(date -u +%T)] $*" | tee -a log.run; }
stamp decomposePar
decomposePar -force > log.decomposePar 2>&1
stamp buoyantSimpleFoam
mpirun --bind-to none -np NPROC buoyantSimpleFoam -parallel > log.buoyantSimpleFoam 2>&1
grep -q '^End' log.buoyantSimpleFoam
stamp reconstructPar
reconstructPar -latestTime -fields '(T TMean wallHeatFlux wallHeatFluxMean)' > log.reconstructPar 2>&1
stamp foamToVTK
foamToVTK -latestTime -no-internal -patches '(walls bed)' -fields '(T TMean wallHeatFlux wallHeatFluxMean)' \
    > log.foamToVTK 2>&1
rm -rf processor*
stamp complete
""".replace("NPROC", str(NP))


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def prepare(case):
    src = C.results_dir(case)
    name = tname(case)
    case_dir = ROOT / name
    if case_dir.exists():
        raise FileExistsError(case_dir)
    (case_dir / "0").mkdir(parents=True)
    (case_dir / "system").mkdir()
    shutil.copytree(src / "constant" / "polyMesh", case_dir / "constant" / "polyMesh")
    for f in ("U", "k", "omega", "nut"):
        shutil.copy2(src / "1200" / f, case_dir / "0" / f)
    for f, (cls, body) in FIELDS.items():
        (case_dir / "0" / f).write_text(foam(cls, f, body), newline="\n")
    const = case_dir / "constant"
    (const / "thermophysicalProperties").write_text(foam("dictionary", "thermophysicalProperties", THERMO), newline="\n")
    (const / "g").write_text(foam("uniformDimensionedVectorField", "g",
                                  "dimensions [0 1 -2 0 0 0 0];\nvalue (0 0 -9.81);"), newline="\n")
    (const / "turbulenceProperties").write_text(foam("dictionary", "turbulenceProperties",
        "simulationType RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }"), newline="\n")
    sysd = case_dir / "system"
    (sysd / "controlDict").write_text(foam("dictionary", "controlDict", CONTROL), newline="\n")
    (sysd / "fvSchemes").write_text(foam("dictionary", "fvSchemes", SCHEMES), newline="\n")
    (sysd / "fvSolution").write_text(foam("dictionary", "fvSolution", SOLUTION), newline="\n")
    (sysd / "decomposeParDict").write_text(foam("dictionary", "decomposeParDict",
                                               f"numberOfSubdomains {NP};\nmethod scotch;"), newline="\n")
    files = sorted(p for p in case_dir.rglob("*") if p.is_file())
    hashes = {p.relative_to(case_dir).as_posix(): sha(p) for p in files}
    (case_dir / "input_hashes.sha256").write_text("".join(f"{v}  {k}\n" for k, v in hashes.items()), newline="\n")
    (case_dir / "source.json").write_text(json.dumps({"airflow_case": case, "airflow_U_sha256": hashes["0/U"]},
                                                    indent=2), newline="\n")
    archive = ROOT / f"{name}.tgz"
    with tarfile.open(archive, "w:gz", compresslevel=3) as tf:
        tf.add(case_dir, arcname=name)
    print(f"{name}: {len(files)} files, archive {archive.stat().st_size / 1e6:.0f} MB")


def ssh(host, cmd, **kw):
    return subprocess.run(["ssh", "-o", "ConnectTimeout=15", host, cmd], check=True, **kw)


def run(case, host, remote_root="sparkshift_cfd"):
    name = tname(case)
    archive, runner = ROOT / f"{name}.tgz", ROOT / "run_thermal_r43.sh"
    runner.write_text(RUNNER, newline="\n")
    out = ROOT / "results" / name
    if out.exists():
        expected = ROOT / name / "source.json"
        downloaded = out / "source.json"
        if (expected.is_file() and downloaded.is_file()
                and (out / "exit_code.txt").is_file() and (out / "log.run").is_file()
                and json.loads(expected.read_text()) == json.loads(downloaded.read_text())
                and (out / "exit_code.txt").read_text().strip() == "0"
                and list(out.glob(f"VTK/*_{END}/boundary/bed.vtp"))
                and list(out.glob(f"VTK/*_{END}/boundary/walls.vtp"))
                and any(line.endswith(" complete") for line in (out / "log.run").read_text().splitlines())):
            print(f"{name}: verified existing download; skipped")
            return
        raise FileExistsError(out)
    q = shlex.quote
    root = q(remote_root)
    ssh(host, f"mkdir -p {root} && cd {root} && test ! -e {q(name)} "
              f"&& test $(df --output=avail -k . | tail -1) -gt 4000000 "
              f"&& test $(docker ps --format '{{{{.Names}}}}' | grep -c '^sfth_' || true) -lt 2 "
              f"&& ! docker ps --format '{{{{.Names}}}}' | grep -E '^sf' | grep -v '^sfth_'")
    subprocess.run(["scp", "-q", str(archive), str(runner), f"{host}:{remote_root}/"], check=True)
    ssh(host, f"cd {root} && echo '{sha(archive)}  {name}.tgz' | sha256sum --quiet -c - && tar -xzf {q(name)}.tgz "
              f"&& rm {q(name)}.tgz && docker run -d --name sfth_{name} --shm-size=8g -v \"$(pwd):/work\" "
              f"--user $(id -u):$(id -g) -e HOME=/work --entrypoint bash opencfd/openfoam-default:2512 "
              f"/work/run_thermal_r43.sh /work/{name} && docker wait sfth_{name} > {q(name)}/exit_code.txt; "
              f"cat {q(name)}/exit_code.txt; tail -3 {q(name)}/log.run")
    code = ssh(host, f"cat {root}/{name}/exit_code.txt", capture_output=True, text=True).stdout.strip()
    if code != "0":
        ssh(host, f"docker logs --tail 30 sfth_{name}; tail -30 {root}/{name}/log.buoyantSimpleFoam")
        raise SystemExit(f"thermal run failed with exit {code}; remote case left for inspection")
    keep = "VTK postProcessing log.* exit_code.txt source.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    incoming = out.parent / f"{name}.tgz"
    with incoming.open("xb") as stream:
        ssh(host, f"cd {root}/{name} && tar -czf - {keep}", stdout=stream)
    out.mkdir()
    with tarfile.open(incoming) as tf:
        for m in tf.getmembers():
            p = PurePosixPath(m.name)
            if p.is_absolute() or ".." in p.parts or not (m.isfile() or m.isdir()):
                raise ValueError(f"unsafe member {m.name}")
        tf.extractall(out, filter="data")
    incoming.unlink()
    if not list(out.glob("VTK/**/bed.vtp")):
        raise SystemExit("download incomplete; remote case left in place")
    ssh(host, f"docker rm sfth_{name} > /dev/null && rm -rf {root}/{q(name)}")
    print(f"{name}: downloaded and remote case removed")


def read_vtp(path):
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    poly = reader.GetOutput()
    sizes = vtk.vtkCellSizeFilter()
    sizes.SetInputData(poly)
    sizes.SetComputeArea(True)
    sizes.Update()
    cen = vtk.vtkCellCenters()
    cen.SetInputData(poly)
    cen.Update()
    cells = sizes.GetOutput().GetCellData()
    data = {cells.GetArrayName(i): vtk_to_numpy(cells.GetArray(i)) for i in range(cells.GetNumberOfArrays())}
    data["xyz"] = vtk_to_numpy(cen.GetOutput().GetPoints().GetData())
    return data


def read_section(path):
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(str(path))
    reader.Update()
    c2p = vtk.vtkCellDataToPointData()
    c2p.SetInputData(reader.GetOutput())
    c2p.PassCellDataOff()
    tri = vtk.vtkTriangleFilter()
    tri.SetInputConnection(c2p.GetOutputPort())
    tri.Update()
    poly = tri.GetOutput()
    pts = vtk_to_numpy(poly.GetPoints().GetData())
    pd = poly.GetPointData()
    fields = {pd.GetArrayName(i): vtk_to_numpy(pd.GetArray(i)) for i in range(pd.GetNumberOfArrays())}
    tris = vtk_to_numpy(poly.GetPolys().GetData()).reshape(-1, 4)[:, 1:]
    return pts, tris, fields


def latest_vtk(out, patch):
    hits = sorted(out.glob(f"VTK/*_{END}/boundary/{patch}.vtp"))
    if not hits:
        raise FileNotFoundError(f"{out}: no {patch}.vtp at {END}")
    return hits[-1]


def zones(case):
    out = ROOT / "results" / tname(case)
    bed, walls = read_vtp(latest_vtk(out, "bed")), read_vtp(latest_vtk(out, "walls"))
    q_b, a_b = bed["wallHeatFluxMean"], bed["Area"]
    x, y = bed["xyz"][:, 0] - NOZZLE[0], bed["xyz"][:, 1] - NOZZLE[1]
    r = np.hypot(x, y) * 1e3
    tb = bed["T"] if "T" in bed else bed["TMean"]
    h = q_b / np.maximum(tb - T_AIR, 1e-6)
    ang = (np.degrees(np.arctan2(x, y)) + 360) % 360       # 0 = front (+Y), 90 = +X (right side of the printer)
    res = {"case": case, "thermal_case": tname(case)}
    for label, lo, hi in (("bead r 0.6-2 mm", .6, 2.), ("print r 2-5 mm", 2., 5.), ("print r 5-10 mm", 5., 10.)):
        m = (r >= lo) & (r < hi)
        sect = []
        for c in (0, 90, 180, 270):
            s = m & (((ang - c + 45) % 360) < 90)
            sect.append(float((h[s] * a_b[s]).sum() / a_b[s].sum()))
        res[label] = {"heat_removed_w": float((q_b[m] * a_b[m]).sum()),
                      "h_mean_w_m2k": float((h[m] * a_b[m]).sum() / a_b[m].sum()),
                      "h_sectors_front_right_rear_left": sect,
                      "h_weakest_over_mean": float(min(sect) / np.mean(sect))}
    xyz = walls["xyz"]
    rw = np.hypot(xyz[:, 0] - NOZZLE[0], xyz[:, 1] - NOZZLE[1])
    noz = (xyz[:, 2] < SOCK_Z) & (rw < 0.004)
    qn = walls["wallHeatFluxMean"]
    res["nozzle"] = {"heat_loss_w": float((qn[noz] * walls["Area"][noz]).sum()),
                     "area_mm2": float(walls["Area"][noz].sum() * 1e6),
                     "other_walls_w": float((qn[~noz] * walls["Area"][~noz]).sum())}
    sec = sorted(out.glob("postProcessing/sections/*/bedPlus05.vtp"), key=lambda p: float(p.parent.name))[-1]
    pts, tris, f = read_section(sec)
    rr = np.hypot(pts[:, 0] - NOZZLE[0], pts[:, 1] - NOZZLE[1]) * 1e3
    tm = f["TMean"]
    for label, lo, hi in (("air 0.5 mm above bead r 0.6-2 mm", .6, 2.), ("air 0.5 mm above print r 2-5 mm", 2., 5.)):
        m = (rr >= lo) & (rr < hi)
        res[label + " mean C"] = float(tm[m].mean() - 273.15)
    rows = [ln.split() for dat in sorted(out.glob("postProcessing/wallHeatFlux/*/wallHeatFlux.dat"))
            for ln in dat.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
    for patch in ("walls", "bed"):
        it = np.array([float(r_[0]) for r_ in rows if r_[1] == patch])
        q = np.array([float(r_[4]) for r_ in rows if r_[1] == patch])
        tail = q[it >= AVG_FROM]
        res[f"{patch}_total_w_avg_window"] = {"mean": float(tail.mean()), "std": float(tail.std()),
                                              "drift_last_200_vs_window": float(q[it > END - 200].mean() - tail.mean())}
    (out / "thermal_zones.json").write_text(json.dumps(res, indent=2), newline="\n")
    return res


def render(tag, pairs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.tri import Triangulation
    labels, cases = zip(*(p.split("=", 1) for p in pairs))
    res = [json.loads((ROOT / "results" / tname(c) / "thermal_zones.json").read_text()) for c in cases]
    n = len(cases)
    fig, ax = plt.subplots(3, n, figsize=(4.2 * n, 12.5), squeeze=False)
    for j, (lab, case) in enumerate(zip(labels, cases)):
        out = ROOT / "results" / tname(case)
        bed = read_vtp(latest_vtk(out, "bed"))
        x, y = (bed["xyz"][:, 0] - NOZZLE[0]) * 1e3, (bed["xyz"][:, 1] - NOZZLE[1]) * 1e3
        tb = bed["T"] if "T" in bed else bed["TMean"]
        h = bed["wallHeatFluxMean"] / np.maximum(tb - T_AIR, 1e-6)
        m = (np.abs(x) < 7) & (np.abs(y) < 7)
        sc = ax[0, j].tripcolor(Triangulation(x[m], y[m]), h[m], cmap="inferno", vmin=0, vmax=600, shading="gouraud")
        for rad in (.6, 2, 5):
            ax[0, j].add_patch(plt.Circle((0, 0), rad, fill=False, color="c", lw=.7, ls="--"))
        ax[0, j].set_aspect("equal")
        ax[0, j].set_title(f"{lab}\nprint heat-transfer coeff. h (W/m2K)", fontsize=9)
        ax[0, j].set_xlabel("X (mm)  - front is +Y (up)")
        fig.colorbar(sc, ax=ax[0, j], shrink=.75)
        for row, surf, (ia, ib), xl in ((1, "xSection", (1, 2), "Y - nozzle (mm), front right"),
                                        (2, "ySection", (0, 2), "X (mm)")):
            sec = sorted(out.glob(f"postProcessing/sections/*/{surf}.vtp"), key=lambda p: float(p.parent.name))[-1]
            pts, tris, f = read_section(sec)
            u = pts[:, ia] * 1e3 - (NOZZLE[1] * 1e3 if ia == 1 else 0)
            v = pts[:, ib] * 1e3
            t = Triangulation(u, v, tris)
            cs = ax[row, j].tripcolor(t, f["TMean"] - 273.15, cmap="coolwarm", vmin=35, vmax=120, shading="gouraud")
            ax[row, j].set_xlim(-8, 8)
            ax[row, j].set_ylim(-79.1, -72)
            ax[row, j].set_aspect("equal")
            ax[row, j].set_xlabel(xl)
            ax[row, j].set_title(("side section" if row == 1 else "front section") + ", air temperature (C)", fontsize=9)
            fig.colorbar(cs, ax=ax[row, j], shrink=.75)
        r = res[j]
        ax[0, j].text(-6.8, -6.8, f"bead h {r['bead r 0.6-2 mm']['h_mean_w_m2k']:.0f}, "
                      f"r2-5 h {r['print r 2-5 mm']['h_mean_w_m2k']:.0f}\n"
                      f"nozzle loss {r['nozzle']['heat_loss_w']:.2f} W", color="w", fontsize=8, va="bottom")
    fig.suptitle("Temperature analysis (forced convection, mean of iterations "
                 f"{AVG_FROM}-{END}): nozzle 250 C, fresh bead 210 C to 60 C at r 5 mm, air 35 C", fontsize=11)
    fig.tight_layout()
    path = Path(__file__).with_name("images") / f"r43_thermal_{tag}.png"
    fig.savefig(path, dpi=110)
    report = {"tag": tag, "boundary_conditions": {"air_c": T_AIR - 273.15, "nozzle_c": T_NOZZLE - 273.15,
              "bead_c": T_BEAD - 273.15, "old_print_c": T_OLD - 273.15, "bead_radius_mm": 2, "ramp_to_mm": 5,
              "other_walls": "adiabatic (sock included)", "solver": "buoyantSimpleFoam v2512, kOmegaSST, "
              "alphatJayatillekeWallFunction Prt 0.85, Sutherland air, hConst Cp 1007, gravity on",
              "averaging": f"iterations {AVG_FROM}-{END}"},
              "cases": {lab: r for lab, r in zip(labels, res)}}
    Path(__file__).with_name(f"verification_thermal_r43_{tag}.json").write_text(json.dumps(report, indent=2),
                                                                                  newline="\n")
    print(path)


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("prepare").add_argument("cases", nargs="+")
    r = sub.add_parser("run")
    r.add_argument("cases", nargs="+")
    r.add_argument("--host", required=True)
    r.add_argument("--remote-root", default="sparkshift_cfd",
                   help="Remote case directory (relative to home or absolute); must have at least 4 GB free")
    sub.add_parser("analyse").add_argument("cases", nargs="+")
    rd = sub.add_parser("render")
    rd.add_argument("--tag", required=True)
    rd.add_argument("pairs", nargs="+")
    a = ap.parse_args()
    if a.cmd == "prepare":
        for c in a.cases:
            prepare(c)
    elif a.cmd == "run":
        for c in a.cases:
            run(c, a.host, a.remote_root)
    elif a.cmd == "analyse":
        for c in a.cases:
            z = zones(c)
            print(json.dumps({k: (v if not isinstance(v, dict) else {kk: vv for kk, vv in v.items()
                                                                       if not isinstance(vv, list)})
                              for k, v in z.items()}, indent=1))
    else:
        render(a.tag, a.pairs)
