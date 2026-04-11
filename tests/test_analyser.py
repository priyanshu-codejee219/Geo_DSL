import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ast_nodes.nodes import (
    AngleLiteral,
    AssertStmt,
    BinOp,
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
    LetStmt,
    NoteStmt,
    NumberLiteral,
    ParamStmt,
    PrimitiveDecl,
    Program,
    PropAssign,
    RangeSpec,
    RatioLiteral,
    ReflectStmt,
    RelConstraint,
    ReturnStmt,
    SetStmt,
    StringLiteral,
    SweepStmt,
    VectorExpr,
)
from lexer.token_types import TokenType
from semantics.analyser import SemanticAnalyser, SemanticError, analyse

def num(v):
    return NumberLiteral(float(v))


def ident(n):
    return IdentExpr(n)


def ang(d):
    return AngleLiteral(float(d))


def ratio(a, b):
    return RatioLiteral(float(a), float(b))


def slit(s):
    return StringLiteral(s)


def vec(x, y):
    return VectorExpr(num(x), num(y))


def add(a, b):
    return BinOp("+", a, b)


def mul(a, b):
    return BinOp("*", a, b)


def cmp(op, a, b):
    return CmpExpr(op, a, b)


def geo_pred(s, r, t):
    return GeometricPred(s, r, t)


def prim(kw_str, name, props=None, constraint=None):
    kw = getattr(TokenType, kw_str.upper())
    return PrimitiveDecl(kw, name, props or [], [], [], constraint)


def prop(name, val_expr):
    return PropAssign(name, val_expr)


def prog(*stmts):
    return Program(list(stmts))


def rng(start, end, step):
    return RangeSpec(num(start), num(end), num(step))


def errors_of(program: Program):
    a = SemanticAnalyser()
    return [e.message for e in a.analyse(program) if e.severity == "error"]


def warnings_of(program: Program):
    a = SemanticAnalyser()
    return [e.message for e in a.analyse(program) if e.severity == "warning"]


def all_messages(program: Program):
    a = SemanticAnalyser()
    return [(e.message, e.severity) for e in a.analyse(program)]


def has_error_containing(program: Program, fragment: str) -> bool:
    return any(fragment in msg for msg in errors_of(program))


def has_warning_containing(program: Program, fragment: str) -> bool:
    return any(fragment in msg for msg in warnings_of(program))


def is_clean(program: Program) -> bool:
    return len(errors_of(program)) == 0


# class for undeclared variable checking.

class TestUndeclaredName(unittest.TestCase):
    def test_label_undeclared_target(self):
        p = prog(LabelStmt("X", "hello"))
        self.assertTrue(has_error_containing(p, "X"))

    def test_set_undeclared_name(self):
        p = prog(SetStmt("r", num(5)))
        self.assertTrue(has_error_containing(p, "r"))

    def test_sweep_undeclared_param(self):
        p = prog(SweepStmt(["t"], speed=None))
        self.assertTrue(has_error_containing(p, "t"))

    def test_call_undeclared_function(self):
        # calling "foo" but foo was never defined — should be an error
        p = prog(CallStmt("foo", []))
        self.assertTrue(has_error_containing(p, "foo"))

    def test_ident_in_expr_undeclared(self):
        p = prog(LetStmt("x", ident("undefined_var")))
        self.assertTrue(has_error_containing(p, "undefined_var"))

    def test_reflect_undeclared_target(self):
        p = prog(
            prim("line", "L"),
            ReflectStmt("Missing", "L"),
        )
        self.assertTrue(has_error_containing(p, "Missing"))

    def test_reflect_undeclared_axis(self):
        p = prog(
            prim("triangle", "T"),
            ReflectStmt("T", "NoAxis"),
        )
        self.assertTrue(has_error_containing(p, "NoAxis"))

    def test_distance_measure_undeclared(self):
        p = prog(DistanceMeasure("A", "B", num(10)))
        errs = errors_of(p)
        self.assertTrue(any("A" in e or "B" in e for e in errs))

    def test_hide_undeclared(self):
        p = prog(HideStmt(["Q"]))
        self.assertTrue(has_error_containing(p, "Q"))

    def test_declared_name_is_fine(self):
        p = prog(
            prim("point", "A"),
            LabelStmt("A", "vertex"),
        )
        self.assertTrue(is_clean(p))


