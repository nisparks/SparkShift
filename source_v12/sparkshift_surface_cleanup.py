"""Find and heal translated-cylinder ridge families in a separate native review copy."""

import importlib.util
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

import adsk.core
import adsk.fusion


BASE = Path(__file__).resolve().parent
OUT = BASE / "sparkshift_ahg_min"
STATE = {}
STRUCTURAL = (
    "PRINT_motor_mount", "PRINT_REAR_MOTOR_SERVO_SPACER",
    "PRINT_000_outer_shell_of_extruder_1", "PRINT_carrier_box_left",
    "PRINT_arm_front_half", "PRINT_DIRECT_CAM", "PRINT_RedLizard_HF_tool_carrier",
    "PRINT_SINGLE_SPRING_PRESSURE_CUP", "TOOL_06_Tool_head_back_part_1",
)
PRINTS = {
    "P01": ("PRINT_motor_mount", "P01_Back_case", (0,1,0)),
    "P02": ("PRINT_REAR_MOTOR_SERVO_SPACER", "P02_Motor_servo_plate", (0,-1,0)),
    "P03": ("PRINT_000_outer_shell_of_extruder_1", "P03_Front_case", (0,-1,0)),
    "P04R": ("PRINT_carrier_box_left", "P04R_Swing_arm_rear_half", (0,-1,0)),
    "P04F": ("PRINT_arm_front_half", "P04F_Swing_arm_front_half", (0,-1,0)),
    "P05": ("PRINT_DIRECT_CAM", "P05_Servo_cam", (0,1,0)),
    "P06": ("PRINT_compound_left", "P06_Left_compound_38T_14T", (0,1,0)),
    "P07": ("PRINT_compound_right", "P07_Right_compound_38T_14T", (0,1,0)),
    "P08": ("PRINT_feed_left", "P08_Left_HGX_drive_37T", (0,1,0)),
    "P09": ("PRINT_feed_right", "P09_Right_HGX_drive_37T", (0,1,0)),
    "P12": ("PRINT_SINGLE_SPRING_PRESSURE_CUP", "P12_Spring_pressure_cup", (-1,0,0)),
    "P13": ("PRINT_MONOLITH_CARTRIDGE_LINER_left", "P13_Left_tooth_liner", (0,1,0)),
    "P14": ("PRINT_MONOLITH_CARTRIDGE_LINER_right", "P14_Right_tooth_liner", (0,1,0)),
    "P15": ("PRINT_MONOLITH_CARTRIDGE_ARCH_left", "P15_Left_belt_arch", (0,1,0)),
    "P16": ("PRINT_MONOLITH_CARTRIDGE_ARCH_right", "P16_Right_belt_arch", (0,1,0)),
    "P17": ("PRINT_RedLizard_HF_tool_carrier", "P17_HF_tool_carrier", (0,-1,0)),
    "P18": ("TOOL_06_Tool_head_back_part_1", "P18_Tool_docking_backplate", (0,1,0)),
}


def load(name):
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, BASE / (name + ".py"))
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return sys.modules[name]


def bodies(app):
    return {b.name: b for b in load("pancake_paths_study").proxies(
        adsk.fusion.Design.cast(app.activeProduct).rootComponent)}


def stats(body):
    return load("sparkshift_cam_v8").stats(body)


def initialize(app, output=None):
    global OUT
    if STATE:
        raise RuntimeError("Surface-cleanup baseline already captured")
    if output is not None:
        OUT = Path(output)
    OUT.mkdir(parents=True, exist_ok=True)
    s = load("pancake_paths_study")
    by = bodies(app)
    m, w = load("sparkshift_ahg_min"), load("sparkshift_cam_v8")
    if w.BEARING not in by:
        raise RuntimeError("Open the captured compact-cam/bolted-arm baseline or its current review copy")
    m.STATE.update(Mv=s.centre(by["AXLE_4x24_moving"]), F=s.centre(by["AXLE_4x25_fixed"]),
                   C=s.centre(by[w.BEARING]), Fo=s.centre(by["CAM_FOLLOWER_623"]))
    w.STATE.update(Mv=m.STATE["Mv"],C=m.STATE["C"])
    STATE["document"] = app.activeDocument.creationId
    STATE["before"] = {n: s.tbm().copy(b) for n, b in by.items()}
    STATE["history"] = []
    STATE["inventory"] = {n: stats(b) for n, b in by.items() if n.startswith("PRINT_")}
    write_report()
    return STATE["inventory"]


def write_report():
    report = {k: v for k, v in STATE.items() if k not in ("before", "current", "accepted")}
    (OUT / "analytic_surface_cleanup.json").write_text(json.dumps(report, indent=2))


def families(body):
    m = load("sparkshift_ahg_min")
    entries = []
    for i, face in enumerate(body.faces):
        g = face.geometry
        if not isinstance(g, adsk.core.Cylinder):
            continue
        axis = [g.axis.x, g.axis.y, g.axis.z]
        a = max(range(3), key=lambda j: abs(axis[j]))
        if abs(axis[a]) < .99999:
            continue
        sign = 1 if axis[a] > 0 else -1
        direction = [value * sign for value in axis]
        origin = [g.origin.x * 10, g.origin.y * 10, g.origin.z * 10]
        p = face.pointOnFace
        ok, normal = face.evaluator.getNormalAtPoint(p)
        if not ok:
            raise RuntimeError("Cannot determine face orientation")
        n, q = [normal.x, normal.y, normal.z], [p.x * 10, p.y * 10, p.z * 10]
        cross = [j for j in range(3) if j != a]
        sense = sum(n[j] * (q[j] - origin[j]) for j in cross)
        intercept = [origin[j] - direction[j] * origin[a] / direction[a] for j in cross]
        entries.append({"i": i, "axis": a, "direction": tuple(round(v, 9) for v in direction),
                        "centre": [round(v, 5) for v in intercept],
                        "r": round(g.radius * 10, 5), "convex": sense > 0,
                        "area": face.area * 100, "bb": m.bb_of(face)})
    bins = defaultdict(list)
    for e in entries:
        bins[(e["axis"], e["direction"], e["r"], e["convex"])].append(e)
    groups = []
    for (axis, direction, radius, convex), rows in bins.items():
        centres = defaultdict(list)
        for row in rows:
            centres[tuple(row["centre"])].append(row)
        pending = set(centres)
        while pending:
            component = {pending.pop()}
            frontier = list(component)
            while frontier:
                p = frontier.pop()
                neighbors = {q for q in pending if math.dist(p, q) <= .76}
                pending -= neighbors
                component |= neighbors
                frontier.extend(neighbors)
            if len(component) < 2:
                continue
            diameter = max(math.dist(p, q) for p in component for q in component)
            if diameter < .001:
                continue
            selected = [r for c in component for r in centres[c]]
            master = max(component, key=lambda c: sum(r["area"] for r in centres[c]))
            minor = [r for r in selected if tuple(r["centre"]) != master and r["area"] < 4]
            bb = [min(r["bb"][2 * i] for r in selected) if j == 0 else
                  max(r["bb"][2 * i + 1] for r in selected) for i in range(3) for j in range(2)]
            status = "translated-ridge-family" if diameter <= 1.31 and (radius >= 2.5 or convex and radius >= 1) else "review-envelope"
            if body.name == "PRINT_motor_mount" and bb[4] < -18:
                status = "protected-belt-region"
            groups.append({"axis": axis, "direction": direction, "radius": radius, "convex": convex,
                           "master_centre": master, "centres": len(component),
                           "diameter": round(diameter, 4), "faces": len(selected),
                           "all_faces": [r["i"] for r in selected],
                           "minor_faces": [r["i"] for r in minor],
                           "minor_area_mm2": round(sum(r["area"] for r in minor), 4),
                           "bounds_mm": [round(x, 4) for x in bb], "status": status})
    return sorted(groups, key=lambda r: (-len(r["minor_faces"]), -r["minor_area_mm2"]))


