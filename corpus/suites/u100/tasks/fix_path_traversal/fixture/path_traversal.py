import os
def read_file(base_dir, filename):
    path = os.path.join(base_dir, filename)
    with open(path) as f:
        return f.read()
