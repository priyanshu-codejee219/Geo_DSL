import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from interpreter.environment import Environment
from interpreter.interpreter import GeoShape
from renderer.renderer import (
    Renderer,
    _extract_world_coords,
    _svg_id,
    _ViewportTransform,
)
from renderer.svg_backend import (
    render_shape,
    shape_centre,
    svg_arc,
    svg_circle,
    svg_ellipse,
    svg_grid,
    svg_label,
    svg_line,
    svg_locus,
    svg_measure_annotation,
    svg_note,
    svg_parallelogram,
    svg_point,
    svg_polygon,
    svg_ray,
    svg_rectangle,
    svg_regular_poly,
    svg_rhombus,
    svg_segment,
    svg_triangle,
)


def test_svg_locus_renders_curve_for_points():
    svg = svg_locus({"points": [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0)]})
    assert "<path" in svg
    assert 'd="M 0.000,0.000 L 10.000,0.000 L 10.000,10.000 Z"' in svg
    assert "stroke=" in svg
    assert 'fill="none"' in svg


def test_svg_point():
    svg = svg_point({"x": 10.0, "y": 20.0})
    assert (
        '<circle cx="10.000" cy="20.000" r="4.0" stroke="#2563eb" fill="#2563eb" opacity="1.0" />'
        == svg
    )


