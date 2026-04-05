from enum import Enum, auto


class TokenType(Enum):
    # Literals & Identifiers
    IDENT = auto()
    NUMBER = auto()
    STRING = auto()
    NEWLINE = auto()
    EOF = auto()

    # Primitive Shape Keywords
    POINT = auto()
    SEGMENT = auto()
    LINE = auto()
    RAY = auto()
    CIRCLE = auto()
    ARC = auto()
    TRIANGLE = auto()
    RECTANGLE = auto()
    RHOMBUS = auto()
    REGULAR_POLY = auto()
    POLYGON = auto()
    ELLIPSE = auto()
    PARALLELOGRAM = auto()

    # Relational Constraint Keywords
    AT = auto()
    ON = auto()
    OF = auto()
    WITH = auto()
    PARALLEL_TO = auto()
    PERPENDICULAR_TO = auto()
    TANGENT_TO = auto()
    BISECTS = auto()
    PASSES_THROUGH = auto()
    CENTERED_AT = auto()

    # Measurement Keywords
    DISTANCE = auto()
    ANGLE = auto()
    LENGTH = auto()
    RADIUS = auto()
    RATIO = auto()
    AREA = auto()
    PERIMETER = auto()
    SIDES = auto()

    # Variable & Parameter Keywords
    LET = auto()
    SET = auto()
    PARAM = auto()
    FROM = auto()
    TO = auto()
    STEP = auto()

    # Control Flow Keywords
    SWEEP = auto()
    SPEED = auto()
    IF = auto()
    ELSE = auto()
    FOR = auto()
    IN = auto()

    # Function Keywords
    DEFINE = auto()
    RETURN = auto()
    CALL = auto()

    # Derived Construction Keywords
    MIDPOINT = auto()
    INTERSECTION = auto()
    PERPENDICULAR_BISECTOR = auto()
    ANGLE_BISECTOR = auto()
    CIRCUMCIRCLE = auto()
    INCIRCLE = auto()
    CONVEX_HULL = auto()
    LOCUS = auto()

    # Transformation Keywords
    REFLECT = auto()
    OVER = auto()
    ROTATE = auto()
    BY = auto()
    ABOUT = auto()
    SCALE = auto()
    TRANSLATE = auto()

    # Assertion Keywords
    ASSERT = auto()
    VERIFY = auto()

    # Rendering & Display Keywords
    LABEL = auto()
    NOTE = auto()
    SHOW = auto()
    HIDE = auto()
    DRAW = auto()
    GRID = auto()
    ANIMATE = auto()
    MEASURE = auto()

    # Unit Suffix
    DEG = auto()

    # Operators
    PLUS = auto()
    MINUS = auto()
    STAR = auto()
    SLASH = auto()

    # Comparison Operators
    EQ = auto()
    NEQ = auto()
    LT = auto()
    GT = auto()
    LTE = auto()
    GTE = auto()

    # Punctuation
    COLON = auto()
    COMMA = auto()
    LPAREN = auto()
    RPAREN = auto()
    LBRACE = auto()
    RBRACE = auto()
    LBRACKET = auto()
    RBRACKET = auto()


# Keyword lookup table
# stores in a dictionary string → TokenType

KEYWORDS: dict[str, TokenType] = {
    "point": TokenType.POINT,
    "segment": TokenType.SEGMENT,
    "line": TokenType.LINE,
    "ray": TokenType.RAY,
    "circle": TokenType.CIRCLE,
    "arc": TokenType.ARC,
    "triangle": TokenType.TRIANGLE,
    "rectangle": TokenType.RECTANGLE,
    "rhombus": TokenType.RHOMBUS,
    "regular_poly": TokenType.REGULAR_POLY,
    "polygon": TokenType.POLYGON,
    "ellipse": TokenType.ELLIPSE,
    "parallelogram": TokenType.PARALLELOGRAM,
    "at": TokenType.AT,
    "on": TokenType.ON,
    "of": TokenType.OF,
    "with": TokenType.WITH,
    "parallel_to": TokenType.PARALLEL_TO,
    "perpendicular_to": TokenType.PERPENDICULAR_TO,
    "tangent_to": TokenType.TANGENT_TO,
    "bisects": TokenType.BISECTS,
    "passes_through": TokenType.PASSES_THROUGH,
    "centered_at": TokenType.CENTERED_AT,
    "distance": TokenType.DISTANCE,
    "angle": TokenType.ANGLE,
    "length": TokenType.LENGTH,
    "radius": TokenType.RADIUS,
    "ratio": TokenType.RATIO,
    "area": TokenType.AREA,
    "perimeter": TokenType.PERIMETER,
    "sides": TokenType.SIDES,
    "let": TokenType.LET,
    "set": TokenType.SET,
    "param": TokenType.PARAM,
    "from": TokenType.FROM,
    "to": TokenType.TO,
    "step": TokenType.STEP,
    "sweep": TokenType.SWEEP,
    "speed": TokenType.SPEED,
    "if": TokenType.IF,
    "else": TokenType.ELSE,
    "for": TokenType.FOR,
    "in": TokenType.IN,
    "define": TokenType.DEFINE,
    "return": TokenType.RETURN,
    "call": TokenType.CALL,
    "midpoint": TokenType.MIDPOINT,
    "intersection": TokenType.INTERSECTION,
    "perpendicular_bisector": TokenType.PERPENDICULAR_BISECTOR,
    "angle_bisector": TokenType.ANGLE_BISECTOR,
    "circumcircle": TokenType.CIRCUMCIRCLE,
    "incircle": TokenType.INCIRCLE,
    "convex_hull": TokenType.CONVEX_HULL,
    "locus": TokenType.LOCUS,
    "reflect": TokenType.REFLECT,
    "over": TokenType.OVER,
    "rotate": TokenType.ROTATE,
    "by": TokenType.BY,
    "about": TokenType.ABOUT,
    "scale": TokenType.SCALE,
    "translate": TokenType.TRANSLATE,
    "assert": TokenType.ASSERT,
    "verify": TokenType.VERIFY,
    "label": TokenType.LABEL,
    "note": TokenType.NOTE,
    "show": TokenType.SHOW,
    "hide": TokenType.HIDE,
    "draw": TokenType.DRAW,
    "grid": TokenType.GRID,
    "animate": TokenType.ANIMATE,
    "measure": TokenType.MEASURE,
    "deg": TokenType.DEG,
}
