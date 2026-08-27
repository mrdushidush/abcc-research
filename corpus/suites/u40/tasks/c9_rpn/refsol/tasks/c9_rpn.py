def rpn_calc(expression):
    stack = []
    for token in expression.split():
        if token in '+-*/':
            b = stack.pop()
            a = stack.pop()
            if token == '+': stack.append(a + b)
            elif token == '-': stack.append(a - b)
            elif token == '*': stack.append(a * b)
            elif token == '/': stack.append(a / b)
        else:
            stack.append(float(token))
    return stack[0]
