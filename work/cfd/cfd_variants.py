"""P22 variants for the CFD design study (session scratch)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from cfd_scene import *  # noqa: E402,F403

OUT = Path(__file__).parent / "variants"
OUT.mkdir(exist_ok=True)


def jet_lip_cutters(r=1.4, y=(16.80, 27.62)):
    """Round the chamber-side bottom corner of each duct-to-slot wall (|X| 11.6 at Z ROOF) with radius r: a
    bell-mouth into the jet. The wall's lowest point stays at ROOF on the slot side (|X| 10.2)."""
    out = []
    for side in (-1, 1):
        x_in, x_out = side * R.WALL_X[0], side * R.WALL_X[1]
        lo, hi = sorted((x_out - side * r, x_out))
        corner = R.shape(R.a.box(lo, hi, y[0], y[1], R.ROOF - 0.01, R.ROOF + r))
        round_ = R.shape(R.a.cyl_y(x_out - side * r, R.ROOF + r, y[0] - 0.1, y[1] + 0.1, r))
        out.append(corner.cut(round_))
    return out


if __name__ == "__main__":
    p22 = brep(carriage()[R.NAMES["p22"]])
    r = float(sys.argv[1]) if len(sys.argv) > 1 else 1.4
    new = R.cut(p22, jet_lip_cutters(r))
    new = R.single(R.unify(new), "P22 lip variant")
    print("valid", new.isValid(), "solids", len(new.Solids()), "volume", round(new.Volume(), 2),
          "was", round(p22.Volume(), 2), "removed", round(p22.Volume() - new.Volume(), 2))
    print("bounds", [round(v, 3) for v in bounds(new)], "was", [round(v, 3) for v in bounds(p22)])
    path = OUT / f"p22_lip{int(round(r * 10))}.brep"
    new.exportBrep(str(path))
    print(path)
