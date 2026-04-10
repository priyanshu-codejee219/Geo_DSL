import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ast_nodes.nodes import (
    AngleLiteral,
    AngleMeasure,
    AreaMeasure,
    AssertStmt,
    BinOp,
    CallStmt,
    CmpExpr,
    ConstraintStmt,
    DefineStmt,
    DerivedDecl,
    DistanceMeasure,
    ElseIfClause,
    ForStmt,
    GeometricPred,
    GridStmt,
    HideStmt,
    IdentExpr,
    IfStmt,
    LabelStmt,
    LengthMeasure,
    LetStmt,
    NoteStmt,
    NumberLiteral,
    ParamStmt,
    PerimeterMeasure,
    PosConstraint,
    PrimitiveDecl,
    Program,
    PropAssign,
    RadiusMeasure,
    RangeSpec,
    RatioLiteral,
    RatioMeasure,
    ReflectStmt,
    RelConstraint,
    ReturnStmt,
    RotateStmt,
    ScaleStmt,
    SetStmt,
    StringLiteral,
    SweepStmt,
    TranslateStmt,
    UnaryOp,
    VectorExpr,
)
from interpreter import (
    Environment,
    GeoArgumentError,
    GeoAssertionError,
    GeoDivisionByZero,
    GeoImmutableError,
    GeoNameError,
    GeoRuntimeError,
    GeoShape,
    GeoTypeError,
    Interpreter,
    ReturnSignal,
    UserFunction,
    interpret,
)


# small helper functions so tests don't have to repeat node constructors everywhere

def num(v):
    return NumberLiteral(float(v))


def ident(n):
    return IdentExpr(n)


def ang(d):
    return AngleLiteral(float(d))


def vec(x, y):
    return VectorExpr(num(x), num(y))


def add(a, b):
    return BinOp("+", a, b)


def sub(a, b):
    return BinOp("-", a, b)


def mul(a, b):
    return BinOp("*", a, b)


def div(a, b):
    return BinOp("/", a, b)


def neg(a):
    return UnaryOp("-", a)


def cmp(op, a, b):
    return CmpExpr(op, a, b)


def geo_pred(s, r, t):
    return GeometricPred(s, r, t)


def prim(kw_str, name, props=None, constraint=None):
    # import here so TokenType doesn't sit unused at module level
    from lexer.token_types import TokenType  # noqa: PLC0415
    kw = getattr(TokenType, kw_str.upper())
    constraints = [constraint] if constraint else []
    return PrimitiveDecl(
        kw, name, props or [], constraints=constraints, constraint=constraint
    )


def prop(name, val_expr):
    return PropAssign(name, val_expr)


def prog(*stmts):
    return Program(list(stmts))


# shapes is stored as (name, shape) pairs so we pull out just the names for asserts
def _shape_names(interp):
    return [n for n, _ in interp.shapes]


class TestEnvironment(unittest.TestCase):
    def test_define_and_get(self):
        env = Environment()
        env.define("x", 42)
        self.assertEqual(env.get("x"), 42)

    def test_get_undefined_raises(self):
        env = Environment()
        with self.assertRaises(GeoNameError):
            env.get("missing")

    def test_is_defined_true(self):
        env = Environment()
        env.define("y", 1)
        self.assertTrue(env.is_defined("y"))

    def test_is_defined_false(self):
        env = Environment()
        self.assertFalse(env.is_defined("z"))

    def test_child_inherits_parent(self):
        parent = Environment()
        parent.define("a", 10)
        child = parent.child()
        self.assertEqual(child.get("a"), 10)

    def test_child_shadows_parent(self):
        # child defines the same name, should not touch parent's value
        parent = Environment()
        parent.define("a", 10)
        child = parent.child()
        child.define("a", 99)
        self.assertEqual(child.get("a"), 99)
        self.assertEqual(parent.get("a"), 10)

    def test_mutable_set(self):
        env = Environment()
        env.define("r", 5, mutable=True)
        env.set("r", 10)
        self.assertEqual(env.get("r"), 10)

    def test_set_immutable_raises(self):
        env = Environment()
        env.define("c", 5, mutable=False)
        with self.assertRaises(GeoImmutableError):
            env.set("c", 99)

    def test_set_undefined_raises(self):
        env = Environment()
        with self.assertRaises(GeoNameError):
            env.set("nope", 1)

    def test_set_in_parent_from_child(self):
        # setting via child scope should update the parent binding
        parent = Environment()
        parent.define("x", 1, mutable=True)
        child = parent.child()
        child.set("x", 100)
        self.assertEqual(parent.get("x"), 100)

    def test_define_param_and_get_range(self):
        env = Environment()
        env.define_param("t", 0.0, 10.0, 0.5)
        self.assertEqual(env.get("t"), 0.0)
        self.assertEqual(env.get_param_range("t"), (0.0, 10.0, 0.5))

    def test_all_bindings_merges_parent(self):
        parent = Environment()
        parent.define("a", 1)
        child = parent.child()
        child.define("b", 2)
        merged = child.all_bindings()
        self.assertIn("a", merged)
        self.assertIn("b", merged)

    def test_all_bindings_excludes_param_meta(self):
        # the __param_* internal keys should never leak out to callers
        env = Environment()
        env.define_param("t", 0, 5, 1)
        keys = env.all_bindings().keys()
        self.assertIn("t", keys)
        for k in keys:
            self.assertFalse(k.startswith("__param_"))


