import json
from pathlib import Path

WORK = Path(__file__).resolve().parent
v26_meta = json.loads((WORK / "v26_meta.json").read_text())

dump = json.loads(Path(r"C:\Users\nspar\AppData\Local\Temp\1792296311963-copilot-tool-output-a7371a3ef1b74142bc98f80b58898d9f.txt").read_text())
occ_bodies = []
for occ in dump["occurrences"]:
    for b in occ["bodies"]:
        occ_bodies.append((occ["name"], b["name"], b["volume_cm3"] * 1000.0))

print(f"Dump bodies: {len(occ_bodies)} vs STEP solids: {len(v26_meta)}")
mismatches = 0
for idx, (m, (oname, bname, ovol)) in enumerate(zip(v26_meta, occ_bodies)):
    m["occ_name"] = oname
    m["name"] = bname
    is_print = bname.startswith("PRINT_") or bname == "TOOL_06_Tool_head_back_part_1"
    is_ref = ("PTFE" in bname or "filament" in bname or "BELT" in bname or "ENVELOPE" in bname)
    m["is_print"] = is_print
    m["is_ref"] = is_ref
    m["is_metal"] = not (is_print or is_ref)
    if abs(m["vol_mm3"] - ovol) > 1.0 and bname != "PRINT_arm_front_half":
        mismatches += 1
        print(f"  Mismatch at {idx}: {bname} step_vol={m['vol_mm3']} dump_vol={ovol}")

print("Total volume mismatches:", mismatches)
(WORK / "v26_meta.json").write_text(json.dumps(v26_meta, indent=2))




