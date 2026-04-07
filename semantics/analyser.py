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
        name = stmt.name
        if scope.lookup_local(name) is not None:
            self._err(f"Redeclaration of '{name}': already declared in this scope")
        elif scope.exists_in_parent(name):
            self._warn(f"'{name}' shadows a name declared in an outer scope")
        scope.declare(name, Kind.SHAPE)

        # Evaluate property expressions
        for pa in stmt.props:
            self._check_expr(pa.value, scope, numeric_required=True)

        # Check constraint targets
        for clause in stmt.constraints:
            self._check_constraint_clause(clause, scope)

    def _check_derived_decl(self, stmt: DerivedDecl, scope: _Scope) -> None:
        name = stmt.name
        if name is not None:
            if scope.lookup_local(name) is not None:
                self._err(f"Redeclaration of '{name}': already declared in this scope")
            elif scope.exists_in_parent(name):
                self._warn(f"'{name}' shadows a name declared in an outer scope")
            scope.declare(name, Kind.SHAPE)

        # All args must be declared
        for arg in stmt.args:
            self._require_declared(arg, scope)

        # Locus constraint: free point variable is declared only within its scope
        if stmt.locus_var is not None:
            child = scope.child()
            child.declare(stmt.locus_var, Kind.SHAPE)
            if stmt.locus_constraint is not None:
                self._check_bool_expr(stmt.locus_constraint, child)
        elif stmt.locus_constraint is not None:
            self._check_bool_expr(stmt.locus_constraint, scope)

    def _check_constraint_stmt(self, stmt: ConstraintStmt, scope: _Scope) -> None:
        sym = scope.lookup(stmt.subject)
        if sym is None:
            self._err(f"Undefined name '{stmt.subject}' in constraint statement")
        elif sym.kind != Kind.SHAPE:
            self._err(
                f"Constraint target '{stmt.subject}' is a {sym.kind.name}, "
                f"expected a SHAPE"
            )
        self._check_constraint_clause(stmt.constraint, scope)

    def _check_constraint_clause(self, clause, scope: _Scope) -> None:
        if isinstance(clause, PosConstraint):
            for target in clause.targets:
                self._check_expr(target, scope)
        elif isinstance(clause, RelConstraint):
            self._require_declared(clause.target, scope)

    def _check_measure(self, stmt, scope: _Scope) -> None:
        if isinstance(stmt, DistanceMeasure):
            self._require_declared(stmt.point_a, scope)
            self._require_declared(stmt.point_b, scope)
            self._check_expr(stmt.value, scope, numeric_required=True)
        elif isinstance(stmt, AngleMeasure):
            self._require_declared(stmt.angle_name, scope)
            # value is an AngleLiteral — always valid
        elif isinstance(stmt, LengthMeasure):
            self._require_declared(stmt.shape_name, scope)
            self._check_expr(stmt.value, scope, numeric_required=True)
        elif isinstance(stmt, RadiusMeasure):
            self._require_declared(stmt.shape_name, scope)
            self._check_expr(stmt.value, scope, numeric_required=True)
        elif isinstance(stmt, RatioMeasure):
            self._require_declared(stmt.shape_a, scope)
            self._require_declared(stmt.shape_b, scope)
            # value is a RatioLiteral — always valid
        elif isinstance(stmt, AreaMeasure):
            self._require_declared(stmt.shape_name, scope)
            self._check_expr(stmt.value, scope, numeric_required=True)
        elif isinstance(stmt, PerimeterMeasure):
            self._require_declared(stmt.shape_name, scope)
            self._check_expr(stmt.value, scope, numeric_required=True)

    def _check_let(self, stmt: LetStmt, scope: _Scope) -> None:
        if scope.lookup_local(stmt.name) is not None:
            self._err(f"Redeclaration of '{stmt.name}': already declared in this scope")
        elif scope.exists_in_parent(stmt.name):
            self._warn(f"'{stmt.name}' shadows a name declared in an outer scope")
        self._check_expr(stmt.value, scope, numeric_required=True)
        scope.declare(stmt.name, Kind.LET)

    def _check_set(self, stmt: SetStmt, scope: _Scope) -> None:
        sym = scope.lookup(stmt.name)
        if sym is None:
            self._err(f"Undefined name '{stmt.name}' in 'set' statement")
        elif sym.kind not in (Kind.LET, Kind.PARAM):
            self._err(
                f"'set {stmt.name}': '{stmt.name}' is a {sym.kind.name}, "
                f"not a LET or PARAM variable"
            )
        self._check_expr(stmt.value, scope, numeric_required=True)

    def _check_param(self, stmt: ParamStmt, scope: _Scope) -> None:
        name = stmt.name
        if scope.lookup_local(name) is not None:
            self._err(f"Redeclaration of '{name}': already declared in this scope")
        elif scope.exists_in_parent(name):
            self._warn(f"'{name}' shadows a name declared in an outer scope")

        rs = stmt.range_spec
        self._check_expr(rs.start, scope, numeric_required=True)
        self._check_expr(rs.end, scope, numeric_required=True)
        self._check_expr(rs.step, scope, numeric_required=True)

        start_v = self._literal_value(rs.start)
        end_v = self._literal_value(rs.end)
        step_v = self._literal_value(rs.step)
        if step_v is not None and step_v == 0.0:
            self._err(f"param '{name}': step cannot be zero (infinite loop)")
        if start_v is not None and end_v is not None and step_v is not None:
            if step_v > 0 and start_v > end_v:
                self._warn(
                    f"param '{name}': start ({start_v}) > end ({end_v}) "
                    f"with positive step — range will produce no frames"
                )
            elif step_v < 0 and start_v < end_v:
                self._warn(
                    f"param '{name}': start ({start_v}) < end ({end_v}) "
                    f"with negative step — range will produce no frames"
                )

        scope.declare(name, Kind.PARAM, param_range=(start_v, end_v, step_v))

    def _check_sweep(self, stmt: SweepStmt, scope: _Scope) -> None:
        for pname in stmt.params:
            sym = scope.lookup(pname)
            if sym is None:
                self._err(f"Undefined name '{pname}' in 'sweep' statement")
            elif sym.kind != Kind.PARAM:
                self._err(
                    f"'sweep {pname}': '{pname}' is a {sym.kind.name}, "
                    f"not a PARAM — only 'param' variables can be swept"
                )
        if stmt.speed is not None:
            self._check_expr(stmt.speed, scope, numeric_required=True)

    def _check_if(self, stmt: IfStmt, scope: _Scope) -> None:
        self._check_bool_expr(stmt.condition, scope)
        # Each branch gets its own scope
        # checks the bunch of statements in If
        then_scope = scope.child()
        saved_return = self._seen_return
        self._seen_return = False
        for s in stmt.body:
            self._check_stmt(s, then_scope)
        self._seen_return = saved_return

        # checks bunch of statements in elif scopes
        for elif_clause in stmt.else_ifs:
            self._check_bool_expr(elif_clause.condition, scope)
            elif_scope = scope.child()
            sr = self._seen_return
            self._seen_return = False
            for s in elif_clause.body:
                self._check_stmt(s, elif_scope)
            self._seen_return = sr

        # checks bunch of statements in else block
        if stmt.else_body is not None:
            else_scope = scope.child()
            sr = self._seen_return
            self._seen_return = False
            for s in stmt.else_body:
                self._check_stmt(s, else_scope)
            self._seen_return = sr

    def _check_for(self, stmt: ForStmt, scope: _Scope) -> None:
        for v in stmt.values:
            self._check_expr(v, scope)

        loop_scope = scope.child()
        if scope.lookup(stmt.var) is not None:
            self._warn(f"Loop variable '{stmt.var}' shadows a name in an outer scope")
        loop_scope.declare(stmt.var, Kind.LOOP_VAR)
        sr = self._seen_return
        self._seen_return = False
        for s in stmt.body:
            self._check_stmt(s, loop_scope)
        self._seen_return = sr

    def _check_define(self, stmt: DefineStmt, scope: _Scope) -> None:
        name = stmt.name
        # Check 2: checks if there is redeclaration or not.
        if scope.lookup_local(name) is not None:
            self._err(f"Redeclaration of '{name}': function already declared")
        elif scope.exists_in_parent(name):
            self._warn(f"'{name}' shadows a name declared in an outer scope")
        scope.declare(name, Kind.FUNCTION, arity=len(stmt.params))

        # Build function body scope
        fn_scope = scope.child()
        for pname in stmt.params:
            if scope.lookup(pname) is not None:
                self._warn(
                    f"Function param '{pname}' of '{name}' shadows an outer name"
                )
            fn_scope.declare(pname, Kind.ARG)

        # Checks body of Function.
        outer_in_fn = self._in_function
        outer_fn_name = self._function_name
        outer_has_ret = self._function_has_return
        outer_seen_ret = self._seen_return

        self._in_function = True
        self._function_name = name
        self._function_has_return = False
        self._seen_return = False

        for s in stmt.body:
            self._check_stmt(s, fn_scope)

        # We warn if the function never has a return statement at all

        if not self._function_has_return:
            self._warn(
                f"Function '{name}' has no 'return' statement — "
                f"it will always return None"
            )

        self._in_function = outer_in_fn
        self._function_name = outer_fn_name
        self._function_has_return = outer_has_ret
        self._seen_return = outer_seen_ret

    def _check_call(self, stmt: CallStmt, scope: _Scope) -> None:
        sym = scope.lookup(stmt.name)
        # checks undeclared names.
        if sym is None:
            self._err(f"Undefined function '{stmt.name}'")
            return
        # checks if it is a function or not.
        if sym.kind != Kind.FUNCTION:
            self._err(f"'{stmt.name}' is a {sym.kind.name}, not a FUNCTION")
            return
        # checks for invalid No. of arguments.
        if sym.arity is not None and len(stmt.args) != sym.arity:
            self._err(
                f"'{stmt.name}' expects {sym.arity} argument(s), got {len(stmt.args)}"
            )
        for i, arg in enumerate(stmt.args):
            self._check_expr(arg, scope)  # checks arg is numeric or not.
            # checks for shape identifiers being passed or not.
            if isinstance(arg, IdentExpr):
                arg_sym = scope.lookup(arg.name)
                if arg_sym is not None and arg_sym.kind == Kind.SHAPE:
                    self._warn(
                        f"Argument {i + 1} to '{stmt.name}' is a SHAPE "
                        f"('{arg.name}') — functions expect numeric values"
                    )

    def _check_return(self, stmt: ReturnStmt, scope: _Scope) -> None:
        if not self._in_function:
            self._err("'return' statement outside a 'define' function body")
            return
        self._function_has_return = True
        self._seen_return = True
        if stmt.value is not None:
            self._check_expr(stmt.value, scope)

    def _check_reflect(self, stmt: ReflectStmt, scope: _Scope) -> None:
        self._require_shape(stmt.target, scope, "reflect")
        self._require_shape(stmt.over, scope, "reflect … over")

    def _check_rotate(self, stmt: RotateStmt, scope: _Scope) -> None:
        self._require_shape(stmt.target, scope, "rotate")
        self._require_shape(stmt.about, scope, "rotate … about")

    def _check_scale(self, stmt: ScaleStmt, scope: _Scope) -> None:
        self._require_shape(stmt.target, scope, "scale")
        self._check_expr(stmt.by, scope, numeric_required=True)

    def _check_translate(self, stmt: TranslateStmt, scope: _Scope) -> None:
        self._require_shape(stmt.target, scope, "translate")
        self._check_expr(stmt.by.x, scope, numeric_required=True)
        self._check_expr(stmt.by.y, scope, numeric_required=True)

    def _check_label(self, stmt: LabelStmt, scope: _Scope) -> None:
        if scope.lookup(stmt.target) is None:
            self._err(f"'label {stmt.target}': name '{stmt.target}' is not declared")

    def _check_hide(self, stmt: HideStmt, scope: _Scope) -> None:
        for target in stmt.targets:
            if scope.lookup(target) is None:
                self._err(f"'hide {target}': name '{target}' is not declared")

    def _check_expr( self, expr, scope: _Scope, numeric_required: bool = False) -> None:

        if isinstance(expr, NumberLiteral):
            return  # always numeric, so always fine

        if isinstance(expr, AngleLiteral):
            return  # always numeric too (degrees)

        if isinstance(expr, StringLiteral):
            if numeric_required:
                self._err("String literal cannot be used in a numeric context")
            return

        if isinstance(expr, RatioLiteral):
            if numeric_required:
                self._err(
                    "Ratio literal cannot be used in a numeric/arithmetic context"
                )
            return

        if isinstance(expr, IdentExpr):
            sym = scope.lookup(expr.name)
            # Check 1: checks undeclared names
            if sym is None:
                self._err(f"Undefined name '{expr.name}'")
                return
            # Check 8: checks if any shape used in arithmetic
            if numeric_required and sym.kind == Kind.SHAPE:
                self._err(
                    f"'{expr.name}' is a SHAPE and cannot be used "
                    f"in a numeric/arithmetic expression"
                )
            # Check 8: checks if any function name used as value
            if numeric_required and sym.kind == Kind.FUNCTION:
                self._err(
                    f"'{expr.name}' is a FUNCTION; use 'call {expr.name}(…)' "
                    f"to invoke it"
                )
            return

        if isinstance(expr, VectorExpr):
            self._check_expr(expr.x, scope, numeric_required=True)
            self._check_expr(expr.y, scope, numeric_required=True)
            return

        if isinstance(expr, BinOp):
            self._check_expr(expr.left, scope, numeric_required=True)
            self._check_expr(expr.right, scope, numeric_required=True)
            return

        if isinstance(expr, UnaryOp):
            self._check_expr(expr.operand, scope, numeric_required=True)
            return

        # checks if expr is an CallStmt (e.g. inside ReturnStmt)
        if isinstance(expr, CallStmt):
            self._check_call(expr, scope)
            return


    def _check_bool_expr(self, expr, scope: _Scope) -> None:
        if isinstance(expr, CmpExpr):
            self._check_expr(expr.left, scope, numeric_required=True)
            self._check_expr(expr.right, scope, numeric_required=True)
        elif isinstance(expr, GeometricPred):
            self._require_declared(expr.subject, scope)
            self._require_declared(expr.target, scope)


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
