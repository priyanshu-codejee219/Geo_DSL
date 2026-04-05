import os
import sys

import pytest

# Add parent directory of current file to allow imports from that level
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lexer import Lexer, LexerError, TokenType


def lex(src: str):
    return [t for t in Lexer(src).tokenize() if t.type != TokenType.EOF]


def types(src: str):
    return [t.type for t in lex(src)]


def test_integer():
    toks = lex("42")
    assert toks[0].type == TokenType.NUMBER
    assert toks[0].value == "42"


def test_float():
    toks = lex("3.14")
    assert toks[0].type == TokenType.NUMBER
    assert toks[0].value == "3.14"


def test_string_literal():
    toks = lex('"hello world"')
    assert toks[0].type == TokenType.STRING
    assert toks[0].value == "hello world"


def test_identifier():
    toks = lex("myShape")
    assert toks[0].type == TokenType.IDENT
    assert toks[0].value == "myShape"


def test_newline_is_emitted():
    toks = lex("point A\npoint B")
    assert TokenType.NEWLINE in [t.type for t in toks]


def test_multiple_newlines():
    toks = lex("a\n\nb")
    nl_count = sum(1 for t in toks if t.type == TokenType.NEWLINE)
    assert nl_count == 2


def test_comment():
    toks = lex("# full line comment\npoint A")
    values = [t.value for t in toks if t.type not in (TokenType.NEWLINE, TokenType.EOF)]
    assert "full" not in values
    assert "comment" not in values
    assert "point" in values


def test_comment_newline_still_emitted():
    toks = lex("# comment\npoint A")
    assert TokenType.NEWLINE in [t.type for t in toks]


def test_inline_comment():
    toks = lex("point A  # this is A\npoint B")
    toks = [t for t in toks if t.type == TokenType.POINT]
    assert len(toks) == 2


def test_deg():
    toks = lex("90deg")
    assert toks[0].type == TokenType.NUMBER
    assert toks[0].value == "90"
    assert toks[1].type == TokenType.DEG


def test_deg_spaced():
    toks = lex("90 deg")
    assert toks[0].type == TokenType.NUMBER
    assert toks[1].type == TokenType.DEG


def test_deg_not_consumed():
    toks = lex("degree")
    assert len(toks) == 1
    assert toks[0].type == TokenType.IDENT
    assert toks[0].value == "degree"


def test_deg_float():
    """'45.5deg' → NUMBER('45.5') + DEG."""
    toks = lex("45.5deg")
    assert toks[0].type == TokenType.NUMBER
    assert toks[0].value == "45.5"
    assert toks[1].type == TokenType.DEG


# very stupid tests
def test_parallel_to():
    assert types("parallel_to") == [TokenType.PARALLEL_TO]


def test_perpendicular_to():
    assert types("perpendicular_to") == [TokenType.PERPENDICULAR_TO]


def test_tangent_to():
    assert types("tangent_to") == [TokenType.TANGENT_TO]


def test_passes_through():
    assert types("passes_through") == [TokenType.PASSES_THROUGH]


def test_centered_at():
    assert types("centered_at") == [TokenType.CENTERED_AT]


def test_perpendicular_bisector():
    assert types("perpendicular_bisector") == [TokenType.PERPENDICULAR_BISECTOR]


def test_angle_bisector():
    assert types("angle_bisector") == [TokenType.ANGLE_BISECTOR]


def test_convex_hull():
    assert types("convex_hull") == [TokenType.CONVEX_HULL]


def test_regular_poly():
    assert types("regular_poly") == [TokenType.REGULAR_POLY]


def test_primitive_shape_keywords():
    words = "point segment line ray circle arc triangle rectangle rhombus polygon ellipse parallelogram"
    toks = lex(words)
    for tok in toks:
        assert tok.type != TokenType.IDENT, f"{tok.value!r} should be a keyword"


def test_control_flow_keywords():
    for word in ("sweep", "speed", "if", "else", "for", "in"):
        toks = lex(word)
        assert toks[0].type != TokenType.IDENT, f"{word!r} should be a keyword"


def test_function_keywords():
    for word in ("define", "return", "call"):
        toks = lex(word)
        assert toks[0].type != TokenType.IDENT, f"{word!r} should be a keyword"


def test_transform_keywords():
    for word in ("reflect", "over", "rotate", "by", "about", "scale", "translate"):
        toks = lex(word)
        assert toks[0].type != TokenType.IDENT, f"{word!r} should be a keyword"


def test_render_keywords():
    for word in ("label", "grid"):
        toks = lex(word)
        assert toks[0].type != TokenType.IDENT, f"{word!r} should be a keyword"


def test_comparison_operators():
    cases = [
        ("=", TokenType.EQ),
        ("!=", TokenType.NEQ),
        ("<", TokenType.LT),
        (">", TokenType.GT),
        ("<=", TokenType.LTE),
        (">=", TokenType.GTE),
    ]
    for src, expected in cases:
        toks = lex(src)
        assert toks[0].type == expected, f"Failed for {src!r}"


