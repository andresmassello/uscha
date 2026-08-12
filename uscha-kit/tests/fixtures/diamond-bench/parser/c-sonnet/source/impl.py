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
            tokens.append(('NUM', int(s[i:j])))
            i = j
            continue
        if c in '+-*/()':
            tokens.append((c, c))
            i += 1
            continue
        raise ParseError('unexpected character')
    tokens.append(('EOF', None))
    return tokens


def trunc_div(a, b):
    q = abs(a) // abs(b)
    if (a < 0) != (b < 0):
        q = -q
    return q


class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def peek(self):
        return self.tokens[self.pos]

    def advance(self):
        t = self.tokens[self.pos]
        self.pos += 1
        return t

    def expect(self, kind):
        t = self.advance()
        if t[0] != kind:
            raise ParseError('expected ' + kind)
        return t

    def parse_expr(self):
        val = self.parse_term()
        while self.peek()[0] in ('+', '-'):
            op = self.advance()[0]
            rhs = self.parse_term()
            if op == '+':
                val = val + rhs
            else:
                val = val - rhs
        return val

    def parse_term(self):
        val = self.parse_factor()
        while self.peek()[0] in ('*', '/'):
            op = self.advance()[0]
            rhs = self.parse_factor()
            if op == '*':
                val = val * rhs
            else:
                if rhs == 0:
                    raise ZeroDivisionError('division by zero')
                val = trunc_div(val, rhs)
        return val

    def parse_factor(self):
        t = self.peek()
        if t[0] == '-':
            self.advance()
            return -self.parse_factor()
        if t[0] == '(':
            self.advance()
            val = self.parse_expr()
            self.expect(')')
            return val
        if t[0] == 'NUM':
            self.advance()
            return t[1]
        raise ParseError('unexpected token')


def main():
    data = sys.stdin.read()
    try:
        tokens = tokenize(data)
        parser = Parser(tokens)
        val = parser.parse_expr()
        if parser.peek()[0] != 'EOF':
            raise ParseError('trailing tokens')
        print(val)
    except Exception:
        print('ERROR')


if __name__ == '__main__':
    main()
    sys.exit(0)
