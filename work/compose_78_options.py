"""Compose images/78_dock_colour_options.png from the four option previews (session artifact)."""
import os
from PIL import Image, ImageDraw, ImageFont

F = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
W, H, BAND = 760, 475, 30
font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 15)
bold = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 15)
rows = [
    ("rainbow", "Chosen: matching docks.", "Each bay is one colour, so the rack is a rainbow from the front and every tool's home bay is obvious."),
    ("complement", "Complementary docks.", "Each dock in the opposite colour to its tool: tools stand out from behind, but two offset rainbows are busy."),
    ("tonal", "Dark-shade docks.", "Each dock a darker version of its tool's colour: tools stand out from behind, but the front reads almost black."),
    ("purple", "All-violet docks.", "Calm and uniform, but from the front the rainbow only shows on the tool tops."),
]
sheet = Image.new("RGB", (2 * W, len(rows) * (H + BAND)), (255, 255, 255))
draw = ImageDraw.Draw(sheet)
for r, (name, title, text) in enumerate(rows):
    y0 = r * (H + BAND)
    for c, view in enumerate(("front", "rear")):
        im = Image.open(os.path.join(F, f"opt_{name}_{view}.png")).convert("RGB").resize((W, H), Image.LANCZOS)
        sheet.paste(im, (c * W, y0 + BAND))
    draw.text((10, y0 + 6), title, fill=(20, 20, 20), font=bold)
    draw.text((10 + draw.textlength(title, font=bold) + 6, y0 + 6), text + " Left: from the front; right: from behind.",
              fill=(20, 20, 20), font=font)
out = os.path.join(ROOT, "images", "78_dock_colour_options.png")
sheet.save(out, optimize=True)
print(out, sheet.size, round(os.path.getsize(out) / 1e6, 2), "MB")
