"""Compose images/77_print_colour_scheme.png from the Fusion colour-review shots (session artifact)."""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, ROOT)
import print_colors as C  # noqa: E402

BAND = 46
WIDE, NARROW, ROW_H = (1200, 720), (600, 720), 720
FONT = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 14)
BOLD = ImageFont.truetype(r"C:\Windows\Fonts\segoeuib.ttf", 15)
SMALL = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 13)


def fit(name, size):
    img = Image.open(os.path.join(FILES, name)).convert("RGB")
    bg = img.getpixel((2, 2))
    diff = Image.new("L", img.size, 0)
    px, dp = img.load(), diff.load()
    for y in range(0, img.height, 2):
        for x in range(0, img.width, 2):
            p = px[x, y]
            if max(abs(p[i] - bg[i]) for i in range(3)) > 14:
                dp[x, y] = 255
    box = diff.getbbox() or (0, 0, img.width, img.height)
    pad = 24
    box = (max(0, box[0] - pad), max(0, box[1] - pad), min(img.width, box[2] + pad), min(img.height, box[3] + pad))
    img = img.crop(box)
    scale = min(size[0] / img.width, size[1] / img.height)
    img = img.resize((int(img.width * scale), int(img.height * scale)), Image.LANCZOS)
    out = Image.new("RGB", size, bg)
    out.paste(img, ((size[0] - img.width) // 2, (size[1] - img.height) // 2))
    return out


def panel(name, size, lines):
    out = Image.new("RGB", (size[0], size[1] + BAND), (255, 255, 255))
    out.paste(fit(name, size), (0, BAND))
    draw = ImageDraw.Draw(out)
    for i, line in enumerate(lines):
        draw.text((10, 4 + 19 * i), line, fill=(20, 20, 20), font=FONT)
    return out


def swatch(draw, x, y, colour, size=20):
    draw.rectangle((x, y, x + size, y + size), fill=C.PALETTE.get(colour, C.OTHER.get(colour, colour)),
                   outline=(120, 120, 120))


def legend(width):
    columns = [
        ("Carriage", [("P03 front case", "Violet"), ("P01 back case", "Magenta"), ("P02 motor/servo plate", "Violet"),
                      ("P04F, P04R swing arm", "Orange"), ("P05 servo cam", "Yellow"), ("P15, P16 belt arches", "Yellow"),
                      ("P06, P07 compounds (inside)", "Green"), ("P08, P09 HGX drives (inside)", "Cyan"),
                      ("P12 spring cup (inside)", "Yellow"), ("P13, P14 tooth liners (inside)", "Orange")]),
        ("Air path, probe and controller", [("P27 CPAP blower mount", "Violet"), ("P20 CPAP hose inlet", "Blue"),
                                            ("P21 CPAP gantry bridge", "Cyan"), ("P22 CPAP lower plenum (GF ABS or ASA)", "Teal"),
                                            ("P23 probe mount", "Lime"), ("P24 EBB42 mount", "Lime")]),
        ("Bays: one filament each", [("Tool body, P18, P25 dock, jaws and P26 chute", None),
                                     ("Ooze pad and wiper: silicone, not printed", "silicone")]),
        ("Rack and jig", [("P29 rack mounts", "Magenta"), ("P30 side spacers", "Violet"), ("P28 calibration jig", "Yellow"),
                          ("Your X-gantry parts, unchanged", "existing")]),
    ]
    height = 330
    out = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(out)
    col_w = width // 4
    for c, (title, rows) in enumerate(columns):
        x0 = 14 + c * col_w
        draw.text((x0, 10), title, fill=(20, 20, 20), font=BOLD)
        for r, (label, colour) in enumerate(rows):
            y = 40 + 27 * r
            if colour is None:
                for k in range(10):
                    draw.rectangle((x0 + 8 * k, y, x0 + 8 * k + 7, y + 20), fill=C.PALETTE[C.TOOLS[k]])
                draw.text((x0 + 88, y + 1), label, fill=(20, 20, 20), font=SMALL)
                continue
            swatch(draw, x0, y, colour)
            text = f"{label}: {colour}" if colour in C.PALETTE else label
            draw.text((x0 + 28, y + 1), text, fill=(20, 20, 20), font=SMALL)
    x0, y0 = 14 + 2 * col_w, 40 + 27 * 5 + 6
    draw.text((x0, y0), "Bays by tool number (tool bodies in GF ABS or ASA)", fill=(20, 20, 20), font=BOLD)
    for k, colour in enumerate(C.TOOLS):
        x = x0 + (k % 5) * 170
        y = y0 + 30 + (k // 5) * 30
        swatch(draw, x, y, colour)
        draw.text((x + 28, y + 1), f"T{k} {colour}", fill=(20, 20, 20), font=SMALL)
    return out


def main():
    rows = [
        (panel("c77_rear.png", WIDE, ["Fusion document 'SparkShift print colours', from behind: each bay is one colour, T9 (magenta, left)",
                                      "to T0 (red, right). The carriage is withdrawn from bay T4 with the green tool."]),
         panel("c77_car_rear.png", NARROW, ["Carriage from behind, rack and gantry hidden: the air path in cool",
                                            "colours along the flow; P24 lime holds the EBB42."])),
        (panel("c77_front.png", WIDE, ["From the front, the view through the door: the docks make the rainbow, each under its own tool.",
                                       "P29 magenta and P30 violet bookend the rack; the black end blocks are your own X-gantry parts."]),
         panel("c77_car_front.png", NARROW, ["Carriage from the front: violet P03 frames the tool; magenta back",
                                             "case, orange swing arm, yellow cam and belt arches."])),
    ]
    width = WIDE[0] + NARROW[0]
    key = legend(width)
    sheet = Image.new("RGB", (width, 2 * (ROW_H + BAND) + key.height), (255, 255, 255))
    for r, (a, b) in enumerate(rows):
        sheet.paste(a, (0, r * (ROW_H + BAND)))
        sheet.paste(b, (WIDE[0], r * (ROW_H + BAND)))
    sheet.paste(key, (0, 2 * (ROW_H + BAND)))
    out = os.path.join(ROOT, "images", "77_print_colour_scheme.png")
    sheet.save(out, optimize=True)
    print(out, sheet.size, round(os.path.getsize(out) / 1e6, 2), "MB")


if __name__ == "__main__":
    main()
