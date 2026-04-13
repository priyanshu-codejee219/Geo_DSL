# Geo_DSL

## Motivation

Geo_DSL is a domain-specific language for building and rendering 2D Euclidean geometry scenes with constraints, animation, and loci. It is designed to help visual learners in mathematics and geometry, as well as teachers, explain geometric motion and locus behavior using a readable script format.

## Target Users

- Visual learners in mathematics and geometry
- Teachers who want to demonstrate geometric constructions and motion
- Students exploring constraint-based geometry and locus visualization
- Developers and researchers building geometry education tools

## DSL Description

Geo_DSL uses simple English-like keywords and expressions to define points, lines, rays, segments, circles, loci, parameters, and animated sweeps.


---

## Supported Keywords

### Shapes
- `point`, `segment`, `line`, `ray`
- `circle`, `arc`, `triangle`
- `rectangle`, `rhombus`, `polygon`
- `regular_poly`, `ellipse`, `parallelogram`

---

### Constraints
- `at`
- `on`
- `passes_through`
- `centered_at`
- `parallel_to`
- `perpendicular_to`
- `tangent_to`
- `bisects`

---

### Variables & Parameters
- `let`
- `set`
- `param`
- `from`, `to`, `step`

---

### Control & Animation
- `sweep`
- `if`, `else`
- `for`, `in`

---

### Derived Constructions
- `midpoint`
- `intersection`
- `perpendicular_bisector`
- `angle_bisector`
- `circumcircle`
- `incircle`
- `convex_hull`
- `locus`

---

### Transformations
- `translate`
- `rotate`
- `scale`
- `reflect`

---

### Rendering
- `label`
- `note`
- `hide`
- `grid`


---

### Assertions
- `assert`

### Expression support

Geo_DSL expressions support numeric arithmetic, trigonometry, and references to parameters and variables. Example operators include `+`, `-`, `*`, `/` and math functions such as `sin(...)` and `cos(...)`.
For detailed description use Guides added in the Repo

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

```

### Expected output

- A wall and ground ray setup.
- A stick segment `XY` sliding from the wall to the ground.
- The midpoint `MP` tracked as the stick moves.
- The locus of the midpoint emerging as a curved path, making the geometric motion easy to understand.

### Actual visual output

Rendering `Examples/sample6.geo` produces an animated SVG with the following visual result(Click to view animated output):

![My Animation](Examples/sample6.svg)

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

### Rhea - 40%
- Lexer: `lexer.py`
- Parser: `parser_utils.py`, `parser.py`
- Solver: `numeric.py`, `solver.py`
- Renderer: `svg_backend.py`, `renderer.py`
- Testing: `test_parser.py`, `test_renderer.py`
- Linting
- README.md
- User Survey

### Priyanshu - 40%
- Lexer: `token_types.py`
- AST Nodes: `ast_nodes.py`
- Parser: `parser.py`
- Solver: `algebraic.py`
- Evaluator: `evaluator.py`
- Renderer: `svg_backend.py`
- Testing: `test_evaluator.py`, `test_lexer.py`, `test_solver.py`

### Ankit - 10%
- Interpreter: `errors.py`, `interpreter.py`
- Testing: `test_interpreter.py`

### Shashank - 10%
- Semantics: `analyser.py`
- Interpreter: `environment.py`
- Testing: `test_analyser.py`

---

> Work distribution is also documented in the project git commit history.
## User Survey Questions
https://docs.google.com/forms/d/e/1FAIpQLSdf-SLnCI8q26a0v1o54XckIPej9POtIpeAE9iIeP1VhaXIww/viewform?usp=publish-editor

- How difficult was it to learn Geo_DSL syntax? (1 = very easy, 5 = very difficult)
- How does Geo_DSL compare to other tools you have used for 2D constructions in the past?
- What is the most useful feature of the language according to you?
- What was the most confusing feature of the DSL?
- Are there any suggestions you would want us to implement in Geo_DSL?
- Which parts of the language did you actually try?
- How natural did describing geometry by constraints feel compared to writing coordinates directly? (1–5)
- Overall satisfaction with GeoScript

---

## User Survey Summary

### Syntax and Grammar
- Easy to learn and understand  
- Flows naturally, similar to English  

### Final Rendered Output
- Good Overall response with some improvements suggested and implemented
  
### Implemented Changes
- Improved SVG output (coloring, grid)  
  - Easy to implement  
  - Significantly improves visualization for learners  

- Fixed area constraint for basic shapes  
  - Resolved a major bug  

### Suggestions Not Implemented
- Scrolling in output (up/down)  
  - Not necessary for the intended visualization use case  

## Notes

The DSL is especially well-suited for classroom demonstrations, homework examples, and interactive geometry explanations. `Examples/sample6.geo` is the recommended sample for visualizing a sliding stick and the midpoint locus.