class TestExpressionEval(unittest.TestCase):
    def setUp(self):
        self.interp = Interpreter()
        self.env = self.interp.env

    def _eval(self, expr):
        return self.interp._eval(expr, self.env)

    def test_number_literal(self):
        self.assertAlmostEqual(self._eval(num(3.14)), 3.14)

    def test_angle_literal_returns_degrees(self):
        self.assertAlmostEqual(self._eval(ang(90)), 90.0)

    def test_ratio_literal_returns_tuple(self):
        self.assertEqual(self._eval(RatioLiteral(1, 2)), (1.0, 2.0))

    def test_string_literal(self):
        self.assertEqual(self._eval(StringLiteral("hello")), "hello")

    def test_ident_expr(self):
        self.env.define("r", 7.0)
        self.assertAlmostEqual(self._eval(ident("r")), 7.0)

    def test_ident_missing_raises(self):
        with self.assertRaises(GeoNameError):
            self._eval(ident("undefined_var"))

    def test_vector_expr(self):
        result = self._eval(vec(3, 4))
        self.assertEqual(result, (3.0, 4.0))

    def test_binop_add(self):
        self.assertAlmostEqual(self._eval(add(num(2), num(3))), 5.0)

    def test_binop_sub(self):
        self.assertAlmostEqual(self._eval(sub(num(10), num(4))), 6.0)

    def test_binop_mul(self):
        self.assertAlmostEqual(self._eval(mul(num(3), num(4))), 12.0)

    def test_binop_div(self):
        self.assertAlmostEqual(self._eval(div(num(10), num(4))), 2.5)

    def test_binop_div_by_zero(self):
        with self.assertRaises(GeoDivisionByZero):
            self._eval(div(num(1), num(0)))

    def test_unary_neg(self):
        self.assertAlmostEqual(self._eval(neg(num(5))), -5.0)

    def test_nested_expr(self):
        # (2 + 3) * 4 = 20
        expr = mul(add(num(2), num(3)), num(4))
        self.assertAlmostEqual(self._eval(expr), 20.0)

    def test_binop_type_error(self):
        # adding a shape to a number should fail with a type error
        self.env.define("s", GeoShape("circle", "C"))
        with self.assertRaises(GeoTypeError):
            self._eval(add(ident("s"), num(1)))


class TestBoolEval(unittest.TestCase):
    def setUp(self):
        self.interp = Interpreter()
        self.env = self.interp.env

    def _bool(self, expr):
        return self.interp._eval_bool(expr, self.env)

    def test_cmp_eq_true(self):
        self.assertTrue(self._bool(cmp("=", num(5), num(5))))

    def test_cmp_eq_false(self):
        self.assertFalse(self._bool(cmp("=", num(5), num(6))))

    def test_cmp_neq(self):
        self.assertTrue(self._bool(cmp("!=", num(1), num(2))))

    def test_cmp_lt(self):
        self.assertTrue(self._bool(cmp("<", num(1), num(2))))
        self.assertFalse(self._bool(cmp("<", num(2), num(1))))

    def test_cmp_gt(self):
        self.assertTrue(self._bool(cmp(">", num(3), num(2))))

    def test_cmp_lte(self):
        self.assertTrue(self._bool(cmp("<=", num(2), num(2))))
        self.assertTrue(self._bool(cmp("<=", num(1), num(2))))

    def test_cmp_gte(self):
        self.assertTrue(self._bool(cmp(">=", num(3), num(3))))

    def test_geometric_pred_no_backend_returns_true(self):
        # no backend means we can't check geometry so it defaults to True
        p = geo_pred("A", "on", "C")
        self.assertTrue(self._bool(p))


