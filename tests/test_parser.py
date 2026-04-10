import pytest

from ast_nodes import (
    AngleLiteral,
    AngleMeasure,
    AreaMeasure,
    # assert
    AssertStmt,
    BinOp,
    CallExpr,
    CallStmt,
    # bool
    CmpExpr,
    # constraint stmt
    ConstraintStmt,
    DefineStmt,
    DerivedDecl,
    # measure stmts
    DistanceMeasure,
    ElseIfClause,
    ForStmt,
    GeometricPred,
    GridStmt,
    HideStmt,
    IdentExpr,
    IfStmt,
    # render stmts
    LabelStmt,
    LengthMeasure,
    # var stmts
    LetStmt,
    NoteStmt,
    # expressions
    NumberLiteral,
    ParamStmt,
    PerimeterMeasure,
    PosConstraint,
    # shape decls
    PrimitiveDecl,
    Program,
    # shape decl pieces
    PropAssign,
    RadiusMeasure,
    RangeSpec,
    RatioLiteral,
    RatioMeasure,
    # transform stmts
    ReflectStmt,
    RelConstraint,
    # function stmts
    ReturnStmt,
    RotateStmt,
    ScaleStmt,
    SetStmt,
    StringLiteral,
    # control stmts
    SweepStmt,
    TranslateStmt,
    UnaryOp,
    VectorExpr,
)
from lexer import Lexer
from lexer.token_types import TokenType
from parser import ParseError, parse


def parse_src(src: str) -> Program:
    return parse(Lexer(src).tokenize())


def first(src: str):
    return parse_src(src).statements[0]


# RULE 2


class TestPrimitiveDecl:
    def test_point(self):
        node = first("point A")
        assert isinstance(node, PrimitiveDecl)
        assert node.shape_kw == TokenType.POINT
        assert node.name == "A"
        assert node.props == []
        assert node.constraint is None

    def test_circle(self):
        node = first("circle C")
        assert node.shape_kw == TokenType.CIRCLE
        assert node.name == "C"

    def test_segment(self):
        node = first("segment AB")
        assert node.shape_kw == TokenType.SEGMENT
        assert node.name == "AB"

    def test_prim_keywords(self):
        cases = [
            ("point", TokenType.POINT),
            ("segment", TokenType.SEGMENT),
            ("line", TokenType.LINE),
            ("ray", TokenType.RAY),
            ("circle", TokenType.CIRCLE),
            ("arc", TokenType.ARC),
            ("triangle", TokenType.TRIANGLE),
            ("rectangle", TokenType.RECTANGLE),
            ("rhombus", TokenType.RHOMBUS),
            ("regular_poly", TokenType.REGULAR_POLY),
            ("polygon", TokenType.POLYGON),
            ("ellipse", TokenType.ELLIPSE),
            ("parallelogram", TokenType.PARALLELOGRAM),
        ]
        for kw, expected in cases:
            node = first(f"{kw} X")
            assert node.shape_kw == expected, f"Failed for {kw!r}"

    def test_circle_with_radius_literal(self):
        node = first("circle C with radius = 50")
        assert len(node.props) == 1
        p = node.props[0]
        assert isinstance(p, PropAssign)
        assert p.name == "radius"
        assert p.value == NumberLiteral(50.0)

    def test_circle_with_radius_ident(self):
        node = first("circle C with radius = r")
        assert node.props[0].value == IdentExpr("r")

    def test_circle_with_radius_expr(self):
        node = first("circle C with radius = r * 2")
        p = node.props[0]
        assert isinstance(p.value, BinOp)
        assert p.value.op == "*"
        assert p.value.left == IdentExpr("r")
        assert p.value.right == NumberLiteral(2.0)

    def test_ellipse_two_props(self):
        node = first("ellipse E with radius = 30, length = 60")
        assert len(node.props) == 2
        assert node.props[0].name == "radius"
        assert node.props[0].value == NumberLiteral(30.0)
        assert node.props[1].name == "length"
        assert node.props[1].value == NumberLiteral(60.0)

    def test_rhombus_with_angle(self):
        node = first("rhombus R with angle = 60deg")
        p = node.props[0]
        assert p.name == "angle"
        assert isinstance(p.value, AngleLiteral)
        assert p.value.degrees == 60.0

    def test_all_prop_names(self):
        for prop in ("radius", "length", "angle", "area", "perimeter"):
            node = first(f"circle C with {prop} = 10")
            assert node.props[0].name == prop