# class redeclaration checking.
class TestRedeclaration(unittest.TestCase):
    def test_let_redeclared_same_scope(self):
        p = prog(
            LetStmt("r", num(5)),
            LetStmt("r", num(10)),
        )
        self.assertTrue(has_error_containing(p, "Redeclaration"))

    def test_shape_redeclared(self):
        p = prog(
            prim("circle", "C"),
            prim("circle", "C"),
        )
        self.assertTrue(has_error_containing(p, "Redeclaration"))

    def test_param_redeclared(self):
        p = prog(
            ParamStmt("t", rng(0, 10, 1)),
            ParamStmt("t", rng(0, 5, 1)),
        )
        self.assertTrue(has_error_containing(p, "Redeclaration"))

    def test_function_redeclared(self):
        p = prog(
            DefineStmt("f", [], [ReturnStmt(num(1))]),
            DefineStmt("f", [], [ReturnStmt(num(2))]),
        )
        self.assertTrue(has_error_containing(p, "Redeclaration"))

    def test_different_names_fine(self):
        p = prog(
            LetStmt("x", num(1)),
            LetStmt("y", num(2)),
        )
        self.assertTrue(is_clean(p))

    def test_redeclaration_in_child_scope_is_shadowing_not_error(self):
        p = prog(
            LetStmt("x", num(1)),
            ForStmt(
                "i",
                [num(1)],
                [
                    LetStmt("x", num(99)),  # shadows outer x
                ],
            ),
        )
        errs = errors_of(p)
        # Should have NO errors (shadow warning only)
        self.assertEqual(len(errs), 0)


# class for checking use before assignment

class TestUseBeforeAssignment(unittest.TestCase):
    def test_let_refers_to_later_let(self):
        p = prog(
            LetStmt("x", ident("y")),
            LetStmt("y", num(5)),
        )
        self.assertTrue(has_error_containing(p, "y"))

    def test_let_refers_to_itself(self):
        p = prog(LetStmt("x", add(ident("x"), num(1))))
        self.assertTrue(has_error_containing(p, "x"))

    def test_let_refers_to_prior_let_is_fine(self):
        p = prog(
            LetStmt("a", num(3)),
            LetStmt("b", mul(ident("a"), num(2))),
        )
        self.assertTrue(is_clean(p))

    def test_param_used_before_declared(self):
        p = prog(
            LetStmt("x", mul(ident("t"), num(2))),
            ParamStmt("t", rng(0, 10, 1)),
        )
        self.assertTrue(has_error_containing(p, "t"))



# class for checking setting on wrong kind

class TestSetOnWrongKind(unittest.TestCase):
    def test_set_on_shape(self):
        p = prog(
            prim("circle", "C"),
            SetStmt("C", num(50)),
        )
        self.assertTrue(has_error_containing(p, "C"))

    def test_set_on_function(self):
        p = prog(
            DefineStmt("f", [], [ReturnStmt(num(1))]),
            SetStmt("f", num(0)),
        )
        self.assertTrue(has_error_containing(p, "f"))

    def test_set_on_let_is_fine(self):
        p = prog(
            LetStmt("r", num(5)),
            SetStmt("r", num(10)),
        )
        self.assertTrue(is_clean(p))

    def test_set_on_param_is_fine(self):
        p = prog(
            ParamStmt("t", rng(0, 10, 1)),
            SetStmt("t", num(5)),
        )
        self.assertTrue(is_clean(p))

    def test_set_on_loop_var_is_error(self):
        p = prog(
            ForStmt(
                "i",
                [num(1), num(2)],
                [
                    SetStmt("i", num(99)),
                ],
            )
        )
        self.assertTrue(has_error_containing(p, "i"))


