#!/usr/bin/env python3
"""
Generate 4 high-resolution animated GIFs for the SparkShift v26 Accessory & 3010 Toolhead Suite:
1. anim_01_full_assembly_360_turntable.gif
2. anim_02_exploded_assembly_sequence.gif
3. anim_03_toolhead_3010_docking_and_nema14_clearance.gif
4. anim_04_printable_parts_360_showcase.gif
"""

import json
import math
from pathlib import Path
from PIL import Image
import numpy as np
import vtk
from vtk.util import numpy_support
from OCP.gp import gp_Pnt, gp_Dir, gp_Vec, gp_Ax1, gp_Trsf
from OCP.BRepBuilderAPI import BRepBuilderAPI_Transform

from build_and_verify_accessories_v26 import (
    WORK, STEP_DIR, SENSOR_DIR,
    load_brep_list, load_step,
    build_p20_inlet, build_p21_mid, build_p22_lower_plenum,
    build_p23_probe_mount, build_p24_ebb42_mount,
    build_sensor_cable, build_accessory_hardware,
    build_toolhead_fan_variants,
    box, cyl_z, rounded_box_xy, cut_all, intersect_all,
)
from render_accessories_v26 import IMG_DIR, shape_to_polydata, make_actor


def make_render_window(width=960, height=680, depth_peeling=False):
    ren = vtk.vtkRenderer()
    ren.SetBackground(0.08, 0.10, 0.13)
    ren.SetBackground2(0.16, 0.19, 0.24)
    ren.GradientBackgroundOn()
    if depth_peeling:
        ren.SetUseDepthPeeling(1)
        ren.SetMaximumNumberOfPeels(16)
        ren.SetOcclusionRatio(0.05)

    rw = vtk.vtkRenderWindow()
    rw.SetOffScreenRendering(1)
    rw.SetAlphaBitPlanes(1)
    rw.SetMultiSamples(4 if not depth_peeling else 0)
    rw.SetSize(width, height)
    rw.AddRenderer(ren)

    for pos, intensity in [
        ((240, -280, 260), 0.90),
        ((-260, -220, 180), 0.65),
        ((0, 300, 120), 0.65),
        ((0, -80, -300), 0.50),
    ]:
        lt = vtk.vtkLight()
        lt.SetLightTypeToSceneLight()
        lt.SetPosition(*pos)
        lt.SetFocalPoint(0, 0, -25)
        lt.SetIntensity(intensity)
        ren.AddLight(lt)

    return rw, ren


def capture_frame(rw):
    rw.Render()
    w2i = vtk.vtkWindowToImageFilter()
    w2i.SetInput(rw)
    w2i.SetInputBufferTypeToRGB()
    w2i.ReadFrontBufferOff()
    w2i.Update()
    vtk_img = w2i.GetOutput()
    w, h, _ = vtk_img.GetDimensions()
    arr = numpy_support.vtk_to_numpy(vtk_img.GetPointData().GetScalars())
    arr = arr.reshape((h, w, 3))[::-1, :, :]
    return Image.fromarray(arr, mode="RGB")


def save_gif(frames, out_path, duration_ms=65):
    pal_frames = [
        f.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
        for f in frames
    ]
    pal_frames[0].save(
        str(out_path),
        save_all=True,
        append_images=pal_frames[1:],
        optimize=True,
        duration=duration_ms,
        loop=0,
    )
    print(f"[GIF] Saved {out_path.name} ({len(frames)} frames, {out_path.stat().st_size / 1024:.1f} KB)")


def set_actor_translation(actor, dx, dy, dz):
    actor.SetPosition(dx, dy, dz)


