"""Print colour scheme for the SparkShift toolchanger: one filament colour per printed part.

Structure is black and greys and the carriage's front face white. The air path runs in blues
(P20 blue, P21 cyan, P22 teal), moving parts in warm colours, electronics and probe in violet and
lime. The ten tools run through a rainbow by tool number, and each dock's purge chute matches its
tool. Hex values are for the CAD views; use the nearest filament colour.
"""

PALETTE = {
    "Black": "#18181B",
    "Charcoal": "#3C4048",
    "Cool Grey": "#9097A0",
    "White": "#EEEEEE",
    "Red": "#D7263D",
    "Orange": "#FF6B1A",
    "Yellow": "#FFC20E",
    "Lime": "#8BD82B",
    "Green": "#12A35A",
    "Teal": "#00A39B",
    "Cyan": "#12B9E6",
    "Blue": "#2453D9",
    "Violet": "#7B3FE4",
    "Magenta": "#E0218A",
}

# Printed parts. Visible carriage parts all differ; parts inside the case may repeat a colour.
PARTS = {
    "P01": "Black",        # back case
    "P02": "Cool Grey",    # motor/servo plate
    "P03": "White",        # front case
    "P04F": "Orange",      # swing arm, front half
    "P04R": "Orange",      # swing arm, rear half
    "P05": "Yellow",       # servo cam
    "P06": "Magenta",      # compounds (inside)
    "P07": "Magenta",
    "P08": "Green",        # HGX drives (inside)
    "P09": "Green",
    "P12": "Yellow",       # spring pressure cup (inside)
    "P13": "White",        # GT2 tooth liners (inside the arches)
    "P14": "White",
    "P15": "Red",          # belt arches
    "P16": "Red",
    "P20": "Blue",         # CPAP hose inlet
    "P21": "Cyan",         # CPAP gantry bridge
    "P22": "Teal",         # CPAP lower plenum (ASA or GF-ABS: beside the hotend)
    "P23": "Lime",         # probe mount
    "P24": "Violet",       # EBB42 mount
    "P18": "Black",        # docking backplate, all ten tools
    "P25": "Black",        # dock
    "Jaws": "White",       # upper and lower snap jaws
    "P27": "Black",        # CPAP blower mount
    "P28": "Yellow",       # calibration jig
    "P29": "Black",        # rack mounts
    "P30": "Charcoal",     # rack side spacers
}

# Tool bodies (Bambu or Red Lizard, ASA or GF-ABS) by tool number; each dock's P26 chute matches.
TOOLS = ("Red", "Orange", "Yellow", "Lime", "Green", "Teal", "Cyan", "Blue", "Violet", "Magenta")

# Purchased parts in the CAD views.
OTHER = {
    "silicone": "#B3261E", "steel": "#A3A8AE", "brass": "#C9962E", "aluminium": "#C9CCD1",
    "bronze": "#B07A3C", "magnet": "#BFC3C8", "fan": "#1E1E21", "pcb": "#1C1D22", "servo": "#1F3A8A",
    "belt": "#141416", "anodised": "#26272B", "cable": "#202024", "ptfe": "#F2F2F2", "probe": "#151517",
    "connector": "#E8E3D3",
}


def hex_rgb(value):
    value = PALETTE.get(value, OTHER.get(value, value)).lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def part(key):
    return hex_rgb(PARTS[key])


def tool(i):
    return hex_rgb(TOOLS[i])
