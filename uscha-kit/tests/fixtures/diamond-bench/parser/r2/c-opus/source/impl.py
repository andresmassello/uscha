"""Integer arithmetic expression evaluator.

Reads one expression from standard input, prints its integer value on one
line, or prints exactly ERROR when the grammar cannot evaluate the input.
Always exits 0.

Grammar (recursive descent, left-associative binary operators):

    expr   := term (('+' | '-') term)*
    term   := unary (('*' | '/') unary)*
    unary  := '-' unary | atom
    atom   := NUMBER | '(' expr ')'

Division truncates toward zero; division by zero is an error.
"""

import sys


class ParseError(Exception):
    """Raised for any input the grammar cannot evaluate."""


def tokenize(text):
    """Turn the input string into a list of tokens.

    A token is either ('num', value) or ('op', symbol) where symbol is one
    of + - * / ( ). Whitespace separates tokens but is otherwise ignored.
    """
    tokens = []
    i = 0
    n = len(text)
    while i < n:
        ch = text[i]
        if ch.isspace():
            i += 1
            continue
        if ch in '+-*/()':
            tokens.append(('op', ch))
            i += 1
            continue
        if ch.isdigit() and ch.isascii():
            start = i
            while i < n and text[i].isdigit() and text[i].isascii():
                i += 1
            tokens.append(('num', int(text[start:i])))
            continue
        raise ParseError('unexpected character: %r' % ch)
    return tokens


class Parser:
    """Recursive-descent parser that evaluates while it parses."""

    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def at_op(self, *symbols):
        tok = self.peek()
        return tok is not None and tok[0] == 'op' and tok[1] in symbols

    def advance(self):
        tok = self.peek()
        if tok is None:
            raise ParseError('unexpected end of input')
        self.pos += 1
        return tok

    def parse(self):
        value = self.expr()
        if self.peek() is not None:
            raise ParseError('trailing input')
        return value

    def expr(self):
        value = self.term()
        while self.at_op('+', '-'):
            op = self.advance()[1]
            right = self.term()
            if op == '+':
                value = value + right
            else:
                value = value - right
        return value

    def term(self):
        value = self.unary()
        while self.at_op('*', '/'):
            op = self.advance()[1]
            right = self.unary()
            if op == '*':
                value = value * right
            else:
                value = divide(value, right)
        return value

    def unary(self):
        if self.at_op('-'):
            self.advance()
            return -self.unary()
        return self.atom()

    def atom(self):
        tok = self.peek()
        if tok is None:
            raise ParseError('unexpected end of input')
        if tok[0] == 'num':
            self.advance()
            return tok[1]
        if tok[0] == 'op' and tok[1] == '(':
            self.advance()
            value = self.expr()
            if not self.at_op(')'):
                raise ParseError('unmatched parenthesis')
            self.advance()
            return value
        raise ParseError('unexpected token: %r' % (tok[1],))


def divide(left, right):
    """Integer division truncating toward zero (so -7 / 2 == -3)."""
    if right == 0:
        raise ParseError('division by zero')
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        return -quotient
    return quotient


def evaluate(text):
    """Evaluate an expression string, raising ParseError on bad input."""
    tokens = tokenize(text)
    if not tokens:
        raise ParseError('empty input')
    return Parser(tokens).parse()


def main():
    text = sys.stdin.read()
    try:
        result = evaluate(text)
    except ParseError:
        sys.stdout.write('ERROR\n')
        return 0
    sys.stdout.write('%d\n' % result)
    return 0


if __name__ == '__main__':
    sys.exit(main())
