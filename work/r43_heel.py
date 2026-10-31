"""R43 study: P22's heel region alone, zoomed (session scratch)."""
import sys
from pathlib import Path

FILES = Path(__file__).parent
sys.path.insert(0, str(FILES))
import r43_sections as S  # noqa: E402

import cadquery as cq  # noqa: E402
import json  # noqa: E402

if __name__ == "__main__":
    m = json.loads((S.SCENE / "manifest.json").read_text())
    c = dict(m["carriage"])
    p22 = cq.Shape.importBrep(str(S.SCENE / c["P22_CPAP_Lower_Plenum_Wide_Jets_Face_Mounts_R41_REVIEW"]))
    p23 = cq.Shape.importBrep(str(S.SCENE / c["P23_Probe_Mount_Raised_Rear_Ears_R37_REVIEW"]))
    items = [(p22, "teal", "P22 R41"), (p23, "orange", "P23")]
    for z in (-77.2, -76.0, -74.8, -73.4, -72.0, -70.5, -69.0, -67.0):
        S.plot(f"heel_plan_z{z:g}.png", items, "z", z, (6, 24), (6, 31), f"P22 heel region, plan at Z{z:g}")
    for x in (10.6, 11.2, 12.2, 13.5, 17.0, 21.5):
        S.plot(f"heel_side_x{x:g}.png", items, "x", x, (6, 31), (-79, -60), f"P22 heel region, side at X{x:g}")
