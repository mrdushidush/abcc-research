def transpose(matrix):
    if not matrix:
        return []
    rows = len(matrix)
    cols = len(matrix[0])
    result = []
    for c in range(cols):
        row = []
        for r in range(rows):
            row.append(matrix[r][c])
        result.append(row)
    return result
