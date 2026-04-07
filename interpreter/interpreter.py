# importing required modules
import math
from typing import Any, Dict, List, Optional, Tuple

# simple point class to store x and y
class GeoPoint:
    __slots__ = ("name", "x", "y")

    def __init__(self, name: str, x: float, y: float):
        self.name = name
        self.x = x
        self.y = y


# class to store any geometric shape
class GeoShape:
    __slots__ = ("kind", "name", "props", "constraints", "points")

    def __init__(self, kind, name, props=None, constraints=None, points=None):
        self.kind = kind
        self.name = name
        self.props = props or {}
        self.constraints = constraints or []
        self.points = points or []


# class for user defined functions
class UserFunction:
    __slots__ = ("name", "params", "body", "closure")

    def __init__(self, name, params, body, closure):
        self.name = name
        self.params = params
        self.body = body
        self.closure = closure
# main interpreter class
class Interpreter:

    # constructor
    def __init__(self):
        self.env = {}
        self.shapes = []

    #Here we run all the statements
    def run(self, program):
        for stmt in program.statements:
            self._exec(stmt)

    #Here we  decide which function to call
    def _exec(self, stmt):
        print("Executing:", type(stmt).__name__)
