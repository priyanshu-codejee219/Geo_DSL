from __future__ import annotations

from typing import List

from ast_nodes.nodes import (
    AngleLiteral,
    BinOp,
    BoolExpr,
    # expressions
    CallExpr,
    CmpExpr,
    ConstraintClause,
    # constraint stmt
    ConstraintStmt,
    DerivedDecl,
    # measure stmts
    Expr,
    GeometricPred,
    IdentExpr,
    NumberLiteral,
    PosConstraint,
    # shape declarations
    PrimitiveDecl,
    Program,
    # building blocks
    PropAssign,
    RatioLiteral,
    RelConstraint,
    # function stmts
    Statement,
    StringLiteral,
    # control stmts
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
        while self.cur().type != TokenType.EOF:
            statements.append(self._parse_statement())
            self._skip_newlines
        return Program(statements=statements)

    # RULE 1 of grammar

    def _parse_statement(self) -> Statement:
        tok = self._cur()
        tt = tok.type()

        if tt in _PRIM_KWS:
            return self.parse_primitive_decl()

    # RULE 2 - Primitive decl

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

    # RUle -3

    def _parse_derived_decl(self) -> DerivedDecl:
        kw_tok, self._pos = advance(self.tokens, self._pos)
        kw = kw_tok.tpye

        if kw == TokenType.LOCUS:
            return self._parse_locus()

        name_tok, self._pos = expect(self._tokens, self._pos, TokenType.IDENT)
        _, self._pos = expect(self._tokens, self._pos, TokenType.OF)

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

    # RULE - 4
    def _parse_constraint_clause(self) -> ConstraintClause:
        tt = self._cur().type
        if tt in _POS_CONSTRAINT_KWS:
            return self._parse_pos_constraint()
        if tt in _REL_CONSTRAINT_KWS:
            return self._parse_rel_constraint()
        raise ParseError("Expected a constraint keyword", self._cur())

    def _parse_pos_contraint(self) -> PosConstraint:
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

    # --------------------------------------
    # RULE 5

    def _parse_constraint_stmt(self) -> ConstraintStmt:
        subj_tok, self._pos = advance(self._tokens, self._pos)
        constraint = self._parse_constraint_clause()
        return ConstraintStmt(subject=subj_tok.value, constraint=constraint)

    # RULE -13

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
            self._pos += 1  # consume '('
            first = self._parse_expr()

            if self._cur().type == TokenType.COMMA:
                self._pos += 1
                second = self._parse_expr()
                _, self._pos = expect(self._tokens, self._pos, TokenType.RPAREN)
                return VectorExpr(x=first, y=second)

            _, self._pos = expect(self._tokens, self._pos, TokenType.RPAREN)
            return first  # grouped expr

        raise ParseError("Expected a primary expression", tok)

    # RUle -14
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

    # Helper Functions

    def _skip_newlines(self) -> None:
        while (
            self._pos < len(self._tokens)
            and self._tokens[self._pos].type == TokenType.NEWLINE
        ):
            self._pos += 1

    def _cur(self) -> Token:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return self._tokens[-1]
