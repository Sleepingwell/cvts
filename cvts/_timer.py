from timeit import default_timer

class Timer:
    def __init__(self, logger=None):
        self.logger = logger

    def __enter__(self):
        self.start = default_timer()
        return self

    def __exit__(self, *args):
        self.elapsed = default_timer() - self.start
        if self.logger is not None:
            self.logger('\ttook: {} seconds'.format(self.elapsed))
