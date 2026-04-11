from __future__ import annotations

import math
from typing import Any

DEFAULT_STROKE = "#2563eb"
DEFAULT_FILL = "none"
DEFAULT_STROKE_WIDTH = 1.8
POINT_RADIUS = 4.0
ARROW_SIZE = 8.0
GRID_STROKE = "#e2e8f0"
GRID_STROKE_WIDTH = 0.8
AXIS_STROKE = "#94a3b8"
LABEL_FONT = "13px 'Inter', 'Segoe UI', sans-serif"
NOTE_FONT = "12px 'Inter', 'Segoe UI', sans-serif"
MEASURE_FONT = "11px 'Inter', 'Segoe UI', sans-serif"
LABEL_OFFSET = 10


def _attrs(**kwargs) -> str:
    parts = []
    for k, v in kwargs.items():
        k = k.replace("_", "-")
        parts.append(f'{k}="{v}"')
    return " ".join(parts)


def _style(stroke: str, fill: str, stroke_width: float, opacity: float) -> str:
    return (
        f'stroke="{stroke}" fill="{fill}" '
        f'stroke-width="{stroke_width}" opacity="{opacity}"'
    )


def _p(x: float, y: float) -> str:
    return f"{x:.3f},{y:.3f}"


def _clamp_line(
    a: float,
    b: float,
    c: float,
    w: float,
    h: float,
) -> list[tuple[float, float]]:
    pts: list[tuple[float, float]] = []

    def _add(x: float, y: float) -> None:
        if -1e-6 <= x <= w + 1e-6 and -1e-6 <= y <= h + 1e-6:
            pts.append((x, y))

    if abs(b) > 1e-9:
        _add(0.0, (-c) / b)
        _add(w, -(a * w + c) / b)
    if abs(a) > 1e-9:
        _add((-c) / a, 0.0)
        _add(-(b * h + c) / a, h)

    unique: list[tuple[float, float]] = []
    for p in pts:
        if not any(math.hypot(p[0] - q[0], p[1] - q[1]) < 1e-4 for q in unique):
            unique.append(p)
    return unique[:2]


def _polygon_points(props: dict[str, Any], n: int) -> list[tuple[float, float]]:
    result = []
    for i in range(1, n + 1):
        x = props.get(f"x{i}")
        y = props.get(f"y{i}")
        if x is not None and y is not None:
            result.append((float(x), float(y)))
    return result


