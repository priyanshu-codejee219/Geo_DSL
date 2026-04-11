import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from interpreter.environment import Environment
from interpreter.interpreter import GeoShape
from solver.algebraic import (
    reflect_point_over_line,
    resolve_arc,
    resolve_circle,
    resolve_circumcircle,
    resolve_convex_hull,
    resolve_ellipse,
    resolve_incircle,
    resolve_intersection,
    resolve_line,
    resolve_midpoint,
    resolve_parallelogram,
    resolve_perpendicular_bisector,
    resolve_point,
    resolve_rectangle,
    resolve_regular_poly,
    resolve_segment,
    resolve_triangle,
    rotate_point_around,
    scale_point_from,
)
from solver.numeric import resolve_numeric
from solver.solver import GeoSolver


def _env(*named_points: tuple) -> Environment:
    env = Environment()
    for name, x, y in named_points:
        s = GeoShape("point", name, props={"x": float(x), "y": float(y)})
        env.define(name, s)
    return env


def _shape(kind: str, name: str = "S", **props) -> GeoShape:
    return GeoShape(kind, name, props=dict(props))


def _approx(a: float, b: float, tol: float = 1e-5) -> bool:
    return abs(a - b) < tol


class TestResolvePoint:
    def test_at_origin(self):
        s = _shape("point")
        s.constraints = [{"kind": "at", "targets": [(0.0, 0.0)]}]
        r = resolve_point(s, Environment())
        assert r is not None
        assert _approx(r.props["x"], 0.0)
        assert _approx(r.props["y"], 0.0)

    def test_at_arbitrary_coords(self):
        s = _shape("point")
        s.constraints = [{"kind": "at", "targets": [(3.0, 7.0)]}]
        r = resolve_point(s, Environment())
        assert _approx(r.props["x"], 3.0)
        assert _approx(r.props["y"], 7.0)

    def test_on_circle_places_at_rightmost(self):
        env = Environment()
        c = GeoShape("circle", "C", props={"cx": 0.0, "cy": 0.0, "radius": 50.0})
        env.define("C", c)
        s = _shape("point")
        s.constraints = [{"kind": "on", "targets": ["C"]}]
        r = resolve_point(s, env)
        assert r is not None
        assert _approx(r.props["x"], 50.0)
        assert _approx(r.props["y"], 0.0)

    def test_default_is_origin(self):
        s = _shape("point")
        s.constraints = []
        r = resolve_point(s, Environment())
        assert _approx(r.props["x"], 0.0)
        assert _approx(r.props["y"], 0.0)

    def test_wrong_kind_returns_none(self):
        s = _shape("circle")
        assert resolve_point(s, Environment()) is None


class TestResolveSegment:
    def test_two_named_endpoints(self):
        env = _env(("A", 0, 0), ("B", 100, 0))
        s = _shape("segment", args=["A", "B"])
        r = resolve_segment(s, env)
        assert r is not None
        assert _approx(r.props["length"], 100.0)
        assert _approx(r.props["x1"], 0.0)
        assert _approx(r.props["x2"], 100.0)

    def test_diagonal_length(self):
        env = _env(("A", 0, 0), ("B", 3, 4))
        s = _shape("segment", args=["A", "B"])
        r = resolve_segment(s, env)
        assert _approx(r.props["length"], 5.0)

    def test_one_endpoint_plus_length(self):
        env = _env(("A", 10, 20))
        s = _shape("segment", args=["A"], length=50.0)
        r = resolve_segment(s, env)
        assert r is not None
        assert _approx(r.props["x1"], 10.0)
        assert _approx(r.props["x2"], 60.0)

    def test_length_only_from_origin(self):
        s = _shape("segment", args=[], length=75.0)
        r = resolve_segment(s, Environment())
        assert r is not None
        assert _approx(r.props["x1"], 0.0)
        assert _approx(r.props["x2"], 75.0)

    def test_missing_data_returns_none(self):
        s = _shape("segment", args=[])
        assert resolve_segment(s, Environment()) is None