class TestVariableStatements(unittest.TestCase):
    def _run(self, *stmts):
        interp = Interpreter()
        interp.run(prog(*stmts))
        return interp

    def test_let_defines_variable(self):
        i = self._run(LetStmt("x", num(42)))
        self.assertAlmostEqual(i.env.get("x"), 42)

    def test_let_is_mutable(self):
        i = self._run(
            LetStmt("x", num(5)),
            SetStmt("x", num(10)),
        )
        self.assertAlmostEqual(i.env.get("x"), 10)

    def test_set_uses_expression(self):
        i = self._run(
            LetStmt("r", num(3)),
            SetStmt("r", add(ident("r"), num(7))),
        )
        self.assertAlmostEqual(i.env.get("r"), 10)

    def test_set_undefined_raises(self):
        with self.assertRaises(GeoNameError):
            self._run(SetStmt("nope", num(1)))

    def test_param_declares_with_range(self):
        i = self._run(ParamStmt("t", RangeSpec(num(0), num(10), num(1))))
        self.assertEqual(i.env.get_param_range("t"), (0.0, 10.0, 1.0))
        self.assertAlmostEqual(i.env.get("t"), 0.0)

    def test_let_expression_using_prior_variable(self):
        i = self._run(
            LetStmt("a", num(3)),
            LetStmt("b", mul(ident("a"), num(2))),
        )
        self.assertAlmostEqual(i.env.get("b"), 6.0)


class TestControlFlow(unittest.TestCase):
    def _run(self, *stmts):
        interp = Interpreter()
        interp.run(prog(*stmts))
        return interp

    def test_if_true_branch(self):
        i = self._run(
            LetStmt("x", num(0)),
            IfStmt(
                condition=cmp(">", num(5), num(3)),
                body=[SetStmt("x", num(1))],
                else_ifs=[],
                else_body=None,
            ),
        )
        self.assertAlmostEqual(i.env.get("x"), 1)

    def test_if_false_goes_to_else(self):
        i = self._run(
            LetStmt("x", num(0)),
            IfStmt(
                condition=cmp(">", num(1), num(10)),
                body=[SetStmt("x", num(99))],
                else_ifs=[],
                else_body=[SetStmt("x", num(7))],
            ),
        )
        self.assertAlmostEqual(i.env.get("x"), 7)

    def test_if_elif_branch(self):
        i = self._run(
            LetStmt("x", num(0)),
            IfStmt(
                condition=cmp(">", num(1), num(10)),
                body=[SetStmt("x", num(1))],
                else_ifs=[
                    ElseIfClause(
                        condition=cmp("=", num(2), num(2)),
                        body=[SetStmt("x", num(2))],
                    )
                ],
                else_body=None,
            ),
        )
        self.assertAlmostEqual(i.env.get("x"), 2)

    def test_for_loop_sums_values(self):
        i = self._run(
            LetStmt("total", num(0)),
            ForStmt(
                var="v",
                values=[num(1), num(2), num(3), num(4)],
                body=[SetStmt("total", add(ident("total"), ident("v")))],
            ),
        )
        self.assertAlmostEqual(i.env.get("total"), 10)

    def test_for_loop_does_not_leak_var(self):
        # loop variable should stay inside the loop scope
        interp = Interpreter()
        interp.run(prog(ForStmt(var="item", values=[num(1)], body=[])))
        self.assertFalse(interp.env.is_defined("item"))

    def test_sweep_advances_param(self):
        i = self._run(
            ParamStmt("t", RangeSpec(num(0), num(10), num(1))),
            SweepStmt(params=["t"], speed=None),
        )
        self.assertAlmostEqual(i.env.get("t"), 1.0)

    def test_sweep_wraps_at_end(self):
        # after reaching the end the param wraps back to start
        i = self._run(
            ParamStmt("t", RangeSpec(num(9), num(10), num(1))),
            SweepStmt(params=["t"], speed=None),
            SweepStmt(params=["t"], speed=None),
        )
        self.assertAlmostEqual(i.env.get("t"), 9.0)