# rule 4


class TestConstraintClause:
    def test_at_ident(self):
        node = first("point A at origin")
        c = node.constraint
        assert isinstance(c, PosConstraint)
        assert c.kind == "at"
        assert c.targets == [IdentExpr("origin")]

    def test_at_vector(self):
        node = first("point A at (100, 200)")
        c = node.constraint
        assert c.kind == "at"
        assert isinstance(c.targets[0], VectorExpr)
        assert c.targets[0].x == NumberLiteral(100.0)
        assert c.targets[0].y == NumberLiteral(200.0)

    def test_on_ident(self):
        node = first("point D on C")
        c = node.constraint
        assert isinstance(c, PosConstraint)
        assert c.kind == "on"
        assert c.targets == [IdentExpr("C")]

    def test_passes_through_single(self):
        node = first("line L passes_through A")
        c = node.constraint
        assert c.kind == "passes_through"
        assert c.targets == [IdentExpr("A")]

    def test_passes_through_multiple(self):
        node = first("circle C passes_through A B C")
        c = node.constraint
        assert c.kind == "passes_through"
        assert c.targets == [IdentExpr("A"), IdentExpr("B"), IdentExpr("C")]

    def test_centered_at(self):
        node = first("circle C centered_at O")
        c = node.constraint
        assert isinstance(c, PosConstraint)
        assert c.kind == "centered_at"
        assert c.targets == [IdentExpr("O")]

    def test_parallel_to(self):
        node = first("line L2 parallel_to L1")
        c = node.constraint
        assert isinstance(c, RelConstraint)
        assert c.kind == "parallel_to"
        assert c.target == "L1"

    def test_perpendicular_to(self):
        node = first("line L perpendicular_to AB")
        c = node.constraint
        assert c.kind == "perpendicular_to"
        assert c.target == "AB"

    def test_tangent_to(self):
        node = first("circle C2 tangent_to C1")
        c = node.constraint
        assert c.kind == "tangent_to"
        assert c.target == "C1"

    def test_bisects(self):
        node = first("ray R bisects AB")
        c = node.constraint
        assert c.kind == "bisects"
        assert c.target == "AB"

    def test_props_and_rel_constraint(self):
        node = first("line L of A tangent_to C")
        assert isinstance(node, PrimitiveDecl)
        assert node.shape_kw == TokenType.LINE
        assert node.name == "L"
        assert node.args == ["A"]
        assert len(node.constraints) == 1
        assert node.constraints[0] == RelConstraint("tangent_to", "C")

    def test_props_and_pos_constraint(self):
        node = first("circle C with radius = 30 centered_at O")
        assert node.props[0].name == "radius"
        assert node.constraint.kind == "centered_at"
        assert node.constraint.targets == [IdentExpr("O")]


# rule 3


