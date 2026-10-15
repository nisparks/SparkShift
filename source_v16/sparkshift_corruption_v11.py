"""Diagnose and repair the captured front-case corruption in an owned copy."""

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
OUT=BASE/"sparkshift_corruption_repair_v11"
CASE="PRINT_000_outer_shell_of_extruder_1"
STATE={}


def load(name):
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,BASE/(name+".py"))
        module=importlib.util.module_from_spec(spec)
        sys.modules[name]=module
        spec.loader.exec_module(module)
    return sys.modules[name]


def bodies(app):
    design=adsk.fusion.Design.cast(app.activeProduct)
    return {body.name:body for body in load("pancake_paths_study").proxies(design.rootComponent)}


def require_review(app):
    if not STATE or app.activeDocument.creationId!=STATE["document"]:
        raise RuntimeError("Activate only the owned v11 repair copy")


def metadata(body):
    m=load("sparkshift_ahg_min")
    row={"faces":body.faces.count,"lumps":body.lumps.count,
         "solid":body.isSolid,"bounds_mm":m.bb_of(body)}
    try:
        row["volume_mm3"]=body.volume*1000
    except RuntimeError as error:
        row["volume_error"]=str(error)
    return row


def initialize(app):
    if STATE:
        raise RuntimeError("The corruption baseline is already captured")
    receipt=json.loads((OUT/"recovered_latest_input.json").read_text())
    source=Path(receipt["input_path"])
    if hashlib.sha256(source.read_bytes()).hexdigest()!=receipt["sha256"]:
        raise RuntimeError("The latest recovered native input changed")
    original=app.activeDocument
    if original.creationId!=receipt["creation_id"]:
        raise RuntimeError("Preserve the current user document before selecting a different baseline")
    design=adsk.fusion.Design.cast(app.activeProduct)
    if design.timeline.count!=receipt["timeline_count"]:
        raise RuntimeError("The user's feature history changed after capture")
    s,w=load("pancake_paths_study"),load("sparkshift_cam_v8")
    by=bodies(app)
    protected={name:w.stats(body) for name,body in by.items() if name!=CASE}
    opened=app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(source)))
    try:
        current=bodies(app)
        if set(current)!=set(by) or metadata(current[CASE])!=metadata(by[CASE]):
            raise RuntimeError("The repair copy differs from the recovered input")
        if protected!={name:w.stats(body) for name,body in current.items() if name!=CASE}:
            raise RuntimeError("An unaffected part changed during baseline import")
        opened.name="SparkShift v11 - face corruption repair WIP"
        STATE.update(document=opened.creationId,review_document=opened,
                     source_document=original,input_path=str(source),
                     input_sha256=receipt["sha256"],protected=protected,
                     before={name:s.tbm().copy(body) for name,body in current.items()},
                     source_timeline_count=design.timeline.count)
    except RuntimeError:
        opened.close(False)
        original.activate()
        raise
    report={"source_document":original.name,"review_document":opened.name,
            "creation_id":opened.creationId,"input_sha256":receipt["sha256"],
            "body_count":len(current),"initial_case":metadata(current[CASE]),
            "source_document_not_modified":True}
    (OUT/"repair_copy_baseline.json").write_text(json.dumps(report,indent=2))
    return report


def inspect_recent_history(app):
    require_review(app)
    design=adsk.fusion.Design.cast(app.activeProduct)
    saved_marker=design.timeline.markerPosition
    report={"stages":[],"feature_inputs":[],"errors":[]}
    try:
        for marker in range(691,design.timeline.count+1):
            design.timeline.markerPosition=marker
            body=bodies(app)[CASE]
            shape=load("pancake_paths_study").tbm().copy(body)
            STATE.setdefault("history_shapes",{})[marker]=shape
            row={"marker":marker,"case":metadata(body)}
            if marker>691:
                feature=design.timeline.item(marker-1).entity
                row["last_feature"]=feature.name
            report["stages"].append(row)
            (OUT/"recent_feature_diagnostic.json").write_text(json.dumps(report,indent=2))
    finally:
        design.timeline.markerPosition=saved_marker
    return report


def capture_case(app,slug,shape=None,centre=(0,20,19.7),extent=13.5,
                 views=("front_iso","rear_iso"),colour=(225,155,65)):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    source=adsk.fusion.Design.cast(app.activeProduct)
    original=app.activeDocument
    body=s.tbm().copy(shape if shape is not None else bodies(app)[CASE])
    template=source.appearances.itemByName("SparkShift arm")
    if template is None:
        raise RuntimeError("The native rendering palette is missing")
    old_camera=app.activeViewport.camera
    old_folder=m.IMAGES_V4
    folder=OUT/"images"
    folder.mkdir(parents=True,exist_ok=True)
    owned=None
    files=[]
    try:
        owned=app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
        owned.name="OWNED v11 diagnostic view - disposable"
        design=adsk.fusion.Design.cast(app.activeProduct)
        design.designType=adsk.fusion.DesignTypes.DirectDesignType
        design.appearances.addByCopy(template,"SparkShift arm")
        appearance=m.rgb_appearance(design,"v11 diagnostic part",colour)
        added=design.rootComponent.bRepBodies.add(body)
        if added is None:
            raise RuntimeError("Cannot render the diagnostic native shape")
        added.appearance=appearance
        for face in added.faces:
            face.appearance=appearance
        app.userInterface.activeSelections.clear()
        m.IMAGES_V4=folder
        for suffix,eye,target,up,ext in m.std_views(centre,extent,views):
            file=slug+suffix+".png"
            m.camera_shot(app,file,eye,target,up,ext)
            if not (folder/file).exists() or (folder/file).stat().st_size<1000:
                raise RuntimeError("The diagnostic image is missing")
            files.append(file)
    finally:
        try:
            if owned is not None and owned.isValid and not owned.close(False):
                raise RuntimeError("Cannot close the disposable diagnostic view")
        finally:
            original.activate()
            m.IMAGES_V4=old_folder
            app.activeViewport.camera=old_camera
            app.activeViewport.refresh()
    return files


