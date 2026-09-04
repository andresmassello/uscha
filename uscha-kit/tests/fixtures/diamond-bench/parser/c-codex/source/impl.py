import sys


class ParseError(Exception):
    pass


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def skip_ws(self):
        while self.pos < self.length and self.text[self.pos].isspace():
            self.pos += 1

    def peek(self):
        self.skip_ws()
        if self.pos >= self.length:
            return None
        return self.text[self.pos]

    def consume(self, char):
        self.skip_ws()
        if self.pos < self.length and self.text[self.pos] == char:
            self.pos += 1
            return True
        return False

    def parse(self):
        value = self.parse_expr()
        self.skip_ws()
        if self.pos != self.length:
            raise ParseError()
        return value

    def parse_expr(self):
        value = self.parse_term()
        while True:
            if self.consume('+'):
                value += self.parse_term()
            elif self.consume('-'):
                value -= self.parse_term()
            else:
                return value

    def parse_term(self):
        value = self.parse_unary()
        while True:
            if self.consume('*'):
                value *= self.parse_unary()
            elif self.consume('/'):
                rhs = self.parse_unary()
                if rhs == 0:
                    raise ParseError()
                value = trunc_div(value, rhs)
            else:
                return value

    def parse_unary(self):
        if self.consume('-'):
            return -self.parse_unary()
        return self.parse_primary()

    def parse_primary(self):
        self.skip_ws()
        if self.pos >= self.length:
            raise ParseError()

        char = self.text[self.pos]
        if char == '(':
            self.pos += 1
            value = self.parse_expr()
            if not self.consume(')'):
                raise ParseError()
            return value

        if char.isdigit():
            start = self.pos
            while self.pos < self.length and self.text[self.pos].isdigit():
                self.pos += 1
            return int(self.text[start:self.pos])

        raise ParseError()


def trunc_div(left, right):
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        return -quotient
    return quotient


def main():
    text = sys.stdin.read()
    try:
        print(Parser(text).parse())
    except Exception:
        print('ERROR')


if __name__ == '__main__':
    main()