class TestDerivedDecl:
    def test_midpoint(self):
        node = first("midpoint M of AB")
        assert isinstance(node, DerivedDecl)
        assert node.kind == "midpoint"
        assert node.name == "M"
        assert node.args == ["AB"]

    def test_intersection(self):
        node = first("intersection P of L1 L2")
        assert node.kind == "intersection"
        assert node.name == "P"
        assert node.args == ["L1", "L2"]

    def test_perpendicular_bisector(self):
        node = first("perpendicular_bisector PB of AB")
        assert node.kind == "perpendicular_bisector"
        assert node.name == "PB"
        assert node.args == ["AB"]

    def test_angle_bisector(self):
        node = first("angle_bisector BR of A B C")
        assert node.kind == "angle_bisector"
        assert node.name == "BR"
        assert node.args == ["A", "B", "C"]

    def test_circumcircle(self):
        node = first("circumcircle CC of T")
        assert node.kind == "circumcircle"
        assert node.name == "CC"
        assert node.args == ["T"]

    def test_incircle(self):
        node = first("incircle IC of T")
        assert node.kind == "incircle"
        assert node.name == "IC"
        assert node.args == ["T"]

    def test_convex_hull_three_args(self):
        node = first("convex_hull CH of A B C")
        assert node.kind == "convex_hull"
        assert node.args == ["A", "B", "C"]

    def test_convex_hull_five_args(self):
        node = first("convex_hull CH of A B C D E")
        assert node.args == ["A", "B", "C", "D", "E"]

    def test_locus_cmp_constraint(self):
        src = "locus of point P { constraint distance_PA = 50 }"
        node = first(src)
        assert isinstance(node, DerivedDecl)
        assert node.kind == "locus"
        assert node.name is None
        assert node.locus_var == "P"
        assert isinstance(node.locus_constraint, CmpExpr)

    def test_locus_geometric_pred_constraint(self):
        src = "locus of point P { constraint P on C }"
        node = first(src)
        assert isinstance(node.locus_constraint, GeometricPred)
        assert node.locus_constraint.subject == "P"
        assert node.locus_constraint.relation == "on"
        assert node.locus_constraint.target == "C"

    def test_locus_distance_call_constraint(self):
        src = "locus of point P { constraint distance(P, A) = distance(P, B) }"
        node = first(src)
        assert isinstance(node.locus_constraint, CmpExpr)
        assert isinstance(node.locus_constraint.left, CallExpr)
        assert isinstance(node.locus_constraint.right, CallExpr)
        assert node.locus_constraint.left.name == "distance"
        assert node.locus_constraint.right.name == "distance"


# rule 5


class TestConstraintStmt:
    def test_ident_parallel_to(self):
        node = first("L1 parallel_to L2")
        assert isinstance(node, ConstraintStmt)
        assert node.subject == "L1"
        assert isinstance(node.constraint, RelConstraint)
        assert node.constraint.kind == "parallel_to"
        assert node.constraint.target == "L2"

    def test_ident_perpendicular_to(self):
        node = first("L1 perpendicular_to L2")
        assert isinstance(node, ConstraintStmt)
        assert node.constraint.kind == "perpendicular_to"

    def test_ident_tangent_to(self):
        node = first("C1 tangent_to C2")
        assert node.constraint.kind == "tangent_to"

    def test_ident_bisects(self):
        node = first("R bisects AB")
        assert node.constraint.kind == "bisects"

    def test_ident_on(self):
        node = first("D on C")
        assert isinstance(node, ConstraintStmt)
        assert node.subject == "D"
        assert isinstance(node.constraint, PosConstraint)
        assert node.constraint.kind == "on"
        assert node.constraint.targets == [IdentExpr("C")]

    def test_ident_at(self):
        node = first("A at origin")
        assert node.constraint.kind == "at"

    def test_ident_passes_through(self):
        node = first("L passes_through A B")
        c = node.constraint
        assert c.kind == "passes_through"
        assert c.targets == [IdentExpr("A"), IdentExpr("B")]

    def test_ident_centered_at(self):
        node = first("P centered_at O")
        assert node.constraint.kind == "centered_at"


