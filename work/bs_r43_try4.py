import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import bs_cli_slice as B
import bs_p22_r43 as P
O = P.OUT
for tag, src, with_settings in (("proj_slice1", P.PROJECT, False), ("proj_slice1_settings", P.PROJECT, True)):
    d = O / tag
    d.mkdir(exist_ok=True)
    cmd = [B.EXE, "--debug", "2", "--allow-mix-temp", "--curr-bed-type", "Textured PEI Plate"]
    if with_settings:
        cmd += ["--load-settings", f"{O / 'machine.json'};{O / 'process.json'}",
                "--load-filaments", ";".join(str(O / f"filament{i + 1}.json") for i in range(8))]
    cmd += ["--slice", "1", "--outputdir", str(d), "--export-3mf", "out.3mf", str(O / src)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    res = d / "result.json"
    j = json.loads(res.read_text()) if res.exists() else {}
    sp = (j.get("sliced_plates") or [{}])[0]
    print(tag, "exit", r.returncode, j.get("error_string"), "| support s:", sp.get("feature_type_times", {}).get("Support"),
          "| interface s:", sp.get("feature_type_times", {}).get("Support interface"), flush=True)
    if j.get("return_code") == 0 and (d / "out.3mf").exists():
        print("   support extrusion boxes:", json.dumps(P.support_in_gcode(d / "out.3mf")))
