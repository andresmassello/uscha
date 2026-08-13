import sys

def tokenize(expr):
    """Tokenize the expression string. Return None if invalid character found."""
    tokens = []
    i = 0
    while i < len(expr):
        if expr[i].isspace():
            i += 1
        elif expr[i] in '+-*/()':
            tokens.append(expr[i])
            i += 1
        elif expr[i].isdigit():
            j = i
            while j < len(expr) and expr[j].isdigit():
                j += 1
            tokens.append(int(expr[i:j]))
            i = j
        else:
            return None  # Invalid character
    return tokens

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.pos = 0

    def current(self):
        """Return the current token, or None if at end."""
        if self.pos < len(self.tokens):
            return self.tokens[self.pos]
        return None

    def consume(self, expected=None):
        """Consume the current token. Optionally check it matches expected value."""
        token = self.current()
        if expected is not None and token != expected:
            return False
        self.pos += 1
        return True

    def parse(self):
        """Parse the expression. Return value on success, None on error."""
        if not self.tokens:
            return None  # Empty input

        result = self.expression()
        if result is None:
            return None

        # Ensure all tokens were consumed
        if self.pos != len(self.tokens):
            return None

        return result

    def expression(self):
        """Parse addition and subtraction (lowest precedence, left-associative)."""
        left = self.term()
        if left is None:
            return None

        while self.current() in ('+', '-'):
            op = self.current()
            self.consume()
            right = self.term()
            if right is None:
                return None
            if op == '+':
                left = left + right
            else:
                left = left - right

        return left

    def term(self):
        """Parse multiplication and division (higher precedence, left-associative)."""
        left = self.factor()
        if left is None:
            return None

        while self.current() in ('*', '/'):
            op = self.current()
            self.consume()
            right = self.factor()
            if right is None:
                return None
            if op == '*':
                left = left * right
            else:
                # Integer division truncating toward zero
                if right == 0:
                    return None  # Division by zero is an error
                left = int(left / right)

        return left

    def factor(self):
        """Parse unary minus and primary expressions."""
        if self.current() == '-':
            self.consume()
            value = self.factor()  # Recursive call for right-associativity of unary minus
            if value is None:
                return None
            return -value
        else:
            return self.primary()

    def primary(self):
        """Parse numbers and parenthesized expressions."""
        token = self.current()

        if isinstance(token, int):
            self.consume()
            return token
        elif token == '(':
            self.consume()
            result = self.expression()
            if result is None:
                return None
            if not self.consume(')'):
                return None  # Unmatched opening parenthesis
            return result
        else:
            return None  # Invalid token or end of input

def main():
    try:
        expr = sys.stdin.read()
    except:
        print("ERROR")
        return

    tokens = tokenize(expr)
    if tokens is None:
        print("ERROR")
        return

    parser = Parser(tokens)
    result = parser.parse()

    if result is None:
        print("ERROR")
    else:
        print(int(result))

if __name__ == '__main__':
    main()
