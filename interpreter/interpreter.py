from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

from ast_nodes.nodes import (
    AngleLiteral,
    AngleMeasure,
    AreaMeasure,
    AssertStmt,
    BinOp,
    CallExpr,
    CallStmt,
    CmpExpr,
    ConstraintStmt,
    DefineStmt,
    DerivedDecl,
    DistanceMeasure,
    ForStmt,
    GeometricPred,
    GridStmt,
    HideStmt,
    IdentExpr,
    IfStmt,
    LabelStmt,
    LengthMeasure,
    LetStmt,
    MeasureStmt,
    NoteStmt,
    NumberLiteral,
    ParamStmt,
    PerimeterMeasure,
    PosConstraint,
    PrimitiveDecl,
    Program,
    RadiusMeasure,
    RatioLiteral,
    RatioMeasure,
    ReflectStmt,
    RelConstraint,
    ReturnStmt,
    RotateStmt,
    ScaleStmt,
    SetStmt,
    Statement,
    StringLiteral,
    SweepStmt,
    TranslateStmt,
    UnaryOp,
    VectorExpr,
)

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


# a point in 2D space with a name, x, and y
# using __slots__ here because point objects are created a lot and this saves memory
class GeoPoint:
    __slots__ = ("name", "x", "y")

    def __init__(self, name: str, x: float, y: float) -> None:
        self.name = name
        self.x = x
        self.y = y

    def __repr__(self) -> str:
        return f"GeoPoint({self.name!r}, x={self.x}, y={self.y})"


#generate container the shapes of any type and also props= numeric properties like radius and length
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

    def __repr__(self) -> str:
        return f"GeoShape({self.kind!r}, {self.name!r}, props={self.props})"



class UserFunction:
    __slots__ = ("name", "params", "body", "closure")

    def __init__(
        self,
        name: str,
        params: List[str],
        body: List[Statement],
        closure: Environment,
    ) -> None:
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure  # lexical closure, not dynamic

    def __repr__(self) -> str:
        return f"<UserFunction {self.name}({', '.join(self.params)})>"


