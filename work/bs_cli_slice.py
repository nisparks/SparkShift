"""Flatten Bambu Studio presets (follow 'inherits' to the root) so the CLI can load them, then slice the CPAP parts."""
import json
import subprocess
import sys
from pathlib import Path

RES = Path(r"C:\Program Files\Bambu Studio\resources\profiles\BBL")
USER = Path(r"C:\Users\nspar\AppData\Roaming\BambuStudio\user\649957155")
OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\bs_cli")
STL = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26\stl")
EXE = r"C:\Program Files\Bambu Studio\bambu-studio.exe"
PARTS = ["P20_CPAP_Hose_Inlet_Thick_Sleeve_R41_REVIEW_PRINT_ORIENTED.stl",
         "P21_CPAP_Gantry_Bridge_Thick_Joints_R41_REVIEW_PRINT_ORIENTED.stl",
         "P22_CPAP_Lower_Plenum_Wide_Jets_Face_Mounts_R41_REVIEW_PRINT_ORIENTED.stl"]
# Plate positions (part centres, mm): inside both nozzles' reach on the H2D (X25-325), 60 mm apart.
PLACE = {"P20": (235.0, 160.0), "P21": (115.0, 160.0), "P22": (175.0, 160.0)}


def placed_stls():
    import trimesh
    out = []
    d = OUT / "placed"
    d.mkdir(exist_ok=True)
    for name in PARTS:
        m = trimesh.load_mesh(str(STL / name))
        cx, cy = PLACE[name[:3]]
        lo, hi = m.bounds
        m.apply_translation([cx - (lo[0] + hi[0]) / 2, cy - (lo[1] + hi[1]) / 2, -lo[2]])
        path = d / name
        m.export(str(path))
        out.append(path)
    return out


def index(kind):
    out = {}
    for p in (RES / kind).glob("*.json"):
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            continue
        if "name" in d:
            out[d["name"]] = d
    return out


def flatten(d, idx, source="system"):
    chain = [d]
    while chain[-1].get("inherits"):
        chain.append(idx[chain[-1]["inherits"]])
    merged = {}
    for layer in reversed(chain):
        merged.update(layer)
    merged.pop("inherits", None)
    merged["from"] = source
    merged["name"] = d["name"]
    return merged


def main():
    OUT.mkdir(exist_ok=True)
    for p in OUT.glob("*"):
        if p.is_file():
            p.unlink()
    machines, processes, filaments = index("machine"), index("process"), index("filament")
    files = {}
    machine = flatten(machines["Bambu Lab H2D 0.4 nozzle"], machines)
    process = flatten(json.loads((USER / "process" / "0.20mm H2D - Voron 5 Wall 8 top-bottom with Support v2.json")
                                 .read_text(encoding="utf-8")), processes, "User")
    # P20 and P22 stand tall on small feet (52 mm on 110 mm2, 75 mm on 146 mm2): an outer brim, 5 mm
    process["brim_type"] = "outer_only"
    process["brim_width"] = "5"
    print("compat:", process.get("compatible_printers"), "| machine:", machine.get("name"), machine.get("printer_model"),
          machine.get("printer_variant"))
    # The user's own filament list and colours (Bambu Studio app config), so opening the project changes nothing there
    conf = Path(r"C:\Users\nspar\AppData\Roaming\BambuStudio\BambuStudio.conf").read_text(encoding="utf-8")
    presets = json.loads(conf[:conf.rfind("}") + 1])["presets"]
    names, colours = presets["filaments"], presets["filament_colors"].split(",")
    fil = []
    for n, c in zip(names, colours):
        f = flatten(filaments[n], filaments)
        f["filament_colour"] = [c]
        fil.append(f)
    for name, d in [("machine", machine), ("process", process)] + [(f"filament{i + 1}", f) for i, f in enumerate(fil)]:
        path = OUT / f"{name}.json"
        path.write_text(json.dumps(d, indent=1), encoding="utf-8")
        files[name] = path
    print("process support:", {k: process.get(k) for k in ("enable_support", "support_type", "support_on_build_plate_only",
                                                             "support_threshold_angle", "support_interface_filament",
                                                             "brim_type", "brim_width", "wall_loops")})
    project = "CPAP_R41_H2D.3mf"
    cmd = [EXE, "--debug", "2", "--orient", "0", "--arrange", "0", "--allow-mix-temp", "--curr-bed-type", "Textured PEI Plate",
           "--load-settings", f"{files['machine']};{files['process']}",
           "--load-filaments", ";".join(str(files[f"filament{i + 1}"]) for i in range(len(fil))),
           "--outputdir", str(OUT), "--export-3mf", project] + [str(p) for p in placed_stls()]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    print("exit", r.returncode)
    res = OUT / "result.json"
    print(res.read_text() if res.exists() else "no result.json")
    for p in sorted(OUT.glob("*")):
        print(" ", p.name, p.stat().st_size)


if __name__ == "__main__":
    main()