class TestResolveLine:
    def test_two_points_horizontal(self):
        env = _env(("A", 0, 5), ("B", 100, 5))
        s = _shape("line")
        s.constraints = [{"kind": "passes_through", "targets": ["A", "B"]}]
        r = resolve_line(s, env)
        assert r is not None
        # Line y = 5  ...  0*x + 1*y - 5 = 0  →  a=0, b=1, c=-5
        assert _approx(abs(r.props["b"]), 1.0)
        assert _approx(abs(r.props["c"]), 5.0)

    def test_two_points_vertical(self):
        env = _env(("A", 3, 0), ("B", 3, 10))
        s = _shape("line")
        s.constraints = [{"kind": "passes_through", "targets": ["A", "B"]}]
        r = resolve_line(s, env)
        # Line x = 3  ...  1*x + 0*y - 3 = 0
        assert _approx(abs(r.props["a"]), 1.0)
        assert _approx(abs(r.props["c"]), 3.0)

    def test_default_horizontal_through_origin(self):
        s = _shape("line")
        s.constraints = []
        r = resolve_line(s, Environment())
        assert r is not None
        assert _approx(r.props["a"], 0.0)
        assert _approx(r.props["b"], 1.0)
        assert _approx(r.props["c"], 0.0)

    def test_parallel_through_point(self):
        env = _env(("P", 0, 10))
        ref = GeoShape("line", "L", props={"a": 0.0, "b": 1.0, "c": 0.0})
        env.define("L", ref)
        s = _shape("line")
        s.constraints = [
            {"kind": "passes_through", "targets": ["P"]},
            {"kind": "parallel_to", "target": "L"},
        ]
        r = resolve_line(s, env)
        assert r is not None
        assert _approx(abs(r.props["c"]), 10.0)

    def test_tangent_to_circle(self):
        env = Environment()
        ref = GeoShape("circle", "C", props={"cx": 100.0, "cy": 0.0, "radius": 40.0})
        env.define("C", ref)
        s = _shape("line")
        s.constraints = [{"kind": "tangent_to", "target": "C"}]
        r = resolve_line(s, env)
        assert r is not None
        assert _approx(r.props["a"], 0.0)
        assert _approx(r.props["b"], 1.0)
        assert _approx(r.props["c"], -40.0)

    def test_bisects_segment(self):
        env = _env(("A", 0, 0), ("B", 10, 0), ("P", 5, 1))
        seg = GeoShape(
            "segment",
            "AB",
            props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0},
        )
        env.define("AB", seg)
        s = _shape("line", args=["P"])
        s.constraints = [{"kind": "bisects", "target": "AB"}]
        r = resolve_line(s, env)
        assert r is not None
        assert _approx(abs(r.props["a"]), 1.0)
        assert _approx(r.props["b"], 0.0)
        assert _approx(r.props["c"], -5.0)


class TestResolveCircle:
    def test_radius_at_origin(self):
        s = _shape("circle", radius=50.0)
        r = resolve_circle(s, Environment())
        assert r is not None
        assert _approx(r.props["radius"], 50.0)
        assert _approx(r.props["cx"], 0.0)

    def test_centered_at_named_point(self):
        env = _env(("O", 10, 20))
        s = _shape("circle", radius=30.0)
        s.constraints = [{"kind": "centered_at", "targets": ["O"]}]
        r = resolve_circle(s, env)
        assert _approx(r.props["cx"], 10.0)
        assert _approx(r.props["cy"], 20.0)
        assert _approx(r.props["radius"], 30.0)

    def test_passes_through_three_points_gives_circumcircle(self):
        # Right triangle with hypotenuse on diameter ... circumcircle centre at midpoint
        env = _env(("A", 0, 0), ("B", 4, 0), ("C", 0, 3))
        s = _shape("circle")
        s.constraints = [{"kind": "passes_through", "targets": ["A", "B", "C"]}]
        r = resolve_circle(s, env)
        assert r is not None
        # All three points should be on the circle
        for name, x, y in [("A", 0, 0), ("B", 4, 0), ("C", 0, 3)]:
            d = math.hypot(x - r.props["cx"], y - r.props["cy"])
            assert _approx(d, r.props["radius"], tol=1e-4)


