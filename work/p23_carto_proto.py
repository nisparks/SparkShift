"""Prototype: a P23 for the Cartographer, 0.2 mm thinner, with M3x5 probe screws. Scratch check only."""
import sys
from pathlib import Path

REPO = Path(r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26")
sys.path.insert(0, str(REPO))

import cadquery as cq  # noqa: E402

import r37_parts as P37  # noqa: E402
import r41_parts as R  # noqa: E402
from audit_tool_owned_2510 import bounds, overlaps  # noqa: E402
from build_modular_toolhead import box, load  # noqa: E402

RAISE = 0.2
SEAT = P37.Z_SEAT + RAISE
CARTO_BOTTOM = -76.600 + P37.DZ + RAISE          # coil face = board bottom
TIP = -78.8794

cart = P37.cartographer(P37.DZ + RAISE)
solids = sorted(cart.Solids(), key=lambda s: bounds(s)[4])
print("Cartographer solids:", len(solids))
for s in solids[:5]:
    print("  low solid", [round(v, 2) for v in bounds(s)], "vol", round(s.Volume(), 2))
board_like = [s for s in cart.Solids() if abs(bounds(s)[4] - CARTO_BOTTOM) < 0.05]
print("solids whose bottom is the coil face:", len(board_like), [[round(v, 2) for v in bounds(s)] for s in board_like[:3]])

p23 = P37.p23()
p23c = p23.cut(box(-25.0, 25.0, -30.0, 15.0, P37.Z_SEAT - 1.0, SEAT)).clean()
print("P23 vol", round(p23.Volume(), 2), "P23C vol", round(p23c.Volume(), 2), "valid", p23c.isValid(), "solids", len(p23c.Solids()),
      "bounds", [round(v, 2) for v in bounds(p23c)])
print("seat moves", RAISE, "coil above tip", round(CARTO_BOTTOM - TIP, 3), "web under sockets", round(P37.SOCKET_BOTTOM - SEAT, 2))

hw = {}
for i, (x, y) in enumerate(P37.PROBE_XY):
    hw[f"PROBE_M3x5_{i}"] = P37.screw(x, y, CARTO_BOTTOM - 1.5, 2.75, 1.5, 5.0)
    hw[f"PROBE_INSERT_{i}"] = P37.insert(x, y)
for i, (x, y) in enumerate(P37.REAR_XY):
    hw[f"REAR_M3x4_{i}"] = P37.screw(x, y, SEAT - 1.65, 2.85, 1.65, 4.0)
    hw[f"REAR_INSERT_{i}"] = P37.insert(x, y)
for n, s in hw.items():
    if "INSERT" not in n:
        top = bounds(s)[5]
        print(f"  {n}: tip Z {top:.3f}, short of the hole end by {P37.SPIGOT_Z[1] - top:.2f}, engagement "
              f"{min(top, P37.SPIGOT_Z[1]) - P37.SPIGOT_Z[0]:.2f}, head bottom {bounds(s)[4]:.3f} ({bounds(s)[4] - TIP:.2f} above the tip)")

parts = {k: load(R.NAMES[k]) for k in ("p01", "p02", "p20", "p21", "p24")}
parts["p22"] = R.p22()
parts["p23c"] = p23c
parts["ebb42"] = P37.ebb42()
everything = {**parts, **hw}
print("Cartographer vs carriage:", overlaps(cart, everything))
for n, s in hw.items():
    hits = overlaps(s, {**parts, "Cartographer": cart})
    if hits:
        print("  ", n, hits)
print("gaps:", {k: round(cart.distance(v), 3) for k, v in (("p22", parts["p22"]), ("p23c", p23c))})
