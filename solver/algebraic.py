from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Optional

import numpy as np

if TYPE_CHECKING:
    from interpreter.environment import Environment
    from interpreter.interpreter import GeoShape


def _pt(name: str, env: "Environment") -> Optional[np.ndarray]:
    try:
        val = env.get(name)
    except Exception:
        return None
    return _pt_from_val(val)


def _pt_from_val(val) -> Optional[np.ndarray]:
    if hasattr(val, "props"):
        x = val.props.get("x")
        y = val.props.get("y")
        if x is not None and y is not None:
            return np.array([float(x), float(y)])
    if isinstance(val, (tuple, list)) and len(val) == 2:
        return np.array([float(val[0]), float(val[1])])
    return None


def _resolve_target(t, env: "Environment") -> Optional[np.ndarray]:
    if isinstance(t, str):
        return _pt(t, env)
    return _pt_from_val(t)


def _segment_midpoint(target, env: "Environment") -> Optional[np.ndarray]:
    ref = None
    if isinstance(target, str):
        try:
            ref = env.get(target)
        except Exception:
            return None
    else:
        ref = target

    if hasattr(ref, "kind") and ref.kind == "segment":
        x1 = ref.props.get("x1")
        y1 = ref.props.get("y1")
        x2 = ref.props.get("x2")
        y2 = ref.props.get("y2")
        if any(v is None for v in (x1, y1, x2, y2)):
            return None
        return np.array([float(x1 + x2) / 2.0, float(y1 + y2) / 2.0])
    return None


def _normalise_line(a: float, b: float, c: float) -> tuple[float, float, float]:
    n = math.hypot(a, b)
    if n < 1e-12:
        return a, b, c
    return a / n, b / n, c / n


def _line_through_two_points(
    p1: np.ndarray, p2: np.ndarray
) -> tuple[float, float, float]:
    d = p2 - p1
    a, b = -d[1], d[0]  # normal = perpendicular to direction
    c = -(a * p1[0] + b * p1[1])
    return _normalise_line(a, b, c)


def _get_line_props(shape: "GeoShape") -> Optional[tuple[float, float, float]]:
    a = shape.props.get("a")
    b = shape.props.get("b")
    c = shape.props.get("c")
    if a is None or b is None or c is None:
        return None
    return float(a), float(b), float(c)


