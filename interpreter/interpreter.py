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
    # handle different statements
    def _exec(self, stmt):
        # variable declaration
        if stmt.type == "let":
            self.env[stmt.name] = self._eval(stmt.value)
        # shape creation
        elif stmt.type == "shape":
            shape = GeoShape(stmt.kind, stmt.name)
            self.shapes.append((stmt.name, shape))
            self.env[stmt.name] = shape
        else:
            print("Unknown statement")
            
    # evaluate expressions
    def _eval(self, expr):
        # number value
        if expr.type == "number":
            return expr.value
        # variable access
        if expr.type == "identifier":
            return self.env.get(expr.name)
        # binary operation
        if expr.type == "binop":
            left = self._eval(expr.left)
            right = self._eval(expr.right)
            if expr.op == "+":
                return left + right
            if expr.op == "-":
                return left - right
        return None
