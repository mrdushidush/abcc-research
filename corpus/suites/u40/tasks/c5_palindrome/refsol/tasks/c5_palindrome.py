def is_palindrome(s):
    cleaned = s.lower().replace(' ', '')
    return cleaned == cleaned[::-1]
