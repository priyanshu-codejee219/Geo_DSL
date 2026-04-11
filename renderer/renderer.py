from __future__ import annotations

import math
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

if TYPE_CHECKING:
    from evaluator.evaluator import SweepFrame
    from interpreter.interpreter import GeoShape, Interpreter

from .svg_backend import (
    render_shape,
    shape_centre,
    svg_grid,
    svg_label,
    svg_measure_annotation,
    svg_note,
)

DEFAULT_WIDTH = 800
DEFAULT_HEIGHT = 600
PADDING = 60
MIN_WORLD_SPAN = 100.0


class Renderer:
    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        padding: int = PADDING,
        background: str = "#f8fafc",
    ) -> None:
        self.width = width
        self.height = height
        self.padding = padding
        self.background = background

    def render(self, interp: "Interpreter") -> str:
        return self.render_static(
            shapes=interp.shapes,
            labels=interp.labels,
            hidden=interp.hidden,
            notes=interp.notes,
            show_grid=interp.show_grid,
            measure_targets=set(),
        )

    def render_static(
        self,
        shapes: List[Tuple[str, "GeoShape"]],
        labels: Dict[str, str] = None,
        hidden: set = None,
        notes: List[str] = None,
        show_grid: bool = False,
        measure_targets: set = None,
    ) -> str:

        labels = labels or {}
        hidden = hidden or set()
        notes = notes or []
        measure_targets = measure_targets or set()

        transform = self._compute_transform(shapes)

        body_parts: list[str] = []

        if show_grid:
            ox, oy = transform.world_to_screen(0.0, 0.0)
            body_parts.append(
                svg_grid(
                    self.width,
                    self.height,
                    spacing=max(20.0, transform.scale * 50),
                    origin_x=ox,
                    origin_y=oy,
                )
            )

        visible = [(name, shape) for name, shape in shapes if name not in hidden]
        shapes_dict = dict(shapes)

        for name, shape in visible:
            transformed_props = transform.transform_props(shape.kind, shape.props)
            opts = {
                "viewport_w": float(self.width),
                "viewport_h": float(self.height),
            }
            svg_elem = render_shape(shape.kind, transformed_props, **opts)
            if svg_elem:
                body_parts.append(f"  <!-- {name} ({shape.kind}) -->")
                body_parts.append(f"  {svg_elem}")

        for name, text in labels.items():
            if name in hidden or name not in shapes_dict:
                continue
            shape = shapes_dict[name]
            cx, cy = shape_centre(shape.kind, shape.props)
            sx, sy = transform.world_to_screen(cx, cy)
            body_parts.append(f"  {svg_label(sx, sy, text)}")

        for name, shape in visible:
            if shape.kind == "point" and name not in labels:
                cx = float(shape.props.get("x", 0.0))
                cy = float(shape.props.get("y", 0.0))
                sx, sy = transform.world_to_screen(cx, cy)
                body_parts.append(
                    f"  {svg_label(sx, sy, name, offset_x=8, offset_y=-8)}"
                )

        for name in measure_targets:
            if name in shapes_dict and name not in hidden:
                shape = shapes_dict[name]
                ann = self._measure_annotation(shape, transform)
                if ann:
                    body_parts.append(f"  {ann}")

        for i, note_text in enumerate(notes):
            ny = self.padding // 2 + i * 18
            body_parts.append(f"  {svg_note(self.padding, float(ny), note_text)}")

        return self._wrap_svg("\n".join(body_parts))

    def render_sweep(
        self,
        sweep_frames: List["SweepFrame"],
        labels: Dict[str, str] = None,
        hidden: set = None,
        notes: List[str] = None,
        show_grid: bool = False,
    ) -> List[str]:
        if not sweep_frames:
            return []

        all_shapes: List[Tuple[str, "GeoShape"]] = []
        for frame in sweep_frames:
            all_shapes.extend(frame.shapes.items())

        transform = self._compute_transform(all_shapes)

        svgs: list[str] = []
        for frame in sweep_frames:
            svg = self._render_with_transform(
                shapes=list(frame.shapes.items()),
                transform=transform,
                labels=labels or {},
                hidden=hidden or set(),
                notes=notes or [],
                show_grid=show_grid,
            )
            svgs.append(svg)
        return svgs

    def render_animated_svg(
        self,
        sweep_frames: List["SweepFrame"],
        labels: Dict[str, str] = None,
        hidden: set = None,
        notes: List[str] = None,
        show_grid: bool = False,
        fps: int = 12,
    ) -> str:
        if not sweep_frames:
            return self._wrap_svg("")

        n_frames = len(sweep_frames)
        duration = n_frames / fps
        frame_dur = duration / n_frames

        all_shapes: Dict[str, "GeoShape"] = {}
        for frame in sweep_frames:
            all_shapes.update(dict(frame.shapes))
        transform = self._compute_transform(list(all_shapes.items()))

        body_parts: list[str] = []

        if show_grid:
            ox, oy = transform.world_to_screen(0.0, 0.0)
            body_parts.append(
                svg_grid(
                    self.width,
                    self.height,
                    spacing=max(20.0, transform.scale * 50),
                    origin_x=ox,
                    origin_y=oy,
                )
            )

        hidden = hidden or set()

        all_names = set()
        for frame in sweep_frames:
            all_names.update(name for name, _ in frame.shapes)

        for name in sorted(all_names):
            if name in hidden:
                continue
            parts = [f'  <g id="shape_{_svg_id(name)}">']
            for fi, frame in enumerate(sweep_frames):
                frame_dict = dict(frame.shapes)
                shape = frame_dict.get(name)
                if shape is None:
                    continue
                tprops = transform.transform_props(shape.kind, shape.props)
                elem = render_shape(
                    shape.kind,
                    tprops,
                    viewport_w=float(self.width),
                    viewport_h=float(self.height),
                )
                if not elem:
                    continue
                begin_s = fi * frame_dur
                _ = begin_s + frame_dur
                parts.append(
                    f'    <g visibility="hidden">'
                    f'<animate attributeName="visibility" '
                    f'values="visible;hidden" '
                    f'keyTimes="0;1" '
                    f'begin="{begin_s:.3f}s" dur="{frame_dur:.3f}s" '
                    f'repeatCount="indefinite" />'
                    f"{elem}</g>"
                )
            parts.append("  </g>")
            body_parts.extend(parts)

        for i, note_text in enumerate(notes or []):
            ny = self.padding // 2 + i * 18
            body_parts.append(svg_note(self.padding, float(ny), note_text))

        return self._wrap_svg("\n".join(body_parts))

    def _render_with_transform(
        self,
        shapes: List[Tuple[str, "GeoShape"]],
        transform: "_ViewportTransform",
        labels: Dict[str, str],
        hidden: set,
        notes: List[str],
        show_grid: bool,
    ) -> str:
        body_parts: list[str] = []

        if show_grid:
            ox, oy = transform.world_to_screen(0.0, 0.0)
            body_parts.append(
                svg_grid(
                    self.width,
                    self.height,
                    spacing=max(20.0, transform.scale * 50),
                    origin_x=ox,
                    origin_y=oy,
                )
            )

        for name, shape in shapes:
            if name in hidden:
                continue
            tprops = transform.transform_props(shape.kind, shape.props)
            elem = render_shape(
                shape.kind,
                tprops,
                viewport_w=float(self.width),
                viewport_h=float(self.height),
            )
            if elem:
                body_parts.append(f"  {elem}")

        for name, text in labels.items():
            if name in hidden or name not in shapes:
                continue
            shape = shapes[name]
            cx, cy = shape_centre(shape.kind, shape.props)
            sx, sy = transform.world_to_screen(cx, cy)
            body_parts.append(f"  {svg_label(sx, sy, text)}")

        for name, shape in shapes.items():
            if shape.kind == "point" and name not in labels and name not in hidden:
                cx = float(shape.props.get("x", 0.0))
                cy = float(shape.props.get("y", 0.0))
                sx, sy = transform.world_to_screen(cx, cy)
                body_parts.append(
                    f"  {svg_label(sx, sy, name, offset_x=8, offset_y=-8)}"
                )

        for i, note_text in enumerate(notes):
            ny = self.padding // 2 + i * 18
            body_parts.append(svg_note(self.padding, float(ny), note_text))

        return self._wrap_svg("\n".join(body_parts))

    def _measure_annotation(
        self,
        shape: "GeoShape",
        transform: "_ViewportTransform",
    ) -> str:
        kind = shape.kind
        props = shape.props

        if kind == "segment":
            x1, y1 = transform.world_to_screen(
                float(props.get("x1", 0)), float(props.get("y1", 0))
            )
            x2, y2 = transform.world_to_screen(
                float(props.get("x2", 0)), float(props.get("y2", 0))
            )
            length = float(props.get("length", math.hypot(x2 - x1, y2 - y1)))
            return svg_measure_annotation(x1, y1, x2, y2, f"{length:.1f}")

        if kind == "circle":
            cx, cy = transform.world_to_screen(
                float(props.get("cx", 0)), float(props.get("cy", 0))
            )
            r = float(props.get("radius", 0)) * transform.scale
            return svg_measure_annotation(
                cx - r, cy, cx + r, cy, f"r={float(props.get('radius', 0)):.1f}"
            )

        return ""

    def _compute_transform(
        self,
        shapes: List[Tuple[str, "GeoShape"]],
    ) -> "_ViewportTransform":
        xs: list[float] = []
        ys: list[float] = []

        for name, shape in shapes:
            coords = _extract_world_coords(shape)
            for x, y in coords:
                xs.append(x)
                ys.append(y)

        if not xs:
            return _ViewportTransform(
                scale=1.0,
                offset_x=self.width / 2,
                offset_y=self.height / 2,
            )

        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        span_x = max(max_x - min_x, MIN_WORLD_SPAN)
        span_y = max(max_y - min_y, MIN_WORLD_SPAN)
        avail_w = self.width - 2 * self.padding
        avail_h = self.height - 2 * self.padding

        scale = min(avail_w / span_x, avail_h / span_y)

        centre_x = (min_x + max_x) / 2
        centre_y = (min_y + max_y) / 2
        offset_x = self.width / 2 - scale * centre_x
        offset_y = self.height / 2 + scale * centre_y

        return _ViewportTransform(scale=scale, offset_x=offset_x, offset_y=offset_y)

    def _wrap_svg(self, body: str) -> str:
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{self.width}" height="{self.height}" '
            f'viewBox="0 0 {self.width} {self.height}">\n'
            f'  <rect width="100%" height="100%" fill="{self.background}" />\n'
            f"{body}\n"
            f"</svg>"
        )


