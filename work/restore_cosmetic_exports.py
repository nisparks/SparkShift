"""Restore exports that only differ from HEAD in the STEP header timestamp or styling-record order, and point the
new verification reports' export hashes for those files back at the committed bytes (session helper)."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner")
BASE = "cad/SparkShift_Accessories_v26"
REPORTS = ["verification_carriage_fixes_r41.json", "verification_cartographer_mount_r42.json"]
STYLE = re.compile(r"^\s*(#\d+\s*=\s*(STYLED_ITEM|OVER_RIDING_STYLED_ITEM|COLOUR_RGB|FILL_AREA_STYLE_COLOUR|FILL_AREA_STYLE|"
                   r"SURFACE_STYLE_\w+|SURFACE_SIDE_STYLE|PRESENTATION_STYLE_ASSIGNMENT|CURVE_STYLE|"
                   r"MECHANICAL_DESIGN_GEOMETRIC_PRESENTATION_REPRESENTATION)\b|[#\d,()\s;]+$)")


def git_bytes(rel):
    r = subprocess.run(["git", "show", f"HEAD:{rel}"], capture_output=True, cwd=REPO)
    return r.stdout if r.returncode == 0 else None


def cosmetic_only(old, new):
    a, b = old.decode(errors="ignore").splitlines(), new.decode(errors="ignore").splitlines()
    if len(a) != len(b):
        return False
    for x, y in zip(a, b):
        if x == y or (x.startswith("FILE_NAME(") and y.startswith("FILE_NAME(")):
            continue
        if not (STYLE.match(x) and STYLE.match(y)):
            return False
    return True


def main():
    for rep in REPORTS:
        path = REPO / BASE / rep
        new = json.loads(path.read_text(encoding="utf-8"))
        head = {e["file"].replace("\\", "/"): e for e in json.loads(git_bytes(f"{BASE}/{rep}"))["exports"]}
        changed = False
        for e in new["exports"]:
            p = e["file"].replace("\\", "/")
            rel = f"{BASE}/{p}"
            committed = git_bytes(rel)
            if committed is None:
                continue
            work = (REPO / rel).read_bytes()
            if work != committed:
                if not cosmetic_only(committed, work):
                    print(f"  KEEP (real change) {p}")
                    continue
                (REPO / rel).write_bytes(committed)
                print(f"  restored {p}")
            h = hashlib.sha256(committed).hexdigest()
            if e["sha256"] != h:
                old = head.get(p)
                assert old and old["sha256"] == h, p
                e["sha256"], e["mb"] = old["sha256"], old["mb"]
                changed = True
                print(f"  report hash -> HEAD for {p}")
        if changed:
            path.write_text(json.dumps(new, indent=2, default=str) + "\n")   # as the build scripts write it
        print(rep, "updated" if changed else "unchanged")


if __name__ == "__main__":
    main()
