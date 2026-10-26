"""Remove the broad revision27 wedges, retaining only localized insert bosses."""

from build_bambu_blended_mounts_r27 import build


if __name__ == "__main__":
    build(localized_bosses=True)
