"""Render multi-view inspection sheets for the SparkShift v26 Accessory Suite using VTK."""

from pathlib import Path
import vtk
from PIL import Image, ImageDraw, ImageFont

from OCP.BRepMesh import BRepMesh_IncrementalMesh
from OCP.StlAPI import StlAPI_Writer
from OCP.BRepTools import BRepTools
from OCP.TopoDS import TopoDS_Compound
from OCP.BRep import BRep_Builder
from OCP.TopExp import TopExp_Explorer
from OCP.TopAbs import TopAbs_SOLID
from OCP.gp import gp_Trsf, gp_Ax1, gp_Pnt, gp_Dir, gp_Vec
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

import json
import math
from build_and_verify_accessories_v26 import (
    HERE, STL_DIR, STEP_DIR, IMG_DIR, WORK, SENSOR_DIR,
    load_brep_list, load_step, export_stl_file, box, cyl_z, rounded_box_xy, intersect_all, cut_all, make_loft_along_y,
    build_p20_inlet, build_p21_mid, build_p22_lower_plenum,
    build_p23_probe_mount, build_p24_ebb42_mount, build_accessory_hardware,
    build_sensor_cable, build_toolhead_fan_variants
)


def shape_to_polydata(shape, tmp_stl):
    BRepMesh_IncrementalMesh(shape, 0.06, False, 0.15, True)
    writer = StlAPI_Writer()
    writer.ASCIIMode = False
    writer.Write(shape, str(tmp_stl))
    reader = vtk.vtkSTLReader()
    reader.SetFileName(str(tmp_stl))
    reader.Update()
    normals = vtk.vtkPolyDataNormals()
    normals.SetInputData(reader.GetOutput())
    normals.SetFeatureAngle(35.0)
    normals.SplittingOn()
    normals.Update()
    return normals.GetOutput()


def make_actor(polydata, color_rgb, opacity=1.0, specular=0.25, edge_vis=False):
    mapper = vtk.vtkPolyDataMapper()
    mapper.SetInputData(polydata)
    actor = vtk.vtkActor()
    actor.SetMapper(mapper)
    prop = actor.GetProperty()
    prop.SetColor(*color_rgb)
    prop.SetOpacity(opacity)
    prop.SetSpecular(specular)
    prop.SetSpecularPower(25.0)
    prop.SetAmbient(0.22)
    prop.SetDiffuse(0.78)
    prop.EdgeVisibilityOff()
    if edge_vis:
        feat = vtk.vtkFeatureEdges()
        feat.SetInputData(polydata)
        feat.BoundaryEdgesOn()
        feat.FeatureEdgesOn()
        feat.ManifoldEdgesOff()
        feat.NonManifoldEdgesOff()
        feat.SetFeatureAngle(28.0)
        feat.ColoringOff()
        feat.Update()
        em = vtk.vtkPolyDataMapper()
        em.SetInputData(feat.GetOutput())
        ea = vtk.vtkActor()
        ea.SetMapper(em)
        ep = ea.GetProperty()
        ep.SetColor(0.12, 0.14, 0.18)
        ep.SetLineWidth(1.1)
        ep.SetOpacity(opacity)
        actor._edge_actor = ea
    return actor