class TestResolveArc:
    def test_default_start_angle_with_explicit_angle(self):
        s = _shape("arc", radius=60.0, angle=15.0)
        r = resolve_arc(s, Environment())
        assert r is not None
        assert _approx(r.props["start_deg"], 0.0)
        assert _approx(r.props["end_deg"], 15.0)

    def test_explicit_start_with_angle_extends_from_start(self):
        s = _shape("arc", radius=60.0, angle=15.0, start=30.0)
        r = resolve_arc(s, Environment())
        assert r is not None
        assert _approx(r.props["start_deg"], 30.0)
        assert _approx(r.props["end_deg"], 45.0)

    def test_explicit_end_with_angle_backfills_start(self):
        s = _shape("arc", radius=60.0, angle=15.0, end=90.0)
        r = resolve_arc(s, Environment())
        assert r is not None
        assert _approx(r.props["start_deg"], 75.0)
        assert _approx(r.props["end_deg"], 90.0)


class TestResolveTriangle:
    def test_three_named_vertices(self):
        env = _env(("A", 0, 0), ("B", 4, 0), ("C", 2, 3))
        s = _shape("triangle", args=["A", "B", "C"])
        r = resolve_triangle(s, env)
        assert r is not None
        assert _approx(r.props["x1"], 0.0)
        assert _approx(r.props["x2"], 4.0)
        assert _approx(r.props["y3"], 3.0)

    def test_missing_vertex_returns_none(self):
        env = _env(("A", 0, 0), ("B", 4, 0))
        s = _shape("triangle", args=["A", "B", "C"])
        assert resolve_triangle(s, env) is None


class TestResolveRectangle:
    def test_width_height_props(self):
        s = _shape("rectangle", length=100.0, height=60.0)
        s.constraints = []
        r = resolve_rectangle(s, Environment())
        assert r is not None
        assert _approx(r.props["width"], 100.0)
        assert _approx(r.props["height"], 60.0)
        assert _approx(r.props["x3"], 100.0)
        assert _approx(r.props["y3"], 60.0)

    def test_area_derives_height(self):
        s = _shape("rectangle", length=10.0, area=50.0)
        s.constraints = []
        r = resolve_rectangle(s, Environment())
        assert r is not None
        assert _approx(r.props["height"], 5.0)


class TestResolveRegularPoly:
    def test_hexagon_vertex_count(self):
        s = _shape("regular_poly", sides=6, radius=100.0)
        s.constraints = []
        r = resolve_regular_poly(s, Environment())
        assert r is not None
        assert r.props["sides"] == 6
        # All vertices should be 100 from centre
        for i in range(1, 7):
            d = math.hypot(
                r.props[f"x{i}"] - r.props["cx"], r.props[f"y{i}"] - r.props["cy"]
            )
            assert _approx(d, 100.0, tol=1e-4)

    def test_square_right_angles(self):
        s = _shape("regular_poly", sides=4, radius=1.0)
        s.constraints = []
        r = resolve_regular_poly(s, Environment())
        p1 = np.array([r.props["x1"], r.props["y1"]])
        p2 = np.array([r.props["x2"], r.props["y2"]])
        assert _approx(float(np.linalg.norm(p2 - p1)), math.sqrt(2), tol=1e-4)


class TestResolveEllipse:
    def test_rx_ry_placed_at_origin(self):
        s = _shape("ellipse", rx=80.0, ry=50.0)
        s.constraints = []
        r = resolve_ellipse(s, Environment())
        assert r is not None
        assert _approx(r.props["rx"], 80.0)
        assert _approx(r.props["ry"], 50.0)
        assert _approx(r.props["cx"], 0.0)


class TestResolveParallelogram:
    def test_base_side_angle_produces_four_vertices(self):
        s = _shape("parallelogram", length=100.0, side=60.0, angle=60.0)
        s.constraints = []
        r = resolve_parallelogram(s, Environment())
        assert r is not None
        for i in range(1, 5):
            assert f"x{i}" in r.props

    def test_opposite_sides_parallel(self):
        s = _shape("parallelogram", length=100.0, side=60.0, angle=45.0)
        s.constraints = []
        r = resolve_parallelogram(s, Environment())
        p1 = np.array([r.props["x1"], r.props["y1"]])
        p2 = np.array([r.props["x2"], r.props["y2"]])
        p3 = np.array([r.props["x3"], r.props["y3"]])
        p4 = np.array([r.props["x4"], r.props["y4"]])
        d12 = p2 - p1
        d43 = p3 - p4
        cross = float(d12[0] * d43[1] - d12[1] * d43[0])
        assert _approx(cross, 0.0, tol=1e-4)


