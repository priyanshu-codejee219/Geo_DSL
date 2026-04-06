from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

# Make the project root importable when running the file directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


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