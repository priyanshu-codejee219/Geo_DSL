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
