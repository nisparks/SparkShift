"""Revision 41: CFD of the CPAP duct (P20 -> P21 -> P22) with OpenFOAM, steady RANS with k-omega SST turbulence.

The air solved for: the inside of P20, P21 and P22 from the hose spigot to the two jets beside the nozzle, a
straight hose section of four bores upstream of the spigot, and the open air around the nozzle (box OUTLET) with
the mounted tool, P22's outside, P01, P23, the Beacon and the screws in it as obstacles. Its faces are open to the
room (total pressure 0), except an optional print surface 0.2 mm under the nozzle tip.

Turbulence: k-omega SST; at the inlet 5 % intensity and a mixing length of 0.07 x the 16.4 mm bore. Walls use
y+-insensitive wall functions (nutUSpalding, omega blended). Air at 20 C (nu 1.5e-5 m2/s, rho 1.2 kg/m3).
The inlet flow steps through several rates in one run (time = iteration), giving the duct's system curve, which
is set against the WS7040 blower's published P-Q curve and an allowance for 1 m of CPAP hose.

Steps, each under WORK/cfd:
  python cfd_cpap_r41.py domain <name> [--duct r41|released] [--tool Bambu|RedLizard] [--bed] [--p22 square|<brep>]
                                       [--leave-out <name prefix>,...]
  python cfd_cpap_r41.py case <name> [--flows 180,120,240] [--interval 600] [--np 20] [--wall-levels "1 2"]
  run cases/<name> with cfd/run_case.sh (native OpenFOAM v2512+), or cfd/launch_docker.sh (opencfd/openfoam-default)
  copy the case's VTK/ and postProcessing/ to results/<name>, then
  python cfd_cpap_r41.py analyse <name>
  python cfd_cpap_r41.py report <name> [<name> ...]   -> verification_cfd_cpap_r41.json
"""
import argparse
import json
import math
import shutil
import sys
import time
from pathlib import Path

import cadquery as cq
import numpy as np
from OCP.BRep import BRep_Tool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.TopAbs import TopAbs_REVERSED
from OCP.TopLoc import TopLoc_Location

import build_and_verify_accessories_v26 as acc
import r37_parts as P37
import r40_parts as P40
import r41_parts as R
from audit_tool_owned_2510 import bounds
from build_modular_toolhead import ROOT, box, load

CFD = acc.WORK / "cfd"
SCENE = acc.WORK / "r41_scene"           # written by build_carriage_fixes_r41.py
REPORT = "verification_cfd_cpap_r41.json"

# geometry (mm)
SPIGOT = (0.0, -48.5, 8.2)               # P20's bore at the hose spigot: centre X, Y and radius (211 mm2)
EXT = (29.0, 4 * 16.4)                   # hose section: from Z29.0 inside the spigot, four bores long
NOZZLE_TIP_Z, NOZZLE_Y = -78.88, 22.7
OUTLET = (-30.0, 30.0, -20.0, 50.0, -95.0, -45.0)   # open air around the nozzle
BED_GAP = 0.2                            # print surface under the nozzle tip, one layer
JET_X = 10.3                             # just inside each jet's exit (the hotend slot's wall is at |X| 10.2)
JET_WINDOW = (16.5, 29.0, -77.2, -73.3)  # Y and Z of the jet passages at |X| 10.3, no outside air

# physics
NU, RHO, INTENSITY = 1.5e-5, 1.2, 0.05
BASE = 1.0e-3                            # background cell (m): level 1 = 0.5 mm, level 2 = 0.25 mm
# WS7040-24-V200 at 100 % PWM (Wonsmart's P-Q curve, digitised): m3/h -> kPa static pressure
BLOWER = [(0, 6.75), (2, 6.4), (4, 6.0), (6, 5.45), (8, 4.5), (9, 4.25), (10, 4.0), (11, 3.6), (12, 3.3),
          (13, 3.05), (14, 2.6), (15, 2.3), (16, 2.0), (17, 1.75), (18, 1.45), (18.5, 1.0), (19, 0.6), (20, 0.25),
          (21.2, 0.0)]
HOSE = {"length_m": 1.0, "bore_mm": 19.0, "darcy_f": 0.06}   # a standard corrugated CPAP hose (an allowance)


# ===================================================================================== scene
def manifest():
    return json.loads((SCENE / "manifest.json").read_text())