def repair_invalid_operations(app):
    require_review(app)
    design=adsk.fusion.Design.cast(app.activeProduct)
    expected=((699,"Extrude33"),(700,"DeleteFace29"),(701,"DeleteFace30"))
    if design.timeline.count!=702 or any(design.timeline.item(index).entity.name!=name
                                        for index,name in expected):
        raise RuntimeError("The diagnosed feature history changed")
    if any(design.timeline.item(index).entity.isSuppressed for index,_ in expected):
        raise RuntimeError("The repair is already applied or the feature state differs")
    feature=design.timeline.item(699).entity
    feature.timelineObject.rollTo(True)
    distance=feature.extentOne.distance.value*10
    if abs(distance)>0.00002 or feature.operation!=adsk.fusion.FeatureOperations.CutFeatureOperation:
        raise RuntimeError("Do not disable a changed, meaningful extrusion")
    preserved=load("pancake_paths_study").tbm().copy(bodies(app)[CASE])
    for index,_ in expected:
        feature=design.timeline.item(index).entity
        feature.timelineObject.rollTo(True)
        feature.isSuppressed=True
    for marker in range(699,703):
        design.timeline.markerPosition=marker
        row=metadata(bodies(app)[CASE])
        if "volume_error" in row or not row["solid"] or row["lumps"]!=1:
            raise RuntimeError("A suppressed history stage still has invalid solid geometry")
    if not design.computeAll():
        raise RuntimeError("The repaired history did not finish recomputing")
    STATE["valid_user_case_before_repair"]=preserved
    STATE["suppressed_invalid_operations"]=[name for _,name in expected]
    report={"disabled_features":[{"index":index,"name":name} for index,name in expected],
            "near_zero_distance_mm":distance,"user_history_deleted":False,
            "other_eight_latest_user_edits_retained":True,
            "case":metadata(bodies(app)[CASE])}
    (OUT/"repair_operations.json").write_text(json.dumps(report,indent=2))
    return report


def initialize_checks(app):
    require_review(app)
    if "helper" in STATE:
        raise RuntimeError("The repaired-case checks are already initialized")
    case=metadata(bodies(app)[CASE])
    if "volume_error" in case or not case["solid"] or case["lumps"]!=1:
        raise RuntimeError("Cannot initialize valid-solid checks on corrupted geometry")
    published=BASE/"sparkshift_case_update_v10"/"cad"/"SparkShift_AHG_min_v10.f3d"
    if hashlib.sha256(published.read_bytes()).hexdigest()!=(
            "41b05239cfa6503babc20d0404025c2fd863d21cfc011178dcd3773dc123aeb2"):
        raise RuntimeError("The published interface baseline changed")
    s=load("pancake_paths_study")
    original=app.activeDocument
    document=app.importManager.importToNewDocument(
        app.importManager.createFusionArchiveImportOptions(str(published)))
    try:
        before={name:s.tbm().copy(body) for name,body in bodies(app).items()}
        if set(before)!=set(STATE["before"]):
            raise RuntimeError("The published and current body inventories differ")
    finally:
        try:
            if document.isValid and not document.close(False):
                raise RuntimeError("Cannot close the owned interface-baseline copy")
        finally:
            original.activate()
    helper_path=BASE/"sparkshift_surface_cleanup.py"
    helper=types.ModuleType("sparkshift_v11_surface_tools")
    helper.__file__=str(helper_path)
    code=helper_path.read_text(encoding="utf-8").replace("_v9","_v11").replace("v9_","v11_")
    exec(compile(code,str(helper_path),"exec"),helper.__dict__)
    helper.initialize(app,output=OUT)
    helper.STATE["before"]=before
    policy_path=BASE/"sparkshift_case_v10.py"
    policy=types.ModuleType("sparkshift_v11_contact_policy")
    policy.__file__=str(policy_path)
    code=policy_path.read_text(encoding="utf-8").replace("_v10","_v11").replace("v10_","v11_")
    exec(compile(code,str(policy_path),"exec"),policy.__dict__)
    policy.OUT=OUT
    policy.STATE.update(document=STATE["document"],helper=helper)
    STATE.update(helper=helper,policy=policy,published_before=before)
    return {"body_count":len(before),"valid_case":case,
            "strict_named_press_reference_policy":True}


def verify_interfaces(app):
    require_review(app)
    s,m,w=load("pancake_paths_study"),load("sparkshift_ahg_min"),load("sparkshift_cam_v8")
    by=bodies(app)
    current={name:w.stats(body) for name,body in by.items()}
    declared=STATE.get("declared_changed_body_names",set())
    replacements=STATE.get("hardware_replacements",{})
    protected_changes=[name for name in STATE["protected"]
                       if name not in declared and name not in replacements
                       and current.get(name)!=STATE["protected"][name]]
    expected_names=(set(STATE["before"])-set(replacements))|set(replacements.values())
    if set(current)!=expected_names:
        raise RuntimeError("An undeclared body was added, removed or renamed")
    case=s.tbm().copy(by[CASE])
    snap=[]
    for name in sorted(name for name in by if name.startswith("OCT_LOCATOR_PIN_")):
        g=next(face.geometry for face in by[name].faces if isinstance(face.geometry,adsk.core.Cylinder))
        origin=(g.origin.x*10,g.origin.y*10,g.origin.z*10)
        axis=(g.axis.x,g.axis.y,g.axis.z)
        transverse=(-axis[2],0,axis[0])
        sections=[]
        for t in (.45,4.65):
            lips=[]
            for sign in (-1,1):
                p=[origin[i]+axis[i]*t+transverse[i]*sign*.735+(.25 if i==1 else 0)
                   for i in range(3)]
                lips.append(int(case.pointContainment(s.P(*p))))
            rails=[]
            for degrees in (135,225):
                angle=math.radians(degrees)
                p=[origin[i]+axis[i]*t+transverse[i]*.85*math.sin(angle)
                   +(.85*math.cos(angle) if i==1 else 0) for i in range(3)]
                rails.append(int(case.pointContainment(s.P(*p))))
            sections.append({"position_mm":t,"capture_lips":lips,"lower_seat_support":rails})
        stops=[]
        for t in (-.18,5.08):
            stops.append(int(case.pointContainment(s.P(*[
                origin[i]+axis[i]*t for i in range(3)]))))
        snap.append({"pin":name,"sections":sections,"axial_stops":stops,
                     "assembled_overlap_mm3":s.common_volume(case,by[name])[0],
                     "nominal_entry_throat_mm":2*math.sqrt(.75**2-(31.5-origin[1])**2)})
    backing=[]
    for name in sorted(name for name in by if name.startswith("OCT_RECEIVER_MAGNET_")):
        bb=m.bb_of(by[name])
        footprint=s.box(bb[0]-.1,bb[1]+.1,bb[2]-1.5,bb[2],bb[4]-.1,bb[5]+.1)
        missing=s.tbm().copy(footprint)
        s.op(missing,case,"cut")
        backing.append({"feature":name,"missing_mm3":missing.volume*1000})
    for name,body in by.items():
        if "4mm_ball" not in name:
            continue
        sphere=next(face.geometry for face in body.faces if isinstance(face.geometry,adsk.core.Sphere))
        x,y,z=sphere.origin.x*10,sphere.origin.y*10,sphere.origin.z*10
        floor=y-2.2
        missing=s.cyl(x,z,floor-1.5,floor,2.170352454704739)
        s.op(missing,case,"cut")
        backing.append({"feature":name,"missing_mm3":missing.volume*1000})
    proof=STATE["helper"].current_proof(app)
    report={"snap_capture":snap,"backing":backing,
            "protected_regions":proof["protected_regions"],
            "hardware_changes":protected_changes+proof["unexpected_hardware_changes"],
            "feature_issues":proof["feature_issues"],
            "current_stats":current,
            "scope":"Preserved current user geometry and published bearing/belt/docking interfaces"}
    (OUT/"current_interface_proof.json").write_text(json.dumps(report,indent=2))
    if (report["hardware_changes"] or len(snap)!=6 or len(backing)!=8
            or any(row["missing_mm3"]>1e-5 for row in backing)
            or any(row["removed_mm3"]>1e-5 for rows in proof["protected_regions"].values() for row in rows)
            or any(state!=0 for row in snap for state in row["axial_stops"])
            or any(state!=0 for row in snap for section in row["sections"]
                   for state in section["capture_lips"]+section["lower_seat_support"])
            or any(row["assembled_overlap_mm3"]>1e-5 for row in snap)):
        raise RuntimeError("A preserved interface is not verified; inspect the current proof")
    STATE["interface_stats"]=current
    return {key:value for key,value in report.items() if key!="current_stats"}


