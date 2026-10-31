"""Bambu Studio project for revision 43's P22 (session scratch): the user's H2D presets, P22 on its back face, and
support only where painted - the cheeks' two bearing faces - with Bambu Support for ABS as the interface. Then slice it
with the CLI and check where the support went."""
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import numpy as np
import trimesh

sys.path.insert(0, str(Path(__file__).parent))
import bs_cli_slice as B  # noqa: E402

OUT = B.OUT.parent / "bs_r43"
STL_NAME = "P22_CPAP_Lower_Plenum_Low_Jets_R43_REVIEW_PRINT_ORIENTED.stl"
CENTRE = (175.0, 160.0)
CHEEK_Z, CHEEK_X = 15.9 + 45.4, (13.6, 22.6)   # the bearing faces: print height, |X| from P22's centre plane
# P23's rear-ear locating bosses (r37_parts REAR_XY, SPIGOT_Z): Ø6.1 tubes standing 2.2 mm proud of P22's underside,
# lying on their side in print; P23's sockets leave them 0.10 mm radial clearance, so support their undersides too
BOSS_X, BOSS_Z, BOSS_R = 15.8, -19.5 + 45.4, 3.05
PROJECT, SLICED = "P22_R43_H2D.3mf", "P22_R43_H2D_sliced.3mf"


def presets():
    machines, processes, filaments = B.index("machine"), B.index("process"), B.index("filament")
    machine = B.flatten(machines["Bambu Lab H2D 0.4 nozzle"], machines)
    process = B.flatten(json.loads((B.USER / "process" / "0.20mm H2D - Voron 5 Wall 8 top-bottom with Support v2.json")
                                   .read_text(encoding="utf-8")), processes, "User")
    conf = Path(r"C:\Users\nspar\AppData\Roaming\BambuStudio\BambuStudio.conf").read_text(encoding="utf-8")
    p = json.loads(conf[:conf.rfind("}") + 1])["presets"]
    names, colours = p["filaments"], p["filament_colors"].split(",")
    fil = []
    for n, c in zip(names, colours):
        f = B.flatten(filaments[n], filaments)
        f["filament_colour"] = [c]
        fil.append(f)
    process.update({"brim_type": "outer_only", "brim_width": "5", "enable_support": "1", "support_type": "tree(manual)",
                    "support_on_build_plate_only": "0",
                    "support_interface_filament": str(names.index("Bambu Support for ABS @BBL H2D") + 1),
                    # the CLI leaves the prime tower at X15, out of the right nozzle's reach: behind the part, centred
                    "wipe_tower_x": ["165"], "wipe_tower_y": ["250"]})
    return machine, process, fil


def placed():
    m = trimesh.load_mesh(str(B.STL / STL_NAME))
    lo, hi = m.bounds
    m.apply_translation([CENTRE[0] - (lo[0] + hi[0]) / 2, CENTRE[1] - (lo[1] + hi[1]) / 2, -lo[2]])
    path = OUT / STL_NAME
    m.export(str(path))
    return path, m


def paint(src, dst):
    """Mark the cheeks' bearing-face triangles as support enforcers (TriangleSelector code '4': a whole triangle)."""
    z = zipfile.ZipFile(src)
    models = [n for n in z.namelist() if n.endswith(".model") and b"<triangle " in z.read(n)]
    out, painted = {}, 0
    for name in models:
        s = z.read(name).decode()
        v = np.array([[float(a), float(b), float(c)] for a, b, c in
                      re.findall(r'<vertex x="([-\d.e]+)" y="([-\d.e]+)" z="([-\d.e]+)"', s)])
        t = np.array([[int(a), int(b), int(c)] for a, b, c in re.findall(r'<triangle v1="(\d+)" v2="(\d+)" v3="(\d+)"', s)])
        p = v[t]
        n = np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0])
        n /= np.linalg.norm(n, axis=1)[:, None]
        c = p.mean(axis=1)
        xmid = (v[:, 0].min() + v[:, 0].max()) / 2
        zb = v[:, 2].min()
        cheeks = (n[:, 2] < -0.999) & (np.abs(c[:, 2] - (zb + CHEEK_Z)) < 0.05) & \
                 (np.abs(c[:, 0] - xmid) > CHEEK_X[0]) & (np.abs(c[:, 0] - xmid) < CHEEK_X[1])
        bosses = np.zeros(len(t), bool)
        for sx in (-1, 1):
            rx, rz = c[:, 0] - (xmid + sx * BOSS_X), c[:, 2] - (zb + BOSS_Z)
            rad = np.hypot(rx, rz)
            outward = (n[:, 0] * rx + n[:, 2] * rz) / np.maximum(rad, 1e-9)
            bosses |= (np.abs(rad - BOSS_R) < 0.08) & (outward > 0.9) & (n[:, 2] < -0.5)
        sel = cheeks | bosses
        idx = iter(range(len(t)))

        def mark(mo):
            i = next(idx)
            return mo.group(0)[:-2] + ' paint_supports="4"/>' if sel[i] else mo.group(0)
        out[name] = re.sub(r'<triangle v1="\d+" v2="\d+" v3="\d+"[^/]*/>', mark, s)
        painted += int(sel.sum())
        area = np.linalg.norm(np.cross(p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]), axis=1) / 2
        print(f"  {name}: {len(t)} triangles; cheeks {int(cheeks.sum())} ({area[cheeks].sum():.1f} mm2), "
              f"boss undersides {int(bosses.sum())} ({area[bosses].sum():.1f} mm2)")
        for sx in (-1, 1):
            b = bosses & (np.sign(c[:, 0] - xmid) == sx)
            if b.any():
                print(f"    boss {sx:+d}: x {np.round([c[b, 0].min() - xmid, c[b, 0].max() - xmid], 2)}, "
                      f"y {np.round([c[b, 1].min(), c[b, 1].max()], 2)}, z {np.round([c[b, 2].min() - zb, c[b, 2].max() - zb], 2)}")
    with zipfile.ZipFile(dst, "w", zipfile.ZIP_DEFLATED) as zout:
        for item in z.infolist():
            data = z.read(item.filename)
            if item.filename in out:
                data = out[item.filename].encode()
            elif item.filename == "Metadata/project_settings.config":
                ps = json.loads(data)
                n = len(ps["filament_settings_id"])
                ps["nozzle_volume_type"] = ["Standard", "High Flow"]      # as bs_project_finalize: the user's H2D
                ps["filament_map"] = ["1"] * n
                ps["filament_nozzle_map"] = ["0"] * n
                ps["filament_volume_map"] = ["0"] * n
                ps["extruder_ams_count"] = ["1#0|4#1", "1#0|4#1"]
                ps["wipe_tower_x"], ps["wipe_tower_y"] = ["165"], ["250"]
                data = json.dumps(ps, indent=4).encode()
            elif item.filename == "Metadata/model_settings.config":
                data = data.decode().replace(f'<metadata key="name" value="{STL_NAME}"/>',
                                             '<metadata key="name" value="P22 CPAP lower plenum (R43)"/>').encode()
            zout.writestr(item, data)
    return painted


