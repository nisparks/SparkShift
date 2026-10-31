"""Compose images/76_p20_p21_screws_r40_fusion.png from the Fusion review shots (session artifact)."""
import json
import os

from PIL import Image, ImageDraw, ImageFont

FILES = r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
W, H, BAND = 600, 375, 48


def panel(name, lines, font):
    shot = Image.open(os.path.join(FILES, name)).convert("RGB").resize((W, H), Image.LANCZOS)
    out = Image.new("RGB", (W, H + BAND), (255, 255, 255))
    out.paste(shot, (0, BAND))
    draw = ImageDraw.Draw(out)
    for i, line in enumerate(lines):
        draw.text((8, 5 + 14 * i), line, fill=(20, 20, 20), font=font)
    return out


def main():
    fusion = json.load(open(os.path.join(FILES, "fusion_review_r40_result.json")))
    g = fusion["native_gaps_mm"]
    font = ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf", 11)
    panels = [
        panel("f40_lugs.png", ["Fusion native review 40, from above with the EBB42 and P24 hidden: P20's lugs",
                               f"at X+-5.5 with ISO 7380 heads, {g['button_head_to_ebb42']:.2f} mm under the board; the cable between."],
              font),
        panel("f40_side.png", [f"Note, unchanged, from +X: P21's conduit meets the X beam's cut end ({g['p21_to_x_beam_note']:.2f} mm)",
                               f"and the probe cable runs {g['probe_cable_to_x_beam_note']:.2f} mm from it. Check on the first fit."],
              font),
        panel("f40_overall.png", [f"The revision-40 carriage from behind: {fusion['bodies']} bodies; P20 and P21",
                                  "volumes match the audit. The beam and rail are clipped references."], font),
    ]
    sheet = Image.new("RGB", (3 * W, H + BAND), (255, 255, 255))
    for i, p in enumerate(panels):
        sheet.paste(p, (i * W, 0))
    out = os.path.join(ROOT, "images", "76_p20_p21_screws_r40_fusion.png")
    sheet.save(out)
    print(out)


if __name__ == "__main__":
    main()
