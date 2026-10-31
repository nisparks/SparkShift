import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bs_cli_slice as B
import bs_p22_r43 as P
O = P.OUT
machine, process, fil = P.presets()
stl = O / P.STL_NAME
def run(tag, overrides, model):
    d = O / tag
    d.mkdir(exist_ok=True)
    pr = dict(process); pr.update(overrides)
    files = {}
    for name, dd in [("machine", machine), ("process", pr)] + [(f"filament{i + 1}", f) for i, f in enumerate(fil)]:
        files[name] = d / f"{name}.json"; files[name].write_text(json.dumps(dd, indent=1), encoding="utf-8")
    cmd = [B.EXE, "--debug", "2", "--allow-mix-temp", "--curr-bed-type", "Textured PEI Plate", "--orient", "0", "--arrange", "0",
           "--load-settings", f"{files['machine']};{files['process']}",
           "--load-filaments", ";".join(str(files[f"filament{i + 1}"]) for i in range(len(fil))),
           "--slice", "0", "--outputdir", str(d), "--export-3mf", "out.3mf", str(model)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    res = d / "result.json"
    j = json.loads(res.read_text()) if res.exists() else {}
    print(tag, "exit", r.returncode, j.get("error_string"), "| support time:",
          (j.get("sliced_plates") or [{}])[0].get("feature_type_times", {}).get("Support"), flush=True)
run("stl_manual", {}, stl)
run("stl_auto_plate", {"support_type": "tree(auto)", "support_on_build_plate_only": "1"}, stl)
run("stl_auto_iface4", {"support_type": "tree(auto)", "support_on_build_plate_only": "1", "support_interface_filament": "4"}, stl)
