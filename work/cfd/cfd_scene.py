"""CFD scratch: load the verified revision-41 scene and look at the duct's openings (session scratch)."""
import json
import sys
from pathlib import Path

HERE = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
OUT = Path(__file__).parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(OUT.parent))
import os  # noqa: E402
os.chdir(HERE)

import cadquery as cq  # noqa: E402

import build_and_verify_accessories_v26 as acc  # noqa: E402
import r37_parts as P37  # noqa: E402
import r41_parts as R  # noqa: E402
from audit_tool_owned_2510 import bounds  # noqa: E402

SCENE = acc.WORK / "r41_scene"
MANIFEST = json.loads((SCENE / "manifest.json").read_text())


def brep(fname):
    return cq.Shape.importBrep(str(SCENE / fname))


def carriage():
    return dict(MANIFEST["carriage"])


def variant_parts(label):
    return [(n, brep(f)) for n, f in MANIFEST["variants"][label]["parts"]]


if __name__ == "__main__":
    from r41_diag import plot_sections
    c = carriage()
    names = [R.NAMES["p20"], R.NAMES["p21"], R.NAMES["p22"], P37.NAMES["cable"]]
    shapes = {n: brep(c[n]) for n in names}
    for n, s in shapes.items():
        print(n, [round(v, 2) for v in bounds(s)], len(s.Solids()))
    for label in ("Bambu", "RedLizard"):
        for n, s in variant_parts(label):
            print(label, n, [round(v, 2) for v in bounds(s)], len(s.Solids()))
    near = []
    for n, f in MANIFEST["carriage"]:
        if n in names:
            continue
        s = brep(f)
        b = bounds(s)
        if b[1] > -32 and b[0] < 32 and b[3] > -2 and b[2] < 60 and b[5] > -100 and b[4] < -38:
            near.append((n, [round(v, 2) for v in b]))
    print("carriage solids near the outlet region:")
    for n, b in near:
        print("  ", n, b)
    p20, p21, p22, cable = (shapes[n] for n in names)
    bam = cq.Compound.makeCompound([s for n, s in variant_parts("Bambu") if n in ("hotend", "hotend hardware", "body")])
    items = [(p22, "teal", "P22"), (p21, "c", "P21"), (p20, "b", "P20"), (cable, "orange", "cable"), (bam, "grey", "Bambu tool")]
    for z in (-76.0, -74.5, -70.0, -65.0, -60.0, -55.0):
        plot_sections(f"cfd_xy_z{z}.png", items, "z", z, (-30, 30), (-50, 35), f"XY at Z {z}")
    for x in (0.0, 5.0, 11.0, 16.0):
        plot_sections(f"cfd_yz_x{x}.png", items, "x", x, (-62, 40), (-82, 34), f"YZ at X {x}")
    plot_sections("cfd_xz_y-45.7.png", items, "y", -45.7, (-25, 25), (-25, 34), "XZ at Y -45.7 (spigot)")
    print("ok")
