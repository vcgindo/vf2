"""Test-only value capture before advancing a mutable ordinary producer."""
from copy import deepcopy


def capture_stages(stages):
    return [deepcopy(stage) for stage in stages]
