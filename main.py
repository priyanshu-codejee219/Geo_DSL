from __future__ import annotations

import argparse
import os
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional

from evaluator.evaluator import Evaluator
from interpreter.errors import (
    GeoAssertionError,
    GeoConstraintError,
    GeoScriptError,
)
from interpreter.interpreter import Interpreter
from lexer.lexer import Lexer, LexerError
from lexer.token_types import TokenType
from parser.parser import parse
from parser.parser_utils import ParseError
from renderer.renderer import Renderer
from solver.solver import GeoSolver

try:
    from semantics.analyser import SemanticAnalyser

    _HAS_ANALYSER = True
except ImportError:
    _HAS_ANALYSER = False


def _supports_colour() -> bool:
    return sys.stdout.isatty() and os.name != "nt"


if _supports_colour():
    _RED = "\033[91m"
    _YELLOW = "\033[93m"
    _GREEN = "\033[92m"
    _CYAN = "\033[96m"
    _BOLD = "\033[1m"
    _RESET = "\033[0m"
else:
    _RED = _YELLOW = _GREEN = _CYAN = _BOLD = _RESET = ""


def _err(msg: str) -> None:
    print(f"{_RED}{_BOLD}Error:{_RESET} {msg}", file=sys.stderr)


def _warn(msg: str) -> None:
    print(f"{_YELLOW}Warning:{_RESET} {msg}", file=sys.stderr)


def _ok(msg: str) -> None:
    print(f"{_GREEN}✓{_RESET} {msg}")


def _info(msg: str) -> None:
    print(f"{_CYAN}{msg}{_RESET}")


def _read_source(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        _err(f"File not found: {path}")
        sys.exit(1)
    except OSError as e:
        _err(f"Cannot read {path}: {e}")
        sys.exit(1)


def _lex(source: str, path: str):
    try:
        return Lexer(source).tokenize()
    except LexerError as e:
        _err(f"{path}: {e}")
        sys.exit(1)


def _parse(tokens, path: str):
    try:
        return parse(tokens)
    except ParseError as e:
        _err(f"{path}: {e}")
        sys.exit(1)


def _analyse(program, path: str) -> None:
    if not _HAS_ANALYSER:
        return
    try:
        analyser = SemanticAnalyser()
        analyser.analyse(program)
    except GeoScriptError as e:
        _err(f"{path}: {e}")
        sys.exit(1)
    except Exception as e:
        _warn(f"Semantic analysis incomplete: {e}")


def _interpret(program, path: str) -> Interpreter:
    solver = GeoSolver()

    def _factory():
        return Interpreter(geometry_backend=GeoSolver())

    ev = Evaluator(_factory)

    solver.program = program
    solver.evaluator = ev

    interp = Interpreter(geometry_backend=solver)
    try:
        interp.run(program)
    except GeoAssertionError as e:
        _err(f"{path}: {e}")
        sys.exit(1)
    except GeoConstraintError as e:
        _err(f"{path}: {e}")
        sys.exit(1)
    except GeoScriptError as e:
        _err(f"{path}: {e}")
        sys.exit(1)
    return interp


def _resolve_loci(interp: Interpreter, program) -> None:
    locus_shapes = {
        name: shape
        for name, shape in interp.shapes.items()
        if shape.kind == "locus"
        and shape.props.get("locus_var") is not None
        and shape.props.get("locus_constraint") is not None
    }

    if not locus_shapes:
        return

    def _factory():
        return Interpreter(geometry_backend=GeoSolver())

    ev = Evaluator(_factory)

    try:
        locus_range = float(interp.env.get("__locus_range"))
    except Exception:
        locus_range = 200.0

    try:
        locus_step = float(interp.env.get("__locus_step"))
    except Exception:
        locus_step = 1.0

    for name, shape in locus_shapes.items():
        locus_var = shape.props["locus_var"]
        locus_constraint = shape.props["locus_constraint"]

        result = ev.run_locus(
            program=program,
            locus_var=locus_var,
            constraint=locus_constraint,
            x_range=(-locus_range, locus_range, locus_step),
            y_range=(-locus_range, locus_range, locus_step),
            shape_name=name,
        )

        shape.props["points"] = result.points
        if result.points:
            _info(f"Locus '{name}': {len(result.points)} points sampled")
        else:
            _warn(
                f"Locus '{name}': no points found — check constraint or increase range"
            )


def _has_sweep(program) -> bool:
    from ast_nodes.nodes import SweepStmt

    for stmt in program.statements:
        if isinstance(stmt, SweepStmt):
            return True
    return False


def _render(interp: Interpreter, renderer: Renderer) -> str:
    return renderer.render(interp)


def _render_animated(
    program,
    param_name: str,
    path: str,
    renderer: Renderer,
) -> str:

    def _factory():
        return Interpreter(geometry_backend=GeoSolver())

    ev = Evaluator(_factory)

    try:
        frames = ev.run_sweep(program, param_name)
    except ValueError as e:
        _err(f"{path}: {e}")
        sys.exit(1)
    except GeoScriptError as e:
        _err(f"{path}: {e}")
        sys.exit(1)

    if not frames:
        _warn("Sweep produced no frames — check param range and step.")
        return renderer.render_static({})

    _info(f"Rendered {len(frames)} sweep frames for param '{param_name}'")
    return renderer.render_animated_svg(frames)


def _write_output(svg: str, out_path: str) -> None:
    try:
        Path(out_path).write_text(svg, encoding="utf-8")
    except OSError as e:
        _err(f"Cannot write {out_path}: {e}")
        sys.exit(1)


def _open_in_browser(svg: str) -> None:
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GeoScript Output</title>
  <style>
    body {{
      margin: 0;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
      background: #f1f5f9;
      font-family: Inter, Segoe UI, sans-serif;
    }}
    .card {{
      background: white;
      border-radius: 12px;
      box-shadow: 0 4px 24px rgba(0,0,0,0.10);
      padding: 24px;
    }}
    h1 {{
      color: #1e293b;
      font-size: 14px;
      font-weight: 500;
      margin: 0 0 12px 0;
      letter-spacing: 0.05em;
      text-transform: uppercase;
    }}
  </style>
</head>
<body>
  <div class="card">
    <h1>GeoScript</h1>
    {svg}
  </div>
</body>
</html>"""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as f:
        f.write(html)
        tmp_path = f.name

    webbrowser.open(f"file://{tmp_path}")
    _info(f"Opened in browser: {tmp_path}")


def _print_tokens(tokens) -> None:
    _info("\n── Token stream ──────────────────────────────")
    for tok in tokens:
        if tok.type != TokenType.EOF:
            print(f"  {tok.line:3}:{tok.column:<3}  {tok.type.name:<25}  {tok.value!r}")
    print()


def _print_ast(program) -> None:
    _info("\n── AST ───────────────────────────────────────")
    for i, stmt in enumerate(program.statements):
        print(f"  [{i:02d}] {stmt}")
    print()


def _print_shapes(interp: Interpreter) -> None:
    _info("\n── Resolved shapes ───────────────────────────")
    if not interp.shapes:
        print("  (none)")
    for name, shape in interp.shapes.items():
        hidden_tag = " [hidden]" if name in interp.hidden else ""
        label_tag = f' label="{interp.labels[name]}"' if name in interp.labels else ""
        print(f"  {name}: {shape.kind}{hidden_tag}{label_tag}")
        for k, v in shape.props.items():
            if isinstance(v, float):
                print(f"      {k} = {v:.4f}")
            elif not callable(v) and k != "points":
                print(f"      {k} = {v!r}")
            elif k == "points":
                print(f"      {k} = [{len(v)} points]")
    if interp.assertions_failed:
        _warn(f"  {len(interp.assertions_failed)} assertion(s) failed:")
        for desc in interp.assertions_failed:
            print(f"      FAILED: {desc}")
    elif interp.assertions_passed:
        _ok(f"  {interp.assertions_passed} assertion(s) passed")
    print()


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="geoscript",
        description="GeoScript DSL — constraint-based 2D geometry renderer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py triangle.geo
  python main.py sweep_demo.geo --param t --open
  python main.py program.geo -o result.svg
  python main.py program.geo --check
  python main.py program.geo --tokens
        """,
    )
    p.add_argument("source", help="Path to the .geo source file")
    p.add_argument(
        "-o",
        "--output",
        metavar="FILE",
        help="Write SVG output to FILE (default: <source>.svg)",
    )
    p.add_argument(
        "--open",
        action="store_true",
        help="Open the rendered output in the default web browser",
    )
    p.add_argument(
        "--param",
        metavar="NAME",
        help="Parameter name to animate (auto-detected if omitted)",
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="Run the full pipeline but do not write or open output",
    )
    p.add_argument(
        "--tokens", action="store_true", help="Print the token stream and exit"
    )
    p.add_argument("--ast", action="store_true", help="Print the AST and exit")
    p.add_argument(
        "--shapes",
        action="store_true",
        help="Print resolved shape properties after interpretation",
    )
    p.add_argument(
        "--no-analyse",
        action="store_true",
        help="Skip semantic analysis (useful during development)",
    )
    p.add_argument(
        "--width",
        type=int,
        default=800,
        metavar="PX",
        help="SVG canvas width in pixels (default: 800)",
    )
    p.add_argument(
        "--height",
        type=int,
        default=600,
        metavar="PX",
        help="SVG canvas height in pixels (default: 600)",
    )
    return p