# main interpreter class
class Interpreter:

    def __init__(self, geometry_backend: Optional[Any] = None) -> None:
        self.env: Environment = Environment()
        self.env.define("pi", math.pi)
        # shapes list stores (name, shape) pairs so duplicates can exist
        self.shapes: List[Tuple[str, GeoShape]] = []
        self.labels: Dict[str, str] = {}  
        self.hidden: set = set()          
        self.notes: List[str] = []        
        self.show_grid: bool = False
        self.assertions_passed: int = 0
        self.assertions_failed: List[str] = []
        self._backend = geometry_backend

    def run(self, program: Program) -> Environment:
       
        try:
            for stmt in program.statements:
                self._exec(stmt, self.env)
        except ReturnSignal:
            raise GeoRuntimeError("'return' used outside of a 'define' function body")
        return self.env

    def run_sweep(
        self, program: Program, param_name: str
    ) -> List[Tuple[float, Environment]]:
        # strip sweep statements so they don't re-advance the param each frame
        replay_program = self._strip_sweep_statements(program)

        # first pass just to collect the param declaration
        self.run(replay_program)
        if not self.env.is_defined(param_name):
            raise GeoNameError(param_name)

        start, end, step = self.env.get_param_range(param_name)
        frames: List[Tuple[float, Environment]] = []

        v = start
        while (step > 0 and v <= end + 1e-9) or (step < 0 and v >= end - 1e-9):
            # snapshot preserves mutability flags and param metadata
            frame_env = self.env.snapshot()

            # set the param value before re-running so dependent lets see it
            frame_env.set(param_name, round(v, 10))

            frame_interp = Interpreter(self._backend)
            frame_interp.env = frame_env
            frame_interp.run(replay_program)

            frames.append((round(v, 10), frame_interp.env))
            v = round(v + step, 10)

        return frames

    # returns a copy of the program with all top-level sweep statements removed
    def _strip_sweep_statements(self, program: Program) -> Program:
        return Program(
            statements=[s for s in program.statements if not isinstance(s, SweepStmt)]
        )

    # dispatch a single statement to the right handler based on its type
    def _exec(self, stmt: Statement, env: Environment) -> None:

        # shape declarations
        if isinstance(stmt, PrimitiveDecl):
            self._exec_primitive(stmt, env)
        elif isinstance(stmt, DerivedDecl):
            self._exec_derived(stmt, env)

        # constraint
        elif isinstance(stmt, ConstraintStmt):
            self._exec_constraint_stmt(stmt, env)

        # measure statements - each one stores a named value in the env
        elif isinstance(stmt, DistanceMeasure):
            self._exec_distance_measure(stmt, env)
        elif isinstance(stmt, AngleMeasure):
            self._exec_angle_measure(stmt, env)
        elif isinstance(stmt, LengthMeasure):
            self._exec_length_measure(stmt, env)
        elif isinstance(stmt, RadiusMeasure):
            self._exec_radius_measure(stmt, env)
        elif isinstance(stmt, RatioMeasure):
            self._exec_ratio_measure(stmt, env)
        elif isinstance(stmt, AreaMeasure):
            self._exec_area_measure(stmt, env)
        elif isinstance(stmt, PerimeterMeasure):
            self._exec_perimeter_measure(stmt, env)

        # variable declarations and updates
        elif isinstance(stmt, LetStmt):
            self._exec_let(stmt, env)
        elif isinstance(stmt, SetStmt):
            self._exec_set(stmt, env)
        elif isinstance(stmt, ParamStmt):
            self._exec_param(stmt, env)

        # control flow
        elif isinstance(stmt, SweepStmt):
            self._exec_sweep(stmt, env)
        elif isinstance(stmt, IfStmt):
            self._exec_if(stmt, env)
        elif isinstance(stmt, ForStmt):
            self._exec_for(stmt, env)

        # function definition, call, and return
        elif isinstance(stmt, DefineStmt):
            self._exec_define(stmt, env)
        elif isinstance(stmt, CallStmt):
            self._exec_call(stmt, env)
        elif isinstance(stmt, ReturnStmt):
            raise ReturnSignal(
                self._eval(stmt.value, env) if stmt.value is not None else None
            )

        # geometric transformations
        elif isinstance(stmt, ReflectStmt):
            self._exec_reflect(stmt, env)
        elif isinstance(stmt, RotateStmt):
            self._exec_rotate(stmt, env)
        elif isinstance(stmt, ScaleStmt):
            self._exec_scale(stmt, env)
        elif isinstance(stmt, TranslateStmt):
            self._exec_translate(stmt, env)

        # assertions
        elif isinstance(stmt, AssertStmt):
            self._exec_assert(stmt, env)

        # display / rendering hints - just record them for the renderer
        elif isinstance(stmt, LabelStmt):
            self.labels[stmt.target] = stmt.text
        elif isinstance(stmt, NoteStmt):
            self.notes.append(stmt.text)
        elif isinstance(stmt, HideStmt):
            self.hidden.update(stmt.targets)
        elif isinstance(stmt, GridStmt):
            self.show_grid = True
        elif isinstance(stmt, MeasureStmt):
            pass  # dimension lines are drawn by the renderer, not the interpreter
        else:
            raise GeoRuntimeError(f"Unknown statement type: {type(stmt).__name__}")

    # declare a primitive shape like point, circle, line, triangle
    def _exec_primitive(self, stmt: PrimitiveDecl, env: Environment) -> None:
        kind = stmt.shape_kw.name.lower()
        name = stmt.name

        # evaluate all property assignments into a plain dict
        props: Dict[str, Any] = {}
        for pa in stmt.props:
            props[pa.name] = self._eval(pa.value, env)

        if stmt.args:
            props["args"] = list(stmt.args)

        shape = GeoShape(kind, name, props=props)

        for clause in stmt.constraints:
            if isinstance(clause, PosConstraint) and clause.kind == "at":
                if kind == "point":
                    target = self._eval(clause.targets[0], env)
                    if isinstance(target, (tuple, list)) and len(target) == 2:
                        shape.props.setdefault("x", float(target[0]))
                        shape.props.setdefault("y", float(target[1]))
            clause_data = self._eval_constraint_clause(clause, env)
            shape.constraints.append(clause_data)

        # ask the backend to resolve/place the shape if one is attached
        if self._backend is not None:
            resolved = self._backend.resolve_primitive(shape, env)
            if resolved is None:
                raise GeoConstraintError(f"Could not resolve primitive shape '{name}'")
            shape = resolved

        self.shapes.append((name, shape))
        env.define(name, shape)

    # declare a derived construction like midpoint, circumcircle, or locus
    def _exec_derived(self, stmt: DerivedDecl, env: Environment) -> None:
        kind = stmt.kind
        name = stmt.name  # can be None for anonymous locus constructions

        if self._backend is not None:
            result = self._backend.resolve_derived(stmt, env)
            if result is None:
                raise GeoConstraintError(
                    f"Could not resolve derived shape '{name or stmt.kind}'"
                )
            self.shapes.append((result.name, result))
            env.define(result.name, result)
            return

        # no backend - store as a stub so the name is still usable
        stub = GeoShape(kind, name or f"_locus_{id(stmt)}", props={"args": stmt.args})
        self.shapes.append((stub.name, stub))
        env.define(stub.name, stub)

    # handle a standalone constraint statement like "AB parallel_to CD"
    def _exec_constraint_stmt(self, stmt: ConstraintStmt, env: Environment) -> None:
        shape_val = env.get(stmt.subject)
        clause = self._eval_constraint_clause(stmt.constraint, env)

        if isinstance(shape_val, GeoShape):
            shape_val.constraints.append(clause)
            if self._backend is not None:
                self._backend.apply_constraint(shape_val, clause, env)

    # convert a PosConstraint or RelConstraint node into a plain dict
    def _eval_constraint_clause(
        self,
        clause: Any,
        env: Environment,
    ) -> Dict[str, Any]:
        if isinstance(clause, PosConstraint):
            targets: List[Any] = [self._eval(t, env) for t in clause.targets]
            return {"kind": clause.kind, "targets": targets}

        if isinstance(clause, RelConstraint):
            return {"kind": clause.kind, "target": clause.target}

        return {"kind": "unknown"}

    # measure statements - store values in the env under a prefixed key
    def _exec_distance_measure(self, stmt: DistanceMeasure, env: Environment) -> None:
        val = self._eval(stmt.value, env)
        env.define(f"__dist_{stmt.point_a}_{stmt.point_b}", val)
        if self._backend is not None:
            self._backend.add_distance_constraint(stmt.point_a, stmt.point_b, val, env)

    def _exec_angle_measure(self, stmt: AngleMeasure, env: Environment) -> None:
        val = stmt.value.degrees  # AngleLiteral carries degrees directly
        env.define(f"__angle_{stmt.angle_name}", val)
        if self._backend is not None:
            self._backend.add_angle_constraint(stmt.angle_name, val, env)

    def _exec_length_measure(self, stmt: LengthMeasure, env: Environment) -> None:
        val = self._eval(stmt.value, env)
        shape = env.get(stmt.shape_name)
        if isinstance(shape, GeoShape):
            shape.props["length"] = val
        env.define(f"__length_{stmt.shape_name}", val)

    def _exec_radius_measure(self, stmt: RadiusMeasure, env: Environment) -> None:
        val = self._eval(stmt.value, env)
        shape = env.get(stmt.shape_name)
        if isinstance(shape, GeoShape):
            shape.props["radius"] = val
        env.define(f"__radius_{stmt.shape_name}", val)

    def _exec_ratio_measure(self, stmt: RatioMeasure, env: Environment) -> None:
        ratio = (stmt.value.left, stmt.value.right)
        env.define(f"__ratio_{stmt.shape_a}_{stmt.shape_b}", ratio)

    def _exec_area_measure(self, stmt: AreaMeasure, env: Environment) -> None:
        val = self._eval(stmt.value, env)
        shape = env.get(stmt.shape_name)
        if isinstance(shape, GeoShape):
            shape.props["area"] = val
        env.define(f"__area_{stmt.shape_name}", val)

    def _exec_perimeter_measure(self, stmt: PerimeterMeasure, env: Environment) -> None:
        val = self._eval(stmt.value, env)
        shape = env.get(stmt.shape_name)
        if isinstance(shape, GeoShape):
            shape.props["perimeter"] = val
        env.define(f"__perimeter_{stmt.shape_name}", val)

    # let creates a mutable variable, set updates an existing mutable one
    def _exec_let(self, stmt: LetStmt, env: Environment) -> None:
        val = self._eval(stmt.value, env)
        env.define(stmt.name, val, mutable=True)

    def _exec_set(self, stmt: SetStmt, env: Environment) -> None:
        val = self._eval(stmt.value, env)
        env.set(stmt.name, val)  # raises GeoImmutableError or GeoNameError if needed

    # param declares an animated parameter with start, end, step
    def _exec_param(self, stmt: ParamStmt, env: Environment) -> None:
        rs = stmt.range_spec
        start = self._eval(rs.start, env)
        end = self._eval(rs.end, env)
        step = self._eval(rs.step, env)
        env.define_param(stmt.name, float(start), float(end), float(step))

    # advance each listed param by one step - wraps around at the boundary
    def _exec_sweep(self, stmt: SweepStmt, env: Environment) -> None:
        speed = float(self._eval(stmt.speed, env)) if stmt.speed else 1.0
        for pname in stmt.params:
            if not env.is_defined(pname):
                raise GeoNameError(pname)
            start, end, step = env.get_param_range(pname)
            current = float(env.get(pname))
            next_val = round(current + step * speed, 10)
            if step > 0 and next_val > end:
                next_val = start
            elif step < 0 and next_val < end:
                next_val = start
            env.set(pname, next_val)

    # if/elif/else - each branch runs in its own child scope
    def _exec_if(self, stmt: IfStmt, env: Environment) -> None:
        if self._eval_bool(stmt.condition, env):
            child = env.child()
            for s in stmt.body:
                self._exec(s, child)
            return
        for elif_clause in stmt.else_ifs:
            if self._eval_bool(elif_clause.condition, env):
                child = env.child()
                for s in elif_clause.body:
                    self._exec(s, child)
                return
        if stmt.else_body is not None:
            child = env.child()
            for s in stmt.else_body:
                self._exec(s, child)

    # for loop - loop variable is read-only inside the body
    def _exec_for(self, stmt: ForStmt, env: Environment) -> None:
        values = [self._eval(v, env) for v in stmt.values]
        for val in values:
            child = env.child()
            child.define(stmt.var, val, mutable=False)
            for s in stmt.body:
                self._exec(s, child)

    # define captures the current env as the closure (lexical scoping)
    def _exec_define(self, stmt: DefineStmt, env: Environment) -> None:
        func = UserFunction(stmt.name, stmt.params, stmt.body, closure=env)
        env.define(stmt.name, func)

    def _exec_call(self, stmt: CallStmt, env: Environment) -> Any:
        func_val = env.get(stmt.name)
        args = [self._eval(a, env) for a in stmt.args]
        return self._call_function(stmt.name, func_val, args, env)

    # create a new scope from the closure and run the function body in it
    def _call_function(
        self,
        name: str,
        func_val: Any,
        args: List[Any],
        env: Environment,
    ) -> Any:
        if not isinstance(func_val, UserFunction):
            raise GeoTypeError(f"'{name}' is not a function")
        if len(args) != len(func_val.params):
            raise GeoArgumentError(name, len(func_val.params), len(args))

        call_env = func_val.closure.child()
        for pname, pval in zip(func_val.params, args):
            call_env.define(pname, pval)

        try:
            for s in func_val.body:
                self._exec(s, call_env)
        except ReturnSignal as ret:
            return ret.value
        return None

    # transformation handlers - delegate to the backend if one is present
    def _exec_reflect(self, stmt: ReflectStmt, env: Environment) -> None:
        shape = self._require_shape(stmt.target, env)
        axis = self._require_shape(stmt.over, env)
        if self._backend is not None:
            result = self._backend.reflect(shape, axis, env)
            if result is not None:
                self.shapes.append((stmt.target, result))
                env.define(stmt.target, result)

    def _exec_rotate(self, stmt: RotateStmt, env: Environment) -> None:
        shape = self._require_shape(stmt.target, env)
        angle = stmt.by.degrees
        pivot = self._require_shape(stmt.about, env)
        if self._backend is not None:
            result = self._backend.rotate(shape, angle, pivot, env)
            if result is not None:
                self.shapes.append((stmt.target, result))
                env.define(stmt.target, result)

    def _exec_scale(self, stmt: ScaleStmt, env: Environment) -> None:
        shape = self._require_shape(stmt.target, env)
        factor = float(self._eval(stmt.by, env))
        if self._backend is not None:
            result = self._backend.scale(shape, factor, env)
            if result is not None:
                self.shapes.append((stmt.target, result))
                env.define(stmt.target, result)

    def _exec_translate(self, stmt: TranslateStmt, env: Environment) -> None:
        shape = self._require_shape(stmt.target, env)
        dx = float(self._eval(stmt.by.x, env))
        dy = float(self._eval(stmt.by.y, env))
        if self._backend is not None:
            result = self._backend.translate(shape, dx, dy, env)
            if result is not None:
                self.shapes.append((stmt.target, result))
                env.define(stmt.target, result)

    # assert evaluates a boolean expression and records pass/fail
    def _exec_assert(self, stmt: AssertStmt, env: Environment) -> None:
        result = self._eval_bool(stmt.expr, env)
        desc = self._describe_bool_expr(stmt.expr)
        if result:
            self.assertions_passed += 1
        else:
            self.assertions_failed.append(desc)
            raise GeoAssertionError(desc)

    # evaluate any expression node and return a Python value
    def _eval(self, expr: Any, env: Environment) -> Any:
        if isinstance(expr, NumberLiteral):
            return expr.value

        if isinstance(expr, AngleLiteral):
            return expr.degrees  # plain float in degrees

        if isinstance(expr, RatioLiteral):
            return (expr.left, expr.right)

        if isinstance(expr, StringLiteral):
            return expr.value

        if isinstance(expr, IdentExpr):
            return env.get(expr.name)

        if isinstance(expr, VectorExpr):
            x = float(self._eval(expr.x, env))
            y = float(self._eval(expr.y, env))
            return (x, y)

        if isinstance(expr, BinOp):
            return self._eval_binop(expr, env)

        if isinstance(expr, UnaryOp):
            return -float(self._eval(expr.operand, env))

        if isinstance(expr, CallExpr):
            return self._eval_call(expr, env)

        # CallStmt can appear inside a return statement
        if isinstance(expr, CallStmt):
            func_val = env.get(expr.name)
            args = [self._eval(a, env) for a in expr.args]
            return self._call_function(expr.name, func_val, args, env)

        raise GeoTypeError(f"Cannot evaluate expression of type {type(expr).__name__}")

    # built-in function calls: distance, cos, sin - then user-defined functions
    def _eval_call(self, expr: CallExpr, env: Environment) -> Any:
        if expr.name == "distance":
            if len(expr.args) != 2:
                raise GeoArgumentError("distance", 2, len(expr.args))
            a = self._eval(expr.args[0], env)
            b = self._eval(expr.args[1], env)
            pa = self._resolve_point(a)
            pb = self._resolve_point(b)
            return math.hypot(pa[0] - pb[0], pa[1] - pb[1])

        if expr.name == "cos":
            if len(expr.args) != 1:
                raise GeoArgumentError("cos", 1, len(expr.args))
            arg = self._eval(expr.args[0], env)
            return math.cos(float(arg))

        if expr.name == "sin":
            if len(expr.args) != 1:
                raise GeoArgumentError("sin", 1, len(expr.args))
            arg = self._eval(expr.args[0], env)
            return math.sin(float(arg))

        func_val = env.get(expr.name)
        args = [self._eval(a, env) for a in expr.args]
        return self._call_function(expr.name, func_val, args, env)

    # pull x, y out of a GeoShape or a (float, float) tuple
    def _resolve_point(self, val: Any) -> Tuple[float, float]:
        if hasattr(val, "props"):
            x = val.props.get("x")
            y = val.props.get("y")
            if x is not None and y is not None:
                return float(x), float(y)
        if isinstance(val, (tuple, list)) and len(val) == 2:
            return float(val[0]), float(val[1])
        raise GeoTypeError(f"Expected a point-like value, got {type(val).__name__}")

    # handle +, -, *, / with proper type checks and zero-division guard
    def _eval_binop(self, expr: BinOp, env: Environment) -> float:
        left = self._eval(expr.left, env)
        right = self._eval(expr.right, env)
        try:
            left = float(left)
            right = float(right)
        except (TypeError, ValueError) as exc:
            raise GeoTypeError(
                f"Arithmetic requires numeric operands, got "
                f"{type(left).__name__} and {type(right).__name__}"
            ) from exc
        if expr.op == "+":
            return left + right
        if expr.op == "-":
            return left - right
        if expr.op == "*":
            return left * right
        if expr.op == "/":
            if right == 0.0:
                raise GeoDivisionByZero()
            return left / right
        raise GeoRuntimeError(f"Unknown binary operator '{expr.op}'")

    # evaluate a comparison or geometric predicate to True/False
    def _eval_bool(self, expr: Any, env: Environment) -> bool:
        if isinstance(expr, CmpExpr):
            left = self._eval(expr.left, env)
            right = self._eval(expr.right, env)
            try:
                left, right = float(left), float(right)
            except (TypeError, ValueError) as exc:
                raise GeoTypeError("Comparison requires numeric operands") from exc
            if expr.op in ("=", "=="):
                return math.isclose(left, right, rel_tol=1e-9)
            if expr.op == "!=":
                return not math.isclose(left, right, rel_tol=1e-9)
            if expr.op == "<":
                return left < right
            if expr.op == ">":
                return left > right
            if expr.op == "<=":
                return left <= right
            if expr.op == ">=":
                return left >= right

        if isinstance(expr, GeometricPred):
            return self._eval_geometric_pred(expr, env)

        raise GeoTypeError(f"Cannot evaluate bool expr of type {type(expr).__name__}")

    # ask the backend to check a geometric predicate; return True in stub mode
    def _eval_geometric_pred(self, pred: GeometricPred, env: Environment) -> bool:
        if self._backend is not None:
            return self._backend.check_predicate(pred, env)
        return True  # no backend means we can't disprove it, so default to True

    # helper to look up a name and make sure it really is a GeoShape
    def _require_shape(self, name: str, env: Environment) -> GeoShape:
        val = env.get(name)
        if not isinstance(val, GeoShape):
            raise GeoTypeError(f"'{name}' is not a shape (got {type(val).__name__})")
        return val

    # turn a boolean expression node into a readable string for assertion messages
    def _describe_bool_expr(self, expr: Any) -> str:
        if isinstance(expr, CmpExpr):
            return f"{expr.left} {expr.op} {expr.right}"
        if isinstance(expr, GeometricPred):
            return f"{expr.subject} {expr.relation} {expr.target}"
        return str(expr)


# convenience function - create an interpreter, run the program, return both
def interpret(
    program: Program,
    geometry_backend: Optional[Any] = None,
) -> Tuple[Interpreter, Environment]:
    interp = Interpreter(geometry_backend)
    env = interp.run(program)
    return interp, env
