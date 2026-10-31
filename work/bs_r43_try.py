import subprocess, json, shutil
from pathlib import Path
O = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\bs_r43")
EXE = r"C:\Program Files\Bambu Studio\bambu-studio.exe"
for src in ("raw.3mf", "P22_R43_H2D.3mf"):
    res = O / "result.json"
    if res.exists():
        res.unlink()
    out = f"try_{src.replace('.3mf', '')}_sliced.3mf"
    cmd = [EXE, "--debug", "2", "--allow-mix-temp", "--curr-bed-type", "Textured PEI Plate", "--slice", "0",
           "--outputdir", str(O), "--export-3mf", out, str(O / src)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    print("==", src, "exit", r.returncode)
    print("stdout tail:", r.stdout[-1500:])
    print("stderr tail:", r.stderr[-800:])
    print(res.read_text() if res.exists() else "no result.json")
