import json, math
from pathlib import Path
from helper_init2 import load_brep_solids, load_step_solids, test_probe, WORK, sensor_dir, v26_solids, gantry_solids

beacon_norm = load_step_solids(sensor_dir / "Beacon_RevH_Assm_Normal.STEP")
beacon_lp = load_step_solids(sensor_dir / "Beacon_RevH_Assm_LowProfile.STEP")
carto_ra = load_step_solids(sensor_dir / "Cartographer_V3_RightAngle.step")

# Shared mounting holes at X = ±15.80, Y_holes = -3.20, Z_seat = -74.5194
for y_holes in [-3.50, -3.20, -3.00, -2.80]:
    # For Beacon (rot=180): holes in STEP are at (±15.8, -3.5). Under rot=180, holes are at (±15.8, +3.5).
    # So to put holes at y_holes, y_coil = y_holes - 3.5!
    y_coil_b = y_holes - 3.5
    rb_norm = test_probe(beacon_norm, (2, 3, 4), 1, 0, 180, 0.0, y_coil_b, -74.5194)
    rb_lp = test_probe(beacon_lp, (0, 1, 2), 4, 3, 180, 0.0, y_coil_b, -74.5194)

    # For Cartographer RA (rot=0): holes in STEP are at (±15.8, -12.707), coil at (0, -15.883).
    # Under rot=0, to put holes at y_holes, y_trans = y_holes + 12.707, which puts coil at y_holes - 3.176!
    y_trans_c = y_holes + 12.70701
    y_coil_c = y_holes - (15.88304 - 12.70701)
    rc_ra = test_probe(carto_ra, tuple(range(2, 102)), 1, 0, 0, 0.0, y_trans_c, -74.5194)

    print(f"=== Y_holes = {y_holes:.2f} mm ===")
    print(f"  Beacon Normal (Y_coil={y_coil_b:.2f}): Yspan={rb_norm['y_span']} hGap={rb_norm['heater_gap_y']:.2f} v26={rb_norm['phys_v26_hits']} gantry={rb_norm['phys_gantry_hits']} metal={rb_norm['metal_hits']}")
    print(f"  Beacon LowPro (Y_coil={y_coil_b:.2f}): Yspan={rb_lp['y_span']} hGap={rb_lp['heater_gap_y']:.2f} v26={rb_lp['phys_v26_hits']} gantry={rb_lp['phys_gantry_hits']} metal={rb_lp['metal_hits']}")
    print(f"  Carto RightAn (Y_coil={y_coil_c:.2f}): Yspan={rc_ra['y_span']} hGap={rc_ra['heater_gap_y']:.2f} v26={rc_ra['phys_v26_hits']} gantry={rc_ra['phys_gantry_hits']} metal={rc_ra['metal_hits']}")

