from __future__ import annotations

import math
from typing import TYPE_CHECKING, Callable, Optional

import numpy as np

if TYPE_CHECKING:
    from interpreter.environment import Environment
    from interpreter.interpreter import GeoShape

from interpreter.errors import GeoConstraintError

MAX_ITER = 300
TOLERANCE = 1e-8
H = 1e-6
DAMPING = 0.6  # Newton step damping factor


def _jacobian(F: Callable, x: np.ndarray) -> np.ndarray:
    n = len(x)
    f0 = np.asarray(F(x), dtype=float)
    m = len(f0)
    J = np.zeros((m, n))
    for j in range(n):
        xp, xm = x.copy(), x.copy()
        xp[j] += H
        xm[j] -= H
        J[:, j] = (np.asarray(F(xp), dtype=float) - np.asarray(F(xm), dtype=float)) / (
            2 * H
        )
    return J


def _newton_raphson(
    F: Callable,
    x0: np.ndarray,
) -> tuple[np.ndarray, float]:
    x = x0.copy().astype(float)
    for _ in range(MAX_ITER):
        f = np.asarray(F(x), dtype=float)
        res = np.linalg.norm(f)
        if res < TOLERANCE:
            return x, float(res)
        J = _jacobian(F, x)
        dx, *_ = np.linalg.lstsq(J, -f, rcond=None)
        x = x + DAMPING * dx
    f = np.asarray(F(x), dtype=float)
    return x, float(np.linalg.norm(f))


def _get_ref_point(name: str, env: "Environment") -> Optional[np.ndarray]:
    try:
        val = env.get(name)
    except Exception:
        return None
    if hasattr(val, "props"):
        x = val.props.get("x")
        y = val.props.get("y")
        if x is not None and y is not None:
            return np.array([float(x), float(y)])
    if isinstance(val, (tuple, list)) and len(val) == 2:
        return np.array([float(val[0]), float(val[1])])
    return None


def _get_ref_circle(name: str, env: "Environment") -> Optional[tuple]:
    try:
        val = env.get(name)
    except Exception:
        return None
    if hasattr(val, "props") and val.kind == "circle":
        cx = val.props.get("cx")
        cy = val.props.get("cy")
        r = val.props.get("radius")
        if cx is not None and cy is not None and r is not None:
            return float(cx), float(cy), float(r)
    return None


def _get_ref_line(name: str, env: "Environment") -> Optional[tuple]:
    try:
        val = env.get(name)
    except Exception:
        return None
    if hasattr(val, "props") and val.kind in ("line", "segment"):
        a = val.props.get("a")
        b = val.props.get("b")
        c = val.props.get("c")
        if a is not None and b is not None and c is not None:
            return float(a), float(b), float(c)
    return None


def _resolve_ref(t, env: "Environment") -> Optional[np.ndarray]:
    if isinstance(t, str):
        return _get_ref_point(t, env)
    if hasattr(t, "props"):
        x = t.props.get("x")
        y = t.props.get("y")
        if x is not None and y is not None:
            return np.array([float(x), float(y)])
    if isinstance(t, (tuple, list)) and len(t) == 2:
        return np.array([float(t[0]), float(t[1])])
    return None


def _resolve_ref_shape(t, env: "Environment"):
    if isinstance(t, str):
        try:
            return env.get(t)
        except Exception:
            return None
    if hasattr(t, "props"):
        return t
    return None


