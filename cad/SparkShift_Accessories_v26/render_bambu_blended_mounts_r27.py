"""Compare blocky revision26 with tapered revision27 from three review angles."""

from render_bambu_closed_mounts_r26 import render_comparison


if __name__ == "__main__":
    render_comparison(
        "Bambu_Closed_Fan_Seats_Continuous_Junction_R26_REVIEW",
        "Bambu_Blended_Closed_Fan_Seats_R27_REVIEW",
        "R26 INTERMEDIATE: block pads, thin lips and tiny relief webs",
        "R27 REVIEW: tapered webs, eased corners and simpler core clearance",
        "51_bambu_blended_mounts_r27_four_views")
