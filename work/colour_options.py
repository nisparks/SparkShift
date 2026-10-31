"""Build four dock-colour options with the new carriage scheme (session preview, not committed)."""
import os
import sys

ROOT = r"C:\Users\nspar\Dev\copilot-worktrees\CxChanger\nisparks-solid-winner\cad\SparkShift_Accessories_v26"
sys.path.insert(0, ROOT)
os.chdir(ROOT)
import build_print_colour_review as B  # noqa: E402
import print_colors as C  # noqa: E402

DARK = {"Red": "#7A1426", "Orange": "#9A3D0C", "Yellow": "#9A7400", "Lime": "#4F7A16", "Green": "#0A5C33",
        "Teal": "#005C57", "Cyan": "#0A6A85", "Blue": "#142F7A", "Violet": "#43227F", "Magenta": "#7D124D"}
T = C.TOOLS
OPTIONS = {
    "rainbow": lambda i: dict(body=T[i], P18=T[i], P25=T[i], Jaws=T[i], P26=T[i]),
    "complement": lambda i: dict(body=T[i], P18=T[i], P25=T[(i + 5) % 10], Jaws=T[i], P26=T[i]),
    "tonal": lambda i: dict(body=T[i], P18=T[i], P25=DARK[T[i]], Jaws=T[i], P26=T[i]),
    "purple": lambda i: dict(body=T[i], P18=T[i], P25="Violet", Jaws=T[i], P26=T[i]),
}
base = dict(C.PARTS)
for name in sys.argv[1:] or OPTIONS:
    C.PARTS.clear()
    C.PARTS.update(base)
    if name == "purple":
        C.PARTS.update(P29="Violet", P30="Magenta")
    C.bay = OPTIONS[name]
    B.OUT = B.acc.WORK / f"colour_option_{name}.step"
    B.main()