def brep(fname):
    return cq.Shape.importBrep(str(SCENE / fname))


def variant_parts(label):
    return [(n, brep(f)) for n, f in manifest()["variants"][label]["parts"]]


def fuse_all(shapes):
    return R.shape(acc.fuse_all([s.wrapped if isinstance(s, cq.Shape) else s for s in shapes]))


def cut_all(base, cutters):
    return R.shape(acc.cut_all(base.wrapped if isinstance(base, cq.Shape) else base,
                               [c.wrapped if isinstance(c, cq.Shape) else c for c in cutters]))


def overlaps_box(b, o):
    return b[1] > o[0] and b[0] < o[1] and b[3] > o[2] and b[2] < o[3] and b[5] > o[4] and b[4] < o[5]


def solid_containing(shape, point):
    for s in shape.Solids():
        if s.isInside(cq.Vector(*point)):
            return s
    return None


# ===================================================================================== fluid domain
def duct_parts(duct, p22=None):
    if duct == "r41":
        c = dict(manifest()["carriage"])
        parts = [brep(c[R.NAMES[k]]) for k in ("p20", "p21", "p22")]
    else:
        parts = [load(P40.NAMES["p20"]), load(P40.NAMES["p21"]), P37.p22()[0]]
    if p22 == "square":
        parts[2] = R.p22(bell_mouth=False)                  # revision 41's first, square-edged jets
    elif p22 is not None:
        parts[2] = cq.Shape.importBrep(str(p22))           # a P22 variant (BREP), with the same P20 and P21
    return parts


def obstacles(duct, tool, outlet, leave_out=()):
    """Every carriage solid and tool part reaching into the outlet box, except the duct itself and any carriage part
    whose name starts with one of `leave_out` (a P22 variant that takes over P23, say)."""
    skip = {R.NAMES["p20"], R.NAMES["p21"], R.NAMES["p22"]}
    out = []
    for n, f in manifest()["carriage"]:
        if n in skip or (duct != "r41" and n.startswith("R41_P22_P01")) or n.startswith(tuple(leave_out)):
            continue
        s = brep(f)
        if overlaps_box(bounds(s), outlet):
            out.append((n, s))
    if duct != "r41":                                        # the released duct's own socket heads
        out += [(n, R.shape(s)) for n, s in P37.other_hardware() if n.startswith("ACC_CASE_BOSS_M3x10_")]
    out += [(f"{tool}:{n}", s) for n, s in variant_parts(tool) if overlaps_box(bounds(s), outlet)]
    return out


def fluid_domain(duct, tool, bed, p22=None, leave_out=()):
    o = list(OUTLET)
    if bed:
        o[4] = NOZZLE_TIP_Z - BED_GAP
    d = fuse_all(duct_parts(duct, p22))
    cx, cy, r = SPIGOT
    inlet_point = (cx, cy, 20.0)
    # the duct's own air: close the spigot mouth, fill the outlet box, keep the pocket at the inlet
    cap = R.shape(acc.cyl_z(cx, cy, EXT[0], 31.0, r + 2.5))
    cavity = solid_containing(cut_all(box(-40, 40, -70, 60, -110, 45), [d, cap, box(*o)]), inlet_point)
    cb = bounds(cavity)
    if cb[0] < -39 or cb[1] > 39 or cb[2] < -69 or cb[5] > 44:
        raise RuntimeError("the duct's air leaks to the outside")
    obs = obstacles(duct, tool, o, leave_out)
    air = cut_all(box(*o), [d] + [s for _, s in obs])
    fluid = fuse_all([cavity, R.shape(acc.cyl_z(cx, cy, EXT[0], EXT[0] + EXT[1], r)), air])
    main = solid_containing(fluid, inlet_point)
    dropped = [round(s.Volume(), 2) for s in fluid.Solids() if not s.isSame(main)]
    return main, o, [n for n, _ in obs], dropped, cavity.Volume()


def patch_faces(fluid, o, z_top, bed):
    planes = [("x", o[0]), ("x", o[1]), ("y", o[2]), ("y", o[3]), ("z", o[4]), ("z", o[5])]
    groups = {"inlet": [], "ambient": [], "walls": [], "bed": []}
    for f in fluid.Faces():
        b = bounds(f)
        name = "walls"
        if f.geomType() == "PLANE":
            if abs(b[4] - z_top) < 1e-6 and abs(b[5] - z_top) < 1e-6:
                name = "inlet"
            for axis, v in planes:
                i = "xyz".index(axis)
                if name == "walls" and abs(b[2 * i] - v) < 1e-6 and abs(b[2 * i + 1] - v) < 1e-6:
                    name = "bed" if (bed and axis == "z" and v == o[4]) else "ambient"
        groups[name].append(f)
    return groups