def test_arithmetic_operators():
    cases = [
        ("+", TokenType.PLUS),
        ("-", TokenType.MINUS),
        ("*", TokenType.STAR),
        ("/", TokenType.SLASH),
    ]
    for src, expected in cases:
        assert lex(src)[0].type == expected


def test_circle_with_radius():
    assert types("circle C with radius 50") == [
        TokenType.CIRCLE,
        TokenType.IDENT,
        TokenType.WITH,
        TokenType.RADIUS,
        TokenType.NUMBER,
    ]


def test_param_range():
    assert types("param r from 10 to 100 step 5") == [
        TokenType.PARAM,
        TokenType.IDENT,
        TokenType.FROM,
        TokenType.NUMBER,
        TokenType.TO,
        TokenType.NUMBER,
        TokenType.STEP,
        TokenType.NUMBER,
    ]


def test_let_statement():
    assert types("let r = 50") == [
        TokenType.LET,
        TokenType.IDENT,
        TokenType.EQ,
        TokenType.NUMBER,
    ]


def test_reflect_statement():
    toks = lex("reflect triangle ABC over line L")
    assert toks[0].type == TokenType.REFLECT
    assert toks[1].type == TokenType.TRIANGLE
    assert toks[2].type == TokenType.IDENT
    assert toks[3].type == TokenType.OVER
    assert toks[4].type == TokenType.LINE


def test_rotate_statement():
    toks = lex("rotate P by 90deg about O")
    assert toks[0].type == TokenType.ROTATE
    assert toks[1].type == TokenType.IDENT
    assert toks[2].type == TokenType.BY
    assert toks[3].type == TokenType.NUMBER
    assert toks[4].type == TokenType.DEG
    assert toks[5].type == TokenType.ABOUT
    assert toks[6].type == TokenType.IDENT


def test_assert_statement():
    toks = lex("assert angle ABC = 90deg")
    assert toks[0].type == TokenType.ASSERT
    assert toks[1].type == TokenType.ANGLE
    assert toks[3].type == TokenType.EQ
    assert toks[4].type == TokenType.NUMBER
    assert toks[5].type == TokenType.DEG


def test_locus_block():
    src = "locus of point P:"
    toks = lex(src)
    assert toks[0].type == TokenType.LOCUS
    assert toks[1].type == TokenType.OF
    assert toks[2].type == TokenType.POINT
    assert toks[3].type == TokenType.IDENT
    assert toks[4].type == TokenType.COLON


def test_incircle_of():
    toks = lex("incircle IC of triangle ABC")
    assert toks[0].type == TokenType.INCIRCLE
    assert toks[1].type == TokenType.IDENT
    assert toks[2].type == TokenType.OF
    assert toks[3].type == TokenType.TRIANGLE


def test_for_loop():
    toks = lex("for x in [1, 2, 3]:")
    assert toks[0].type == TokenType.FOR
    assert toks[1].type == TokenType.IDENT
    assert toks[2].type == TokenType.IN
    assert toks[3].type == TokenType.LBRACKET
    assert [toks[4].type, toks[6].type, toks[8].type] == [
        TokenType.NUMBER,
        TokenType.NUMBER,
        TokenType.NUMBER,
    ]
    assert [toks[5].type, toks[7].type] == [TokenType.COMMA, TokenType.COMMA]
    assert toks[9].type == TokenType.RBRACKET
    assert toks[10].type == TokenType.COLON


def test_define_statement():
    toks = lex("define Foo(A, B){")
    assert toks[0].type == TokenType.DEFINE
    assert toks[1].type == TokenType.IDENT
    assert toks[2].type == TokenType.LPAREN
    assert toks[3].type == TokenType.IDENT
    assert toks[4].type == TokenType.COMMA
    assert toks[5].type == TokenType.IDENT
    assert toks[6].type == TokenType.RPAREN
    assert toks[7].type == TokenType.LBRACE


def test_vector_expr():
    toks = lex("translate AB by (10, 20)")
    assert toks[0].type == TokenType.TRANSLATE
    assert toks[2].type == TokenType.BY
    assert toks[3].type == TokenType.LPAREN
    assert toks[4].type == TokenType.NUMBER
    assert toks[5].type == TokenType.COMMA
    assert toks[6].type == TokenType.NUMBER
    assert toks[7].type == TokenType.RPAREN


def test_if_else_keywords():
    src = "if x > 0:\n  hide B\nelse:\n  hide A"
    t = types(src)
    assert TokenType.IF in t
    assert TokenType.ELSE in t


def test_line_numbers():
    toks = lex("point A\npoint B\npoint C")
    kw = [t for t in toks if t.type == TokenType.POINT]
    assert kw[0].line == 1
    assert kw[1].line == 2
    assert kw[2].line == 3


def test_column_numbers():
    toks = lex("circle C")
    assert toks[0].column == 1
    assert toks[1].column == 8


def test_unterminated_string():
    with pytest.raises(LexerError) as exc_info:
        lex('"not closed')
    assert exc_info.value.line == 1


def test_string_cannot_span_lines():
    with pytest.raises(LexerError):
        lex('"line one\nline two"')


def test_not_alone():
    with pytest.raises(LexerError):
        lex("!")


def test_unexpected_char():
    with pytest.raises(LexerError):
        lex("circle @ C")