class TestMeasureStmt:
    def test_distance(self):
        node = first("distance A B = 100")
        assert isinstance(node, DistanceMeasure)
        assert node.point_a == "A"
        assert node.point_b == "B"
        assert node.value == NumberLiteral(100.0)

    def test_distance_expr_rhs(self):
        node = first("distance A B = r * 2")
        assert isinstance(node.value, BinOp)

    def test_angle(self):
        node = first("angle ABC = 60deg")
        assert isinstance(node, AngleMeasure)
        assert node.angle_name == "ABC"
        assert isinstance(node.value, AngleLiteral)
        assert node.value.degrees == 60.0

    def test_length_of(self):
        node = first("length of AB = 50")
        assert isinstance(node, LengthMeasure)
        assert node.shape_name == "AB"
        assert node.value == NumberLiteral(50.0)

    def test_radius_of(self):
        node = first("radius of C = 30")
        assert isinstance(node, RadiusMeasure)
        assert node.shape_name == "C"
        assert node.value == NumberLiteral(30.0)

    def test_ratio_of(self):
        node = first("ratio of AB to CD = 2:3")
        assert isinstance(node, RatioMeasure)
        assert node.shape_a == "AB"
        assert node.shape_b == "CD"
        assert isinstance(node.value, RatioLiteral)
        assert node.value.left == 2.0
        assert node.value.right == 3.0

    def test_area_of(self):
        node = first("area of T = 150")
        assert isinstance(node, AreaMeasure)
        assert node.shape_name == "T"
        assert node.value == NumberLiteral(150.0)

    def test_perimeter_of(self):
        node = first("perimeter of P = 300")
        assert isinstance(node, PerimeterMeasure)
        assert node.shape_name == "P"
        assert node.value == NumberLiteral(300.0)


# rule 7


class TestVarStmt:
    def test_let_number(self):
        node = first("let r = 50")
        assert isinstance(node, LetStmt)
        assert node.name == "r"
        assert node.value == NumberLiteral(50.0)

    def test_let_ident_rhs(self):
        node = first("let d = base_r")
        assert node.value == IdentExpr("base_r")

    def test_let_angle(self):
        node = first("let a = 45deg")
        assert isinstance(node.value, AngleLiteral)
        assert node.value.degrees == 45.0

    def test_let_arithmetic_expr(self):
        node = first("let r = 3 * 10 + 5")
        # top node is BinOp('+', BinOp('*', 3, 10), 5)
        assert isinstance(node.value, BinOp)
        assert node.value.op == "+"
        assert isinstance(node.value.left, BinOp)
        assert node.value.left.op == "*"

    def test_set_simple(self):
        node = first("set r = 80")
        assert isinstance(node, SetStmt)
        assert node.name == "r"
        assert node.value == NumberLiteral(80.0)

    def test_set_expr(self):
        node = first("set r = r + 10")
        assert isinstance(node, SetStmt)
        assert isinstance(node.value, BinOp)
        assert node.value.op == "+"
        assert node.value.left == IdentExpr("r")

    def test_param_integers(self):
        node = first("param r from 10 to 100 step 10")
        assert isinstance(node, ParamStmt)
        assert node.name == "r"
        rs = node.range_spec
        assert isinstance(rs, RangeSpec)
        assert rs.start == NumberLiteral(10.0)
        assert rs.end == NumberLiteral(100.0)
        assert rs.step == NumberLiteral(10.0)

    def test_param_degrees(self):
        node = first("param theta from 0deg to 180deg step 5deg")
        rs = node.range_spec
        assert isinstance(rs.start, AngleLiteral)
        assert rs.start.degrees == 0.0
        assert isinstance(rs.end, AngleLiteral)
        assert rs.end.degrees == 180.0
        assert isinstance(rs.step, AngleLiteral)
        assert rs.step.degrees == 5.0

    def test_param_ident_bounds(self):
        node = first("param r from min_r to max_r step 1")
        rs = node.range_spec
        assert isinstance(rs.start, IdentExpr)
        assert rs.start.name == "min_r"
        assert isinstance(rs.end, IdentExpr)
        assert rs.end.name == "max_r"


# rule 8