def test_svg_segment():
    svg = svg_segment({"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0})
    assert (
        '<line x1="0.000" y1="0.000" x2="10.000" y2="10.000" stroke="#2563eb" fill="none" stroke-width="1.8" opacity="1.0" />'
        == svg
    )


def test_svg_line():
    svg = svg_line({"a": 1.0, "b": -1.0, "c": 0.0}, viewport_w=100.0, viewport_h=100.0)
    assert "<line" in svg


def test_svg_ray():
    svg = svg_ray(
        {"ox": 0.0, "oy": 0.0, "dx": 1.0, "dy": 0.0}, viewport_w=100.0, viewport_h=100.0
    )
    assert "<line" in svg
    assert 'x1="0.000" y1="0.000"' in svg


def test_svg_circle():
    svg = svg_circle({"cx": 5.0, "cy": 5.0, "radius": 3.0})
    assert (
        '<circle cx="5.000" cy="5.000" r="3.000" stroke="#2563eb" fill="none" stroke-width="1.8" opacity="1.0" />'
        == svg
    )


def test_svg_arc():
    svg = svg_arc(
        {"cx": 0.0, "cy": 0.0, "radius": 5.0, "start_deg": 0.0, "end_deg": 90.0}
    )
    assert "<path" in svg
    assert 'd="M 5.000 0.000 A 5.000 5.000 0 0 1 0.000 5.000"' in svg


def test_svg_ellipse():
    svg = svg_ellipse({"cx": 0.0, "cy": 0.0, "rx": 5.0, "ry": 3.0, "rotation_deg": 0.0})
    assert (
        '<ellipse cx="0.000" cy="0.000" rx="5.000" ry="3.000" transform="rotate(0.000 0.000 0.000)"'
        in svg
    )


def test_svg_triangle():
    svg = svg_triangle(
        {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "x3": 5.0, "y3": 10.0}
    )
    assert "<polygon" in svg
    assert 'points="0.000,0.000 10.000,0.000 5.000,10.000"' in svg


def test_svg_rectangle():
    svg = svg_rectangle(
        {
            "x1": 0.0,
            "y1": 0.0,
            "x2": 10.0,
            "y2": 0.0,
            "x3": 10.0,
            "y3": 10.0,
            "x4": 0.0,
            "y4": 10.0,
        }
    )
    assert "<polygon" in svg


def test_svg_rhombus():
    svg = svg_rhombus(
        {
            "x1": 0.0,
            "y1": 5.0,
            "x2": 5.0,
            "y2": 0.0,
            "x3": 10.0,
            "y3": 5.0,
            "x4": 5.0,
            "y4": 10.0,
        }
    )
    assert "<polygon" in svg


def test_svg_parallelogram():
    svg = svg_parallelogram(
        {
            "x1": 0.0,
            "y1": 0.0,
            "x2": 10.0,
            "y2": 0.0,
            "x3": 15.0,
            "y3": 10.0,
            "x4": 5.0,
            "y4": 10.0,
        }
    )
    assert "<polygon" in svg


def test_svg_regular_poly():
    svg = svg_regular_poly(
        {
            "sides": 6,
            "x1": 0.0,
            "y1": 0.0,
            "x2": 1.0,
            "y2": 0.0,
            "x3": 0.5,
            "y3": 0.866,
            "x4": -0.5,
            "y4": 0.866,
            "x5": -1.0,
            "y5": 0.0,
            "x6": -0.5,
            "y6": -0.866,
        }
    )
    assert "<polygon" in svg


def test_svg_polygon():
    svg = svg_polygon(
        {
            "n": 5,
            "x1": 0.0,
            "y1": 0.0,
            "x2": 2.0,
            "y2": 0.0,
            "x3": 2.5,
            "y3": 2.0,
            "x4": 1.0,
            "y4": 3.0,
            "x5": 0.0,
            "y5": 2.0,
        }
    )
    assert "<polygon" in svg


def test_svg_label():
    svg = svg_label(10.0, 20.0, "test label")
    assert 'x="20.000"' in svg
    assert 'y="10.000"' in svg
    assert ">test label</text>" in svg


def test_svg_note():
    svg = svg_note(10.0, 20.0, "test note")
    assert '<text x="10.000" y="20.000"' in svg
    assert 'font-style="italic"' in svg
    assert ">test note</text>" in svg


def test_svg_measure_annotation():
    svg = svg_measure_annotation(0.0, 0.0, 10.0, 0.0, "5.0")
    assert "<line" in svg
    assert "<text" in svg
    assert ">5.0</text>" in svg


def test_svg_grid():
    svg = svg_grid(100.0, 100.0, spacing=20.0, origin_x=0.0, origin_y=0.0)
    assert "<line" in svg


def test_render_shape():
    svg = render_shape("point", {"x": 5.0, "y": 5.0})
    assert "<circle" in svg


def test_shape_centre():
    centre = shape_centre("point", {"x": 10.0, "y": 20.0})
    assert centre == (10.0, 20.0)

    centre = shape_centre("circle", {"cx": 5.0, "cy": 5.0})
    assert centre == (5.0, 5.0)

    centre = shape_centre("segment", {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 10.0})
    assert centre == (5.0, 5.0)


def test_renderer_render_static():
    renderer = Renderer()
    shapes = [("p1", GeoShape("point", "p1", {"x": 10.0, "y": 20.0}))]
    svg = renderer.render_static(shapes)
    assert "<svg" in svg
    assert "</svg>" in svg
    assert "<circle" in svg


def test_renderer_render_sweep():
    renderer = Renderer()
    from evaluator.evaluator import SweepFrame

    frame = SweepFrame(
        param_name="t",
        param_value=1.0,
        shapes={"p1": GeoShape("point", "p1", {"x": 10.0, "y": 20.0})},
        env=Environment(),
    )
    svgs = renderer.render_sweep([frame])
    assert len(svgs) == 1
    assert "<svg" in svgs[0]


def test_renderer_render_animated_svg():
    renderer = Renderer()
    from evaluator.evaluator import SweepFrame

    frame = SweepFrame(
        param_name="t",
        param_value=1.0,
        shapes={"p1": GeoShape("point", "p1", {"x": 10.0, "y": 20.0})},
        env=Environment(),
    )
    svg = renderer.render_animated_svg([frame])
    assert "<svg" in svg
    assert "animated" not in svg


def test_renderer__measure_annotation():
    renderer = Renderer()
    shape = GeoShape(
        "segment", "s1", {"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "length": 10.0}
    )
    transform = _ViewportTransform(scale=1.0, offset_x=50.0, offset_y=50.0)
    ann = renderer._measure_annotation(shape, transform)
    assert "<line" in ann
    assert "<text" in ann


def test_renderer__compute_transform():
    renderer = Renderer()
    shapes = [
        ("p1", GeoShape("point", "p1", {"x": 0.0, "y": 0.0})),
        ("p2", GeoShape("point", "p2", {"x": 10.0, "y": 10.0})),
    ]
    transform = renderer._compute_transform(shapes)
    assert transform.scale > 0
    assert transform.offset_x > 0


def test_renderer__wrap_svg():
    renderer = Renderer()
    body = '<circle cx="10" cy="20" r="5" />'
    svg = renderer._wrap_svg(body)
    assert svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"')
    assert body in svg
    assert svg.endswith("</svg>")


def test_viewport_transform_world_to_screen():
    vt = _ViewportTransform(scale=2.0, offset_x=10.0, offset_y=20.0)
    sx, sy = vt.world_to_screen(5.0, 3.0)
    assert sx == 20.0
    assert sy == 14.0


def test_viewport_transform_scale_length():
    vt = _ViewportTransform(scale=2.0, offset_x=0.0, offset_y=0.0)
    assert vt.scale_length(5.0) == 10.0


def test_viewport_transform_transform_props():
    vt = _ViewportTransform(scale=2.0, offset_x=10.0, offset_y=20.0)
    props = {"x": 1.0, "y": 2.0, "radius": 3.0}
    transformed = vt.transform_props("point", props)
    assert transformed["x"] == 12.0
    assert transformed["y"] == 16.0
    assert transformed["radius"] == 6.0


def test_extract_world_coords():
    shape = GeoShape("point", "p1", {"x": 1.0, "y": 2.0})
    coords = _extract_world_coords(shape)
    assert coords == [(1.0, 2.0)]

    shape = GeoShape("circle", "c1", {"cx": 0.0, "cy": 0.0, "radius": 5.0})
    coords = _extract_world_coords(shape)
    assert len(coords) == 2


def test_svg_id():
    assert _svg_id("my_shape") == "my_shape"
    assert _svg_id("my-shape") == "my_shape"
    assert _svg_id("my shape") == "my_shape"
