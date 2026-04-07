from __future__ import annotations
import math
from typing import Any, Dict, List, Optional, Tuple

from .environment import Environment
from .errors import (
    GeoArgumentError,
    GeoAssertionError,
    GeoConstraintError,
    GeoDivisionByZero,
    GeoNameError,
    GeoRuntimeError,
    GeoTypeError,
    ReturnSignal,
)

# stores a point with x and y
class GeoPoint:
    __slots__ = ("name", "x", "y")

    def __init__(self, name: str, x: float, y: float) -> None:
        self.name = name
        self.x = x
        self.y = y


# stores any geometric shape
class GeoShape:
    __slots__ = ("kind", "name", "props", "constraints", "points")

    def __init__(
        self,
        kind: str,
        name: str,
        props: Optional[Dict[str, Any]] = None,
        constraints: Optional[List[Any]] = None,
        points: Optional[List[GeoPoint]] = None,
    ) -> None:
        self.kind = kind
        self.name = name
        self.props = props or {}
        self.constraints = constraints or []
        self.points = points or []


# stores user defined function
class UserFunction:
    __slots__ = ("name", "params", "body", "closure")

    def __init__(
        self,
        name: str,
        params: List[str],
        body: List[Any],
        closure: Environment,
    ) -> None:
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure


# main interpreter class
class Interpreter:

    # initialize everything
    def __init__(self, geometry_backend: Optional[Any] = None) -> None:
        self.env: Environment = Environment()

        # store constant pi
        self.env.define("pi", math.pi)

        # store shapes created
        self.shapes: List[Tuple[str, GeoShape]] = []

        # store labels
        self.labels: Dict[str, str] = {}

        # hidden shapes
        self.hidden: set[str] = set()

        # notes
        self.notes: List[str] = []

        # grid flag
        self.show_grid: bool = False

        # assertion tracking
        self.assertions_passed: int = 0
        self.assertions_failed: List[str] = []

        self._backend = geometry_backend

    # run all statements
    def run(self, program: Any) -> Environment:
        try:
            for stmt in program.statements:
                self._exec(stmt, self.env)
        except ReturnSignal:
            raise GeoRuntimeError("return used outside function")
        return self.env

    # execute one statement
    def _exec(self, stmt: Any, env: Environment) -> None:

        # variable declaration
        if hasattr(stmt, "name") and hasattr(stmt, "value"):
            val = self._eval(stmt.value, env)
            env.define(stmt.name, val)

        # ignore unknown for now
        else:
            pass

    # evaluate expressions
    def _eval(self, expr: Any, env: Environment) -> Any:

        # number
        if hasattr(expr, "value") and isinstance(expr.value, (int, float)):
            return expr.value

        # variable
        if hasattr(expr, "name"):
            return env.get(expr.name)

        return None

    # binary operations
    def _eval_binop(self, left: Any, right: Any, op: str) -> float:
        try:
            l = float(left)
            r = float(right)
        except (TypeError, ValueError):
            raise GeoTypeError("invalid operands")

        if op == "+":
            return l + r
        if op == "-":
            return l - r
        if op == "*":
            return l * r
        if op == "/":
            if r == 0:
                raise GeoDivisionByZero()
            return l / r

        raise GeoRuntimeError("unknown operator")

    # simple function call
    def _call_function(
        self,
        name: str,
        func_val: Any,
        args: List[Any],
        env: Environment,
    ) -> Any:
        if not isinstance(func_val, UserFunction):
            raise GeoTypeError(f"{name} is not a function")

        if len(args) != len(func_val.params):
            raise GeoArgumentError(name, len(func_val.params), len(args))

        call_env = func_val.closure.child()

        for pname, pval in zip(func_val.params, args):
            call_env.define(pname, pval)

        try:
            for stmt in func_val.body:
                self._exec(stmt, call_env)
        except ReturnSignal as ret:
            return ret.value

        return None


# helper function to run interpreter
def interpret(
    program: Any,
    geometry_backend: Optional[Any] = None,
) -> Tuple[Interpreter, Environment]:

    interp = Interpreter(geometry_backend)
    env = interp.run(program)
    return interp, env