def scan(app):
    by = bodies(app)
    report = {}
    for n in STRUCTURAL:
        report[n] = {"stats": stats(by[n]), "families": families(by[n]),
                     "plane_bands": plane_bands(by[n])}
    STATE["scan"] = report
    write_report()
    return {n: {"faces": r["stats"]["faces"], "families": len(r["families"]),
                "ridge_faces": sum(len(g["minor_faces"]) for g in r["families"]
                                   if g["status"] == "translated-ridge-family"),
                "plane_bands": len(r["plane_bands"])}
            for n, r in report.items()}


def plane_bands(body):
    m = load("sparkshift_ahg_min")
    bins = defaultdict(list)
    for i, face in enumerate(body.faces):
        g = face.geometry
        if not isinstance(g,adsk.core.Plane) or face.area*100>5:
            continue
        n=(g.normal.x,g.normal.y,g.normal.z)
        bb=m.bb_of(face)
        if abs(n[1])>.05 or bb[3]-bb[2]<.2:
            continue
        point=face.pointOnFace
        offset=sum(a*b*10 for a,b in zip(n,(point.x,point.y,point.z)))
        bins[(tuple(round(v,6) for v in n),round(bb[2],3),round(bb[3],3))].append(
            {"i":i,"offset":round(offset,6),"bb":bb,"area":face.area*100})
    groups=[]
    for (normal,y0,y1),rows in bins.items():
        pending=set(range(len(rows)))
        while pending:
            selected={pending.pop()}
            frontier=list(selected)
            while frontier:
                index=frontier.pop()
                p=tuple((rows[index]["bb"][2*k]+rows[index]["bb"][2*k+1])/2 for k in (0,2))
                neighbors={j for j in pending if math.dist(p,tuple(
                    (rows[j]["bb"][2*k]+rows[j]["bb"][2*k+1])/2 for k in (0,2)))<1.5}
                pending-=neighbors
                selected|=neighbors
                frontier.extend(neighbors)
            faces=[rows[j] for j in selected]
            offsets={r["offset"] for r in faces}
            if len(offsets)<3 or max(offsets)-min(offsets)>1.31:
                continue
            bb=[min(r["bb"][2*k] for r in faces) if end==0 else max(
                r["bb"][2*k+1] for r in faces) for k in range(3) for end in (0,1)]
            if body.name=="PRINT_motor_mount" and bb[4]<-18:
                continue
            groups.append({"faces":[r["i"] for r in faces],"normal":normal,"y":[y0,y1],
                           "offset_span_mm":max(offsets)-min(offsets),"bounds_mm":bb,
                           "area_mm2":sum(r["area"] for r in faces)})
    return groups


def heal_plane_bands(app, name):
    m=load("sparkshift_ahg_min")
    initial=plane_bands(bodies(app)[name])
    pending=list(initial)
    seeds=[]
    while pending:
        component=[pending.pop(0)]
        changed=True
        while changed:
            changed=False
            for band in list(pending):
                if any(max(abs(a-b) for a,b in zip(band["y"],g["y"]))<.02 and
                       m.bb_gap_l(band["bounds_mm"],g["bounds_mm"])<.12 for g in component):
                    pending.remove(band)
                    component.append(band)
                    changed=True
        seeds.append(component)
    results=[]
    for index,seed in enumerate(seeds):
        current=[g for g in plane_bands(bodies(app)[name]) if any(
            max(abs(a-b) for a,b in zip(g["y"],old["y"]))<.02 and
            m.bb_gap_l(g["bounds_mm"],old["bounds_mm"])<.12 for old in seed)]
        if not current:
            continue
        ids=sorted({i for group in current for i in group["faces"]})
        report=heal_indices(app,name,ids,"Continuous planar boundary %d" % (index+1),
                            axial_planes=True,metadata={"plane_band_groups":current})
        results.append({"status":report["status"],"selected_faces":len(ids),
                        "error":report.get("error")})
    return {"part":name,"results":results,"remaining":plane_bands(bodies(app)[name]),
            "current":stats(bodies(app)[name])}


def heal_family(app, name, radius, centre, include_side_planes=True, whole_family=False,
                all_offset_faces=False):
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the separate surface-cleanup review copy")
    proxy = bodies(app)[name]
    group = next((g for g in families(proxy) if abs(g["radius"] - radius) < 1e-4
                  and math.dist(g["master_centre"], centre) < .02), None)
    if group is None or group["status"] != "translated-ridge-family":
        raise RuntimeError("No eligible ridge family")
    ids = group["all_faces"] if whole_family else group["minor_faces"]
    if all_offset_faces:
        ids = []
        for i in group["all_faces"]:
            g = proxy.faces.item(i).geometry
            xyz = [g.origin.x * 10, g.origin.y * 10, g.origin.z * 10]
            c = [xyz[j] for j in range(3) if j != group["axis"]]
            if math.dist(c, group["master_centre"]) > 1e-4:
                ids.append(i)
    return heal_indices(app, name, ids, "Analytic cleanup - R%.3f surface" % radius,
                        group["axis"], include_side_planes, False, {"family": group})