def support_in_gcode(sliced):
    z = zipfile.ZipFile(sliced)
    g = z.read(next(n for n in z.namelist() if n.endswith(".gcode"))).decode(errors="replace")
    feat, layer_z, x, y = None, 0.0, None, None
    boxes = {}
    for line in g.splitlines():
        if line.startswith("; FEATURE:"):
            feat = line[10:].strip()
        elif line.startswith("; Z_HEIGHT:"):
            layer_z = float(line.split(":")[1])
        elif line.startswith("G1") and feat and "Support" in feat:
            mx, my = re.search(r"X([-\d.]+)", line), re.search(r"Y([-\d.]+)", line)
            if mx and my and "E" in line:
                b = boxes.setdefault(feat, [1e9, -1e9, 1e9, -1e9, 1e9, -1e9])
                xx, yy = float(mx.group(1)), float(my.group(1))
                b[:] = [min(b[0], xx), max(b[1], xx), min(b[2], yy), max(b[3], yy), min(b[4], layer_z), max(b[5], layer_z)]
    return {k: [round(v, 2) for v in b] for k, b in boxes.items()}


def main():
    OUT.mkdir(exist_ok=True)
    machine, process, fil = presets()
    files = {}
    for name, d in [("machine", machine), ("process", process)] + [(f"filament{i + 1}", f) for i, f in enumerate(fil)]:
        files[name] = OUT / f"{name}.json"
        files[name].write_text(json.dumps(d, indent=1), encoding="utf-8")
    stl, m = placed()
    print("P22 on the plate: bounds", np.round(m.bounds, 2).tolist())
    raw = OUT / "raw.3mf"
    cmd = [B.EXE, "--debug", "2", "--orient", "0", "--arrange", "0", "--allow-mix-temp", "--curr-bed-type", "Textured PEI Plate",
           "--load-settings", f"{files['machine']};{files['process']}",
           "--load-filaments", ";".join(str(files[f"filament{i + 1}"]) for i in range(len(fil))),
           "--outputdir", str(OUT), "--export-3mf", raw.name, str(stl)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    print("export exit", r.returncode)
    print("painted", paint(raw, OUT / PROJECT), "triangles")
    if "--no-slice" in sys.argv:          # the CLI can't slice project files here (see bs_r43_try*.py); slice in the GUI
        return
    res = OUT / "result.json"
    if res.exists():
        res.unlink()
    cmd = [B.EXE, "--debug", "2", "--allow-mix-temp", "--curr-bed-type", "Textured PEI Plate",
           "--load-settings", f"{files['machine']};{files['process']}",
           "--load-filaments", ";".join(str(files[f"filament{i + 1}"]) for i in range(len(fil))),
           "--slice", "0", "--outputdir", str(OUT), "--export-3mf", SLICED, str(OUT / PROJECT)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    print("slice exit", r.returncode)
    print(res.read_text() if res.exists() else "no result.json")
    if (OUT / SLICED).exists():
        print("support extrusion (x0, x1, y0, y1, z0, z1):", json.dumps(support_in_gcode(OUT / SLICED)))
        print("P22 centre", CENTRE, "| cheeks at |X - centre| 13.95-22.42, print height", CHEEK_Z)


if __name__ == "__main__":
    main()
