import sys

def evaluate(expression):
    """Evaluate an arithmetic expression and return the integer result."""
    tokens = tokenize(expression)
    if tokens is None or not tokens:
        return "ERROR"

    try:
        result, pos = parse_expr(tokens, 0)
        if pos != len(tokens):
            return "ERROR"
        return str(int(result))
    except:
        return "ERROR"

def tokenize(expression):
    """Tokenize the expression into numbers and operators."""
    tokens = []
    i = 0
    while i < len(expression):
        if expression[i].isspace():
            i += 1
        elif expression[i] in "+-*/()":
            tokens.append(expression[i])
            i += 1
        elif expression[i].isdigit():
            j = i
            while j < len(expression) and expression[j].isdigit():
                j += 1
            tokens.append(int(expression[i:j]))
            i = j
        else:
            return None
    return tokens

def parse_expr(tokens, pos):
    """Parse addition and subtraction (lowest precedence)."""
    left, pos = parse_term(tokens, pos)

    while pos < len(tokens) and tokens[pos] in ('+', '-'):
        op = tokens[pos]
        pos += 1
        right, pos = parse_term(tokens, pos)
        if op == '+':
            left = left + right
        else:
            left = left - right

    return left, pos

def parse_term(tokens, pos):
    """Parse multiplication and division."""
    left, pos = parse_unary(tokens, pos)

    while pos < len(tokens) and tokens[pos] in ('*', '/'):
        op = tokens[pos]
        pos += 1
        right, pos = parse_unary(tokens, pos)
        if op == '*':
            left = left * right
        else:
            if right == 0:
                raise ValueError("Division by zero")
            left = int(left / right)

    return left, pos

def parse_unary(tokens, pos):
    """Parse unary minus and primary expressions."""
    if pos < len(tokens) and tokens[pos] == '-':
        pos += 1
        val, pos = parse_unary(tokens, pos)
        return -val, pos
    else:
        return parse_primary(tokens, pos)

def parse_primary(tokens, pos):
    """Parse numbers and parenthesized expressions."""
    if pos >= len(tokens):
        raise ValueError("Unexpected end of expression")

    token = tokens[pos]
    if isinstance(token, int):
        return token, pos + 1
    elif token == '(':
        pos += 1
        val, pos = parse_expr(tokens, pos)
        if pos >= len(tokens) or tokens[pos] != ')':
            raise ValueError("Unmatched parenthesis")
        return val, pos + 1
    else:
        raise ValueError("Unexpected token")

if __name__ == "__main__":
    expr = sys.stdin.read()
    print(evaluate(expr))
