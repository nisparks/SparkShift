import json, subprocess, sys, zipfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bs_cli_slice as B
import bs_p22_r43 as P
O = P.OUT
machine, process, fil = P.presets()
src = zipfile.ZipFile(O / P.PROJECT)
for keep_model_settings in (True, False):
    tag = "model_only" + ("_with_model_settings" if keep_model_settings else "")
    d = O / tag
    d.mkdir(exist_ok=True)
    m3 = d / "p22_painted_model.3mf"
    with zipfile.ZipFile(m3, "w", zipfile.ZIP_DEFLATED) as z:
        for it in src.infolist():
            n = it.filename
            if n.startswith("Metadata/") and not (keep_model_settings and n == "Metadata/model_settings.config"):
                continue
            z.writestr(it, src.read(n))
    files = {}
    for name, dd in [("machine", machine), ("process", process)] + [(f"filament{i + 1}", f) for i, f in enumerate(fil)]:
        files[name] = d / f"{name}.json"; files[name].write_text(json.dumps(dd, indent=1), encoding="utf-8")
    cmd = [B.EXE, "--debug", "2", "--allow-mix-temp", "--curr-bed-type", "Textured PEI Plate", "--orient", "0", "--arrange", "0",
           "--load-settings", f"{files['machine']};{files['process']}",
           "--load-filaments", ";".join(str(files[f"filament{i + 1}"]) for i in range(len(fil))),
           "--slice", "0", "--outputdir", str(d), "--export-3mf", "out.3mf", str(m3)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    res = d / "result.json"
    j = json.loads(res.read_text()) if res.exists() else {}
    sp = (j.get("sliced_plates") or [{}])[0]
    print(tag, "exit", r.returncode, j.get("error_string"), "| support s:", sp.get("feature_type_times", {}).get("Support"),
          "| interface s:", sp.get("feature_type_times", {}).get("Support interface"), "| filaments:", sp.get("filaments"), flush=True)
    if (d / "out.3mf").exists() and j.get("return_code") == 0:
        print("   support extrusion boxes:", json.dumps(P.support_in_gcode(d / "out.3mf")))
