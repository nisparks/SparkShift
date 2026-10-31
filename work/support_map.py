"""Where Bambu Studio put supports on the CPAP plate (sliced with the user's preset, ABS interface), per overhang."""
import json
import re
import sys
from pathlib import Path

import numpy as np
import trimesh

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))
FILES = Path(__file__).resolve().parent
GCODE = FILES / "bs_cli" / "no_interface_filament" / "plate_1.gcode"
PLACED = FILES / "bs_cli" / "placed"
SUPPORT = ("Support", "Support interface", "Support transition")


def support_points():
    z, feat, x, y = 0.0, "", None, None
    pts = []
    for line in GCODE.open(encoding="utf-8", errors="ignore"):
        if line.startswith("; Z_HEIGHT:"):
            z = float(line.split(":")[1])
        elif line.startswith("; FEATURE:"):
            feat = line.split(":", 1)[1].strip()
        elif line.startswith(("G1 ", "G2 ", "G3 ")):
            mx, my, me = re.search(r"X([-\d.]+)", line), re.search(r"Y([-\d.]+)", line), re.search(r"E([-\d.]+)", line)
            nx = float(mx.group(1)) if mx else x
            ny = float(my.group(1)) if my else y
            if me and float(me.group(1)) > 0 and feat in SUPPORT and x is not None and nx is not None:
                for t in np.linspace(0, 1, 4):
                    pts.append((x + t * (nx - x), y + t * (ny - y), z, SUPPORT.index(feat)))
            x, y = nx, ny
    return np.array(pts)


def regions(mesh):
    n, cen, area = mesh.face_normals, mesh.triangles_center, mesh.area_faces
    slope = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))
    need = (n[:, 2] < 0) & (slope < 30.0) & (cen[:, 2] > 0.05)
    idx = np.nonzero(need)[0]
    hit = mesh.ray.intersects_any(cen[idx] - [0, 0, 0.01], np.tile([0, 0, -1.0], (len(idx), 1)))
    blocked = np.zeros(len(mesh.faces), bool)
    blocked[idx[hit]] = True
    sub = set(np.nonzero(blocked)[0].tolist())
    parent = {i: i for i in sub}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for a, b in mesh.face_adjacency:
        if a in sub and b in sub:
            parent[find(a)] = find(b)
    groups = {}
    for i in sub:
        groups.setdefault(find(i), []).append(i)
    out = []
    for g in groups.values():
        g = np.array(g)
        if area[g].sum() < 1.0:
            continue
        tri = mesh.triangles[g].reshape(-1, 3)
        out.append({"area_mm2": float(area[g].sum()), "lo": tri.min(axis=0), "hi": tri.max(axis=0),
                    "z": float((cen[g, 2] * area[g]).sum() / area[g].sum())})
    return sorted(out, key=lambda r: -r["area_mm2"])


def main():
    pts = support_points()
    print(f"support extrusion samples: {len(pts)}; z range {pts[:, 2].min():.2f}-{pts[:, 2].max():.2f}")
    report = {}
    for stl in sorted(PLACED.glob("*.stl")):
        part = stl.name[:3]
        mesh = trimesh.load_mesh(str(stl))
        lo, hi = mesh.bounds
        near = pts[(pts[:, 0] > lo[0] - 8) & (pts[:, 0] < hi[0] + 8) & (pts[:, 1] > lo[1] - 8) & (pts[:, 1] < hi[1] + 8)]
        inside = np.zeros(len(near), bool)
        rows = []
        for r in regions(mesh):
            sel = near[(near[:, 0] >= r["lo"][0]) & (near[:, 0] <= r["hi"][0]) & (near[:, 1] >= r["lo"][1]) &
                       (near[:, 1] <= r["hi"][1]) & (near[:, 2] <= r["z"] + 0.05) & (near[:, 2] >= r["z"] - 1.0)]
            top = sel[sel[:, 3] >= 1] if len(sel) else sel
            rows.append({"area_mm2": round(r["area_mm2"], 1), "print_z_mm": round(r["z"], 2),
                         "print_bbox_mm": [round(float(v), 1) for v in (*r["lo"][:2], *r["hi"][:2])],
                         "support_samples_below": int(len(sel)), "interface_samples_below": int(len(top))})
        report[part] = {"support_samples_near_part": int(len(near)), "support_samples_inside_part": int(inside.sum()),
                        "unsupported_from_straight_below": rows}
        print(f"== {part}: {len(near)} support samples near, {int(inside.sum())} inside the part's solid")
        for row in rows:
            ok = "SUPPORTED" if row["support_samples_below"] > 5 else "no support"
            print(f"   {row['area_mm2']:7.1f} mm2 at print z {row['print_z_mm']:6.2f} bbox {row['print_bbox_mm']}: "
                  f"{ok} ({row['support_samples_below']} samples, {row['interface_samples_below']} interface)")
    (FILES / "support_map.json").write_text(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
