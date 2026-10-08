"""Explicit assessment boundary timers; no engine hooks or execution authority.

The caller owns stage selection. Raw total includes every interval, including
diagnostics and external acceptance. Exclusive rows partition that same clock;
subtracting diagnostics does not measure an uncaptured production invocation.
"""
from contextlib import contextmanager
import time


class DailyTiming:
    CATEGORIES = frozenset((
        'admission_ingestion', 'opening_calculation', 'actions',
        'closing_sources', 'presentation_publication_readiness',
        'startup_orchestration', 'diagnostics', 'external_acceptance',
    ))

    def __init__(self, *, clock=time.perf_counter):
        self.clock = clock
        self.started = clock()
        self.previous = self.started
        self.stack = []
        self.rows = []
        self.exclusive = dict.fromkeys(self.CATEGORIES, 0.0)
        self.finished = None

    def _tick(self):
        now = self.clock()
        if now < self.previous:
            raise ValueError('Timing clock moved backwards')
        category = self.stack[-1]['category'] if self.stack else 'startup_orchestration'
        self.exclusive[category] += now - self.previous
        self.previous = now
        return now

    @contextmanager
    def boundary(self, category, name):
        if self.finished is not None:
            raise ValueError('Timing already finished')
        if category not in self.CATEGORIES or not isinstance(name, str) or not name:
            raise ValueError('Explicit known boundary required')
        now = self._tick()
        row = dict(category=category, name=name, start_seconds=now-self.started,
                   depth=len(self.stack), status='RUNNING')
        self.rows.append(row)
        self.stack.append(row)
        try:
            yield
        except BaseException:
            row['status'] = 'FAILED'
            raise
        else:
            row['status'] = 'COMPLETE'
        finally:
            end = self._tick()
            self.stack.pop()
            row['elapsed_seconds'] = end-self.started-row['start_seconds']

    def finish(self, *, published_consumable):
        if self.stack or self.finished is not None:
            raise ValueError('Cannot finish active or finished timing')
        end = self._tick()
        self.finished = end
        return dict(
            schema='fresh-daily-boundary-timing-v1',
            elapsed_invocation_seconds=end-self.started,
            published_consumable=bool(published_consumable),
            exclusive_seconds=dict(sorted(self.exclusive.items())),
            boundaries=self.rows,
            limitation=('Inclusive boundary rows overlap: do not sum them. '
                        'Exclusive categories partition this invocation only. '
                        'Diagnostic subtraction is attribution, not an observed '
                        'uncaptured production run. Reader success must be proved '
                        'by the caller; this timer does not certify publication.'),
        )
