"""R43 study: the Bambu hotend (with its silicone sock) and the Red Lizard against P22, mounted and along the whole
60 mm withdrawal (the carriage backs away in -Y and leaves the tool in its dock), for R41 and the variants.
Reports the smallest gap per hotend part and where it is (session scratch)."""
import json
import sys
from pathlib import Path

FILES = Path(__file__).parent
sys.path.insert(0, str(FILES))
import r43_sections as S  # noqa: E402

import cadquery as cq  # noqa: E402
from OCP.BRepExtrema import BRepExtrema_DistShapeShape  # noqa: E402

VARIANTS = FILES / "r43" / "variants"
SOLID_NAMES = {"Bambu": {0: "ceramic (zirconia) block", 1: "aluminium heater cradle", 2: "wire bail and latch",
                         3: "hotend (nozzle, melt block, heatsink)", 4: "silicone sock", 5: "retaining magnet"}}


def dist(a, b):
    d = BRepExtrema_DistShapeShape(a.wrapped, b.wrapped)
    d.Perform()
    return d.Value(), d.PointOnShape1(1), d.PointOnShape2(1)


def bbox_gap(a, b):
    g = 0.0
    for lo1, hi1, lo2, hi2 in ((a.xmin, a.xmax, b.xmin, b.xmax), (a.ymin, a.ymax, b.ymin, b.ymax),
                               (a.zmin, a.zmax, b.zmin, b.zmax)):
        g = max(g, lo2 - hi1, lo1 - hi2)
    return g


def hotend_solids(scene, label):
    m = json.loads((scene / "manifest.json").read_text())
    out = []
    for n, f in m["variants"][label]["parts"]:
        if "hotend" not in n:
            continue
        for i, so in enumerate(cq.Shape.importBrep(str(scene / f)).Solids()):
            name = SOLID_NAMES.get(label, {}).get(i, f"{n} [{i}]") if n == "hotend" else f"{n} [{i}]"
            out.append((name, so))
    return out


def sweep(p22, solids, travel=60.0, step=0.5, cutoff=4.0):
    best = {}
    for k in range(int(travel / step) + 1):
        d = k * step
        moved = p22.translate(cq.Vector(0, -d, 0))
        mb = moved.BoundingBox()
        for name, so in solids:
            if bbox_gap(mb, so.BoundingBox()) > cutoff:
                continue
            v, p1, p2 = dist(moved, so)
            if name not in best or v < best[name][0]:
                best[name] = (v, d, (round(p2.X(), 2), round(p2.Y(), 2), round(p2.Z(), 2)))
    return best


if __name__ == "__main__":
    scene = FILES / "r41_scene"
    m = json.loads((scene / "manifest.json").read_text())
    designs = {"R41": cq.Shape.importBrep(str(scene / dict(m["carriage"])["P22_CPAP_Lower_Plenum_Wide_Jets_Face_Mounts_R41_REVIEW"]))}
    for k in sys.argv[1:] or ("long", "rear"):
        designs[k] = cq.Shape.importBrep(str(VARIANTS / f"p22_{k}.brep"))
    out = {}
    for label in ("Bambu", "RedLizard"):
        solids = hotend_solids(scene, label)
        for dname, p22 in designs.items():
            mounted = {n: round(dist(p22, so)[0], 3) for n, so in solids if bbox_gap(p22.BoundingBox(), so.BoundingBox()) < 6}
            sw = sweep(p22, solids)
            out[f"{label}/{dname}"] = {"mounted_mm": mounted,
                                       "withdrawal_min_mm": {n: {"gap_mm": round(v, 3), "at_withdrawal_mm": d, "hotend_point": p}
                                                             for n, (v, d, p) in sw.items()}}
            print(f"== {label} vs P22 {dname}")
            for n in sorted(set(mounted) | set(sw)):
                s_ = sw.get(n)
                print(f"   {n:42s} mounted {mounted.get(n, float('nan')):7.3f} mm   withdrawal min "
                      f"{(s_[0] if s_ else float('nan')):7.3f} mm at {s_[1] if s_ else '-'} mm  {s_[2] if s_ else ''}", flush=True)
    (FILES / "r43" / "hotend_clearance.json").write_text(json.dumps(out, indent=1))
