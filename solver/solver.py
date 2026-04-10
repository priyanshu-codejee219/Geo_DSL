from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Optional

import numpy as np

if TYPE_CHECKING:
    from ast_nodes.nodes import DerivedDecl, GeometricPred
    from interpreter.environment import Environment

from interpreter.errors import GeoNameError
from interpreter.interpreter import GeoShape

from .algebraic import (
    _get_line_props,
    reflect_point_over_line,
    resolve_angle_bisector,
    resolve_arc,
    resolve_circle,
    resolve_circumcircle,
    resolve_convex_hull,
    resolve_ellipse,
    resolve_incircle,
    resolve_intersection,
    resolve_line,
    resolve_midpoint,
    resolve_parallelogram,
    resolve_perpendicular_bisector,
    resolve_point,
    resolve_polygon,
    resolve_ray,
    resolve_rectangle,
    resolve_regular_poly,
    resolve_rhombus,
    resolve_segment,
    resolve_triangle,
    rotate_point_around,
    scale_point_from,
)
from .numeric import resolve_numeric

_ALGEBRAIC: dict[str, Any] = {
    "point": resolve_point,
    "segment": resolve_segment,
    "line": resolve_line,
    "ray": resolve_ray,
    "circle": resolve_circle,
    "arc": resolve_arc,
    "triangle": resolve_triangle,
    "rectangle": resolve_rectangle,
    "rhombus": resolve_rhombus,
    "regular_poly": resolve_regular_poly,
    "polygon": resolve_polygon,
    "ellipse": resolve_ellipse,
    "parallelogram": resolve_parallelogram,
}


