class TextStats:
    def __init__(self, text):
        self.text = text
        self.words = text.lower().split()
    def word_count(self):
        return len(self.words)
    def char_count(self):
        return len(self.text.replace(' ', ''))
    def most_common_word(self):
        freq = {}
        for w in self.words:
            freq[w] = freq.get(w, 0) + 1
        return max(freq, key=freq.get)
