"""Unverified R41 carriage preview for Fusion, in print colours, from the cached part BREPs (session scratch)."""
import sys

sys.path.insert(0, r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files")
from r41_diag import *  # noqa: E402,F403
import json  # noqa: E402
import build_and_verify_accessories_v26 as acc  # noqa: E402
import build_print_colour_review as CR  # noqa: E402
import print_colors as C  # noqa: E402
from audit_tool_owned_2510 import compound  # noqa: E402

cached = {k: get(k) for k in ("p20", "p21", "p22", "p24", "p02")}
p03 = cq.Shape.importBrep(str(OUT / "p03_15x5x3.brep"))
items = []
meta = json.loads((acc.WORK / "v26_meta.json").read_text())
for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep")):
    name = m["name"]
    if name.startswith(CR.OLD_TOOL):
        continue
    key = CR.CORE_PRINTS.get(name)
    if key == "P02":
        items.append((f"P02_{R.NAMES['p02']}", cached["p02"], C.part("P02")))
    elif key == "P03":
        items.append((f"P03_{R.NAMES['p03_15x5x3']}", p03, C.part("P03")))
    elif key:
        shape = load(CR.PRINT_SET[key]) if key in CR.PRINT_SET else P37.shape(s)
        items.append((f"{key}_{CR.PRINT_SET.get(key, name)}", shape, C.part(key)))
    else:
        items.append((name, P37.shape(s), CR.hardware_colour(name)))
b = P37.beacon()
items += [(f"P20_{R.NAMES['p20']}", cached["p20"], C.part("P20")), (f"P21_{R.NAMES['p21']}", cached["p21"], C.part("P21")),
          (f"P22_{R.NAMES['p22']}", cached["p22"], C.part("P22")), (f"P23_{P37.NAMES['p23']}", P37.p23(), C.part("P23")),
          (f"P24_{R.NAMES['p24']}", cached["p24"], C.part("P24")), ("Probe_cable", P37.cable(), C.hex_rgb("cable")),
          ("Beacon_RevH", compound(b[2:5]), C.hex_rgb("probe")), ("EBB42", P37.ebb42(), C.hex_rgb("pcb"))]
for n, s in R.other_hardware() + P37.probe_hardware():
    items.append((n, s, C.hex_rgb("brass" if "HEATSET" in n else "steel")))
asm = CR.group("SparkShift_R41_carriage_preview", items)
path = OUT / "r41_preview.step"
asm.export(str(path))
print(path, len(items), "items", round(path.stat().st_size / 1e6, 1), "MB")
