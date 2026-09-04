import sys


class ParseError(Exception):
    pass


def trunc_div(left, right):
    if right == 0:
        raise ParseError()
    quotient = abs(left) // abs(right)
    if (left < 0) != (right < 0):
        return -quotient
    return quotient


class Parser:
    def __init__(self, text):
        self.text = text
        self.pos = 0
        self.length = len(text)

    def skip_ws(self):
        while self.pos < self.length and self.text[self.pos].isspace():
            self.pos += 1

    def parse(self):
        value = self.parse_expression()
        self.skip_ws()
        if self.pos != self.length:
            raise ParseError()
        return value

    def parse_expression(self):
        return self.parse_add_sub()

    def parse_add_sub(self):
        value = self.parse_mul_div()
        while True:
            self.skip_ws()
            if self.pos >= self.length or self.text[self.pos] not in '+-':
                return value
            op = self.text[self.pos]
            self.pos += 1
            right = self.parse_mul_div()
            if op == '+':
                value += right
            else:
                value -= right

    def parse_mul_div(self):
        value = self.parse_unary()
        while True:
            self.skip_ws()
            if self.pos >= self.length or self.text[self.pos] not in '*/':
                return value
            op = self.text[self.pos]
            self.pos += 1
            right = self.parse_unary()
            if op == '*':
                value *= right
            else:
                value = trunc_div(value, right)

    def parse_unary(self):
        self.skip_ws()
        if self.pos < self.length and self.text[self.pos] == '-':
            self.pos += 1
            return -self.parse_unary()
        return self.parse_primary()

    def parse_primary(self):
        self.skip_ws()
        if self.pos >= self.length:
            raise ParseError()

        ch = self.text[self.pos]
        if ch == '(':
            self.pos += 1
            value = self.parse_expression()
            self.skip_ws()
            if self.pos >= self.length or self.text[self.pos] != ')':
                raise ParseError()
            self.pos += 1
            return value

        if ch.isdigit():
            start = self.pos
            while self.pos < self.length and self.text[self.pos].isdigit():
                self.pos += 1
            return int(self.text[start:self.pos])

        raise ParseError()


def main():
    try:
        text = sys.stdin.read()
        value = Parser(text).parse()
        print(value)
    except Exception:
        print('ERROR')


if __name__ == '__main__':
    main()
