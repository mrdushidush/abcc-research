class Router:
    def __init__(self):
        self.routes = {}

    def add_route(self, method, path, handler):
        key = method.upper() + ' ' + path
        self.routes[key] = handler

    def match(self, method, path):
        key = method.upper() + ' ' + path
        if key in self.routes:
            return self.routes[key]
        return None
