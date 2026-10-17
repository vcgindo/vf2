"""Retired historical trace-day entry; use its pinned historical source only.

Current production exposes one native execution behavior without trace hooks.
This adapter deliberately cannot turn an old trace request into a production
day or claim the old archive/validation contract still exists.
"""


def execute_day(**kwargs):
    raise ValueError(
        'Historical validation-day execution is unsupported by cleaned source; '
        'preserved trace tools require their pinned pre-Step3 source. '
        'Use native production entrypoints without evidence/callback arguments.')
