from __future__ import annotations

from typing import List

from lexer import Token, TokenType


class Parser:
    def __init__(self, tokens: List[Token]) -> None:
        self._tokens: List[Token] = tokens
        self._pos: int = 0
        self._skip_newlines()

    # Helper Functions

    def _skip_newlines(self) -> None:
        while (
            self._pos < len(self._tokens)
            and self._tokens[self._pos].type == TokenType.NEWLINE
        ):
            self._pos += 1

    def _cur(self) -> Token:
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return self._tokens[-1]
