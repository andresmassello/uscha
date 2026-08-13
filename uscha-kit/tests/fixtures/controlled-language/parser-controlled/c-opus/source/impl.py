"""Integer arithmetic expression evaluator.

Reads one expression from stdin, prints its integer value, or ERROR.
Always exits 0.

Grammar (recursive descent, left-associative binaries):
    expr   := term (('+' | '-') term)*
    term   := unary (('*' | '/') unary)*
    unary  := '-' unary | atom
    atom   := NUMBER | '(' expr ')'
"""

import sys


class ParseError(Exception):
    """Raised for any input the grammar cannot evaluate."""


def tokenize(text):
    """Turn the input string into a list of tokens.

    A token is either ('num', int) or ('op', str) where str is one of
    + - * / ( ).  Whitespace between tokens is insignificant.
    """
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in "+-*/()":
            tokens.append(("op", ch))
            i += 1
            continue
        if ch.isdigit() and ch.isascii():
            j = i
            while j < n and text[j].isdigit() and text[j].isascii():
                j += 1
            tokens.append(("num", int(text[i:j])))
            i = j
            continue
        # Stray token: anything else is not part of the grammar.
        raise ParseError("stray token: %r" % ch)
    return tokens


class Parser(object):
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def accept_op(self, *ops):
        tok = self.peek()
        if tok is not None and tok[0] == "op" and tok[1] in ops:
            self.pos += 1
            return tok[1]
        return None

    def parse(self):
        value = self.expr()
        if self.pos != len(self.tokens):
            # Trailing junk, e.g. an unmatched ')'.
            raise ParseError("unexpected trailing token")
        return value

    def expr(self):
        value = self.term()
        while True:
            op = self.accept_op("+", "-")
            if op is None:
                return value
            right = self.term()
            if op == "+":
                value = value + right
            else:
                value = value - right

    def term(self):
        value = self.unary()
        while True:
            op = self.accept_op("*", "/")
            if op is None:
                return value
            right = self.unary()
            if op == "*":
                value = value * right
            else:
                value = div_trunc(value, right)

    def unary(self):
        if self.accept_op("-") is not None:
            return -self.unary()
        return self.atom()

    def atom(self):
        tok = self.peek()
        if tok is None:
            # Empty input, or a trailing operator with no operand.
            raise ParseError("unexpected end of input")
        if tok[0] == "num":
            self.pos += 1
            return tok[1]
        if tok[1] == "(":
            self.pos += 1
            value = self.expr()
            if self.accept_op(")") is None:
                raise ParseError("unmatched '('")
            return value
        raise ParseError("unexpected token: %r" % tok[1])


def div_trunc(a, b):
    """Integer division truncating toward zero.  -7 / 2 == -3."""
    if b == 0:
        raise ParseError("division by zero")
    quotient = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        return -quotient
    return quotient


def evaluate(text):
    return Parser(tokenize(text)).parse()


def main():
    data = sys.stdin.read()
    try:
        result = evaluate(data)
    except ParseError:
        sys.stdout.write("ERROR\n")
        return 0
    sys.stdout.write("%d\n" % result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