class TestFunctions(unittest.TestCase):
    def _run(self, *stmts):
        interp = Interpreter()
        interp.run(prog(*stmts))
        return interp

    def test_define_creates_function(self):
        i = self._run(
            DefineStmt("double", ["n"], [ReturnStmt(mul(ident("n"), num(2)))])
        )
        self.assertIsInstance(i.env.get("double"), UserFunction)

    def test_call_function(self):
        i = self._run(
            DefineStmt("square", ["n"], [ReturnStmt(mul(ident("n"), ident("n")))]),
            LetStmt("result", num(0)),
        )
        func = i.env.get("square")
        result = i._call_function("square", func, [4.0], i.env)
        self.assertAlmostEqual(result, 16.0)

    def test_call_stmt_executes_body(self):
        # calling inc twice should increment counter to 2
        i = self._run(
            LetStmt("counter", num(0)),
            DefineStmt("inc", [], [SetStmt("counter", add(ident("counter"), num(1)))]),
            CallStmt("inc", []),
            CallStmt("inc", []),
        )
        self.assertAlmostEqual(i.env.get("counter"), 2)

    def test_wrong_arg_count_raises(self):
        interp = Interpreter()
        interp.run(
            prog(DefineStmt("f", ["a", "b"], [ReturnStmt(add(ident("a"), ident("b")))]))
        )
        func = interp.env.get("f")
        with self.assertRaises(GeoArgumentError):
            interp._call_function("f", func, [1.0], interp.env)

    def test_call_non_function_raises(self):
        interp = Interpreter()
        interp.env.define("x", 42)
        with self.assertRaises(GeoTypeError):
            interp._call_function("x", 42, [], interp.env)

    def test_recursive_function(self):
        # build fact(n) = if n<=1: 1 else n * fact(n-1) by hand
        fact_body = [
            IfStmt(
                condition=cmp("<=", ident("n"), num(1)),
                body=[ReturnStmt(num(1))],
                else_ifs=[],
                else_body=[
                    ReturnStmt(
                        mul(
                            ident("n"),
                            CallStmt("fact", [sub(ident("n"), num(1))]),
                        )
                    )
                ],
            )
        ]
        interp = Interpreter()
        interp.run(prog(DefineStmt("fact", ["n"], fact_body)))
        func = interp.env.get("fact")
        result = interp._call_function("fact", func, [5.0], interp.env)
        self.assertAlmostEqual(result, 120.0)

    def test_closure_captures_outer_variable(self):
        i = self._run(
            LetStmt("offset", num(10)),
            DefineStmt(
                "add_offset", ["n"], [ReturnStmt(add(ident("n"), ident("offset")))]
            ),
        )
        func = i.env.get("add_offset")
        result = i._call_function("add_offset", func, [5.0], i.env)
        self.assertAlmostEqual(result, 15.0)


class TestShapeDeclarations(unittest.TestCase):
    def _run(self, *stmts):
        interp = Interpreter()
        interp.run(prog(*stmts))
        return interp

    def test_primitive_circle_no_props(self):
        i = self._run(prim("circle", "C"))
        shape = i.env.get("C")
        self.assertIsInstance(shape, GeoShape)
        self.assertEqual(shape.kind, "circle")
        self.assertEqual(shape.name, "C")

    def test_primitive_circle_with_radius(self):
        i = self._run(prim("circle", "C", [prop("radius", num(50))]))
        shape = i.env.get("C")
        self.assertAlmostEqual(shape.props["radius"], 50.0)

    def test_primitive_triangle(self):
        i = self._run(prim("triangle", "T"))
        self.assertIsInstance(i.env.get("T"), GeoShape)
        self.assertEqual(i.env.get("T").kind, "triangle")

    def test_primitive_stored_in_shapes_list(self):
        i = self._run(prim("segment", "AB"))
        self.assertIn("AB", _shape_names(i))

    def test_primitive_with_pos_constraint_at(self):
        constraint = PosConstraint("at", [vec(0, 0)])
        i = self._run(prim("point", "A", [], constraint))
        shape = i.env.get("A")
        self.assertTrue(len(shape.constraints) > 0)
        self.assertEqual(shape.constraints[0]["kind"], "at")

    def test_primitive_with_rel_constraint(self):
        constraint = RelConstraint("parallel_to", "L2")
        i = self._run(
            prim("line", "L1"),
            prim("line", "L2"),
            prim("line", "L3", [], constraint),
        )
        shape = i.env.get("L3")
        self.assertEqual(shape.constraints[0]["kind"], "parallel_to")

    def test_derived_midpoint(self):
        decl = DerivedDecl("midpoint", "M", ["AB"])
        i = self._run(decl)
        shape = i.env.get("M")
        self.assertIsInstance(shape, GeoShape)
        self.assertEqual(shape.kind, "midpoint")

    def test_derived_circumcircle(self):
        decl = DerivedDecl("circumcircle", "CC", ["T"])
        i = self._run(decl)
        self.assertIn("CC", _shape_names(i))

    def test_derived_incircle(self):
        decl = DerivedDecl("incircle", "IC", ["T"])
        i = self._run(decl)
        self.assertIn("IC", _shape_names(i))

    def test_constraint_stmt_attaches_to_shape(self):
        rel = RelConstraint("tangent_to", "C2")
        i = self._run(
            prim("circle", "C1"),
            prim("circle", "C2"),
            ConstraintStmt("C1", rel),
        )
        shape = i.env.get("C1")
        kinds = [c["kind"] for c in shape.constraints]
        self.assertIn("tangent_to", kinds)