def heal_indices(app, name, ids, label, axis=1, side_planes=True, axial_planes=False, metadata=None):
    if app.activeDocument.creationId != STATE["document"]:
        raise RuntimeError("Activate the separate surface-cleanup review copy")
    s = load("pancake_paths_study")
    proxy = bodies(app)[name]
    before = s.tbm().copy(proxy)
    selected = {}
    for i in ids:
        f = proxy.faces.item(i).nativeObject or proxy.faces.item(i)
        selected[f.tempId] = f
    if side_planes or axial_planes:
        for face in list(selected.values()):
            for edge in face.edges:
                for adjacent in edge.faces:
                    g = adjacent.geometry
                    if not isinstance(g, adsk.core.Plane) or adjacent.area * 100 > 4:
                        continue
                    normal = [g.normal.x, g.normal.y, g.normal.z][axis]
                    if (side_planes and abs(normal) < .05) or (axial_planes and abs(normal) > .999):
                        selected[adjacent.tempId] = adjacent
    collection = adsk.core.ObjectCollection.create()
    for f in selected.values():
        collection.add(f)
    component = (proxy.nativeObject or proxy).parentComponent
    report = {"part": name, "operation": label, "selected_faces": len(selected), "before": stats(before),
              **(metadata or {})}
    if not selected:
        raise RuntimeError("No faces selected for " + label)
    feature = None
    try:
        feature = component.features.deleteFaceFeatures.add(collection)
        if feature is None or feature.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            raise RuntimeError("Face healing failed" if feature is None else feature.errorOrWarningMessage)
        feature.name = label
        current = bodies(app)[name]
        if current.lumps.count != 1:
            raise RuntimeError("Healing split the part")
        report["after"] = stats(current)
        report["volume_change_mm3"] = round((current.volume - before.volume) * 1000, 6)
        report["status"] = "healed-pending-clearance-review"
        STATE.setdefault("accepted", {}).setdefault(name, []).append(feature)
    except RuntimeError as error:
        report["status"] = "failed"
        report["error"] = str(error)
        if feature is not None and feature.isValid:
            feature.deleteMe()
        current = bodies(app)[name]
        if stats(current) != stats(before):
            raise RuntimeError("Failed healing did not restore its input: " + name)
    STATE["history"].append(report)
    write_report()
    return report


def coaxial_patch(app, name, centre, master_radius, retired_radii, label):
    proxy = bodies(app)[name]
    ids = []
    for i, face in enumerate(proxy.faces):
        g = face.geometry
        if not isinstance(g, adsk.core.Cylinder) or abs(g.axis.y) < .99999:
            continue
        c = (g.origin.x * 10, g.origin.z * 10)
        d = math.dist(c, centre)
        r = g.radius * 10
        if d > 1.31:
            continue
        if any(abs(r - old) < 1e-4 for old in retired_radii) or (
                abs(r - master_radius) < 1e-4 and d > .02 and face.area * 100 < 4):
            ids.append(i)
    return heal_indices(app, name, ids, label, axial_planes=True,
                        metadata={"centre": centre, "retained_radius": master_radius,
                                  "retired_radii": retired_radii})


def replace_cylinder_patch(app, name, centre, radius, old_radii, y0, y1, label,
                           cone_template=None, extra_ids=()):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    proxy = bodies(app)[name]
    before = s.tbm().copy(proxy)
    component = (proxy.nativeObject or proxy).parentComponent
    if cone_template is None:
        cylinder = s.cyl(*centre, y0 - 2, y1 + 2, radius)
        side = next(f for f in cylinder.faces if isinstance(f.geometry, adsk.core.Cylinder))
    else:
        g=cone_template
        r0,r1=g.radius-1.5*math.tan(g.halfAngle),g.radius+1.5*math.tan(g.halfAngle)
        if r0<=0:
            raise RuntimeError("The cone guide would cross its apex")
        p0=adsk.core.Point3D.create(g.origin.x-g.axis.x*1.5,g.origin.y-g.axis.y*1.5,g.origin.z-g.axis.z*1.5)
        p1=adsk.core.Point3D.create(g.origin.x+g.axis.x*1.5,g.origin.y+g.axis.y*1.5,g.origin.z+g.axis.z*1.5)
        cylinder=s.tbm().createCylinderOrCone(p0,r0,p1,r1)
        side=next(f for f in cylinder.faces if isinstance(f.geometry,adsk.core.Cone))
    sheet = s.tbm().copy(side)
    if proxy.assemblyContext:
        inverse = proxy.assemblyContext.transform2.copy()
        inverse.invert()
        s.tbm().transform(sheet, inverse)
    guide = component.features.baseFeatures.add()
    guide.name = label + " guide"
    guide.startEdit()
    try:
        component.bRepBodies.add(sheet, guide)
    finally:
        guide.finishEdit()
    guide_body = next(body for body in component.bRepBodies if not body.isSolid)
    guide_body.name = label + " guide"
    report = {"part": name, "operation": label, "before": stats(before), "centre": centre,
              "radius": radius, "old_radii": old_radii}
    replace = None
    try:
        proxy = bodies(app)[name]
        selected = {}
        for f in proxy.faces:
            g = f.geometry
            if cone_template is None:
                if not isinstance(g, adsk.core.Cylinder) or abs(g.axis.y) < .99999:
                    continue
                if math.dist((g.origin.x * 10, g.origin.z * 10), centre) > 1.31:
                    continue
            else:
                if not isinstance(g,adsk.core.Cone) or abs(g.halfAngle-cone_template.halfAngle)>1e-8:
                    continue
                if g.axis.dotProduct(cone_template.axis)<.999999:
                    continue
                if g.origin.distanceTo(cone_template.origin)*10>1.31:
                    continue
            if not any(abs(g.radius * 10 - r) < 1e-4 for r in old_radii):
                continue
            bb = m.bb_of(f)
            if bb[2] < y0 - 1e-4 or bb[3] > y1 + 1e-4:
                continue
            native = f.nativeObject or f
            selected[native.tempId] = native
        for i in extra_ids:
            f=proxy.faces.item(i).nativeObject or proxy.faces.item(i)
            selected[f.tempId]=f
        for f in list(selected.values()):
            for edge in f.edges:
                for adjacent in edge.faces:
                    if isinstance(adjacent.geometry, adsk.core.Plane) and adjacent.area * 100 < 4:
                        bb = m.bb_of(adjacent)
                        if bb[2] >= y0 - 1e-4 and bb[3] <= y1 + 1e-4:
                            selected[adjacent.tempId] = adjacent
        sources, targets = adsk.core.ObjectCollection.create(), adsk.core.ObjectCollection.create()
        for f in selected.values():
            sources.add(f)
        targets.add(guide_body)
        if not sources.count:
            raise RuntimeError("No source faces for cylinder replacement")
        inp = component.features.replaceFaceFeatures.createInput(sources, False, targets)
        replace = component.features.replaceFaceFeatures.add(inp)
        if replace is None or replace.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
            raise RuntimeError("Replace Face failed" if replace is None else replace.errorOrWarningMessage)
        replace.name = label
        remove = component.features.removeFeatures.add(
            next(body for body in component.bRepBodies if not body.isSolid))
        remove.name = "Remove " + label + " guide"
        current = bodies(app)[name]
        if current.lumps.count != 1:
            raise RuntimeError("Cylinder replacement split the part")
        report.update(status="replaced-pending-clearance-review", after=stats(current),
                      volume_change_mm3=round((current.volume - before.volume) * 1000, 6))
    except RuntimeError as error:
        report.update(status="failed", error=str(error))
        if replace is not None and replace.isValid:
            replace.deleteMe()
        if guide.isValid:
            guide.deleteMe()
        if stats(bodies(app)[name]) != stats(before):
            raise RuntimeError("Cylinder replacement rollback failed")
    STATE["history"].append(report)
    write_report()
    return report


