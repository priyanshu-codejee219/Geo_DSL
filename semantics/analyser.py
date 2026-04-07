from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

# Make the project root importable when running the file directly
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



# Symbol kinds maintained in the symbol table.
class Kind(Enum):
    SHAPE = auto() 
    LET = auto()
    PARAM = auto()  
    FUNCTION = auto()
    LOOP_VAR = auto()
    ARG = auto()  


_SHAPE_KINDS: Set[str] = {
    "point",
    "segment",
    "line",
    "ray",
    "circle",
    "arc",
    "triangle",
    "rectangle",
    "rhombus",
    "regular_poly",
    "polygon",
    "ellipse",
    "parallelogram",
}

_DERIVED_KINDS: Set[str] = {
    "midpoint",
    "intersection",
    "perpendicular_bisector",
    "angle_bisector",
    "circumcircle",
    "incircle",
    "convex_hull",
    "locus",
}


 

@dataclass
class SemanticError:
    """One semantic error or warning detected during analysis."""

    message: str
    severity: str = "error"  # or "warning"

    def __str__(self) -> str:
        tag = "ERROR" if self.severity == "error" else "WARNING"
        return f"[Semantic {tag}] {self.message}"


# Structure of statement info.

@dataclass
class _Symbol:
    name: str
    kind: Kind
    # For number of formal parameters in the function.
    arity: Optional[int] = None
    param_range: Optional[Tuple[float, float, float]] = None

# Maintains the scope, (where the analyzer is currently in the .geo file), says whether in (global, in a function, if/else block)