class _ViewportTransform:
    __slots__ = ("scale", "offset_x", "offset_y")

    def __init__(self, scale: float, offset_x: float, offset_y: float) -> None:
        self.scale = scale
        self.offset_x = offset_x
        self.offset_y = offset_y

    def world_to_screen(self, wx: float, wy: float) -> tuple[float, float]:
        sx = wx * self.scale + self.offset_x
        sy = -wy * self.scale + self.offset_y
        return sx, sy

    def scale_length(self, world_length: float) -> float:
        return world_length * self.scale

    def transform_props(self, kind: str, props: Dict[str, Any]) -> Dict[str, Any]:
        p = dict(props)

        if "x" in p and "y" in p:
            sx, sy = self.world_to_screen(float(p["x"]), float(p["y"]))
            p["x"] = sx
            p["y"] = sy

        if "cx" in p and "cy" in p:
            sx, sy = self.world_to_screen(float(p["cx"]), float(p["cy"]))
            p["cx"] = sx
            p["cy"] = sy

        for key in ("radius", "rx", "ry", "length"):
            if key in p:
                p[key] = float(p[key]) * self.scale

        i = 1
        while f"x{i}" in p:
            sx, sy = self.world_to_screen(float(p[f"x{i}"]), float(p[f"y{i}"]))
            p[f"x{i}"] = sx
            p[f"y{i}"] = sy
            i += 1

        if "ox" in p and "oy" in p:
            sx, sy = self.world_to_screen(float(p["ox"]), float(p["oy"]))
            p["ox"] = sx
            p["oy"] = sy
            p["dy"] = -float(p.get("dy", 0.0))

        if kind == "line" and "a" in p:
            a = float(props.get("a", 0.0))
            b = float(props.get("b", 1.0))
            c = float(props.get("c", 0.0))
            if abs(b) > 1e-9:
                wx1, wy1 = 0.0, -c / b
                wx2, wy2 = 1.0, -(a + c) / b
            else:
                wx1, wy1 = -c / a, 0.0
                wx2, wy2 = -(c + b) / a, 1.0
            sx1, sy1 = self.world_to_screen(wx1, wy1)
            sx2, sy2 = self.world_to_screen(wx2, wy2)
            dx, dy = sx2 - sx1, sy2 - sy1
            na, nb = -dy, dx
            nc = -(na * sx1 + nb * sy1)
            norm = math.hypot(na, nb)
            if norm > 1e-12:
                p["a"] = na / norm
                p["b"] = nb / norm
                p["c"] = nc / norm

        if "points" in p and isinstance(p["points"], list):
            p["points"] = [
                self.world_to_screen(float(x), float(y)) for x, y in p["points"]
            ]

        return p


def _extract_world_coords(shape: "GeoShape") -> list[tuple[float, float]]:
    coords: list[tuple[float, float]] = []
    p = shape.props
    _ = shape.kind

    if "x" in p and "y" in p:
        coords.append((float(p["x"]), float(p["y"])))

    if "cx" in p and "cy" in p:
        cx = float(p["cx"])
        cy = float(p["cy"])
        r = float(p.get("radius", p.get("rx", 0.0)))
        ry = float(p.get("ry", r))
        coords += [(cx - r, cy - ry), (cx + r, cy + ry)]

    i = 1
    while f"x{i}" in p:
        coords.append((float(p[f"x{i}"]), float(p[f"y{i}"])))
        i += 1

    if "ox" in p and "oy" in p:
        coords.append((float(p["ox"]), float(p["oy"])))

    if "points" in p and isinstance(p["points"], list):
        for pt in p["points"]:
            if len(pt) >= 2:
                coords.append((float(pt[0]), float(pt[1])))

    return coords


def _svg_id(name: str) -> str:
    return "".join(c if c.isalnum() or c == "_" else "_" for c in name)