def heal_part_families(app, name, limit=None):
    groups = [g for g in families(bodies(app)[name]) if
              g["status"] == "translated-ridge-family" and g["minor_faces"]]
    if limit is not None:
        groups = groups[:limit]
    results = []
    STATE["batch"] = {"part": name, "state": "running", "done": 0, "total": len(groups)}
    write_report()
    for group in groups:
        remaining = [g for g in families(bodies(app)[name]) if
                     abs(g["radius"] - group["radius"]) < 1e-4 and
                     math.dist(g["master_centre"], group["master_centre"]) < .02]
        if not remaining:
            continue
        report = heal_family(app, name, group["radius"], group["master_centre"])
        results.append({"radius": group["radius"], "centre": group["master_centre"],
                        "status": report["status"]})
        STATE["batch"]["done"] += 1
        write_report()
    STATE["batch"]["state"] = "complete"
    write_report()
    return {"part": name, "results": results, "current": stats(bodies(app)[name])}


def append_cut(app, name, tool, label):
    return append_boolean(app, name, tool, label, "cut")


def append_join(app, name, tool, label):
    return append_boolean(app, name, tool, label, "join")


def append_boolean(app, name, tool, label, kind):
    s = load("pancake_paths_study")
    proxy = bodies(app)[name]
    before = s.tbm().copy(proxy)
    expected = s.tbm().copy(proxy)
    s.op(expected, tool, kind)
    if expected.lumps.count != 1:
        raise RuntimeError("Surface normalization would split the part")
    component = (proxy.nativeObject or proxy).parentComponent
    if component.bRepBodies.count != 1:
        raise RuntimeError("Finish or remove unrelated construction bodies before normalization")
    local = s.tbm().copy(tool)
    if proxy.assemblyContext:
        inverse = proxy.assemblyContext.transform2.copy()
        inverse.invert()
        s.tbm().transform(local, inverse)
    feature = component.features.baseFeatures.add()
    feature.name = label + " tool"
    feature.startEdit()
    try:
        for i in range(local.lumps.count):
            component.bRepBodies.add(s.tbm().copy(local.lumps.item(i)), feature)
    finally:
        feature.finishEdit()
    tools = adsk.core.ObjectCollection.create()
    target = component.bRepBodies.itemByName(name)
    added = [body for body in component.bRepBodies if body.name != name]
    if target is None or len(added) != local.lumps.count:
        raise RuntimeError("Cannot identify every new normalization tool")
    for i, body in enumerate(added):
        body.name = label + " tool " + str(i)
        tools.add(body)
    inp = component.features.combineFeatures.createInput(target, tools)
    inp.operation = (adsk.fusion.FeatureOperations.CutFeatureOperation if kind == "cut"
                     else adsk.fusion.FeatureOperations.JoinFeatureOperation)
    inp.isKeepToolBodies = False
    cut = component.features.combineFeatures.add(inp)
    cut.name = label
    if cut.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState:
        raise RuntimeError(cut.errorOrWarningMessage)
    after = bodies(app)[name]
    if abs(after.volume - expected.volume) > 1e-7 or after.lumps.count != 1:
        raise RuntimeError("Native normalization differs from the reviewed shape")
    report = {"part": name, "operation": label, "before": stats(before), "after": stats(after),
              "status": "normalized-pending-clearance-review"}
    STATE["history"].append(report)
    write_report()
    return report


def lower_heatset(app):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    by = bodies(app)
    nut_name = "ARM_LOWER_M3_HEX_NUT"
    bolt_name = "ARM_LOWER_M3x16_BUTTON_HEAD"
    if nut_name not in by or bolt_name not in by:
        raise RuntimeError("The lower through-nut baseline is not present")
    centre = (8.0, -13.3)
    host = s.cyl(*centre, 20.5, 24.5, 3.8)
    s.op(host, m.cone_y(*centre, 20.3, 3.3, 20.5, 3.8), "join")
    append_join(app, "PRINT_arm_front_half", host, "Backed lower heat-set boss")
    pilot = s.cyl(*centre, 20.5, 24.51, 2.0)
    s.op(pilot, m.cone_y(*centre,24.1,2.0,24.5,2.2), "join")
    append_cut(app, "PRINT_arm_front_half", pilot, "Lower M3 insert pilot and lead-in")
    append_cut(app, "PRINT_arm_front_half", s.cyl(*centre, 15.5, 20.51, 1.7),
               "Lower bolt passage to insert shoulder")
    relief = m.arc_slot(centre, 4.15, -7, .3, 20.15, 24.85)
    append_cut(app, "PRINT_000_outer_shell_of_extruder_1", relief, "Heat-set boss swing clearance")
    insert = s.cyl(*centre, 20.5, 24.5, 2.3)
    s.op(insert, s.cyl(*centre, 20.4, 24.6, 1.5), "cut")
    by = bodies(app)
    insert_name = "ARM_LOWER_M3_HEATSET_4p6x4"
    m.replace(by[nut_name], insert, insert_name, insert_name)
    bolt = m.screw_shape(*centre, 11.4, 2.85, 1.65, 25.4, r=1.5)
    socket_r = 2.0 / math.sqrt(3)
    polygon = [(centre[0] + socket_r * math.cos(i * math.pi / 3),
                centre[1] + socket_r * math.sin(i * math.pi / 3)) for i in range(6)]
    s.op(bolt, load("sparkshift_strength_v7").polygon(polygon, 9.65, 10.7), "cut")
    bolt_new_name = "ARM_LOWER_M3x14_BUTTON_HEAD"
    m.replace(bodies(app)[bolt_name], bolt, bolt_new_name, bolt_new_name)
    report = {"part": "lower arm joint", "operation": "Replace loose nut with backed heat-set",
              "insert": insert_name, "insert_mm": [3, 4.6, 4.0], "insert_y_mm": [20.5, 24.5],
              "pilot_diameter_mm": 4.0, "lead_in_diameter_mm": 4.4,
              "host_diameter_mm": 7.6, "radial_material_before_insertion_mm": 1.8,
              "radial_material_outside_insert_envelope_mm": 1.5,
              "bolt": bolt_new_name, "engagement_mm": 4.0, "tip_beyond_insert_mm": .9,
              "load_direction": "Bolt tension seats the insert against its rear backing shoulder",
              "fit_limit": "Pilot remains a reference; match the actual insert and printing process",
              "status": "modified-pending-clearance-review"}
    STATE["hardware_changes"] = {nut_name: insert_name, bolt_name: bolt_new_name}
    STATE["history"].append(report)
    write_report()
    return report