class TestResolveMidpoint:
    def test_midpoint_of_two_points(self):
        env = _env(("A", 0, 0), ("B", 10, 0))
        r = resolve_midpoint(_shape("point", "M"), ["A", "B"], env)
        assert _approx(r.props["x"], 5.0)
        assert _approx(r.props["y"], 0.0)

    def test_midpoint_of_segment(self):
        env = Environment()
        seg = GeoShape(
            "segment", "AB", props={"x1": 2.0, "y1": 4.0, "x2": 8.0, "y2": 10.0}
        )
        env.define("AB", seg)
        r = resolve_midpoint(_shape("point", "M"), ["AB"], env)
        assert _approx(r.props["x"], 5.0)
        assert _approx(r.props["y"], 7.0)

    def test_missing_point_returns_none(self):
        assert resolve_midpoint(_shape("point", "M"), ["A", "B"], Environment()) is None


class TestResolveIntersection:
    def test_two_lines_cross(self):
        env = Environment()
        L1 = GeoShape("line", "L1", props={"a": 0.0, "b": 1.0, "c": 0.0})
        L2 = GeoShape("line", "L2", props={"a": 1.0, "b": 0.0, "c": -5.0})
        env.define("L1", L1)
        env.define("L2", L2)
        r = resolve_intersection(_shape("point", "P"), ["L1", "L2"], env)
        assert _approx(r.props["x"], 5.0)
        assert _approx(r.props["y"], 0.0)

    def test_parallel_lines_returns_none(self):
        env = Environment()
        L1 = GeoShape("line", "L1", props={"a": 0.0, "b": 1.0, "c": 0.0})
        L2 = GeoShape("line", "L2", props={"a": 0.0, "b": 1.0, "c": -5.0})
        env.define("L1", L1)
        env.define("L2", L2)
        assert resolve_intersection(_shape("point", "P"), ["L1", "L2"], env) is None

    def test_line_circle_intersection(self):
        env = Environment()
        L = GeoShape("line", "L", props={"a": 1.0, "b": 0.0, "c": 0.0})
        C = GeoShape("circle", "C", props={"cx": 0.0, "cy": 0.0, "radius": 5.0})
        env.define("L", L)
        env.define("C", C)
        r = resolve_intersection(_shape("point", "P"), ["L", "C"], env)
        assert r is not None
        d = math.hypot(r.props["x"] - 0, r.props["y"] - 0)
        assert _approx(d, 5.0, tol=1e-4)


class TestResolvePerpendicularBisector:
    def test_bisector_of_horizontal_segment(self):
        env = Environment()
        seg = GeoShape(
            "segment", "AB", props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
        )
        env.define("AB", seg)
        r = resolve_perpendicular_bisector(_shape("line", "PB"), ["AB"], env)
        assert r is not None
        # Bisector should pass through midpoint (5, 0)
        a = r.props["a"]
        b = r.props["b"]
        c = r.props["c"]
        residual = a * 5.0 + b * 0.0 + c
        assert _approx(residual, 0.0)
        assert abs(r.props["b"]) < 1e-6


class TestResolveCircumAndIn:
    def setup_method(self):
        self.env = _env(("A", 0, 0), ("B", 4, 0), ("C", 0, 3))
        tri = GeoShape(
            "triangle",
            "T",
            props={
                "x1": 0.0,
                "y1": 0.0,
                "x2": 4.0,
                "y2": 0.0,
                "x3": 0.0,
                "y3": 3.0,
            },
        )
        self.env.define("T", tri)

    def test_circumcircle_all_vertices_on_circle(self):
        r = resolve_circumcircle(_shape("circle", "CC"), ["T"], self.env)
        assert r is not None
        cx, cy, radius = r.props["cx"], r.props["cy"], r.props["radius"]
        for x, y in [(0, 0), (4, 0), (0, 3)]:
            assert _approx(math.hypot(x - cx, y - cy), radius, tol=1e-4)

    def test_incircle_inside_triangle(self):
        r = resolve_incircle(_shape("circle", "IC"), ["T"], self.env)
        assert r is not None
        assert _approx(r.props["radius"], 1.0, tol=1e-4)


