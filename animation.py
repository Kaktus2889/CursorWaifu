"""Sub-frame sprite rendering. Blended frames are not additional drawn poses."""
import math
from PySide6.QtCore import Qt
from PySide6.QtGui import QBitmap, QPainter, QPixmap, QRegion


def smoothstep(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def blend(a, b, amount):
    """Premultiplied additive mixing preserves alpha (no opacity pulsing)."""
    if amount <= 0:
        return a
    if amount >= 1:
        return b
    out = QPixmap(a.size())
    out.fill(Qt.transparent)
    painter = QPainter(out)
    painter.setCompositionMode(QPainter.CompositionMode_Plus)
    painter.setOpacity(1 - amount)
    painter.drawPixmap(0, 0, a)
    painter.setOpacity(amount)
    painter.drawPixmap(0, 0, b)
    painter.end()
    return out


def align_run(frames):
    """Remove atlas padding drift using a shared scale and stable head baseline."""
    boxes = [QRegion(QBitmap.fromImage(f.toImage().createAlphaMask())).boundingRect()
             for f in frames]
    scale = 232 / max(b.height() for b in boxes)
    result = []
    for f, box in zip(frames, boxes):
        sprite = f.copy(box).scaled(round(box.width()*scale), round(box.height()*scale),
                                   Qt.KeepAspectRatio, Qt.SmoothTransformation)
        out = QPixmap(270, 270)
        out.fill(Qt.transparent)
        painter = QPainter(out)
        painter.drawPixmap((270-sprite.width())//2, 20, sprite)
        painter.end()
        result.append(out)
    return result


class RunCycle:
    def __init__(self, frames):
        # 8 source poses, 4 subframes each; generated once, never in paintEvent.
        self.frames = []
        for i, frame in enumerate(frames):
            for step in range(4):
                self.frames.append(blend(frame, frames[(i+1) % len(frames)],
                                         smoothstep(step/4)))

    def sample(self, phase):
        return self.frames[int((phase % 8) * 4) % len(self.frames)]


def ease(current, target, dt, rate=12):
    return current + (target-current) * (-math.expm1(-rate * max(0, dt)))