def current_proof(app):
    s, m, w = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_cam_v8")
    by, original = bodies(app), STATE["before"]
    report = {"protected_regions": {}, "unchanged_hardware": [], "unexpected_hardware_changes": [],
              "magnet_backing_missing_mm3": None, "errors": []}
    h, p, c = m.HOB_MOVING, w.STATE["Mv"], w.STATE["C"]
    regions = {
        "PRINT_arm_front_half": [s.cyl(*h, 24.15, 26.75, 3.67),
                                 s.cyl(*p, 20.1, 25.15, 4.4)],
        "PRINT_carrier_box_left": [s.cyl(*h, 12.5, 16.05, 3.7),
                                   s.cyl(*p, 10.95, 15.65, 7.55)],
        "PRINT_motor_mount": [s.box(-30, 30, -20, 40, -70, -18),
                             s.cyl(*m.HOB_FIXED, 12.5, 15.5, 3.7),
                             s.cyl(*p, 3.25, 5.35, 3.55),
                             s.cyl(*m.STATE["F"], 3.25, 5.35, 3.55)],
        "PRINT_000_outer_shell_of_extruder_1": [
            s.cyl(*m.HOB_FIXED, 24.15, 27.1, 3.7),
            s.cyl(*m.STATE["F"], 20.1, 24.9, 4.2),
            s.cyl(*p, 25.05, 28.55, 4.2),
            s.cyl(*c, 10.65, 13.25, 4.67)],
    }
    for name, zones in regions.items():
        results = []
        for i, zone in enumerate(zones):
            a, b = s.tbm().copy(original[name]), s.tbm().copy(by[name])
            s.op(a, zone, "common")
            s.op(b, zone, "common")
            added, removed = s.tbm().copy(b), s.tbm().copy(a)
            s.op(added, a, "cut")
            s.op(removed, b, "cut")
            results.append({"region": i, "added_mm3": added.volume * 1000,
                            "removed_mm3": removed.volume * 1000})
        report["protected_regions"][name] = results
    magnet = m.bb_of(by["OCT_RECEIVER_MAGNET_3"])
    footprint = s.box(magnet[0],magnet[1],magnet[2]-1.5,magnet[2],magnet[4],magnet[5])
    missing = s.tbm().copy(footprint)
    s.op(missing, by["PRINT_000_outer_shell_of_extruder_1"], "cut")
    report["magnet_backing_missing_mm3"] = missing.volume * 1000
    replacements = STATE.get("hardware_changes", {})
    for n, before in original.items():
        if n in STRUCTURAL or n in replacements:
            continue
        if n not in by or stats(by[n]) != stats(before):
            report["unexpected_hardware_changes"].append(n)
        else:
            report["unchanged_hardware"].append(n)
    report["feature_issues"] = {}
    for n in STRUCTURAL:
        comp = (by[n].nativeObject or by[n]).parentComponent
        issues = [{"name": f.name, "health": f.healthState, "message": f.errorOrWarningMessage}
                  for f in comp.features if f.healthState != adsk.fusion.FeatureHealthStates.HealthyFeatureHealthState]
        if issues:
            report["feature_issues"][n] = issues
    (OUT / "analytic_geometry_proof.json").write_text(json.dumps(report, indent=2))
    return report


def contacts(app, names, poses=((0, 0), (90, -4.453), (150, -6.053), (0, .3), (0, -7))):
    s, m, w = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_cam_v8")
    by = bodies(app)
    originals = STATE["before"]
    paths = {n: b.assemblyContext.fullPathName for n, b in by.items()}
    current = {n: s.tbm().copy(b) for n, b in by.items()}
    report = {"parts": list(names), "poses": list(poses), "unexpected_overlaps": [], "inherited_overlaps": [],
              "press_fits": [], "near": [], "errors": []}
    for phi, arm in poses:
        shapes, baseline = {}, {}
        for n, b in current.items():
            if "TEMP" in paths[n] or n == "CLOSING_SPRING_ENVELOPE":
                continue
            rot = (w.STATE["C"], phi) if n in w.CAM_ROTATES else (
                (w.STATE["Mv"], arm) if any(g in paths[n] for g in m.ARM_GROUPS) else None)
            shapes[n] = m.rotated(b, *rot) if rot and rot[1] else s.tbm().copy(b)
            if n in originals:
                baseline[n] = m.rotated(originals[n], *rot) if rot and rot[1] else originals[n]
        for name in names:
            a = shapes[name]
            for other, b in shapes.items():
                if other == name or other in names and other < name:
                    continue
                if m.bb_gap_l(m.bb_of(a), m.bb_of(b)) > .4:
                    continue
                try:
                    distance = app.measureManager.measureMinimumDistance(a, b).value * 10
                    volume = s.common_volume(a, b)[0] if distance < 1e-5 else 0.0
                    if volume > .001:
                        record = [phi, arm, name, other, round(volume, 5)]
                        if ({name, other} == {"PRINT_arm_front_half", "ARM_LOWER_M3_HEATSET_4p6x4"} and
                            volume < (16.22 if STATE.get("arm_heatset_pilots") else 1.6)):
                            report["press_fits"].append(record)
                        elif (STATE.get("arm_heatset_pilots") and
                              {name, other} == {"PRINT_arm_front_half","ARM_SPLIT_M3_INSERT_0"} and volume<16.22):
                            report["press_fits"].append(record)
                        elif (STATE.get("aligned_frame_pilot") and
                              {name, other} == {"PRINT_motor_mount", "FRAME_M3_HEATSET_in_P01"} and
                              volume < 16.22):
                            report["press_fits"].append(record)
                        else:
                            old_volume = s.common_volume(baseline[name], baseline[other])[0] if (
                                name in baseline and other in baseline) else 0.0
                            if volume <= old_volume + .002:
                                report["inherited_overlaps"].append(record + [round(old_volume, 5)])
                            else:
                                report["unexpected_overlaps"].append(record + [round(old_volume, 5)])
                    elif distance < .4:
                        report["near"].append([phi, arm, name, other, round(distance, 5)])
                except RuntimeError as error:
                    report["errors"].append([phi, arm, name, other, str(error)])
        (OUT / ("analytic_contacts_" + names[0] + ".json")).write_text(json.dumps(report, indent=2))
    return report


def refill_arc_boundary(app, name, point, outer, inner, y0, y1, label, angles=(-7, .3), clip=None):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    envelope = m.arc_slot(point, outer, *angles, y0, y1)
    void = m.arc_slot(point, inner, *angles, y0 - .001, y1 + .001)
    s.op(envelope, void, "cut")
    if clip is not None:
        s.op(envelope, s.box(*clip), "common")
    joined = append_join(app, name, envelope, label + " solid boundary")
    cut = append_cut(app, name, void, label + " continuous relief")
    return {"join": joined, "cut": cut}


