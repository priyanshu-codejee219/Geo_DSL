import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from evaluator.evaluator import Evaluator, ForResult, LocusResult, SweepFrame
from interpreter.environment import Environment
from interpreter.interpreter import Interpreter
from lexer.lexer import Lexer
from parser.parser import parse


def _parse(source: str):
    tokens = Lexer(source).tokenize()
    return parse(tokens)


def _factory():
    return Interpreter(geometry_backend=None)


def _evaluator() -> Evaluator:
    return Evaluator(_factory)


def _approx(a: float, b: float, tol: float = 1e-9) -> bool:
    return abs(a - b) < tol


class TestDataclasses:
    def test_sweep_frame_fields(self):
        env = Environment()
        sf = SweepFrame(param_name="t", param_value=1.0, shapes={}, env=env)
        assert sf.param_name == "t"
        assert sf.param_value == 1.0
        assert sf.shapes == {}

    def test_locus_result_defaults(self):
        lr = LocusResult(var_name="P", points=[(1.0, 2.0)])
        assert lr.shape_name is None
        assert lr.points[0] == (1.0, 2.0)

    def test_for_result_default_frames(self):
        fr = ForResult(var_name="k")
        assert fr.frames == []


class TestRunSweep:
    def test_frame_count_matches_range(self):
        program = _parse("""
param t from 0 to 4 step 1
""")
        ev = _evaluator()
        frames = ev.run_sweep(program, "t")
        # 0, 1, 2, 3, 4  →  5 frames
        assert len(frames) == 5

    def test_frame_param_values_correct(self):
        program = _parse("""
param t from 0 to 2 step 1
""")
        frames = _evaluator().run_sweep(program, "t")
        values = [f.param_value for f in frames]
        assert values == [0.0, 1.0, 2.0]

    def test_fractional_step(self):
        program = _parse("""
param t from 0 to 1 step 0.5
""")
        frames = _evaluator().run_sweep(program, "t")
        assert len(frames) == 3
        assert _approx(frames[1].param_value, 0.5)

    def test_single_step_range(self):
        program = _parse("""
param t from 10 to 10 step 1
""")
        frames = _evaluator().run_sweep(program, "t")
        assert len(frames) == 1
        assert _approx(frames[0].param_value, 10.0)

    def test_undeclared_param_raises(self):
        program = _parse("""
param t from 0 to 5 step 1
""")
        with pytest.raises(ValueError, match="not declared"):
            _evaluator().run_sweep(program, "angle")

    def test_each_frame_is_sweep_frame_instance(self):
        program = _parse("""
param t from 0 to 2 step 1
""")
        frames = _evaluator().run_sweep(program, "t")
        for f in frames:
            assert isinstance(f, SweepFrame)

    def test_param_name_recorded_in_frame(self):
        program = _parse("""
param theta from 0 to 90 step 45
""")
        frames = _evaluator().run_sweep(program, "theta")
        for f in frames:
            assert f.param_name == "theta"

    def test_shapes_dict_present_per_frame(self):
        program = _parse("""
param t from 0 to 1 step 1
point A at (0, 0)
""")
        frames = _evaluator().run_sweep(program, "t")
        for f in frames:
            assert isinstance(f.shapes, dict)

    def test_let_depends_on_param(self):
        program = _parse("""
param t from 1 to 3 step 1
let r = t
""")
        frames = _evaluator().run_sweep(program, "t")
        for f in frames:
            r_val = f.env.get("r")
            assert _approx(float(r_val), f.param_value)

    def test_env_per_frame_is_independent(self):
        program = _parse("""
param t from 0 to 1 step 1
""")
        frames = _evaluator().run_sweep(program, "t")
        # Set a value in frame 0's env
        frames[0].env.define("marker", 999)
        # frame 1 should not see it
        assert not frames[1].env.is_defined("marker")