class TestControlStmt:
    def test_sweep_single(self):
        node = first("sweep theta")
        assert isinstance(node, SweepStmt)
        assert node.params == ["theta"]
        assert node.speed is None

    def test_sweep_multiple(self):
        node = first("sweep r1, r2, d")
        assert node.params == ["r1", "r2", "d"]
        assert node.speed is None

    def test_sweep_with_speed(self):
        node = first("sweep theta speed 2")
        assert node.params == ["theta"]
        assert node.speed == NumberLiteral(2.0)

    def test_sweep_multiple_with_speed(self):
        node = first("sweep r1, r2 speed 0.5")
        assert node.params == ["r1", "r2"]
        assert node.speed == NumberLiteral(0.5)

    def test_if_only(self):
        src = 'if theta > 90deg { label T "obtuse" }'
        node = first(src)
        assert isinstance(node, IfStmt)
        assert isinstance(node.condition, CmpExpr)
        assert node.condition.op == ">"
        assert len(node.body) == 1
        assert node.else_ifs == []
        assert node.else_body is None

    def test_if_else(self):
        src = "if r > 50 { circle C } else { point O }"
        node = first(src)
        assert isinstance(node, IfStmt)
        assert node.else_body is not None
        assert len(node.else_body) == 1

    def test_if_else_if_else(self):
        src = (
            'if a > 90deg { label T "obtuse" } '
            'else if a = 90deg { label T "right" } '
            'else { label T "acute" }'
        )
        node = first(src)
        assert len(node.else_ifs) == 1
        assert isinstance(node.else_ifs[0], ElseIfClause)
        assert node.else_body is not None

    def test_if_body_multiple_stmts(self):
        src = 'if r > 50 { circle C with radius = r\nlabel C "big" }'
        node = first(src)
        assert len(node.body) == 2

    def test_if_geometric_pred_condition(self):
        src = 'if P on C { label P "on circle" }'
        node = first(src)
        assert isinstance(node.condition, GeometricPred)
        assert node.condition.subject == "P"
        assert node.condition.relation == "on"
        assert node.condition.target == "C"

    # for

    def test_for_loop(self):
        src = "for n in [3, 4, 5, 6] { regular_poly P }"
        node = first(src)
        assert isinstance(node, ForStmt)
        assert node.var == "n"
        assert len(node.values) == 4
        assert node.values[0] == NumberLiteral(3.0)
        assert node.values[3] == NumberLiteral(6.0)
        assert len(node.body) == 1

    def test_for_single_value(self):
        src = "for r in [50] { circle C with radius = r }"
        node = first(src)
        assert node.values == [NumberLiteral(50.0)]

    def test_for_expr_values(self):
        src = "for r in [base * 1, base * 2] { circle C with radius = r }"
        node = first(src)
        assert all(isinstance(v, BinOp) for v in node.values)


# rule 9


class TestFunctionStmt:
    def test_define_no_params_no_return(self):
        src = "define Draw() { circle C }"
        node = first(src)
        assert isinstance(node, DefineStmt)
        assert node.name == "Draw"
        assert node.params == []
        assert len(node.body) == 1

    def test_define_one_param(self):
        src = "define Circumcircle(T) { midpoint M of T }"
        node = first(src)
        assert node.params == ["T"]

    def test_define_multiple_params(self):
        src = "define Bisect(A, B, C) { ray R }"
        node = first(src)
        assert node.params == ["A", "B", "C"]

    def test_define_with_return(self):
        src = "define GetRadius(C) { return r }"
        node = first(src)
        ret = node.body[0]
        assert isinstance(ret, ReturnStmt)
        assert ret.value == IdentExpr("r")

    def test_define_return_empty(self):
        src = "define F() { return }"
        ret = first(src).body[0]
        assert isinstance(ret, ReturnStmt)
        assert ret.value is None

    def test_define_multi_statement_body(self):
        src = (
            "define Build(T) {\n"
            "  circumcircle CC of T\n"
            "  incircle IC of T\n"
            "  return CC\n"
            "}"
        )
        node = first(src)
        assert len(node.body) == 3

    def test_call_no_args(self):
        node = first("call Draw()")
        assert isinstance(node, CallStmt)
        assert node.name == "Draw"
        assert node.args == []

    def test_call_one_arg(self):
        node = first("call Circumcircle(T)")
        assert node.name == "Circumcircle"
        assert node.args == [IdentExpr("T")]

    def test_call_multiple_args(self):
        node = first("call Bisect(A, B, C)")
        assert len(node.args) == 3
        assert node.args[0] == IdentExpr("A")

    def test_call_expr_args(self):
        node = first("call Scale(r * 2, offset + 1)")
        assert isinstance(node.args[0], BinOp)
        assert isinstance(node.args[1], BinOp)