class TestMeasureStatements(unittest.TestCase):
    def _run(self, *stmts):
        interp = Interpreter()
        interp.run(prog(*stmts))
        return interp

    def test_distance_measure(self):
        i = self._run(DistanceMeasure("A", "B", num(30)))
        self.assertAlmostEqual(i.env.get("__dist_A_B"), 30.0)

    def test_angle_measure(self):
        i = self._run(AngleMeasure("alpha", AngleLiteral(45.0)))
        self.assertAlmostEqual(i.env.get("__angle_alpha"), 45.0)

    def test_length_measure_updates_shape(self):
        i = self._run(
            prim("segment", "AB"),
            LengthMeasure("AB", num(100)),
        )
        self.assertAlmostEqual(i.env.get("AB").props["length"], 100.0)

    def test_radius_measure_updates_shape(self):
        i = self._run(
            prim("circle", "C"),
            RadiusMeasure("C", num(25)),
        )
        self.assertAlmostEqual(i.env.get("C").props["radius"], 25.0)

    def test_ratio_measure(self):
        i = self._run(
            prim("segment", "AB"),
            prim("segment", "CD"),
            RatioMeasure("AB", "CD", RatioLiteral(1.0, 2.0)),
        )
        self.assertEqual(i.env.get("__ratio_AB_CD"), (1.0, 2.0))

    def test_area_measure(self):
        i = self._run(
            prim("triangle", "T"),
            AreaMeasure("T", num(60)),
        )
        self.assertAlmostEqual(i.env.get("T").props["area"], 60.0)

    def test_perimeter_measure(self):
        i = self._run(
            prim("triangle", "T"),
            PerimeterMeasure("T", num(30)),
        )
        self.assertAlmostEqual(i.env.get("T").props["perimeter"], 30.0)


class TestAssertions(unittest.TestCase):
    def _run(self, *stmts):
        interp = Interpreter()
        interp.run(prog(*stmts))
        return interp

    def test_assert_passes(self):
        i = self._run(AssertStmt(cmp("=", num(1), num(1))))
        self.assertEqual(i.assertions_passed, 1)
        self.assertEqual(len(i.assertions_failed), 0)

    def test_assert_fails_raises(self):
        with self.assertRaises(GeoAssertionError):
            self._run(AssertStmt(cmp("=", num(1), num(2))))

    def test_multiple_asserts(self):
        i = self._run(
            AssertStmt(cmp("<", num(1), num(2))),
            AssertStmt(cmp(">", num(5), num(3))),
        )
        self.assertEqual(i.assertions_passed, 2)

    def test_assert_with_variable(self):
        i = self._run(
            LetStmt("r", num(50)),
            AssertStmt(cmp("=", ident("r"), num(50))),
        )
        self.assertEqual(i.assertions_passed, 1)


class TestRenderStatements(unittest.TestCase):
    def _run(self, *stmts):
        interp = Interpreter()
        interp.run(prog(*stmts))
        return interp

    def test_label_stored(self):
        i = self._run(
            prim("circle", "C"),
            LabelStmt("C", "My Circle"),
        )
        self.assertEqual(i.labels["C"], "My Circle")

    def test_note_stored(self):
        i = self._run(NoteStmt("This is a note"))
        self.assertIn("This is a note", i.notes)

    def test_hide_stored(self):
        i = self._run(HideStmt(["A", "B"]))
        self.assertIn("A", i.hidden)
        self.assertIn("B", i.hidden)

    def test_grid_flag(self):
        i = self._run(GridStmt())
        self.assertTrue(i.show_grid)


