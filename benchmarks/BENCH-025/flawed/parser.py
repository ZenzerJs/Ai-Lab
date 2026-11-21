"""Recursive-descent parser: strict precedence and EOF checks.

program  := stmt (';' stmt)* ';'?
stmt     := name '=' expr | expr
expr     := term (('+'|'-') term)*
term     := factor (('*'|'/') factor)*
factor   := ('-'|'+') factor | atom
atom     := num | name | '(' expr ')'
"""
from models import (Assign, Binary, Literal, Name, ParseError, Unary)


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.i = 0

    def peek(self):
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def advance(self):
        tok = self.peek()
        self.i += 1
        return tok

    def expect(self, kind):
        tok = self.peek()
        if tok is None:
            raise ParseError(f"expected {kind}, got end of input")
        if tok.kind != kind:
            raise ParseError(
                f"expected {kind}, got {tok.kind!r} at {tok.pos}")
        return self.advance()

    def parse_program(self):
        stmts = [self.parse_statement()]
        while self.peek() is not None and self.peek().kind == "semi":
            self.advance()
            if self.peek() is None:
                break
            stmts.append(self.parse_statement())
        if self.peek() is not None:
            raise ParseError(
                f"unexpected {self.peek().text!r} at {self.peek().pos}")
        return stmts

    def parse_statement(self):
        tok = self.peek()
        if tok is not None and tok.kind == "name":
            nxt = self.tokens[self.i + 1] if self.i + 1 < len(
                self.tokens) else None
            if nxt is not None and nxt.kind == "eq":
                self.advance()   # name
                self.advance()   # '='
                return Assign(tok.text, self.parse_expr())
        return self.parse_expr()

    def parse_expr(self):
        node = self.parse_term()
        while self.peek() is not None and self.peek().kind == "op" \
                and self.peek().text in "+-":
            op = self.advance().text
            node = Binary(op, node, self.parse_term())
        return node

    def parse_term(self):
        node = self.parse_factor()
        while self.peek() is not None and self.peek().kind == "op" \
                and self.peek().text in "*/":
            op = self.advance().text
            node = Binary(op, node, self.parse_factor())
        return node

    def parse_factor(self):
        tok = self.peek()
        if tok is not None and tok.kind == "op" and tok.text in "-+":
            op = self.advance().text
            return Unary(op, self.parse_factor())
        return self.parse_atom()

    def parse_atom(self):
        tok = self.peek()
        if tok is None:
            raise ParseError("expected expression, got end of input")
        if tok.kind == "num":
            self.advance()
            return Literal(int(tok.text))
        if tok.kind == "name":
            self.advance()
            return Name(tok.text)
        if tok.kind == "lparen":
            self.advance()
            node = self.parse_expr()
            self.expect("rparen")
            return node
        raise ParseError(f"unexpected {tok.text!r} at {tok.pos}")