# class for checking sweeping on wrong kind

class TestSweepOnWrongKind(unittest.TestCase):
    def test_sweep_on_let(self):
        p = prog(
            LetStmt("r", num(5)),
            SweepStmt(["r"], speed=None),
        )
        self.assertTrue(has_error_containing(p, "r"))

    def test_sweep_on_shape(self):
        p = prog(
            prim("circle", "C"),
            SweepStmt(["C"], speed=None),
        )
        self.assertTrue(has_error_containing(p, "C"))

    def test_sweep_on_param_is_fine(self):
        p = prog(
            ParamStmt("t", rng(0, 10, 1)),
            SweepStmt(["t"], speed=None),
        )
        self.assertTrue(is_clean(p))

    def test_sweep_multiple_params(self):
        p = prog(
            ParamStmt("t", rng(0, 5, 1)),
            ParamStmt("s", rng(0, 5, 1)),
            SweepStmt(["t", "s"], speed=None),
        )
        self.assertTrue(is_clean(p))



# class for checking wrong no of args

class TestWrongArgCount(unittest.TestCase):
    def test_too_few_args(self):
        p = prog(
            DefineStmt("f", ["a", "b"], [ReturnStmt(add(ident("a"), ident("b")))]),
            CallStmt("f", [num(1)]),
        )
        self.assertTrue(has_error_containing(p, "f"))

    def test_too_many_args(self):
        p = prog(
            DefineStmt("f", ["a"], [ReturnStmt(ident("a"))]),
            CallStmt("f", [num(1), num(2), num(3)]),
        )
        self.assertTrue(has_error_containing(p, "f"))

    def test_correct_arg_count(self):
        p = prog(
            DefineStmt("add2", ["a", "b"], [ReturnStmt(add(ident("a"), ident("b")))]),
            CallStmt("add2", [num(1), num(2)]),
        )
        self.assertTrue(is_clean(p))

    def test_zero_arg_function(self):
        p = prog(
            DefineStmt("greet", [], [ReturnStmt(num(0))]),
            CallStmt("greet", []),
        )
        self.assertTrue(is_clean(p))

    def test_zero_arg_with_args_errors(self):
        p = prog(
            DefineStmt("greet", [], [ReturnStmt(num(0))]),
            CallStmt("greet", [num(1)]),
        )
        self.assertTrue(has_error_containing(p, "greet"))


# class for checking return statement outside the class

class TestReturnOutsideFunction(unittest.TestCase):
    def test_return_at_top_level(self):
        p = prog(ReturnStmt(num(42)))
        self.assertTrue(has_error_containing(p, "return"))

    def test_return_inside_function_is_fine(self):
        p = prog(
            DefineStmt("f", [], [ReturnStmt(num(1))]),
        )
        self.assertTrue(is_clean(p))

    def test_return_inside_if_outside_function(self):
        p = prog(
            IfStmt(
                condition=cmp(">", num(1), num(0)),
                body=[ReturnStmt(num(1))],
                else_ifs=[],
                else_body=None,
            )
        )
        self.assertTrue(has_error_containing(p, "return"))

    def test_return_inside_for_outside_function(self):
        p = prog(ForStmt("i", [num(1)], [ReturnStmt(num(0))]))
        self.assertTrue(has_error_containing(p, "return"))


# class for type checking in expressions