def _point_residuals(x: np.ndarray, constraints: list, env: "Environment") -> list:
    px, py = x[0], x[1]
    R: list[float] = []

    for c in constraints:
        kind = c.get("kind")

        if kind == "at":
            t = (c.get("targets") or [None])[0]
            p = _resolve_ref(t, env)
            if p is not None:
                R += [px - p[0], py - p[1]]

        elif kind == "on":
            raw = (c.get("targets") or [None])[0]
            ref = _resolve_ref_shape(raw, env)
            if ref is not None and hasattr(ref, "props"):
                if ref.kind == "circle":
                    rcx = float(ref.props.get("cx", 0))
                    rcy = float(ref.props.get("cy", 0))
                    rr = float(ref.props.get("radius", 1))
                    R.append((px - rcx) ** 2 + (py - rcy) ** 2 - rr**2)
                elif ref.kind == "line":
                    a = float(ref.props.get("a", 0))
                    b = float(ref.props.get("b", 1))
                    cv = float(ref.props.get("c", 0))
                    R.append(a * px + b * py + cv)

        elif kind == "distance":
            rp = c.get("ref_point")
            d = c.get("value")
            if rp is not None and d is not None:
                R.append(math.hypot(px - float(rp[0]), py - float(rp[1])) - float(d))

        elif kind == "centered_at":
            t = (c.get("targets") or [None])[0]
            p = _resolve_ref(t, env)
            if p is not None:
                R += [px - p[0], py - p[1]]

    return R if R else [px, py]


def _circle_residuals(x: np.ndarray, constraints: list, env: "Environment") -> list:
    cx, cy, r = x[0], x[1], x[2]
    R: list[float] = []

    for c in constraints:
        kind = c.get("kind")

        if kind in ("at", "centered_at"):
            t = (c.get("targets") or [None])[0]
            p = _resolve_ref(t, env)
            if p is not None:
                R += [cx - p[0], cy - p[1]]

        elif kind == "radius":
            R.append(r - float(c.get("value", r)))

        elif kind == "passes_through":
            for t in c.get("targets", []):
                p = _resolve_ref(t, env)
                if p is not None:
                    R.append((cx - p[0]) ** 2 + (cy - p[1]) ** 2 - r**2)

        elif kind in ("tangent_to", "tangent_external", "tangent_internal"):
            raw = c.get("target") or (c.get("targets") or [None])[0]
            ref = _resolve_ref_shape(raw, env)
            if ref is not None and hasattr(ref, "props"):
                if ref.kind == "circle":
                    cx2 = float(ref.props.get("cx", 0))
                    cy2 = float(ref.props.get("cy", 0))
                    r2 = float(ref.props.get("radius", 1))
                    d = math.hypot(cx - cx2, cy - cy2)
                    if kind == "tangent_external":
                        R.append(d - (r + r2))
                    elif kind == "tangent_internal":
                        R.append(d - abs(r - r2))
                    else:
                        R.append(min(abs(d - (r + r2)), abs(d - abs(r - r2))))
                elif ref.kind == "line":
                    a = float(ref.props.get("a", 0))
                    b = float(ref.props.get("b", 1))
                    cv = float(ref.props.get("c", 0))
                    R.append(abs(a * cx + b * cy + cv) - abs(r))

    for c in constraints:
        fixed_r = c.get("radius")
        if fixed_r is not None:
            R.append(r - float(fixed_r))
            break

    return R if R else [cx, cy, r - 50.0]


def _segment_residuals(x: np.ndarray, constraints: list, env: "Environment") -> list:
    x1, y1, x2, y2 = x[0], x[1], x[2], x[3]
    R: list[float] = []

    for c in constraints:
        kind = c.get("kind")

        if kind == "passes_through":
            for t in c.get("targets", []):
                p = _resolve_ref(t, env)
                if p is not None:
                    dx, dy = x2 - x1, y2 - y1
                    R.append(dx * (p[1] - y1) - dy * (p[0] - x1))

        elif kind == "length":
            target_len = float(c.get("value", 0))
            R.append(math.hypot(x2 - x1, y2 - y1) - target_len)

        elif kind == "parallel_to":
            raw = c.get("target")
            ref = _resolve_ref_shape(raw, env)
            if ref is not None and hasattr(ref, "props"):
                a = float(ref.props.get("a", 0))
                b = float(ref.props.get("b", 1))
                dx, dy = x2 - x1, y2 - y1
                R.append(a * dx + b * dy)

        elif kind == "perpendicular_to":
            raw = c.get("target")
            ref = _resolve_ref_shape(raw, env)
            if ref is not None and hasattr(ref, "props"):
                a = float(ref.props.get("a", 0))
                b = float(ref.props.get("b", 1))
                dx, dy = x2 - x1, y2 - y1
                R.append(b * dx - a * dy)

    for c in constraints:
        if c.get("kind") == "__length_prop":
            R.append(math.hypot(x2 - x1, y2 - y1) - float(c["value"]))

    return R if R else [x1, y1, x2 - 100.0, y2]


