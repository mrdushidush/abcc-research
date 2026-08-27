def power_set(s):
    result = [[]]
    for elem in s:
        result += [subset + [elem] for subset in result]
    return result
