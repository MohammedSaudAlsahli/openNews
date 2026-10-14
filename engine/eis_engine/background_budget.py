"""Conservative local inference scheduling, driven by native macOS thermal signals."""
import time
from .contracts import Failure


class BackgroundBudget:
    def __init__(self):
        self.updated = 0.0
        self.thermal = 'unknown'
        self.low_power = False
        self.next_at = 0.0

    def update(self, payload):
        thermal, low_power = payload.get('thermal'), payload.get('low_power')
        if thermal not in {'nominal','fair','serious','critical','unknown'} or type(low_power) is not bool:
            raise Failure('VALIDATION_ERROR', 'Invalid device energy state.')
        self.thermal, self.low_power, self.updated = thermal, low_power, time.monotonic()
        return {'phase': self.phase()}

    def phase(self):
        if time.monotonic()-self.updated > 30 or self.thermal == 'unknown': return 'waiting_device'
        if self.thermal != 'nominal': return 'cooling'
        if self.low_power: return 'low_power'
        if time.monotonic() < self.next_at: return 'resting'
        return ''

    def finished(self, elapsed):
        # One article per batch, at most roughly 20% inference duty cycle.
        self.next_at = time.monotonic()+max(60, elapsed*4)
