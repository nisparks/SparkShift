"""Preserve the live user-edited cases and repair only source-bound breakthroughs."""

import hashlib
import importlib.util
import json
import math
import sys
import types
from pathlib import Path

import adsk.core
import adsk.fusion


BASE=Path(__file__).resolve().parent
OUT=BASE/"sparkshift_case_update_v10"
STATE={}
CASE="PRINT_000_outer_shell_of_extruder_1"
BACK="PRINT_motor_mount"


def load(name):
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,BASE/(name+".py"))
        module=importlib.util.module_from_spec(spec)
        sys.modules[name]=module
        spec.loader.exec_module(module)
    return sys.modules[name]


def by_name(app):
    return {b.name:b for b in load("pancake_paths_study").proxies(
        adsk.fusion.Design.cast(app.activeProduct).rootComponent)}


def initialize(app):
    if STATE:
        raise RuntimeError("User-edit baseline already captured")
    OUT.mkdir(parents=True,exist_ok=True)
    path=OUT/"cad"/"Input_user_case_edits.f3d"
    if not path.exists():
        raise RuntimeError("Export the live user-edited assembly before cloning")
    s=load("pancake_paths_study")
    stats=load("sparkshift_cam_v8").stats
    original=app.activeDocument
    before={n:s.tbm().copy(b) for n,b in by_name(app).items()}
    expected={n:stats(b) for n,b in before.items()}
    opened=app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(path)))
    try:
        current=by_name(app)
        if set(current)!=set(before):
            raise RuntimeError("User-edit snapshot inventory changed")
        for name in before:
            if stats(current[name])!=expected[name]:
                raise RuntimeError("User-edit snapshot mismatch: "+name)
    except RuntimeError:
        opened.close(False)
        original.activate()
        raise
    opened.name="SparkShift user case update v10 - WIP review"
    helper_path=BASE/"sparkshift_surface_cleanup.py"
    helper=types.ModuleType("sparkshift_v10_checks")
    helper.__file__=str(helper_path)
    code=helper_path.read_text(encoding="utf-8").replace("v9_","v10_").replace("images_v9","images_v10").replace("stl_v9","stl_v10")
    exec(compile(code,str(helper_path),"exec"),helper.__dict__)
    helper.initialize(app,output=OUT)
    STATE.update(source_document=original,document=opened.creationId,
                 before=before,helper=helper)
    report={"input_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "source_document":original.name,"review_document":opened.name,
            "body_count":len(before),"case_baselines":{n:expected[n] for n in (CASE,BACK)},
            "user_history_preserved":True}
    (OUT/"user_edit_baseline.json").write_text(json.dumps(report,indent=2))
    return report


def require_review(app):
    if app.activeDocument.creationId!=STATE["document"]:
        raise RuntimeError("Activate the owned v10 review copy, not the user source")


def inspect_interfaces(app):
    require_review(app)
    m=load("sparkshift_ahg_min")
    case=by_name(app)[CASE]
    regions={"left_upper_socket":(-11,-3,26,32,34.5,42.5),
             "right_upper_socket":(3,11,26,32,34.5,42.5),
             "upper_magnet_corners":(-11,11,26,32,30,35)}
    report={}
    for label,region in regions.items():
        faces=[]
        for i,face in enumerate(case.faces):
            bb=m.bb_of(face)
            if m.bb_gap_l(bb,region)>0 or face.area*100>150:
                continue
            g=face.geometry
            row={"i":i,"type":type(g).__name__,"area_mm2":face.area*100,"bounds_mm":bb}
            if isinstance(g,adsk.core.Cylinder):
                row.update(radius_mm=g.radius*10,
                           origin_mm=[g.origin.x*10,g.origin.y*10,g.origin.z*10])
            if isinstance(g,adsk.core.Plane):
                row["normal"]=[g.normal.x,g.normal.y,g.normal.z]
            faces.append(row)
        report[label]=faces
    (OUT/"case_interface_faces.json").write_text(json.dumps(report,indent=2))
    return {label:len(rows) for label,rows in report.items()}