class TestRunLocus:
    def _circle_constraint(self):
        from ast_nodes.nodes import BinOp, CmpExpr, IdentExpr, NumberLiteral

        x_sq = BinOp("*", IdentExpr("__P_x"), IdentExpr("__P_x"))
        y_sq = BinOp("*", IdentExpr("__P_y"), IdentExpr("__P_y"))
        lhs = BinOp("+", x_sq, y_sq)
        return CmpExpr("=", lhs, NumberLiteral(100.0))

    def test_locus_returns_locus_result(self):
        from ast_nodes.nodes import CmpExpr, NumberLiteral

        constraint = CmpExpr("=", NumberLiteral(1.0), NumberLiteral(1.0))
        program = _parse("point A at (0, 0)")
        ev = _evaluator()
        result = ev.run_locus(
            program,
            locus_var="P",
            constraint=constraint,
            x_range=(0.0, 2.0, 1.0),
            y_range=(0.0, 2.0, 1.0),
        )
        assert isinstance(result, LocusResult)
        assert result.var_name == "P"

    def test_always_true_constraint_captures_all_grid_points(self):
        from ast_nodes.nodes import CmpExpr, NumberLiteral

        constraint = CmpExpr("=", NumberLiteral(1.0), NumberLiteral(1.0))
        program = _parse("point A at (0, 0)")
        result = _evaluator().run_locus(
            program,
            locus_var="P",
            constraint=constraint,
            x_range=(0.0, 2.0, 1.0),
            y_range=(0.0, 2.0, 1.0),
        )
        assert len(result.points) == 9

    def test_always_false_constraint_captures_no_points(self):
        from ast_nodes.nodes import CmpExpr, NumberLiteral

        constraint = CmpExpr("=", NumberLiteral(1.0), NumberLiteral(2.0))
        program = _parse("point A at (0, 0)")
        result = _evaluator().run_locus(
            program,
            locus_var="P",
            constraint=constraint,
            x_range=(-5.0, 5.0, 1.0),
            y_range=(-5.0, 5.0, 1.0),
        )
        assert len(result.points) == 0

    def test_shape_name_attached(self):
        from ast_nodes.nodes import CmpExpr, NumberLiteral

        constraint = CmpExpr("=", NumberLiteral(1.0), NumberLiteral(1.0))
        program = _parse("point A at (0, 0)")
        result = _evaluator().run_locus(
            program,
            locus_var="P",
            constraint=constraint,
            x_range=(0.0, 1.0, 1.0),
            y_range=(0.0, 1.0, 1.0),
            shape_name="my_locus",
        )
        assert result.shape_name == "my_locus"

    def test_points_are_tuples_of_floats(self):
        from ast_nodes.nodes import CmpExpr, NumberLiteral

        constraint = CmpExpr("=", NumberLiteral(1.0), NumberLiteral(1.0))
        program = _parse("point A at (0, 0)")
        result = _evaluator().run_locus(
            program,
            locus_var="P",
            constraint=constraint,
            x_range=(0.0, 1.0, 1.0),
            y_range=(0.0, 1.0, 1.0),
        )
        for pt in result.points:
            assert isinstance(pt, tuple)
            assert len(pt) == 2
            assert isinstance(pt[0], float)
            assert isinstance(pt[1], float)

    def test_distance_function_call_works_in_locus_constraint(self):
        from ast_nodes.nodes import BinOp, CallExpr, CmpExpr, IdentExpr, NumberLiteral

        program = _parse("point A at (0, 0)\npoint B at (100, 0)")
        lhs = BinOp(
            "+",
            CallExpr("distance", [IdentExpr("P"), IdentExpr("A")]),
            CallExpr("distance", [IdentExpr("P"), IdentExpr("B")]),
        )
        constraint = CmpExpr("=", lhs, NumberLiteral(200.0))

        result = _evaluator().run_locus(
            program,
            locus_var="P",
            constraint=constraint,
            x_range=(-100.0, 200.0, 10.0),
            y_range=(-50.0, 50.0, 10.0),
        )

        assert (-50.0, 0.0) in result.points
        assert (150.0, 0.0) in result.points
        assert len(result.points) >= 2

    def test_distance_locus_uses_tolerance_to_approximate_ellipse(self):
        from ast_nodes.nodes import BinOp, CallExpr, CmpExpr, IdentExpr, NumberLiteral

        program = _parse("point A at (0, 0)\npoint B at (100, 0)")
        lhs = BinOp(
            "+",
            CallExpr("distance", [IdentExpr("P"), IdentExpr("A")]),
            CallExpr("distance", [IdentExpr("P"), IdentExpr("B")]),
        )
        constraint = CmpExpr("=", lhs, NumberLiteral(200.0))

        result = _evaluator().run_locus(
            program,
            locus_var="P",
            constraint=constraint,
            x_range=(-100.0, 100.0, 10.0),
            y_range=(-50.0, 50.0, 10.0),
        )

        assert len(result.points) > 8
        assert any(abs(y) > 1e-6 for x, y in result.points)


