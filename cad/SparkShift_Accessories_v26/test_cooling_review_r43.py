import json
import math
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import numpy as np

import cfd_bead_zones_r43 as Z
import cfd_cpap_r41_post as P
import cfd_nozzle_focus_r43 as F
import cfd_outlet_balance_r43 as B
import cfd_provenance_r43 as V


class CoolingReviewTests(unittest.TestCase):
    def test_expanded_slot_uses_its_own_geometry(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            p22 = root / "p22.brep"
            p22.write_bytes(b"geometry identity")
            params = {"mouth_height_mm": 2, "angle_deg": 40,
                      "floor_reference_height_mm": .9, "roof_raise_mm": 3}
            (root / "domain.json").write_text(json.dumps({
                "p22_variant": str(p22), "geometry_sha256": {"p22": V.digest(p22)}, "rear_slot": params}))
            with patch.object(B.C, "results_dir", return_value=root):
                self.assertEqual(B.slot_parameters("test"), params)
                p22.write_bytes(b"changed geometry")
                with self.assertRaisesRegex(ValueError, "stale"):
                    B.slot_parameters("test")

    def test_slot_plane_uses_requested_angle(self):
        with patch.object(B.P, "cut", return_value="plane") as cut, \
                patch.object(B.P, "clip_box", return_value="clipped"), \
                patch.object(B, "keep_inside", return_value="section"):
            section, normal = B.slot_section(None, None, angle=40)
            self.assertEqual(section, "section")
            self.assertAlmostEqual(normal[1], math.cos(math.radians(40)))
            self.assertAlmostEqual(normal[2], -math.sin(math.radians(40)))
            np.testing.assert_allclose(cut.call_args.args[2], normal)

    def test_duplicate_result_directory_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for name in ("first_1200", "stale_1200"):
                (root / "VTK" / name).mkdir(parents=True)
            with patch.object(P.C, "results_dir", return_value=root):
                with self.assertRaisesRegex(ValueError, "exactly one"):
                    P.vtk_dir("test", 1200)

    def test_missing_or_changed_cache_fingerprint_is_rejected(self):
        with self.assertRaises(ValueError):
            V.require_current(None, {"grid": "new"}, "cache")
        with self.assertRaises(ValueError):
            V.require_current({"grid": "old"}, {"grid": "new"}, "cache")
        V.require_current({"grid": "same"}, {"grid": "same"}, "cache")

    def test_own_side_below_tip_is_a_hit(self):
        p = np.array([[-10, Z.NY, Z.BED_Z + 3], [-2, Z.NY, Z.BED_Z + .1]])
        self.assertEqual(Z.classify("left", p, 4), ("hit", 0))

    def test_later_return_after_crossing_centre_is_not_a_hit(self):
        p = np.array([[-10, Z.NY, Z.BED_Z + 3], [-2, Z.NY, Z.BED_Z + 2],
                      [1, Z.NY, Z.BED_Z + .1], [-1, Z.NY, Z.BED_Z + .1]])
        self.assertEqual(Z.classify("left", p, 4)[0], "higher")

    def test_air_above_the_tip_is_not_a_hit(self):
        p = np.array([[-10, Z.NY, Z.BED_Z + 3], [-2, Z.NY, F.C.NOZZLE_TIP_Z + .01]])
        self.assertEqual(Z.classify("left", p, 4)[0], "higher")

    def test_straight_ray_stops_at_the_print_plane(self):
        p = Z.straight(np.array([-6, Z.NY, Z.BED_Z + .33]), np.array([.6, 0, -.8]))
        self.assertAlmostEqual(p[-1, 2], Z.BED_Z)
        self.assertTrue(np.all(p[:, 2] >= Z.BED_Z - 1e-12))

    def test_plot_target_is_below_tip(self):
        x = np.linspace(-4, 4, 10)
        z = np.linspace(Z.BED_Z, Z.BED_Z + 4, 10)
        u = np.ma.array(np.ones((10, 10)))
        fig, ax = plt.subplots()
        F.draw_section(ax, (x, z, u, u, u), "test", "X", [], (-2, 2))
        target = next(p for p in ax.patches if isinstance(p, Rectangle))
        self.assertAlmostEqual(target.get_y() + target.get_height(), F.C.NOZZLE_TIP_Z)
        plt.close(fig)


class FlowOppositionTests(unittest.TestCase):
    def test_plane_flux_integrates_scaled_uniform_flow_with_sign(self):
        import cfd_flow_opposition_r43 as O

        def probe(_, pts):
            return np.ones(len(pts), bool), np.tile([0.0, -2.0, 0.0], (len(pts), 1))

        with patch.object(O.N, "probe", probe):
            flux = O.plane_flux(None, 1.5, "y", 20.0, (-1.0, 1.0), (0.0, 0.5))
        expected = 3.0 * 2e-3 * 0.5e-3 * 60000.0
        self.assertAlmostEqual(flux["reverse_lpm"], expected, places=6)
        self.assertAlmostEqual(flux["net_lpm"], -expected, places=6)
        self.assertEqual(flux["forward_lpm"], 0.0)


if __name__ == "__main__":
    unittest.main()
