import sys

def tokenize(expr):
    """Tokenize the expression into (type, value) tuples."""
    tokens = []
    i = 0
    while i < len(expr):
        if expr[i].isspace():
            i += 1
            continue
        if expr[i].isdigit():
            j = i
            while j < len(expr) and expr[j].isdigit():
                j += 1
            tokens.append(('NUMBER', int(expr[i:j])))
            i = j
        elif expr[i] in '+-*/()':
            tokens.append((expr[i], expr[i]))
            i += 1
        else:
            return None  # Invalid character
    return tokens

def parse_and_evaluate(tokens):
    """Parse and evaluate the expression using recursive descent."""
    if not tokens:
        return None

    pos = [0]  # Mutable position tracker

    def peek():
        if pos[0] < len(tokens):
            return tokens[pos[0]]
        return None

    def consume():
        token = peek()
        pos[0] += 1
        return token

    def parse_expression():
        """Parse: term (('+' | '-') term)*"""
        left = parse_term()
        if left is None:
            return None

        while peek() and peek()[0] in ['+', '-']:
            op = consume()[0]
            right = parse_term()
            if right is None:
                return None
            if op == '+':
                left = left + right
            else:
                left = left - right

        return left

    def parse_term():
        """Parse: factor (('*' | '/') factor)*"""
        left = parse_factor()
        if left is None:
            return None

        while peek() and peek()[0] in ['*', '/']:
            op = consume()[0]
            right = parse_factor()
            if right is None:
                return None
            if op == '*':
                left = left * right
            else:
                if right == 0:
                    return None  # Division by zero
                left = int(left / right)  # Truncate toward zero

        return left

    def parse_factor():
        """Parse: ['-'] factor | primary"""
        if peek() and peek()[0] == '-':
            consume()
            val = parse_factor()  # Recursive for multiple unary minuses
            if val is None:
                return None
            return -val
        return parse_primary()

    def parse_primary():
        """Parse: NUMBER | '(' expression ')'"""
        token = peek()
        if token is None:
            return None

        if token[0] == 'NUMBER':
            consume()
            return token[1]
        elif token[0] == '(':
            consume()
            val = parse_expression()
            if val is None:
                return None
            if not peek() or peek()[0] != ')':
                return None  # Missing closing paren
            consume()
            return val
        else:
            return None

    result = parse_expression()
    if result is None:
        return None

    # Ensure all tokens were consumed
    if pos[0] != len(tokens):
        return None

    return result

def main():
    try:
        expr = sys.stdin.read()
        expr = expr.strip()

        if not expr:
            print("ERROR")
            return

        tokens = tokenize(expr)
        if tokens is None:
            print("ERROR")
            return

        result = parse_and_evaluate(tokens)
        if result is None:
            print("ERROR")
            return

        print(int(result))
    except Exception:
        print("ERROR")

if __name__ == '__main__':
    main()
