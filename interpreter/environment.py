from __future__ import annotations
from typing import Any, Dict, Optional, Tuple

from .errors import GeoNameError, GeoImmutableError


class Environment:
    def __init__(self, parent: Optional["Environment"] = None) -> None:
        self._bindings: Dict[str, Any] = {}
        self._mutable:  set[str]  = set()   # names bound with `let` or `param`
        self.parent: Optional["Environment"] = parent


    def get(self, name: str) -> Any:
        if name in self._bindings:
            return self._bindings[name]
        if self.parent is not None:
            return self.parent.get(name)
        raise GeoNameError(name)

    def is_defined(self, name: str) -> bool:
        if name in self._bindings:
            return True
        if self.parent is not None:
            return self.parent.is_defined(name)
        return False

    def define(self, name: str, value: Any, *, mutable: bool = False) -> None:
        self._bindings[name] = value
        if mutable:
            self._mutable.add(name)

    def set(self, name: str, value: Any) -> None:
        scope = self._owner_scope(name)
        if scope is None:
            raise GeoNameError(name)
        if name not in scope._mutable:
            raise GeoImmutableError(name)
        scope._bindings[name] = value

    def _owner_scope(self, name: str) -> Optional["Environment"]:
        if name in self._bindings:
            return self
        if self.parent is not None:
            return self.parent._owner_scope(name)
        return None


    def define_param(self, name: str, start: float, end: float, step: float) -> None:
        if not self.is_defined(name):
            self.define(name, start, mutable=True)
        else:
            if name not in self._mutable:
                self._mutable.add(name)
        self._bindings[f"__param_{name}_start"] = start
        self._bindings[f"__param_{name}_end"]   = end
        self._bindings[f"__param_{name}_step"]  = step

    def get_param_range(self, name: str) -> Tuple[float, float, float]:
        try:
            start = self.get(f"__param_{name}_start")
            end   = self.get(f"__param_{name}_end")
            step  = self.get(f"__param_{name}_step")
        except GeoNameError:
            raise GeoNameError(name) from None
        return start, end, step

    def snapshot(self) -> "Environment":
        flat = Environment()
        self._copy_into(flat)
        return flat

    def _copy_into(self, target: "Environment") -> None:
        if self.parent is not None:
            self.parent._copy_into(target)
        for name, value in self._bindings.items():
            target._bindings[name] = value
            if name in self._mutable:
                target._mutable.add(name)

    def child(self) -> "Environment":
        return Environment(parent=self)

    def all_bindings(self) -> Dict[str, Any]:
        merged: Dict[str, Any] = {}
        if self.parent is not None:
            merged.update(self.parent.all_bindings())
        merged.update(
            {k: v for k, v in self._bindings.items()
             if not k.startswith("__param_")}
        )
        return merged

    def __repr__(self) -> str:  # pragma: no cover
        keys = list(self._bindings.keys())
        return f"Environment(bindings={keys}, has_parent={self.parent is not None})"
