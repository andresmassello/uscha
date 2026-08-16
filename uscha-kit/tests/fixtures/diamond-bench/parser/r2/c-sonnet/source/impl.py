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
        raise ParseError("unexpected character")
    return tokens


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
        self.pos += 1
        return tok

    def parse_expr(self):
        val = self.parse_term()
        while True:
            tok = self.peek()
            if tok is not None and tok[0] in ('+', '-'):
                self.advance()
                rhs = self.parse_term()
                if tok[0] == '+':
                    val = val + rhs
                else:
                    val = val - rhs
            else:
                break
        return val

    def parse_term(self):
        val = self.parse_factor()
        while True:
            tok = self.peek()
            if tok is not None and tok[0] in ('*', '/'):
                self.advance()
                rhs = self.parse_factor()
                if tok[0] == '*':
                    val = val * rhs
                else:
                    if rhs == 0:
                        raise ParseError("division by zero")
                    q = abs(val) // abs(rhs)
                    if (val < 0) != (rhs < 0):
                        q = -q
                    val = q
            else:
                break
        return val

    def parse_factor(self):
        tok = self.peek()
        if tok is not None and tok[0] == '-':
            self.advance()
            return -self.parse_factor()
        return self.parse_primary()

    def parse_primary(self):
        tok = self.peek()
        if tok is None:
            raise ParseError("unexpected end of input")
        if tok[0] == 'NUM':
            self.advance()
            return tok[1]
        if tok[0] == '(':
            self.advance()
            val = self.parse_expr()
            tok2 = self.peek()
            if tok2 is None or tok2[0] != ')':
                raise ParseError("expected closing parenthesis")
            self.advance()
            return val
        raise ParseError("unexpected token")


def evaluate(text):
    tokens = tokenize(text)
    parser = Parser(tokens)
    if parser.peek() is None:
        raise ParseError("empty expression")
    value = parser.parse_expr()
    if parser.pos != len(parser.tokens):
        raise ParseError("trailing tokens")
    return value


def main():
    data = sys.stdin.read()
    try:
        result = evaluate(data)
        print(result)
    except Exception:
        print("ERROR")
    sys.exit(0)


if __name__ == "__main__":
    main()