class TestResolveConvexHull:
    def test_square_hull(self):
        env = _env(("A", 0, 0), ("B", 1, 0), ("C", 1, 1), ("D", 0, 1))
        r = resolve_convex_hull(_shape("polygon", "H"), ["A", "B", "C", "D"], env)
        assert r is not None
        assert r.props["n"] == 4

    def test_interior_point_excluded(self):
        env = _env(("A", 0, 0), ("B", 2, 0), ("C", 2, 2), ("D", 0, 2), ("M", 1, 1))
        r = resolve_convex_hull(_shape("polygon", "H"), ["A", "B", "C", "D", "M"], env)
        assert r.props["n"] == 4


class TestTransformHelpers:
    def test_reflect_over_y_axis(self):
        p = np.array([3.0, 4.0])
        r = reflect_point_over_line(p, 1.0, 0.0, 0.0)
        assert _approx(r[0], -3.0)
        assert _approx(r[1], 4.0)

    def test_reflect_over_x_axis(self):
        p = np.array([3.0, 4.0])
        r = reflect_point_over_line(p, 0.0, 1.0, 0.0)
        assert _approx(r[0], 3.0)
        assert _approx(r[1], -4.0)

    def test_rotate_90_degrees(self):
        p = np.array([1.0, 0.0])
        center = np.array([0.0, 0.0])
        r = rotate_point_around(p, center, 90.0)
        assert _approx(r[0], 0.0)
        assert _approx(r[1], 1.0)

    def test_rotate_full_circle_returns_to_start(self):
        p = np.array([3.0, 7.0])
        center = np.array([1.0, 2.0])
        r = rotate_point_around(p, center, 360.0)
        assert _approx(r[0], p[0])
        assert _approx(r[1], p[1])

    def test_scale_from_origin(self):
        p = np.array([2.0, 3.0])
        center = np.array([0.0, 0.0])
        r = scale_point_from(p, center, 2.0)
        assert _approx(r[0], 4.0)
        assert _approx(r[1], 6.0)


class TestNumericPoint:
    def test_at_constraint_converges_exactly(self):
        s = _shape("point")
        s.constraints = [{"kind": "at", "targets": [(42.0, -7.0)]}]
        r = resolve_numeric(s, Environment())
        assert r is not None
        assert _approx(r.props["x"], 42.0)
        assert _approx(r.props["y"], -7.0)

    def test_on_circle_constraint(self):
        env = Environment()
        c = GeoShape("circle", "C", props={"cx": 0.0, "cy": 0.0, "radius": 10.0})
        env.define("C", c)
        s = _shape("point")
        s.constraints = [
            {"kind": "on", "targets": ["C"]},
            {"kind": "at", "targets": [(0.0, 10.0)]},
        ]
        r = resolve_numeric(s, env)
        assert r is not None
        d = math.hypot(r.props["x"], r.props["y"])
        assert _approx(d, 10.0, tol=1e-3)

    def test_distance_constraint(self):
        s = _shape("point")
        s.constraints = [
            {"kind": "distance", "ref_point": (0.0, 0.0), "value": 5.0},
            {"kind": "at", "targets": [(5.0, 0.0)]},
        ]
        r = resolve_numeric(s, Environment())
        assert r is not None
        d = math.hypot(r.props["x"], r.props["y"])
        assert _approx(d, 5.0, tol=1e-3)


class TestNumericCircle:
    def test_radius_constraint_honoured(self):
        s = _shape("circle")
        s.constraints = [{"kind": "radius", "value": 77.0}]
        r = resolve_numeric(s, Environment())
        assert r is not None
        assert _approx(r.props["radius"], 77.0, tol=1e-3)

    def test_tangent_to_line(self):
        env = Environment()
        L = GeoShape("line", "L", props={"a": 0.0, "b": 1.0, "c": 0.0})  # y=0
        env.define("L", L)
        s = _shape("circle")
        s.constraints = [
            {"kind": "tangent_to", "target": "L"},
            {"kind": "radius", "value": 30.0},
            {"kind": "at", "targets": [(0.0, 30.0)]},
        ]
        r = resolve_numeric(s, env)
        assert r is not None
        assert _approx(abs(r.props["cy"]), 30.0, tol=1e-2)