class TestTransformStmt:
    def test_reflect(self):
        node = first("reflect ABC over L")
        assert isinstance(node, ReflectStmt)
        assert node.target == "ABC"
        assert node.over == "L"

    def test_rotate(self):
        node = first("rotate P by 72deg about O")
        assert isinstance(node, RotateStmt)
        assert node.target == "P"
        assert isinstance(node.by, AngleLiteral)
        assert node.by.degrees == 72.0
        assert node.about == "O"

    def test_scale_literal(self):
        node = first("scale C by 2")
        assert isinstance(node, ScaleStmt)
        assert node.target == "C"
        assert node.by == NumberLiteral(2.0)

    def test_scale_expr(self):
        node = first("scale C by factor * 2")
        assert isinstance(node, ScaleStmt)
        assert isinstance(node.by, BinOp)

    def test_translate(self):
        node = first("translate AB by (100, 50)")
        assert isinstance(node, TranslateStmt)
        assert node.target == "AB"
        assert isinstance(node.by, VectorExpr)
        assert node.by.x == NumberLiteral(100.0)
        assert node.by.y == NumberLiteral(50.0)

    def test_translate_negative_vector(self):
        node = first("translate AB by (-30, 0)")
        assert isinstance(node.by.x, UnaryOp)
        assert node.by.x.op == "-"


class TestAssertStmt:
    def test_assert_cmp_eq(self):
        node = first("assert len_AB = len_CD")
        assert isinstance(node, AssertStmt)
        assert isinstance(node.expr, CmpExpr)
        assert node.expr.op == "="
        assert node.expr.left == IdentExpr("len_AB")
        assert node.expr.right == IdentExpr("len_CD")

    def test_assert_cmp_neq(self):
        node = first("assert r != 0")
        assert node.expr.op == "!="

    def test_assert_cmp_gt(self):
        node = first("assert theta > 0deg")
        assert node.expr.op == ">"

    def test_assert_geometric_pred(self):
        node = first("assert P on C")
        assert isinstance(node.expr, GeometricPred)
        assert node.expr.subject == "P"
        assert node.expr.relation == "on"
        assert node.expr.target == "C"

    def test_assert_parallel_pred(self):
        node = first("assert L1 parallel_to L2")
        assert isinstance(node.expr, GeometricPred)
        assert node.expr.relation == "parallel_to"


# rule 12


class TestRenderStmt:
    def test_label(self):
        node = first('label T "my triangle"')
        assert isinstance(node, LabelStmt)
        assert node.target == "T"
        assert node.text == "my triangle"

    def test_note(self):
        node = first('note "construction complete"')
        assert isinstance(node, NoteStmt)
        assert node.text == "construction complete"

    def test_hide_single(self):
        node = first("hide helper_line")
        assert isinstance(node, HideStmt)
        assert node.targets == ["helper_line"]

    def test_hide_multiple(self):
        node = first("hide L1 L2 PB")
        assert node.targets == ["L1", "L2", "PB"]

    def test_grid(self):
        node = first("grid")
        assert isinstance(node, GridStmt)


# rule 13