def _line_residuals(x: np.ndarray, constraints: list, env: "Environment") -> list:
    a, b, c_val = x[0], x[1], x[2]
    R: list[float] = []

    R.append(a**2 + b**2 - 1)

    for c in constraints:
        kind = c.get("kind")

        if kind == "passes_through":
            for t in c.get("targets", []):
                p = _resolve_ref(t, env)
                if p is not None:
                    R.append(a * p[0] + b * p[1] + c_val)

        elif kind in ("tangent_to", "tangent_external", "tangent_internal"):
            raw = c.get("target") or (c.get("targets") or [None])[0]
            ref = _resolve_ref_shape(raw, env)
            if ref is not None and hasattr(ref, "props"):
                if ref.kind == "circle":
                    cx = float(ref.props.get("cx", 0))
                    cy = float(ref.props.get("cy", 0))
                    r = float(ref.props.get("radius", 1))
                    dist = abs(a * cx + b * cy + c_val)
                    R.append(dist - r)

        elif kind == "parallel_to":
            raw = c.get("target")
            ref = _resolve_ref_shape(raw, env)
            if ref is not None and hasattr(ref, "props"):
                ra = float(ref.props.get("a", 0))
                rb = float(ref.props.get("b", 1))
                R.append(abs(a * ra + b * rb) - 1)

        elif kind == "perpendicular_to":
            raw = c.get("target")
            ref = _resolve_ref_shape(raw, env)
            if ref is not None and hasattr(ref, "props"):
                ra = float(ref.props.get("a", 0))
                rb = float(ref.props.get("b", 1))
                R.append(a * ra + b * rb)

    return R if R else [a, b - 1.0, c_val]


def _triangle_residuals(x: np.ndarray, constraints: list, env: "Environment") -> list:
    px1, py1, px2, py2, px3, py3 = x
    R: list[float] = []

    verts = [
        np.array([px1, py1]),
        np.array([px2, py2]),
        np.array([px3, py3]),
    ]

    for c in constraints:
        kind = c.get("kind")

        if kind == "passes_through":
            for i, t in enumerate(c.get("targets", [])[:3]):
                if isinstance(t, str):
                    ref = _get_ref_point(t, env)
                    if ref is not None:
                        R += [verts[i][0] - ref[0], verts[i][1] - ref[1]]

        elif kind == "equilateral":
            s1 = np.linalg.norm(verts[1] - verts[0])
            s2 = np.linalg.norm(verts[2] - verts[1])
            s3 = np.linalg.norm(verts[0] - verts[2])
            R += [float(s1 - s2), float(s2 - s3)]

        elif kind == "isoceles":
            s1 = np.linalg.norm(verts[1] - verts[0])
            s2 = np.linalg.norm(verts[2] - verts[0])
            R.append(float(s1 - s2))

        elif kind == "right_angle":
            u = verts[1] - verts[0]
            v = verts[2] - verts[0]
            R.append(float(np.dot(u, v)))

        elif kind == "perimeter":
            target = float(c.get("value", 0))
            p = (
                np.linalg.norm(verts[1] - verts[0])
                + np.linalg.norm(verts[2] - verts[1])
                + np.linalg.norm(verts[0] - verts[2])
            )
            R.append(float(p) - target)

        elif kind == "area":
            target = float(c.get("value", 0))
            d1 = verts[1] - verts[0]
            d2 = verts[2] - verts[0]
            area = abs(d1[0] * d2[1] - d1[1] * d2[0]) / 2
            R.append(area - target)

    if not R:
        R = [px1, py1, px2 - 100.0, py2, px3, py3 - 100.0]

    return R


