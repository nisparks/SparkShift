"""Label native v10 captures without altering the rendered geometry."""

import argparse
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFont


def crop(path):
    with Image.open(path) as source:
        image=source.convert("RGB")
    background=Image.new("RGB",image.size,image.getpixel((2,2)))
    mask=ImageChops.difference(image,background).convert("L").point(
        lambda value:255 if value>15 else 0)
    bounds=mask.getbbox()
    if bounds is None:
        raise RuntimeError("Empty native capture: "+str(path))
    return image.crop((max(0,bounds[0]-12),max(0,bounds[1]-12),
                       min(image.width,bounds[2]+12),min(image.height,bounds[3]+12)))


def panel(folder,name,title,items,note,width=850,height=780):
    canvas=Image.new("RGB",(len(items)*width,height+160),(238,241,245))
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf",23)
    small=ImageFont.truetype(r"C:\Windows\Fonts\segoeui.ttf",20)
    draw.text((18,14),title,font=font,fill=(20,25,35))
    for index,(label,file) in enumerate(items):
        image=crop(folder/file)
        image.thumbnail((width-36,height-60))
        canvas.paste(image,(index*width+(width-image.width)//2,
                           90+(height-60-image.height)//2))
        draw.text((index*width+18,54),label,font=small,fill=(35,40,50))
    draw.text((18,height+104),note,font=small,fill=(35,40,50))
    draw.text((18,height+133),"WIP - NOT READY FOR PRINTING. Native CAD renders, not physical qualification.",
              font=small,fill=(145,35,35))
    path=folder/name
    canvas.save(path)
    with Image.open(path) as saved:
        saved.verify()
    return path


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    folder=parser.parse_args().root/"images_v10"
    panels=[
        ("v10_exploded.png","SparkShift v10 - illustrative exploded assembly",[
            ("Exploded layout - front","v10_exploded_front_iso.png"),
            ("Exploded layout - rear","v10_exploded_rear_iso.png")],
         "Display translations only, not a validated installation sequence. F3D/STEP remain assembled.",
         1150,1000),
        ("v10_overview.png","SparkShift v10 - current assembly",[
            ("Closed reference pose","v10_assembly_closed_front_iso.png"),
            ("Open dwell: arm -6.053 deg / cam 150 deg","v10_assembly_open_front_iso.png")],
         "Blue: back case   Orange: front case   Red/blue: arm halves   Green: tool carrier"),
        ("v10_cases.png","User-edited cases retained",[
            ("Back case - inside","v10_back_case_front_iso.png"),
            ("Front case - inside","v10_front_case_rear_iso.png")],
         "Local floor repairs, snap capture and running reliefs are downstream of the user's history."),
        ("v10_pin_capture.png","Integral press/snap capture - upper-left coupling detail",[
            ("Empty seat and capture lips","v10_snap_empty_front_iso.png"),
            ("Steel contact tracks remain exposed","v10_snap_installed_front_iso.png")],
         "Nominal 1.5 mm pins; approximately 1.397 mm entry throat. Printed retention is unqualified."),
        ("v10_lower_clearance.png","Lower swing-arm passage - right-half native cutaways",[
            ("Closed reference pose","v10_lower_closed_low_front_iso.png"),
            ("Open dwell pose","v10_lower_open_low_front_iso.png")],
         "Tool omitted to expose the arm. Lower-corner relief: 0.25 mm nominal radial allowance."),
        ("v10_arm_connection.png","Two-piece swing arm - upper/lower clamps and central key",[
            ("Front/insert side","v10_arm_structure_front_iso.png"),
            ("Rear/screw side","v10_arm_structure_rear_iso.png")],
         "Gold: clamp screw/heat-set references. The two-piece arm and backed lower insert are retained."),
        ("v10_cam_cavity.png","Cam retainer - longitudinal native cutaway",[
            ("Blind head/washer cavity; exterior driver tunnel closed","v10_cam_blind_right.png")],
         "Preassemble the horn/cam bolt before closing the case. Actual servo thread remains unverified.",
         1200,640),
    ]
    for name,title,items,note,*size in panels:
        path=panel(folder,name,title,items,note,*size)
        print(path.name,path.stat().st_size,"bytes")


if __name__=="__main__":
    main()
