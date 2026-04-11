import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from renderer.svg_backend import svg_locus


def test_svg_locus_renders_curve_for_points():
    svg = svg_locus({"points": [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]})
    assert "<path" in svg
    assert 'd="M 0.000,0.000 L 10.000,0.000 L 10.000,10.000 Z"' in svg
    assert "stroke=" in svg
    assert 'fill="none"' in svg