class TestTransformations(unittest.TestCase):
    def _run(self, *stmts):
        interp = Interpreter()
        interp.run(prog(*stmts))
        return interp

    def test_reflect_does_not_crash(self):
        # no backend so reflect just does nothing, should not raise
        self._run(
            prim("line", "L"),
            prim("triangle", "T"),
            ReflectStmt("T", "L"),
        )

    def test_rotate_does_not_crash(self):
        self._run(
            prim("point", "O"),
            prim("triangle", "T"),
            RotateStmt("T", AngleLiteral(90), "O"),
        )

    def test_scale_does_not_crash(self):
        self._run(
            prim("circle", "C"),
            ScaleStmt("C", num(2)),
        )

    def test_translate_does_not_crash(self):
        self._run(
            prim("point", "P"),
            TranslateStmt("P", VectorExpr(num(10), num(20))),
        )

    def test_transform_non_shape_raises(self):
        interp = Interpreter()
        interp.env.define("notashape", 42)
        with self.assertRaises(GeoTypeError):
            interp._exec_scale(ScaleStmt("notashape", num(2)), interp.env)


class TestInterpretConvenience(unittest.TestCase):
    def test_returns_interpreter_and_env(self):
        p = prog(LetStmt("x", num(5)))
        interp, env = interpret(p)
        self.assertIsInstance(interp, Interpreter)
        self.assertIsInstance(env, Environment)
        self.assertAlmostEqual(env.get("x"), 5)

    def test_shapes_collected(self):
        p = prog(prim("circle", "C", [prop("radius", num(30))]))
        interp, _env = interpret(p)
        self.assertIn("C", _shape_names(interp))

    def test_complex_program(self):
        # small program that exercises let, shapes, assert and label together
        p = prog(
            LetStmt("r", num(50)),
            prim("circle", "C", [prop("radius", IdentExpr("r"))]),
            LetStmt("area_approx", mul(mul(ident("r"), ident("r")), num(3))),
            AssertStmt(cmp("=", ident("area_approx"), num(7500))),
            LabelStmt("C", "main circle"),
        )
        interp, env = interpret(p)
        self.assertAlmostEqual(env.get("r"), 50)
        self.assertAlmostEqual(env.get("area_approx"), 7500)
        self.assertEqual(interp.labels["C"], "main circle")
        self.assertEqual(interp.assertions_passed, 1)


class TestEdgeCases(unittest.TestCase):
    def test_redefine_variable_in_same_scope(self):
        # defining the same name twice just overwrites the old value
        interp = Interpreter()
        interp.env.define("x", 1)
        interp.env.define("x", 2)
        self.assertEqual(interp.env.get("x"), 2)

    def test_nested_for_loops(self):
        # 2 outer iterations, inner adds 10+20 each time = 60 total
        interp = Interpreter()
        interp.run(
            prog(
                LetStmt("total", num(0)),
                ForStmt(
                    var="i",
                    values=[num(1), num(2)],
                    body=[
                        ForStmt(
                            var="j",
                            values=[num(10), num(20)],
                            body=[SetStmt("total", add(ident("total"), ident("j")))],
                        )
                    ],
                ),
            )
        )
        self.assertAlmostEqual(interp.env.get("total"), 60)

    def test_param_used_in_expression(self):
        interp = Interpreter()
        interp.run(
            prog(
                ParamStmt("t", RangeSpec(num(5), num(10), num(1))),
                LetStmt("doubled", mul(ident("t"), num(2))),
            )
        )
        # t starts at 5 so doubled should be 10
        self.assertAlmostEqual(interp.env.get("doubled"), 10.0)

    def test_multiple_shapes(self):
        interp = Interpreter()
        interp.run(
            prog(
                prim("circle", "C1"),
                prim("circle", "C2"),
                prim("triangle", "T"),
            )
        )
        self.assertEqual(len(interp.shapes), 3)

    def test_empty_program(self):
        interp, _env = interpret(Program([]))
        self.assertEqual(len(interp.shapes), 0)

    def test_if_with_shape_assertion(self):
        # r=30 > 20 so only BigC should exist
        interp = Interpreter()
        interp.run(
            prog(
                LetStmt("r", num(30)),
                IfStmt(
                    condition=cmp(">", ident("r"), num(20)),
                    body=[prim("circle", "BigC", [prop("radius", ident("r"))])],
                    else_ifs=[],
                    else_body=[prim("circle", "SmallC")],
                ),
            )
        )
        self.assertIn("BigC", _shape_names(interp))
        self.assertFalse(interp.env.is_defined("SmallC"))