def render_view(actors, cam_pos, focal_pt, view_up, out_png, width=1400, height=1100, zoom=1.15, depth_peeling=False):
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.95, 0.96, 0.97)
    ren.SetBackground2(0.84, 0.86, 0.90)
    ren.GradientBackgroundOn()
    for a in actors:
        ren.AddActor(a)
        if hasattr(a, "_edge_actor"):
            ren.AddActor(a._edge_actor)

    cam = ren.GetActiveCamera()
    cam.SetPosition(*cam_pos)
    cam.SetFocalPoint(*focal_pt)
    cam.SetViewUp(*view_up)
    cam.ParallelProjectionOn()
    ren.ResetCamera()
    cur_fp = cam.GetFocalPoint()
    cur_pos = cam.GetPosition()
    dx, dy, dz = focal_pt[0] - cur_fp[0], focal_pt[1] - cur_fp[1], focal_pt[2] - cur_fp[2]
    cam.SetFocalPoint(*focal_pt)
    cam.SetPosition(cur_pos[0] + dx, cur_pos[1] + dy, cur_pos[2] + dz)
    cam.SetClippingRange(1.0, 2000.0)
    cam.Zoom(zoom)

    ren.RemoveAllLights()
    l_key = vtk.vtkLight()
    l_key.SetLightTypeToCameraLight()
    l_key.SetPosition(0.55, 0.85, 0.75)
    l_key.SetIntensity(0.88)
    ren.AddLight(l_key)

    l_fill = vtk.vtkLight()
    l_fill.SetLightTypeToCameraLight()
    l_fill.SetPosition(-0.85, -0.45, -0.30)
    l_fill.SetIntensity(0.32)
    ren.AddLight(l_fill)

    l_rim = vtk.vtkLight()
    l_rim.SetLightTypeToCameraLight()
    l_rim.SetPosition(0.0, 0.90, -0.80)
    l_rim.SetIntensity(0.22)
    ren.AddLight(l_rim)

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetSize(width, height)
    if depth_peeling:
        rw.SetAlphaBitPlanes(1)
        rw.SetMultiSamples(0)
        ren.SetUseDepthPeeling(1)
        ren.SetMaximumNumberOfPeels(20)
        ren.SetOcclusionRatio(0.02)
    else:
        rw.SetMultiSamples(8)
    rw.AddRenderer(ren)
    rw.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.Update()

    writer = vtk.vtkPNGWriter()
    writer.SetFileName(str(out_png))
    writer.SetInputConnection(w2i.GetOutputPort())
    writer.Write()


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_stl = WORK / "tmp_render.stl"

    v26_meta = json.loads((WORK / "v26_meta.json").read_text())
    v26_raw = load_brep_list(WORK / "v26_cache.brep")
    gantry_meta = json.loads((WORK / "gantry_meta.json").read_text())
    gantry_raw = load_brep_list(WORK / "gantry_cache.brep")

    p20_body, p20_air = build_p20_inlet()
    p21_body, p21_air = build_p21_mid()
    p22_body, p22_air = build_p22_lower_plenum()
    p23_body = build_p23_probe_mount()
    p24_body = build_p24_ebb42_mount()
    sensor_cable = build_sensor_cable()
    acc_hw = build_accessory_hardware()

    # Transform Beacon RevH Normal facing FORWARD (+Y toward nozzle: rot_z = 0, Y_coil = +3.20, Z_seat = -75.00):
    beacon_sols = load_step(SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")
    trsf_beacon = gp_Trsf()
    trsf_beacon.SetTranslation(gp_Vec(0.0, 3.20, -75.000))
    beacon_world = [BRepBuilderAPI_Transform(s, trsf_beacon, True).Shape() for s in beacon_sols]
    beacon_bot_ko = beacon_world[0]
    beacon_top_ko = intersect_all(beacon_world[1], [box(-20.0, 20.0, -20.0, 20.0, -76.61, -56.61)])
    beacon_phys   = beacon_world[2:5]

    # Transform BTT EBB42 CAN V1.2 rotated so 4-pin MicroFit & USB-C face UP (+Z) and flipped so pins face FORWARD (+Y toward extruder motor):
    ebb_raw = load_brep_list(WORK / "ebb42_cache.brep")
    t_center = gp_Trsf()
    t_center.SetTranslation(gp_Vec(-20.0, -20.0, 0.0))
    t_ry180 = gp_Trsf()
    t_ry180.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(0, 1, 0)), math.pi)
    t_rx90 = gp_Trsf()
    t_rx90.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), math.pi / 2.0)
    t_pos_ebb = gp_Trsf()
    t_pos_ebb.SetTranslation(gp_Vec(-1.248, -31.630, 6.500))
    trsf_ebb = t_pos_ebb.Multiplied(t_rx90.Multiplied(t_ry180.Multiplied(t_center)))
    ebb_world = [BRepBuilderAPI_Transform(s, trsf_ebb, True).Shape() for s, _ in ebb_raw]

    v26_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(v26_meta, v26_raw)}
    th_vars = build_toolhead_fan_variants(v26_by_name)

    # Build VTK actors for core v26 parts (with 3010 toolhead installed)
    v26_actors = []
    for m, (s, _) in zip(v26_meta, v26_raw):
        name = m["name"]
        if "ENVELOPE" in name and "SERVO" not in name:
            continue
        if name in ("PRINT_RedLizard_HF_tool_carrier", "PRINT_Tool_docking_backplate"):
            continue
        pd = shape_to_polydata(s, tmp_stl)
        if name == "PRINT_motor_mount":
            col, op = (0.20, 0.45, 0.78), 1.0 # P01 Blue
        elif name == "PRINT_REAR_MOTOR_SERVO_SPACER":
            col, op = (0.58, 0.35, 0.72), 1.0 # P02 Purple
        elif name == "PRINT_000_outer_shell_of_extruder_1":
            col, op = (0.88, 0.72, 0.18), 1.0 # P03 Yellow
        elif name in ("PRINT_carrier_box_left", "PRINT_arm_front_half"):
            col, op = (0.85, 0.25, 0.25), 1.0 # P04 Red
        elif "HOBBY_SERVO_ENVELOPE" in name:
            col, op = (0.25, 0.55, 0.85), 1.0
        elif "HF_04" in name or "HF_05" in name:
            col, op = (0.85, 0.55, 0.20), 1.0 # Copper/Brass Heater & Nozzle
        elif "MONO_CART_MGN12H" in name:
            col, op = (0.35, 0.40, 0.45), 1.0
        elif "AHG" in name:
            col, op = (0.28, 0.30, 0.34), 1.0
        elif m["is_print"]:
            col, op = (0.70, 0.72, 0.75), 1.0
        else:
            col, op = (0.62, 0.65, 0.68), 1.0
        v26_actors.append(make_actor(pd, col, op))

    v26_actors.append(make_actor(shape_to_polydata(th_vars["P17_HF_tool_carrier_3010"], tmp_stl), (0.92, 0.52, 0.16), 1.0))
    v26_actors.append(make_actor(shape_to_polydata(th_vars["P18_Tool_docking_backplate_3010"], tmp_stl), (0.22, 0.68, 0.42), 1.0))
    v26_actors.append(make_actor(shape_to_polydata(th_vars["Fan_3010_Axial"], tmp_stl), (0.14, 0.16, 0.20), 1.0))
    for sc in th_vars["Fan_3010_Screws"]:
        v26_actors.append(make_actor(shape_to_polydata(sc, tmp_stl), (0.82, 0.80, 0.75), 1.0))

    # Build VTK actors for key Monolith Gantry keepouts (X-beam Body12, Rail Body13, Belts Body1/2, X-edge XY joints Body4..9, Pole Body40)
    # Clip tall vertical gantry keepouts to Z in [-85, +32] so camera ResetCamera() frames the toolhead tightly.
    gantry_clip_box = box(-150.0, 150.0, -150.0, 150.0, -85.0, 32.0)
    gantry_actors = []
    gantry_show_names = {
        "GANTRY_Body12", "GANTRY_Body13", "GANTRY_Body1", "GANTRY_Body2",
        "GANTRY_Body4", "GANTRY_Body5", "GANTRY_Body6", "GANTRY_Body7",
        "GANTRY_Body8", "GANTRY_Body9", "GANTRY_Body40"
    }
    for m, (s, _) in zip(gantry_meta, gantry_raw):
        if m["name"] in gantry_show_names:
            s_clipped = intersect_all(s, [gantry_clip_box])
            pd = shape_to_polydata(s_clipped, tmp_stl)
            if m["name"] == "GANTRY_Body40":
                col, op = (0.75, 0.30, 0.30), 0.30
            elif m["name"] in ("GANTRY_Body4", "GANTRY_Body5", "GANTRY_Body6", "GANTRY_Body7", "GANTRY_Body8", "GANTRY_Body9"):
                col, op = (0.55, 0.42, 0.28), 0.26
            elif m["name"] in ("GANTRY_Body1", "GANTRY_Body2"):
                col, op = (0.35, 0.38, 0.42), 0.28
            else:
                col, op = (0.45, 0.48, 0.52), 0.48
            gantry_actors.append(make_actor(pd, col, op))

    # Build VTK actors for the 5 new accessory parts (P20..P24) + sensor cable
    act_p20 = make_actor(shape_to_polydata(p20_body, tmp_stl), (0.14, 0.72, 0.64), 1.0, edge_vis=False) # Teal Upper Inlet
    act_p21 = make_actor(shape_to_polydata(p21_body, tmp_stl), (0.90, 0.36, 0.26), 1.0, edge_vis=False) # Coral Mid Gantry Bridge
    act_p22 = make_actor(shape_to_polydata(p22_body, tmp_stl), (0.16, 0.76, 0.52), 1.0, edge_vis=False) # Emerald/Teal Lower Plenum
    act_p23 = make_actor(shape_to_polydata(p23_body, tmp_stl), (0.20, 0.52, 0.92), 1.0, edge_vis=False) # Blue Beacon/Carto Mount
    act_p24 = make_actor(shape_to_polydata(p24_body, tmp_stl), (0.94, 0.56, 0.14), 1.0, edge_vis=False) # Amber EBB42 Mount
    act_cable = make_actor(shape_to_polydata(sensor_cable, tmp_stl), (0.95, 0.22, 0.58), 1.0, edge_vis=False) # Magenta Sensor Wire

    # Deep-shadow interior liner inside the crescent sub-sock nozzle hoods so the outlet slot reads cleanly:
    ring_liner = cut_all(
        rounded_box_xy(-12.20, 12.20, 14.80, 33.80, -76.95, -75.80, 1.2),
        [rounded_box_xy(-10.85, 10.85, 10.00, 42.00, -78.50, -74.50, 3.8)],
    )
    act_ring_liner = make_actor(shape_to_polydata(ring_liner, tmp_stl), (0.02, 0.16, 0.12), 1.0, specular=0.03)

    # Translucent blue Volcano Silicone Sock (X in [-7.00, 7.00], Y in [12.95, 38.45], Z in [-74.35, -59.50]):
    silicone_sock_shape = cut_all(
        rounded_box_xy(-7.00, 7.00, 12.95, 38.45, -74.35, -59.50, 1.2),
        [box(-5.80, 5.80, 13.95, 37.25, -73.40, -59.00), cyl_z(0.0, 22.70, -76.00, -72.00, 3.80)],
    )
    v26_actors.append(make_actor(shape_to_polydata(silicone_sock_shape, tmp_stl), (0.15, 0.55, 0.92), 0.42))

    acc_actors = [act_p20, act_p21, act_p22, act_ring_liner, act_p23, act_p24, act_cable]
    for _, hs in acc_hw:
        acc_actors.append(make_actor(shape_to_polydata(hs, tmp_stl), (0.78, 0.76, 0.70), 1.0))

    # Beacon actors + translucent keepout cones
    beacon_actors = [make_actor(shape_to_polydata(bs, tmp_stl), (0.12, 0.15, 0.18), 1.0) for bs in beacon_phys]
    act_top_ko = make_actor(shape_to_polydata(beacon_top_ko, tmp_stl), (0.10, 0.85, 0.95), 0.32)
    act_bot_ko = make_actor(shape_to_polydata(beacon_bot_ko, tmp_stl), (0.95, 0.80, 0.10), 0.32)

    # EBB42 actors
    ebb_actors = []
    for idx_e, es in enumerate(ebb_world):
        col = (0.12, 0.14, 0.18) if idx_e == 0 else (0.82, 0.82, 0.85)
        ebb_actors.append(make_actor(shape_to_polydata(es, tmp_stl), col, 1.0))

    # Fluid air actors
    air_actors = [
        make_actor(shape_to_polydata(s, tmp_stl), (0.15, 0.70, 0.98), 0.88)
        for s in (p20_air, p21_air, p22_air)
    ]

    # Render 1: Rear-Right Iso (Full Assembly + Gantry + CPAP + EBB42 + Beacon)
    render_view(
        v26_actors + gantry_actors + acc_actors + beacon_actors + ebb_actors,
        cam_pos=(-180, -210, 40), focal_pt=(0, -15, -20), view_up=(0, 0, 1),
        out_png=IMG_DIR / "01_rear_right_iso_complete.png", zoom=1.20, depth_peeling=True
    )

    # Render 2: Rear-Left Iso (Showing CPAP behind Monolith Gantry, EBB42 behind motor, and Servo)
    render_view(
        v26_actors + gantry_actors + acc_actors + beacon_actors + ebb_actors,
        cam_pos=(180, -210, 40), focal_pt=(0, -15, -20), view_up=(0, 0, 1),
        out_png=IMG_DIR / "02_rear_left_iso_complete.png", zoom=1.20, depth_peeling=True
    )

    # Render 3: Side Profile (-X Right View) showing Monolith X-Beam, CPAP corridor, EBB42, and Beacon Keepout Cone
    render_view(
        v26_actors + gantry_actors + acc_actors + beacon_actors + [act_top_ko, act_bot_ko] + ebb_actors,
        cam_pos=(-260, -10, -20), focal_pt=(0, -10, -20), view_up=(0, 0, 1),
        out_png=IMG_DIR / "03_right_side_gantry_and_keepout.png", zoom=1.25, depth_peeling=True
    )

    # Render 4: Lower Beacon/Cartographer + CPAP Dual Nozzle Jets Close-up (Bottom-Front-Right Iso)
    render_view(
        v26_actors + acc_actors + beacon_actors + [act_top_ko, act_bot_ko],
        cam_pos=(-130, 140, -115), focal_pt=(0, 8, -68), view_up=(0, 0, 1),
        out_png=IMG_DIR / "04_lower_beacon_and_nozzle_jets.png", zoom=2.10, depth_peeling=True
    )

    # Render 5: Internal CPAP Airflow Volume + Beacon Keepout + Monolith Gantry (Ghost Shell View)
    ghost_shells = [
        make_actor(shape_to_polydata(p20_body, tmp_stl), (0.18, 0.72, 0.48), 0.22),
        make_actor(shape_to_polydata(p21_body, tmp_stl), (0.86, 0.26, 0.22), 0.22),
        make_actor(shape_to_polydata(p22_body, tmp_stl), (0.20, 0.76, 0.42), 0.22),
        act_p23, act_p24, act_top_ko, act_bot_ko
    ]
    render_view(
        gantry_actors + ghost_shells + air_actors + beacon_actors + ebb_actors,
        cam_pos=(-170, -190, -10), focal_pt=(0, -20, -25), view_up=(0, 0, 1),
        out_png=IMG_DIR / "05_cpap_internal_air_and_keepout.png", zoom=1.25, depth_peeling=True
    )

    # Render 6: Accessories-Only Isolated View (P20..P24 + Beacon + EBB42 + Hardware)
    render_view(
        acc_actors + beacon_actors + [act_top_ko] + ebb_actors,
        cam_pos=(-160, -180, 25), focal_pt=(0, -15, -20), view_up=(0, 0, 1),
        out_png=IMG_DIR / "06_accessories_isolated_iso.png", zoom=1.25, depth_peeling=True
    )

    # Render 7: Front-3/4 Isolated CPAP Inlet vs. Dual Wide-Open Nozzle Outlets Comparison
    render_view(
        acc_actors + beacon_actors + ebb_actors,
        cam_pos=(-125, 200, 15), focal_pt=(0, -5, -30), view_up=(0, 0, 1),
        out_png=IMG_DIR / "07_cpap_inlet_vs_outlets_front_iso.png", zoom=1.28, depth_peeling=True
    )

    # Render 10: Bottom-Up Close-up of Widened Nozzle Clearance & Sealed Underside Behind Nozzle
    render_view(
        v26_actors + acc_actors + beacon_actors,
        cam_pos=(18, 5, -165), focal_pt=(0, 18, -74), view_up=(0, 1, 0),
        out_png=IMG_DIR / "10_nozzle_clearance_and_sealed_underside.png", zoom=2.35, depth_peeling=True
    )

    # Render 11: Top-Down Bore View into P20 CPAP Hose Inlet & Upper EBB42 Co-Bolted Wings (matching user screenshot angle)
    act_p20_edge = make_actor(shape_to_polydata(p20_body, tmp_stl), (0.14, 0.72, 0.64), 1.0, edge_vis=True)
    act_p21_edge = make_actor(shape_to_polydata(p21_body, tmp_stl), (0.90, 0.36, 0.26), 1.0, edge_vis=True)
    act_p24_edge = make_actor(shape_to_polydata(p24_body, tmp_stl), (0.94, 0.56, 0.14), 1.0, edge_vis=True)
    hw_actors = [make_actor(shape_to_polydata(hs, tmp_stl), (0.78, 0.76, 0.70), 1.0, edge_vis=True) for _, hs in acc_hw]
    render_view(
        v26_actors + [act_p20_edge, act_p21_edge, act_p24_edge, act_cable] + hw_actors + ebb_actors,
        cam_pos=(0.0, -72.0, 95.0), focal_pt=(0.0, -37.0, 5.0), view_up=(0, 1, 0),
        out_png=IMG_DIR / "11_p20_bore_smooth_fairing_and_ebb42_mount.png", zoom=2.85, depth_peeling=True
    )

    # Render 12: Rear-Left Close-up of P20 Multi-Barb Trianglelab 7040 Spigot & Smooth Upper Wing Transition (matching user screenshot)
    render_view(
        v26_actors + [act_p20_edge, act_p21_edge, act_p24_edge, act_cable] + hw_actors + ebb_actors,
        cam_pos=(48.0, -82.0, 5.0), focal_pt=(6.0, -38.0, 15.0), view_up=(0, 0, 1),
        out_png=IMG_DIR / "12_p20_multibarb_and_wing_closeup.png", zoom=2.35, depth_peeling=True
    )

    # Render 13: Toolhead 2510 (Left) vs 3010 (Right) Side-by-Side Comparison (Front-Right & Rear-Left Iso)
    tool_hotend_names = [
        "HF_00_K1_heatsink", "HF_01_K1_heatbreak_subassembly", "HF_02_K1_heatbreak_subassembly_1",
        "HF_03_K1_heatbreak_subassembly_2", "HF_04_Creality_Ender_3_Volcano_Hotend_v14",
        "HF_05_HF03_NOMINAL_VOLCANO_NOZZLE_NOT_VENDOR_CAD", "HF_06_HF04_HEATER_6x20_NOMINAL_REFERENCE",
        "HF_07_HF05_THERMISTOR_3x15_NOMINAL_REFERENCE",
        "M2_5x8_HF_mount_0", "M2_5x8_HF_mount_1", "M2_5x8_HF_mount_2", "M2_5x8_HF_mount_3",
        "OCT_TOOL_05_4mm_ball:1", "OCT_TOOL_11_4mm_ball:2", "OCT_TOOL_12_4mm_ball:3", "OCT_TOOL_13_4mm_ball:4",
        "OCT_TOOL_14_magnet_5-15-3:1", "OCT_TOOL_15_magnet_5-15-3:2", "OCT_TOOL_16_magnet_5-15-3:3", "OCT_TOOL_17_magnet_5-15-3:4",
        "OCT_TOOL_10_M3_6:1", "OCT_TOOL_23_M3_6:2", "OCT_TOOL_24_M3_6:3", "OCT_TOOL_25_M3_6:4",
    ]
    def make_shifted_actors(dx, p17_s, p18_s, fan_s, fan_sc_list, p17_col):
        t_sh = gp_Trsf()
        t_sh.SetTranslation(gp_Vec(dx, 0.0, 0.0))
        acts = [
            make_actor(shape_to_polydata(BRepBuilderAPI_Transform(p17_s, t_sh, True).Shape(), tmp_stl), p17_col, 1.0, edge_vis=True),
            make_actor(shape_to_polydata(BRepBuilderAPI_Transform(p18_s, t_sh, True).Shape(), tmp_stl), (0.22, 0.68, 0.42), 1.0, edge_vis=True),
            make_actor(shape_to_polydata(BRepBuilderAPI_Transform(fan_s, t_sh, True).Shape(), tmp_stl), (0.14, 0.16, 0.20), 1.0, edge_vis=True),
            make_actor(shape_to_polydata(BRepBuilderAPI_Transform(silicone_sock_shape, t_sh, True).Shape(), tmp_stl), (0.15, 0.55, 0.92), 0.75),
        ]
        for sc in fan_sc_list:
            acts.append(make_actor(shape_to_polydata(BRepBuilderAPI_Transform(sc, t_sh, True).Shape(), tmp_stl), (0.82, 0.80, 0.75), 1.0))
        for hn in tool_hotend_names:
            hs = BRepBuilderAPI_Transform(v26_by_name[hn][0], t_sh, True).Shape()
            col = (0.82, 0.22, 0.20) if "HF_00" in hn else ((0.85, 0.68, 0.22) if "HF_05" in hn else (0.72, 0.74, 0.78))
            acts.append(make_actor(shape_to_polydata(hs, tmp_stl), col, 1.0))
        return acts

    # Render 13: 3010 Toolhead Front-3/4 Complete Assembly (Left) vs. Bare Shroud / Air Nozzle / Wire Channels (Right)
    comp_3010_left = make_shifted_actors(-22.0, th_vars["P17_HF_tool_carrier_3010"], th_vars["P18_Tool_docking_backplate_3010"], th_vars["Fan_3010_Axial"], th_vars["Fan_3010_Screws"], (0.92, 0.52, 0.16))
    t_sh_r = gp_Trsf()
    t_sh_r.SetTranslation(gp_Vec(22.0, 0.0, 0.0))
    bare_3010_acts = [
        make_actor(shape_to_polydata(BRepBuilderAPI_Transform(th_vars["P17_HF_tool_carrier_3010"], t_sh_r, True).Shape(), tmp_stl), (0.92, 0.52, 0.16), 1.0, edge_vis=True),
        make_actor(shape_to_polydata(BRepBuilderAPI_Transform(th_vars["P18_Tool_docking_backplate_3010"], t_sh_r, True).Shape(), tmp_stl), (0.22, 0.68, 0.42), 0.35, edge_vis=False),
        make_actor(shape_to_polydata(BRepBuilderAPI_Transform(v26_by_name["HF_00_K1_heatsink"][0], t_sh_r, True).Shape(), tmp_stl), (0.82, 0.22, 0.20), 1.0, edge_vis=True),
        make_actor(shape_to_polydata(BRepBuilderAPI_Transform(v26_by_name["HF_04_Creality_Ender_3_Volcano_Hotend_v14"][0], t_sh_r, True).Shape(), tmp_stl), (0.72, 0.74, 0.78), 1.0),
        make_actor(shape_to_polydata(BRepBuilderAPI_Transform(v26_by_name["HF_05_HF03_NOMINAL_VOLCANO_NOZZLE_NOT_VENDOR_CAD"][0], t_sh_r, True).Shape(), tmp_stl), (0.85, 0.68, 0.22), 1.0),
        make_actor(shape_to_polydata(BRepBuilderAPI_Transform(silicone_sock_shape, t_sh_r, True).Shape(), tmp_stl), (0.15, 0.55, 0.92), 0.75),
    ]
    render_view(
        comp_3010_left + bare_3010_acts,
        cam_pos=(-45.0, 155.0, -5.0), focal_pt=(0.0, 26.0, -20.0), view_up=(0, 0, 1),
        out_png=IMG_DIR / "13_toolhead_2510_and_3010_comparison.png", zoom=1.35, depth_peeling=True
    )

    # Render 14: Voron 350 10-Toolhead Array (All 10 Toolheads with 3010 Axial Fans at 37.30 mm pitch, T0..T9)
    ten_tool_actors = []
    # Carriage non-tool actors at X=0 (station 4):
    for m, (s, _) in zip(v26_meta, v26_raw):
        if m["is_ref"]:
            continue
        if m["idx"] in range(87, 120):
            continue
        poly = shape_to_polydata(s, tmp_stl)
        col = (0.38, 0.56, 0.80) if m["is_print"] else (0.72, 0.74, 0.78)
        ten_tool_actors.append(make_actor(poly, col, 1.0))
    ten_tool_actors.extend(acc_actors + beacon_actors + ebb_actors)

    for st_idx in range(10):
        dx = (st_idx - 4) * 37.30
        p17_col = (0.96, 0.58, 0.14) if st_idx == 4 else (0.88, 0.48, 0.16)
        ten_tool_actors.extend(make_shifted_actors(
            dx, th_vars["P17_HF_tool_carrier_3010"], th_vars["P18_Tool_docking_backplate_3010"],
            th_vars["Fan_3010_Axial"], th_vars["Fan_3010_Screws"], p17_col
        ))
    render_view(
        ten_tool_actors,
        cam_pos=(18.65, 520.0, 15.0), focal_pt=(18.65, 20.0, -15.0), view_up=(0, 0, 1),
        out_png=IMG_DIR / "14_voron350_10_toolheads_pitch_37p3mm.png", zoom=1.42, depth_peeling=True
    )

    # Render 15: Rear-3/4 & Side-3/4 View of 3010 Toolhead Showing Lateral Side Exhaust Windows, Rear V-Splitter, and Partitioned Wire Tunnels
    render_view(
        comp_3010_left + bare_3010_acts,
        cam_pos=(65.0, -125.0, -15.0), focal_pt=(0.0, 24.0, -28.0), view_up=(0, 0, 1),
        out_png=IMG_DIR / "15_toolhead_rear_vent_and_wire_channels.png", zoom=1.45, depth_peeling=True
    )

    # Render 16: Front-Right Close-up on Carriage (matching user screenshot angle) Showing Wide-Open Lateral Side Exhaust Windows
    carr_only_actors = []
    for m, (s, _) in zip(v26_meta, v26_raw):
        if m["is_ref"] or m["idx"] in range(87, 120):
            continue
        poly = shape_to_polydata(s, tmp_stl)
        col = (0.24, 0.38, 0.68) if "motor_mount" in m["name"] else ((0.85, 0.56, 0.22) if m["is_print"] else (0.72, 0.74, 0.78))
        carr_only_actors.append(make_actor(poly, col, 1.0, edge_vis=True))
    carr_only_actors.extend(acc_actors + beacon_actors + ebb_actors)
    carr_only_actors.extend(make_shifted_actors(
        0.0, th_vars["P17_HF_tool_carrier_3010"], th_vars["P18_Tool_docking_backplate_3010"],
        th_vars["Fan_3010_Axial"], th_vars["Fan_3010_Screws"], (0.22, 0.24, 0.28)
    ))
    render_view(
        carr_only_actors,
        cam_pos=(-95.0, 88.0, -32.0), focal_pt=(-2.0, 20.0, -42.0), view_up=(0, 0, 1),
        out_png=IMG_DIR / "16_toolhead_side_exhaust_on_carriage.png", zoom=1.85, depth_peeling=True
    )

    render_full_exploded_views(
        v26_meta, v26_raw, gantry_meta, gantry_raw,
        p20_body, p21_body, p22_body, p23_body, p24_body,
        sensor_cable, acc_hw, beacon_phys, ebb_world,
        th_vars, silicone_sock_shape, tmp_stl
    )

    print("Rendered VTK views in", IMG_DIR)