class TestExpressions:
    def _e(self, src: str) -> object:
        return first(f"let _x = {src}").value

    # ── literals ──────────────────────────────────────────────────────────────

    def test_integer(self):
        assert self._e("42") == NumberLiteral(42.0)

    def test_float(self):
        assert self._e("3.14") == NumberLiteral(3.14)

    def test_angle(self):
        node = self._e("90deg")
        assert isinstance(node, AngleLiteral)
        assert node.degrees == 90.0

    def test_ratio(self):
        node = self._e("2:3")
        assert isinstance(node, RatioLiteral)
        assert node.left == 2.0
        assert node.right == 3.0

    def test_string(self):
        node = self._e('"hello"')
        assert isinstance(node, StringLiteral)
        assert node.value == "hello"

    def test_ident(self):
        assert self._e("r") == IdentExpr("r")

    def test_vector(self):
        node = self._e("(10, 20)")
        assert isinstance(node, VectorExpr)
        assert node.x == NumberLiteral(10.0)
        assert node.y == NumberLiteral(20.0)

    # arithmetic

    def test_add(self):
        node = self._e("2 + 3")
        assert isinstance(node, BinOp)
        assert node.op == "+"
        assert node.left == NumberLiteral(2.0)
        assert node.right == NumberLiteral(3.0)

    def test_sub(self):
        node = self._e("10 - 4")
        assert node.op == "-"

    def test_mul(self):
        node = self._e("3 * 7")
        assert node.op == "*"

    def test_div(self):
        node = self._e("9 / 3")
        assert node.op == "/"

    def test_precedence_mul_before_add(self):
        node = self._e("2 + 3 * 4")
        assert node.op == "+"
        assert isinstance(node.right, BinOp)
        assert node.right.op == "*"

    def test_left_associativity_add(self):
        node = self._e("1 + 2 + 3")
        assert node.op == "+"
        assert isinstance(node.left, BinOp)
        assert node.left.op == "+"

    def test_parens_override_precedence(self):
        """(2 + 3) * 4"""
        node = self._e("(2 + 3) * 4")
        assert node.op == "*"
        assert isinstance(node.left, BinOp)
        assert node.left.op == "+"

    def test_unary_minus(self):
        node = self._e("-5")
        assert isinstance(node, UnaryOp)
        assert node.op == "-"
        assert node.operand == NumberLiteral(5.0)

    def test_unary_minus_in_expr(self):
        node = self._e("10 + -3")
        assert node.op == "+"
        assert isinstance(node.right, UnaryOp)

    def test_vector_with_exprs(self):
        node = self._e("(dx * 2, dy + 5)")
        assert isinstance(node, VectorExpr)
        assert isinstance(node.x, BinOp)
        assert isinstance(node.y, BinOp)


# rul 14


class TestBoolExpr:
    def _b(self, src: str) -> object:
        return first(f"assert {src}").expr

    def test_cmp_eq(self):
        node = self._b("r = 50")
        assert isinstance(node, CmpExpr)
        assert node.op == "="
        assert node.left == IdentExpr("r")
        assert node.right == NumberLiteral(50.0)

    def test_cmp_neq(self):
        assert self._b("r != 0").op == "!="

    def test_cmp_lt(self):
        assert self._b("r < 100").op == "<"

    def test_cmp_gt(self):
        assert self._b("r > 0").op == ">"

    def test_cmp_lte(self):
        assert self._b("r <= 100").op == "<="

    def test_cmp_gte(self):
        assert self._b("r >= 0").op == ">="

    def test_cmp_angle(self):
        node = self._b("theta > 90deg")
        assert isinstance(node.right, AngleLiteral)

    def test_geo_pred_on(self):
        node = self._b("P on C")
        assert isinstance(node, GeometricPred)
        assert node.subject == "P"
        assert node.relation == "on"
        assert node.target == "C"

    def test_geo_pred_parallel_to(self):
        node = self._b("L1 parallel_to L2")
        assert node.relation == "parallel_to"

    def test_geo_pred_perpendicular_to(self):
        node = self._b("L1 perpendicular_to L2")
        assert node.relation == "perpendicular_to"

    def test_geo_pred_tangent_to(self):
        node = self._b("C1 tangent_to C2")
        assert node.relation == "tangent_to"

    def test_geo_pred_bisects(self):
        node = self._b("R bisects AB")
        assert node.relation == "bisects"

    def test_geo_pred_passes_through(self):
        node = self._b("L passes_through A")
        assert node.relation == "passes_through"

    def test_geo_pred_centered_at(self):
        node = self._b("C centered_at O")
        assert node.relation == "centered_at"


# rule 1