class TestTypeCheckingInExpressions(unittest.TestCase):
    def test_string_in_arithmetic(self):
        p = prog(LetStmt("x", add(slit("hello"), num(1))))
        self.assertTrue(has_error_containing(p, "String literal"))

    def test_ratio_in_arithmetic(self):
        p = prog(LetStmt("x", add(ratio(1, 2), num(3))))
        self.assertTrue(has_error_containing(p, "Ratio literal"))

    def test_shape_in_arithmetic(self):
        p = prog(
            prim("circle", "C"),
            LetStmt("x", add(ident("C"), num(1))),
        )
        self.assertTrue(has_error_containing(p, "SHAPE"))

    def test_function_name_as_value(self):
        p = prog(
            DefineStmt("f", [], [ReturnStmt(num(1))]),
            LetStmt("x", add(ident("f"), num(1))),
        )
        self.assertTrue(has_error_containing(p, "FUNCTION"))

    def test_number_in_arithmetic_is_fine(self):
        p = prog(LetStmt("x", add(num(2), num(3))))
        self.assertTrue(is_clean(p))

    def test_param_in_arithmetic_is_fine(self):
        p = prog(
            ParamStmt("t", rng(0, 10, 1)),
            LetStmt("doubled", mul(ident("t"), num(2))),
        )
        self.assertTrue(is_clean(p))

    def test_let_in_arithmetic_is_fine(self):
        p = prog(
            LetStmt("r", num(5)),
            LetStmt("area", mul(ident("r"), ident("r"))),
        )
        self.assertTrue(is_clean(p))


# class for warning about return statement in functions


class TestFunctionReturnConsistency(unittest.TestCase):
    def test_function_with_no_return_warns(self):
        p = prog(
            DefineStmt(
                "side_effect",
                [],
                [
                    LetStmt("x", num(5)),
                ],
            ),
        )
        self.assertTrue(has_warning_containing(p, "no 'return'"))

    def test_function_with_return_no_warning(self):
        p = prog(
            DefineStmt("f", ["n"], [ReturnStmt(mul(ident("n"), num(2)))]),
        )
        self.assertFalse(has_warning_containing(p, "no 'return'"))

    def test_function_with_conditional_return(self):
        p = prog(
            DefineStmt(
                "g",
                ["x"],
                [
                    IfStmt(
                        condition=cmp(">", ident("x"), num(0)),
                        body=[ReturnStmt(ident("x"))],
                        else_ifs=[],
                        else_body=None,
                    )
                ],
            ),
        )
        self.assertFalse(has_warning_containing(p, "no 'return'"))



# class for checking argument type

class TestArgumentTypeChecking(unittest.TestCase):
    def test_shape_passed_as_arg_warns(self):
        p = prog(
            prim("circle", "C"),
            DefineStmt("double", ["n"], [ReturnStmt(mul(ident("n"), num(2)))]),
            CallStmt("double", [ident("C")]),
        )
        self.assertTrue(has_warning_containing(p, "SHAPE"))

    def test_numeric_arg_is_fine(self):
        p = prog(
            LetStmt("r", num(5)),
            DefineStmt("double", ["n"], [ReturnStmt(mul(ident("n"), num(2)))]),
            CallStmt("double", [ident("r")]),
        )
        self.assertFalse(has_warning_containing(p, "SHAPE"))



class TestShadowingRules(unittest.TestCase):
    def test_let_shadows_outer_let(self):
        p = prog(
            LetStmt("x", num(1)),
            ForStmt(
                "i",
                [num(1)],
                [
                    LetStmt("x", num(99)),
                ],
            ),
        )
        self.assertTrue(has_warning_containing(p, "shadows"))

    def test_loop_var_shadows_outer(self):
        p = prog(
            LetStmt("i", num(0)),
            ForStmt("i", [num(1), num(2)], []),
        )
        self.assertTrue(has_warning_containing(p, "shadows"))

    def test_function_param_shadows_outer(self):
        p = prog(
            LetStmt("n", num(10)),
            DefineStmt("f", ["n"], [ReturnStmt(ident("n"))]),
        )
        self.assertTrue(has_warning_containing(p, "shadows"))

    def test_no_shadowing_different_names(self):
        p = prog(
            LetStmt("x", num(1)),
            ForStmt(
                "i",
                [num(1)],
                [
                    LetStmt("y", num(2)),
                ],
            ),
        )
        self.assertFalse(has_warning_containing(p, "shadows"))


