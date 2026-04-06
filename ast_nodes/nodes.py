from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Union

from lexer import TokenType


@dataclass
class NumberLiteral:
    value: float

    def __eq__(self, other: object) -> bool:
        return isinstance(other, NumberLiteral) and self.value == other.value


@dataclass
class AngleLiteral:
    degrees: float

    def __eq__(self, other: object) -> bool:
        return isinstance(other, AngleLiteral) and self.degrees == other.degrees


@dataclass
class RatioLiteral:
    left: float
    right: float

    def __eq__(self, other: object) -> bool:
        return (
            isinstance(other, RatioLiteral)
            and self.left == other.left
            and self.right == other.right
        )


@dataclass
class StringLiteral:
    value: str

    def __eq__(self, other: object) -> bool:
        return isinstance(other, StringLiteral) and self.value == other.value


@dataclass
class IdentExpr:
    name: str

    def __eq__(self, other: object) -> bool:
        return isinstance(other, IdentExpr) and self.name == other.name


@dataclass
class CallExpr:
    name: str
    args: List["Expr"]


@dataclass
class VectorExpr:
    x: "Expr"
    y: "Expr"


@dataclass
class BinOp:
    op: str
    left: "Expr"
    right: "Expr"


@dataclass
class UnaryOp:
    op: str  # - only
    operand: "Expr"


Expr = Union[
    NumberLiteral,
    AngleLiteral,
    RatioLiteral,
    StringLiteral,
    IdentExpr,
    CallExpr,
    VectorExpr,
    BinOp,
    UnaryOp,
]


@dataclass
class CmpExpr:
    op: str
    left: Expr
    right: Expr


@dataclass
class GeometricPred:
    subject: str
    relation: str
    target: str


BoolExpr = Union[CmpExpr, GeometricPred]


@dataclass
class PropAssign:
    name: str
    value: Expr


@dataclass
class PosConstraint:
    kind: str
    targets: List[Expr]


@dataclass
class RelConstraint:
    kind: str
    target: str


ConstraintClause = Union[PosConstraint, RelConstraint]


@dataclass
class PrimitiveDecl:
    shape_kw: TokenType  # prim_kw
    name: str  # ident
    props: List[PropAssign]
    args: List[str] = field(default_factory=list)  # of INdent {IDENT}
    constraints: List[ConstraintClause] = field(default_factory=list)
    constraint: Optional[ConstraintClause] = None


@dataclass
class DerivedDecl:
    kind: str
    name: Optional[str]
    args: List[str]  #
    locus_var: Optional[str] = field(default=None)
    locus_constraint: Optional[BoolExpr] = field(default=None)


ShapeDecl = Union[PrimitiveDecl, DerivedDecl]


@dataclass
class ConstraintStmt:
    subject: str  # the ident
    constraint: ConstraintClause  # pos or rel


ConstraintStmtGroup = Union[ConstraintStmt]


@dataclass
class DistanceMeasure:
    point_a: str
    point_b: str
    value: Expr


@dataclass
class AngleMeasure:
    angle_name: str
    value: AngleLiteral


@dataclass
class LengthMeasure:
    shape_name: str
    value: Expr


@dataclass
class RadiusMeasure:
    shape_name: str
    value: Expr


@dataclass
class RatioMeasure:
    shape_a: str
    shape_b: str
    value: RatioLiteral


@dataclass
class AreaMeasure:
    shape_name: str
    value: Expr


@dataclass
class PerimeterMeasure:
    shape_name: str
    value: Expr


MeasureStmt = Union[
    DistanceMeasure,
    AngleMeasure,
    LengthMeasure,
    RadiusMeasure,
    RatioMeasure,
    AreaMeasure,
    PerimeterMeasure,
]


@dataclass
class LetStmt:
    name: str
    value: Expr


@dataclass
class SetStmt:
    name: str
    value: Expr


@dataclass
class RangeSpec:
    start: Expr
    end: Expr
    step: Expr


@dataclass
class ParamStmt:
    name: str
    range_spec: RangeSpec


VarStmt = Union[LetStmt, SetStmt, ParamStmt]


@dataclass
class SweepStmt:
    params: List[str]
    speed: Optional[Expr]


@dataclass
class ElseIfClause:
    condition: BoolExpr
    body: "List[Statement]"


@dataclass
class IfStmt:
    condition: BoolExpr
    body: "List[Statement]"
    else_ifs: List[ElseIfClause]
    else_body: "Optional[List[Statement]]"


@dataclass
class ForStmt:
    var: str
    values: List[Expr]
    body: "List[Statement]"


ControlStmt = Union[SweepStmt, IfStmt, ForStmt]


@dataclass
class ReturnStmt:
    value: Optional[Expr]


@dataclass
class DefineStmt:
    name: str
    params: List[str]
    body: "List[Statement]"


@dataclass
class CallStmt:
    name: str
    args: List[Expr]


FunctionStmt = Union[DefineStmt, CallStmt]


@dataclass
class ReflectStmt:
    target: str
    over: str


@dataclass
class RotateStmt:
    target: str
    by: AngleLiteral
    about: str


@dataclass
class ScaleStmt:
    target: str
    by: Expr


@dataclass
class TranslateStmt:
    target: str
    by: VectorExpr


TransformStmt = Union[ReflectStmt, RotateStmt, ScaleStmt, TranslateStmt]


@dataclass
class AssertStmt:
    expr: BoolExpr


AssertStmtGroup = Union[AssertStmt]


@dataclass
class LabelStmt:
    target: str
    text: str


@dataclass
class NoteStmt:
    text: str


@dataclass
class HideStmt:
    targets: List[str]


@dataclass
class GridStmt:
    pass


RenderStmt = Union[
    LabelStmt,
    NoteStmt,
    HideStmt,
    GridStmt,
]


Statement = Union[
    PrimitiveDecl,
    DerivedDecl,
    ConstraintStmt,
    DistanceMeasure,
    AngleMeasure,
    LengthMeasure,
    RadiusMeasure,
    RatioMeasure,
    AreaMeasure,
    PerimeterMeasure,
    LetStmt,
    SetStmt,
    ParamStmt,
    SweepStmt,
    IfStmt,
    ForStmt,
    DefineStmt,
    CallStmt,
    ReflectStmt,
    RotateStmt,
    ScaleStmt,
    TranslateStmt,
    AssertStmt,
    LabelStmt,
    NoteStmt,
    HideStmt,
    GridStmt,
    MeasureStmt,
    ReturnStmt,
]

@dataclass
class Program:
    statements: List[Statement]