def normalize_fore_pivot(app):
    s, m, w = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_cam_v8")
    name, p = "PRINT_arm_front_half", w.STATE["Mv"]
    h = s.centre(bodies(app)["SHAFT_hob_left"])
    results = [append_join(app, name, s.cyl(*p, 19.8, 24.25, 6.8), "Concentric fore-pivot cup")]
    for a, b, r in ((19.79, 20.15, 6.15), (20.15, 22.0, 2.35), (22.0, 22.3, 2.8),
                    (22.3, 24.15, 3.52), (24.15, 25.1, 4.35)):
        results.append(append_cut(app, name, s.cyl(*p, a, b, r),
                                  "Aligned pivot bore %.2f %.2f" % (a, b)))
    results.append(append_cut(app, name, s.cyl(*h, 19.79, 20.15, 10.0),
                              "Concentric 37T clearance at pivot"))
    results.append(append_cut(app, name, s.cyl(*h, 20.15, 24.25, 9.35),
                              "Concentric HGX clearance at pivot"))
    results.append(append_cut(app, name, s.box(-20, 3.65, 19.79, 24.251, 5.0, 24.0),
                              "Align fore-pivot outer flank"))
    return [r["after"] for r in results]


def revert_operations(app, name, labels):
    component = (bodies(app)[name].nativeObject or bodies(app)[name]).parentComponent
    wanted = set(labels) | {label + " tool" for label in labels}
    features = [f for f in component.features if f.name in wanted]
    if len(features) != 2 * len(labels):
        raise RuntimeError("Cannot identify every owned feature for rollback")
    for feature in reversed(features):
        if not feature.deleteMe():
            raise RuntimeError("Could not roll back " + feature.name)
    for row in STATE["history"]:
        if row.get("part") == name and row.get("operation") in labels:
            row["status"] = "reverted-for-corrected-seat-boundary"
    write_report()
    return stats(bodies(app)[name])


def normalize_cam_pocket(app):
    s, m, w = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_cam_v8")
    name, c = "PRINT_motor_mount", w.STATE["C"]
    # The interleaved front-case support occupies part of this annulus; do not refill it.
    results = [append_cut(app, name, s.cyl(*c, 4.5, 11.4, 9.6), "One cylindrical cam pocket")]
    return [r["after"] for r in results]


def normalize_fixed_compound_pocket(app):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    by = bodies(app)
    f, p = m.STATE["F"], m.STATE["Mv"]
    motor = m.motor_axis(by)
    name = "PRINT_motor_mount"
    ring = s.cyl(*f, 5.3, 11.4, 10.9)
    s.op(ring, s.cyl(*f, 5.29, 11.41, 10.2), "cut")
    results = [append_join(app, name, ring, "Concentric fixed-compound pocket boundary")]
    for point, radius, a, b, label in ((f, 10.2, 5.3, 11.4, "One fixed-compound clearance"),
                                      (p, 10.2, 5.3, 11.4, "Preserve moving-compound clearance")):
        results.append(append_cut(app, name, s.cyl(*point, a, b, radius), label))
    slot = load("sparkshift_strength_v7").tapered_capsule(motor, 3.6, (0, 8.8), .9, 5.29, 11.4)
    results.append(append_cut(app, name, slot, "Round-ended pinion and gear-valley clearance"))
    results.append(append_cut(app, name, s.cyl(*p, 10.6, 11.4, 10.65),
                              "Moving hinge-ring front clearance"))
    return [r["after"] for r in results]


def normalize_case_boundaries(app):
    m = load("sparkshift_ahg_min")
    results = [
        refill_arc_boundary(app, "PRINT_000_outer_shell_of_extruder_1",
                            (14.79551, 32.11082), 7.4, 6.9, 11.4, 14.4,
                            "Analytic upper arm shoulder"),
        refill_arc_boundary(app, "PRINT_000_outer_shell_of_extruder_1",
                            m.FOLLOWER_AXIS, 9.3, 8.7, 11.4, 13.4,
                            "Analytic follower-fork pocket"),
        refill_arc_boundary(app, "PRINT_carrier_box_left",
                            (18.75, -14.7294047847718), 4.5, 3.85, 12.0, 14.49,
                            "Analytic lower frame-boss clearance", angles=(-.3, 7),
                            clip=(13.55, 17.8, 12.0, 14.49, -11.84, -8.0)),
    ]
    return results


def normalize_filament_gallery(app):
    m = load("sparkshift_ahg_min")
    return append_cut(app, "PRINT_RedLizard_HF_tool_carrier",
                      m.axis_cyl((0, 22.7, 0), (0, 0, 1), 1.35, -18.95, 16.75),
                      "Continuous axial filament gallery")


def normalize_rear_foot(app):
    s, m = load("pancake_paths_study"), load("sparkshift_ahg_min")
    name, centre = "PRINT_carrier_box_left", (15.4, -9.8794047847718)
    results = [append_join(app, name, s.cyl(*centre, 12.0, 15.6, 2.2),
                           "One circular lower-contact support")]
    trim = s.box(13.0, 18.0, 12.0, 15.6, -12.2, -8.0)
    s.op(trim, s.cyl(*centre, 11.99, 15.61, 2.2), "cut")
    results.append(append_cut(app, name, trim, "Continuous lower-support outer arc"))
    results.append(append_cut(app, name,
                              m.arc_slot((18.75, -14.7294047847718), 3.85, -.3, 7, 12.0, 14.49),
                              "Preserve lower frame-boss travel"))
    results.append(append_cut(app, name, s.box(17.0,18.0,11.99,15.61,-12.2,-7.5),
                              "Align entire lower-support flank"))
    return [r["after"] for r in results]


def normalize_front_moving_drive(app):
    s, m, w = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_cam_v8")
    by = bodies(app)
    h, fixed = s.centre(by["SHAFT_hob_left"]), s.centre(by["SHAFT_hob_right"])
    name = "PRINT_000_outer_shell_of_extruder_1"
    tool = m.arc_slot(h,10.3,-7,.3,11.4,20.35)
    s.op(tool,s.box(-30,20.5,11.39,20.36,-20,25),"common")
    result = append_cut(app,name,tool,"One steel-axis moving-drive sweep with 2 mm wall")
    return {"hob_axis_xz_mm": h, "fixed_axis_xz_mm": fixed, "operation": result}


def normalize_frame_pilot(app):
    s, m, w = load("pancake_paths_study"), load("sparkshift_ahg_min"), load("sparkshift_cam_v8")
    centre = s.centre(bodies(app)["FRAME_M3_HEATSET_in_P01"])
    ring = s.cyl(*centre, .3, 4.6, 2.75)
    s.op(ring, s.cyl(*centre, .29, 4.61, 2.0), "cut")
    append_join(app, "PRINT_motor_mount", ring, "Solid coaxial frame-insert surroundings")
    append_cut(app, "PRINT_motor_mount", s.cyl(*centre,.3,4.6,2.0),
               "Retain nominal 4 mm frame-insert pilot")
    append_cut(app, "PRINT_motor_mount", s.cyl(*w.STATE["C"],2.7,4.5,9.45),
               "Preserve horn-side cam-neck clearance")
    report = {"centre_xz_mm": centre, "pilot_diameter_mm": 4.0,
              "insert_reference_od_mm": 4.6, "insert_y_mm": [.3,4.3],
              "nominal_diameter_changed": False,
              "change": "Remove shifted-cylinder pilot halos; retain the insert axis and nominal bore",
              "physical_fit": "Existing frame-pilot reference, not a supplier-qualified insertion fit"}
    STATE["aligned_frame_pilot"] = report
    write_report()
    return report