class TestNumericSegment:
    def test_length_constraint(self):
        s = _shape("segment")
        s.constraints = [{"kind": "length", "value": 80.0}]
        r = resolve_numeric(s, Environment())
        assert r is not None
        length = math.hypot(
            r.props["x2"] - r.props["x1"],
            r.props["y2"] - r.props["y1"],
        )
        assert _approx(length, 80.0, tol=1e-3)


class TestNumericTriangle:
    def test_area_constraint(self):
        s = _shape("triangle")
        s.constraints = [{"kind": "area", "value": 50.0}]
        r = resolve_numeric(s, Environment())
        assert r is not None
        p1 = np.array([r.props["x1"], r.props["y1"]])
        p2 = np.array([r.props["x2"], r.props["y2"]])
        p3 = np.array([r.props["x3"], r.props["y3"]])
        d1 = p2 - p1
        d2 = p3 - p1
        area = abs(d1[0] * d2[1] - d1[1] * d2[0]) / 2
        assert _approx(area, 50.0, tol=1e-2)


class TestGeoSolverPrimitive:
    def setup_method(self):
        self.solver = GeoSolver()
        self.env = Environment()

    def test_point_resolved_algebraically(self):
        s = _shape("point")
        s.constraints = [{"kind": "at", "targets": [(5.0, 5.0)]}]
        r = self.solver.resolve_primitive(s, self.env)
        assert _approx(r.props["x"], 5.0)

    def test_circle_resolved_algebraically(self):
        s = _shape("circle", radius=40.0)
        r = self.solver.resolve_primitive(s, self.env)
        assert _approx(r.props["radius"], 40.0)
        assert "cx" in r.props

    def test_unknown_kind_returns_stub(self):
        s = _shape("locus")
        r = self.solver.resolve_primitive(s, self.env)
        assert r is not None

    def test_apply_constraint_resolves_line_bisects(self):
        seg = GeoShape(
            "segment",
            "AB",
            props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0},
        )
        self.env.define("AB", seg)
        line = _shape("line")
        self.solver.apply_constraint(
            line, {"kind": "bisects", "target": "AB"}, self.env
        )
        assert _approx(line.props.get("a", 0.0), 0.0)
        assert _approx(line.props.get("b", 1.0), 1.0)
        assert _approx(line.props.get("c", 0.0), 0.0)


class TestGeoSolverDerived:
    def setup_method(self):
        self.solver = GeoSolver()
        self.env = _env(("A", 0, 0), ("B", 6, 0), ("C", 3, 4))
        tri = GeoShape(
            "triangle",
            "T",
            props={"x1": 0.0, "y1": 0.0, "x2": 6.0, "y2": 0.0, "x3": 3.0, "y3": 4.0},
        )
        self.env.define("T", tri)

        seg = GeoShape(
            "segment",
            "AB",
            props={"x1": 0.0, "y1": 0.0, "x2": 6.0, "y2": 0.0, "length": 6.0},
        )
        self.env.define("AB", seg)

    def _stmt(self, kind, name, args):

        class Stmt:
            pass

        s = Stmt()
        s.kind = kind
        s.name = name
        s.args = args
        s.locus_var = None
        s.locus_constraint = None
        return s

    def test_midpoint(self):
        r = self.solver.resolve_derived(
            self._stmt("midpoint", "M", ["A", "B"]), self.env
        )
        assert _approx(r.props["x"], 3.0)
        assert _approx(r.props["y"], 0.0)

    def test_circumcircle(self):
        r = self.solver.resolve_derived(
            self._stmt("circumcircle", "CC", ["T"]), self.env
        )
        assert r is not None
        assert r.kind == "circle"

    def test_incircle(self):
        r = self.solver.resolve_derived(self._stmt("incircle", "IC", ["T"]), self.env)
        assert r is not None
        assert r.kind == "circle"

    def test_perpendicular_bisector(self):
        r = self.solver.resolve_derived(
            self._stmt("perpendicular_bisector", "PB", ["AB"]), self.env
        )
        assert r is not None
        assert r.kind == "line"

    def test_locus_returns_stub(self):
        r = self.solver.resolve_derived(self._stmt("locus", None, []), self.env)
        assert r is not None
        assert r.kind == "locus"


