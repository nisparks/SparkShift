from pathlib import Path

import cadquery as cq


ROOT = Path(
    r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner"
)
STEP_DIR = ROOT / "cad" / "SparkShift_Accessories_v26" / "step"
OUT_DIR = Path(
    r"C:\Users\nspar\.copilot\session-state\601ee3b1-e729-45ee-9b22-df076d6c9dc8\files"
)

carrier_path = STEP_DIR / "P17_Bambu_P2S_tool_carrier_3010.step"
hotend_path = STEP_DIR / "Hotend_Voron_Bambu_P2S.step"

carrier = cq.importers.importStep(str(carrier_path)).val()
hotend = cq.importers.importStep(str(hotend_path)).val()

rear_min_y = 11.50
split_y = 24.00
front_max_y = 35.93
explode = 10.00

rear_box = cq.Solid.makeBox(
    40.0,
    split_y - rear_min_y,
    140.0,
    cq.Vector(-20.0, rear_min_y, -75.0),
)
front_box = cq.Solid.makeBox(
    40.0,
    front_max_y - split_y,
    140.0,
    cq.Vector(-20.0, split_y, -75.0),
)

rear = carrier.intersect(rear_box).translate(cq.Vector(0.0, -explode, 0.0))
front = carrier.intersect(front_box).translate(cq.Vector(0.0, explode, 0.0))

bolt_shapes = []
for sx in (-12.0, 12.0):
    for sz in (-49.5, -25.5):
        bolt_shapes.append(
            cq.Solid.makeCylinder(
                1.50,
                22.0,
                cq.Vector(sx, 21.0, sz),
                cq.Vector(0.0, 1.0, 0.0),
            )
        )
        bolt_shapes.append(
            cq.Solid.makeCylinder(
                2.75,
                1.60,
                cq.Vector(sx, 35.93 + explode, sz),
                cq.Vector(0.0, 1.0, 0.0),
            )
        )

preview = cq.Compound.makeCompound(
    [
        rear,
        front,
        hotend,
    ]
    + bolt_shapes
)

preview_step = OUT_DIR / "bambu_two_piece_front_rear_split_preview.step"
preview_stl = OUT_DIR / "bambu_two_piece_front_rear_split_preview.stl"
cq.exporters.export(preview, str(preview_step))
cq.exporters.export(preview, str(preview_stl))

print(preview_step)
print(preview_stl)
print("split_y_mm", split_y)
print("explode_y_mm", explode)
print("rear_mating_face_y", split_y - explode)
print("front_mating_face_y", split_y + explode)
print("bolt_pattern_x_z_mm", [[-12.0, -49.5], [12.0, -49.5], [-12.0, -25.5], [12.0, -25.5]])
