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
            tokens.append(('NUM', s[i:j]))
            i = j
            continue
        if c in '+-*/()':
            tokens.append((c, c))
            i += 1
            continue
        raise ParseError('bad char')
    return tokens


def int_divide(a, b):
    if b == 0:
        raise ParseError('division by zero')
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
        return None

    def advance(self):
        tok = self.peek()
        if tok is None:
            raise ParseError('unexpected end')
        self.pos += 1
        return tok

    def parse_expr(self):
        value = self.parse_term()
        while True:
            tok = self.peek()
            if tok is not None and tok[0] in ('+', '-'):
                self.advance()
                rhs = self.parse_term()
                if tok[0] == '+':
                    value = value + rhs
                else:
                    value = value - rhs
            else:
                break
        return value

    def parse_term(self):
        value = self.parse_factor()
        while True:
            tok = self.peek()
            if tok is not None and tok[0] in ('*', '/'):
                self.advance()
                rhs = self.parse_factor()
                if tok[0] == '*':
                    value = value * rhs
                else:
                    value = int_divide(value, rhs)
            else:
                break
        return value

    def parse_factor(self):
        tok = self.peek()
        if tok is not None and tok[0] == '-':
            self.advance()
            return -self.parse_factor()
        return self.parse_primary()

    def parse_primary(self):
        tok = self.advance()
        if tok[0] == 'NUM':
            return int(tok[1])
        if tok[0] == '(':
            value = self.parse_expr()
            close = self.advance()
            if close[0] != ')':
                raise ParseError('expected )')
            return value
        raise ParseError('unexpected token')


def main():
    data = sys.stdin.read()
    try:
        tokens = tokenize(data)
        if not tokens:
            raise ParseError('empty')
        parser = Parser(tokens)
        value = parser.parse_expr()
        if parser.pos != len(parser.tokens):
            raise ParseError('trailing tokens')
        print(value)
    except ParseError:
        print('ERROR')
    except Exception:
        print('ERROR')
    sys.exit(0)


if __name__ == '__main__':
    main()