def write_stl(fluid, groups, path, lin=0.01, ang=0.25):
    """One ASCII STL in metres, a solid per patch, triangulated once so the patches share their edges."""
    BRepMesh_IncrementalMesh(fluid.wrapped, lin, False, ang, True)
    counts = {}
    with open(path, "w", newline="\n") as fh:
        for name, faces in groups.items():
            if not faces:
                continue
            fh.write(f"solid {name}\n")
            n = 0
            for f in faces:
                loc = TopLoc_Location()
                tri = BRep_Tool.Triangulation_s(f.wrapped, loc)
                trsf = loc.Transformation()
                pts = [tri.Node(i).Transformed(trsf) for i in range(1, tri.NbNodes() + 1)]
                rev = f.wrapped.Orientation() == TopAbs_REVERSED
                for k in range(1, tri.NbTriangles() + 1):
                    i1, i2, i3 = tri.Triangle(k).Get()
                    if rev:
                        i2, i3 = i3, i2
                    p = [np.array([q.X(), q.Y(), q.Z()]) for q in (pts[i1 - 1], pts[i2 - 1], pts[i3 - 1])]
                    nrm = np.cross(p[1] - p[0], p[2] - p[0])
                    nrm = nrm / (np.linalg.norm(nrm) or 1.0)
                    fh.write(f" facet normal {nrm[0]:.6e} {nrm[1]:.6e} {nrm[2]:.6e}\n  outer loop\n")
                    for q in p:
                        fh.write(f"   vertex {q[0] * 1e-3:.9e} {q[1] * 1e-3:.9e} {q[2] * 1e-3:.9e}\n")
                    fh.write("  endloop\n endfacet\n")
                    n += 1
            fh.write(f"endsolid {name}\n")
            counts[name] = n
    return counts


def build_domain(name, duct, tool, bed, p22=None, leave_out=()):
    t0 = time.perf_counter()
    out = CFD / "domains" / name
    out.mkdir(parents=True, exist_ok=True)
    fluid, o, obs, dropped, cavity = fluid_domain(duct, tool, bed, p22, leave_out)
    z_top = EXT[0] + EXT[1]
    groups = patch_faces(fluid, o, z_top, bed)
    areas = {k: round(sum(f.Area() for f in v), 2) for k, v in groups.items()}
    if abs(areas["inlet"] - math.pi * SPIGOT[2] ** 2) > 0.5:
        raise RuntimeError(f"inlet area {areas['inlet']}")
    counts = write_stl(fluid, groups, out / "domain.stl")
    cx, cy, r = SPIGOT
    meta = {"duct": duct, "tool": tool, "bed": bed, "p22_variant": str(p22) if p22 else None,
            "left_out": list(leave_out), "outlet_box_mm": o,
            "inlet": {"centre_mm": [cx, cy, z_top], "radius_mm": r, "area_mm2": areas["inlet"]},
            "location_in_mesh_m": [cx * 1e-3, cy * 1e-3, (EXT[0] + 10.0) * 1e-3],
            "bounds_mm": [round(v, 3) for v in bounds(fluid)], "volume_mm3": round(fluid.Volume(), 1),
            "duct_air_mm3": round(cavity, 1), "patch_areas_mm2": areas, "triangles": counts, "obstacles": obs,
            "dropped_pockets_mm3": dropped, "nozzle_tip_z_mm": NOZZLE_TIP_Z,
            "seconds": round(time.perf_counter() - t0, 1)}
    (out / "domain.json").write_text(json.dumps(meta, indent=1))
    return meta


# ===================================================================================== OpenFOAM case
FOAM_HEADER = """/*--------------------------------*- C++ -*----------------------------------*\\
  SparkShift CPAP duct CFD, written by cfd_cpap_r41.py
\\*---------------------------------------------------------------------------*/
FoamFile {{ version 2.0; format ascii; class {cls}; object {obj}; }}
"""


