"""Writing pages to the sink."""


class Sink:
    def __init__(self):
        self.pages = []

    def write(self, page):
        self.pages.append(list(page))

    def rows(self):
        return [row for page in self.pages for row in page]


def write_all(sink, pages):
    for page in pages:
        sink.write(page)
    return sink
