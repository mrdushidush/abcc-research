def fibonacci(n):
    if n <= 0:
        return []
    if n == 1:
        return [0]
    result = [0, 1]
    while len(result) < n:
        result.append(result[-1] + result[-2])
    return result
