from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

if TYPE_CHECKING:
    from ast_nodes.nodes import BoolExpr, Program
    from interpreter.environment import Environment
    from interpreter.interpreter import GeoShape


@dataclass
class SweepFrame:
    param_name: str
    param_value: float
    shapes: List[Tuple[str, "GeoShape"]]
    env: "Environment"


@dataclass
class LocusResult:
    var_name: str
    points: List[Tuple[float, float]]  # (x, y) of each satisfying position
    shape_name: Optional[str] = None


@dataclass
class ForResult:
    var_name: str
    frames: List[Dict[str, "GeoShape"]] = field(default_factory=list)


class Evaluator:
    def __init__(self, interpreter_factory: Any) -> None:
        self._factory = interpreter_factory

    # Public API

    def run_sweep(
        self,
        program: "Program",
        param_name: str,
        base_env: Optional["Environment"] = None,
    ) -> List[SweepFrame]:
        # Step 1: discovery run
        discovery = self._factory()
        discovery.run(program)
        if not discovery.env.is_defined(param_name):
            raise ValueError(f"param '{param_name}' is not declared in the program")
        start, end, step = discovery.env.get_param_range(param_name)

        frames: List[SweepFrame] = []
        v = start
        while (step > 0 and v <= end + 1e-9) or (step < 0 and v >= end - 1e-9):
            frame_interp = self._factory()

            frame_interp.env.define(param_name, round(v, 10), mutable=True)
            frame_interp.env.define(f"__param_{param_name}_start", start)
            frame_interp.env.define(f"__param_{param_name}_end", end)
            frame_interp.env.define(f"__param_{param_name}_step", step)

            frame_interp.run(program)

            frames.append(
                SweepFrame(
                    param_name=param_name,
                    param_value=round(v, 10),
                    shapes=frame_interp.shapes,
                    env=frame_interp.env,
                )
            )
            v = round(v + step, 10)

        return frames

    def run_locus(
        self,
        program: "Program",
        locus_var: str,
        constraint: "BoolExpr",
        x_range: Tuple[float, float, float],
        y_range: Tuple[float, float, float],
        shape_name: Optional[str] = None,
    ) -> LocusResult:

        context_interp = self._factory()
        context_interp.run(program)
        context_env = context_interp.env

        points: List[Tuple[float, float]] = []

        x_start, x_end, x_step = x_range
        y_start, y_end, y_step = y_range
        tolerance = self._locus_tolerance(x_step, y_step)

        px = x_start
        while px <= x_end + 1e-9:
            py = y_start
            while py <= y_end + 1e-9:
                test_env = context_env.child()
                from interpreter.interpreter import GeoShape

                pt_shape = GeoShape("point", locus_var, props={"x": px, "y": py})
                test_env.define(locus_var, pt_shape)

                try:
                    satisfied = self._eval_locus_constraint(
                        context_interp, constraint, test_env, tolerance, locus_var
                    )
                except Exception:
                    satisfied = False

                if satisfied:
                    points.append((round(px, 8), round(py, 8)))

                py = round(py + y_step, 10)
            px = round(px + x_step, 10)

        return LocusResult(
            var_name=locus_var,
            points=points,
            shape_name=shape_name,
        )

    def _locus_tolerance(self, x_step: float, y_step: float) -> float:
        """Choose a tolerance for approximate locus equality tests."""
        tol = math.hypot(x_step, y_step) * 1.25
        return max(tol, 0.5)

    def _expr_uses_locus_var(self, expr: Any, locus_var: str) -> bool:
        from ast_nodes.nodes import CallExpr, IdentExpr

        if isinstance(expr, IdentExpr):
            return expr.name == locus_var
        if isinstance(expr, CallExpr):
            return any(self._expr_uses_locus_var(arg, locus_var) for arg in expr.args)
        if hasattr(expr, "left") and hasattr(expr, "right"):
            return self._expr_uses_locus_var(
                expr.left, locus_var
            ) or self._expr_uses_locus_var(expr.right, locus_var)
        if hasattr(expr, "operand"):
            return self._expr_uses_locus_var(expr.operand, locus_var)
        if hasattr(expr, "x") and hasattr(expr, "y"):
            return self._expr_uses_locus_var(
                expr.x, locus_var
            ) or self._expr_uses_locus_var(expr.y, locus_var)
        return False

    def _eval_locus_constraint(
        self,
        interp: Any,
        constraint: Any,
        env: "Environment",
        tolerance: float,
        locus_var: str,
    ) -> bool:
        from ast_nodes.nodes import CmpExpr

        if isinstance(constraint, CmpExpr) and constraint.op in ("=", "==", "!="):
            if not (
                self._expr_uses_locus_var(constraint.left, locus_var)
                or self._expr_uses_locus_var(constraint.right, locus_var)
            ):
                return interp._eval_bool(constraint, env)

            left = interp._eval(constraint.left, env)
            right = interp._eval(constraint.right, env)
            try:
                left_val = float(left)
                right_val = float(right)
            except (TypeError, ValueError):
                return interp._eval_bool(constraint, env)

            if constraint.op in ("=", "=="):
                return abs(left_val - right_val) <= tolerance
            return abs(left_val - right_val) > tolerance

        return interp._eval_bool(constraint, env)

    def run_for(
        self,
        program: "Program",
        var_name: str,
        values: List[Any],
    ) -> ForResult:
        result = ForResult(var_name=var_name)

        for val in values:
            frame_interp = self._factory()
            frame_interp.env.define(var_name, val)
            frame_interp.run(program)
            result.frames.append(dict(frame_interp.shapes))

        return result

    def animation_frames(
        self,
        program: "Program",
        param_name: str,
    ) -> List[Dict[str, Any]]:
        frames = self.run_sweep(program, param_name)
        return [
            {
                "param": f.param_value,
                "shapes": {name: _serialise_shape(s) for name, s in f.shapes.items()},
            }
            for f in frames
        ]


def _serialise_shape(shape: "GeoShape") -> Dict[str, Any]:
    return {
        "kind": shape.kind,
        "name": shape.name,
        "props": {
            k: v
            for k, v in shape.props.items()
            if isinstance(v, (int, float, str, bool))
        },
    }