# class for checking parameter range validation


class TestParamRangeValidation(unittest.TestCase):
    def test_zero_step_is_error(self):
        p = prog(ParamStmt("t", RangeSpec(num(0), num(10), num(0))))
        self.assertTrue(has_error_containing(p, "step cannot be zero"))

    def test_positive_step_start_greater_than_end_warns(self):
        p = prog(ParamStmt("t", RangeSpec(num(10), num(0), num(1))))
        self.assertTrue(has_warning_containing(p, "no frames"))

    def test_negative_step_start_less_than_end_warns(self):
        p = prog(ParamStmt("t", RangeSpec(num(0), num(10), num(-1))))
        self.assertTrue(has_warning_containing(p, "no frames"))

    def test_valid_range_positive_step(self):
        p = prog(ParamStmt("t", rng(0, 10, 1)))
        self.assertFalse(has_error_containing(p, "step"))
        self.assertFalse(has_warning_containing(p, "no frames"))

    def test_valid_range_negative_step(self):
        p = prog(ParamStmt("t", rng(10, 0, -1)))
        self.assertFalse(has_error_containing(p, "step"))
        self.assertFalse(has_warning_containing(p, "no frames"))


# class for checking dead code in program.

class TestDeadCode(unittest.TestCase):
    def test_stmt_after_return_warns(self):
        p = prog(
            DefineStmt(
                "f",
                [],
                [
                    ReturnStmt(num(1)),
                    LetStmt("dead", num(2)),  # unreachable
                ],
            ),
        )
        self.assertTrue(has_warning_containing(p, "Unreachable"))

    def test_two_stmts_after_return_warns_twice(self):
        p = prog(
            DefineStmt(
                "f",
                [],
                [
                    ReturnStmt(num(1)),
                    LetStmt("a", num(2)),
                    LetStmt("b", num(3)),
                ],
            ),
        )
        warns = warnings_of(p)
        unreachable = [w for w in warns if "Unreachable" in w]
        self.assertGreaterEqual(len(unreachable), 2)

    def test_return_at_end_no_dead_code(self):
        p = prog(
            DefineStmt(
                "f",
                ["n"],
                [
                    LetStmt("doubled", mul(ident("n"), num(2))),
                    ReturnStmt(ident("doubled")),
                ],
            ),
        )
        self.assertFalse(has_warning_containing(p, "Unreachable"))

    def test_no_dead_code_outside_function(self):
        p = prog(
            LetStmt("x", num(1)),
            LetStmt("y", num(2)),
        )
        self.assertFalse(has_warning_containing(p, "Unreachable"))


# class for correct tests