class TestGeoSolverTransformations:
    def setup_method(self):
        self.solver = GeoSolver()
        self.env = Environment()
        self.axis = GeoShape("line", "L", props={"a": 1.0, "b": 0.0, "c": 0.0})  # x=0
        self.pivot = GeoShape("point", "O", props={"x": 0.0, "y": 0.0})

    def test_reflect_point_over_y_axis(self):
        pt = GeoShape("point", "P", props={"x": 3.0, "y": 4.0})
        r = self.solver.reflect(pt, self.axis, self.env)
        assert _approx(r.props["x"], -3.0)
        assert _approx(r.props["y"], 4.0)

    def test_rotate_point_90(self):
        pt = GeoShape("point", "P", props={"x": 1.0, "y": 0.0})
        r = self.solver.rotate(pt, 90.0, self.pivot, self.env)
        assert _approx(r.props["x"], 0.0, tol=1e-5)
        assert _approx(r.props["y"], 1.0, tol=1e-5)

    def test_scale_circle_radius(self):
        c = GeoShape("circle", "C", props={"cx": 0.0, "cy": 0.0, "radius": 10.0})
        r = self.solver.scale(c, 3.0, self.env)
        assert _approx(r.props["radius"], 30.0)

    def test_translate_segment(self):
        seg = GeoShape(
            "segment", "S", props={"x1": 0.0, "y1": 0.0, "x2": 5.0, "y2": 0.0}
        )
        r = self.solver.translate(seg, 10.0, 5.0, self.env)
        assert _approx(r.props["x1"], 10.0)
        assert _approx(r.props["y1"], 5.0)
        assert _approx(r.props["x2"], 15.0)

    def test_reflect_triangle(self):
        tri = GeoShape(
            "triangle",
            "T",
            props={
                "x1": 1.0,
                "y1": 0.0,
                "x2": 2.0,
                "y2": 0.0,
                "x3": 1.5,
                "y3": 1.0,
            },
        )
        r = self.solver.reflect(tri, self.axis, self.env)
        assert _approx(r.props["x1"], -1.0)
        assert _approx(r.props["x2"], -2.0)


