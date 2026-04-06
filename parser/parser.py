from __future__ import annotations

from typing import List, Optional

from ast_nodes.nodes import (
    AngleLiteral,
    AngleMeasure,
    AreaMeasure,
    AssertStmt,
    BinOp,
    BoolExpr,
    CallExpr,
    CallStmt,
    CmpExpr,
    ConstraintClause,
    ConstraintStmt,
    DefineStmt,
    DerivedDecl,
    DistanceMeasure,
    ElseIfClause,
    Expr,
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
    Statement,
    StringLiteral,
    SweepStmt,
    TranslateStmt,
    UnaryOp,
    VectorExpr,
)
from lexer import Token
from lexer.token_types import TokenType

from .parser_utils import ParseError, advance, expect, peek

_PRIM_KWS = frozenset(
    {
        TokenType.POINT,
        TokenType.SEGMENT,
        TokenType.LINE,
        TokenType.RAY,
        TokenType.CIRCLE,
        TokenType.ARC,
        TokenType.TRIANGLE,
        TokenType.RECTANGLE,
        TokenType.RHOMBUS,
        TokenType.REGULAR_POLY,
        TokenType.POLYGON,
        TokenType.ELLIPSE,
        TokenType.PARALLELOGRAM,
    }
)

_DERIVED_KWS = frozenset(
    {
        TokenType.MIDPOINT,
        TokenType.INTERSECTION,
        TokenType.PERPENDICULAR_BISECTOR,
        TokenType.ANGLE_BISECTOR,
        TokenType.CIRCUMCIRCLE,
        TokenType.INCIRCLE,
        TokenType.CONVEX_HULL,
        TokenType.LOCUS,
    }
)

_PROP_NAMES = frozenset(
    {
        TokenType.RADIUS,
        TokenType.LENGTH,
        TokenType.ANGLE,
        TokenType.AREA,
        TokenType.PERIMETER,
        TokenType.SIDES,
    }
)

_REL_CONSTRAINT_KWS = frozenset(
    {
        TokenType.PARALLEL_TO,
        TokenType.PERPENDICULAR_TO,
        TokenType.TANGENT_TO,
        TokenType.BISECTS,
    }
)

_POS_CONSTRAINT_KWS = frozenset(
    {
        TokenType.AT,
        TokenType.ON,
        TokenType.PASSES_THROUGH,
        TokenType.CENTERED_AT,
    }
)

_CONSTRAINT_KWS = _REL_CONSTRAINT_KWS | _POS_CONSTRAINT_KWS

_CMP_OPS = frozenset(
    {
        TokenType.EQ,
        TokenType.NEQ,
        TokenType.LT,
        TokenType.GT,
        TokenType.LTE,
        TokenType.GTE,
    }
)

_GEO_PRED_KWS = frozenset(
    {
        TokenType.ON,
        TokenType.PARALLEL_TO,
        TokenType.PERPENDICULAR_TO,
        TokenType.TANGENT_TO,
        TokenType.BISECTS,
        TokenType.PASSES_THROUGH,
        TokenType.CENTERED_AT,
    }
)

_MEASURE_KWS = frozenset(
    {
        TokenType.DISTANCE,
        TokenType.ANGLE,
        TokenType.LENGTH,
        TokenType.RADIUS,
        TokenType.RATIO,
        TokenType.AREA,
        TokenType.PERIMETER,
    }
)

_TRANSFORM_KWS = frozenset(
    {
        TokenType.REFLECT,
        TokenType.ROTATE,
        TokenType.SCALE,
        TokenType.TRANSLATE,
    }
)