class TestHappyPath(unittest.TestCase):
    def test_empty_program(self):
        self.assertTrue(is_clean(Program([])))

    def test_basic_circle(self):
        p = prog(prim("circle", "C", [prop("radius", num(50))]))
        self.assertTrue(is_clean(p))

    def test_let_and_shape(self):
        p = prog(
            LetStmt("r", num(50)),
            prim("circle", "C", [prop("radius", ident("r"))]),
        )
        self.assertTrue(is_clean(p))

    def test_param_and_sweep(self):
        p = prog(
            ParamStmt("t", rng(0, 10, 1)),
            SweepStmt(["t"], speed=None),
        )
        self.assertTrue(is_clean(p))

    def test_define_and_call(self):
        p = prog(
            DefineStmt("sq", ["n"], [ReturnStmt(mul(ident("n"), ident("n")))]),
            CallStmt("sq", [num(5)]),
        )
        self.assertTrue(is_clean(p))

    def test_if_else(self):
        p = prog(
            LetStmt("x", num(0)),
            IfStmt(
                condition=cmp(">", num(5), num(3)),
                body=[SetStmt("x", num(1))],
                else_ifs=[],
                else_body=[SetStmt("x", num(2))],
            ),
        )
        self.assertTrue(is_clean(p))

    def test_for_loop(self):
        p = prog(
            LetStmt("total", num(0)),
            ForStmt(
                "v",
                [num(1), num(2), num(3)],
                [
                    SetStmt("total", add(ident("total"), ident("v"))),
                ],
            ),
        )
        self.assertTrue(is_clean(p))

    def test_assert_valid(self):
        p = prog(
            LetStmt("r", num(5)),
            AssertStmt(cmp(">", ident("r"), num(0))),
        )
        self.assertTrue(is_clean(p))

    def test_derived_midpoint(self):
        p = prog(
            prim("segment", "AB"),
            DerivedDecl("midpoint", "M", ["AB"]),
        )
        self.assertTrue(is_clean(p))

    def test_label_declared_shape(self):
        p = prog(
            prim("circle", "C"),
            LabelStmt("C", "unit circle"),
        )
        self.assertTrue(is_clean(p))

    def test_transform_reflect(self):
        p = prog(
            prim("line", "L"),
            prim("triangle", "T"),
            ReflectStmt("T", "L"),
        )
        self.assertTrue(is_clean(p))

    def test_constraint_stmt(self):
        p = prog(
            prim("line", "L1"),
            prim("line", "L2"),
            ConstraintStmt("L1", RelConstraint("parallel_to", "L2")),
        )
        self.assertTrue(is_clean(p))

    def test_measure_distance(self):
        p = prog(
            prim("point", "A"),
            prim("point", "B"),
            DistanceMeasure("A", "B", num(30)),
        )
        self.assertTrue(is_clean(p))

    def test_note_and_grid(self):
        p = prog(NoteStmt("a note"), GridStmt())
        self.assertTrue(is_clean(p))

    def test_complex_program(self):
        p = prog(
            LetStmt("r", num(50)),
            prim("circle", "C", [prop("radius", ident("r"))]),
            ParamStmt("t", rng(0, 360, 5)),
            DefineStmt(
                "scale_r", ["factor"], [ReturnStmt(mul(ident("r"), ident("factor")))]
            ),
            CallStmt("scale_r", [num(2)]),
            SweepStmt(["t"], speed=None),
            AssertStmt(cmp(">", ident("r"), num(0))),
            LabelStmt("C", "main"),
        )
        self.assertTrue(is_clean(p))


# class for collecting errors

class TestErrorAccumulation(unittest.TestCase):
    def test_multiple_errors_collected(self):
        p = prog(
            LabelStmt("X", "missing"),  
            SetStmt("Y", num(5)),  
        )
        errs = errors_of(p)
        self.assertGreaterEqual(len(errs), 2)

    def test_errors_and_warnings_together(self):
        p = prog(
            LetStmt("x", num(1)),
            ForStmt(
                "x",
                [num(1)],
                [  # x shadows → warning
                    SetStmt("ghost", num(0)),  # ghost undeclared → error
                ],
            ),
        )
        errs = errors_of(p)
        warns = warnings_of(p)
        self.assertGreaterEqual(len(errs), 1)
        self.assertGreaterEqual(len(warns), 1)



class TestAnalyseConvenienceFunction(unittest.TestCase):
    def test_returns_list(self):
        result = analyse(Program([]))
        self.assertIsInstance(result, list)

    def test_returns_semantic_error_objects(self):
        p = prog(LabelStmt("Missing", "text"))
        result = analyse(p)
        self.assertGreater(len(result), 0)
        self.assertIsInstance(result[0], SemanticError)

    def test_str_representation(self):
        err = SemanticError("something went wrong", severity="error")
        self.assertIn("ERROR", str(err))
        self.assertIn("something went wrong", str(err))

    def test_warning_str_representation(self):
        warn = SemanticError("heads up", severity="warning")
        self.assertIn("WARNING", str(warn))


if __name__ == "__main__":
    unittest.main()