def main(argv: Optional[list[str]] = None) -> int:

    parser = _build_arg_parser()
    args = parser.parse_args(argv)

    source_path = args.source

    source = _read_source(source_path)

    tokens = _lex(source, source_path)
    if args.tokens:
        _print_tokens(tokens)
        return 0

    program = _parse(tokens, source_path)
    if args.ast:
        _print_ast(program)
        return 0

    if not args.no_analyse:
        _analyse(program, source_path)

    interp = _interpret(program, source_path)

    if args.shapes:
        _print_shapes(interp)

    if args.check:
        _ok(f"No errors found in {source_path}")
        if interp.assertions_passed:
            _ok(f"{interp.assertions_passed} assertion(s) passed")
        return 0

    renderer = Renderer(
        width=args.width,
        height=args.height,
        background="#000000",
        curve_color="#916df7",
        locus_color="#3bf69a",
        grid_color="#ffffff",
    )

    param_name = args.param or _detect_param(program)
    is_animated = _has_sweep(program) or (args.param is not None)

    if is_animated and param_name:
        svg = _render_animated(program, param_name, source_path, renderer)
    else:
        svg = _render(interp, renderer)

    if args.open and not args.output:
        _open_in_browser(svg)
    else:
        out_path = args.output or str(Path(source_path).with_suffix(".svg"))
        _write_output(svg, out_path)
        _ok(f"Rendered to {out_path}")
        if args.open:
            _open_in_browser(Path(out_path).read_text(encoding="utf-8"))

    return 0


def _detect_param(program) -> Optional[str]:
    from ast_nodes.nodes import ParamStmt

    for stmt in program.statements:
        if isinstance(stmt, ParamStmt):
            return stmt.name
    return None


if __name__ == "__main__":
    sys.exit(main())