def main():
    IMG_DIR.mkdir(parents=True, exist_ok=True)
    tmp_stl = WORK / "_tmp_anim_render.stl"

    v26_meta = json.loads((WORK / "v26_meta.json").read_text())
    v26_raw = load_brep_list(WORK / "v26_cache.brep")
    gantry_meta = json.loads((WORK / "gantry_meta.json").read_text())
    gantry_raw = load_brep_list(WORK / "gantry_cache.brep")
    v26_by_name = {m["name"]: (s, bb, m) for m, (s, bb) in zip(v26_meta, v26_raw)}

    p20_body, _ = build_p20_inlet()
    p21_body, _ = build_p21_mid()
    p22_body, _ = build_p22_lower_plenum()
    p23_body = build_p23_probe_mount()
    p24_body = build_p24_ebb42_mount()
    sensor_cable = build_sensor_cable()
    acc_hw = build_accessory_hardware()
    th_vars = build_toolhead_fan_variants(v26_by_name)

    beacon_sols = load_step(SENSOR_DIR / "Beacon_RevH_Assm_Normal.STEP")
    trsf_beacon = gp_Trsf()
    trsf_beacon.SetTranslation(gp_Vec(0.0, 3.20, -75.000))
    beacon_world = [BRepBuilderAPI_Transform(s, trsf_beacon, True).Shape() for s in beacon_sols]
    beacon_phys = beacon_world[2:5]

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

    silicone_sock_shape = cut_all(
        rounded_box_xy(-7.00, 7.00, 12.95, 38.45, -74.35, -59.50, 1.2),
        [box(-5.80, 5.80, 13.95, 37.25, -73.40, -59.00), cyl_z(0.0, 22.70, -76.00, -72.00, 3.80)],
    )

    # Separate carriage actors vs removable toolhead hotend actors
    carr_actors = []
    tool_hotend_actors = []
    for m, (s, _) in zip(v26_meta, v26_raw):
        name = m["name"]
        if "ENVELOPE" in name and "SERVO" not in name:
            continue
        if name in ("PRINT_RedLizard_HF_tool_carrier", "PRINT_Tool_docking_backplate"):
            continue
        pd = shape_to_polydata(s, tmp_stl)
        if name == "PRINT_motor_mount":
            col = (0.20, 0.45, 0.78)
        elif name == "PRINT_REAR_MOTOR_SERVO_SPACER":
            col = (0.58, 0.35, 0.72)
        elif name == "PRINT_000_outer_shell_of_extruder_1":
            col = (0.88, 0.72, 0.18)
        elif name in ("PRINT_carrier_box_left", "PRINT_arm_front_half"):
            col = (0.85, 0.25, 0.25)
        elif "HOBBY_SERVO_ENVELOPE" in name:
            col = (0.25, 0.55, 0.85)
        elif "HF_00" in name:
            col = (0.82, 0.22, 0.20)
        elif "HF_04" in name or "HF_05" in name:
            col = (0.85, 0.55, 0.20)
        elif "MONO_CART_MGN12H" in name:
            col = (0.35, 0.40, 0.45)
        elif "AHG" in name:
            col = (0.28, 0.30, 0.34)
        elif m["is_print"]:
            col = (0.70, 0.72, 0.75)
        else:
            col = (0.62, 0.65, 0.68)

        act = make_actor(pd, col, 1.0)
        if m["idx"] in range(87, 120):
            tool_hotend_actors.append(act)
        else:
            carr_actors.append(act)

    act_sock = make_actor(shape_to_polydata(silicone_sock_shape, tmp_stl), (0.15, 0.55, 0.92), 0.75)
    tool_hotend_actors.append(act_sock)

    act_p17_3010 = make_actor(shape_to_polydata(th_vars["P17_HF_tool_carrier_3010"], tmp_stl), (0.92, 0.52, 0.16), 1.0, edge_vis=True)
    act_p18_3010 = make_actor(shape_to_polydata(th_vars["P18_Tool_docking_backplate_3010"], tmp_stl), (0.22, 0.68, 0.42), 1.0, edge_vis=True)
    act_fan_3010 = make_actor(shape_to_polydata(th_vars["Fan_3010_Axial"], tmp_stl), (0.14, 0.16, 0.20), 1.0, edge_vis=True)
    act_fan_screws = [make_actor(shape_to_polydata(sc, tmp_stl), (0.82, 0.80, 0.75), 1.0) for sc in th_vars["Fan_3010_Screws"]]

    act_p20 = make_actor(shape_to_polydata(p20_body, tmp_stl), (0.18, 0.42, 0.82), 1.0, edge_vis=True)
    act_p21 = make_actor(shape_to_polydata(p21_body, tmp_stl), (0.12, 0.68, 0.62), 1.0, edge_vis=True)
    act_p22 = make_actor(shape_to_polydata(p22_body, tmp_stl), (0.95, 0.52, 0.15), 1.0, edge_vis=True)
    act_p23 = make_actor(shape_to_polydata(p23_body, tmp_stl), (0.92, 0.78, 0.16), 1.0, edge_vis=True)
    act_p24 = make_actor(shape_to_polydata(p24_body, tmp_stl), (0.64, 0.30, 0.78), 1.0, edge_vis=True)
    act_cable = make_actor(shape_to_polydata(sensor_cable, tmp_stl), (0.95, 0.22, 0.58), 1.0)
    act_hw = [make_actor(shape_to_polydata(hs, tmp_stl), (0.78, 0.76, 0.70), 1.0) for _, hs in acc_hw]
    act_beacon = [make_actor(shape_to_polydata(bs, tmp_stl), (0.12, 0.15, 0.18), 1.0) for bs in beacon_phys]
    act_ebb = [
        make_actor(shape_to_polydata(es, tmp_stl), (0.12, 0.14, 0.18) if idx_e == 0 else (0.82, 0.82, 0.85), 1.0)
        for idx_e, es in enumerate(ebb_world)
    ]

    # -------------------------------------------------------------------------
    # ANIMATION 1: 360-Degree Turntable of Full Assembly
    # -------------------------------------------------------------------------
    rw, ren = make_render_window(960, 680)
    all_full_actors = (
        carr_actors + tool_hotend_actors +
        [act_p17_3010, act_p18_3010, act_fan_3010] + act_fan_screws +
        [act_p20, act_p21, act_p22, act_p23, act_p24, act_cable] +
        act_hw + act_beacon + act_ebb
    )
    for a in all_full_actors:
        ren.AddActor(a)

    frames_1 = []
    n_frames_1 = 36
    radius = 235.0
    focal = (0.0, -5.0, -15.0)
    for i in range(n_frames_1):
        theta = 2.0 * math.pi * i / n_frames_1
        cx = focal[0] + radius * math.cos(theta)
        cy = focal[1] + radius * math.sin(theta)
        cz = focal[2] + 38.0 + 18.0 * math.sin(theta)
        cam = ren.GetActiveCamera()
        cam.SetPosition(cx, cy, cz)
        cam.SetFocalPoint(*focal)
        cam.SetViewUp(0, 0, 1)
        ren.ResetCamera()
        cam.Zoom(1.42)
        ren.ResetCameraClippingRange()
        frames_1.append(capture_frame(rw))
    save_gif(frames_1, IMG_DIR / "anim_01_full_assembly_360_turntable.gif", duration_ms=65)

    # -------------------------------------------------------------------------
    # ANIMATION 2: Exploded Assembly Sequence (P20..P24 + EBB42 + Beacon + 3010 Toolhead)
    # -------------------------------------------------------------------------
    frames_2 = []
    n_frames_2 = 32
    for i in range(n_frames_2):
        # Smooth 0 -> 1 -> 0 cosine pulse
        t = 0.5 * (1.0 - math.cos(2.0 * math.pi * i / n_frames_2))
        set_actor_translation(act_p20, 0.0, -28.0 * t, 36.0 * t)
        set_actor_translation(act_p21, 0.0, -32.0 * t, 0.0)
        set_actor_translation(act_p22, 0.0, -18.0 * t, -26.0 * t)
        set_actor_translation(act_p23, 0.0, 0.0, -44.0 * t)
        for ab in act_beacon:
            set_actor_translation(ab, 0.0, 0.0, -60.0 * t)
        set_actor_translation(act_p24, 0.0, -22.0 * t, 18.0 * t)
        for ae in act_ebb:
            set_actor_translation(ae, 0.0, -44.0 * t, 18.0 * t)
        set_actor_translation(act_cable, 0.0, -36.0 * t, -10.0 * t)
        for ah in act_hw:
            set_actor_translation(ah, 0.0, -38.0 * t, 12.0 * t)

        # Toolhead explosion forward (+Y)
        for th_a in tool_hotend_actors:
            set_actor_translation(th_a, 0.0, 26.0 * t, 0.0)
        set_actor_translation(act_p17_3010, 0.0, 44.0 * t, 0.0)
        set_actor_translation(act_p18_3010, 0.0, 62.0 * t, 0.0)
        set_actor_translation(act_fan_3010, -28.0 * t, 44.0 * t, 0.0)
        for sc_a in act_fan_screws:
            set_actor_translation(sc_a, -42.0 * t, 44.0 * t, 0.0)

        az = -0.65 + 0.35 * math.sin(2.0 * math.pi * i / n_frames_2)
        cam = ren.GetActiveCamera()
        cam.SetPosition(250.0 * math.cos(az), -250.0 * math.sin(az) - 40.0, 40.0)
        cam.SetFocalPoint(0.0, -5.0, -18.0)
        cam.SetViewUp(0, 0, 1)
        ren.ResetCamera()
        cam.Zoom(1.22)
        ren.ResetCameraClippingRange()
        frames_2.append(capture_frame(rw))

    # Reset all actor positions back to (0,0,0)
    for a in all_full_actors:
        set_actor_translation(a, 0.0, 0.0, 0.0)
    save_gif(frames_2, IMG_DIR / "anim_02_exploded_assembly_sequence.gif", duration_ms=70)

    # -------------------------------------------------------------------------
    # ANIMATION 3: 3010 Toolhead Docking Cycle & 17.4-21.8mm NEMA14 Motor Envelope
    # -------------------------------------------------------------------------
    # Add translucent green 21.8mm max-thickness NEMA14 pancake motor envelope (Y = -28.30 to -6.50 mm)
    nema14_max_env = cyl_z(0.0, 0.0, 0.0, 21.80, 18.20)
    t_rot_nema = gp_Trsf()
    t_rot_nema.SetRotation(gp_Ax1(gp_Pnt(0, 0, 0), gp_Dir(1, 0, 0)), -math.pi / 2.0)
    t_pos_nema = gp_Trsf()
    t_pos_nema.SetTranslation(gp_Vec(0.0, -28.30, 17.65))
    nema14_world = BRepBuilderAPI_Transform(nema14_max_env, t_pos_nema.Multiplied(t_rot_nema), True).Shape()
    act_nema14_max = make_actor(shape_to_polydata(nema14_world, tmp_stl), (0.18, 0.88, 0.38), 0.38)
    ren.AddActor(act_nema14_max)

    frames_3 = []
    n_frames_3 = 30
    moving_tool_group = tool_hotend_actors + [act_p17_3010, act_p18_3010, act_fan_3010] + act_fan_screws
    for i in range(n_frames_3):
        t = 0.5 * (1.0 - math.cos(2.0 * math.pi * i / n_frames_3))
        dy_dock = 35.0 * t
        for m_act in moving_tool_group:
            set_actor_translation(m_act, 0.0, dy_dock, 0.0)
        az = 0.55 + 0.45 * math.sin(2.0 * math.pi * i / n_frames_3)
        cam = ren.GetActiveCamera()
        cam.SetPosition(-210.0 * math.cos(az), 210.0 * math.sin(az), -8.0)
        cam.SetFocalPoint(0.0, 12.0, -22.0)
        cam.SetViewUp(0, 0, 1)
        ren.ResetCamera()
        cam.Zoom(1.42)
        ren.ResetCameraClippingRange()
        frames_3.append(capture_frame(rw))

    for m_act in moving_tool_group:
        set_actor_translation(m_act, 0.0, 0.0, 0.0)
    ren.RemoveActor(act_nema14_max)
    save_gif(frames_3, IMG_DIR / "anim_03_toolhead_3010_docking_and_nema14_clearance.gif", duration_ms=70)

    # -------------------------------------------------------------------------
    # ANIMATION 4: 360-Degree Showcase of All 8 Pure-Primitive Printable Parts
    # -------------------------------------------------------------------------
    rw4, ren4 = make_render_window(960, 680)
    p17_2510 = th_vars["P17_HF_tool_carrier_2510"]
    p17_3010 = th_vars["P17_HF_tool_carrier_3010"]
    p18_3010 = th_vars["P18_Tool_docking_backplate_3010"]

    gallery_specs = [
        (p20_body, (-75.0,  0.0,  20.0), (0.18, 0.42, 0.82)), # P20 Blue
        (p21_body, (-30.0,  0.0,  38.0), (0.12, 0.68, 0.62)), # P21 Teal
        (p22_body, ( 20.0,  0.0,  62.0), (0.95, 0.52, 0.15)), # P22 Orange
        (p23_body, ( 68.0,  0.0,  72.0), (0.92, 0.78, 0.16)), # P23 Gold
        (p24_body, (-75.0,  0.0, -55.0), (0.64, 0.30, 0.78)), # P24 Purple
        (p17_3010, (-22.0, -24.0, -35.0), (0.92, 0.52, 0.16)), # P17_3010 Amber
        (p17_2510, ( 26.0, -24.0, -35.0), (0.20, 0.62, 0.86)), # P17_2510 Cyan
        (p18_3010, ( 68.0, -40.0, -45.0), (0.22, 0.68, 0.42)), # P18_3010 Green
    ]
    for s_part, (gx, gy, gz), col in gallery_specs:
        tr = gp_Trsf()
        tr.SetTranslation(gp_Vec(gx, gy, gz))
        s_shifted = BRepBuilderAPI_Transform(s_part, tr, True).Shape()
        ren4.AddActor(make_actor(shape_to_polydata(s_shifted, tmp_stl), col, 1.0, edge_vis=True))

    frames_4 = []
    n_frames_4 = 36
    for i in range(n_frames_4):
        theta = 2.0 * math.pi * i / n_frames_4
        cam = ren4.GetActiveCamera()
        cam.SetPosition(320.0 * math.sin(theta), 320.0 * math.cos(theta), 55.0 + 25.0 * math.sin(theta))
        cam.SetFocalPoint(0.0, 0.0, -10.0)
        cam.SetViewUp(0, 0, 1)
        ren4.ResetCamera()
        cam.Zoom(1.38)
        ren4.ResetCameraClippingRange()
        frames_4.append(capture_frame(rw4))
    save_gif(frames_4, IMG_DIR / "anim_04_printable_parts_360_showcase.gif", duration_ms=65)


if __name__ == "__main__":
    main()
