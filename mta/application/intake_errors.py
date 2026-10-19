"""Bounded production rejection diagnostics, never retained calculation graphs."""


class NativeIntakeRejected(ValueError):
    def __init__(self, message, *, stage, rejections):
        self.stage = stage
        self.rejections = [dict(row) for row in rejections]
        super().__init__(message)
