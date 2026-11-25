import tempfile
import unittest
from pathlib import Path

import eval_fixtures as fx

try:
    import matplotlib  # noqa: F401
    import plot
except ImportError:
    plot = None


@unittest.skipIf(plot is None, "matplotlib is not installed")
class Plots(unittest.TestCase):
    def test_all_plots_and_report_are_written(self):
        with tempfile.TemporaryDirectory() as tmp:
            fx.fake_results(tmp)
            files = plot.make_all(tmp, boot=200)
            self.assertEqual(len(files), 11)
            for _, p in files:
                self.assertGreater(Path(p).stat().st_size, 1000, p)
            html = (Path(tmp) / "report.html").read_text()
            self.assertEqual(html.count("data:image/png;base64"), 11)
            self.assertIn("P(beats default)", html)

    def test_empty_results_still_draw_placeholders(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(len(plot.make_all(tmp, boot=50)), 11)


if __name__ == "__main__":
    unittest.main()
