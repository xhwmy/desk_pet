"""Elapsed-time clip playback and nonrepeating weighted activity selection."""

import math
import random


class ClipClock:
    def __init__(self, durations, loop=False):
        self.durations = tuple(durations)
        if not self.durations or any(not math.isfinite(t) or t <= 0 for t in self.durations):
            raise ValueError('Clip durations must be finite positive seconds')
        self.loop = loop
        self.frame = 0
        self.elapsed = 0.0
        self.finished = False

    def advance(self, dt):
        if self.finished:
            return
        # A stalled UI must not eat a complete manual action on resumption.
        self.elapsed += min(.25, max(0, dt))
        while self.elapsed + 1e-9 >= self.durations[self.frame]:
            self.elapsed = max(0, self.elapsed - self.durations[self.frame])
            if self.frame + 1 < len(self.durations):
                self.frame += 1
            elif self.loop:
                self.frame = 0
            else:
                self.finished = True
                break


def choose_action(weights, previous=None, rng=None):
    rng = rng or random
    pool = [(name, weight) for name, weight in weights.items() if weight > 0]
    alternatives = [(name, weight) for name, weight in pool if name != previous]
    pool = alternatives or pool
    if not pool:
        return None
    ticket = rng.random() * sum(weight for _, weight in pool)
    for name, weight in pool:
        ticket -= weight
        if ticket < 0:
            return name
    return pool[-1][0]
