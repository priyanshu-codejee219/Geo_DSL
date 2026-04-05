from __future__ import annotations

from typing import List

from lexer import Token
from lexer.token_types import TokenType


class ParseError(Exception):
    def __init__(self, message: str, token: Token) -> None:
        super().__init__(
            f"[Parser] Line {token.line}, Col {token.column}: {message} "
            f"(got {token.type.name} {token.value!r})"
        )
        self.token = token


def peek(tokens: List[Token], pos: int, offset: int = 0) -> Token:
    idx = pos + offset
    return tokens[idx] if idx < len(tokens) else tokens[-1]


def advance(tokens: List[Token], pos: int) -> tuple[Token, int]:
    tok = tokens[pos]
    new_pos = pos + 1
    while new_pos < len(tokens) and tokens[new_pos].type == TokenType.NEWLINE:
        new_pos += 1
    return tok, new_pos


def expect(tokens: List[Token], pos: int, *types: TokenType) -> tuple[Token, int]:
    tok = tokens[pos]
    if tok.type not in types:
        expected_names = " or ".join(t.name for t in types)
        raise ParseError(f"Expected {expected_names}", tok)
    return advance(tokens, pos)
