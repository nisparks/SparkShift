"""Why doesn't Bambu Studio support P23's locating bosses on revision 43's P22? Slice the print-oriented STL with the
user's process preset and a few support variants (no painting), and look for support extrusion under the bosses and
under the cheeks."""
import json
import re
import subprocess
import sys
import time
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import bs_cli_slice as B  # noqa: E402
import bs_p22_r43 as P  # noqa: E402

OUT = B.OUT.parent / "bs_r43_boss"
CX, CY = P.CENTRE
# on the plate (from the painted triangles): bosses x = CX +- 12.75..18.85, y 167.4..169.6, underside from z 22.85;
# cheeks |x - CX| 13.6..22.6 at print height 61.3, over P22 itself
REGIONS = {"bosses": lambda x, y, z: 12.0 < abs(x - CX) < 19.6 and 166.6 < y < 170.4 and z <= 23.2,
           "cheeks": lambda x, y, z: 13.0 < abs(x - CX) < 23.2 and 50.0 < z <= 61.6}
VARIANTS = {
    "preset_as_is": {},
    "remove_small_off": {"support_remove_small_overhang": "0"},
    "plate_only_off": {"support_on_build_plate_only": "0"},
    "plate_only_off_remove_small_off": {"support_on_build_plate_only": "0", "support_remove_small_overhang": "0"},
}


def support_hits(gcode):
    feat, z, x, y = None, 0.0, 0.0, 0.0
    hits = {k: {} for k in REGIONS}
    total = {}
    for line in gcode.splitlines():
        if line.startswith("; FEATURE:"):
            feat = line[10:].strip()
        elif line.startswith("; Z_HEIGHT:"):
            z = float(line.split(":")[1])
        elif line[:3] in ("G0 ", "G1 ", "G2 ", "G3 "):
            mx, my = re.search(r"X([-\d.]+)", line), re.search(r"Y([-\d.]+)", line)
            nx = float(mx.group(1)) if mx else x
            ny = float(my.group(1)) if my else y
            if feat and "upport" in feat and re.search(r"E[\d.]", line):
                total[feat] = total.get(feat, 0) + 1
                for k, f in REGIONS.items():
                    for px, py in ((x, y), (nx, ny), ((x + nx) / 2, (y + ny) / 2)):
                        if f(px, py, z):
                            h = hits[k].setdefault(feat, [0, 1e9, -1e9])
                            h[0] += 1
                            h[1], h[2] = min(h[1], z), max(h[2], z)
                            break
            x, y = nx, ny
    return total, hits


def main():
    OUT.mkdir(exist_ok=True)
    machine, process, fil = P.presets()
    base = B.flatten(json.loads((B.USER / "process" / "0.20mm H2D - Voron 5 Wall 8 top-bottom with Support v2.json")
                                .read_text(encoding="utf-8")), B.index("process"), "User")
    keys = ("enable_support", "support_type", "support_threshold_angle", "support_on_build_plate_only",
            "support_remove_small_overhang", "support_critical_regions_only")
    print("user preset:", {k: base.get(k) for k in keys})
    # the user's preset, but keep the brim, the interface filament and the prime tower where bs_p22_r43 puts them
    for k in keys:
        if k in base:
            process[k] = base[k]
        else:
            process.pop(k, None)
    stl, _ = P.placed()
    files = {"machine": OUT / "machine.json"}
    files["machine"].write_text(json.dumps(machine, indent=1), encoding="utf-8")
    fils = []
    for i, f in enumerate(fil):
        p = OUT / f"filament{i + 1}.json"
        p.write_text(json.dumps(f, indent=1), encoding="utf-8")
        fils.append(str(p))
    only = sys.argv[1:] or list(VARIANTS)
    for name in only:
        proc = dict(process, **VARIANTS[name])
        d = OUT / name
        d.mkdir(exist_ok=True)
        for p in d.glob("*"):
            p.unlink()
        pp = d / "process.json"
        pp.write_text(json.dumps(proc, indent=1), encoding="utf-8")
        cmd = [B.EXE, "--debug", "2", "--orient", "0", "--arrange", "0", "--allow-mix-temp",
               "--curr-bed-type", "Textured PEI Plate", "--load-settings", f"{files['machine']};{pp}",
               "--load-filaments", ";".join(fils), "--slice", "0", "--outputdir", str(d), "--export-3mf", "sliced.3mf",
               str(stl)]
        t0 = time.time()
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
        out = d / "sliced.3mf"
        print(f"\n[{name}] {VARIANTS[name]} exit {r.returncode} in {time.time() - t0:.0f} s")
        if not out.exists():
            res = d / "result.json"
            print("  no output;", res.read_text() if res.exists() else "no result.json")
            continue
        z = zipfile.ZipFile(out)
        g = z.read(next(n for n in z.namelist() if n.endswith(".gcode"))).decode(errors="replace")
        total, hits = support_hits(g)
        print("  support extrusion moves by feature:", total or "none")
        for k, h in hits.items():
            print(f"  under the {k}:", {f: f"{v[0]} moves, z {v[1]:.2f}-{v[2]:.2f}" for f, v in h.items()} or "nothing")


if __name__ == "__main__":
    main()
