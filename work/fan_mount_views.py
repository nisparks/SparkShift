"""Views and sections of the R32 Red Lizard and Bambu bodies around the fan mounts (investigation only)."""

import sys
from pathlib import Path

sys.path.insert(0, r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")

import cadquery as cq
from PIL import Image, ImageDraw

from audit_low_z_bed_clearance import load_parked_variants
from build_modular_toolhead import box, load
from render_accessories_v26 import make_actor, render_view, shape_to_polydata

OUT = Path(r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files\inspect")
TMP = OUT / "fan_mounts_tmp.stl"
red = load_parked_variants()["RedLizard"]["tool"].Solids()
RL = {"body": load("RedLizard_Side2510_Flush_Side_R32_REVIEW"), "hotend": cq.Compound.makeCompound(red[1:14]),
      "fan": red[14], "screws": cq.Compound.makeCompound(red[15:19]), "P18": cq.Compound.makeCompound(red[19:])}
fan_sc = load("Bambu_Fan_2510_And_Screws_R30_REVIEW").Solids()
BB = {"body": load("Bambu_Compact_Flush_Side_R32_REVIEW"), "hotend": load("Tool2510_Reversed_Bambu_Reference_REVIEW"),
      "fan": [s for s in fan_sc if s.Volume() > 300][0],
      "screws": cq.Compound.makeCompound([s for s in fan_sc if s.Volume() <= 300] +
                                         load("Bambu_Fan_Side_M2p5_L4_Inserts_R30_REVIEW").Solids()),
      "P18": load("P18_Tool_docking_backplate_3010")}
COLORS = {"body": (0.95, 0.55, 0.15), "hotend": (0.72, 0.72, 0.75), "fan": (0.15, 0.15, 0.18),
          "screws": (0.85, 0.65, 0.2), "P18": (0.75, 0.2, 0.7)}


def panel(parts, keys, clip, eye, target, title, up=(0, 0, 1), zoom=1.0):
    actors = []
    for k in keys:
        part = parts[k].intersect(clip)
        if part.Solids():
            actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), COLORS[k], 1.0, edge_vis=True))
    path = OUT / "fan_mounts_panel.png"
    render_view(actors, eye, target, up, path, width=800, height=700, zoom=zoom)
    image = Image.open(path).convert("RGB")
    ImageDraw.Draw(image).text((10, 10), title, fill=(0, 0, 0))
    path.unlink()
    return image


def sheet(panels, cols, name):
    rows = (len(panels) + cols - 1) // cols
    out = Image.new("RGB", (800 * cols, 700 * rows), "white")
    for i, p in enumerate(panels):
        out.paste(p, (800 * (i % cols), 700 * (i // cols)))
    out.save(OUT / name)
    print(OUT / name, flush=True)


everything = box(-30, 30, 0, 50, -80, 50)
low = box(-30, 30, 0, 50, -80, -15.03)
panels = [
    panel(RL, ["body", "hotend", "fan", "screws", "P18"], low, (260, 260, -60), (8, 30, -35), "RL front-right, all"),
    panel(RL, ["body", "screws"], low, (260, 260, -60), (8, 30, -35), "RL body + fan screws/inserts only"),
    panel(RL, ["body", "screws"], low, (-200, 240, -160), (6, 30, -35), "RL body from front-left-below"),
    panel(RL, ["body", "hotend", "screws"], box(-30, 30, 33.53, 50, -80, -15.03), (10, 300, -35), (8, 33, -35),
          "RL section Y=33.5 looking -Y (front cut away)"),
    panel(RL, ["body", "hotend", "fan", "screws"], box(-30, 30, 0, 50, -80, -35.03), (10, 40, 300), (8, 25, -36),
          "RL section Z=-35 from above", up=(0, 1, 0)),
    panel(RL, ["body", "hotend", "screws"], box(9.47, 30, 0, 50, -80, -15.03), (-300, 25, -35), (9.5, 25, -35),
          "RL section X=9.5 looking +X... from -X"),
]
sheet(panels, 3, "rl_fan_mount_views.png")
panels = [
    panel(BB, ["body", "hotend", "fan", "screws", "P18"], low, (260, 260, -60), (8, 30, -40), "Bambu front-right, all"),
    panel(BB, ["body", "screws"], low, (260, 260, -60), (8, 30, -40), "Bambu body + fan screws/inserts"),
    panel(BB, ["body", "hotend", "screws"], box(-30, 30, 35.47, 50, -80, -15.03), (10, -300, -40), (6, 36, -40),
          "Bambu section Y=35.5 looking +Y (front kept)"),
    panel(BB, ["body", "hotend", "screws"], box(5.03, 30, 0, 50, -80, -15.03), (-300, 30, -40), (7, 30, -40),
          "Bambu section X=5 from -X"),
]
sheet(panels, 2, "bambu_fan_mount_views.png")
TMP.unlink(missing_ok=True)