def _rectangle_residuals(x: np.ndarray, constraints: list, env: "Environment") -> list:
    bx, by, w, h = x
    R: list[float] = []

    for c in constraints:
        kind = c.get("kind")
        if kind == "at":
            t = (c.get("targets") or [None])[0]
            if isinstance(t, (tuple, list)) and len(t) == 2:
                R += [bx - float(t[0]), by - float(t[1])]
        elif kind == "area":
            R.append(w * h - float(c.get("value", 0)))
        elif kind == "perimeter":
            R.append(2 * (w + h) - float(c.get("value", 0)))
        elif kind == "width":
            R.append(w - float(c.get("value", 0)))
        elif kind == "height":
            R.append(h - float(c.get("value", 0)))

    for c in constraints:
        if c.get("kind") == "__width_prop":
            R.append(w - float(c["value"]))
        if c.get("kind") == "__height_prop":
            R.append(h - float(c["value"]))

    R += [max(0.0, 1.0 - w), max(0.0, 1.0 - h)]
    return R if R else [bx, by, w - 100.0, h - 100.0]


def _ellipse_residuals(x: np.ndarray, constraints: list, env: "Environment") -> list:
    cx, cy, rx, ry = x
    R: list[float] = []

    for c in constraints:
        kind = c.get("kind")
        if kind in ("at", "centered_at"):
            t = (c.get("targets") or [None])[0]
            if isinstance(t, (tuple, list)) and len(t) == 2:
                R += [cx - float(t[0]), cy - float(t[1])]
            elif isinstance(t, str):
                ref = _get_ref_point(t, env)
                if ref is not None:
                    R += [cx - ref[0], cy - ref[1]]
        elif kind == "passes_through":
            for t in c.get("targets", []):
                if isinstance(t, str):
                    ref = _get_ref_point(t, env)
                    if ref is not None:
                        R.append(
                            ((ref[0] - cx) / rx) ** 2 + ((ref[1] - cy) / ry) ** 2 - 1.0
                        )
        elif kind == "area":
            R.append(math.pi * rx * ry - float(c.get("value", 0)))

    return R if R else [cx, cy, rx - 80.0, ry - 50.0]


def _guess(shape: "GeoShape", kind: str) -> np.ndarray:
    p = shape.props
    if kind == "point":
        return np.array([p.get("x", 0.0), p.get("y", 0.0)])
    if kind == "circle":
        return np.array([p.get("cx", 0.0), p.get("cy", 0.0), p.get("radius", 50.0)])
    if kind == "segment":
        return np.array(
            [p.get("x1", 0.0), p.get("y1", 0.0), p.get("x2", 100.0), p.get("y2", 0.0)]
        )
    if kind == "triangle":
        return np.array(
            [
                p.get("x1", 0.0),
                p.get("y1", 0.0),
                p.get("x2", 100.0),
                p.get("y2", 0.0),
                p.get("x3", 50.0),
                p.get("y3", 86.6),
            ]
        )
    if kind == "rectangle":
        return np.array(
            [
                p.get("x1", 0.0),
                p.get("y1", 0.0),
                p.get("width", 100.0),
                p.get("height", 60.0),
            ]
        )
    if kind == "ellipse":
        return np.array(
            [p.get("cx", 0.0), p.get("cy", 0.0), p.get("rx", 80.0), p.get("ry", 50.0)]
        )
    if kind == "rhombus":
        return np.array(
            [
                p.get("cx", 0.0),
                p.get("cy", 0.0),
                p.get("half_diag_x", 60.0),
                p.get("half_diag_y", 40.0),
            ]
        )
    if kind == "regular_poly":
        return np.array([p.get("cx", 0.0), p.get("cy", 0.0), p.get("radius", 80.0)])
    return np.zeros(2)


