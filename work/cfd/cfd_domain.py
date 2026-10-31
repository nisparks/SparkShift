"""Fluid domain for the CPAP duct CFD (session scratch while developing; ported to the repo once it works).

The air the CFD solves for:
  * the inside of P20 -> P21 -> P22, from the hose spigot to the jets beside the nozzle;
  * a straight hose section upstream of the spigot (bore Ø16.4, 4 diameters) so the inflow can develop;
  * the open air around the nozzle (box OUTLET) with the mounted tool, P22's outside, P01, P23, the Beacon and
    the screws as obstacles. Its faces are open to the room, except an optional print surface under the nozzle.

Built from the verified revision-41 scene (WORK/r41_scene), or the released P20/P21/P22 for comparison.
Writes <out>/domain.stl (metres; solids inlet, ambient, walls[, bed]) and <out>/domain.json.
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cfd_scene import *  # noqa: E402,F403

import r40_parts as P40  # noqa: E402
from build_modular_toolhead import box, load  # noqa: E402
from OCP.BRep import BRep_Tool  # noqa: E402
from OCP.BRepMesh import BRepMesh_IncrementalMesh  # noqa: E402
from OCP.TopAbs import TopAbs_REVERSED  # noqa: E402
from OCP.TopLoc import TopLoc_Location  # noqa: E402

SPIGOT = (0.0, -48.5, 8.2)          # bore centre X, Y and radius (Ø16.4 = 211 mm2)
EXT = (29.0, 4 * 16.4)              # hose section: starts inside the spigot bore at Z29.0, 4 D long
NOZZLE_TIP_Z = -78.88
OUTLET = (-30.0, 30.0, -20.0, 50.0, -95.0, -45.0)   # open air around the nozzle (mm)
BED_GAP = 0.2                       # print surface this far below the nozzle tip (one layer)


def fuse_all(shapes):
    return R.shape(acc.fuse_all([s.wrapped if isinstance(s, cq.Shape) else s for s in shapes]))


def cut_all(base, cutters):
    return R.shape(acc.cut_all(base.wrapped if isinstance(base, cq.Shape) else base,
                               [c.wrapped if isinstance(c, cq.Shape) else c for c in cutters]))


def overlaps_box(b, o, pad=0.0):
    return b[1] > o[0] - pad and b[0] < o[1] + pad and b[3] > o[2] - pad and b[2] < o[3] + pad and \
        b[5] > o[4] - pad and b[4] < o[5] + pad


def duct_parts(duct):
    c = carriage()
    if duct == "r41":
        return [brep(c[R.NAMES[k]]) for k in ("p20", "p21", "p22")]
    return [load(P40.NAMES["p20"]), load(P40.NAMES["p21"]), P37.p22()[0]]


def obstacles(duct, tool, outlet):
    """Every carriage solid and tool part that reaches into the outlet box, except the duct itself."""
    skip = {R.NAMES["p20"], R.NAMES["p21"], R.NAMES["p22"]}
    out = []
    for n, f in MANIFEST["carriage"]:
        if n in skip:
            continue
        if duct != "r41" and n.startswith("R41_P22_P01"):
            continue                                   # released duct: its own socket-head screws below
        s = brep(f)
        if overlaps_box(bounds(s), outlet):
            out.append((n, s))
    if duct != "r41":
        for n, s in P37.other_hardware():
            if n.startswith("ACC_CASE_BOSS_M3x10_"):
                out.append((n, R.shape(s)))
    for n, s in variant_parts(tool):
        if overlaps_box(bounds(s), outlet):
            out.append((f"{tool}:{n}", s))
    return out


def solid_containing(shape, point):
    for s in shape.Solids():
        if s.isInside(cq.Vector(*point)):
            return s
    return None


def build(duct="r41", tool="Bambu", bed=False):
    t0 = time.perf_counter()
    o = list(OUTLET)
    if bed:
        o[4] = NOZZLE_TIP_Z - BED_GAP
    parts = duct_parts(duct)
    d = fuse_all(parts)
    cx, cy, r = SPIGOT
    inlet_point = (cx, cy, 20.0)
    # 1. The duct's own air: close the spigot mouth and fill the outlet box, then take the pocket at the inlet.
    cap = R.shape(acc.cyl_z(cx, cy, EXT[0], 31.0, r + 2.5))
    big = box(-40, 40, -70, 60, -110, 45)
    pockets = cut_all(big, [d, cap, box(*o)])
    cavity = solid_containing(pockets, inlet_point)
    if cavity is None:
        raise RuntimeError("no cavity at the inlet")
    cb = bounds(cavity)
    print(f"cavity {cavity.Volume():.0f} mm3, bounds {[round(v, 1) for v in cb]}", flush=True)
    if cb[0] < -39 or cb[1] > 39 or cb[2] < -69 or cb[5] > 44:
        raise RuntimeError("the duct's air leaks to the outside")
    # 2. Hose section and the open air around the nozzle.
    ext = R.shape(acc.cyl_z(cx, cy, EXT[0], EXT[0] + EXT[1], r))
    obs = obstacles(duct, tool, o)
    print(f"{len(obs)} obstacles in the outlet box: {[n for n, _ in obs]}", flush=True)
    air = cut_all(box(*o), [d] + [s for _, s in obs])
    fluid = fuse_all([cavity, ext, air])
    main = solid_containing(fluid, inlet_point)
    dropped = [round(s.Volume(), 2) for s in fluid.Solids() if not s.isSame(main)]
    print(f"fluid {main.Volume():.0f} mm3 ({len(fluid.Solids())} solids, dropped {dropped}); "
          f"{time.perf_counter() - t0:.0f} s", flush=True)
    return main, o, obs, dropped, cavity.Volume()


def classify(fluid, o, z_top, bed):
    planes = {("x", o[0]), ("x", o[1]), ("y", o[2]), ("y", o[3]), ("z", o[4]), ("z", o[5])}
    groups = {"inlet": [], "ambient": [], "walls": [], "bed": []}
    for f in fluid.Faces():
        b = bounds(f)
        name = "walls"
        if f.geomType() == "PLANE":
            if abs(b[4] - z_top) < 1e-6 and abs(b[5] - z_top) < 1e-6:
                name = "inlet"
            else:
                for axis, v in planes:
                    i = "xyz".index(axis)
                    if abs(b[2 * i] - v) < 1e-6 and abs(b[2 * i + 1] - v) < 1e-6:
                        name = "bed" if (bed and axis == "z" and v == o[4]) else "ambient"
        groups[name].append(f)
    return groups


def write_stl(fluid, groups, path, lin=0.01, ang=0.25):
    BRepMesh_IncrementalMesh(fluid.wrapped, lin, False, ang, True)
    counts = {}
    with open(path, "w") as fh:
        for name, faces in groups.items():
            if not faces:
                continue
            fh.write(f"solid {name}\n")
            n = 0
            for f in faces:
                loc = TopLoc_Location()
                tri = BRep_Tool.Triangulation_s(f.wrapped, loc)
                if tri is None:
                    raise RuntimeError(f"untriangulated face in {name}")
                trsf = loc.Transformation()
                pts = [tri.Node(i).Transformed(trsf) for i in range(1, tri.NbNodes() + 1)]
                rev = f.wrapped.Orientation() == TopAbs_REVERSED
                for k in range(1, tri.NbTriangles() + 1):
                    i1, i2, i3 = tri.Triangle(k).Get()
                    if rev:
                        i2, i3 = i3, i2
                    p = [pts[i - 1] for i in (i1, i2, i3)]
                    ux, uy, uz = (p[1].X() - p[0].X(), p[1].Y() - p[0].Y(), p[1].Z() - p[0].Z())
                    vx, vy, vz = (p[2].X() - p[0].X(), p[2].Y() - p[0].Y(), p[2].Z() - p[0].Z())
                    nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
                    ln = (nx * nx + ny * ny + nz * nz) ** 0.5 or 1.0
                    fh.write(f" facet normal {nx / ln:.6e} {ny / ln:.6e} {nz / ln:.6e}\n  outer loop\n")
                    for q in p:
                        fh.write(f"   vertex {q.X() * 1e-3:.9e} {q.Y() * 1e-3:.9e} {q.Z() * 1e-3:.9e}\n")
                    fh.write("  endloop\n endfacet\n")
                    n += 1
            fh.write(f"endsolid {name}\n")
            counts[name] = n
    return counts


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--duct", default="r41", choices=("r41", "released"))
    p.add_argument("--tool", default="Bambu", choices=("Bambu", "RedLizard"))
    p.add_argument("--bed", action="store_true")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    fluid, o, obs, dropped, cavity_vol = build(a.duct, a.tool, a.bed)
    fluid.exportBrep(str(out / "domain.brep"))
    z_top = EXT[0] + EXT[1]
    groups = classify(fluid, o, z_top, a.bed)
    areas = {k: round(sum(f.Area() for f in v), 2) for k, v in groups.items()}
    print("patch areas mm2", areas, flush=True)
    if abs(areas["inlet"] - 3.141592653589793 * SPIGOT[2] ** 2) > 0.5:
        raise RuntimeError(f"inlet area {areas['inlet']}")
    counts = write_stl(fluid, groups, out / "domain.stl")
    cx, cy, r = SPIGOT
    meta = {"duct": a.duct, "tool": a.tool, "bed": a.bed, "outlet_box_mm": o, "bed_z_mm": o[4] if a.bed else None,
            "inlet": {"centre_mm": [cx, cy, z_top], "radius_mm": r, "area_mm2": areas["inlet"]},
            "location_in_mesh_m": [cx * 1e-3, cy * 1e-3, (EXT[0] + 10.0) * 1e-3],
            "bounds_mm": [round(v, 3) for v in bounds(fluid)], "volume_mm3": round(fluid.Volume(), 1),
            "duct_air_mm3": round(cavity_vol, 1), "patch_areas_mm2": areas, "triangles": counts,
            "obstacles": [n for n, _ in obs], "dropped_pockets_mm3": dropped, "nozzle_tip_z_mm": NOZZLE_TIP_Z}
    (out / "domain.json").write_text(json.dumps(meta, indent=1))
    print(json.dumps({k: meta[k] for k in ("bounds_mm", "volume_mm3", "duct_air_mm3", "triangles")}))


if __name__ == "__main__":
    main()
