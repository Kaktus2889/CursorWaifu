"""Frame-rate independent, acceleration-limited cursor following (pixels/seconds)."""
from dataclasses import dataclass
from math import hypot, sqrt


@dataclass
class Motion:
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    chasing: bool = False

    def stop(self):
        self.vx = self.vy = 0.0
        self.chasing = False

    def step(self, tx, ty, dt, size=190, speed=1.0, enabled=True):
        # Substeps keep acceleration/braking consistent even on busy desktops.
        remaining = max(0.0, min(dt, 0.1))
        travelled = 0.0
        while remaining > 1e-9:
            h = min(remaining, 1 / 240)
            remaining -= h
            dx, dy = tx - self.x, ty - self.y
            distance = hypot(dx, dy)
            radius = size * 0.56
            if not enabled:
                self.chasing = False
            elif distance > radius + 18:
                self.chasing = True
            elif distance <= radius + 0.5:
                self.chasing = False
            accel = 1800 * speed
            gap = max(0, distance - radius)
            desired = min(460 * speed, gap * 5, sqrt(2 * accel * gap)) if self.chasing else 0
            ux, uy = (dx / distance, dy / distance) if distance else (0, 0)
            dvx, dvy = ux * desired - self.vx, uy * desired - self.vy
            change = hypot(dvx, dvy)
            scale = min(1, accel * h / change) if change else 0
            self.vx += dvx * scale
            self.vy += dvy * scale
            if not self.chasing and hypot(self.vx, self.vy) < 1:
                self.vx = self.vy = 0
            mx, my = self.vx * h, self.vy * h
            self.x += mx
            self.y += my
            travelled += hypot(mx, my)
        return travelled