def study_heatset_split(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    by=bodies(app)
    insert=m.bb_of(by["SPRING_PRELOAD_M3_HEATSET"])
    mouth=insert[1]
    y,z=(insert[2]+insert[3])/2,(insert[4]+insert[5])/2
    tool=m.axis_cyl((0,y,z),(1,0,0),2.3,mouth,mouth+2)
    cone=s.tbm().createCylinderOrCone(s.P(mouth+2,y,z),.23,
                                    s.P(mouth+6,y,z),.35)
    s.op(tool,cone,"join")
    s.op(tool,m.axis_cyl((0,y,z),(1,0,0),3.5,mouth+6,26),"join")
    front=s.tbm().copy(by[CASE])
    clearance=s.box(20.25,22.6,11.35,18.3,z-3.7,z+3.7)
    s.op(front,clearance,"cut")
    rear_name="PRINT_motor_mount"
    rear=s.tbm().copy(by[rear_name])
    extension=s.box(20.5,22.5,9.8,18.1,z-3.5,z+3.5)
    s.op(rear,extension,"join")
    if front.lumps.count!=1 or rear.lumps.count!=1:
        raise RuntimeError("The proposed case-split transfer is not one connected part per half")
    access=s.common_volume(tool,front)[0]
    overlap=s.common_volume(front,rear)[0]
    removed=s.tbm().copy(by[CASE])
    s.op(removed,front,"cut")
    added=s.tbm().copy(rear)
    s.op(added,by[rear_name],"cut")
    report={"front_removed_mm3":removed.volume*1000,
            "rear_added_mm3":added.volume*1000,
            "front_cutback_bounds_mm":m.bb_of(removed),
            "rear_extension_bounds_mm":m.bb_of(added),
            "nominal_mating_allowance_mm":.2,
            "iron_shaft_diameter_mm":7.0,
            "tool_tip_diameter_mm":4.6,
            "straight_tool_reach_mm":26-mouth,
            "front_case_alone_tool_obstruction_mm3":access,
            "assembled_case_overlap_mm3":overlap,
            "heatset_and_other_hardware_unchanged":True,
            "no_native_changes_applied":True}
    STATE["heatset_split_study"]={"front":front,"rear":rear,"cut":clearance,
                                  "extension":extension,"tool":tool,"report":report}
    (OUT/"heatset_split_study.json").write_text(json.dumps(report,indent=2))
    return report


def apply_access_and_window_changes(app):
    require_review(app)
    if "native_changes" in STATE or (OUT/"native_changes_journal.json").exists():
        raise RuntimeError("Inspect the recorded native change journal instead of repeating edits")
    w,s,m=load("sparkshift_cam_v8"),load("pancake_paths_study"),load("sparkshift_ahg_min")
    current={name:w.stats(body) for name,body in bodies(app).items()}
    if current!=STATE["latest_user_source_stats"]:
        raise RuntimeError("Capture the newest user edits before applying this study")
    trial=STATE["combined_virtual_report"]
    if (trial["stage"]!="complete" or trial["unexpected_pose_overlaps"]
            or trial["withdrawal_overlaps"] or trial["errors"]
            or trial["singular_left_wall_face_count"]!=1):
        raise RuntimeError("The combined virtual study has not passed")
    helper=STATE["helper"]
    split,mount=STATE["heatset_split_study"],STATE["lower_mount_study"]
    report={"stage":"running","operations":[],"hardware_replacements":{},
            "user_single_face_edit_retained":True}

    def write():
        (OUT/"native_changes_journal.json").write_text(json.dumps(report,indent=2))

    write()
    for name,tool,label,kind in (
        (CASE,split["cut"],"V11 bench heat-set access at opposite case seam","cut"),
        ("PRINT_motor_mount",split["extension"],"V11 rear-case wall compensation for heat-set access","join"),
        ("PRINT_RedLizard_HF_tool_carrier",mount["slab"],"V11 lower mounting shelf with retained filament boss","cut"),
    ):
        require_review(app)
        report["operations"].append(helper.append_boolean(app,name,tool,label,kind))
        write()
    by=bodies(app)
    sink_top=m.bb_of(by["HF_00_K1_heatsink"])[5]
    counterbores=None
    for index in range(4):
        bbox=m.bb_of(by["M2_5x8_HF_mount_"+str(index)])
        x,y=(bbox[0]+bbox[1])/2,(bbox[2]+bbox[3])/2
        tool=m.axis_cyl((x,y,0),(0,0,1),2.4,sink_top+2.0,sink_top+8.0)
        if counterbores is None:
            counterbores=tool
        else:
            s.op(counterbores,tool,"join")
    report["operations"].append(helper.append_cut(
        app,"PRINT_RedLizard_HF_tool_carrier",counterbores,"V11 recessed M2.5 mounting-head seats"))
    write()
    closures=s.tbm().copy(mount["closures"][0])
    s.op(closures,mount["closures"][1],"join")
    report["operations"].append(helper.append_join(
        app,CASE,closures,"V11 close lower tool-mount notches at aligned case edge"))
    write()
    for old_name,row in mount["screws"].items():
        require_review(app)
        m.replace(bodies(app)[old_name],row["body"],row["name"],row["name"])
        report["hardware_replacements"][old_name]=row["name"]
        write()
    design=adsk.fusion.Design.cast(app.activeProduct)
    if not design.computeAll():
        raise RuntimeError("The modified native assembly did not recompute")
    report["stage"]="applied-pending-current-verification"
    report["body_count"]=len(bodies(app))
    write()
    STATE["native_changes"]=report
    STATE["hardware_replacements"]=dict(report["hardware_replacements"])
    STATE["declared_changed_body_names"]={CASE,"PRINT_motor_mount","PRINT_RedLizard_HF_tool_carrier"}
    helper.STATE["hardware_changes"]=dict(report["hardware_replacements"])
    for key in ("verified_case_stats","verified_tool_travel_stats","exported_geometry_stats"):
        STATE["policy"].STATE.pop(key,None)
    return report


def verify_access_and_mount(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    by=bodies(app)
    case=by[CASE]
    carrier=by["PRINT_RedLizard_HF_tool_carrier"]
    sink_top=m.bb_of(by["HF_00_K1_heatsink"])[5]
    wall_faces=[]
    for face in case.faces:
        g=face.geometry
        if not isinstance(g,adsk.core.Plane) or abs(g.normal.x)<.99:
            continue
        bbox=m.bb_of(face)
        if bbox[0]>-3.6 and bbox[1]<-2.9 and bbox[4]<-18 and bbox[5]>30:
            wall_faces.append({"area_mm2":face.area*100,"bounds_mm":bbox})
    shoulders=[]
    for index in range(4):
        name="M2_5x5_HF_mount_"+str(index)
        old=STATE["before"]["M2_5x8_HF_mount_"+str(index)]
        bbox=m.bb_of(by[name])
        x,y=(bbox[0]+bbox[1])/2,(bbox[2]+bbox[3])/2
        footprint=m.axis_cyl((x,y,0),(0,0,1),2.25,sink_top,sink_top+2.0)
        s.op(footprint,m.axis_cyl((x,y,0),(0,0,1),1.35,sink_top-.1,sink_top+2.1),"cut")
        missing=s.tbm().copy(footprint)
        s.op(missing,carrier,"cut")
        shoulders.append({"screw":name,"plastic_under_head_mm":2.0,
                          "bearing_annulus_missing_mm3":missing.volume*1000,
                          "tip_shift_mm":bbox[4]-m.bb_of(old)[4],
                          "head_to_case_vertical_allowance_mm":sink_top+5.2-bbox[5]})
    protected=m.axis_cyl((0,22.7,0),(0,0,1),2.9,-80,80)
    before=s.tbm().copy(STATE["before"]["PRINT_RedLizard_HF_tool_carrier"])
    after=s.tbm().copy(carrier)
    s.op(before,protected,"common")
    s.op(after,protected,"common")
    removed=s.tbm().copy(before)
    added=s.tbm().copy(after)
    s.op(removed,after,"cut")
    s.op(added,before,"cut")
    iron_study=STATE.get("broad_native_study",STATE["heatset_split_study"])
    report={"singular_wall_face_count":len(wall_faces),"singular_wall_faces":wall_faces,
            "bare_front_case_iron_obstruction_mm3":s.common_volume(
                iron_study["tool"],case)[0],
            "assembled_case_overlap_mm3":s.common_volume(case,by["PRINT_motor_mount"])[0],
            "mount_shoulders":shoulders,
            "filament_boss_difference_mm3":(removed.volume+added.volume)*1000,
            "spring_heatset_position_unchanged":load("sparkshift_cam_v8").stats(
                by["SPRING_PRELOAD_M3_HEATSET"])==STATE["protected"]["SPRING_PRELOAD_M3_HEATSET"],
            "iron_envelope_note":("10 mm heater body, 7 mm shaft, 4.6 mm working end"
                                  if "broad_native_study" in STATE else
                                  "7 mm shaft, 4.6 mm working end")
                                 +"; front half alone, not universal physical tool qualification"}
    (OUT/"current_access_and_mount_proof.json").write_text(json.dumps(report,indent=2))
    if (len(wall_faces)!=1 or report["bare_front_case_iron_obstruction_mm3"]>1e-5
            or report["assembled_case_overlap_mm3"]>1e-5
            or report["filament_boss_difference_mm3"]>1e-5
            or not report["spring_heatset_position_unchanged"]
            or any(row["bearing_annulus_missing_mm3"]>1e-5
                   or abs(row["tip_shift_mm"])>1e-5
                   or row["head_to_case_vertical_allowance_mm"]<.69 for row in shoulders)):
        raise RuntimeError("The requested single face, insertion path or mounting support has not passed")
    STATE["access_and_mount_proof"]=report
    return report


def interior_halfspace(face):
    if not isinstance(face.geometry,adsk.core.Plane):
        raise RuntimeError("The closure boundary is not a plane")
    point=face.geometry.origin
    ok,normal=face.evaluator.getNormalAtPoint(face.pointOnFace)
    if not ok or abs(normal.y)>1e-8:
        raise RuntimeError("Cannot preserve the existing wall boundary")
    normal.normalize()
    centre=point.copy()
    shift=normal.copy()
    shift.scaleBy(-10.0)
    centre.translateBy(shift)
    box=adsk.core.OrientedBoundingBox3D.create(
        centre,normal,adsk.core.Vector3D.create(0,1,0),20.0,20.0,20.0)
    return load("pancake_paths_study").tbm().createBox(box)


def study_lower_mount(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    by=bodies(app)
    carrier_name="PRINT_RedLizard_HF_tool_carrier"
    carrier=s.tbm().copy(by[carrier_name])
    sink_top=m.bb_of(by["HF_00_K1_heatsink"])[5]
    bottom=sink_top+5.2
    top=bottom-.3
    seat=sink_top+2.0
    slab=s.box(-14.1,14.1,11.4,31.5,top,sink_top+7.8)
    filament=m.axis_cyl((0,22.7,0),(0,0,1),2.9,top-.1,sink_top+8.0)
    s.op(slab,filament,"cut")
    s.op(carrier,slab,"cut")
    screws={}
    shoulders=[]
    for index in range(4):
        old_name="M2_5x8_HF_mount_"+str(index)
        original=by[old_name]
        bbox=m.bb_of(original)
        x,y=(bbox[0]+bbox[1])/2,(bbox[2]+bbox[3])/2
        screw=m.translated(original,dz=-3.0)
        s.op(screw,s.box(-50,50,-50,80,bbox[4],100),"common")
        if screw.lumps.count!=1:
            raise RuntimeError("The shorter mounting-screw reference is not one solid")
        new_name="M2_5x5_HF_mount_"+str(index)
        screws[old_name]={"name":new_name,"body":screw}
        counterbore=m.axis_cyl((x,y,0),(0,0,1),2.4,seat,sink_top+8.0)
        s.op(carrier,counterbore,"cut")
        footprint=m.axis_cyl((x,y,0),(0,0,1),2.25,sink_top,seat)
        s.op(footprint,m.axis_cyl((x,y,0),(0,0,1),1.35,sink_top-.1,seat+.1),"cut")
        missing=s.tbm().copy(footprint)
        s.op(missing,carrier,"cut")
        shoulders.append({"mount":index,"nominal_plastic_under_head_mm":2.0,
                          "bearing_annulus_missing_mm3":missing.volume*1000,
                          "screw_tip_shift_mm":m.bb_of(screw)[4]-bbox[4],
                          "new_head_top_z_mm":m.bb_of(screw)[5]})
    if carrier.lumps.count!=1:
        raise RuntimeError("The proposed lower tool mount disconnects the carrier")
    case=s.tbm().copy(by[CASE])
    closures=[]
    for sign in (-1,1):
        candidates=[]
        for face in by[CASE].faces:
            geometry=face.geometry
            if not isinstance(geometry,adsk.core.Plane) or abs(geometry.normal.x)<.99:
                continue
            bbox=m.bb_of(face)
            if (sign==1 and 2.9<bbox[0]<3.5 and bbox[1]<3.5 or
                    sign==-1 and -3.6<bbox[0] and bbox[1]<-2.9):
                if bbox[4]<-15 and bbox[5]>30:
                    candidates.append(face)
        if len(candidates)!=1:
            raise RuntimeError("Cannot identify the user's singular inner-wall boundary")
        x0,x1=(-11.675,-3.1) if sign==-1 else (3.1,11.66)
        fill=s.box(x0,x1,29.5,31.5,bottom,sink_top+7.85)
        s.op(fill,interior_halfspace(candidates[0]),"common")
        s.op(case,fill,"join")
        closures.append(fill)
    if case.lumps.count!=1:
        raise RuntimeError("The proposed lower-window closure disconnects the case")
    added=s.tbm().copy(case)
    s.op(added,by[CASE],"cut")
    occupants=[]
    for name,body in by.items():
        if name==CASE:
            continue
        shape=(carrier if name==carrier_name else
               screws[name]["body"] if name in screws else body)
        if m.bb_gap_l(m.bb_of(added),m.bb_of(shape))>0:
            continue
        volume,overlap=s.common_volume(added,shape)
        if volume>1e-5:
            occupants.append({"body":name,"volume_mm3":volume,"bounds_mm":m.bb_of(overlap)})
    report={"case_added_mm3":added.volume*1000,
            "case_added_bounds_mm":m.bb_of(added),
            "case_lower_edge_z_mm":bottom,
            "carrier_mount_top_z_mm":top,
            "nominal_carrier_to_case_vertical_clearance_mm":.3,
            "head_seat_z_mm":seat,
            "screw_head_to_case_vertical_clearance_mm":.7,
            "hardware_change":"Four M2.5x8 references become M2.5x5; their axes and tips stay fixed",
            "shoulders":shoulders,"remaining_static_occupants":occupants,
            "filament_boss_and_rear_tool_docking_web_preserved":True,
            "no_native_changes_applied":True}
    STATE["lower_mount_study"]={"case":case,"carrier":carrier,"slab":slab,
                                "screws":screws,"closures":closures,"report":report}
    (OUT/"lower_mount_study.json").write_text(json.dumps(report,indent=2))
    return report


def study_broad_heatset_split(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    by=bodies(app)
    source=STATE["lower_mount_study"]["case"]
    rear_source=STATE["published_before"]["PRINT_motor_mount"]
    cut=s.box(20.25,22.6,9.8,21.8,-17.8,53.5)
    reserve=None
    clearance_reserve=None
    stations=((18.75,-14.73,3.55),(18.1,41.72,3.55))
    for x,z,radius in stations:
        pad=s.cyl(x,z,9.7,31.6,radius)
        allowance=s.cyl(x,z,9.7,31.6,radius+.2)
        if reserve is None:
            reserve=pad
            clearance_reserve=allowance
        else:
            s.op(reserve,pad,"join")
            s.op(clearance_reserve,allowance,"join")
    s.op(cut,reserve,"cut")
    front=s.tbm().copy(source)
    s.op(front,cut,"cut")
    extension=s.tbm().copy(source)
    s.op(extension,s.box(20.5,22.5,9.8,21.6,-17.6,53.3),"common")
    s.op(extension,clearance_reserve,"cut")
    rear=s.tbm().copy(rear_source)
    s.op(rear,extension,"join")
    if front.lumps.count!=1 or rear.lumps.count!=1:
        raise RuntimeError("The broad split disconnects a case half")
    bb=m.bb_of(by["SPRING_PRELOAD_M3_HEATSET"])
    mouth=bb[1]
    y,z=(bb[2]+bb[3])/2,(bb[4]+bb[5])/2
    tool=m.axis_cyl((0,y,z),(1,0,0),2.3,mouth,mouth+2)
    s.op(tool,s.tbm().createCylinderOrCone(
        s.P(mouth+2,y,z),.23,s.P(mouth+6,y,z),.35),"join")
    s.op(tool,m.axis_cyl((0,y,z),(1,0,0),3.5,mouth+6,5),"join")
    s.op(tool,s.tbm().createCylinderOrCone(s.P(5,y,z),.35,s.P(9,y,z),.5),"join")
    s.op(tool,m.axis_cyl((0,y,z),(1,0,0),5.0,9,28),"join")
    lip=s.tbm().copy(front)
    s.op(lip,tool,"common")
    if s.common_volume(lip,reserve)[0]>1e-5:
        raise RuntimeError("The wider tool relief would remove reserved fastener support")
    s.op(front,tool,"cut")
    if front.lumps.count!=1:
        raise RuntimeError("The wider tool relief disconnects the front case")
    access,hit=s.common_volume(tool,front)
    overlap=s.common_volume(front,rear)[0]
    supports=[]
    for x,z,radius in stations:
        zone=s.cyl(x,z,9.7,31.6,radius)
        before=s.tbm().copy(source)
        after=s.tbm().copy(front)
        s.op(before,zone,"common")
        s.op(after,zone,"common")
        added=s.tbm().copy(after)
        removed=s.tbm().copy(before)
        s.op(added,before,"cut")
        s.op(removed,after,"cut")
        supports.append({"axis_xz_mm":[x,z],"protected_radius_mm":radius,
                         "front_support_difference_mm3":(added.volume+removed.volume)*1000})
    removed=s.tbm().copy(source)
    s.op(removed,front,"cut")
    added=s.tbm().copy(rear)
    s.op(added,rear_source,"cut")
    belt=s.box(-30,30,-20,40,-70,-18)
    belt_change=s.tbm().copy(added)
    s.op(belt_change,belt,"common")
    report={"front_removed_from_pre_seam_mm3":removed.volume*1000,
            "rear_added_from_pre_seam_mm3":added.volume*1000,
            "cutback_bounds_mm":m.bb_of(removed),
            "rear_extension_bounds_mm":m.bb_of(added),
            "cutback_rear_edge_y_mm":21.8,"rear_extension_front_y_mm":21.6,
            "nominal_mating_allowance_mm":.2,"iron_heater_body_diameter_mm":10.0,
            "iron_shaft_diameter_mm":7.0,"bare_front_iron_obstruction_mm3":access,
            "local_projecting_lip_relief_mm3":lip.volume*1000,
            "iron_obstruction_bounds_mm":m.bb_of(hit) if access>1e-7 else None,
            "case_overlap_mm3":overlap,"retained_fastener_supports":supports,
            "belt_band_material_change_mm3":belt_change.volume*1000,
            "no_native_changes_applied":True}
    STATE["broad_heatset_study"]={"front":front,"rear":rear,"cut":cut,
                                 "extension":extension,"tool":tool,
                                 "source_front":source,"source_rear":rear_source,
                                 "reserve":reserve,"report":report}
    (OUT/"broad_heatset_split_study.json").write_text(json.dumps(report,indent=2))
    return report


def apply_broad_heatset_split(app):
    require_review(app)
    if "broad_native_study" in STATE or (OUT/"broad_split_native_journal.json").exists():
        raise RuntimeError("Inspect the existing broad-split journal instead of repeating changes")
    current={name:load("sparkshift_cam_v8").stats(body) for name,body in bodies(app).items()}
    if current!=STATE["exported_geometry_stats"]:
        raise RuntimeError("Preserve any newer user edits before replacing the provisional seam")
    checks=STATE["broad_virtual_report"]
    if (checks["stage"]!="complete" or checks["unexpected_pose_overlaps"]
            or checks["withdrawal_overlaps"] or checks["errors"]):
        raise RuntimeError("The broader seam has not passed the virtual assembly gates")
    s=load("pancake_paths_study")
    helper,study=STATE["helper"],STATE["broad_heatset_study"]
    local_addition=s.tbm().copy(bodies(app)["PRINT_motor_mount"])
    s.op(local_addition,study["source_rear"],"cut")
    report={"stage":"running","operations":[],"user_requested_broad_strip":True}

    def write():
        (OUT/"broad_split_native_journal.json").write_text(json.dumps(report,indent=2))

    write()
    for name,tool,label,kind in (
        ("PRINT_motor_mount",local_addition,"V11 retire localized heat-set compensation tab","cut"),
        (CASE,study["cut"],"V11 broad rear-edge cutback with retained fastener pads","cut"),
        (CASE,study["tool"],"V11 smooth wider-tool clearance at projecting edge","cut"),
        ("PRINT_motor_mount",study["extension"],"V11 broad compensating rear-shell sidewall","join"),
    ):
        require_review(app)
        report["operations"].append(helper.append_boolean(app,name,tool,label,kind))
        write()
    design=adsk.fusion.Design.cast(app.activeProduct)
    if not design.computeAll():
        raise RuntimeError("The broader case split did not recompute")
    STATE["broad_native_study"]=study
    STATE.pop("step_job",None)
    STATE.pop("exported_shapes",None)
    for key in ("verified_case_stats","verified_tool_travel_stats","exported_geometry_stats"):
        STATE["policy"].STATE.pop(key,None)
    report["stage"]="applied-pending-final-verification"
    write()
    return report


def study_inward_case_clamp(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    by=bodies(app)
    x,z=17.75,-13.5
    screw=m.translated(by["CLAM_M3x20_FRAME_2"],dx=x-18.75,dy=.4,
                       dz=z+14.729404784771766)
    s.op(screw,s.cyl(x,z,5.2,10.2001,1.5),"join")
    nut=s.tbm().copy(by["MONOC_M3_NUT_left_11.2"])
    matrix=adsk.core.Matrix3D.create()
    matrix.setToRotation(math.pi/2,adsk.core.Vector3D.create(0,0,1),s.P(0,0,0))
    s.tbm().transform(nut,matrix)
    bbox=m.bb_of(nut)
    centre=[(bbox[2*i]+bbox[2*i+1])/2 for i in range(3)]
    nut=m.translated(nut,dx=x-centre[0],dy=8.0-centre[1],dz=z-centre[2])
    rear=s.tbm().copy(by["PRINT_motor_mount"])
    stock=s.box(13.35,22.5,5.0,10.8,-17.95,-9.05)
    corner=s.box(14.2,22.5,9.8,21.6,-20.4,-12.0)
    s.op(rear,stock,"join")
    s.op(rear,corner,"join")
    front=s.tbm().copy(by[CASE])
    retired=s.box(13.8,22.6,9.7,21.8,-20.4,-9.4)
    s.op(front,retired,"cut")
    fore_corner=s.box(14.2,22.5,21.8,31.5,-20.4,-12.0)
    s.op(front,fore_corner,"join")
    face_support=s.box(14.2,22.5,29.6,31.5,-20.4,-9.4)
    s.op(front,face_support,"join")
    reliefs=m.arc_slot((15.4,-9.8794047847718),2.45,-7,.3,11.75,15.85)
    s.op(reliefs,m.arc_slot((8,-13.3),3.55,-7,.3,11.75,16.0),"join")
    s.op(reliefs,m.arc_slot((8,-13.3),4.15,-7,.3,15.35,25.9),"join")
    s.op(reliefs,m.arc_slot((8,-13.3),3.1,-7,.3,9.4,11.75),"join")
    shaft=s.cyl(x,z,5.1,30.2,1.65)
    connector=s.box(13.8,x,9.3,25.9,-17.5,-10.0)
    head=s.cyl(x,z,30.2,38,3.15)
    s.op(rear,reliefs,"cut")
    s.op(front,reliefs,"cut")
    s.op(rear,shaft,"cut")
    s.op(front,shaft,"cut")
    s.op(rear,connector,"cut")
    s.op(front,connector,"cut")
    s.op(front,head,"cut")
    pocket=s.box(x-2.9,x+2.9,6.7,9.3,z-3.325,z+3.325)
    entry=s.box(x,22.6,6.7,9.3,z-3.325,z+3.325)
    s.op(pocket,entry,"join")
    s.op(rear,pocket,"cut")
    if rear.lumps.count!=1 or front.lumps.count!=1:
        raise RuntimeError("The thick case-clamp corner disconnects a shell")
    report={"new_axis_xz_mm":[x,z],"bolt":"M3x25 reference",
            "retention":"Side-loaded captive M3 nut in rear case",
            "nut_loading_slot_mm":[6.7,9.3],"rear_nut_backing_mm":1.7,
            "outer_wall_at_front_head_recess_mm":22.5-x-3.15,
            "outer_wall_at_nut_pocket_mm":22.5-x-2.9,
            "front_rear_mating_allowance_mm":.2,
            "case_overlap_mm3":s.common_volume(front,rear)[0],
            "no_native_changes_applied":True,
            "user_unavailable_decision":"Use the ordinary captive nut only for this casing clamp; preserve all arm and spring heat-sets."}
    STATE["inward_clamp_study"]={"front":front,"rear":rear,"screw":screw,"nut":nut,
                                 "stock":stock,"corner":corner,"retired":retired,
                                 "fore_corner":fore_corner,"face_support":face_support,"reliefs":reliefs,
                                 "shaft":shaft,"connector":connector,"head":head,
                                 "pocket":pocket,"report":report}
    (OUT/"inward_case_clamp_study.json").write_text(json.dumps(report,indent=2))
    return report


def apply_inward_case_clamp(app):
    require_review(app)
    if (OUT/"inward_clamp_native_journal.json").exists():
        raise RuntimeError("Inspect the clamp journal rather than repeating edits")
    if STATE["inward_clamp_virtual_report"].get("added_material_overlaps"):
        raise RuntimeError("The clamp-corner study has not passed")
    helper,trial=STATE["helper"],STATE["inward_clamp_study"]
    report={"stage":"running","operations":[],
            "decision":"User unavailable: captive M3 nut for this case clamp only"}

    def write():
        (OUT/"inward_clamp_native_journal.json").write_text(json.dumps(report,indent=2))

    write()
    steps=(
        ("PRINT_motor_mount","stock","V11 reinforced side-loaded case-nut stock","join"),
        ("PRINT_motor_mount","corner","V11 thick matched lower rear-case corner","join"),
        (CASE,"retired","V11 remove obsolete lower clamp seam remnants","cut"),
        (CASE,"fore_corner","V11 matched lower front-case shoulder","join"),
        (CASE,"face_support","V11 substantial front clamp-head support","join"),
    )
    for name,key,label,kind in steps:
        require_review(app)
        report["operations"].append(helper.append_boolean(app,name,trial[key],label,kind))
        write()
    for name in ("PRINT_motor_mount",CASE):
        for key,label in (
            ("reliefs","V11 preserve continuous lower arm and bolt-head travel"),
            ("shaft","V11 inward case-clamp shaft passage"),
            ("connector","V11 open internal clearance without thin guide web"),
        ):
            report["operations"].append(helper.append_cut(app,name,trial[key],label))
            write()
    report["operations"].append(helper.append_cut(app,CASE,trial["head"],
                                                 "V11 inward front clamp-head recess"))
    write()
    report["operations"].append(helper.append_cut(app,"PRINT_motor_mount",trial["pocket"],
                                                 "V11 side-entry captive case-nut pocket"))
    write()
    m=load("sparkshift_ahg_min")
    m.replace(bodies(app)["CLAM_M3x20_FRAME_2"],trial["screw"],
              "CLAM_M3x25_FRAME_2","CLAM_M3x25 lower right case clamp")
    m.replace(bodies(app)["CLAM_M3_FRAME_INSERT_2"],trial["nut"],
              "CLAM_M3_CAPTIVE_NUT_2","M3 captive nut - lower right case clamp")
    if not adsk.fusion.Design.cast(app.activeProduct).computeAll():
        raise RuntimeError("The reinforced case clamp did not recompute")
    STATE["hardware_replacements"]={
        "CLAM_M3x20_FRAME_2":"CLAM_M3x25_FRAME_2",
        "CLAM_M3_FRAME_INSERT_2":"CLAM_M3_CAPTIVE_NUT_2",
    }
    helper.STATE["hardware_changes"]=dict(STATE["hardware_replacements"])
    for key in ("verified_case_stats","verified_tool_travel_stats","exported_geometry_stats"):
        STATE["policy"].STATE.pop(key,None)
    report["stage"]="applied-pending-final-checks"
    report["new_axis_xz_mm"]=trial["report"]["new_axis_xz_mm"]
    report["toolhead_unchanged"]=True
    write()
    return report


def study_back_loaded_case_heatset(app):
    require_review(app)
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    by=bodies(app)
    x,z=18.2,-13.7
    rear=s.tbm().copy(by["PRINT_motor_mount"])
    s.op(rear,STATE["inward_clamp_study"]["stock"],"join")
    host=s.cyl(x,z,5.0,11.6,3.6)
    s.op(rear,host,"join")
    old_passage=s.cyl(17.75,-13.5,5.1,21.6,1.75)
    s.op(rear,old_passage,"join")
    s.op(rear,STATE["inward_clamp_study"]["reliefs"],"cut")
    rear_access=s.cyl(x,z,.2,6.0,2.4)
    pilot=s.cyl(x,z,6.0,10.0,2.0)
    shaft=s.cyl(x,z,10.0,31.5,1.65)
    s.op(rear,rear_access,"cut")
    s.op(rear,pilot,"cut")
    s.op(rear,shaft,"cut")
    front=s.tbm().copy(by[CASE])
    face=STATE["inward_clamp_study"]["face_support"]
    s.op(front,face,"join")
    fore_passage=s.cyl(17.75,-13.5,21.8,31.5,1.75)
    s.op(front,fore_passage,"join")
    s.op(front,shaft,"cut")
    screw=m.translated(by["CLAM_M3x25_FRAME_2"],dx=.45,dy=1.3,dz=-.2)
    original=STATE["before"]["CLAM_M3_FRAME_INSERT_2"]
    insert=m.translated(original,dx=x-18.75,dy=-4.0,
                        dz=z+14.729404784771766)
    if rear.lumps.count!=1 or front.lumps.count!=1:
        raise RuntimeError("The heat-set conversion disconnects a casing half")
    report={"axis_xz_mm":[x,z],"heatset_y_mm":[6,10],
            "prepared_pilot_diameter_mm":4.0,"rear_access_diameter_mm":4.8,
            "heatset_installed_from_rear_before_actuator_plate":True,
            "full_prepared_pilot_radial_wall_mm":1.6,
            "forward_backing_shoulder_mm":1.6,
            "outside_wall_outside_4p6_insert_mm":2.0,
            "screw_head_seat_y_mm":31.5,"screw_tip_y_mm":6.5,
            "nominal_thread_engagement_mm":3.5,
            "counterbore_removed_from_front":True,
            "no_native_changes_applied":True}
    STATE["back_loaded_heatset_study"]={
        "front":front,"rear":rear,"screw":screw,"insert":insert,
        "host":host,"old_passage":old_passage,"fore_passage":fore_passage,
        "rear_access":rear_access,"pilot":pilot,"shaft":shaft,
        "face":face,"report":report}
    (OUT/"back_loaded_case_heatset_study.json").write_text(json.dumps(report,indent=2))
    return report


def apply_back_loaded_case_heatset(app):
    require_review(app)
    if (OUT/"back_loaded_heatset_native_journal.json").exists():
        raise RuntimeError("Inspect the heat-set journal instead of repeating edits")
    if STATE["back_loaded_heatset_virtual_report"].get("added_material_overlaps"):
        raise RuntimeError("The backed heat-set study has not passed")
    s=load("pancake_paths_study")
    helper,trial=STATE["helper"],STATE["back_loaded_heatset_study"]
    report={"stage":"running","operations":[],"user_requested_heatset_not_nut":True}

    def write():
        (OUT/"back_loaded_heatset_native_journal.json").write_text(json.dumps(report,indent=2))

    write()
    for name,tool,label,kind in (
        ("PRINT_motor_mount",STATE["inward_clamp_study"]["stock"],
         "V11 restore solid stock instead of side-loaded nut opening","join"),
        ("PRINT_motor_mount",trial["host"],"V11 full-wall backed case heat-set host","join"),
        ("PRINT_motor_mount",trial["old_passage"],"V11 retire previous case-clamp axis","join"),
        ("PRINT_motor_mount",STATE["inward_clamp_study"]["reliefs"],
         "V11 retain arm travel around backed case insert","cut"),
        ("PRINT_motor_mount",trial["rear_access"],"V11 outside heat-set loading counterbore","cut"),
        ("PRINT_motor_mount",trial["pilot"],"V11 calibrated rear-loaded M3 pilot","cut"),
        ("PRINT_motor_mount",trial["shaft"],"V11 backed insert screw passage","cut"),
        (CASE,trial["face"],"V11 solid front screw-bearing face without thin recess wall","join"),
        (CASE,trial["fore_passage"],"V11 retire previous front-clamp axis","join"),
        (CASE,trial["shaft"],"V11 matching heat-set case-clamp passage","cut"),
    ):
        require_review(app)
        report["operations"].append(helper.append_boolean(app,name,tool,label,kind))
        write()
    m=load("sparkshift_ahg_min")
    m.replace(bodies(app)["CLAM_M3x25_FRAME_2"],trial["screw"],
              "CLAM_M3x25_FRAME_2","M3x25 lower case clamp into heat-set")
    m.replace(bodies(app)["CLAM_M3_CAPTIVE_NUT_2"],trial["insert"],
              "CLAM_M3_FRAME_INSERT_2","Rear-loaded M3 lower case-clamp heat-set")
    if not adsk.fusion.Design.cast(app.activeProduct).computeAll():
        raise RuntimeError("The user-directed heat-set assembly did not recompute")
    STATE["hardware_replacements"]={
        "CLAM_M3x20_FRAME_2":"CLAM_M3x25_FRAME_2",
        "CLAM_M3_FRAME_INSERT_2":"CLAM_M3_FRAME_INSERT_2",
    }
    helper.STATE["hardware_changes"]=dict(STATE["hardware_replacements"])
    STATE["back_loaded_heatset_applied"]=True
    report["stage"]="applied-pending-final-checks"
    report["nut_removed"]=True
    report["toolhead_unchanged"]=True
    write()
    return report


def apply_plate_clamp_and_head_alignment(app):
    require_review(app)
    if (OUT/"plate_and_head_alignment_journal.json").exists():
        raise RuntimeError("Inspect the alignment journal instead of repeating edits")
    if STATE["rear_plate_virtual_report"]["added_material_contacts"]:
        raise RuntimeError("The plate-clamp stack has not passed")
    if STATE["cutout_study"]["report"]["introduced_contacts"]:
        raise RuntimeError("The head-alignment study has not passed")
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    helper=STATE["helper"]
    plate,heads=STATE["rear_plate_clamp_study"],STATE["cutout_study"]
    report={"stage":"running","operations":[],
            "user_requested_blue_sandwich_and_purple_insert":True}

    def write():
        (OUT/"plate_and_head_alignment_journal.json").write_text(json.dumps(report,indent=2))

    write()
    for name,tool,label,kind in (
        ("PRINT_REAR_MOTOR_SERVO_SPACER",plate["pilot"],
         "V11 raised lower clamp heat-set pilot in actuator plate","cut"),
        ("PRINT_REAR_MOTOR_SERVO_SPACER",s.cyl(-16,-13,-5.3,-3.7,1.65),
         "V11 standard M3x35 tip allowance in rear plate","cut"),
        ("PRINT_motor_mount",plate["old"],
         "V11 retire lower-left blue case insert pocket","join"),
        ("PRINT_motor_mount",plate["through"],
         "V11 aligned blue sandwich through-clearance","cut"),
        (CASE,plate["fill"],
         "V11 retire former lower-left front head pocket","join"),
        (CASE,plate["through"],
         "V11 raised lower-left clamp passage","cut"),
        (CASE,s.cyl(-16,-13,29.8,38,3.15),
         "V11 raised lower-left head clearance","cut"),
        (CASE,heads["fills"],
         "V11 fill retired misaligned lower-right head cutouts","join"),
        (CASE,heads["aligned"],
         "V11 concentric actual lower-right head clearance","cut"),
        (CASE,heads["upper_fill"],
         "V11 corrected visible upper frame-head seat stock","join"),
        (CASE,heads["upper_shaft"],
         "V11 upper frame screw shank allowance","cut"),
        (CASE,heads["upper_head"],
         "V11 aligned upper frame-head recess","cut"),
    ):
        require_review(app)
        report["operations"].append(helper.append_boolean(app,name,tool,label,kind))
        write()
    m.replace(bodies(app)["CLAM_M3x20_FRAME_3"],plate["screw"],
              "CLAM_M3x35_FRAME_3","M3x35 lower left clamp into rear plate")
    m.replace(bodies(app)["CLAM_M3_FRAME_INSERT_3"],plate["insert"],
              "CLAM_M3_FRAME_INSERT_3","Raised M3 heat-set in actuator rear plate")
    m.replace(bodies(app)["FRAME_M3x30_into_P01_insert"],heads["upper"],
              "FRAME_M3x30_into_P01_insert","M3x30 frame clamp with socket head")
    if not adsk.fusion.Design.cast(app.activeProduct).computeAll():
        raise RuntimeError("The aligned fastening stack did not recompute")
    STATE["hardware_replacements"].update({
        "CLAM_M3x20_FRAME_3":"CLAM_M3x35_FRAME_3",
        "CLAM_M3_FRAME_INSERT_3":"CLAM_M3_FRAME_INSERT_3",
        "FRAME_M3x30_into_P01_insert":"FRAME_M3x30_into_P01_insert",
    })
    helper.STATE["hardware_changes"]=dict(STATE["hardware_replacements"])
    STATE["declared_changed_body_names"].add("PRINT_REAR_MOTOR_SERVO_SPACER")
    STATE["policy"].STATE.setdefault("press_reference_limits",{})[
        frozenset(("PRINT_REAR_MOTOR_SERVO_SPACER","CLAM_M3_FRAME_INSERT_3"))]=16.22
    for key in ("verified_case_stats","verified_tool_travel_stats","exported_geometry_stats"):
        STATE["policy"].STATE.pop(key,None)
    report["stage"]="applied-pending-final-checks"
    report["purple_lower_outline_unchanged"]=True
    report["blue_part_is_clearance_not_insert_host"]=True
    write()
    return report
