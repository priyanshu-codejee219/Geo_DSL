import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from ast_nodes.nodes import (
    AngleLiteral,
    BinOp,
    CallStmt,
    CmpExpr,
    DefineStmt,
    DistanceMeasure,
    ForStmt,
    GeometricPred,
    HideStmt,
    IdentExpr,
    LabelStmt,
    LetStmt,
    NumberLiteral,
    ParamStmt,
    PrimitiveDecl,
    Program,
    PropAssign,
    RangeSpec,
    RatioLiteral,
    ReflectStmt,
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


#class redeclaration checking.
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

if __name__ == "__main__":
    unittest.main()