_RENDER_KWS = frozenset(
    {
        TokenType.LABEL,
        TokenType.NOTE,
        TokenType.HIDE,
        TokenType.GRID,
        TokenType.MEASURE,
    }
)


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self._tokens: List[Token] = tokens
        self._pos: int = 0
        self._skip_newlines()

    def parse(self) -> Program:
        statements: List[Statement] = []
        while self._cur().type != TokenType.EOF:
            statements.append(self._parse_statement())
            self._skip_newlines()
         
        return Program(statements = statements)

    def _parse_statement(self) -> Statement:
        tok = self._cur()
        tt = tok.type

        if tt in _PRIM_KWS:
            return self._parse_primitive_decl()
        if tt in _DERIVED_KWS:
            return self._parse_derived_decl()

        if tt in _MEASURE_KWS:
            return self._parse_measure_stmt()

        if tt == TokenType.LET:
            return self._parse_let_stmt()
        if tt == TokenType.SET:
            return self._parse_set_stmt()
        if tt == TokenType.PARAM:
            return self._parse_param_stmt()

        if tt == TokenType.SWEEP:
            return self._parse_sweep_stmt()
        if tt == TokenType.IF:
            return self._parse_if_stmt()
        if tt == TokenType.FOR:
            return self._parse_for_stmt()

        if tt == TokenType.DEFINE:
            return self._parse_define_stmt()
        if tt == TokenType.CALL:
            return self._parse_call_stmt()
        if tt == TokenType.RETURN:
            return self._parse_return_stmt()

        if tt in _TRANSFORM_KWS:
            return self._parse_transform_stmt()

        if tt == TokenType.ASSERT:
            return self._parse_assert_stmt()

        if tt in _RENDER_KWS:
            return self._parse_render_stmt()

        if (
            tt == TokenType.IDENT
            and peek(self._tokens, self._pos, 1).type in _CONSTRAINT_KWS
        ):
            return self._parse_constraint_stmt()

        raise ParseError("Unexpected token — cannot begin a statement", tok)

    def _parse_primitive_decl(self) -> PrimitiveDecl:
        kw_tok, self._pos = advance(self._tokens, self._pos)
        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)

        args: List[str] = []
        props: List[PropAssign] = []
        constraints: List[ConstraintClause] = []

        if self._cur().type == TokenType.OF:
            self._pos += 1
            first_arg, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            args.append(first_arg.value)
            while self._cur().type == TokenType.IDENT:
                next_arg, self._pos = advance(self._tokens, self._pos)
                args.append(next_arg.value)

        if self._cur().type == TokenType.WITH:
            self._pos += 1
            self._skip_newlines()
            props.append(self._parse_prop_assign())
            while self._cur().type == TokenType.COMMA:
                self._pos += 1
                self._skip_newlines()
                props.append(self._parse_prop_assign())

        while self._cur().type in _CONSTRAINT_KWS:
            constraints.append(self._parse_constraint_clause())

        return PrimitiveDecl(
            shape_kw=kw_tok.type,
            name=name_tok.value,
            props=props,
            args=args,
            constraints=constraints,
            constraint=constraints[0] if constraints else None,
        )

    def _parse_prop_assign(self) -> PropAssign:
        prop_tok, self._pos = expect(
            self._tokens,
            self._pos,
            TokenType.IDENT,
            *tuple(_PROP_NAMES),
        )
        _, self._pos = expect(self._tokens, self._pos, TokenType.EQ)
        value = self._parse_expr()
        return PropAssign(name=prop_tok.value, value=value)

    def _parse_derived_decl(self) -> DerivedDecl:
        kw_tok, self._pos = advance(self._tokens, self._pos)
        kw = kw_tok.type

        if kw == TokenType.LOCUS:
            return self._parse_locus()

        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(self._tokens, self._pos, TokenType.OF)

        args: List[str] = []

        if kw == TokenType.ANGLE_BISECTOR:
            a_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            b_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            c_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            args = [a_tok.value, b_tok.value, c_tok.value]

        elif kw == TokenType.INTERSECTION:
            a_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            b_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            args = [a_tok.value, b_tok.value]

        elif kw == TokenType.CONVEX_HULL:
            first_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            args.append(first_tok.value)
            while self._cur().type == TokenType.IDENT:
                more_tok, self._pos = advance(self._tokens, self._pos)
                args.append(more_tok.value)

        else:
            arg_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            args.append(arg_tok.value)

        return DerivedDecl(
            kind=kw_tok.value,
            name=name_tok.value,
            args=args,
        )

    def _parse_locus(self) -> DerivedDecl:
        _, self._pos = expect(self._tokens, self._pos, TokenType.OF)
        _, self._pos = expect(self._tokens, self._pos, TokenType.POINT)
        var_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(self._tokens, self._pos, TokenType.LBRACE)
        self._skip_newlines()

        kw_tok = self._cur()
        if kw_tok.type != TokenType.IDENT or kw_tok.value != "constraint":
            raise ParseError("Expected keyword 'constraint' inside locus body", kw_tok)
        self._pos += 1

        bool_ex = self._parse_bool_expr()
        self._skip_newlines()
        _, self._pos = expect(self._tokens, self._pos, TokenType.RBRACE)

        return DerivedDecl(
            kind="locus",
            name=None,
            args=[],
            locus_var=var_tok.value,
            locus_constraint=bool_ex,
        )

    def _parse_constraint_clause(self) -> ConstraintClause:
        tt = self._cur().type
        if tt in _POS_CONSTRAINT_KWS:
            return self._parse_pos_constraint()
        if tt in _REL_CONSTRAINT_KWS:
            return self._parse_rel_constraint()
        raise ParseError("Expected a constraint keyword", self._cur())

    def _parse_pos_constraint(self) -> PosConstraint:
        kw_tok, self._pos = advance(self._tokens, self._pos)
        kw = kw_tok.type

        if kw == TokenType.AT:
            expr = self._parse_expr()
            return PosConstraint(kind="at", targets=[expr])

        if kw == TokenType.ON:
            name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            return PosConstraint(kind="on", targets=[IdentExpr(name_tok.value)])

        if kw == TokenType.PASSES_THROUGH:
            first_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            targets: List[Expr] = [IdentExpr(first_tok.value)]
            while self._cur().type == TokenType.IDENT:
                more_tok, self._pos = advance(self._tokens, self._pos)
                targets.append(IdentExpr(more_tok.value))
            return PosConstraint(kind="passes_through", targets=targets)

        if kw == TokenType.CENTERED_AT:
            name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            return PosConstraint(
                kind="centered_at", targets=[IdentExpr(name_tok.value)]
            )

        raise ParseError("Unrecognised positional constraint", kw_tok)

    def _parse_rel_constraint(self) -> RelConstraint:
        kw_tok, self._pos = advance(self._tokens, self._pos)
        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        return RelConstraint(kind=kw_tok.value, target=name_tok.value)

    def _parse_constraint_stmt(self) -> ConstraintStmt:
        subj_tok, self._pos = advance(self._tokens, self._pos)
        constraint = self._parse_constraint_clause()
        return ConstraintStmt(subject=subj_tok.value, constraint=constraint)

    def _parse_measure_stmt(self):
        kw_tok, self._pos = advance(self._tokens, self._pos)
        kw = kw_tok.type

        if kw == TokenType.DISTANCE:
            a_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            b_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            _, self._pos = expect(self._tokens, self._pos, TokenType.EQ)
            value = self._parse_expr()
            return DistanceMeasure(
                point_a=a_tok.value, point_b=b_tok.value, value=value
            )

        if kw == TokenType.ANGLE:
            name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            _, self._pos = expect(self._tokens, self._pos, TokenType.EQ)
            ang_val = self._parse_angle_val()
            return AngleMeasure(angle_name=name_tok.value, value=ang_val)

        if kw in (
            TokenType.LENGTH,
            TokenType.RADIUS,
            TokenType.AREA,
            TokenType.PERIMETER,
        ):
            _, self._pos = expect(self._tokens, self._pos, TokenType.OF)
            name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            _, self._pos = expect(self._tokens, self._pos, TokenType.EQ)
            value = self._parse_expr()
            if kw == TokenType.LENGTH:
                return LengthMeasure(shape_name=name_tok.value, value=value)
            if kw == TokenType.RADIUS:
                return RadiusMeasure(shape_name=name_tok.value, value=value)
            if kw == TokenType.AREA:
                return AreaMeasure(shape_name=name_tok.value, value=value)
            return PerimeterMeasure(shape_name=name_tok.value, value=value)

        if kw == TokenType.RATIO:
            _, self._pos = expect(self._tokens, self._pos, TokenType.OF)
            a_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            _, self._pos = expect(self._tokens, self._pos, TokenType.TO)
            b_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            _, self._pos = expect(self._tokens, self._pos, TokenType.EQ)
            ratio_v = self._parse_ratio_val()
            return RatioMeasure(shape_a=a_tok.value, shape_b=b_tok.value, value=ratio_v)

        raise ParseError("Unrecognised measurement keyword", kw_tok)

    def _parse_let_stmt(self) -> LetStmt:
        self._pos += 1
        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(self._tokens, self._pos, TokenType.EQ)
        value = self._parse_expr()
        return LetStmt(name=name_tok.value, value=value)

    def _parse_set_stmt(self) -> SetStmt:
        self._pos += 1
        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(self._tokens, self._pos, TokenType.EQ)
        value = self._parse_expr()
        return SetStmt(name=name_tok.value, value=value)

    def _parse_param_stmt(self) -> ParamStmt:
        self._pos += 1
        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        range_spec = self._parse_range_spec()
        return ParamStmt(name=name_tok.value, range_spec=range_spec)

    def _parse_range_spec(self) -> RangeSpec:
        _, self._pos = expect(self._tokens, self._pos, TokenType.FROM)
        start = self._parse_expr()
        _, self._pos = expect(self._tokens, self._pos, TokenType.TO)
        end = self._parse_expr()
        _, self._pos = expect(self._tokens, self._pos, TokenType.STEP)
        step = self._parse_expr()
        return RangeSpec(start=start, end=end, step=step)

    def _parse_sweep_stmt(self) -> SweepStmt:
        self._pos += 1
        first_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        params = [first_tok.value]
        while self._cur().type == TokenType.COMMA:
            self._pos += 1
            more_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            params.append(more_tok.value)

        speed: Optional[Expr] = None
        if self._cur().type == TokenType.SPEED:
            self._pos += 1
            speed = self._parse_expr()

        return SweepStmt(params=params, speed=speed)

    def _parse_if_stmt(self) -> IfStmt:
        self._pos += 1
        condition = self._parse_bool_expr()
        _, self._pos = expect(self._tokens, self._pos, TokenType.LBRACE)
        body = self._parse_block()
        _, self._pos = expect(self._tokens, self._pos, TokenType.RBRACE)

        else_ifs: List[ElseIfClause] = []
        else_body: Optional[List[Statement]] = None

        while (
            self._cur().type == TokenType.ELSE
            and peek(self._tokens, self._pos, 1).type == TokenType.IF
        ):
            self._pos += 1
            self._pos += 1
            ei_cond = self._parse_bool_expr()
            _, self._pos = expect(self._tokens, self._pos, TokenType.LBRACE)
            ei_body = self._parse_block()
            _, self._pos = expect(self._tokens, self._pos, TokenType.RBRACE)
            else_ifs.append(ElseIfClause(condition=ei_cond, body=ei_body))

        if self._cur().type == TokenType.ELSE:
            self._pos += 1
            _, self._pos = expect(self._tokens, self._pos, TokenType.LBRACE)
            else_body = self._parse_block()
            _, self._pos = expect(self._tokens, self._pos, TokenType.RBRACE)

        return IfStmt(
            condition=condition,
            body=body,
            else_ifs=else_ifs,
            else_body=else_body,
        )

    def _parse_for_stmt(self) -> ForStmt:
        self._pos += 1
        var_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(self._tokens, self._pos, TokenType.IN)
        _, self._pos = expect(self._tokens, self._pos, TokenType.LBRACKET)

        values: List[Expr] = [self._parse_expr()]
        while self._cur().type == TokenType.COMMA:
            self._pos += 1
            values.append(self._parse_expr())

        _, self._pos = expect(self._tokens, self._pos, TokenType.RBRACKET)
        _, self._pos = expect(self._tokens, self._pos, TokenType.LBRACE)
        body = self._parse_block()
        _, self._pos = expect(self._tokens, self._pos, TokenType.RBRACE)

        return ForStmt(var=var_tok.value, values=values, body=body)

    def _parse_block(self) -> List[Statement]:
        stmts: List[Statement] = []
        self._skip_newlines()
        while self._cur().type not in (TokenType.RBRACE, TokenType.EOF):
            stmts.append(self._parse_statement())
            self._skip_newlines()
        return stmts

    def _parse_define_stmt(self) -> DefineStmt:
        self._pos += 1
        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(self._tokens, self._pos, TokenType.LPAREN)

        params: List[str] = []
        if self._cur().type == TokenType.IDENT:
            p_tok, self._pos = advance(self._tokens, self._pos)
            params.append(p_tok.value)
            while self._cur().type == TokenType.COMMA:
                self._pos += 1
                p_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
                params.append(p_tok.value)

        _, self._pos = expect(self._tokens, self._pos, TokenType.RPAREN)
        _, self._pos = expect(self._tokens, self._pos, TokenType.LBRACE)
        body = self._parse_block()
        _, self._pos = expect(self._tokens, self._pos, TokenType.RBRACE)

        return DefineStmt(name=name_tok.value, params=params, body=body)

    def _parse_call_stmt(self) -> CallStmt:
        self._pos += 1
        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(self._tokens, self._pos, TokenType.LPAREN)

        args: List[Expr] = []
        if self._cur().type != TokenType.RPAREN:
            args.append(self._parse_expr())
            while self._cur().type == TokenType.COMMA:
                self._pos += 1
                args.append(self._parse_expr())

        _, self._pos = expect(self._tokens, self._pos, TokenType.RPAREN)
        return CallStmt(name=name_tok.value, args=args)

    def _parse_return_stmt(self) -> ReturnStmt:
        self._pos += 1
        tt = self._cur().type
        if tt in (TokenType.RBRACE, TokenType.EOF, TokenType.NEWLINE):
            return ReturnStmt(value=None)
        return ReturnStmt(value=self._parse_expr())

    def _parse_transform_stmt(self):
        kw_tok, self._pos = advance(self._tokens, self._pos)
        kw = kw_tok.type

        target_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(
            self._tokens,
            self._pos,
            TokenType.BY if kw != TokenType.REFLECT else TokenType.OVER,
        )

        if kw == TokenType.REFLECT:
            over_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            return ReflectStmt(target=target_tok.value, over=over_tok.value)

        if kw == TokenType.ROTATE:
            angle = self._parse_angle_val()
            _, self._pos = expect(self._tokens, self._pos, TokenType.ABOUT)
            about_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            return RotateStmt(target=target_tok.value, by=angle, about=about_tok.value)

        if kw == TokenType.SCALE:
            factor = self._parse_expr()
            return ScaleStmt(target=target_tok.value, by=factor)

        if kw == TokenType.TRANSLATE:
            vec = self._parse_vector_expr()
            return TranslateStmt(target=target_tok.value, by=vec)

        raise ParseError("Unrecognised transformation keyword", kw_tok)

    def _parse_assert_stmt(self) -> AssertStmt:
        self._pos += 1
        return AssertStmt(expr=self._parse_bool_expr())

    def _parse_render_stmt(self):
        kw_tok, self._pos = advance(self._tokens, self._pos)
        kw = kw_tok.type

        if kw == TokenType.LABEL:
            tgt_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            str_tok, self._pos = expect(self._tokens, self._pos, TokenType.STRING)
            return LabelStmt(target=tgt_tok.value, text=str_tok.value)

        if kw == TokenType.NOTE:
            str_tok, self._pos = expect(self._tokens, self._pos, TokenType.STRING)
            return NoteStmt(text=str_tok.value)

        if kw == TokenType.HIDE:
            first_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            targets = [first_tok.value]
            while self._cur().type == TokenType.IDENT:
                more_tok, self._pos = advance(self._tokens, self._pos)
                targets.append(more_tok.value)
            return HideStmt(targets=targets)

        if kw == TokenType.GRID:
            return GridStmt()

        if kw == TokenType.MEASURE:
            tgt_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            return MeasureStmt(target=tgt_tok.value)

        raise ParseError("Unrecognised render keyword", kw_tok)

    def _parse_expr(self) -> Expr:
        return self._parse_add_expr()

    def _parse_add_expr(self) -> Expr:
        left = self._parse_mul_expr()
        while self._cur().type in (TokenType.PLUS, TokenType.MINUS):
            op_tok, self._pos = advance(self._tokens, self._pos)
            right = self._parse_mul_expr()
            left = BinOp(op=op_tok.value, left=left, right=right)
        return left

    def _parse_mul_expr(self) -> Expr:
        left = self._parse_unary()
        while self._cur().type in (TokenType.STAR, TokenType.SLASH):
            op_tok, self._pos = advance(self._tokens, self._pos)
            right = self._parse_unary()
            left = BinOp(op=op_tok.value, left=left, right=right)
        return left

    def _parse_unary(self) -> Expr:
        if self._cur().type == TokenType.MINUS:
            self._pos += 1
            return UnaryOp(op="-", operand=self._parse_primary())
        return self._parse_primary()

    def _parse_primary(self) -> Expr:
        tok = self._cur()
        tt = tok.type

        if tt == TokenType.NUMBER:
            self._pos += 1
            val = float(tok.value)

            if self._cur().type == TokenType.DEG:
                self._pos += 1
                return AngleLiteral(degrees=val)

            if self._cur().type == TokenType.COLON:
                self._pos += 1
                rhs_tok, self._pos = expect(self._tokens, self._pos, TokenType.NUMBER)
                return RatioLiteral(left=val, right=float(rhs_tok.value))

            return NumberLiteral(value=val)

        if tt == TokenType.STRING:
            self._pos += 1
            return StringLiteral(value=tok.value)

        if tt in (TokenType.IDENT, TokenType.DISTANCE):
            name = tok.value
            self._pos += 1
            if self._cur().type == TokenType.LPAREN:
                self._pos += 1
                args: List[Expr] = []
                if self._cur().type != TokenType.RPAREN:
                    args.append(self._parse_expr())
                    while self._cur().type == TokenType.COMMA:
                        self._pos += 1
                        args.append(self._parse_expr())
                _, self._pos = expect(self._tokens, self._pos, TokenType.RPAREN)
                return CallExpr(name=name, args=args)

            if tt == TokenType.IDENT:
                return IdentExpr(name=name)
            raise ParseError("Expected a function call", tok)

        if tt == TokenType.LPAREN:
            self._pos += 1
            first = self._parse_expr()

            if self._cur().type == TokenType.COMMA:
                self._pos += 1
                second = self._parse_expr()
                _, self._pos = expect(self._tokens, self._pos, TokenType.RPAREN)
                return VectorExpr(x=first, y=second)

            _, self._pos = expect(self._tokens, self._pos, TokenType.RPAREN)
            return first

        raise ParseError("Expected a primary expression", tok)

    def _parse_bool_expr(self) -> BoolExpr:
        if (
            self._cur().type == TokenType.IDENT
            and peek(self._tokens, self._pos, 1).type in _GEO_PRED_KWS
        ):
            subj_tok, self._pos = advance(self._tokens, self._pos)
            rel_tok, self._pos = advance(self._tokens, self._pos)
            tgt_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
            return GeometricPred(
                subject=subj_tok.value,
                relation=rel_tok.value,
                target=tgt_tok.value,
            )

        left = self._parse_expr()
        if self._cur().type not in _CMP_OPS:
            raise ParseError(
                "Expected a comparison operator in boolean expression", self._cur()
            )
        op_tok, self._pos = advance(self._tokens, self._pos)
        right = self._parse_expr()
        return CmpExpr(op=op_tok.value, left=left, right=right)

    def _parse_angle_val(self) -> AngleLiteral:
        num_tok, self._pos = expect(self._tokens, self._pos, TokenType.NUMBER)
        _, self._pos = expect(self._tokens, self._pos, TokenType.DEG)
        return AngleLiteral(degrees=float(num_tok.value))

    def _parse_ratio_val(self) -> RatioLiteral:
        lhs_tok, self._pos = expect(self._tokens, self._pos, TokenType.NUMBER)
        _, self._pos = expect(self._tokens, self._pos, TokenType.COLON)
        rhs_tok, self._pos = expect(self._tokens, self._pos, TokenType.NUMBER)
        return RatioLiteral(left=float(lhs_tok.value), right=float(rhs_tok.value))

    def _parse_vector_expr(self) -> VectorExpr:
        _, self._pos = expect(self._tokens, self._pos, TokenType.LPAREN)
        x = self._parse_expr()
        _, self._pos = expect(self._tokens, self._pos, TokenType.COMMA)
        y = self._parse_expr()
        _, self._pos = expect(self._tokens, self._pos, TokenType.RPAREN)
        return VectorExpr(x=x, y=y)

    def _cur(self) -> Token:
        return (
            self._tokens[self._pos]
            if self._pos < len(self._tokens)
            else self._tokens[-1]
        )

    def _skip_newlines(self) -> None:
        while (
            self._pos < len(self._tokens)
            and self._tokens[self._pos].type == TokenType.NEWLINE
        ):
            self._pos += 1


def parse(tokens: List[Token]) -> Program:
    return Parser(tokens).parse()