def finish_planar_roots(app):
    s=load("pancake_paths_study")
    results=[
        append_join(app,"PRINT_motor_mount",s.box(10.2,12.2,5.3,6.6,25.5,26.2),
                    "Solid aligned spring-shoulder floor"),
        append_join(app,"PRINT_motor_mount",s.box(-10.14,-9.95,5.3,6.0,53.05,53.25),
                    "Solid aligned upper-pocket corner"),
    ]
    name="PRINT_carrier_box_left"
    body=bodies(app)[name]
    desired=(5.397762,14.6,32.11082424143633)
    cones=[f.geometry for f in body.faces if isinstance(f.geometry,adsk.core.Cone)
           and abs(f.geometry.radius*10-5.1633)<1e-4 and abs(f.geometry.halfAngle-.15707963267948966)<1e-8]
    if not cones:
        raise RuntimeError("The known spring-relief cone is absent")
    template=min(cones,key=lambda g:math.dist(
        (g.origin.x*10,g.origin.y*10,g.origin.z*10),desired))
    ids={i for group in plane_bands(body) for i in group["faces"]}
    results.append(replace_cylinder_patch(app,name,(template.origin.x*10,template.origin.z*10),
                     template.radius*10,[template.radius*10],2.5,15.6,"One analytic spring-relief cone",
                     cone_template=template,extra_ids=ids))
    return results


def size_arm_heatset_pilots(app):
    s,m=load("pancake_paths_study"),load("sparkshift_ahg_min")
    rows=[]
    for label,centre,a,b in (("lower",(8,-13.3),20.5,24.5),
                             ("upper",(14.95,31.4),15.6,19.6)):
        ring=s.cyl(*centre,a,b,2.65)
        s.op(ring,s.cyl(*centre,a-.01,b+.01,2.0),"cut")
        append_join(app,"PRINT_arm_front_half",ring,label.title()+" heat-set pilot backing")
        pilot=s.cyl(*centre,a,b,2.0)
        taper=m.cone_y(*centre,b-.4,2.0,b,2.2) if label=="lower" else m.cone_y(*centre,a,2.2,a+.4,2.0)
        s.op(pilot,taper,"join")
        append_cut(app,"PRINT_arm_front_half",pilot,label.title()+" calibrated heat-set pilot")
        rows.append({"joint":label,"centre_xz_mm":centre,"insert_y_mm":[a,b],
                     "pilot_diameter_mm":4.0,"entry_diameter_mm":4.4,"entry_length_mm":.4})
    report={"insert_reference":"ruthex RX-M3Sx4.0, M3, 4.6 mm OD, 4 mm length",
            "product_url":"https://www.ruthex.de/en/products/ruthex-gewindeeinsatz-m3s-100stuck-rx-m3x4-0-short-messing-gewindebuchsen-fur-3d-druck",
            "manufacturer_table_url":"https://cdn.shopify.com/s/files/1/0567/7019/9760/files/1Tabelle.PT05_c83a08d8-a1be-4f48-a772-9879f2ad8423.jpg?v=1748341702",
            "manufacturer_nominal_hole_mm":4.0,"manufacturer_min_wall_mm":1.6,
            "lower_nominal_wall_before_insertion_mm":1.8,"pilots":rows,
            "fit_limit":"The nominal manufacturer hole still requires calibration for the actual insert, material and printer"}
    STATE["arm_heatset_pilots"]=report
    (OUT/"v9_arm_heatset_pilots.json").write_text(json.dumps(report,indent=2))
    write_report()
    return report


def solo_views(app, keys, prefix="v9", views=("front_iso","rear_iso")):
    m, s = load("sparkshift_ahg_min"), load("pancake_paths_study")
    design=adsk.fusion.Design.cast(app.activeProduct)
    root=design.rootComponent
    by = bodies(app)
    colours = {"P01":(70,130,210), "P02":(150,95,185), "P03":(225,155,65),
               "P04R":(205,65,80), "P04F":(55,145,220), "P17":(85,180,115)}
    old = m.IMAGES_V4
    m.IMAGES_V4 = OUT / "images_v9"
    files = []
    try:
        for key in keys:
            name = PRINTS[key][0]
            bb = m.bb_of(by[name])
            centre = tuple((bb[2*i]+bb[2*i+1])/2 for i in range(3))
            extent = max(bb[1]-bb[0],bb[5]-bb[4]) * .11
            for phase, body in (("before",STATE["before"][name]),("after",by[name])):
                look=m.rgb_appearance(design,"v9 isolated "+key,colours.get(key,(185,190,200)))
                states=[(o,o.isLightBulbOn) for o in root.occurrences]
                group=root.occurrences.addNewComponent(adsk.core.Matrix3D.create())
                group.component.name="TEMP v9 "+key
                try:
                    feature=group.component.features.baseFeatures.add()
                    feature.startEdit()
                    try:
                        added=group.component.bRepBodies.add(s.tbm().copy(body),feature)
                        for face in added.faces:
                            face.appearance=look
                    finally:
                        feature.finishEdit()
                    group.component.bRepBodies.item(0).appearance=look
                    for o,_ in states:
                        o.isLightBulbOn=False
                    for suffix,eye,target,up,ext in m.std_views(centre,extent,views):
                        file=prefix+"_"+key+"_"+phase+suffix+".png"
                        m.camera_shot(app,file,eye,target,up,ext)
                        files.append(file)
                finally:
                    group.deleteMe()
                    for o,state in states:
                        if o.isValid:
                            o.isLightBulbOn=state
    finally:
        m.IMAGES_V4 = old
    (OUT / ("v9_images_" + keys[0] + ".json")).write_text(json.dumps(files,indent=2))
    return files