def resolve_point(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "point":
        return None

    for c in shape.constraints:
        kind = c.get("kind")

        if kind == "at":
            t = (c.get("targets") or [None])[0]
            if isinstance(t, (tuple, list)) and len(t) == 2:
                shape.props["x"] = float(t[0])
                shape.props["y"] = float(t[1])
                return shape
            if isinstance(t, (int, float)):
                shape.props["x"] = float(t)
                shape.props["y"] = 0.0
                return shape

        if kind == "on":
            raw = (c.get("targets") or [None])[0]
            # target may be a string name OR an already-evaluated GeoShape
            ref = env.get(raw) if isinstance(raw, str) else raw
            if ref is not None and hasattr(ref, "props"):
                if ref.kind == "circle":
                    cx = float(ref.props.get("cx", 0.0))
                    cy = float(ref.props.get("cy", 0.0))
                    r = float(ref.props.get("radius", 1.0))
                    shape.props["x"] = cx + r
                    shape.props["y"] = cy
                    return shape
                if ref.kind == "line":
                    abc = _get_line_props(ref)
                    if abc:
                        a, b, c_val = abc
                        denom = a * a + b * b
                        if denom > 1e-12:
                            shape.props["x"] = -a * c_val / denom
                            shape.props["y"] = -b * c_val / denom
                            return shape

    # Default: origin
    shape.props.setdefault("x", 0.0)
    shape.props.setdefault("y", 0.0)
    return shape


def resolve_segment(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "segment":
        return None

    args = shape.props.get("args", [])
    length = shape.props.get("length")

    def _resolve_target(t) -> Optional[np.ndarray]:
        if isinstance(t, str):
            return _pt(t, env)
        if hasattr(t, "props"):  # GeoShape already evaluated
            x = t.props.get("x")
            y = t.props.get("y")
            if x is not None and y is not None:
                return np.array([float(x), float(y)])
        if isinstance(t, (tuple, list)) and len(t) == 2:
            return np.array([float(t[0]), float(t[1])])
        return None

    if len(args) >= 2:
        p1 = _pt(args[0], env)
        p2 = _pt(args[1], env)
        if p1 is not None and p2 is not None:
            shape.props.update(
                {
                    "x1": p1[0],
                    "y1": p1[1],
                    "x2": p2[0],
                    "y2": p2[1],
                    "length": float(np.linalg.norm(p2 - p1)),
                }
            )
            return shape

    for c in shape.constraints:
        if c.get("kind") == "passes_through":
            targets = c.get("targets", [])
            if len(targets) >= 2:
                p1 = _resolve_target(targets[0])
                p2 = _resolve_target(targets[1])
                if p1 is not None and p2 is not None:
                    shape.props.update(
                        {
                            "x1": p1[0],
                            "y1": p1[1],
                            "x2": p2[0],
                            "y2": p2[1],
                            "length": float(np.linalg.norm(p2 - p1)),
                        }
                    )
                    return shape

    if length is not None and len(args) >= 1:
        p1 = _pt(args[0], env)
        if p1 is not None:
            shape.props.update(
                {
                    "x1": p1[0],
                    "y1": p1[1],
                    "x2": p1[0] + float(length),
                    "y2": p1[1],
                }
            )
            return shape

    if length is not None:
        shape.props.update(
            {
                "x1": 0.0,
                "y1": 0.0,
                "x2": float(length),
                "y2": 0.0,
            }
        )
        return shape

    return None


def resolve_line(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "line":
        return None

    through: list[np.ndarray] = []
    perp_of: Optional[str] = None
    para_of: Optional[str] = None
    tang_of: Optional[str] = None
    bisects_of: Optional[Any] = None

    for arg in shape.props.get("args", []):
        p = _pt(arg, env)
        if p is not None:
            through.append(p)

    for c in shape.constraints:
        kind = c.get("kind")
        if kind == "passes_through":
            for t in c.get("targets", []):
                if isinstance(t, str):
                    p = _pt(t, env)
                    if p is not None:
                        through.append(p)
                elif isinstance(t, (tuple, list)) and len(t) == 2:
                    through.append(np.array([float(t[0]), float(t[1])]))
                else:
                    p = _pt_from_val(t)
                    if p is not None:
                        through.append(p)
        elif kind == "perpendicular_to":
            perp_of = c.get("target")
        elif kind == "parallel_to":
            para_of = c.get("target")
        elif kind == "tangent_to":
            tang_of = c.get("target")
        elif kind == "bisects":
            bisects_of = c.get("target")

    if bisects_of is not None:
        midpoint = _segment_midpoint(bisects_of, env)
        if midpoint is not None:
            through.append(midpoint)

    if len(through) >= 2:
        if perp_of or para_of or tang_of:
            pass
    elif len(through) == 1:
        directions = [perp_of, para_of, tang_of]
        if sum(d is not None for d in directions) > 1:
            pass

    if len(through) >= 2:
        a, b, c_val = _line_through_two_points(through[0], through[1])
        shape.props.update({"a": a, "b": b, "c": c_val})
        return shape

    if len(through) == 1:
        p = through[0]

        if tang_of:
            try:
                ref = env.get(tang_of)
                if hasattr(ref, "kind") and ref.kind == "circle":
                    cx = float(ref.props.get("cx", 0))
                    cy = float(ref.props.get("cy", 0))
                    r = float(ref.props.get("radius", 0))
                    px, py = p
                    vx = px - cx
                    vy = py - cy
                    d2 = vx**2 + vy**2
                    d = math.sqrt(d2)
                    if d > r:
                        cos_phi = r / d
                        sin_phi = math.sqrt(1 - cos_phi**2)

                        ux = vx / d
                        uy = vy / d

                        px_u = -uy
                        py_u = ux

                        t1x = cx + r * (ux * cos_phi - px_u * sin_phi)
                        t1y = cy + r * (uy * cos_phi - py_u * sin_phi)
                        t2x = cx + r * (ux * cos_phi + px_u * sin_phi)
                        t2y = cy + r * (uy * cos_phi + py_u * sin_phi)
                        if t1x > px:
                            tx, ty = t1x, t1y
                        else:
                            tx, ty = t2x, t2y

                        a, b, c_val = _line_through_two_points(p, np.array([tx, ty]))
                        shape.props.update({"a": a, "b": b, "c": c_val})
                        return shape
            except Exception:
                pass

        if perp_of:
            try:
                ref = env.get(perp_of)
                abc = _get_line_props(ref) if hasattr(ref, "props") else None
            except Exception:
                abc = None
            if abc:
                ra, rb, _ = abc

                a, b = rb, -ra
                c_val = -(a * p[0] + b * p[1])
                a, b, c_val = _normalise_line(a, b, c_val)
                shape.props.update({"a": a, "b": b, "c": c_val})
                return shape

        if para_of:
            try:
                ref = env.get(para_of)
                abc = _get_line_props(ref) if hasattr(ref, "props") else None
            except Exception:
                abc = None
            if abc:
                a, b, _ = abc
                c_val = -(a * p[0] + b * p[1])
                a, b, c_val = _normalise_line(a, b, c_val)
                shape.props.update({"a": a, "b": b, "c": c_val})
                return shape

        a, b, c_val = _normalise_line(0.0, 1.0, -p[1])
        shape.props.update({"a": a, "b": b, "c": c_val})
        return shape

    if tang_of:
        try:
            ref = env.get(tang_of)
            if hasattr(ref, "kind") and ref.kind == "circle":
                cx = float(ref.props.get("cx", 0))
                cy = float(ref.props.get("cy", 0))
                r = float(ref.props.get("radius", 0))
                if r > 0:
                    c_val = -(cy + r)
                    a, b, c_val = _normalise_line(0.0, 1.0, c_val)
                    shape.props.update({"a": a, "b": b, "c": c_val})
                    return shape
        except Exception:
            pass

    shape.props.setdefault("a", 0.0)
    shape.props.setdefault("b", 1.0)
    shape.props.setdefault("c", 0.0)
    return shape


def resolve_ray(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "ray":
        return None

    through: list[np.ndarray] = []
    bisects_of: Optional[Any] = None

    for arg in shape.props.get("args", []):
        p = _pt(arg, env)
        if p is not None:
            through.append(p)

    for c in shape.constraints:
        kind = c.get("kind")
        if kind == "passes_through":
            for t in c.get("targets", []):
                p = _resolve_target(t, env)
                if p is not None:
                    through.append(p)
        elif kind == "at":
            t = (c.get("targets") or [None])[0]
            p = _resolve_target(t, env)
            if p is not None:
                through.insert(0, p)
        elif kind == "bisects":
            bisects_of = c.get("target")

    if bisects_of is not None:
        midpoint = _segment_midpoint(bisects_of, env)
        if midpoint is not None:
            through.append(midpoint)

    if len(through) >= 2:
        origin = through[0]
        d = through[1] - origin
        norm = np.linalg.norm(d)
        if norm > 1e-12:
            d = d / norm
        shape.props.update(
            {
                "ox": origin[0],
                "oy": origin[1],
                "dx": d[0],
                "dy": d[1],
            }
        )
        return shape

    if len(through) == 1:
        origin = through[0]
        shape.props.update(
            {
                "ox": origin[0],
                "oy": origin[1],
                "dx": 1.0,
                "dy": 0.0,
            }
        )
        return shape

    shape.props.setdefault("ox", 0.0)
    shape.props.setdefault("oy", 0.0)
    shape.props.setdefault("dx", 1.0)
    shape.props.setdefault("dy", 0.0)
    return shape


def resolve_circle(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "circle":
        return None

    radius = shape.props.get("radius")

    for c in shape.constraints:
        kind = c.get("kind")

        if kind == "centered_at":
            raw = (c.get("targets") or [None])[0]
            center = _resolve_target(raw, env)
            if center is not None and radius is not None:
                shape.props.update(
                    {
                        "cx": center[0],
                        "cy": center[1],
                        "radius": float(radius),
                    }
                )
                return shape

        if kind == "at":
            raw = (c.get("targets") or [None])[0]
            center = _resolve_target(raw, env)
            if center is not None and radius is not None:
                shape.props.update(
                    {
                        "cx": center[0],
                        "cy": center[1],
                        "radius": float(radius),
                    }
                )
                return shape

        if kind == "passes_through":
            pts = []
            for t in c.get("targets", []):
                p = _resolve_target(t, env)
                if p is not None:
                    pts.append(p)
            if len(pts) >= 3:
                result = _circumcircle_from_points(pts[0], pts[1], pts[2])
                if result:
                    cx, cy, r = result
                    shape.props.update({"cx": cx, "cy": cy, "radius": r})
                    return shape

        if kind == "tangent_to":
            target = c.get("target")
            try:
                ref = env.get(target)
                if hasattr(ref, "kind") and ref.kind == "line":
                    abc = _get_line_props(ref)
                    if abc:
                        a, b, c_val = abc
                        norm = math.sqrt(a**2 + b**2)
                        d = abs(c_val) / norm
                        shape.props.update({"cx": 0.0, "cy": 0.0, "radius": d})
                        return shape
                elif hasattr(ref, "kind") and ref.kind == "circle":
                    cx1 = float(ref.props.get("cx", 0))
                    cy1 = float(ref.props.get("cy", 0))
                    r1 = float(ref.props.get("radius", 0))
                    r = shape.props.get("radius", 0)
                    if r > 0:
                        # Simple external tangency: place to the right
                        cx = cx1 + r1 + r
                        cy = cy1
                        shape.props.update({"cx": cx, "cy": cy, "radius": float(r)})
                        return shape
            except Exception:
                pass

    # Default: at origin with given radius
    if radius is not None:
        shape.props.setdefault("cx", 0.0)
        shape.props.setdefault("cy", 0.0)
        shape.props["radius"] = float(radius)
        return shape

    return None


def resolve_arc(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "arc":
        return None

    radius = shape.props.get("radius")
    angle_prop = shape.props.get("angle")
    start_prop = shape.props.get("start")
    end_prop = shape.props.get("end")
    start_deg = shape.props.get(
        "start_deg", start_prop if start_prop is not None else 0.0
    )
    end_deg = shape.props.get(
        "end_deg",
        end_prop
        if end_prop is not None
        else (float(angle_prop) if angle_prop is not None else 90.0),
    )

    if angle_prop is not None:
        angle_val = float(angle_prop)
        if start_prop is not None or "start_deg" in shape.props:
            start_deg = float(start_deg)
            end_deg = start_deg + angle_val
        elif end_prop is not None or "end_deg" in shape.props:
            end_deg = float(end_deg)
            start_deg = end_deg - angle_val
        else:
            start_deg = 0.0
            end_deg = angle_val

    # Reuse circle logic for center/radius
    shape.kind = "circle"
    resolved = resolve_circle(shape, env)
    shape.kind = "arc"

    if resolved is None and radius is None:
        return None

    shape.props.setdefault("cx", 0.0)
    shape.props.setdefault("cy", 0.0)
    shape.props.setdefault("radius", 50.0)
    shape.props["start_deg"] = float(start_deg)
    shape.props["end_deg"] = float(end_deg)
    return shape


def resolve_triangle(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "triangle":
        return None

    args = shape.props.get("args", [])

    if len(args) >= 3:
        pts = [_pt(a, env) for a in args[:3]]
        if all(p is not None for p in pts):
            shape.props.update(
                {
                    "x1": pts[0][0],
                    "y1": pts[0][1],
                    "x2": pts[1][0],
                    "y2": pts[1][1],
                    "x3": pts[2][0],
                    "y3": pts[2][1],
                }
            )
            return shape

    through = []
    for c in shape.constraints:
        if c.get("kind") == "passes_through":
            for t in c.get("targets", []):
                if isinstance(t, str):
                    p = _pt(t, env)
                    if p is not None:
                        through.append(p)
                else:
                    p = _pt_from_val(t)
                    if p is not None:
                        through.append(p)
    if len(through) >= 3:
        shape.props.update(
            {
                "x1": through[0][0],
                "y1": through[0][1],
                "x2": through[1][0],
                "y2": through[1][1],
                "x3": through[2][0],
                "y3": through[2][1],
            }
        )
        return shape

    return None


def resolve_rectangle(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "rectangle":
        return None

    width = shape.props.get("length") or shape.props.get("width")
    height = shape.props.get("height")
    area = shape.props.get("area")

    if area is not None:
        if width is not None and height is None:
            height = float(area) / float(width)
        elif height is not None and width is None:
            width = float(area) / float(height)

    origin = np.array([0.0, 0.0])
    for c in shape.constraints:
        if c.get("kind") == "at":
            t = (c.get("targets") or [None])[0]
            p = _resolve_target(t, env)
            if p is not None:
                origin = p

    if width is not None and height is not None:
        w, h = float(width), float(height)
        x0, y0 = origin
        shape.props.update(
            {
                "x1": x0,
                "y1": y0,
                "x2": x0 + w,
                "y2": y0,
                "x3": x0 + w,
                "y3": y0 + h,
                "x4": x0,
                "y4": y0 + h,
                "width": w,
                "height": h,
            }
        )
        return shape

    through = []
    for c in shape.constraints:
        if c.get("kind") == "passes_through":
            for t in c.get("targets", []):
                p = _resolve_target(t, env)
                if p is not None:
                    through.append(p)
    if len(through) >= 2:
        p1, p2 = through[0], through[1]
        x0, y0 = min(p1[0], p2[0]), min(p1[1], p2[1])
        x1, y1 = max(p1[0], p2[0]), max(p1[1], p2[1])
        shape.props.update(
            {
                "x1": x0,
                "y1": y0,
                "x2": x1,
                "y2": y0,
                "x3": x1,
                "y3": y1,
                "x4": x0,
                "y4": y1,
                "width": x1 - x0,
                "height": y1 - y0,
            }
        )
        return shape

    return None


def resolve_rhombus(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "rhombus":
        return None

    side = shape.props.get("length")
    angle = shape.props.get("angle")  # interior angle in degrees

    if side is None or angle is None:
        return None

    s = float(side)
    ang = math.radians(float(angle))

    # Half-diagonals: d1 = s*cos(ang/2), d2 = s*sin(ang/2)
    d1 = s * math.cos(ang / 2)
    d2 = s * math.sin(ang / 2)

    cx, cy = 0.0, 0.0
    for c in shape.constraints:
        if c.get("kind") in ("at", "centered_at"):
            t = (c.get("targets") or [None])[0]
            p = _resolve_target(t, env)
            if p is not None:
                cx, cy = p[0], p[1]

    shape.props.update(
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
    return shape


def resolve_regular_poly(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "regular_poly":
        return None

    sides = shape.props.get("sides") or shape.props.get("n")
    radius = shape.props.get("radius")

    if sides is None or radius is None:
        return None

    n = int(sides)
    r = float(radius)

    cx, cy = 0.0, 0.0
    start_deg = float(shape.props.get("start_deg", 90.0))

    for c in shape.constraints:
        if c.get("kind") in ("centered_at", "at"):
            t = (c.get("targets") or [None])[0]
            p = _resolve_target(t, env)
            if p is not None:
                cx, cy = p[0], p[1]

    shape.props["cx"] = cx
    shape.props["cy"] = cy
    shape.props["radius"] = r
    shape.props["sides"] = n
    shape.props["start_deg"] = start_deg

    for i in range(n):
        theta = math.radians(start_deg + 360 * i / n)
        shape.props[f"x{i + 1}"] = cx + r * math.cos(theta)
        shape.props[f"y{i + 1}"] = cy + r * math.sin(theta)

    return shape


def resolve_polygon(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    if shape.kind != "polygon":
        return None

    # Collect point arrays from all available sources
    pts: list[np.ndarray] = []

    # Source 1: named args (set by DerivedDecl stub path)
    for a in shape.props.get("args", []):
        p = _resolve_target(a, env)
        if p is not None:
            pts.append(p)

    # Source 2: passes_through constraint (PrimitiveDecl path)
    if len(pts) < 3:
        for c in shape.constraints:
            if c.get("kind") == "passes_through":
                for t in c.get("targets", []):
                    p = _resolve_target(t, env)
                    if p is not None:
                        pts.append(p)

    if len(pts) < 3:
        return None

    shape.props["n"] = len(pts)
    for i, p in enumerate(pts):
        shape.props[f"x{i + 1}"] = p[0]
        shape.props[f"y{i + 1}"] = p[1]
    return shape


def resolve_ellipse(shape: "GeoShape", env: "Environment") -> Optional["GeoShape"]:
    """
    Ellipse defined by:
      - rx (semi-major), ry (semi-minor), center
      - OR two foci + sum-of-distances (major axis length)
    """
    if shape.kind != "ellipse":
        return None

    rx = shape.props.get("rx") or shape.props.get("radius")
    ry = shape.props.get("ry")

    cx, cy = 0.0, 0.0
    for c in shape.constraints:
        if c.get("kind") in ("centered_at", "at"):
            t = (c.get("targets") or [None])[0]
            p = _resolve_target(t, env)
            if p is not None:
                cx, cy = p[0], p[1]

    if rx is not None and ry is not None:
        shape.props.update(
            {
                "cx": cx,
                "cy": cy,
                "rx": float(rx),
                "ry": float(ry),
                "rotation_deg": float(shape.props.get("rotation_deg", 0.0)),
            }
        )
        return shape

    return None


def resolve_parallelogram(
    shape: "GeoShape", env: "Environment"
) -> Optional["GeoShape"]:
    """
    Parallelogram from base, side, and angle.
    p1 at origin (or constrained), p2 = p1 + (base, 0),
    p4 = p1 + (side*cos(angle), side*sin(angle)), p3 = p2 + (p4 - p1).
    """
    if shape.kind != "parallelogram":
        return None

    base = shape.props.get("length") or shape.props.get("base")
    side = shape.props.get("side")
    angle = shape.props.get("angle")

    if base is None or side is None or angle is None:
        return None

    b = float(base)
    s = float(side)
    ang = math.radians(float(angle))

    origin = np.array([0.0, 0.0])
    for c in shape.constraints:
        if c.get("kind") in ("at", "centered_at"):
            t = (c.get("targets") or [None])[0]
            p = _resolve_target(t, env)
            if p is not None:
                origin = p

    p1 = origin
    p2 = p1 + np.array([b, 0.0])
    p4 = p1 + np.array([s * math.cos(ang), s * math.sin(ang)])
    p3 = p2 + (p4 - p1)

    shape.props.update(
        {
            "x1": p1[0],
            "y1": p1[1],
            "x2": p2[0],
            "y2": p2[1],
            "x3": p3[0],
            "y3": p3[1],
            "x4": p4[0],
            "y4": p4[1],
        }
    )
    return shape


def resolve_midpoint(
    result: "GeoShape", args: list[str], env: "Environment"
) -> Optional["GeoShape"]:
    """midpoint M of segment  OR  midpoint M of pointA pointB"""
    if len(args) == 1:
        try:
            seg = env.get(args[0])
        except Exception:
            return None
        if hasattr(seg, "props"):
            x1 = seg.props.get("x1")
            y1 = seg.props.get("y1")
            x2 = seg.props.get("x2")
            y2 = seg.props.get("y2")
            if all(v is not None for v in (x1, y1, x2, y2)):
                mid = (
                    np.array([float(x1), float(y1)]) + np.array([float(x2), float(y2)])
                ) / 2
                result.props["x"] = mid[0]
                result.props["y"] = mid[1]
                return result

    if len(args) >= 2:
        p1 = _pt(args[0], env)
        p2 = _pt(args[1], env)
        if p1 is not None and p2 is not None:
            mid = (p1 + p2) / 2
            result.props["x"] = mid[0]
            result.props["y"] = mid[1]
            return result

    return None


def resolve_intersection(
    result: "GeoShape", args: list[str], env: "Environment"
) -> Optional["GeoShape"]:
    if len(args) < 2:
        return None
    try:
        o1 = env.get(args[0])
        o2 = env.get(args[1])
    except Exception:
        return None
    if not (hasattr(o1, "props") and hasattr(o2, "props")):
        return None

    k1, k2 = o1.kind, o2.kind

    # line ∩ line
    if k1 == "line" and k2 == "line":
        abc1 = _get_line_props(o1)
        abc2 = _get_line_props(o2)
        if abc1 and abc2:
            a1, b1, c1 = abc1
            a2, b2, c2 = abc2
            A = np.array([[a1, b1], [a2, b2]])
            rhs = np.array([-c1, -c2])
            if abs(np.linalg.det(A)) < 1e-12:
                return None  # parallel
            pt = np.linalg.solve(A, rhs)
            result.props["x"] = pt[0]
            result.props["y"] = pt[1]
            return result

    # line ∩ circle  (or circle ∩ line)
    def _lc(line, circle):
        abc = _get_line_props(line)
        if not abc:
            return None
        a, b, c_val = abc
        cx = float(circle.props.get("cx", 0.0))
        cy = float(circle.props.get("cy", 0.0))
        r = float(circle.props.get("radius", 1.0))
        # distance from centre to line
        dist = abs(a * cx + b * cy + c_val)
        if dist > r + 1e-9:
            return None
        # foot of perpendicular
        fx = cx - a * (a * cx + b * cy + c_val)
        fy = cy - b * (a * cx + b * cy + c_val)
        h = math.sqrt(max(0.0, r**2 - dist**2))
        # direction along line
        tx, ty = -b, a
        tn = math.hypot(tx, ty)
        if tn < 1e-12:
            return None
        tx, ty = tx / tn, ty / tn
        return fx + h * tx, fy + h * ty

    if k1 == "line" and k2 == "circle":
        pt = _lc(o1, o2)
    elif k1 == "circle" and k2 == "line":
        pt = _lc(o2, o1)
    else:
        return None  # circle ∩ circle → numeric

    if pt is None:
        return None
    result.props["x"] = pt[0]
    result.props["y"] = pt[1]
    return result


def resolve_perpendicular_bisector(
    result: "GeoShape", args: list[str], env: "Environment"
) -> Optional["GeoShape"]:
    """perpendicular_bisector PB of segment AB"""
    if not args:
        return None
    try:
        seg = env.get(args[0])
    except Exception:
        return None
    if not hasattr(seg, "props"):
        return None

    x1 = seg.props.get("x1")
    y1 = seg.props.get("y1")
    x2 = seg.props.get("x2")
    y2 = seg.props.get("y2")
    if any(v is None for v in (x1, y1, x2, y2)):
        return None

    p1 = np.array([float(x1), float(y1)])
    p2 = np.array([float(x2), float(y2)])
    mid = (p1 + p2) / 2
    d = p2 - p1  # direction of segment
    # Bisector is perpendicular to d, passing through mid
    # Normal of bisector is d itself
    a, b = d[0], d[1]
    c_val = -(a * mid[0] + b * mid[1])
    a, b, c_val = _normalise_line(a, b, c_val)

    result.kind = "line"
    result.props.update({"a": a, "b": b, "c": c_val})
    return result


def resolve_angle_bisector(
    result: "GeoShape", args: list[str], env: "Environment"
) -> Optional["GeoShape"]:
    # Case 1: three vertex names
    if len(args) == 3:
        a_pt = _pt(args[0], env)
        b_pt = _pt(args[1], env)  # vertex
        c_pt = _pt(args[2], env)
        if a_pt is not None and b_pt is not None and c_pt is not None:
            u = a_pt - b_pt
            v = c_pt - b_pt
            nu = np.linalg.norm(u)
            nv = np.linalg.norm(v)
            if nu > 1e-12 and nv > 1e-12:
                u_hat = u / nu
                v_hat = v / nv
                bisector_dir = u_hat + v_hat
                bn = np.linalg.norm(bisector_dir)
                if bn > 1e-12:
                    bisector_dir = bisector_dir / bn
                result.kind = "ray"
                result.props.update(
                    {
                        "ox": b_pt[0],
                        "oy": b_pt[1],
                        "dx": bisector_dir[0],
                        "dy": bisector_dir[1],
                    }
                )
                return result

    if len(args) >= 1:
        try:
            angle_deg = env.get(f"__angle_{args[0]}")
        except Exception:
            angle_deg = 0.0
        half_rad = math.radians(float(angle_deg) / 2)
        result.kind = "ray"
        result.props.update(
            {
                "ox": 0.0,
                "oy": 0.0,
                "dx": math.cos(half_rad),
                "dy": math.sin(half_rad),
            }
        )
        return result

    return None


def resolve_circumcircle(
    result: "GeoShape", args: list[str], env: "Environment"
) -> Optional["GeoShape"]:
    """circumcircle CC of triangle T"""
    if not args:
        return None
    try:
        tri = env.get(args[0])
    except Exception:
        return None
    if not hasattr(tri, "props"):
        return None

    coords = _triangle_coords(tri)
    if coords is None:
        return None
    p1, p2, p3 = coords

    r = _circumcircle_from_points(p1, p2, p3)
    if r is None:
        return None
    cx, cy, radius = r
    result.kind = "circle"
    result.props.update({"cx": cx, "cy": cy, "radius": radius})
    return result


def resolve_incircle(
    result: "GeoShape", args: list[str], env: "Environment"
) -> Optional["GeoShape"]:
    """incircle IC of triangle T"""
    if not args:
        return None
    try:
        tri = env.get(args[0])
    except Exception:
        return None
    if not hasattr(tri, "props"):
        return None

    coords = _triangle_coords(tri)
    if coords is None:
        return None
    p1, p2, p3 = coords

    a = float(np.linalg.norm(p3 - p2))  # side opposite p1
    b = float(np.linalg.norm(p3 - p1))  # side opposite p2
    c = float(np.linalg.norm(p2 - p1))  # side opposite p3
    s = a + b + c
    if s < 1e-12:
        return None

    center = (a * p1 + b * p2 + c * p3) / s
    d1 = p2 - p1
    d2 = p3 - p1
    area = abs(d1[0] * d2[1] - d1[1] * d2[0]) / 2
    inradius = area / (s / 2)

    result.kind = "circle"
    result.props.update({"cx": center[0], "cy": center[1], "radius": inradius})
    return result


def resolve_convex_hull(
    result: "GeoShape", args: list[str], env: "Environment"
) -> Optional["GeoShape"]:
    """convex_hull P of A B C D ..."""
    pts = []
    for name in args:
        p = _pt(name, env)
        if p is not None:
            pts.append(p)

    if len(pts) < 3:
        return None

    hull = _gift_wrap(pts)
    result.kind = "polygon"
    result.props["n"] = len(hull)
    for i, p in enumerate(hull):
        result.props[f"x{i + 1}"] = p[0]
        result.props[f"y{i + 1}"] = p[1]
    return result


def reflect_point_over_line(p: np.ndarray, a: float, b: float, c: float) -> np.ndarray:
    """Reflect point p over line ax + by + c = 0."""
    denom = a * a + b * b
    if denom < 1e-12:
        return p.copy()
    t = (a * p[0] + b * p[1] + c) / denom
    return p - 2 * t * np.array([a, b])


def rotate_point_around(
    p: np.ndarray, center: np.ndarray, angle_deg: float
) -> np.ndarray:
    """Rotate point p by angle_deg around center."""
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    R = np.array([[cos_a, -sin_a], [sin_a, cos_a]])
    return center + R @ (p - center)


def scale_point_from(p: np.ndarray, center: np.ndarray, factor: float) -> np.ndarray:
    """Scale point p by factor from center."""
    return center + factor * (p - center)


def _triangle_coords(
    tri: "GeoShape",
) -> Optional[tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Extract three vertex arrays from a resolved triangle shape."""
    x1 = tri.props.get("x1")
    y1 = tri.props.get("y1")
    x2 = tri.props.get("x2")
    y2 = tri.props.get("y2")
    x3 = tri.props.get("x3")
    y3 = tri.props.get("y3")
    if any(v is None for v in (x1, y1, x2, y2, x3, y3)):
        return None
    return (
        np.array([float(x1), float(y1)]),
        np.array([float(x2), float(y2)]),
        np.array([float(x3), float(y3)]),
    )


def _circumcircle_from_points(
    p1: np.ndarray, p2: np.ndarray, p3: np.ndarray
) -> Optional[tuple[float, float, float]]:
    """Return (cx, cy, radius) of the circumcircle of three points, or None."""
    ax, ay = p2 - p1
    bx, by = p3 - p1
    D = 2 * (ax * by - ay * bx)
    if abs(D) < 1e-12:
        return None  # collinear
    ux = (by * (ax**2 + ay**2) - ay * (bx**2 + by**2)) / D
    uy = (ax * (bx**2 + by**2) - bx * (ax**2 + ay**2)) / D
    cx = p1[0] + ux
    cy = p1[1] + uy
    r = float(np.linalg.norm(np.array([ux, uy])))
    return cx, cy, r


def _gift_wrap(pts: list[np.ndarray]) -> list[np.ndarray]:
    """Jarvis march convex hull. Returns ordered hull vertices."""
    n = len(pts)
    if n < 3:
        return pts
    start = int(np.argmin([p[0] for p in pts]))
    hull = []
    cur = start
    while True:
        hull.append(pts[cur])
        nxt = (cur + 1) % n
        for i in range(n):
            ab = pts[nxt] - pts[cur]
            ai = pts[i] - pts[cur]
            cross = ab[0] * ai[1] - ab[1] * ai[0]
            if cross > 0:
                nxt = i
        cur = nxt
        if cur == start:
            break
    return hull
