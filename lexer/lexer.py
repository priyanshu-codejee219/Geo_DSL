from __future__ import annotations

from dataclasses import dataclass
from typing import List

from .token_types import KEYWORDS, TokenType


@dataclass(frozen=True)
class Token:
    type: TokenType
    value: str
    line: int
    column: int

    def __repr__(self) -> str:
        return f"Token({self.type.name}, {self.value!r}, {self.line}:{self.column})"


class LexerError(Exception):
    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(f"[Lexer] Line {line}, Col {column}: {message}")
        self.line = line
        self.column = column


class Lexer:
    def __init__(self, source: str) -> None:
        self._src: str = source
        self._pos: int = 0  # index of next character to read
        self._line: int = 1  # current 1-based line number
        self._col: int = 1  # current 1-based column number
        self._tokens: List[Token] = []

    def tokenize(self) -> List[Token]:

        while not self._at_end():
            self._scan_token()

        self._tokens.append(Token(TokenType.EOF, "", self._line, self._col))
        return self._tokens

    def _at_end(self) -> bool:
        return self._pos >= len(self._src)

    def _peek(self, offset: int = 0) -> str:

        idx = self._pos + offset
        return self._src[idx] if idx < len(self._src) else ""

    def _advance(self) -> str:

        ch = self._src[self._pos]
        self._pos += 1
        if ch == "\n":
            self._line += 1
            self._col = 1
        else:
            self._col += 1
        return ch

    def _match(self, expected: str) -> bool:

        if self._at_end() or self._src[self._pos] != expected:
            return False
        self._advance()
        return True

    def _add(self, ttype: TokenType, value: str, line: int, col: int) -> None:

        self._tokens.append(Token(ttype, value, line, col))

    def _scan_token(self) -> None:

        start_line = self._line
        start_col = self._col
        ch = self._advance()

        if ch in (" ", "\t", "\r"):  # our language wil ignore these white spaces
            return

        if ch == "\n":
            self._add(TokenType.NEWLINE, "\\n", start_line, start_col)
            return

        if ch == "#":  # comments
            while not self._at_end() and self._peek() != "\n":
                self._advance()

            return

        if ch == '"':
            self._scan_string(start_line, start_col)
            return

        if ch.isdigit():
            self._scan_number(ch, start_line, start_col)
            return

        if ch.isalpha() or ch == "_":
            self._scan_word(ch, start_line, start_col)
            return

        if ch == "!":
            if self._match("="):
                self._add(TokenType.NEQ, "!=", start_line, start_col)
            else:
                raise LexerError(
                    "Unexpected '!' — did you mean '!='?", start_line, start_col
                )
            return

        if ch == "<":
            if self._match("="):
                self._add(TokenType.LTE, "<=", start_line, start_col)
            else:
                self._add(TokenType.LT, "<", start_line, start_col)
            return

        if ch == ">":
            if self._match("="):
                self._add(TokenType.GTE, ">=", start_line, start_col)
            else:
                self._add(TokenType.GT, ">", start_line, start_col)
            return

        _SIMPLE: dict[str, TokenType] = {
            "+": TokenType.PLUS,
            "-": TokenType.MINUS,
            "*": TokenType.STAR,
            "/": TokenType.SLASH,
            "=": TokenType.EQ,
            ":": TokenType.COLON,
            ",": TokenType.COMMA,
            "(": TokenType.LPAREN,
            ")": TokenType.RPAREN,
            "{": TokenType.LBRACE,
            "}": TokenType.RBRACE,
            "[": TokenType.LBRACKET,
            "]": TokenType.RBRACKET,
        }
        if ch in _SIMPLE:
            self._add(_SIMPLE[ch], ch, start_line, start_col)
            return

        raise LexerError(f"Unexpected character {ch!r}", start_line, start_col)

    def _scan_string(self, start_line: int, start_col: int) -> None:

        buf: List[str] = []
        while not self._at_end():
            ch = self._peek()
            if ch == '"':
                self._advance()
                self._add(TokenType.STRING, "".join(buf), start_line, start_col)
                return
            if ch == "\n":
                raise LexerError(
                    "Unterminated string literal — closing '\"' missing",
                    start_line,
                    start_col,
                )
            buf.append(self._advance())

        raise LexerError(
            "Unterminated string literal — reached end of file", start_line, start_col
        )

    def _scan_number(self, first_digit: str, start_line: int, start_col: int) -> None:

        buf: List[str] = [first_digit]

        # Integer part
        while not self._at_end() and self._peek().isdigit():
            buf.append(self._advance())

        if self._peek() == "." and self._peek(1).isdigit():
            buf.append(self._advance())
            while not self._at_end() and self._peek().isdigit():
                buf.append(self._advance())

        self._add(TokenType.NUMBER, "".join(buf), start_line, start_col)

        if self._peek(0) == "d" and self._peek(1) == "e" and self._peek(2) == "g":
            next_after_deg = self._peek(3)
            if not (next_after_deg.isalnum() or next_after_deg == "_"):
                deg_col = self._col
                self._advance()  # d
                self._advance()  # e
                self._advance()  # g
                self._add(TokenType.DEG, "deg", self._line, deg_col)

    def _scan_word(self, first_char: str, start_line: int, start_col: int) -> None:

        buf: List[str] = [first_char]
        while not self._at_end():
            ch = self._peek()
            if ch.isalnum() or ch == "_":
                buf.append(self._advance())
            else:
                break

        word = "".join(buf)
        ttype = KEYWORDS.get(
            word, TokenType.IDENT
        )  # if the key for qord exists, then return that, else it is ident.
        self._add(ttype, word, start_line, start_col)
