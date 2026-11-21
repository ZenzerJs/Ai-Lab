"""Tokenizer: numbers, identifiers, and operator punctuation."""
from models import LexError, Token

_OPS = "+-*/"
_PUNCT = {"(": "lparen", ")": "rparen", ";": "semi", "=": "eq"}
_IDENT_START = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ_"
_IDENT_CONT = _IDENT_START + "0123456789"


def tokenize(source):
    """Returns the token list; LexError carries the 0-based offset."""
    tokens = []
    i = 0
    while i < len(source):
        ch = source[i]
        if ch in " \t\n":
            i += 1
            continue
        if ch.isdigit():
            j = i + 1
            while j < len(source) and source[j].isdigit():
                j += 1
            tokens.append(Token("num", source[i:j], i))
            i = j
            continue
        if ch in _IDENT_START:
            j = i + 1
            while j < len(source) and source[j] in _IDENT_CONT:
                j += 1
            tokens.append(Token("name", source[i:j], i))
            i = j
            continue
        if ch in _OPS:
            tokens.append(Token("op", ch, i))
            i += 1
            continue
        if ch in _PUNCT:
            tokens.append(Token(_PUNCT[ch], ch, i))
            i += 1
            continue
        raise LexError(f"unknown character {ch!r} at {i}")
    return tokens