def foam(path, obj, body, cls="dictionary"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(FOAM_HEADER.format(cls=cls, obj=obj) + body, newline="\n")


def inlet_turbulence(lpm, area_mm2, d_mm):
    u = lpm / 60000.0 / (area_mm2 * 1e-6)
    k = 1.5 * (INTENSITY * u) ** 2
    lm = 0.07 * d_mm * 1e-3
    return u, k, math.sqrt(k) / (0.09 ** 0.25 * lm), lm


def write_case(name, flows, interval, upwind, np_, wall_levels="1 2", zone_level=2, domain=None, roughness_mm=0.0):
    dom = CFD / "domains" / (domain or name)
    case = CFD / "cases" / name
    meta = json.loads((dom / "domain.json").read_text())
    iters = [2 * interval] + [interval] * (len(flows) - 1)
    if case.exists():
        shutil.rmtree(case)
    (case / "constant" / "triSurface").mkdir(parents=True)
    shutil.copy(dom / "domain.stl", case / "constant" / "triSurface" / "domain.stl")
    shutil.copy(dom / "domain.json", case / "domain.json")
    pad = 1.5e-3
    b = [v * 1e-3 for v in meta["bounds_mm"]]
    lo = [b[0] - pad, b[2] - pad, b[4] - pad]
    n = [math.ceil((b[2 * i + 1] + pad - lo[i]) / BASE) for i in range(3)]
    hi = [lo[i] + n[i] * BASE for i in range(3)]
    v = [(lo[0], lo[1], lo[2]), (hi[0], lo[1], lo[2]), (hi[0], hi[1], lo[2]), (lo[0], hi[1], lo[2]),
         (lo[0], lo[1], hi[2]), (hi[0], lo[1], hi[2]), (hi[0], hi[1], hi[2]), (lo[0], hi[1], hi[2])]
    foam(case / "system" / "blockMeshDict", "blockMeshDict", f"""
scale 1;
vertices ( {' '.join(f'({x:.6f} {y:.6f} {z:.6f})' for x, y, z in v)} );
blocks ( hex (0 1 2 3 4 5 6 7) ({n[0]} {n[1]} {n[2]}) simpleGrading (1 1 1) );
edges ();
boundary ( background {{ type patch; faces ( (0 3 2 1) (4 5 6 7) (0 1 5 4) (2 3 7 6) (0 4 7 3) (1 2 6 5) ); }} );
mergePatchPairs ();
""")
    foam(case / "system" / "surfaceFeatureExtractDict", "surfaceFeatureExtractDict", """
domain.stl
{
    extractionMethod    extractFromSurface;
    includedAngle       150;
    subsetFeatures { nonManifoldEdges no; openEdges yes; }
    writeObj            no;
}
""")
    loc = meta["location_in_mesh_m"]
    loc = [loc[0] + 0.37e-3, loc[1] + 0.23e-3, loc[2] + 0.13e-3]     # off the background mesh's planes
    tip = meta["nozzle_tip_z_mm"] * 1e-3
    bed = meta["bed"]
    bed_region = " bed { name bed; }" if bed else ""
    bed_level = "\n                bed     { level (2 2); patchInfo { type wall; } }" if bed else ""
    foam(case / "system" / "snappyHexMeshDict", "snappyHexMeshDict", f"""
castellatedMesh true;
snap            true;
addLayers       false;

geometry
{{
    domain.stl
    {{
        type triSurfaceMesh;
        name domain;
        regions {{ inlet {{ name inlet; }} ambient {{ name ambient; }} walls {{ name walls; }}{bed_region} }}
    }}
    nozzleZone {{ type box; min (-0.0160 0.0120 {tip - 0.0050:.5f}); max (0.0160 0.0330 {tip + 0.0090:.5f}); }}
}}

castellatedMeshControls
{{
    maxLocalCells       4000000;
    maxGlobalCells      20000000;
    minRefinementCells  10;
    maxLoadUnbalance    0.10;
    nCellsBetweenLevels 3;
    features ( {{ file "domain.eMesh"; level 2; }} );
    refinementSurfaces
    {{
        domain
        {{
            level (1 1);
            regions
            {{
                inlet   {{ level (1 1); patchInfo {{ type patch; }} }}
                ambient {{ level (0 0); patchInfo {{ type patch; }} }}
                walls   {{ level ({wall_levels}); patchInfo {{ type wall; }} }}{bed_level}
            }}
        }}
    }}
    resolveFeatureAngle 30;
    refinementRegions {{ nozzleZone {{ mode inside; levels ((1e15 {zone_level})); }} }}
    locationInMesh ({loc[0]:.6f} {loc[1]:.6f} {loc[2]:.6f});
    allowFreeStandingZoneFaces true;
}}

snapControls
{{
    nSmoothPatch 3; tolerance 2.0; nSolveIter 50; nRelaxIter 5; nFeatureSnapIter 10;
    implicitFeatureSnap false; explicitFeatureSnap true; multiRegionFeatureSnap true;
}}

addLayersControls
{{
    relativeSizes true; layers {{ }} expansionRatio 1.2; finalLayerThickness 0.5; minThickness 0.1; nGrow 0;
    featureAngle 60; nRelaxIter 3; nSmoothSurfaceNormals 1; nSmoothNormals 3; nSmoothThickness 10;
    maxFaceThicknessRatio 0.5; maxThicknessToMedialRatio 0.3; minMedialAxisAngle 90; nBufferCellsNoExtrude 0;
    nLayerIter 50;
}}

meshQualityControls
{{
    #includeEtc "caseDicts/meshQualityDict"
    relaxed {{ maxNonOrtho 75; }}
    nSmoothScale 4;
    errorReduction 0.75;
}}

mergeTolerance 1e-6;
""")
    foam(case / "system" / "decomposeParDict", "decomposeParDict", f"\nnumberOfSubdomains {np_};\nmethod scotch;\n")
    foam(case / "system" / "meshQualityDict", "meshQualityDict", '\n#includeEtc "caseDicts/meshQualityDict"\n')
    # first-order upwind until `upwind`, then the runner swaps in the second-order schemes
    schemes = """
ddtSchemes { default steadyState; }
gradSchemes { default cellLimited Gauss linear 1; }
divSchemes
{
    default none;
    div(phi,U) bounded Gauss %s;
    turbulence bounded Gauss %s;
    div(phi,k) $turbulence;
    div(phi,omega) $turbulence;
    div((nuEff*dev2(T(grad(U))))) Gauss linear;
}
laplacianSchemes { default Gauss linear limited corrected 0.5; }
interpolationSchemes { default linear; }
snGradSchemes { default limited corrected 0.5; }
wallDist { method meshWave; }
"""
    for fname, pair in (("fvSchemes", ("upwind", "upwind")), ("fvSchemes.first", ("upwind", "upwind")),
                        ("fvSchemes.second", ("linearUpwindV grad(U)", "limitedLinear 1"))):
        foam(case / "system" / fname, "fvSchemes", schemes % pair)
    foam(case / "system" / "fvSolution", "fvSolution", """
solvers
{
    p { solver GAMG; smoother GaussSeidel; tolerance 1e-7; relTol 0.01; }
    Phi { $p; }
    "(U|k|omega)" { solver smoothSolver; smoother GaussSeidel; tolerance 1e-8; relTol 0.1; nSweeps 1; }
}
SIMPLE { nNonOrthogonalCorrectors 1; consistent no; }
potentialFlow { nNonOrthogonalCorrectors 10; }
relaxationFactors { fields { p 0.3; } equations { U 0.7; k 0.5; omega 0.5; } }
cache { grad(U); }
""")
    total = sum(iters)
    foam(case / "system" / "controlDict", "controlDict", f"""
application     simpleFoam;
startFrom       latestTime;
startTime       0;
stopAt          endTime;
endTime         {total};
deltaT          1;
writeControl    timeStep;
writeInterval   {interval};
purgeWrite      0;
writeFormat     binary;
writePrecision  8;
writeCompression off;
timeFormat      general;
timePrecision   6;
runTimeModifiable true;

functions
{{
    pTotal   {{ type pressure; libs (fieldFunctionObjects); mode total; rho rhoInf; rhoInf 1; result pTotal;
               writeControl writeTime; }}
    inletAvg {{ type surfaceFieldValue; libs (fieldFunctionObjects); regionType patch; name inlet;
               operation areaAverage; fields (p pTotal); writeFields false; log false;
               writeControl timeStep; writeInterval 5; }}
    flows    {{ type surfaceFieldValue; libs (fieldFunctionObjects); regionType patch; name ambient;
               operation sum; fields (phi); writeFields false; log false; writeControl timeStep; writeInterval 5; }}
    residuals {{ type solverInfo; libs (utilityFunctionObjects); fields (U p k omega); }}
    yPlus    {{ type yPlus; libs (fieldFunctionObjects); writeControl writeTime; log false; }}
}}
""")
    foam(case / "constant" / "transportProperties", "transportProperties", f"\ntransportModel  Newtonian;\nnu {NU};\n")
    foam(case / "constant" / "turbulenceProperties", "turbulenceProperties",
         "\nsimulationType  RAS;\nRAS { RASModel kOmegaSST; turbulence on; printCoeffs on; }\n")
    area, d = meta["inlet"]["area_mm2"], 2 * meta["inlet"]["radius_mm"]
    _, k0, w0, lm = inlet_turbulence(flows[0], area, d)
    kamb, wamb = 1.5e-4, 22.0                     # the room: about 1 % of 1 m/s, 1 mm eddies
    table, t = [], 0
    for i, (q, it) in enumerate(zip(flows, iters)):
        table.append((t + (0.5 if i else 0), q / 60000.0))
        t += it
        table.append((t, q / 60000.0))
    table_s = " ".join(f"({tt:g} {qq:.8e})" for tt, qq in table)
    zero, walls = case / "0.orig", '"(walls|bed)"'
    constraint = '    #includeEtc "caseDicts/setConstraintTypes"\n'
    foam(zero / "U", "U", f"""
dimensions [0 1 -1 0 0 0 0];
internalField uniform (0 0 0);
boundaryField
{{
{constraint}    inlet {{ type flowRateInletVelocity; volumetricFlowRate table ( {table_s} ); extrapolateProfile no;
             value uniform (0 0 0); }}
    ambient {{ type pressureInletOutletVelocity; value uniform (0 0 0); }}
    {walls} {{ type noSlip; }}
    background {{ type zeroGradient; }}
}}
""", "volVectorField")
    foam(zero / "p", "p", f"""
dimensions [0 2 -2 0 0 0 0];
internalField uniform 0;
boundaryField
{{
{constraint}    inlet {{ type zeroGradient; }}
    ambient {{ type totalPressure; p0 uniform 0; value uniform 0; }}
    {walls} {{ type zeroGradient; }}
    background {{ type zeroGradient; }}
}}
""", "volScalarField")
    foam(zero / "k", "k", f"""
dimensions [0 2 -2 0 0 0 0];
internalField uniform {kamb};
boundaryField
{{
{constraint}    inlet {{ type turbulentIntensityKineticEnergyInlet; intensity {INTENSITY}; value uniform {k0:.6e}; }}
    ambient {{ type inletOutlet; inletValue uniform {kamb}; value uniform {kamb}; }}
    {walls} {{ type kqRWallFunction; value uniform {kamb}; }}
    background {{ type zeroGradient; }}
}}
""", "volScalarField")
    foam(zero / "omega", "omega", f"""
dimensions [0 0 -1 0 0 0 0];
internalField uniform {wamb};
boundaryField
{{
{constraint}    inlet {{ type turbulentMixingLengthFrequencyInlet; mixingLength {lm:.6e}; value uniform {w0:.6e}; }}
    ambient {{ type inletOutlet; inletValue uniform {wamb}; value uniform {wamb}; }}
    {walls} {{ type omegaWallFunction; value uniform {wamb}; }}
    background {{ type zeroGradient; }}
}}
""", "volScalarField")
    # smooth walls, or FDM layer ridges as an equivalent sand-grain roughness (all walls, the hotend included)
    nut_wall = ("nutUSpaldingWallFunction; value uniform 0;" if not roughness_mm else
                f"nutkRoughWallFunction; Ks uniform {roughness_mm * 1e-3:.6e}; Cs uniform 0.5; value uniform 0;")
    foam(zero / "nut", "nut", f"""
dimensions [0 2 -1 0 0 0 0];
internalField uniform 0;
boundaryField
{{
{constraint}    inlet {{ type calculated; value uniform 0; }}
    ambient {{ type calculated; value uniform 0; }}
    {walls} {{ type {nut_wall} }}
    background {{ type calculated; value uniform 0; }}
}}
""", "volScalarField")
    stages, t = [], 0
    for q, it in zip(flows, iters):
        t += it
        stages.append({"lpm": q, "end": t, "inlet_velocity_ms": round(inlet_turbulence(q, area, d)[0], 3)})
    (case / "stages.json").write_text(json.dumps({"np": np_, "stages": stages, "nu": NU, "rho": RHO,
                                                   "intensity": INTENSITY, "mixing_length_m": lm,
                                                   "wall_levels": wall_levels, "zone_level": zone_level,
                                                   "wall_roughness_mm": roughness_mm, "background_cells": n}, indent=1))
    for fname, text in (("np.txt", f"{np_}\n"), ("upwind.txt", f"{upwind}\n"),
                        ("times.txt", ",".join(str(s["end"]) for s in stages) + "\n")):
        (case / fname).write_text(text, newline="\n")
    return case


# ===================================================================================== analysis
def blower_pa(lpm):
    q = np.array([p[0] for p in BLOWER]) * 1000 / 60
    return np.interp(lpm, q, np.array([p[1] for p in BLOWER]) * 1000)


def hose_pa(lpm, h=HOSE):
    a = math.pi / 4 * (h["bore_mm"] * 1e-3) ** 2
    v = lpm / 60000 / a
    return h["darcy_f"] * h["length_m"] / (h["bore_mm"] * 1e-3) * 0.5 * RHO * v * v


def fit_power(rows):
    q = np.array([r["lpm"] for r in rows])
    p = np.array([r["inlet_total_pa"] for r in rows])
    n, lnc = np.polyfit(np.log(q), np.log(p), 1)
    return math.exp(lnc), float(n)


def operating_point(rows, hose=True):
    c, n = fit_power(rows)
    lo, hi = 1.0, 354.0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        if blower_pa(mid) - (hose_pa(mid) if hose else 0.0) - c * mid ** n > 0:
            lo = mid
        else:
            hi = mid
    q = 0.5 * (lo + hi)
    return {"lpm": round(q, 1), "duct_pa": round(c * q ** n), "hose_pa": round(hose_pa(q)) if hose else 0,
            "blower_pa": round(float(blower_pa(q))), "fit_pa": {"c": round(c, 6), "n": round(n, 3)}}


def results_dir(name):
    return CFD / "results" / name


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)
    d = sub.add_parser("domain")
    d.add_argument("name")
    d.add_argument("--duct", default="r41", choices=("r41", "released"))
    d.add_argument("--tool", default="Bambu", choices=("Bambu", "RedLizard"))
    d.add_argument("--bed", action="store_true")
    d.add_argument("--p22", help="'square' for revision 41's first, square-edged jets, or a BREP of a P22 variant, "
                                 "instead of the scene's P22")
    d.add_argument("--leave-out", default="", help="comma-separated name prefixes of carriage parts to leave out of "
                                                   "the obstacles (a P22 variant that takes over P23, say)")
    c = sub.add_parser("case")
    c.add_argument("name")
    c.add_argument("--domain")
    c.add_argument("--flows", default="180,120,240")
    c.add_argument("--interval", type=int, default=600)
    c.add_argument("--upwind", type=int, default=300)
    c.add_argument("--np", type=int, default=20)
    c.add_argument("--wall-levels", default="1 2")
    c.add_argument("--zone-level", type=int, default=2)
    c.add_argument("--roughness-mm", type=float, default=0.0, help="equivalent sand-grain roughness of the walls")
    a_ = sub.add_parser("analyse")
    a_.add_argument("name")
    r_ = sub.add_parser("report")
    r_.add_argument("names", nargs="+")
    a = p.parse_args()
    if a.cmd == "domain":
        leave_out = tuple(s for s in a.leave_out.split(",") if s)
        print(json.dumps(build_domain(a.name, a.duct, a.tool, a.bed, a.p22, leave_out), indent=1))
    elif a.cmd == "case":
        print(write_case(a.name, [float(v) for v in a.flows.split(",")], a.interval, a.upwind, a.np,
                         a.wall_levels, a.zone_level, a.domain, a.roughness_mm))
    elif a.cmd == "analyse":
        import cfd_cpap_r41_post as post
        out = post.analyse_case(a.name)
        print(json.dumps([{k: r[k] for k in ("lpm", "inlet_total_pa", "jets_sum_lpm")} for r in out], indent=1))
    elif a.cmd == "report":
        import cfd_cpap_r41_post as post
        report = post.report(a.names)
        (ROOT / REPORT).write_text(json.dumps(report, indent=2, default=str) + "\n")
        print(json.dumps(report["operating_points"], indent=1))


if __name__ == "__main__":
    sys.exit(main())
