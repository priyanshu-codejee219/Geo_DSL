from __future__ import annotations

from typing import List, Union

from dataclass import dataclass


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