class GeoSolver:
    # Full geometry backend — algebraic first, numeric fallback.

    def __init__(self):
        self.program = None
        self.evaluator = None

    def resolve_primitive(
        self,
        shape: GeoShape,
        env: "Environment",
    ) -> Optional[GeoShape]:
        alg_fn = _ALGEBRAIC.get(shape.kind)
        if alg_fn is not None:
            result = alg_fn(shape, env)
            if result is not None:
                return result

        # Numeric fallback
        result = resolve_numeric(shape, env)
        if result is not None:
            return result

        return shape

    def resolve_derived(
        self,
        stmt: "DerivedDecl",
        env: "Environment",
    ) -> Optional[GeoShape]:
        kind = stmt.kind
        name = stmt.name or f"_derived_{id(stmt)}"
        args = stmt.args

        result = GeoShape(kind="point", name=name)

        if kind == "midpoint":
            return resolve_midpoint(result, args, env)

        if kind == "intersection":
            return resolve_intersection(result, args, env)

        if kind == "perpendicular_bisector":
            return resolve_perpendicular_bisector(result, args, env)

        if kind == "angle_bisector":
            return resolve_angle_bisector(result, args, env)

        if kind == "circumcircle":
            return resolve_circumcircle(result, args, env)

        if kind == "incircle":
            return resolve_incircle(result, args, env)

        if kind == "convex_hull":
            return resolve_convex_hull(result, args, env)

        if kind == "locus":
            if self.evaluator and self.program:
                try:
                    locus_range = float(env.get("__locus_range"))
                except Exception:
                    locus_range = 200.0
                try:
                    locus_step = float(env.get("__locus_step"))
                except Exception:
                    locus_step = 1.0

                result = self.evaluator.run_locus(
                    program=self.program,
                    locus_var=stmt.locus_var,
                    constraint=stmt.locus_constraint,
                    x_range=(-locus_range, locus_range, locus_step),
                    y_range=(-locus_range, locus_range, locus_step),
                    shape_name=name,
                )
                return GeoShape(
                    "locus",
                    name,
                    props={"points": result.points},
                )
            else:
                return GeoShape(
                    "locus",
                    name,
                    props={
                        "locus_var": stmt.locus_var,
                        "locus_constraint": stmt.locus_constraint,
                    },
                )

        return None

    def apply_constraint(
        self,
        shape: GeoShape,
        clause: dict[str, Any],
        env: "Environment",
    ) -> None:

        shape.constraints.append(clause)
        resolved = self.resolve_primitive(shape, env)
        if resolved is not None:
            shape.props.update(resolved.props)

    # def apply_constraint(
    #     self,
    #     shape: GeoShape,
    #     clause: dict,
    #     env: "Environment",
    # ) -> None:
    #     shape.constraints.append(clause)
    #     resolved = self.resolve_primitive(shape, env)
    #     if resolved is not None:
    #         shape.props.update(resolved.props)

    def add_distance_constraint(
        self,
        point_a: str,
        point_b: str,
        value: float,
        env: "Environment",
    ) -> None:
        try:
            shape_b = env.get(point_b)
        except GeoNameError:
            return
        if not isinstance(shape_b, GeoShape):
            return
        try:
            pa = env.get(point_a)
            ref_pt = (
                (
                    float(pa.props.get("x", 0.0)),
                    float(pa.props.get("y", 0.0)),
                )
                if hasattr(pa, "props")
                else (0.0, 0.0)
            )
        except GeoNameError:
            ref_pt = (0.0, 0.0)
        shape_b.constraints.append(
            {
                "kind": "distance",
                "ref_point": ref_pt,
                "value": float(value),
            }
        )

    def add_angle_constraint(
        self,
        angle_name: str,
        value_deg: float,
        env: "Environment",
    ) -> None:
        env.define(f"__angle_{angle_name}", float(value_deg))

    def check_predicate(
        self,
        pred: "GeometricPred",
        env: "Environment",
    ) -> bool:
        try:
            subj = env.get(pred.subject)
            tgt = env.get(pred.target)
        except GeoNameError:
            return False

        rel = pred.relation
        if rel == "on":
            return self._check_on(subj, tgt)
        if rel == "parallel_to":
            return self._check_parallel(subj, tgt)
        if rel == "perpendicular_to":
            return self._check_perpendicular(subj, tgt)
        if rel == "bisects":
            return self._check_bisects(subj, tgt, env)
        if rel == "tangent_to":
            return self._check_tangent(subj, tgt, rel)
        if rel == "passes_through":
            return self._check_passes_through(subj, tgt)
        if rel == "centered_at":
            return self._check_centered_at(subj, tgt)
        return False

    def reflect(
        self,
        shape: GeoShape,
        axis: GeoShape,
        env: "Environment",
    ) -> Optional[GeoShape]:
        abc = _get_line_props(axis)
        if abc is None:
            return None
        a, b, c = abc
        result = GeoShape(shape.kind, shape.name + "'", props=dict(shape.props))
        self._transform_vertices(result, lambda p: reflect_point_over_line(p, a, b, c))
        return result

    def rotate(
        self,
        shape: GeoShape,
        angle_deg: float,
        pivot: GeoShape,
        env: "Environment",
    ) -> Optional[GeoShape]:
        center = np.array(
            [
                float(pivot.props.get("x", 0.0)),
                float(pivot.props.get("y", 0.0)),
            ]
        )
        result = GeoShape(shape.kind, shape.name + "'", props=dict(shape.props))
        self._transform_vertices(
            result, lambda p: rotate_point_around(p, center, angle_deg)
        )
        return result

    def scale(
        self,
        shape: GeoShape,
        factor: float,
        env: "Environment",
    ) -> Optional[GeoShape]:
        center = np.zeros(2)
        result = GeoShape(shape.kind, shape.name + "'", props=dict(shape.props))
        self._transform_vertices(result, lambda p: scale_point_from(p, center, factor))
        for key in ("radius", "rx", "ry"):
            if key in result.props:
                result.props[key] = float(result.props[key]) * abs(factor)
        return result

    def translate(
        self,
        shape: GeoShape,
        dx: float,
        dy: float,
        env: "Environment",
    ) -> Optional[GeoShape]:
        delta = np.array([dx, dy])
        result = GeoShape(shape.kind, shape.name + "'", props=dict(shape.props))
        self._transform_vertices(result, lambda p: p + delta)
        for xk, yk in [("cx", "cy")]:
            if xk in result.props:
                result.props[xk] = float(result.props[xk]) + dx
                result.props[yk] = float(result.props[yk]) + dy
        return result

    @staticmethod
    def _transform_vertices(
        shape: GeoShape,
        f: Any,
    ) -> None:

        p = shape.props

        # Single-point shapes
        if "x" in p and "y" in p:
            new = f(np.array([float(p["x"]), float(p["y"])]))
            p["x"], p["y"] = new[0], new[1]

        # Circles
        if "cx" in p and "cy" in p:
            new = f(np.array([float(p["cx"]), float(p["cy"])]))
            p["cx"], p["cy"] = new[0], new[1]

        # Multi-vertex shapes (up to 16 vertices)
        for i in range(1, 17):
            xk, yk = f"x{i}", f"y{i}"
            if xk in p:
                new = f(np.array([float(p[xk]), float(p[yk])]))
                p[xk], p[yk] = new[0], new[1]
            else:
                break

        # Segment endpoints
        for xk, yk in [("x1", "y1"), ("x2", "y2")]:
            if xk in p and f"x{xk[1]}" not in p:
                new = f(np.array([float(p[xk]), float(p[yk])]))
                p[xk], p[yk] = new[0], new[1]

    @staticmethod
    def _check_on(subj: Any, tgt: Any) -> bool:
        if not (hasattr(subj, "props") and hasattr(tgt, "props")):
            return False
        if subj.kind == "point":
            px = float(subj.props.get("x", 0.0))
            py = float(subj.props.get("y", 0.0))
            if tgt.kind == "circle":
                cx = float(tgt.props.get("cx", 0.0))
                cy = float(tgt.props.get("cy", 0.0))
                r = float(tgt.props.get("radius", 0.0))
                return abs(math.hypot(px - cx, py - cy) - r) < 1e-6
            if tgt.kind == "line":
                abc = _get_line_props(tgt)
                if abc:
                    a, b, c = abc
                    return abs(a * px + b * py + c) < 1e-6
            if tgt.kind in ("segment", "triangle", "polygon"):
                return GeoSolver._point_on_edges(px, py, tgt)
        return False

    @staticmethod
    def _check_parallel(subj: Any, tgt: Any) -> bool:
        if not (hasattr(subj, "props") and hasattr(tgt, "props")):
            return False
        abc1 = _get_line_props(subj)
        abc2 = _get_line_props(tgt)
        if abc1 and abc2:
            a1, b1, _ = abc1
            a2, b2, _ = abc2
            return abs(a1 * b2 - a2 * b1) < 1e-6
        return False

    @staticmethod
    def _check_perpendicular(subj: Any, tgt: Any) -> bool:
        if not (hasattr(subj, "props") and hasattr(tgt, "props")):
            return False
        abc1 = _get_line_props(subj)
        abc2 = _get_line_props(tgt)
        if abc1 and abc2:
            a1, b1, _ = abc1
            a2, b2, _ = abc2
            return abs(a1 * a2 + b1 * b2) < 1e-6
        return False

    @staticmethod
    def _check_tangent(subj: Any, tgt: Any, rel: str) -> bool:
        if not (hasattr(subj, "props") and hasattr(tgt, "props")):
            return False
        if subj.kind == "circle" and tgt.kind == "circle":
            d = math.hypot(
                float(subj.props.get("cx", 0)) - float(tgt.props.get("cx", 0)),
                float(subj.props.get("cy", 0)) - float(tgt.props.get("cy", 0)),
            )
            r1 = float(subj.props.get("radius", 0))
            r2 = float(tgt.props.get("radius", 0))
            return abs(d - (r1 + r2)) < 1e-6 or abs(d - abs(r1 - r2)) < 1e-6
        if subj.kind == "circle" and tgt.kind == "line":
            abc = _get_line_props(tgt)
            if not abc:
                return False
            a, b, c = abc
            cx = float(subj.props.get("cx", 0))
            cy = float(subj.props.get("cy", 0))
            r = float(subj.props.get("radius", 0))
            return abs(abs(a * cx + b * cy + c) - r) < 1e-6
        return False

    @staticmethod
    def _check_bisects(subj: Any, tgt: Any, env: "Environment") -> bool:
        if not (hasattr(subj, "props") and hasattr(tgt, "props")):
            return False
        if tgt.kind != "segment":
            return False

        x1 = tgt.props.get("x1")
        y1 = tgt.props.get("y1")
        x2 = tgt.props.get("x2")
        y2 = tgt.props.get("y2")
        if any(v is None for v in (x1, y1, x2, y2)):
            return False
        mid = np.array([(float(x1) + float(x2)) / 2, (float(y1) + float(y2)) / 2])

        if subj.kind == "line":
            abc = _get_line_props(subj)
            if abc:
                a, b, c = abc
                return bool(abs(a * mid[0] + b * mid[1] + c) < 1e-6)
            return False

        if subj.kind == "ray":
            ox = subj.props.get("ox")
            oy = subj.props.get("oy")
            dx = subj.props.get("dx")
            dy = subj.props.get("dy")
            if any(v is None for v in (ox, oy, dx, dy)):
                return False
            origin = np.array([float(ox), float(oy)])
            direction = np.array([float(dx), float(dy)])
            if np.linalg.norm(direction) < 1e-12:
                return False
            vector = mid - origin
            cross = direction[0] * vector[1] - direction[1] * vector[0]
            dot = direction[0] * vector[0] + direction[1] * vector[1]
            return bool(abs(cross) < 1e-6 and dot >= -1e-6)

        return False

    @staticmethod
    def _check_passes_through(subj: Any, tgt: Any) -> bool:
        if not (hasattr(subj, "props") and hasattr(tgt, "props")):
            return False
        if tgt.kind != "point":
            return False
        px = float(tgt.props.get("x", 0))
        py = float(tgt.props.get("y", 0))
        if subj.kind == "line":
            abc = _get_line_props(subj)
            if abc:
                a, b, c = abc
                return abs(a * px + b * py + c) < 1e-6
        if subj.kind == "circle":
            cx = float(subj.props.get("cx", 0))
            cy = float(subj.props.get("cy", 0))
            r = float(subj.props.get("radius", 0))
            return abs(math.hypot(px - cx, py - cy) - r) < 1e-6
        return False

    @staticmethod
    def _check_centered_at(subj: Any, tgt: Any) -> bool:
        if not (hasattr(subj, "props") and hasattr(tgt, "props")):
            return False
        if tgt.kind != "point":
            return False
        tx = float(tgt.props.get("x", 0))
        ty = float(tgt.props.get("y", 0))
        cx = float(subj.props.get("cx", subj.props.get("x", 0)))
        cy = float(subj.props.get("cy", subj.props.get("y", 0)))
        return math.hypot(cx - tx, cy - ty) < 1e-6

    @staticmethod
    def _point_on_edges(px: float, py: float, shape: GeoShape) -> bool:
        p = np.array([px, py])

        vertices: list[np.ndarray] = []

        if shape.kind == "segment":
            x1 = shape.props.get("x1")
            y1 = shape.props.get("y1")
            x2 = shape.props.get("x2")
            y2 = shape.props.get("y2")
            if any(v is None for v in (x1, y1, x2, y2)):
                return False
            vertices = [
                np.array([float(x1), float(y1)]),
                np.array([float(x2), float(y2)]),
            ]
        else:
            i = 1
            while f"x{i}" in shape.props:
                xi = shape.props[f"x{i}"]
                yi = shape.props[f"y{i}"]
                vertices.append(np.array([float(xi), float(yi)]))
                i += 1

        if len(vertices) < 2:
            return False

        n = len(vertices)
        close = shape.kind != "segment"

        edges = [
            (vertices[i], vertices[(i + 1) % n]) for i in range(n if close else n - 1)
        ]

        TOL = 1e-6
        for a_pt, b_pt in edges:
            ab = b_pt - a_pt
            ap = p - a_pt
            cross = float(ab[0] * ap[1] - ab[1] * ap[0])
            if abs(cross) > TOL * (np.linalg.norm(ab) + 1e-12):
                continue
            dot = float(np.dot(ab, ap))
            ab_sq = float(np.dot(ab, ab))
            if -TOL <= dot <= ab_sq + TOL:
                return True

        return False