def assembled_arm_views(app):
    m, s, w = load("sparkshift_ahg_min"), load("pancake_paths_study"), load("sparkshift_cam_v8")
    design = adsk.fusion.Design.cast(app.activeProduct)
    root, by = design.rootComponent, bodies(app)
    names = [n for n,b in by.items() if any(g in b.assemblyContext.fullPathName for g in m.ARM_GROUPS)]
    names += ["6700ZZ arm rear hinge (on moving hub)","AXLE_4x24_moving","PRINT_compound_left"]
    names = list(dict.fromkeys(names))
    palette = {"PRINT_carrier_box_left":(205,65,80),"PRINT_arm_front_half":(55,145,220),
               "PRINT_feed_left":(100,175,95),"PRINT_compound_left":(150,100,190),
               "ARM_SPLIT_M3x10_SHCS_0":(235,190,50),"ARM_SPLIT_M3_INSERT_0":(210,150,50),
               "ARM_LOWER_M3x14_BUTTON_HEAD":(235,190,50),"ARM_LOWER_M3_HEATSET_4p6x4":(210,150,50)}
    old = m.IMAGES_V4
    m.IMAGES_V4 = OUT / "images_v9"
    files = []
    try:
        for mode in ("complete","structure"):
            chosen = names if mode=="complete" else [
                "PRINT_carrier_box_left","PRINT_arm_front_half","ARM_SPLIT_M3x10_SHCS_0",
                "ARM_SPLIT_M3_INSERT_0","ARM_LOWER_M3x14_BUTTON_HEAD","ARM_LOWER_M3_HEATSET_4p6x4"]
            items = [(s.tbm().copy(by[n]),n,m.rgb_appearance(design,"v9 arm "+n,
                      palette.get(n,(175,185,200)))) for n in chosen]
            states = [(o,o.isLightBulbOn) for o in root.occurrences]
            group = s.add_group(root,"TEMP v9 assembled arm",items)
            try:
                for o,_ in states:
                    o.isLightBulbOn=False
                views = ("front_iso","rear_iso","right") if mode=="complete" else ("right",)
                for suffix,eye,target,up,ext in m.std_views((8,15,30),10.3,views):
                    file="v9_arm_"+mode+suffix+".png"
                    m.camera_shot(app,file,eye,target,up,ext)
                    files.append(file)
                if mode=="structure":
                    for suffix,eye,target,up,ext in m.std_views((8,20,-12.5),3.0,("front_iso","rear_iso")):
                        file="v9_lower_heatset"+suffix+".png"
                        m.camera_shot(app,file,eye,target,up,ext)
                        files.append(file)
            finally:
                group.deleteMe()
                for o,state in states:
                    if o.isValid:
                        o.isLightBulbOn=state
    finally:
        m.IMAGES_V4=old
    (OUT / "v9_arm_images.json").write_text(json.dumps(files,indent=2))
    return files


def bed_face(body, direction):
    mesh = body.meshManager.createMeshCalculator()
    mesh.setQuality(adsk.fusion.TriangleMeshQualityOptions.NormalQualityTriangleMesh)
    points = mesh.calculate().nodeCoordinatesAsDouble
    candidates = []
    for face in body.faces:
        if not isinstance(face.geometry,adsk.core.Plane):
            continue
        point = face.pointOnFace
        ok, normal = face.evaluator.getNormalAtPoint(point)
        if not ok:
            raise RuntimeError("Cannot measure the supplied print face")
        n = (normal.x,normal.y,normal.z)
        if sum(n[i]*direction[i] for i in range(3)) > -.999:
            continue
        p = (point.x,point.y,point.z)
        protrusion = max(sum(n[k]*(points[i+k]-p[k]) for k in range(3))*10
                         for i in range(0,len(points),3))
        if protrusion > .01:
            continue
        candidates.append((face.area,tuple(-v for v in n),protrusion,
                           [point.x*10,point.y*10,point.z*10]))
    if not candidates:
        raise RuntimeError("No supporting planar face in the specified print direction: "+body.name)
    area, build, protrusion, origin = max(candidates,key=lambda c:c[0])
    contact_area = sum(c[0]*100 for c in candidates if
                       sum(c[1][i]*build[i] for i in range(3)) > .999999999 and
                       abs(sum(build[i]*(c[3][i]-origin[i]) for i in range(3))) < 1e-4)
    return {"build_direction":build,"face_area_mm2":area*100,
            "coplanar_contact_area_mm2":contact_area,
            "face_origin_mm":origin,"outside_plane_mm":protrusion}


def export_meshes(app):
    design = adsk.fusion.Design.cast(app.activeProduct)
    by = bodies(app)
    root = design.rootComponent
    folder=OUT/"stl_v9_assembly"
    folder.mkdir(parents=True,exist_ok=True)
    states=[(o,o.isLightBulbOn) for o in root.allOccurrences]
    body_states=[(b,b.isLightBulbOn) for b in by.values()]
    report={}
    try:
        for o,_ in states:
            o.isLightBulbOn=True
        for key,(name,file,direction) in PRINTS.items():
            body=by[name]
            if body.lumps.count!=1:
                raise RuntimeError("Print is not one connected solid: "+key)
            orientation=bed_face(body,direction)
            body.isLightBulbOn=True
            path=folder/(file+".stl")
            options=design.exportManager.createSTLExportOptions(body,str(path))
            options.meshRefinement=adsk.fusion.MeshRefinementSettings.MeshRefinementHigh
            options.isBinaryFormat=True
            if not design.exportManager.execute(options) or not path.exists() or path.stat().st_size<=84:
                raise RuntimeError("Missing raw STL output: "+key)
            report[key]={"path":str(path),"native":stats(body),**orientation}
            (OUT/"v9_mesh_export.json").write_text(json.dumps(report,indent=2))
    finally:
        for b,state in body_states:
            if b.isValid:
                b.isLightBulbOn=state
        for o,state in states:
            if o.isValid:
                o.isLightBulbOn=state
    return report


def tool_travel(app):
    s,m,w=load("pancake_paths_study"),load("sparkshift_ahg_min"),load("sparkshift_cam_v8")
    by=bodies(app)
    tools={n:s.tbm().copy(b) for n,b in by.items() if b.assemblyContext.fullPathName.startswith("12 ")
           and not n.startswith("REFERENCE_")}
    targets={}
    for n,b in by.items():
        if n in tools or n.startswith("REFERENCE_") or n=="CLOSING_SPRING_ENVELOPE":
            continue
        path=b.assemblyContext.fullPathName
        if n in w.CAM_ROTATES:
            targets[n]=m.rotated(b,w.STATE["C"],150)
        elif any(g in path for g in m.ARM_GROUPS):
            targets[n]=m.rotated(b,w.STATE["Mv"],-6.053)
        else:
            targets[n]=s.tbm().copy(b)
    distances=(0,2.5,5,7.5,10,15,20,25,30,35)
    report={"distances_mm":distances,"arm_deg":-6.053,"cam_deg":150,
            "tool_bodies":list(tools),"unexpected_overlaps":[],"errors":[],
            "excluded_display_references":["REFERENCE_*","CLOSING_SPRING_ENVELOPE"]}
    for distance in distances:
        for name,body in tools.items():
            moving=m.translated(body,dy=distance)
            for other,target in targets.items():
                if m.bb_gap_l(m.bb_of(moving),m.bb_of(target))>0:
                    continue
                try:
                    if app.measureManager.measureMinimumDistance(moving,target).value>1e-6:
                        continue
                    volume=s.common_volume(moving,target)[0]
                    if volume>.001:
                        report["unexpected_overlaps"].append([distance,name,other,round(volume,6)])
                except RuntimeError as error:
                    report["errors"].append([distance,name,other,str(error)])
        (OUT/"v9_tool_travel.json").write_text(json.dumps(report,indent=2))
    return report
