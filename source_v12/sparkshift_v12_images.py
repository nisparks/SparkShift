"""Caption renders of the approved v12 WIP, not unapplied design studies."""

import argparse

from pathlib import Path
from sparkshift_v10_images import panel


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root",type=Path,required=True)
    folder=parser.parse_args().root/"images_v12"
    panels=[
        ("v12_exploded.png","SparkShift v12 - approved illustrative exploded assembly",[
            ("Front view","v12_exploded_front_iso.png"),
            ("Rear view","v12_exploded_rear_iso.png")],
         "Display translations only, not a validated installation sequence. F3D/STEP remain assembled.",
         1150,1000),
        ("v12_overview.png","SparkShift v12 - approved current WIP",[
            ("Closed reference pose - five flush case heads","v12_assembly_closed_front_iso.png"),
            ("Open dwell - original toolhead retained","v12_assembly_open_front_iso.png")],
         "Orange/blue: case halves   Red/blue: arm halves   Green: original tool carrier"),
        ("v12_cases.png","Preserved case refinements and mating split",[
            ("Blue carriage/rear case","v12_back_case_front_iso.png"),
            ("Yellow front case - inspected native solid","v12_front_case_rear_iso.png")],
         "User edits retained. Complete paired docking symmetry and further surface refinement remain WIP."),
        ("v12_pin_capture.png","Integral locating-pin capture - approved current geometry",[
            ("Empty receiver","v12_snap_empty_front_iso.png"),
            ("Steel contact tracks remain exposed","v12_snap_installed_front_iso.png")],
         "Nominal 1.5 mm pins. Actual printed snap force and retention remain unqualified."),
        ("v12_lower_clearance.png","Current lower casing with the unchanged tool carrier",[
            ("Closed reference pose","v12_lower_closed_low_front_iso.png"),
            ("Open dwell pose","v12_lower_open_low_front_iso.png")],
         "Functional tool passage retained. The rejected shelf and shorter hotend screws are absent."),
        ("v12_arm_connection.png","User-refined two-piece arm - upper/lower heat-set clamps",[
            ("Front/insert side","v12_arm_structure_front_iso.png"),
            ("Rear/screw side","v12_arm_structure_rear_iso.png")],
         "Latest user face/fillet/chamfer changes retained. Loaded stiffness and insert pullout are unqualified."),
        ("v12_cam_cavity.png","Approved cam retainer - native longitudinal cutaway",[
            ("Blind running cavity; tool-top clearance retained","v12_cam_blind_right.png")],
         "Assemble horn/cam retainer before case closure. Actual servo thread still needs confirmation.",
         1200,640),
        ("v12_insert_stack.png","Case-clamp heat-set installation and capture",[
            ("Native cutaway - purple insert captured by blue","v12_plate_insert_front_iso.png"),
            ("Lower-right insert loaded from bare rear case","v12_case_insert_rear_iso.png")],
         "Real heat-sets, no captive nuts. Install before closing plate/case access; physical fit remains WIP.",
         1050,850),
    ]
    for name,title,items,note,*size in panels:
        path=panel(folder,name,title,items,note,*size)
        print(path.name,path.stat().st_size,"bytes")


if __name__=="__main__":
    main()