def set_actor_pos(actor, dx, dy, dz):
    actor.SetPosition(dx, dy, dz)
    if hasattr(actor, "_edge_actor"):
        actor._edge_actor.SetPosition(dx, dy, dz)


def build_exploded_groups(
    v26_meta, v26_raw, gantry_meta, gantry_raw,
    p20_body, p21_body, p22_body, p23_body, p24_body,
    sensor_cable, acc_hw, beacon_phys, ebb_world,
    th_vars, silicone_sock_shape, tmp_stl
):
    """
    Build all actors for the complete SparkShift v26j + Monolith 2WD 9mm Gantry +
    P20..P24 Accessories + EBB42 + Beacon + 3010 Toolhead system, returning a list
    of (actor, (dx, dy, dz)) tuples for exploded-view interpolation t in [0, 1].
    """
    items = []

    # 1. Detailed Monolith 2WD 9mm Gantry (2020 X-Beam, MGN12 Rail, 9mm GT2 Belt Loops, and Left/Right XY-Joint Assemblies)
    mono_sols = load_step(STEP_DIR / "Monolith_2WD_9mm_X_Axis_and_Belts.step")
    beam_clip = box(-88.0, 88.0, -60.0, 30.0, -70.0, 10.0)
    rail_clip = box(-82.0, 82.0, -60.0, 30.0, -70.0, 10.0)
    for g_idx, gs in enumerate(mono_sols):
        if g_idx == 0:
            # 2020 Carbon/Alu X-Beam (stationary datum)
            s_b = intersect_all(gs, [beam_clip])
            items.append((make_actor(shape_to_polydata(s_b, tmp_stl), (0.26, 0.30, 0.36), 1.0, edge_vis=True), (0.0, 0.0, 0.0)))
        elif g_idx == 1:
            # MGN12 Linear Rail on front face of X-Beam
            s_r = intersect_all(gs, [rail_clip])
            items.append((make_actor(shape_to_polydata(s_r, tmp_stl), (0.74, 0.78, 0.84), 1.0, edge_vis=True), (0.0, 10.0, 0.0)))
        elif g_idx in (2, 3):
            # Upper (g_idx=2) and Lower (g_idx=3) 9mm GT2 Belt Loops
            dz_b = 14.0 if g_idx == 2 else -14.0
            items.append((make_actor(shape_to_polydata(gs, tmp_stl), (0.20, 0.22, 0.26), 0.85, edge_vis=True), (0.0, 0.0, dz_b)))
        elif 4 <= g_idx <= 33:
            # Right (-X) Monolith 2WD 9mm XY-Joint Assembly (shifted inward by +66mm to sit at X=-88mm beam end, explodes outward -28mm in X)
            tr_in = gp_Trsf()
            tr_in.SetTranslation(gp_Vec(66.0, 0.0, 0.0))
            gs_in = BRepBuilderAPI_Transform(gs, tr_in, True).Shape()
            is_housing = g_idx in (21, 22)
            col = (0.78, 0.56, 0.26) if is_housing else (0.74, 0.76, 0.80)
            dz_j = 10.0 if g_idx == 21 else (-10.0 if g_idx == 22 else 0.0)
            items.append((make_actor(shape_to_polydata(gs_in, tmp_stl), col, 1.0, edge_vis=is_housing), (-28.0, 0.0, dz_j)))
        elif 34 <= g_idx <= 63:
            # Left (+X) Monolith 2WD 9mm XY-Joint Assembly (shifted inward by -66mm to sit at X=+88mm beam end, explodes outward +28mm in X)
            tr_in = gp_Trsf()
            tr_in.SetTranslation(gp_Vec(-66.0, 0.0, 0.0))
            gs_in = BRepBuilderAPI_Transform(gs, tr_in, True).Shape()
            is_housing = g_idx in (34, 35)
            col = (0.78, 0.56, 0.26) if is_housing else (0.74, 0.76, 0.80)
            dz_j = 10.0 if g_idx == 34 else (-10.0 if g_idx == 35 else 0.0)
            items.append((make_actor(shape_to_polydata(gs_in, tmp_stl), col, 1.0, edge_vis=is_housing), (28.0, 0.0, dz_j)))

    # 2. Core v26j Carriage, Belt Clamps, HGX Drive, Swing Arm, Receiver Case, Motor & Servo
    for m, (s, _) in zip(v26_meta, v26_raw):
        idx = m["idx"]
        name = m["name"]
        if "ENVELOPE" in name and "SERVO" not in name:
            continue
        if name in ("PRINT_RedLizard_HF_tool_carrier", "TOOL_06_Tool_head_back_part_1", "PRINT_Tool_docking_backplate"):
            continue
        pd = shape_to_polydata(s, tmp_stl)

        if idx == 17:
            # MONO_CART_MGN12H linear block
            items.append((make_actor(pd, (0.45, 0.50, 0.56), 1.0, edge_vis=True), (0.0, 20.0, 0.0)))
        elif idx in (34, 35, 36, 37):
            # MGN12H M3x10 mount screws
            items.append((make_actor(pd, (0.78, 0.78, 0.82), 1.0), (0.0, 32.0, 0.0)))
        elif idx in (18, 19, 20, 21, 26, 28, 30, 32):
            # Left (+X) belt liner P13, belt arch P15, belt teeth & draw bolts/nuts
            col = (0.38, 0.62, 0.76) if m["is_print"] else ((0.22, 0.24, 0.28) if idx in (30, 32) else (0.78, 0.78, 0.82))
            items.append((make_actor(pd, col, 1.0, edge_vis=m["is_print"]), (34.0, 34.0, 0.0)))
        elif idx in (22, 23, 24, 25, 27, 29, 31, 33):
            # Right (-X) belt liner P14, belt arch P16, belt teeth & draw bolts/nuts
            col = (0.38, 0.62, 0.76) if m["is_print"] else ((0.22, 0.24, 0.28) if idx in (31, 33) else (0.78, 0.78, 0.82))
            items.append((make_actor(pd, col, 1.0, edge_vis=m["is_print"]), (-34.0, 34.0, 0.0)))
        elif idx in (54, 3, 45, 57, 130, 131):
            # P01 Core Extruder Frame + rear cam bearing + hall sensor
            col = (0.20, 0.45, 0.78) if idx == 54 else (0.75, 0.76, 0.80)
            items.append((make_actor(pd, col, 1.0, edge_vis=(idx == 54)), (0.0, 44.0, 0.0)))
        elif idx in (58, 59, 60, 61, 62, 63, 64, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85):
            # HGX Gear Train (P06..P09) + Direct Servo Cam (P05)
            col = (0.30, 0.78, 0.48) if m["is_print"] else (0.74, 0.76, 0.80)
            items.append((make_actor(pd, col, 1.0, edge_vis=m["is_print"]), (0.0, 72.0, 0.0)))
        elif idx in (46, 47, 48, 49, 65, 66, 67, 68, 69, 70, 71, 72, 73, 86, 132):
            # Split Swing Arm (P04R/P04F) + Spring Cup (P12) + Follower
            col = (0.86, 0.26, 0.26) if m["is_print"] else (0.76, 0.78, 0.82)
            items.append((make_actor(pd, col, 1.0, edge_vis=m["is_print"]), (0.0, 96.0, 0.0)))
        elif idx in (53, 0, 1, 2, 4, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 39, 41, 43):
            # P03 Triple-Bridged Front Receiver Case + Maxwell pins/magnets
            col = (0.88, 0.72, 0.18) if idx == 53 else (0.76, 0.78, 0.82)
            items.append((make_actor(pd, col, 1.0, edge_vis=(idx == 53)), (0.0, 122.0, 0.0)))
        elif idx in (38, 40, 42, 44):
            # 4 Long Case Clamp Bolts in front of P03
            items.append((make_actor(pd, (0.82, 0.82, 0.86), 1.0), (0.0, 142.0, 0.0)))
        elif idx in (50, 51, 52):
            # P02 Rear Motor/Servo Spacer Plate
            col = (0.58, 0.35, 0.72) if idx == 50 else (0.78, 0.78, 0.82)
            items.append((make_actor(pd, col, 1.0, edge_vis=(idx == 50)), (0.0, -14.0, 22.0)))
        elif idx in (5, 55, 56, 121, 122, 123, 124, 125, 126, 127, 128, 129, 133, 134):
            # NEMA14 Pancake Stepper + MG90S Servo Envelope
            if idx == 5:
                col = (0.25, 0.55, 0.85)
            elif idx in (121, 123):
                col = (0.68, 0.70, 0.74)
            elif idx == 122:
                col = (0.24, 0.26, 0.30)
            else:
                col = (0.78, 0.72, 0.45)
            items.append((make_actor(pd, col, 1.0, edge_vis=(idx in (5, 121, 122, 123))), (0.0, -34.0, 32.0)))
        elif idx in (87, 103, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118, 119):
            # Toolhead kinematic balls, magnets & M3x6 screws (grouped with P18_3010)
            items.append((make_actor(pd, (0.78, 0.78, 0.82), 1.0), (0.0, 162.0, 0.0)))
        elif idx in range(88, 100):
            # K1 Heatsink + Volcano Hotend + Brass Nozzle + Heater/Thermistor
            if "HF_00" in name:
                col = (0.82, 0.22, 0.20)
            elif "HF_04" in name or "HF_05" in name:
                col = (0.85, 0.58, 0.20)
            else:
                col = (0.74, 0.76, 0.80)
            items.append((make_actor(pd, col, 1.0, edge_vis=("HF_00" in name)), (0.0, 184.0, -12.0)))

    # 3. Removable 3010 High-Flow Toolhead Printed Parts, Sock & Fan
    items.append((
        make_actor(shape_to_polydata(th_vars["P18_Tool_docking_backplate_3010"], tmp_stl), (0.22, 0.68, 0.42), 1.0, edge_vis=True),
        (0.0, 162.0, 0.0)
    ))
    items.append((
        make_actor(shape_to_polydata(silicone_sock_shape, tmp_stl), (0.15, 0.55, 0.92), 0.78),
        (0.0, 184.0, -12.0)
    ))
    items.append((
        make_actor(shape_to_polydata(th_vars["P17_HF_tool_carrier_3010"], tmp_stl), (0.92, 0.52, 0.16), 1.0, edge_vis=True),
        (0.0, 206.0, 0.0)
    ))
    items.append((
        make_actor(shape_to_polydata(th_vars["Fan_3010_Axial"], tmp_stl), (0.16, 0.18, 0.22), 1.0, edge_vis=True),
        (0.0, 232.0, 0.0)
    ))
    for sc in th_vars["Fan_3010_Screws"]:
        items.append((make_actor(shape_to_polydata(sc, tmp_stl), (0.82, 0.80, 0.75), 1.0), (0.0, 246.0, 0.0)))

    # 4. Accessories Suite (P20..P24 + EBB42 + Beacon + Sensor Cable + Hardware)
    items.append((
        make_actor(shape_to_polydata(p24_body, tmp_stl), (0.94, 0.56, 0.14), 1.0, edge_vis=True),
        (0.0, -56.0, 44.0)
    ))
    for idx_e, es in enumerate(ebb_world):
        col = (0.14, 0.16, 0.20) if idx_e == 0 else (0.82, 0.82, 0.85)
        items.append((make_actor(shape_to_polydata(es, tmp_stl), col, 1.0), (0.0, -80.0, 48.0)))

    # Vertical CPAP Column (P20 -> P21 -> P22) aligned cleanly behind EBB42 & Gantry at Y = -112 mm
    items.append((
        make_actor(shape_to_polydata(p20_body, tmp_stl), (0.14, 0.72, 0.64), 1.0, edge_vis=True),
        (0.0, -112.0, 56.0)
    ))
    items.append((
        make_actor(shape_to_polydata(p21_body, tmp_stl), (0.90, 0.36, 0.26), 1.0, edge_vis=True),
        (0.0, -112.0, 0.0)
    ))
    items.append((
        make_actor(shape_to_polydata(sensor_cable, tmp_stl), (0.95, 0.22, 0.58), 1.0),
        (0.0, -96.0, -8.0)
    ))
    for _, hs in acc_hw:
        items.append((make_actor(shape_to_polydata(hs, tmp_stl), (0.78, 0.76, 0.70), 1.0), (0.0, -88.0, 20.0)))

    items.append((
        make_actor(shape_to_polydata(p22_body, tmp_stl), (0.16, 0.76, 0.52), 1.0, edge_vis=True),
        (0.0, -112.0, -50.0)
    ))
    items.append((
        make_actor(shape_to_polydata(p23_body, tmp_stl), (0.20, 0.52, 0.92), 1.0, edge_vis=True),
        (0.0, -18.0, -60.0)
    ))
    for bs in beacon_phys:
        items.append((make_actor(shape_to_polydata(bs, tmp_stl), (0.14, 0.17, 0.22), 1.0), (0.0, -18.0, -84.0)))

    return items