def svg_point(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_STROKE,
    stroke_width: float = 1.0,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    x = float(props.get("x", 0.0))
    y = float(props.get("y", 0.0))
    return (
        f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{POINT_RADIUS}" '
        f'stroke="{stroke}" fill="{fill}" opacity="{opacity}" />'
    )


def svg_segment(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    x1 = float(props.get("x1", 0.0))
    y1 = float(props.get("y1", 0.0))
    x2 = float(props.get("x2", 0.0))
    y2 = float(props.get("y2", 0.0))
    return (
        f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
        f"{_style(stroke, fill, stroke_width, opacity)} />"
    )


def svg_line(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    viewport_w: float = 800.0,
    viewport_h: float = 600.0,
    **_: Any,
) -> str:
    a = float(props.get("a", 0.0))
    b = float(props.get("b", 1.0))
    c = float(props.get("c", 0.0))
    pts = _clamp_line(a, b, c, viewport_w, viewport_h)
    if len(pts) < 2:
        return ""
    x1, y1 = pts[0]
    x2, y2 = pts[1]
    return (
        f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
        f"{_style(stroke, fill, stroke_width, opacity)} />"
    )


def svg_ray(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    viewport_w: float = 800.0,
    viewport_h: float = 600.0,
    **_: Any,
) -> str:
    ox = float(props.get("ox", 0.0))
    oy = float(props.get("oy", 0.0))
    dx = float(props.get("dx", 1.0))
    dy = float(props.get("dy", 0.0))

    # Extend to viewport boundary
    t_max = max(viewport_w, viewport_h) * 2
    ex = ox + dx * t_max
    ey = oy + dy * t_max

    # Arrowhead at end
    angle = math.atan2(dy, dx)
    a1 = angle + math.radians(150)
    a2 = angle - math.radians(150)
    ax1 = ex + ARROW_SIZE * math.cos(a1)
    ay1 = ey + ARROW_SIZE * math.sin(a1)
    ax2 = ex + ARROW_SIZE * math.cos(a2)
    ay2 = ey + ARROW_SIZE * math.sin(a2)

    style = _style(stroke, fill, stroke_width, opacity)
    return (
        f'<line x1="{ox:.3f}" y1="{oy:.3f}" x2="{ex:.3f}" y2="{ey:.3f}" {style} />'
        f'<line x1="{ex:.3f}" y1="{ey:.3f}" x2="{ax1:.3f}" y2="{ay1:.3f}" {style} />'
        f'<line x1="{ex:.3f}" y1="{ey:.3f}" x2="{ax2:.3f}" y2="{ay2:.3f}" {style} />'
    )


def svg_circle(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    cx = float(props.get("cx", 0.0))
    cy = float(props.get("cy", 0.0))
    r = float(props.get("radius", 1.0))
    return (
        f'<circle cx="{cx:.3f}" cy="{cy:.3f}" r="{r:.3f}" '
        f"{_style(stroke, fill, stroke_width, opacity)} />"
    )


def svg_arc(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    cx = float(props.get("cx", 0.0))
    cy = float(props.get("cy", 0.0))
    r = float(props.get("radius", 1.0))
    start_deg = float(props.get("start_deg", 0.0))
    end_deg = float(props.get("end_deg", 90.0))

    start_rad = math.radians(start_deg)
    end_rad = math.radians(end_deg)

    x1 = cx + r * math.cos(start_rad)
    y1 = cy + r * math.sin(start_rad)
    x2 = cx + r * math.cos(end_rad)
    y2 = cy + r * math.sin(end_rad)

    delta = (end_deg - start_deg) % 360
    large = 1 if delta > 180 else 0

    return (
        f'<path d="M {x1:.3f} {y1:.3f} A {r:.3f} {r:.3f} 0 {large} 1 {x2:.3f} {y2:.3f}" '
        f"{_style(stroke, fill, stroke_width, opacity)} />"
    )


def svg_ellipse(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    cx = float(props.get("cx", 0.0))
    cy = float(props.get("cy", 0.0))
    rx = float(props.get("rx", 1.0))
    ry = float(props.get("ry", 1.0))
    rot = float(props.get("rotation_deg", 0.0))
    return (
        f'<ellipse cx="{cx:.3f}" cy="{cy:.3f}" rx="{rx:.3f}" ry="{ry:.3f}" '
        f'transform="rotate({rot:.3f} {cx:.3f} {cy:.3f})" '
        f"{_style(stroke, fill, stroke_width, opacity)} />"
    )


def _svg_polygon_from_vertices(
    pts: list[tuple[float, float]],
    stroke: str,
    fill: str,
    stroke_width: float,
    opacity: float,
    closed: bool = True,
) -> str:
    if len(pts) < 2:
        return ""
    points_str = " ".join(f"{x:.3f},{y:.3f}" for x, y in pts)
    tag = "polygon" if closed else "polyline"
    return (
        f'<{tag} points="{points_str}" {_style(stroke, fill, stroke_width, opacity)} />'
    )


def svg_triangle(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    pts = _polygon_points(props, 3)
    return _svg_polygon_from_vertices(pts, stroke, fill, stroke_width, opacity)


def svg_rectangle(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    pts = _polygon_points(props, 4)
    if pts:
        return _svg_polygon_from_vertices(pts, stroke, fill, stroke_width, opacity)
    x = float(props.get("x1", 0.0))
    y = float(props.get("y1", 0.0))
    width = float(props.get("width", 0.0))
    height = float(props.get("height", 0.0))
    return (
        f'<rect x="{x:.3f}" y="{y:.3f}" width="{width:.3f}" height="{height:.3f}" '
        f"{_style(stroke, fill, stroke_width, opacity)} />"
    )


def svg_rhombus(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    pts = _polygon_points(props, 4)
    return _svg_polygon_from_vertices(pts, stroke, fill, stroke_width, opacity)


def svg_parallelogram(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    pts = _polygon_points(props, 4)
    return _svg_polygon_from_vertices(pts, stroke, fill, stroke_width, opacity)


def svg_regular_poly(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    n = int(props.get("sides", props.get("n", 6)))
    pts = _polygon_points(props, n)
    return _svg_polygon_from_vertices(pts, stroke, fill, stroke_width, opacity)


def svg_polygon(
    props: dict[str, Any],
    stroke: str = DEFAULT_STROKE,
    fill: str = DEFAULT_FILL,
    stroke_width: float = DEFAULT_STROKE_WIDTH,
    opacity: float = 1.0,
    **_: Any,
) -> str:
    n = int(props.get("n", 0))
    pts = _polygon_points(props, n)
    return _svg_polygon_from_vertices(pts, stroke, fill, stroke_width, opacity)


def _order_locus_points(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    if len(points) < 3:
        return points

    cx = sum(x for x, _ in points) / len(points)
    cy = sum(y for _, y in points) / len(points)
    return sorted(points, key=lambda pt: math.atan2(pt[1] - cy, pt[0] - cx))


def svg_locus(
    props: dict[str, Any],
    stroke: str = "#dc2626",
    fill: str = "none",
    stroke_width: float = 1.5,
    opacity: float = 0.95,
    **_: Any,
) -> str:
    pts = props.get("points", [])
    if len(pts) < 2:
        return ""

    unique_pts: list[tuple[float, float]] = []
    seen: set[tuple[float, float]] = set()
    for x, y in pts:
        key = (round(float(x), 8), round(float(y), 8))
        if key not in seen:
            seen.add(key)
            unique_pts.append((float(x), float(y)))

    if len(unique_pts) < 3:
        return ""

    ordered_pts = _order_locus_points(unique_pts)
    path_data = "M " + _p(*ordered_pts[0])
    for x, y in ordered_pts[1:]:
        path_data += " L " + _p(x, y)
    path_data += " Z"

    return (
        f'<path d="{path_data}" stroke="{stroke}" fill="{fill}" '
        f'stroke-width="{stroke_width:.3f}" opacity="{opacity}" '
        f'stroke-linecap="round" stroke-linejoin="round" />'
    )


def svg_label(
    x: float,
    y: float,
    text: str,
    offset_x: float = LABEL_OFFSET,
    offset_y: float = -LABEL_OFFSET,
) -> str:
    tx = x + offset_x
    ty = y + offset_y
    return (
        f'<text x="{tx:.3f}" y="{ty:.3f}" '
        f'font="{LABEL_FONT}" fill="#1e293b" '
        f'font-size="13" font-family="Inter, Segoe UI, sans-serif">'
        f"{_escape(text)}</text>"
    )


def svg_note(x: float, y: float, text: str) -> str:
    return (
        f'<text x="{x:.3f}" y="{y:.3f}" '
        f'font="{NOTE_FONT}" fill="#475569" '
        f'font-size="12" font-family="Inter, Segoe UI, sans-serif" '
        f'font-style="italic">'
        f"{_escape(text)}</text>"
    )


def svg_measure_annotation(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    text: str,
    offset: float = 18.0,
) -> str:

    mx = (x1 + x2) / 2
    my = (y1 + y2) / 2
    dx = x2 - x1
    dy = y2 - y1
    length = math.hypot(dx, dy)
    if length < 1e-6:
        return ""

    nx = -dy / length
    ny = dx / length

    lx = mx + nx * offset
    ly = my + ny * offset

    t = 5.0
    tick1a = (x1 + nx * t, y1 + ny * t)
    tick1b = (x1 - nx * t, y1 - ny * t)
    tick2a = (x2 + nx * t, y2 + ny * t)
    tick2b = (x2 - nx * t, y2 - ny * t)

    dim_style = 'stroke="#64748b" stroke-width="1" fill="none"'
    return (
        f'<line x1="{lx - nx * offset + nx * (offset - 2):.3f}" '
        f'y1="{ly - ny * offset + ny * (offset - 2):.3f}" '
        f'x2="{lx + (x2 - x1) / length * length - nx * offset + nx * (offset - 2):.3f}" '
        f'y2="{ly + (y2 - y1) / length * length - ny * offset + ny * (offset - 2):.3f}" '
        f"{dim_style} />"
        f'<line x1="{tick1a[0]:.3f}" y1="{tick1a[1]:.3f}" '
        f'x2="{tick1b[0]:.3f}" y2="{tick1b[1]:.3f}" {dim_style} />'
        f'<line x1="{tick2a[0]:.3f}" y1="{tick2a[1]:.3f}" '
        f'x2="{tick2b[0]:.3f}" y2="{tick2b[1]:.3f}" {dim_style} />'
        f'<text x="{lx:.3f}" y="{ly:.3f}" text-anchor="middle" '
        f'font-size="11" font-family="Inter, Segoe UI, sans-serif" fill="#64748b">'
        f"{_escape(text)}</text>"
    )


def svg_grid(
    viewport_w: float,
    viewport_h: float,
    spacing: float = 50.0,
    origin_x: float = 0.0,
    origin_y: float = 0.0,
) -> str:
    lines: list[str] = []

    gstyle = f'stroke="{GRID_STROKE}" stroke-width="{GRID_STROKE_WIDTH}"'
    x = origin_x % spacing
    while x <= viewport_w:
        lines.append(
            f'<line x1="{x:.1f}" y1="0" x2="{x:.1f}" y2="{viewport_h:.1f}" {gstyle} />'
        )
        x += spacing
    y = origin_y % spacing
    while y <= viewport_h:
        lines.append(
            f'<line x1="0" y1="{y:.1f}" x2="{viewport_w:.1f}" y2="{y:.1f}" {gstyle} />'
        )
        y += spacing

    astyle = f'stroke="{AXIS_STROKE}" stroke-width="1.2"'
    if 0 <= origin_x <= viewport_w:
        lines.append(
            f'<line x1="{origin_x:.1f}" y1="0" '
            f'x2="{origin_x:.1f}" y2="{viewport_h:.1f}" {astyle} />'
        )
    if 0 <= origin_y <= viewport_h:
        lines.append(
            f'<line x1="0" y1="{origin_y:.1f}" '
            f'x2="{viewport_w:.1f}" y2="{origin_y:.1f}" {astyle} />'
        )

    return "\n".join(lines)


SHAPE_GENERATORS: dict[str, Any] = {
    "point": svg_point,
    "segment": svg_segment,
    "line": svg_line,
    "ray": svg_ray,
    "circle": svg_circle,
    "arc": svg_arc,
    "ellipse": svg_ellipse,
    "triangle": svg_triangle,
    "rectangle": svg_rectangle,
    "rhombus": svg_rhombus,
    "parallelogram": svg_parallelogram,
    "regular_poly": svg_regular_poly,
    "polygon": svg_polygon,
    "locus": svg_locus,
}


def render_shape(
    kind: str,
    props: dict[str, Any],
    **opts: Any,
) -> str:
    fn = SHAPE_GENERATORS.get(kind)
    if fn is None:
        return f"<!-- unsupported shape kind: {kind} -->"
    return fn(props, **opts)


def _escape(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def shape_centre(kind: str, props: dict[str, Any]) -> tuple[float, float]:
    p = props
    if kind == "point":
        return float(p.get("x", 0)), float(p.get("y", 0))
    if kind in ("circle", "arc", "ellipse", "regular_poly", "rhombus"):
        return float(p.get("cx", 0)), float(p.get("cy", 0))
    if kind == "segment":
        return (
            (float(p.get("x1", 0)) + float(p.get("x2", 0))) / 2,
            (float(p.get("y1", 0)) + float(p.get("y2", 0))) / 2,
        )
    if kind in ("triangle", "rectangle", "polygon", "parallelogram", "convex_hull"):
        n = int(p.get("n", 3 if kind == "triangle" else 4))
        xs = [float(p.get(f"x{i}", 0)) for i in range(1, n + 1)]
        ys = [float(p.get(f"y{i}", 0)) for i in range(1, n + 1)]
        return (sum(xs) / max(len(xs), 1)), (sum(ys) / max(len(ys), 1))
    if kind == "line":
        return 0.0, 0.0
    return 0.0, 0.0
