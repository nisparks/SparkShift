"""Show removal of the broad wedges from the revision27 shelf."""

from render_bambu_closed_mounts_r26 import render_comparison


if __name__ == "__main__":
    render_comparison(
        "Bambu_Blended_Closed_Fan_Seats_R27_REVIEW",
        "Bambu_Flat_Shelf_Local_Fan_Bosses_R28_REVIEW",
        "R27 SUPERSEDED: broad tapered wedges",
        "R28: flat shelf underside with localized round insert bosses",
        "54_bambu_flat_shelf_r28_four_views")