class TestEnvironmentFixes(unittest.TestCase):
    def test_snapshot_is_new_environment(self):
        env = Environment()
        snap = env.snapshot()
        self.assertIsInstance(snap, Environment)
        self.assertIsNot(snap, env)

    def test_snapshot_copies_bindings(self):
        env = Environment()
        env.define("x", 42)
        snap = env.snapshot()
        self.assertEqual(snap.get("x"), 42)

    def test_snapshot_preserves_mutability(self):
        # snapshot should keep the mutable flag so set() still works on it
        env = Environment()
        env.define_param("t", 0.0, 10.0, 1.0)
        snap = env.snapshot()
        snap.set("t", 5.0)
        self.assertEqual(snap.get("t"), 5.0)

    def test_snapshot_preserves_param_metadata(self):
        env = Environment()
        env.define_param("t", 2.0, 8.0, 2.0)
        snap = env.snapshot()
        start, end, step = snap.get_param_range("t")
        self.assertEqual((start, end, step), (2.0, 8.0, 2.0))

    def test_snapshot_parent_bindings_included(self):
        # snapshot should flatten the whole scope chain
        parent = Environment()
        parent.define("a", 100)
        child = parent.child()
        child.define("b", 200)
        snap = child.snapshot()
        self.assertEqual(snap.get("a"), 100)
        self.assertEqual(snap.get("b"), 200)
        self.assertIsNone(snap.parent)

    def test_define_param_idempotent_preserves_current_value(self):
        # if we advance t and then hit ParamStmt again, t should stay at 7
        env = Environment()
        env.define_param("t", 0.0, 10.0, 1.0)
        env.set("t", 7.0)
        env.define_param("t", 0.0, 10.0, 1.0)
        self.assertEqual(env.get("t"), 7.0)

    def test_define_param_second_call_keeps_mutable(self):
        env = Environment()
        env.define_param("t", 0.0, 5.0, 1.0)
        env.define_param("t", 0.0, 5.0, 1.0)
        env.set("t", 3.0)
        self.assertEqual(env.get("t"), 3.0)

    def test_get_param_range_from_child_scope(self):
        # range metadata is stored in the parent but should be readable from child
        parent = Environment()
        parent.define_param("t", 1.0, 9.0, 2.0)
        child = parent.child()
        start, end, step = child.get_param_range("t")
        self.assertEqual((start, end, step), (1.0, 9.0, 2.0))

    def test_snapshot_does_not_affect_original(self):
        env = Environment()
        env.define("x", 10, mutable=True)
        snap = env.snapshot()
        snap.set("x", 99)
        self.assertEqual(env.get("x"), 10)


class TestRunSweep(unittest.TestCase):
    def _make_param_program(self, name, start, end, step):
        return prog(
            ParamStmt(name, RangeSpec(num(start), num(end), num(step))),
            prim("circle", "C", [prop("radius", ident(name))]),
        )

    def test_run_sweep_returns_list(self):
        interp = Interpreter()
        program = self._make_param_program("t", 0.0, 2.0, 1.0)
        frames = interp.run_sweep(program, "t")
        self.assertIsInstance(frames, list)

    def test_run_sweep_frame_count(self):
        # 0, 1, 2 = 3 frames
        interp = Interpreter()
        program = self._make_param_program("t", 0.0, 2.0, 1.0)
        frames = interp.run_sweep(program, "t")
        self.assertEqual(len(frames), 3)

    def test_run_sweep_frame_values_correct(self):
        interp = Interpreter()
        program = self._make_param_program("t", 0.0, 2.0, 1.0)
        frames = interp.run_sweep(program, "t")
        param_values = [v for v, _ in frames]
        self.assertEqual(param_values, [0.0, 1.0, 2.0])

    def test_run_sweep_with_program_containing_sweep_stmt(self):
        # sweep stmts inside the program should be stripped before replaying
        program = prog(
            ParamStmt("t", RangeSpec(num(0), num(2), num(1))),
            SweepStmt(params=["t"], speed=None),
            prim("circle", "C", [prop("radius", ident("t"))]),
        )
        interp = Interpreter()
        frames = interp.run_sweep(program, "t")
        param_values = [v for v, _ in frames]
        self.assertEqual(param_values, [0.0, 1.0, 2.0])
        for expected_t, frame_env in frames:
            self.assertAlmostEqual(frame_env.get("t"), expected_t)

    def test_run_sweep_env_has_correct_param_value(self):
        interp = Interpreter()
        program = self._make_param_program("t", 5.0, 7.0, 1.0)
        frames = interp.run_sweep(program, "t")
        for expected_t, frame_env in frames:
            self.assertAlmostEqual(frame_env.get("t"), expected_t)

    def test_run_sweep_unknown_param_raises(self):
        interp = Interpreter()
        program = prog(prim("circle", "C"))
        interp.run(program)
        with self.assertRaises(GeoNameError):
            interp.run_sweep(program, "missing_param")

    def test_run_sweep_single_step(self):
        # start == end so only one frame
        interp = Interpreter()
        program = self._make_param_program("t", 10.0, 10.0, 1.0)
        frames = interp.run_sweep(program, "t")
        self.assertEqual(len(frames), 1)
        self.assertAlmostEqual(frames[0][0], 10.0)