class TestRunFor:
    def test_frame_count_equals_value_list_length(self):
        program = _parse("point A at (0, 0)")
        result = _evaluator().run_for(program, "k", [1.0, 2.0, 3.0])
        assert isinstance(result, ForResult)
        assert len(result.frames) == 3

    def test_empty_value_list(self):
        program = _parse("point A at (0, 0)")
        result = _evaluator().run_for(program, "k", [])
        assert len(result.frames) == 0

    def test_var_name_stored(self):
        program = _parse("point A at (0, 0)")
        result = _evaluator().run_for(program, "angle", [0.0])
        assert result.var_name == "angle"

    def test_frames_are_dicts(self):
        program = _parse("point A at (0, 0)")
        result = _evaluator().run_for(program, "k", [1.0, 2.0])
        for frame in result.frames:
            assert isinstance(frame, dict)


# ─────────────────────────────────────────────────────────────────────────────
# animation_frames — JSON serialisation
# ─────────────────────────────────────────────────────────────────────────────


class TestAnimationFrames:
    def test_returns_list_of_dicts(self):
        program = _parse("""
param t from 0 to 2 step 1
""")
        frames = _evaluator().animation_frames(program, "t")
        assert isinstance(frames, list)
        for f in frames:
            assert "param" in f
            assert "shapes" in f

    def test_param_values_in_order(self):
        program = _parse("""
param t from 0 to 2 step 1
""")
        frames = _evaluator().animation_frames(program, "t")
        params = [f["param"] for f in frames]
        assert params == [0.0, 1.0, 2.0]

    def test_shapes_are_serialisable(self):
        import json

        program = _parse("""
param t from 0 to 1 step 1
point A at (0, 0)
""")
        frames = _evaluator().animation_frames(program, "t")
        # If this doesn't raise, all values are JSON-safe
        for f in frames:
            json.dumps(f)

    def test_shape_dict_has_kind_and_name(self):
        program = _parse("""
param t from 0 to 0 step 1
point A at (0, 0)
""")
        frames = _evaluator().animation_frames(program, "t")
        shapes = frames[0]["shapes"]
        assert "A" in shapes
        assert shapes["A"]["kind"] == "point"
        assert shapes["A"]["name"] == "A"


class TestEdgeCases:
    def test_sweep_with_no_shapes_still_produces_frames(self):
        program = _parse("""
param t from 0 to 3 step 1
""")
        frames = _evaluator().run_sweep(program, "t")
        assert len(frames) == 4
        for f in frames:
            assert f.shapes == {}

    def test_multiple_params_sweep_one(self):
        program = _parse("""
param t from 0 to 2 step 1
param r from 10 to 10 step 1
""")
        frames = _evaluator().run_sweep(program, "t")
        assert len(frames) == 3
        for f in frames:
            assert _approx(float(f.env.get("r")), 10.0)

    def test_factory_called_fresh_per_frame(self):
        call_count = [0]
        original_factory = _factory

        def counting_factory():
            call_count[0] += 1
            return original_factory()

        ev = Evaluator(counting_factory)
        program = _parse("param t from 0 to 2 step 1")
        ev.run_sweep(program, "t")
        assert call_count[0] == 4