def render_exploded_sheet(items, cam_pos, focal_pt, view_up, zoom, title_text, subtitle_text, out_png, width=1920, height=1200):
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.09, 0.11, 0.14)
    ren.SetBackground2(0.14, 0.17, 0.22)
    ren.GradientBackgroundOn()
    ren.SetUseDepthPeeling(1)
    ren.SetMaximumNumberOfPeels(20)
    ren.SetOcclusionRatio(0.02)

    for act, (dx, dy, dz) in items:
        set_actor_pos(act, dx, dy, dz)
        ren.AddActor(act)
        if hasattr(act, "_edge_actor"):
            ren.AddActor(act._edge_actor)

    cam = ren.GetActiveCamera()
    cam.SetPosition(*cam_pos)
    cam.SetFocalPoint(*focal_pt)
    cam.SetViewUp(*view_up)
    cam.ParallelProjectionOn()
    ren.ResetCamera()
    cur_fp = cam.GetFocalPoint()
    cur_pos = cam.GetPosition()
    ox, oy, oz = focal_pt[0] - cur_fp[0], focal_pt[1] - cur_fp[1], focal_pt[2] - cur_fp[2]
    cam.SetFocalPoint(*focal_pt)
    cam.SetPosition(cur_pos[0] + ox, cur_pos[1] + oy, cur_pos[2] + oz)
    cam.SetClippingRange(1.0, 3000.0)
    cam.Zoom(zoom)

    ren.RemoveAllLights()
    for pos, inten in [((0.55, 0.85, 0.75), 0.90), ((-0.85, -0.45, -0.30), 0.38), ((0.0, 0.90, -0.80), 0.28)]:
        lt = vtk.vtkLight()
        lt.SetLightTypeToCameraLight()
        lt.SetPosition(*pos)
        lt.SetIntensity(inten)
        ren.AddLight(lt)

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetAlphaBitPlanes(1)
    rw.SetMultiSamples(0)
    rw.SetSize(width, height)
    rw.AddRenderer(ren)
    rw.Render()

    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGB()
    w2i.Update()
    vtk_img = w2i.GetOutput()
    from vtk.util import numpy_support
    import numpy as np
    arr = numpy_support.vtk_to_numpy(vtk_img.GetPointData().GetScalars()).reshape((height, width, 3))[::-1, :, :]
    img = Image.fromarray(arr, mode="RGB")
    draw = ImageDraw.Draw(img)

    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)
        font_sub   = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 16)
        font_card_t = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 16)
        font_card_b = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 14)
    except Exception:
        font_title = font_sub = font_card_t = font_card_b = ImageFont.load_default()

    # Top header banner
    draw.rectangle([0, 0, width, 74], fill=(16, 20, 26))
    draw.line([0, 74, width, 74], fill=(45, 55, 70), width=2)
    draw.text((28, 14), title_text, fill=(240, 244, 250), font=font_title)
    draw.text((28, 44), subtitle_text, fill=(170, 182, 198), font=font_sub)

    # Bottom 6-column architecture legend banner
    draw.rectangle([0, height - 118, width, height], fill=(16, 20, 26))
    draw.line([0, height - 118, width, height - 118], fill=(45, 55, 70), width=2)

    cards = [
        ("1. 3010 Toolhead (P17/P18)", "3010 Fan + Bellmouth + Side Vents\nK1 Heatsink + Volcano Hotend/Sock", (235, 133, 41)),
        ("2. Receiver & Arm (P03/P04)", "Triple-Bridged P03 + Case Bolts\nP04F/P04R Arm + P05 Cam + HGX", (224, 184, 46)),
        ("3. Core Frame & Belts (P01)", "P01 Core Mount + Shear Tenons\nP13-P16 Belt Clamps + MGN12H", (51, 115, 199)),
        ("4. Monolith 2WD 9mm Gantry", "2020 Carbon X-Beam + MGN12 Rail\nDual 9mm GT2 Belts + XY Keepouts", (153, 117, 77)),
        ("5. Rear Drive & EBB42 (P02/P24)", "P02 Plate + 17.4-21.8mm NEMA14\nMG90S Servo + P24 EBB42 Mount", (240, 143, 36)),
        ("6. CPAP & Probe (P20-P23)", "P20 3-Barb Inlet -> P21 Gantry Trunk\nP22 300° Plenum + P23 Beacon/Carto", (36, 184, 163)),
    ]
    margin_x = 20
    gap = 14
    card_w = (width - 2 * margin_x - (len(cards) - 1) * gap) // len(cards)
    for idx_c, (ctitle, cbody, ccol) in enumerate(cards):
        x0 = margin_x + idx_c * (card_w + gap)
        y0 = height - 104
        x1 = x0 + card_w
        y1 = height - 14
        draw.rectangle([x0, y0, x1, y1], fill=(22, 27, 35), outline=ccol, width=2)
        draw.text((x0 + 12, y0 + 8), ctitle, fill=ccol, font=font_card_t)
        draw.text((x0 + 12, y0 + 34), cbody, fill=(210, 218, 228), font=font_card_b)

    img.save(str(out_png))
    for act, _ in items:
        set_actor_pos(act, 0.0, 0.0, 0.0)