class _Scope:
    
    def __init__(self, parent: Optional["_Scope"] = None) -> None:
        self._table: Dict[str, _Symbol] = {}
        self.parent = parent

    # We record the order in which names are declared 

    _declared_order: List[str] = field(default_factory=list)

    def declare(self, name: str, kind: Kind, **kw) -> bool:
        """
        Add *name* to this scope. Returns False if the name already exists
        in *this exact scope* (redeclaration), True otherwise.
        """
        exists_here = name in self._table
        self._table[name] = _Symbol(name, kind, **kw)
        return not exists_here  

    def lookup(self, name: str) -> Optional[_Symbol]:
        """Walk up the scope chain; return None if not found."""
        if name in self._table:
            return self._table[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None

    def lookup_local(self, name: str) -> Optional[_Symbol]:
        """Look up only in this scope (not parents)."""
        return self._table.get(name)

    def exists_in_parent(self, name: str) -> bool:
        """Return True if *name* is visible in any enclosing scope."""
        if self.parent is None:
            return False
        return self.parent.lookup(name) is not None

    def child(self) -> "_Scope":
        return _Scope(parent=self)
    

class SemanticAnalyser:
    
    def __init__(self) -> None:
        self._errors: List[SemanticError] = []
        self._scope: _Scope = _Scope() 
        self._in_function: bool = False  
        self._function_name: str = ""  
        self._function_has_return: bool = False
        self._seen_return: bool = False


    def analyse(self, program: Program) -> List[SemanticError]:
        """Run all checks and return the list of errors / warnings."""
        self._errors.clear()
        self._scope = _Scope()
        self._in_function = False
        self._seen_return = False
        for stmt in program.statements:
            self._check_stmt(stmt, self._scope)
        return list(self._errors)


    def _err(self, msg: str) -> None:
        self._errors.append(SemanticError(msg, severity="error"))

    def _warn(self, msg: str) -> None:
        self._errors.append(SemanticError(msg, severity="warning"))

    #checks every statement

    def _check_stmt(self, stmt: Statement, scope: _Scope) -> None:

        if self._seen_return and self._in_function:
            self._warn(
                f"Unreachable statement after 'return' in function "
                f"'{self._function_name}': {type(stmt).__name__}"
            )

        # checks shape declaration statements
        if isinstance(stmt, PrimitiveDecl):
            self._check_primitive_decl(stmt, scope)
        elif isinstance(stmt, DerivedDecl):
            self._check_derived_decl(stmt, scope)

        # checks constarint statements
        elif isinstance(stmt, ConstraintStmt):
            self._check_constraint_stmt(stmt, scope)

        # checks measure statements
        elif isinstance(
            stmt,
            (
                DistanceMeasure,
                AngleMeasure,
                LengthMeasure,
                RadiusMeasure,
                RatioMeasure,
                AreaMeasure,
                PerimeterMeasure,
            )
        ):
            self._check_measure(stmt, scope)

        # checks variable statements
        elif isinstance(stmt, LetStmt):
            self._check_let(stmt, scope)
        elif isinstance(stmt, SetStmt):
            self._check_set(stmt, scope)
        elif isinstance(stmt, ParamStmt):
            self._check_param(stmt, scope)

        # checks conrol flow statements
        elif isinstance(stmt, SweepStmt):
            self._check_sweep(stmt, scope)
        elif isinstance(stmt, IfStmt):
            self._check_if(stmt, scope)
        elif isinstance(stmt, ForStmt):
            self._check_for(stmt, scope)

        # checks function related statements
        elif isinstance(stmt, DefineStmt):
            self._check_define(stmt, scope)
        elif isinstance(stmt, CallStmt):
            self._check_call(stmt, scope)
        elif isinstance(stmt, ReturnStmt):
            self._check_return(stmt, scope)

        # checks trnansformation statements
        elif isinstance(stmt, ReflectStmt):
            self._check_reflect(stmt, scope)
        elif isinstance(stmt, RotateStmt):
            self._check_rotate(stmt, scope)
        elif isinstance(stmt, ScaleStmt):
            self._check_scale(stmt, scope)
        elif isinstance(stmt, TranslateStmt):
            self._check_translate(stmt, scope)

        # checks assertion statements
        elif isinstance(stmt, AssertStmt):
            self._check_bool_expr(stmt.expr, scope)

        # checks rendering and display statements
        elif isinstance(stmt, LabelStmt):
            self._check_label(stmt, scope)
        elif isinstance(stmt, HideStmt):
            self._check_hide(stmt, scope)
        elif isinstance(stmt, (NoteStmt, GridStmt)):
            pass  # nothing to check
        elif isinstance(stmt, MeasureStmt):
            pass  # dimension annotations checked above in the measure branch

    def _check_primitive_decl(self, stmt: PrimitiveDecl, scope: _Scope) -> None:
        pass

    def _check_derived_decl(self, stmt: DerivedDecl, scope: _Scope) -> None:
        pass

    def _check_constraint_stmt(self, stmt: ConstraintStmt, scope: _Scope) -> None:
        pass

    def _check_constraint_clause(self, clause, scope: _Scope) -> None:
        pass

    def _check_measure(self, stmt, scope: _Scope) -> None:
        pass

    def _check_let(self, stmt: LetStmt, scope: _Scope) -> None:
        pass

    def _check_set(self, stmt: SetStmt, scope: _Scope) -> None:
        pass

    def _check_param(self, stmt: ParamStmt, scope: _Scope) -> None:
        pass

    def _check_sweep(self, stmt: SweepStmt, scope: _Scope) -> None:
        pass

    def _check_if(self, stmt: IfStmt, scope: _Scope) -> None:
        pass

    def _check_for(self, stmt: ForStmt, scope: _Scope) -> None:
        pass

    def _check_define(self, stmt: DefineStmt, scope: _Scope) -> None:
        pass

    def _check_call(self, stmt: CallStmt, scope: _Scope) -> None:
        pass

    def _check_return(self, stmt: ReturnStmt, scope: _Scope) -> None:
        pass

    def _check_reflect(self, stmt: ReflectStmt, scope: _Scope) -> None:
        pass

    def _check_rotate(self, stmt: RotateStmt, scope: _Scope) -> None:
        pass

    def _check_scale(self, stmt: ScaleStmt, scope: _Scope) -> None:
        pass

    def _check_translate(self, stmt: TranslateStmt, scope: _Scope) -> None:
        pass

    def _check_label(self, stmt: LabelStmt, scope: _Scope) -> None:
        pass

    def _check_hide(self, stmt: HideStmt, scope: _Scope) -> None:
        pass

    def _check_expr( self, expr, scope: _Scope, numeric_required: bool = False) -> None:
        pass

    def _check_bool_expr(self, expr, scope: _Scope) -> None:
        pass


    def _require_declared(self, name: str, scope: _Scope) -> Optional[_Symbol]:
        sym = scope.lookup(name)
        if sym is None:
            self._err(f"Undefined name '{name}'")
        return sym

    def _require_shape(
        self,
        name: str,
        scope: _Scope,
        context: str = "",
    ) -> None:
        sym = scope.lookup(name)
        if sym is None:
            self._err(
                f"Undefined name '{name}'" + (f" in '{context}'" if context else "")
            )
        elif sym.kind != Kind.SHAPE:
            self._err(
                f"'{name}' is a {sym.kind.name}, expected a SHAPE"
                + (f" in '{context}'" if context else "")
            )

    @staticmethod
    def _literal_value(expr) -> Optional[float]:
        """Return the float value of a number literal, or None if not literal."""
        if isinstance(expr, NumberLiteral):
            return float(expr.value)
        if isinstance(expr, AngleLiteral):
            return float(expr.degrees)
        return None

def analyse(program: Program) -> List[SemanticError]:

    return SemanticAnalyser().analyse(program)
