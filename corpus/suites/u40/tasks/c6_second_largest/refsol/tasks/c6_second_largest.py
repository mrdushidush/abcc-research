def find_second_largest(numbers):
    unique = list(set(numbers))
    if len(unique) < 2:
        return None
    unique.sort(reverse=True)
    return unique[1]
