"""Print colour scheme for the SparkShift toolchanger: a filament colour for every printed part.

No black, white or grey on the printed parts. The ten tools run through a rainbow by tool number, and
bay(i) gives the colours for tool i and its dock. The carriage uses the colour wheel by job: a purple
case (violet front case and motor plate, magenta back case), warm moving parts (orange swing arm,
yellow cam and belt arches), the CPAP air path in cool colours along the flow (P27 violet at the blower,
then P20 blue, P21 cyan, P22 teal) and the probe and EBB42 mounts in lime. Hex values are for the CAD
views; use the nearest filament colour.
"""

PALETTE = {
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

# Printed parts other than the tools and docks. Parts that touch never share a colour.
PARTS = {
    "P01": "Magenta",      # back case
    "P02": "Violet",       # motor/servo plate
    "P03": "Violet",       # front case: frames every tool
    "P04F": "Orange",      # swing arm, front half
    "P04R": "Orange",      # swing arm, rear half
    "P05": "Yellow",       # servo cam
    "P06": "Green",        # compounds (inside)
    "P07": "Green",
    "P08": "Cyan",         # HGX drives (inside)
    "P09": "Cyan",
    "P12": "Yellow",       # spring pressure cup (inside)
    "P13": "Orange",       # GT2 tooth liners (inside the arches)
    "P14": "Orange",
    "P15": "Yellow",       # belt arches
    "P16": "Yellow",
    "P20": "Blue",         # CPAP hose inlet
    "P21": "Cyan",         # CPAP gantry bridge
    "P22": "Teal",         # CPAP lower plenum (ASA or GF-ABS: beside the hotend)
    "P23": "Lime",         # probe mount
    "P24": "Lime",         # EBB42 mount
    "P27": "Violet",       # CPAP blower mount, where the air path starts
    "P28": "Yellow",       # calibration jig
    "P29": "Magenta",      # rack mounts
    "P30": "Violet",       # rack side spacers
}

# Tool bodies (Bambu or Red Lizard, ASA or GF-ABS) by tool number.
TOOLS = ("Red", "Orange", "Yellow", "Lime", "Green", "Teal", "Cyan", "Blue", "Violet", "Magenta")


def bay(i):
    """Colours for tool i and its dock: body, P18 backplate, P25 dock, snap jaws and P26 chute."""
    c = TOOLS[i]
    return {"body": c, "P18": c, "P25": c, "Jaws": c, "P26": c}


# Purchased parts in the CAD views.
OTHER = {
    "silicone": "#B3261E", "steel": "#A3A8AE", "brass": "#C9962E", "aluminium": "#C9CCD1",
    "bronze": "#B07A3C", "magnet": "#BFC3C8", "fan": "#1E1E21", "pcb": "#1C1D22", "servo": "#1F3A8A",
    "belt": "#141416", "anodised": "#26272B", "cable": "#202024", "ptfe": "#F2F2F2", "probe": "#151517",
    "connector": "#E8E3D3", "existing": "#18181B",
}


def hex_rgb(value):
    value = PALETTE.get(value, OTHER.get(value, value)).lstrip("#")
    return tuple(int(value[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def part(key):
    return hex_rgb(PARTS[key])


def tool(i):
    return hex_rgb(TOOLS[i])
