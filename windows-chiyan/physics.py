"""Independent, screen-local motion in pixels and seconds.

Inspired by dsh-pet's separation of rendered actions and pointer physics.
No upstream implementation or assets are copied.
"""

from dataclasses import dataclass
import math


@dataclass
class Body:
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0


def clamp_position(position, bounds):
    left, top, right, bottom = bounds
    return (max(left, min(position[0], max(left, right))),
            max(top, min(position[1], max(top, bottom))))


def spring_follow(body, target, dt):
    # Analytic critically damped spring: stable even if timer intervals vary.
    dt = min(.05, max(0, dt))
    omega = 18.0
    decay = math.exp(-omega * dt)
    axes = []
    for position, speed, destination in ((body.x, body.vx, target[0]), (body.y, body.vy, target[1])):
        offset = position - destination
        term = speed + omega * offset
        axes.append((destination + (offset + term * dt) * decay,
                     (speed - omega * term * dt) * decay))
    return Body(axes[0][0], axes[1][0], axes[0][1], axes[1][1])


def release_velocity(samples, now):
    if len(samples) < 2 or now - samples[-1][0] > .15:
        return (0, 0)
    recent = [s for s in samples if samples[-1][0] - s[0] <= .12]
    if len(recent) < 2:
        return (0, 0)
    span = recent[-1][0] - recent[0][0]
    if span < .02:
        return (0, 0)
    vx = (recent[-1][1] - recent[0][1]) / span
    vy = (recent[-1][2] - recent[0][2]) / span
    speed = math.hypot(vx, vy)
    if speed < 500:
        return (0, 0)
    scale = min(1, 2200 / speed)
    return vx * scale, vy * scale


def step_throw(body, bounds, dt):
    left, top, right, bottom = bounds
    right, bottom = max(left, right), max(top, bottom)
    x, y = clamp_position((body.x, body.y), bounds)
    vx, vy = body.vx, body.vy
    remaining = min(.05, max(0, dt))
    impact = 0.0
    while remaining > 1e-10:
        step = min(remaining, 1 / 120)
        remaining -= step
        if not (y >= bottom and vy == 0):
            vy += 1400 * step
        x += vx * step
        y += vy * step
        if x < left:
            x, vx = left, abs(vx) * .65
        elif x > right:
            x, vx = right, -abs(vx) * .65
        if y < top:
            y, vy = top, abs(vy) * .65
        elif y >= bottom:
            y = bottom
            if vy > 0:
                impact = max(impact, vy)
                vy = -vy * .55 if vy > 90 else 0
        if y >= bottom and vy == 0:
            vx *= math.exp(-6 * step)
            if abs(vx) < 15:
                vx = 0
    return Body(x, y, vx, vy), impact