def review_contacts(app,poses=None):
    require_review(app)
    helper=STATE["helper"]
    w=load("sparkshift_cam_v8")
    names=[CASE,BACK,"PRINT_carrier_box_left","PRINT_arm_front_half","PRINT_DIRECT_CAM",
           "PRINT_REAR_MOTOR_SERVO_SPACER","PRINT_RedLizard_HF_tool_carrier",
           "TOOL_06_Tool_head_back_part_1"]
    result=helper.contacts(app,names,poses=w.POSES if poses is None else poses)
    limits={frozenset((CASE,"SPRING_PRELOAD_M3_HEATSET")):1.44,
            frozenset((BACK,"FRAME_M3_HEATSET_in_P01")):16.22,
            frozenset(("PRINT_carrier_box_left","STOCK_047_3mm_flange_bearing_1_1")):.051,
            frozenset(("PRINT_arm_front_half","ARM_SPLIT_M3_INSERT_0")):16.22,
            frozenset(("PRINT_arm_front_half","ARM_LOWER_M3_HEATSET_4p6x4")):16.22}
    limits.update({frozenset((BACK,"CLAM_M3_FRAME_INSERT_"+str(i))):1.44 for i in range(4)})
    limits.update({frozenset((BACK,"SPACER_M3_HEATSET_"+str(i))):16.22 for i in range(2)})
    limits.update({frozenset(("PRINT_RedLizard_HF_tool_carrier",n)):2.0
                   for n in ("OCT_TOOL_09_M3_heatset_nut_small:1","OCT_TOOL_20_M3_heatset_nut_small:2",
                             "OCT_TOOL_21_M3_heatset_nut_small:3","OCT_TOOL_22_M3_heatset_nut_small:4")})
    limits.update(STATE.get("press_reference_limits",{}))
    overlaps=result["unexpected_overlaps"]+result["inherited_overlaps"]+result["press_fits"]
    unexpected=[r[:5] for r in overlaps if r[4]>limits.get(frozenset((r[2],r[3])),0)]
    report={"poses":result["poses"],"unexpected_overlaps":unexpected,
            "declared_press_fit_count":len(overlaps)-len(unexpected),"errors":result["errors"],
            "note":"Fresh user input is not treated as permission to inherit accidental clashes"}
    (OUT/"current_case_contacts.json").write_text(json.dumps(report,indent=2))
    return report