class TestReturnSignalLeakFix(unittest.TestCase):
    # return outside a function used to leak ReturnSignal out of run()
    # it should be caught and re-raised as GeoRuntimeError instead

    def test_return_at_top_level_raises_runtime_error(self):
        interp = Interpreter()
        with self.assertRaises(GeoRuntimeError):
            interp.run(prog(ReturnStmt(num(42))))

    def test_return_does_not_leak_return_signal_at_top_level(self):
        interp = Interpreter()
        try:
            interp.run(prog(ReturnStmt(num(1))))
        except ReturnSignal:
            self.fail("ReturnSignal leaked out of run(), expected GeoRuntimeError")
        except Exception:  # noqa: BLE001
            pass

    def test_return_inside_if_at_top_level_raises_runtime_error(self):
        interp = Interpreter()
        stmt = IfStmt(
            condition=cmp(">", num(1), num(0)),
            body=[ReturnStmt(num(5))],
            else_ifs=[],
            else_body=None,
        )
        try:
            interp.run(prog(stmt))
            self.fail("Expected GeoRuntimeError but nothing was raised")
        except ReturnSignal:
            self.fail("ReturnSignal leaked from if body")
        except GeoRuntimeError:
            pass

    def test_return_inside_for_at_top_level_raises_runtime_error(self):
        interp = Interpreter()
        stmt = ForStmt(
            var="i",
            values=[num(1)],
            body=[ReturnStmt(num(99))],
        )
        try:
            interp.run(prog(stmt))
            self.fail("Expected GeoRuntimeError but nothing was raised")
        except ReturnSignal:
            self.fail("ReturnSignal leaked from for body")
        except GeoRuntimeError:
            pass

    def test_return_inside_function_still_works_after_fix(self):
        # make sure the fix didn't break normal returns inside define blocks
        interp = Interpreter()
        interp.run(
            prog(DefineStmt("double", ["n"], [ReturnStmt(mul(ident("n"), num(2)))]))
        )
        func = interp.env.get("double")
        result = interp._call_function("double", func, [7.0], interp.env)
        self.assertAlmostEqual(result, 14.0)

    def test_return_inside_for_inside_function_works_after_fix(self):
        # early return from a for loop inside a function should still give the right value
        interp = Interpreter()
        interp.run(
            prog(
                DefineStmt(
                    "first_val",
                    ["dummy"],
                    [
                        ForStmt(
                            "v",
                            [num(10), num(20), num(30)],
                            [ReturnStmt(ident("v"))],
                        )
                    ],
                )
            )
        )
        func = interp.env.get("first_val")
        result = interp._call_function("first_val", func, [0.0], interp.env)
        self.assertAlmostEqual(result, 10.0)

    def test_return_none_at_top_level_still_raises(self):
        interp = Interpreter()
        with self.assertRaises(GeoRuntimeError):
            interp.run(prog(ReturnStmt(None)))

    def test_return_inside_else_at_top_level_raises(self):
        interp = Interpreter()
        stmt = IfStmt(
            condition=cmp(">", num(0), num(1)),  # false so else runs
            body=[],
            else_ifs=[],
            else_body=[ReturnStmt(num(7))],
        )
        try:
            interp.run(prog(stmt))
            self.fail("Expected GeoRuntimeError but nothing was raised")
        except ReturnSignal:
            self.fail("ReturnSignal leaked from else body")
        except GeoRuntimeError:
            pass


if __name__ == "__main__":
    unittest.main()