class TestGeoSolverPredicates:
    def setup_method(self):
        self.solver = GeoSolver()
        self.env = Environment()

    def _def(self, shape):
        self.env.define(shape.name, shape)

    def test_point_on_circle_true(self):
        from ast_nodes.nodes import GeometricPred

        c = GeoShape("circle", "C", props={"cx": 0.0, "cy": 0.0, "radius": 5.0})
        pt = GeoShape("point", "P", props={"x": 5.0, "y": 0.0})
        self._def(c)
        self._def(pt)
        pred = GeometricPred(subject="P", relation="on", target="C")
        assert self.solver.check_predicate(pred, self.env) is True

    def test_point_not_on_circle(self):
        from ast_nodes.nodes import GeometricPred

        c = GeoShape("circle", "C", props={"cx": 0.0, "cy": 0.0, "radius": 5.0})
        pt = GeoShape("point", "P", props={"x": 3.0, "y": 0.0})
        self._def(c)
        self._def(pt)
        pred = GeometricPred(subject="P", relation="on", target="C")
        assert self.solver.check_predicate(pred, self.env) is False

    def test_point_on_segment(self):
        from ast_nodes.nodes import GeometricPred

        seg = GeoShape(
            "segment", "S", props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
        )
        pt = GeoShape("point", "P", props={"x": 5.0, "y": 0.0})
        self._def(seg)
        self._def(pt)
        pred = GeometricPred(subject="P", relation="on", target="S")
        assert self.solver.check_predicate(pred, self.env) is True

    def test_point_off_segment(self):
        from ast_nodes.nodes import GeometricPred

        seg = GeoShape(
            "segment", "S", props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
        )
        pt = GeoShape("point", "P", props={"x": 5.0, "y": 1.0})
        self._def(seg)
        self._def(pt)
        pred = GeometricPred(subject="P", relation="on", target="S")
        assert self.solver.check_predicate(pred, self.env) is False

    def test_parallel_lines(self):
        from ast_nodes.nodes import GeometricPred

        L1 = GeoShape("line", "L1", props={"a": 0.0, "b": 1.0, "c": 0.0})
        L2 = GeoShape("line", "L2", props={"a": 0.0, "b": 1.0, "c": -5.0})
        self._def(L1)
        self._def(L2)
        pred = GeometricPred(subject="L1", relation="parallel_to", target="L2")
        assert self.solver.check_predicate(pred, self.env) is True

    def test_perpendicular_lines(self):
        from ast_nodes.nodes import GeometricPred

        L1 = GeoShape("line", "L1", props={"a": 1.0, "b": 0.0, "c": 0.0})
        L2 = GeoShape("line", "L2", props={"a": 0.0, "b": 1.0, "c": 0.0})
        self._def(L1)
        self._def(L2)
        pred = GeometricPred(subject="L1", relation="perpendicular_to", target="L2")
        assert self.solver.check_predicate(pred, self.env) is True

    def test_external_tangency(self):
        from ast_nodes.nodes import GeometricPred

        C1 = GeoShape("circle", "C1", props={"cx": 0.0, "cy": 0.0, "radius": 3.0})
        C2 = GeoShape("circle", "C2", props={"cx": 8.0, "cy": 0.0, "radius": 5.0})
        self._def(C1)
        self._def(C2)
        pred = GeometricPred(subject="C1", relation="tangent_to", target="C2")
        assert self.solver.check_predicate(pred, self.env) is True

    def test_bisects_segment(self):
        from ast_nodes.nodes import GeometricPred

        L = GeoShape("line", "L", props={"a": 1.0, "b": 0.0, "c": -5.0})
        seg = GeoShape(
            "segment", "S", props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
        )
        self._def(L)
        self._def(seg)
        pred = GeometricPred(subject="L", relation="bisects", target="S")
        assert self.solver.check_predicate(pred, self.env) is True

    def test_bisects_segment_ray(self):
        from ast_nodes.nodes import GeometricPred

        seg = GeoShape(
            "segment", "S", props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
        )
        R = GeoShape(
            "ray",
            "R",
            props={"ox": 5.0, "oy": -1.0, "dx": 0.0, "dy": 1.0},
        )
        self._def(seg)
        self._def(R)
        pred = GeometricPred(subject="R", relation="bisects", target="S")
        assert self.solver.check_predicate(pred, self.env) is True

    def test_passes_through(self):
        from ast_nodes.nodes import GeometricPred

        L = GeoShape("line", "L", props={"a": 0.0, "b": 1.0, "c": 0.0})
        pt = GeoShape("point", "P", props={"x": 7.0, "y": 0.0})
        self._def(L)
        self._def(pt)
        pred = GeometricPred(subject="L", relation="passes_through", target="P")
        assert self.solver.check_predicate(pred, self.env) is True

    def test_centered_at(self):
        from ast_nodes.nodes import GeometricPred

        C = GeoShape("circle", "C", props={"cx": 3.0, "cy": 4.0, "radius": 5.0})
        pt = GeoShape("point", "O", props={"x": 3.0, "y": 4.0})
        self._def(C)
        self._def(pt)
        pred = GeometricPred(subject="C", relation="centered_at", target="O")
        assert self.solver.check_predicate(pred, self.env) is True


class TestPointOnEdges:
    def test_midpoint_of_segment(self):
        seg = GeoShape(
            "segment", "S", props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
        )
        assert GeoSolver._point_on_edges(5.0, 0.0, seg) is True

    def test_endpoint_on_segment(self):
        seg = GeoShape(
            "segment", "S", props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
        )
        assert GeoSolver._point_on_edges(0.0, 0.0, seg) is True
        assert GeoSolver._point_on_edges(10.0, 0.0, seg) is True

    def test_off_segment_collinear_but_beyond(self):
        seg = GeoShape(
            "segment", "S", props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0}
        )
        assert GeoSolver._point_on_edges(15.0, 0.0, seg) is False

    def test_point_on_triangle_edge(self):
        tri = GeoShape(
            "triangle",
            "T",
            props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "x3": 5.0, "y3": 8.0},
        )
        assert GeoSolver._point_on_edges(5.0, 0.0, tri) is True

    def test_interior_point_not_on_edge(self):
        tri = GeoShape(
            "triangle",
            "T",
            props={"x1": 0.0, "y1": 0.0, "x2": 10.0, "y2": 0.0, "x3": 5.0, "y3": 8.0},
        )
        assert GeoSolver._point_on_edges(5.0, 2.0, tri) is False