class TestMultiStatement:
    def test_two_stmts(self):
        prog = parse_src("point A\npoint B")
        assert len(prog.statements) == 2
        assert prog.statements[0].name == "A"
        assert prog.statements[1].name == "B"

    def test_blank_lines_ignored(self):
        prog = parse_src("\n\npoint A\n\npoint B\n\n")
        assert len(prog.statements) == 2

    def test_comments_ignored(self):
        prog = parse_src("# declare a circle\ncircle C with radius = 50")
        assert len(prog.statements) == 1

    def test_statement_types_across_groups(self):
        src = """
# classic incircle construction demo
param r from 20 to 80 step 5
let base = 100
triangle T
point A at (0, 0)
point B at (100, 0)
point C at (50, 80)
incircle IC of T
circumcircle CC of T
L1 parallel_to L2
distance A B = base
assert IC on T
assert CC centered_at O
define Build(X) {
    midpoint M of X
    return M
}
call Build(T)
reflect T over L
rotate P by 45deg about O
scale C by 2
translate AB by (10, 0)
sweep r speed 2
for n in [3, 4, 5] { regular_poly P }
label T "triangle"
note "done"
hide helper
grid
"""
        prog = parse_src(src)
        type_names = {type(s).__name__ for s in prog.statements}

        # Every grammar group must appear
        assert "ParamStmt" in type_names  # var_stmt
        assert "LetStmt" in type_names  # var_stmt
        assert "PrimitiveDecl" in type_names  # shape_decl
        assert "DerivedDecl" in type_names  # shape_decl
        assert "ConstraintStmt" in type_names  # constraint_stmt
        assert "DistanceMeasure" in type_names  # measure_stmt
        assert "AssertStmt" in type_names  # assert_stmt
        assert "DefineStmt" in type_names  # function_stmt
        assert "CallStmt" in type_names  # function_stmt
        assert "ReflectStmt" in type_names  # transform_stmt
        assert "RotateStmt" in type_names  # transform_stmt
        assert "ScaleStmt" in type_names  # transform_stmt
        assert "TranslateStmt" in type_names  # transform_stmt
        assert "SweepStmt" in type_names  # control_stmt
        assert "ForStmt" in type_names  # control_stmt
        assert "LabelStmt" in type_names  # render_stmt
        assert "NoteStmt" in type_names  # render_stmt
        assert "HideStmt" in type_names  # render_stmt
        assert "GridStmt" in type_names  # render_stmt


class TestParseErrors:
    def test_missing_ident_after_keyword(self):
        """circle with radius 50  — IDENT missing after 'circle'"""
        with pytest.raises(ParseError):
            first("circle with radius 50")

    def test_missing_eq_in_let(self):
        """let r 50  — '=' missing"""
        with pytest.raises(ParseError):
            first("let r 50")

    def test_missing_eq_in_set(self):
        with pytest.raises(ParseError):
            first("set r 50")

    def test_missing_from_in_param(self):
        with pytest.raises(ParseError):
            first("param r 10 to 100 step 5")

    def test_missing_to_in_param(self):
        with pytest.raises(ParseError):
            first("param r from 10 100 step 5")

    def test_missing_step_in_param(self):
        with pytest.raises(ParseError):
            first("param r from 10 to 100 5")

    def test_empty_for_value_list(self):
        """for n in [] { } — empty list is invalid (grammar requires ≥1 expr)"""
        with pytest.raises(ParseError):
            first("for n in [] { point A }")

    def test_unclosed_brace_in_if(self):
        with pytest.raises(ParseError):
            first("if r > 50 { circle C")

    def test_lone_operator_not_statement(self):
        with pytest.raises(ParseError):
            first("+ 50")

    def test_missing_of_in_derived(self):
        """midpoint M AB  — 'of' missing"""
        with pytest.raises(ParseError):
            first("midpoint M AB")

    def test_missing_angle_kw_in_angle_bisector(self):
        """angle_bisector BR of ABC  — 'angle' keyword missing"""
        with pytest.raises(ParseError):
            first("angle_bisector BR of ABC")

    def test_rotate_missing_about(self):
        with pytest.raises(ParseError):
            first("rotate P by 45deg O")

    def test_reflect_missing_over(self):
        with pytest.raises(ParseError):
            first("reflect T L")

    def test_locus_missing_constraint_keyword(self):
        with pytest.raises(ParseError):
            first("locus of point P { P on C }")
