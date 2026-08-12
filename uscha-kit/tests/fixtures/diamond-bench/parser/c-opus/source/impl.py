import sys


class ParseError(Exception):
    pass


def tokenize(s):
    tokens = []
    i = 0
    n = len(s)
    while i < n:
        c = s[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit():
            j = i
            while j < n and s[j].isdigit():
                j += 1
            tokens.append(("NUM", int(s[i:j])))
            i = j
            continue
        if c in "+-*/()":
            tokens.append((c, c))
            i += 1
            continue
        raise ParseError("unexpected character: %r" % c)
    return tokens


def trunc_div(a, b):
    if b == 0:
        raise ParseError("division by zero")
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return (None, None)

    def advance(self):
        tok = self.tokens[self.pos]
        self.pos += 1
        return tok

    def expect(self, kind):
        t, v = self.peek()
        if t != kind:
            raise ParseError("expected %r" % kind)
        return self.advance()

    def parse(self):
        value = self.expr()
        if self.pos != len(self.tokens):
            raise ParseError("trailing tokens")
        return value

    # expr = term (('+' | '-') term)*   left-associative
    def expr(self):
        value = self.term()
        while True:
            t, _ = self.peek()
            if t == "+":
                self.advance()
                value = value + self.term()
            elif t == "-":
                self.advance()
                value = value - self.term()
            else:
                break
        return value

    # term = unary (('*' | '/') unary)*   left-associative
    def term(self):
        value = self.unary()
        while True:
            t, _ = self.peek()
            if t == "*":
                self.advance()
                value = value * self.unary()
            elif t == "/":
                self.advance()
                value = trunc_div(value, self.unary())
            else:
                break
        return value

    # unary = '-' unary | primary   (binds tighter than * and /)
    def unary(self):
        t, _ = self.peek()
        if t == "-":
            self.advance()
            return -self.unary()
        return self.primary()

    # primary = number | '(' expr ')'
    def primary(self):
        t, v = self.peek()
        if t == "NUM":
            self.advance()
            return v
        if t == "(":
            self.advance()
            value = self.expr()
            self.expect(")")
            return value
        raise ParseError("expected number or '('")


def main():
    data = sys.stdin.read()
    try:
        tokens = tokenize(data)
        if not tokens:
            raise ParseError("empty input")
        result = Parser(tokens).parse()
        sys.stdout.write(str(result) + "\n")
    except ParseError:
        sys.stdout.write("ERROR\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
