"""Finish the CLI-made CPAP project so it matches the user's H2D: nozzle types, filament map, AMS count, short names."""
import json
import zipfile
from pathlib import Path

SRC = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\bs_cli\CPAP_R41_H2D.3mf")
DST = SRC.with_name("CPAP_R41_H2D_brim.3mf")
NAMES = {"P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW_PRINT_ORIENTED.stl": "P20 CPAP hose inlet (R41)",
         "P21_CPAP_Gantry_Bridge_Thick_Joints_R41_REVIEW_PRINT_ORIENTED.stl": "P21 CPAP gantry bridge (R41)",
         "P22_CPAP_Lower_Plenum_Wide_Jets_Face_Mounts_R41_REVIEW_PRINT_ORIENTED.stl": "P22 CPAP lower plenum (R41)"}


def main():
    zin = zipfile.ZipFile(SRC)
    ps = json.loads(zin.read("Metadata/project_settings.config"))
    n = len(ps["filament_settings_id"])
    # as in the user's own saved H2D projects (Standard left, High Flow right; auto filament grouping)
    ps["nozzle_volume_type"] = ["Standard", "High Flow"]
    ps["filament_map"] = ["1"] * n
    ps["filament_nozzle_map"] = ["0"] * n
    ps["filament_volume_map"] = ["0"] * n
    ps["extruder_ams_count"] = ["1#0|4#1", "1#0|4#1"]
    # The CLI leaves the prime tower at X15, out of the right nozzle's reach (X25-350): put it behind the parts, centred
    ps["wipe_tower_x"] = ["165"]
    ps["wipe_tower_y"] = ["250"]
    with zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == "Metadata/project_settings.config":
                data = json.dumps(ps, indent=4).encode()
            elif item.filename == "Metadata/model_settings.config":
                s = data.decode()
                for old, new in NAMES.items():
                    s = s.replace(f'<metadata key="name" value="{old}"/>', f'<metadata key="name" value="{new}"/>')
                data = s.encode()
            zout.writestr(item, data)
    check = zipfile.ZipFile(DST)
    p = json.loads(check.read("Metadata/project_settings.config"))
    print(DST, DST.stat().st_size)
    print({k: p[k] for k in ("nozzle_volume_type", "filament_map", "extruder_ams_count", "brim_type", "brim_width",
                             "support_interface_filament", "print_settings_id", "wipe_tower_x", "wipe_tower_y")})
    import re
    print(re.findall(r'<metadata key="name" value="([^"]+)"', check.read("Metadata/model_settings.config").decode()))


if __name__ == "__main__":
    main()
