# Geo_DSL

## Overview

Geo_DSL is a domain-specific language for building and rendering 2D Euclidean geometry scenes with constraints, animation, and loci. It is designed to help visual learners in mathematics and geometry, as well as teachers, explain geometric motion and locus behavior using a readable script format.

## Target Users

- Visual learners in mathematics and geometry
- Teachers who want to demonstrate geometric constructions and motion
- Students exploring constraint-based geometry and locus visualization
- Developers and researchers building geometry education tools

## DSL Description

Geo_DSL uses simple English-like keywords and expressions to define points, lines, rays, segments, circles, loci, parameters, and animated sweeps.

### Core concepts

- `point <Name> at (<x>,<y>)`
- `segment <Name> of <P1> <P2>`
- `line <Name> of <P1> <P2>`
- `ray <Name> of <P1> <P2>`
- `midpoint <Name> of <AB> `
- `param <name> from <start> to <end> step <delta>`
- `sweep <parameter>`
- `label <Shape> "Text"`
- `let <name> = <expression>`

### Supported keywords

Geo_DSL supports geometric construction, constraint, and rendering keywords such as:

- Shapes: `point`, `segment`, `line`, `ray`, `circle`, `arc`, `triangle`, `rectangle`, `rhombus`, `regular_poly`, `polygon`, `ellipse`, `parallelogram`
- Derived constructions: `midpoint`, `intersection`, `perpendicular_bisector`, `angle_bisector`, `circumcircle`, `incircle`, `convex_hull`, `locus`
- Control and animation: `param`, `from`, `to`, `step`, `sweep`, `speed`, `if`, `else`, `for`, `in`
- Rendering: `label`, `note`, `show`, `hide`, `draw`, `grid`, `animate`, `measure`
- Assertions: `assert`, `verify`

### Expression support

Geo_DSL expressions support numeric arithmetic, trigonometry, and references to parameters and variables. Example operators include `+`, `-`, `*`, `/` and math functions such as `sin(...)` and `cos(...)`.

## Sample Program

The sample program below is `Examples/sample6.geo`. It visualizes a math problem where a stick slides down a wall and the locus of the midpoint of the stick is traced.

```geo
point O at (0,0)
point A at (0,100)
point B at (100,0)

ray Wall of O A
ray Ground of O B

let l = 100

param theta from 89 to 0 step -1
point X at (0,l*sin(theta*3.14/180))
point Y at (l*cos(theta*3.14/180),0)
segment XY of X Y
midpoint MP of XY
sweep theta

label A "Wall"
label B "Ground"
```

### Expected output

- A wall and ground ray setup.
- A stick segment `XY` sliding from the wall to the ground.
- The midpoint `MP` tracked as the stick moves.
- The locus of the midpoint emerging as a curved path, making the geometric motion easy to understand.

### Actual visual output

Rendering `Examples/sample6.geo` produces an animated SVG with the following visual result:

- Canvas size: `800x600` with a dark background.
- A vertical wall ray drawn on the left side and a horizontal ground ray at the bottom.
- The stick segment `XY` animates as it slides down from the wall to the ground over 90 frames.
- The midpoint `MP` is rendered as a small blue point with a purple outline, moving along the path defined by the stick.
- Point `O` remains fixed at the wall-ground intersection, while labeled points `A` and `B` mark the wall and ground anchors.
- The animation output is written to `sample6.svg` when using the `-o sample6.svg` command.

## How to Build and Run

### Requirements

- Python 3.9 or newer
- `numpy`
- `pytest`
- `ruff`

Install dependencies:

```bash
python -m pip install -r requirements.txt
```

### Run a Geo_DSL program

Render the sample file to SVG:

```bash
python main.py Examples/sample6.geo -o sample6.svg
```

Render and open in the browser:

```bash
python main.py Examples/sample6.geo --open
```

Check the program without writing output:

```bash
python main.py Examples/sample6.geo --check
```

Print tokens or AST for debugging:

```bash
python main.py Examples/sample6.geo --tokens
python main.py Examples/sample6.geo --ast
```

## Tests and Linting

Run unit tests with:

```bash
pytest
```

Run linting with Ruff:

```bash
python -m ruff check .
```

## Member Contributions


> Work distribution is also documented in the project git commit history.

## User Survey Summary


## Notes

The DSL is especially well-suited for classroom demonstrations, homework examples, and interactive geometry explanations. `Examples/sample6.geo` is the recommended sample for visualizing a sliding stick and the midpoint locus.
