def truncate(s, max_len):
    if len(s) <= max_len:
        return s
    return s[:max_len - 3] + '...'
