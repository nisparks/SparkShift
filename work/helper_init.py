import json
from pathlib import Path
from OCP.STEPControl import STEPControl_Reader

ref_json = Path(r"C:\Users\nspar\.copilot\session-state\4cb0e434-6f95-42f4-83ee-667c5a4a7f3c\files\compact_direct_cam\monolith_mount_reference\reference_measurements.json")
ref_data = json.loads(ref_json.read_text())
for row in ref_data["sources"]["integration"]["bodies"]:
    if row["component"] == "2WD full Y travel:1":
        print(f"{row['body_name']:8s} bounds={row['bounds_mm']} vol={row['volume_mm3']:.1f}")