def render_full_exploded_views(
    v26_meta, v26_raw, gantry_meta, gantry_raw,
    p20_body, p21_body, p22_body, p23_body, p24_body,
    sensor_cable, acc_hw, beacon_phys, ebb_world,
    th_vars, silicone_sock_shape, tmp_stl
):
    items = build_exploded_groups(
        v26_meta, v26_raw, gantry_meta, gantry_raw,
        p20_body, p21_body, p22_body, p23_body, p24_body,
        sensor_cable, acc_hw, beacon_phys, ebb_world,
        th_vars, silicone_sock_shape, tmp_stl
    )

    # View 18: Front-Right 3/4 Full-System Exploded View (Toolhead -> P03 -> P04/HGX -> P01 -> Gantry -> P02/NEMA14/EBB42 & P20-P23 CPAP/Beacon)
    render_exploded_sheet(
        items,
        cam_pos=(-360.0, -165.0, 125.0),
        focal_pt=(0.0, 56.0, -5.0),
        view_up=(0.0, 0.0, 1.0),
        zoom=1.38,
        title_text="SparkShift v26j — Full-System Exploded Architecture with Monolith 2WD 9mm Gantry (Front-Right Isometric)",
        subtitle_text="Left-to-Right: (1) 3010 Toolhead P17/P18 <- (2) P03 Receiver & P04/P05/HGX Drive <- (3) P01 Core & P13-P16 Belt Clamps <- (4) Monolith Gantry & MGN12H -> (5) P02/NEMA14/Servo & P24/EBB42 -> (6) P20-P22 CPAP & P23 Beacon",
        out_png=IMG_DIR / "18_full_exploded_with_gantry_front_iso.png",
    )

    # View 19: Rear-Left 3/4 Full-System Exploded View (Highlighting Behind-Gantry CPAP Stack P20->P21->P22, EBB42 Mount P24, Monolith X-Beam/Belts & Probe P23)
    render_exploded_sheet(
        items,
        cam_pos=(340.0, -245.0, 115.0),
        focal_pt=(0.0, 44.0, -5.0),
        view_up=(0.0, 0.0, 1.0),
        zoom=1.38,
        title_text="SparkShift v26j — Full-System Exploded Architecture with Monolith 2WD 9mm Gantry (Rear-Left Isometric)",
        subtitle_text="Rear-to-Front: (6) P20 3-Barb Inlet, P21 Gantry Trunk, P22 300° Plenum & P23 Beacon -> (5) EBB42 & P24 Mount + NEMA14/Servo/P02 -> (4) Monolith 2WD 9mm X-Beam, Rail, Belts & XY Keepouts -> (3..1) Carriage & 3010 Toolhead",
        out_png=IMG_DIR / "19_full_exploded_with_gantry_rear_iso.png",
    )



if __name__ == "__main__":
    main()