def _write_back(shape: "GeoShape", sol: np.ndarray) -> None:
    kind = shape.kind
    p = shape.props

    if kind == "point":
        p["x"], p["y"] = sol[0], sol[1]

    elif kind == "circle":
        p["cx"], p["cy"], p["radius"] = sol[0], sol[1], abs(sol[2])

    elif kind == "segment":
        p["x1"], p["y1"], p["x2"], p["y2"] = sol
        p["length"] = float(np.linalg.norm(sol[2:] - sol[:2]))

    elif kind == "triangle":
        p["x1"], p["y1"] = sol[0], sol[1]
        p["x2"], p["y2"] = sol[2], sol[3]
        p["x3"], p["y3"] = sol[4], sol[5]

    elif kind == "rectangle":
        bx, by, w, h = sol[0], sol[1], abs(sol[2]), abs(sol[3])
        p.update(
            {
                "x1": bx,
                "y1": by,
                "x2": bx + w,
                "y2": by,
                "x3": bx + w,
                "y3": by + h,
                "x4": bx,
                "y4": by + h,
                "width": w,
                "height": h,
            }
        )

    elif kind == "ellipse":
        p["cx"], p["cy"] = sol[0], sol[1]
        p["rx"], p["ry"] = abs(sol[2]), abs(sol[3])

    elif kind == "rhombus":
        cx, cy, d1, d2 = sol[0], sol[1], abs(sol[2]), abs(sol[3])
        p.update(
            {
                "cx": cx,
                "cy": cy,
                "x1": cx + d1,
                "y1": cy,
                "x2": cx,
                "y2": cy + d2,
                "x3": cx - d1,
                "y3": cy,
                "x4": cx,
                "y4": cy - d2,
            }
        )

    elif kind == "regular_poly":
        cx, cy, r = sol[0], sol[1], abs(sol[2])
        n = int(p.get("sides", 6))
        start_deg = float(p.get("start_deg", 90.0))
        p["cx"] = cx
        p["cy"] = cy
        p["radius"] = r
        for i in range(n):
            theta = math.radians(start_deg + 360 * i / n)
            p[f"x{i + 1}"] = cx + r * math.cos(theta)
            p[f"y{i + 1}"] = cy + r * math.sin(theta)


def _build_residuals(
    kind: str, constraints: list, env: "Environment"
) -> Optional[Callable]:
    if kind == "point":
        return lambda x: _point_residuals(x, constraints, env)
    if kind == "circle":
        return lambda x: _circle_residuals(x, constraints, env)
    if kind == "segment":
        return lambda x: _segment_residuals(x, constraints, env)
    if kind == "line":
        return lambda x: _line_residuals(x, constraints, env)
    if kind == "triangle":
        return lambda x: _triangle_residuals(x, constraints, env)
    if kind == "rectangle":
        return lambda x: _rectangle_residuals(x, constraints, env)
    if kind == "ellipse":
        return lambda x: _ellipse_residuals(x, constraints, env)
    if kind in ("rhombus", "regular_poly"):
        return lambda x: _circle_residuals(x[:3], constraints, env)
    return None


def resolve_numeric(
    shape: "GeoShape",
    env: "Environment",
) -> Optional["GeoShape"]:
    kind = shape.kind
    F = _build_residuals(kind, shape.constraints, env)

    if F is None:
        return None

    x0 = _guess(shape, kind)
    sol, res = _newton_raphson(F, x0)
    if res > 1.0:
        raise GeoConstraintError(
            f"Constraints on {kind} '{shape.name}' are unsatisfiable "
            f"(final residual {res:.4f} > threshold 1.0). "
            f"Check for conflicting or missing constraints."
        )

    _write_back(shape, sol)
    return shape