def repair_floors(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    helper=STATE["helper"]
    by=by_name(app)
    ball=by["OCT_TOOL_05_4mm_ball:1"]
    sphere=next(f.geometry for f in ball.faces if isinstance(f.geometry,adsk.core.Sphere))
    centre=(sphere.origin.x*10,sphere.origin.z*10)
    floor=sphere.origin.y*10-2.2
    helper.append_join(app,CASE,s.cyl(*centre,floor-1.5,floor,3.6),
                       "V10 complete coupling socket backing")
    helper.append_cut(app,CASE,s.cyl(*centre,floor,31.5,2.170352454704739),
                      "V10 preserve coupling socket clearance")
    magnet=by["OCT_RECEIVER_MAGNET_2"]
    mb=m.bb_of(magnet)
    rectangle=s.box(mb[0]-.1,mb[1]+.1,mb[2]-1.5,mb[2],mb[4]-.1,mb[5]+.1)
    helper.append_join(app,CASE,rectangle,"V10 complete upper magnet-pocket backing")
    report={"socket_centre_xz_mm":centre,"socket_floor_y_mm":floor,
            "socket_backing_mm":1.5,"magnet_backing_mm":1.5,
            "pin_and_ball_positions_changed":False,
            "user_features_rewritten":False}
    STATE["floor_repairs"]=report
    (OUT/"floor_repairs.json").write_text(json.dumps(report,indent=2))
    return report


def add_snap_seats(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    helper=STATE["helper"]
    by=by_name(app)
    report=[]
    face_y=31.5
    for name in sorted(n for n in by if n.startswith("OCT_LOCATOR_PIN_")):
        pin=by[name]
        cylinder=next(f.geometry for f in pin.faces if isinstance(f.geometry,adsk.core.Cylinder))
        origin=(cylinder.origin.x*10,cylinder.origin.y*10,cylinder.origin.z*10)
        axis=(cylinder.axis.x,cylinder.axis.y,cylinder.axis.z)
        if abs(axis[1])>1e-6:
            raise RuntimeError("The current pin axes are not in the contact plane")
        ends=[]
        for edge in pin.edges:
            curve=edge.geometry
            if isinstance(curve,adsk.core.Circle3D):
                d=cylinder.origin.vectorTo(curve.center).dotProduct(cylinder.axis)*10
                if all(abs(d-old)>1e-4 for old in ends):
                    ends.append(d)
        ends.sort()
        if len(ends)!=2 or abs(ends[1]-ends[0]-4.9)>.01:
            raise RuntimeError("Pin length no longer matches the captured reference")
        bands=((ends[0]+.15,ends[0]+.75),(ends[1]-.5,ends[1]))
        cavities=[]
        for index,(a,b) in enumerate(bands):
            outer=m.axis_cyl(origin,axis,1.3,a,b)
            s.op(outer,s.box(-25,25,28.0,face_y,-20,50),"common")
            cavity=m.axis_cyl(origin,axis,.75,a-.001,b+.001)
            s.op(outer,cavity,"cut")
            helper.append_join(app,CASE,outer,"V10 snap band "+name+" "+str(index+1))
            cavities.append(cavity)
        # Keep the original V seating and the exposed middle contact tracks; only
        # the two short end bands provide >180 degree capture.
        opening_height=face_y-origin[1]
        throat=2*math.sqrt(.75*.75-opening_height*opening_height)
        report.append({"pin":name,"pin_axis":axis,"origin_mm":origin,
                       "seat_diameter_mm":1.5,"nominal_throat_mm":throat,
                       "outer_diameter_mm":2.6,"capture_bands_mm":bands,
                       "adhesive":False,"separate_keeper":False,
                       "nominal_pin_positions_changed":False,
                       "fit_limit":"Snap insertion, stiffness and retention need material/printer calibration"})
    STATE["snap_seats"]=report
    (OUT/"snap_pin_seats.json").write_text(json.dumps(report,indent=2))
    return report


def clear_socket_backing(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    helper=STATE["helper"]
    by=by_name(app)
    sphere=next(f.geometry for f in by["OCT_TOOL_05_4mm_ball:1"].faces
                if isinstance(f.geometry,adsk.core.Sphere))
    centre=(sphere.origin.x*10,sphere.origin.z*10)
    floor=sphere.origin.y*10-2.2
    tool=m.arc_slot(centre,3.9,-.3,7,floor-1.8,30.01)
    helper.append_cut(app,"PRINT_arm_front_half",tool,
                      "V10 rounded upper-corner clearance behind coupling socket")
    report={"socket_axis_xz_mm":centre,"radius_mm":3.9,
            "nominal_pad_clearance_mm":.3,"arm_inverse_angles_deg":[-.3,7],
            "region":"Front plate's remote upper corner; through the print face, not a thin skin",
            "bearing_and_fastener_stations_changed":False}
    (OUT/"socket_arm_clearance.json").write_text(json.dumps(report,indent=2))
    return report


def coplanar_groups(body):
    faces=list(body.faces)
    index={f.tempId:i for i,f in enumerate(faces)}
    eligible={}
    for i,f in enumerate(faces):
        if not isinstance(f.geometry,adsk.core.Plane):
            continue
        ok,n=f.evaluator.getNormalAtPoint(f.pointOnFace)
        if not ok:
            raise RuntimeError("Cannot classify the current plane")
        point=f.pointOnFace
        eligible[i]=(n,sum(a*b*10 for a,b in zip((n.x,n.y,n.z),(point.x,point.y,point.z))))
    pending=set(eligible)
    groups=[]
    while pending:
        component={pending.pop()}
        frontier=list(component)
        while frontier:
            i=frontier.pop()
            n,d=eligible[i]
            for edge in faces[i].edges:
                for adjacent in edge.faces:
                    j=index.get(adjacent.tempId)
                    if j not in pending:
                        continue
                    other,offset=eligible[j]
                    if n.dotProduct(other)>.999999999 and abs(d-offset)<1e-5:
                        pending.remove(j)
                        component.add(j)
                        frontier.append(j)
        if len(component)>1:
            groups.append(sorted(component))
    return groups


def close_cam_access(app):
    require_review(app)
    s,m,w=load("pancake_paths_study"),load("sparkshift_ahg_min"),load("sparkshift_cam_v8")
    helper=STATE["helper"]
    c=w.STATE["C"]
    front=m.bb_of(by_name(app)[CASE])[3]
    helper.append_join(app,CASE,s.cyl(*c,13.2,front,3.21),
                       "V10 close unnecessary exterior cam access tunnel")
    helper.append_cut(app,CASE,s.cyl(*c,13.15,13.55,3.2),
                      "V10 retain bearing inner-ring relief")
    helper.append_cut(app,CASE,s.cyl(*c,13.55,16.35,2.85),
                      "V10 blind head washer and journal cavity")
    report={"axis_xz_mm":c,"outside_access":False,
            "outer_face_y_mm":front,"blind_cavity_end_y_mm":16.35,
            "running_cavity_diameter_mm":5.7,"head_end_y_mm":16.0,
            "head_axial_clearance_mm":.35,
            "assembly_order":"Secure cam/horn centre bolt on the bench before the case halves close",
            "bearing_seat_changed":False}
    STATE["cam_access"]=report
    (OUT/"cam_access_closed.json").write_text(json.dumps(report,indent=2))
    return report


def merge_coplanar(app,name):
    require_review(app)
    helper,s=STATE["helper"],load("pancake_paths_study")
    attempted=set()
    reports=[]
    for _ in range(30):
        body=by_name(app)[name]
        groups=coplanar_groups(body)
        choices=[]
        for group in groups:
            master=max(group,key=lambda i:body.faces.item(i).area)
            indices=[i for i in group if i!=master]
            signature=tuple(round(v,6) for i in group for v in
                            load("sparkshift_ahg_min").bb_of(body.faces.item(i)))
            if signature not in attempted:
                choices.append((group,indices,signature))
        if not choices:
            break
        group,indices,signature=choices[0]
        attempted.add(signature)
        before=s.tbm().copy(body)
        row=helper.heal_indices(app,name,indices,"V10 merge coincident plane patches",
                                side_planes=False,axial_planes=False,
                                metadata={"coplanar_faces":len(group)})
        if row["status"]!="failed":
            after=by_name(app)[name]
            added=s.tbm().copy(after);s.op(added,before,"cut")
            removed=s.tbm().copy(before);s.op(removed,after,"cut")
            delta=(added.volume+removed.volume)*1000
            row["solid_difference_mm3"]=delta
            if delta>1e-5:
                feature=helper.STATE["accepted"][name].pop()
                feature.deleteMe()
                row["status"]="reverted-geometric-change"
        reports.append({"status":row["status"],"group_faces":len(group),
                        "difference_mm3":row.get("solid_difference_mm3"),
                        "error":row.get("error")})
    result={"part":name,"operations":reports,"remaining_groups":coplanar_groups(by_name(app)[name]),
            "final_faces":by_name(app)[name].faces.count}
    (OUT/("coplanar_merge_"+name+".json")).write_text(json.dumps(result,indent=2))
    return result


def clear_lower_arm_corner(app):
    require_review(app)
    helper,s,m=STATE["helper"],load("pancake_paths_study"),load("sparkshift_ahg_min")
    label="V10 continuous lower swing-arm corner clearance"
    component=(by_name(app)[CASE].nativeObject or by_name(app)[CASE]).parentComponent
    if any(feature.name==label for feature in component.features):
        raise RuntimeError("The lower corner clearance is already applied")
    centre=(15.4,-9.8794047847718)
    arm=by_name(app)["PRINT_carrier_box_left"]
    matches=[face.geometry for face in arm.faces
             if isinstance(face.geometry,adsk.core.Cylinder)
             and abs(face.geometry.axis.y)>.999999
             and math.dist((face.geometry.origin.x*10,face.geometry.origin.z*10),centre)<1e-5
             and abs(face.geometry.radius*10-2.2)<1e-5]
    if not matches:
        raise RuntimeError("The reviewed lower-arm corner has changed")
    before=s.tbm().copy(by_name(app)[CASE])
    tool=m.arc_slot(centre,2.45,-7.0,.3,11.75,15.85)
    row=helper.append_cut(app,CASE,tool,label)
    removed=s.tbm().copy(before)
    s.op(removed,by_name(app)[CASE],"cut")
    report={"corner_centre_xz_mm":centre,"corner_radius_mm":2.2,
            "clearance_radius_mm":2.45,"radial_allowance_mm":.25,
            "arm_angles_deg":[-7.0,.3],"y_mm":[11.75,15.85],
            "removed_mm3":removed.volume*1000,"removed_bounds_mm":m.bb_of(removed),
            "user_history_rewritten":False,"native_operation":row}
    STATE["lower_corner_clearance"]=report
    (OUT/"lower_corner_clearance.json").write_text(json.dumps(report,indent=2))
    return report


def capture_views(app,slug,names,centre,extent,views=("front_iso",),
                  arm_deg=0,cam_deg=0,clip=None,translations=None,extra_shapes=None):
    current=require_verified_geometry(app)
    if current!=STATE.get("exported_geometry_stats"):
        raise RuntimeError("The visual source differs from the current CAD exports")
    s,m,w=load("pancake_paths_study"),load("sparkshift_ahg_min"),load("sparkshift_cam_v8")
    source_design=adsk.fusion.Design.cast(app.activeProduct)
    original,by=app.activeDocument,by_name(app)
    colours={BACK:(70,130,210),CASE:(225,155,65),
             "PRINT_REAR_MOTOR_SERVO_SPACER":(150,95,185),
             "PRINT_carrier_box_left":(205,65,80),
             "PRINT_arm_front_half":(55,145,220),
             "PRINT_DIRECT_CAM":(170,90,200),
             "PRINT_RedLizard_HF_tool_carrier":(85,180,115),
             "TOOL_06_Tool_head_back_part_1":(75,150,105),
             "ARM_SPLIT_M3x10_SHCS_0":(235,190,50),
             "ARM_SPLIT_M3_INSERT_0":(210,150,50),
             "ARM_LOWER_M3x14_BUTTON_HEAD":(235,190,50),
             "ARM_LOWER_M3_HEATSET_4p6x4":(210,150,50),
             "CLAM_M3_FRAME_INSERT_2":(210,150,50),
             "CLAM_M3_FRAME_INSERT_3":(210,150,50),
             "SPRING_PRELOAD_M3_HEATSET":(210,150,50)}
    snapshots={n:w.stats(b) for n,b in by.items()}
    if translations is not None:
        if set(translations)!=set(names):
            raise RuntimeError("Every exploded-view body needs an explicit display translation")
        if any(len(delta)!=3 or not all(math.isfinite(value) for value in delta)
               for delta in translations.values()):
            raise RuntimeError("An exploded-view translation is invalid")
    shapes=[]
    for name in names:
        body=by[name]
        path=body.assemblyContext.fullPathName
        shape=s.tbm().copy(body)
        if name in w.CAM_ROTATES and cam_deg:
            shape=m.rotated(shape,w.STATE["C"],cam_deg)
        elif any(part in path for part in m.ARM_GROUPS) and arm_deg:
            shape=m.rotated(shape,w.STATE["Mv"],arm_deg)
        if translations is not None:
            delta=translations[name]
            shape=m.translated(shape,dx=delta[0],dy=delta[1],dz=delta[2])
        if clip is not None:
            s.op(shape,s.box(*clip),"common")
            if not shape.lumps.count:
                continue
        shapes.append((name,shape))
    reference_names=[]
    for name,shape,colour in extra_shapes or ():
        if name in by or name in reference_names:
            raise RuntimeError("A visual reference duplicates an assembly body")
        if not shape.isSolid or not math.isfinite(shape.volume) or shape.volume<=0:
            raise RuntimeError("The visual reference is not a valid solid")
        shapes.append((name,s.tbm().copy(shape)))
        colours[name]=colour
        reference_names.append(name)
    if not shapes:
        raise RuntimeError("The documentation view contains no native solids")
    template=source_design.appearances.itemByName("SparkShift arm")
    if template is None:
        raise RuntimeError("The native visual palette is missing")
    old_camera=app.activeViewport.camera
    old_folder=m.IMAGES_V4
    folder=OUT/"images_v10"
    folder.mkdir(parents=True,exist_ok=True)
    m.IMAGES_V4=folder
    owned=None
    files=[]
    captured=[]
    try:
        owned=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        owned.name="OWNED v10 native visual - disposable "+slug
        design=adsk.fusion.Design.cast(app.activeProduct)
        design.designType=adsk.fusion.DesignTypes.DirectDesignType
        design.appearances.addByCopy(template,"SparkShift arm")
        appearances={}
        for name,shape in shapes:
            colour=colours.get(name,(130,165,120) if name.startswith("PRINT_") else (175,185,200))
            if colour not in appearances:
                appearances[colour]=m.rgb_appearance(
                    design,"v10 documentation "+"_".join(map(str,colour)),colour)
            appearance=appearances[colour]
            body=design.rootComponent.bRepBodies.add(shape)
            if body is None:
                raise RuntimeError("Cannot add the native visual copy: "+name)
            body.name=name
            body.appearance=appearance
            for face in body.faces:
                face.appearance=appearance
            captured.append(name)
        ui=app.userInterface
        ui.activeSelections.clear()
        for suffix,eye,target,up,ext in m.std_views(centre,extent,views):
            file="v10_"+slug+suffix+".png"
            m.camera_shot(app,file,eye,target,up,ext)
            path=folder/file
            if not path.exists() or path.stat().st_size<1000:
                raise RuntimeError("Missing native documentation image: "+file)
            files.append(file)
    finally:
        try:
            if owned is not None and owned.isValid and not owned.close(False):
                raise RuntimeError("Cannot close the disposable native visual")
        finally:
            original.activate()
            m.IMAGES_V4=old_folder
            app.activeViewport.camera=old_camera
            app.activeViewport.refresh()
    if snapshots!={n:w.stats(b) for n,b in by_name(app).items()}:
        raise RuntimeError("Native documentation changed the assembly geometry")
    report={"files":files,"bodies":captured,"arm_deg":arm_deg,"cam_deg":cam_deg,
            "section_box_mm":clip,"native_geometry_unchanged":True,
            "disposable_document_closed":True,
            "illustrative_translations_mm":translations,
            "visual_only_reference_bodies":reference_names,
            "native_source_sha256":json.loads((OUT/"v10_cad_export.json").read_text())["exports"]["f3d"]["sha256"]}
    (OUT/("visual_"+slug+".json")).write_text(json.dumps(report,indent=2))
    return report


def capture_exploded_views(app):
    require_verified_geometry(app)
    by=by_name(app)
    names=sorted(n for n in by if not n.startswith("REFERENCE_")
                 and n!="CLOSING_SPRING_ENVELOPE")
    front_supports={CASE,"STOCK_014_3mm_flange_bearing_2",
                    "STOCK_015_4mm_flange_bearing_2",
                    "STOCK_063_4mm_flange_bearing_front_frame_left",
                    "CAM_OUTBOARD_MF85ZZ_5x8x2p5",
                    "SPRING_PRELOAD_THRUST_BALL_4mm","SPRING_PRELOAD_M3x6_GRUB",
                    "SPRING_PRELOAD_M3_HEATSET"}
    front_arm={"PRINT_arm_front_half","STOCK_049_3mm_flange_bearing_1_2",
               "STOCK_050_4mm_flange_bearing_1_2",
               "ARM_SPLIT_M3_INSERT_0","ARM_LOWER_M3_HEATSET_4p6x4"}
    rear_supports={"MR74 4x7x2 fixed axle rear (pin plate C-seat)",
                   "MR74 4x7x2 moving axle rear (pin plate)"}
    if (front_supports|front_arm|rear_supports)-set(names):
        raise RuntimeError("The exploded-view support inventory no longer matches the audited model")
    translations={}
    for name in names:
        path=by[name].assemblyContext.fullPathName
        y=0.0
        if path.startswith("01 "):
            y=-25.0
        if path.startswith("12 "):
            y=125.0
        if (path.startswith("LDO-") or path.startswith("10 ") or
                name=="PRINT_REAR_MOTOR_SERVO_SPACER" or
                name=="HOBBY_SERVO_ENVELOPE" or name.startswith("MG90S_") or
                name.startswith("M3x18 ISO7380 motor ear") or
                name.startswith("SPACER_M3x14_")):
            y=-60.0
        if name in front_supports or name.startswith(("OCT_LOCATOR_PIN_","OCT_RECEIVER_MAGNET_")):
            y=70.0
        if name in front_arm:
            y=28.0
        if name in rear_supports:
            y=-25.0
        if name.startswith("CLAM_M3x") and "FRAME_" in name:
            y=105.0
        if name in ("ARM_SPLIT_M3x10_SHCS_0","ARM_LOWER_M3x14_BUTTON_HEAD"):
            y=-12.0
        translations[name]=(0.0,y,0.0)
    return capture_views(app,"exploded",names,(0,35,-1.6),28.5,
                         views=("front_iso","rear_iso"),translations=translations)


def require_verified_geometry(app):
    require_review(app)
    current={n:load("sparkshift_cam_v8").stats(b) for n,b in by_name(app).items()}
    if any(current!=STATE.get(key) for key in ("verified_case_stats","verified_tool_travel_stats")):
        raise RuntimeError("The assembly changed after its current clearance audits")
    proof=json.loads((OUT/"current_interface_proof.json").read_text())
    if len(proof["snap_capture"])!=6 or len(proof["backing"])!=8:
        raise RuntimeError("The current pin/floor proof has an incomplete inventory")
    for pin in proof["snap_capture"]:
        if (pin["assembled_overlap_mm3"]>1e-5 or
                not 0<pin["nominal_entry_throat_mm"]<1.5 or
                any(state!=0 for state in pin["axial_stops"]) or
                any(state!=0 for row in pin["sections"]
                    for state in row["capture_lips"]+row["lower_seat_support"])):
            raise RuntimeError("Current pin capture is not geometrically verified: "+pin["pin"])
    if (proof["hardware_changes"] or
            any(row["missing_mm3"]>1e-5 for row in proof["backing"]) or
            any(row["removed_mm3"]>1e-5 for rows in proof["protected_regions"].values() for row in rows)):
        raise RuntimeError("A protected interface or floor is no longer verified")
    return current


def export_checkpoint(app):
    current=require_verified_geometry(app)
    design=adsk.fusion.Design.cast(app.activeProduct)
    root,by=design.rootComponent,by_name(app)
    paths={kind:OUT/"cad"/("SparkShift_AHG_min_v10."+kind) for kind in ("f3d","step")}
    if any(path.exists() for path in paths.values()):
        raise RuntimeError("Inspect the existing export receipt instead of repeating the exports")
    report={"parts":current,"joint_count":sum(c.joints.count for c in design.allComponents),
            "creation_id":app.activeDocument.creationId,"exports":{}}
    for kind,path in paths.items():
        states=[(occ,occ.isLightBulbOn) for occ in root.allOccurrences]
        body_states=[(body,body.isLightBulbOn) for body in by.values()]
        try:
            if kind=="step":
                for occ,_ in states:
                    occ.isLightBulbOn=True
                for body,_ in body_states:
                    body.isLightBulbOn=True
                options=design.exportManager.createSTEPExportOptions(str(path))
            else:
                options=design.exportManager.createFusionArchiveExportOptions(str(path))
            if not design.exportManager.execute(options) or not path.exists() or path.stat().st_size<100000:
                raise RuntimeError("Missing current CAD export: "+kind)
            report["exports"][kind]={"path":str(path),"bytes":path.stat().st_size,
                                    "sha256":hashlib.sha256(path.read_bytes()).hexdigest()}
            (OUT/"v10_cad_export.json").write_text(json.dumps(report,indent=2))
        finally:
            for body,state in body_states:
                if body.isValid:
                    body.isLightBulbOn=state
            for occ,state in states:
                if occ.isValid:
                    occ.isLightBulbOn=state
    if current!=require_verified_geometry(app):
        raise RuntimeError("CAD export changed the native assembly")
    STATE["exported_geometry_stats"]=current
    return {key:value for key,value in report.items() if key!="parts"}
