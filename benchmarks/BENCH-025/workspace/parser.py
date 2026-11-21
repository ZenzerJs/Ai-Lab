"""Parser."""
from models import Assign, Binary, Literal, Name, ParseError, Unary


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
        if tok is not None and tok.kind == kind:
            return self.advance()
        raise ParseError("unexpected token")

    def parse_program(self):
        stmts = [self.parse_statement()]
        while self.peek() is not None and self.peek().kind == "semi":
            self.advance()
            stmts.append(self.parse_statement())
        return stmts

    def parse_statement(self):
        tok = self.peek()
        if tok is not None and tok.kind == "name":
            nxt = self.tokens[self.i + 1] if self.i + 1 < len(
                self.tokens) else None
            if nxt is not None and nxt.kind == "eq":
                self.advance()
                self.advance()
                return Assign(tok.text, self.parse_expr())
        return self.parse_expr()

    def parse_expr(self):
        node = self.parse_atom()
        while self.peek() is not None and self.peek().kind == "op":
            op = self.advance().text
            node = Binary(op, node, self.parse_atom())
        return node

    def parse_atom(self):
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end of input")
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
        if tok.kind == "op":
            self.advance()
            return Unary(tok.text, self.parse_atom())
        raise ParseError("unexpected token")
