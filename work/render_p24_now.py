"""Render P24 (current) with its neighbours from three angles (session look-see)."""
import json, os, sys
ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, ROOT); os.chdir(ROOT)
from PIL import Image, ImageDraw
import cadquery as cq
import build_and_verify_accessories_v26 as acc
import r37_parts as P37
import r40_parts as P
from build_modular_toolhead import box, load, primitives
from build_p24_cable_entry_r35 import NAMES as R35
from render_accessories_v26 import make_actor, render_view, shape_to_polydata
from render_bambu_clean_r29 import TMP

OUT = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
meta = json.loads((acc.WORK / "v26_meta.json").read_text())
v26 = {m["name"]: P37.shape(s) for m, (s, _) in zip(meta, acc.load_brep_list(acc.WORK / "v26_cache.brep"))}
motor = [v26[n] for n in v26 if n.startswith("AHG")]
p24 = load(R35["p24"])
items = [(p24, (0.55, 0.85, 0.2)), (P37.ebb42(), (0.1, 0.45, 0.2)), (load("P02_Motor_servo_plate_12p5mm"), (0.48, 0.25, 0.89)),
         (P.p21()[0], (0.1, 0.72, 0.9)), (v26["HOBBY_SERVO_ENVELOPE"], (0.12, 0.23, 0.54))] + [(m, (0.3, 0.3, 0.33)) for m in motor]
def view(sel, clip, eye, target, name, zoom):
    actors = []
    for shape, colour in sel:
        part = shape.intersect(clip)
        if part.isNull() or not part.Solids():
            continue
        actors.append(make_actor(shape_to_polydata(part.wrapped, TMP), colour, 1.0, edge_vis=True))
    path = os.path.join(OUT, name)
    render_view(actors, eye, target, (0, 0, 1), path, width=1000, height=900, zoom=zoom)
    return path
big = box(-40, 40, -60, 20, -40, 80)
t = (0, -15, 15)
paths = [
    view([items[0]], big, (120, -120, 90), t, "p24_now_alone_rear.png", 1.4),
    view([items[0]], big, (-110, 90, 60), t, "p24_now_alone_front.png", 1.4),
    view(items, box(-40, 40, -60, 20, -40, 80), (150, -170, 70), t, "p24_now_context.png", 1.3),
    view([i for i in items if i[0] is not items[1][0]], big, (0, -200, 15), t, "p24_now_from_back_noboard.png", 1.6),
]
ims = [Image.open(p).convert("RGB").resize((700, 630)) for p in paths]
sheet = Image.new("RGB", (1400, 1260), "white")
for k, im in enumerate(ims):
    sheet.paste(im, ((k % 2) * 700, (k // 2) * 630))
sheet.save(os.path.join(OUT, "p24_now_sheet.png"))
print("ok")
