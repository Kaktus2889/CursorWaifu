from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path
from motion import Motion
from caret import CaretObserver, to_logical

from PySide6.QtCore import QPoint, QRect, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QCursor, QIcon, QPainter, QPixmap, QTransform, QBitmap, QRegion
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon, QWidget


APP_NAME = "CursorWaifu"
SPRITE_COLUMNS = 4
SPRITE_ROWS = 3
TICK_MS = 16


def resource_path(relative: str) -> Path:
    """Return a resource path that works in source and PyInstaller builds."""
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return root / relative


class CursorWaifu(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.settings = QSettings("Soymix", APP_NAME)
        self.pet_size = int(self.settings.value("size", 190))
        self.speed = float(self.settings.value("speed", 1.0))
        self.following = self.settings.value("following", True, type=bool)
        self.watch_typing = self.settings.value("watch_typing", True, type=bool)
        self.caret_observer = CaretObserver()
        self.caret_point = None
        self.last_caret_poll = 0.0
        self.auto_reaction = False

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)
        self.setWindowFlag(Qt.WindowDoesNotAcceptFocus, True)
        self.setFixedSize(self.pet_size, self.pet_size)

        self.frames = self._load_frames()
        self.mirrored = [p.transformed(QTransform().scale(-1, 1)) for p in self.frames]
        self.motion = Motion()
        self.last_tick = time.monotonic()
        self.anim_time = 0.0
        self.run_phase = 0.0
        self.menu_open = False
        self.manual_sleep = False
        self.next_idle_action = time.monotonic() + 10
        self.frame_index = 0
        self.facing_right = True
        self.velocity_x = 0.0
        self.velocity_y = 0.0
        self.float_x = 0.0
        self.float_y = 0.0
        self.drag_offset: QPoint | None = None
        self.last_motion = time.monotonic()
        self.last_frame_change = time.monotonic()
        self.state = "idle"
        self.reaction_until = 0.0

        screen = QApplication.primaryScreen().availableGeometry()
        saved = self.settings.value("position")
        if isinstance(saved, QPoint):
            start = saved
        else:
            start = QPoint(screen.right() - self.width() - 24, screen.bottom() - self.height() - 24)
        self.move(self._clamped_position(start))
        self.float_x = float(self.x())
        self.float_y = float(self.y())
        self.motion.x = self.float_x
        self.motion.y = self.float_y

        self.tray = self._create_tray()
        self.timer = QTimer(self)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._tick)
        self.timer.start(TICK_MS)

    def _load_frames(self) -> list[QPixmap]:
        # New atlas has explicit row boundaries: never split a body at 1/4 height.
        idle = QPixmap(str(resource_path("assets/idle_v3.webp")))
        extra = QPixmap(str(resource_path("assets/motion_v2.webp")))
        if idle.isNull() or extra.isNull():
            raise FileNotFoundError("Brak arkusza idle_v3.webp lub motion_v2.webp")
        rows = [0, 355, 675, 955, 1254]
        idle_raw = []
        for row in range(4):
            y0, y1 = [round(y * idle.height() / 1254) for y in rows[row:row+2]]
            for col in range(4):
                x0, x1 = round(col * idle.width()/4), round((col+1)*idle.width()/4)
                idle_raw.append(idle.copy(x0, y0, x1-x0, y1-y0))
        # Alpha bounding boxes plus a common scale preserve full feet and head size.
        boxes = [QRegion(QBitmap.fromImage(p.toImage().createAlphaMask())).boundingRect() for p in idle_raw]
        factor = 238 / max(b.height() for b in boxes)
        idle_frames = []
        for source, box in zip(idle_raw, boxes):
            canvas = QPixmap(270, 270)
            canvas.fill(Qt.transparent)
            p = source.copy(box).scaled(round(box.width()*factor), round(box.height()*factor),
                                         Qt.KeepAspectRatio, Qt.SmoothTransformation)
            painter = QPainter(canvas)
            painter.drawPixmap((270-p.width())//2, 258-p.height(), p)
            painter.end()
            idle_frames.append(canvas)
        # Preserve public frame indices, but replace every damaged legacy idle.
        frames = [idle_frames[i] for i in [0, 1, 2, 15, 0, 0, 0, 0, 8, 13, 4, 15]]
        for row in range(4):
            for col in range(4):
                x0, x1 = round(col*extra.width()/4), round((col+1)*extra.width()/4)
                y0, y1 = round(row*extra.height()/4), round((row+1)*extra.height()/4)
                frames.append(extra.copy(x0, y0, x1-x0, y1-y0))
        frames.extend(idle_frames)
        return frames

    def _create_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(QIcon(self.frames[0]), self)
        tray.setToolTip(APP_NAME)
        menu = self._build_menu(include_quit=True)
        menu.aboutToShow.connect(lambda: self._refresh_tray(menu))
        menu.aboutToHide.connect(lambda: setattr(self, "menu_open", False))
        tray.setContextMenu(menu)
        tray.activated.connect(self._tray_activated)
        tray.show()
        return tray

    def _refresh_tray(self, menu):
        self.menu_open = True
        self.motion.stop()
        # Rebuild so checkmarks reflect changes made via the pet's own menu.
        fresh = self._build_menu()
        old_actions = menu.actions()
        for action in old_actions:
            menu.removeAction(action)
        for action in fresh.actions():
            if action.menu():
                action.menu().setParent(menu)
            action.setParent(menu)
            menu.addAction(action)
        for action in old_actions:
            action.deleteLater()
        fresh.deleteLater()

    def _build_menu(self, include_quit: bool = True) -> QMenu:
        menu = QMenu(self)

        follow_action = QAction("Biegaj za kursorem", menu)
        follow_action.setCheckable(True)
        follow_action.setChecked(self.following)
        follow_action.triggered.connect(self._toggle_following)
        menu.addAction(follow_action)
        typing = menu.addAction("Patrz na miejsce pisania (bez odczytu tekstu)")
        typing.setCheckable(True)
        typing.setChecked(self.watch_typing)
        typing.triggered.connect(self._toggle_typing)

        size_menu = menu.addMenu("Rozmiar")
        for label, value in (("Mała", 140), ("Normalna", 190), ("Duża", 250)):
            action = QAction(label, size_menu)
            action.setCheckable(True)
            action.setChecked(self.pet_size == value)
            action.triggered.connect(lambda checked=False, size=value: self._set_size(size))
            size_menu.addAction(action)

        speed_menu = menu.addMenu("Szybkość")
        for label, value in (("Spokojna", 0.7), ("Normalna", 1.0), ("Turbo", 1.45)):
            action = QAction(label, speed_menu)
            action.setCheckable(True)
            action.setChecked(abs(self.speed - value) < 0.01)
            action.triggered.connect(lambda checked=False, speed=value: self._set_speed(speed))
            speed_menu.addAction(action)

        menu.addSeparator()
        for label, state in (("Rozejrzyj się", "look"), ("Ziewnij", "yawn"), ("Pobujaj się", "sway"), ("Nieśmiała mina", "shy")):
            menu.addAction(label).triggered.connect(lambda checked=False, s=state: self._play(s, 3.5))
        wave = menu.addAction("Pomachaj 👋")
        wave.triggered.connect(lambda: self._play("wave", 2))
        for label, state in (("Zatańcz", "dance"), ("Przeciągnij się", "stretch"), ("Podskocz", "jump"), ("Usiądź", "sit")):
            menu.addAction(label).triggered.connect(lambda checked=False, s=state: self._play(s, 3))
        menu.addAction("Obudź / wznów").triggered.connect(lambda: self._toggle_following(True))
        sleep = menu.addAction("Idź spać 💤")
        sleep.triggered.connect(self._sleep)

        if sys.platform == "win32":
            startup = QAction("Uruchamiaj z Windowsem", menu)
            startup.setCheckable(True)
            startup.setChecked(self._autostart_enabled())
            startup.triggered.connect(self._set_autostart)
            menu.addAction(startup)

        if include_quit:
            menu.addSeparator()
            quit_action = menu.addAction("Zamknij")
            quit_action.triggered.connect(QApplication.quit)
        return menu

    def _tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.DoubleClick:
            self.show()
            self.raise_()
            self._toggle_following(True)

    def _play(self, state, duration, automatic=False):
        self.auto_reaction = automatic
        self.manual_sleep = False
        self.motion.stop()
        self.state = state
        self.anim_time = 0
        self.reaction_until = time.monotonic() + duration
        self.last_motion = time.monotonic()
        self._animate(0)
        self.update()

    def _toggle_typing(self, enabled):
        self.watch_typing = enabled
        self.caret_point = None
        self.caret_observer.reset()
        self.settings.setValue("watch_typing", enabled)

    def _poll_caret(self, now):
        if not self.watch_typing:
            self.caret_point = None
            return
        if now - self.last_caret_poll >= 0.12:
            self.last_caret_poll = now
            point = to_logical(self.caret_observer.poll(), QApplication.screens())
            self.caret_point = QPoint(round(point[0]), round(point[1])) if point else None

    def _watch_destination(self, caret):
        # Sit below and beside the insertion point, leaving the text line clear.
        screen = QApplication.screenAt(caret) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        x = caret.x() + 24
        y = caret.y() + 30
        if x + self.width() > area.right():
            x = caret.x() - self.width() - 24
        if y + self.height() > area.bottom():
            y = caret.y() - self.height() - 30
        return self._clamped_position(QPoint(x, y))

    def _animate(self, dt):
        self.anim_time += dt
        t = self.anim_time
        clips = {
            "dance": ([24, 25, 26, 27], 0.18),
            "stretch": ([20, 21, 22, 21, 23], 0.42),
            "wave": ([3, 11, 3, 0], 0.32),
            "sit": ([8], 1),
            "sleeping": ([9], 1),
            "jump": ([11], 1),
            "drag": ([10], 1),
            "look": ([28, 32, 33, 32, 28, 31], 0.6),
            "yawn": ([29, 34, 34, 35, 28], 0.65),
            "shy": ([28, 31, 31, 30, 28], 0.55),
            "sway": ([36, 38, 37, 39], 0.55),
            "watch": ([32, 32, 32, 33], 0.8),
            "drowsy": ([36, 40, 37, 40], 0.9),
        }
        if self.state in clips:
            frames, interval = clips[self.state]
            self.frame_index = frames[int(t / interval) % len(frames)]
        elif self.state == "running":
            self.frame_index = 12 + int(self.run_phase) % 8
        else:
            phase = t % 4.3
            self.frame_index = 2 if phase > 4.12 else (0 if phase < 2.1 else 1)

    def _tick(self):
        now = time.monotonic()
        dt = min(max(now - self.last_tick, 0), 0.1)
        self.last_tick = now
        if self.menu_open:
            self.motion.stop()
            return
        if self.drag_offset is not None:
            self.state = "drag"
            self._animate(dt)
            self.update()
            return
        if self.manual_sleep:
            self.state = "sleeping"
            self._animate(dt)
            self.update()
            return
        self._poll_caret(now)
        cursor = QCursor.pos()
        watching = self.following and self.caret_point is not None
        mouse_far = math.hypot(cursor.x() - self.x() - self.width()/2,
                               cursor.y() - self.y() - self.height()/2) > self.pet_size * 0.85
        if self.auto_reaction and (watching or (self.following and mouse_far)):
            self.reaction_until = 0
        if self.reaction_until > now:
            self._animate(dt)
            self.update()
            return

        # Follow a reachable point; at screen edges do not run against a wall.
        desired = (self._watch_destination(self.caret_point) if watching else
                   self._clamped_position(cursor - QPoint(self.width() // 2, self.height() // 2)))
        before_x, before_y = self.motion.x, self.motion.y
        self.motion.step(desired.x(), desired.y(), dt, self.pet_size, self.speed, self.following,
                         stop_radius=4 if watching else None)
        self.float_x, self.float_y = self.motion.x, self.motion.y
        self._apply_float_position()
        distance = math.hypot(self.motion.x - before_x, self.motion.y - before_y)
        moving = distance > 0.02
        if moving:
            if self.state != "running":
                self.run_phase = 0
                self.anim_time = 0
            self.state = "running"
            self.last_motion = now
            self.next_idle_action = now + random.uniform(10, 17)
            if abs(self.motion.vx) > 18:
                self.facing_right = self.motion.vx > 0
            # Footfall cadence follows distance, not a fixed animation timer.
            self.run_phase += distance / (self.pet_size * 0.85) * 8
        else:
            idle_for = now - self.last_motion
            state = ("watch" if watching else "sleeping" if idle_for > 110 else
                     "drowsy" if idle_for > 80 else "sit" if idle_for > 25 else "idle")
            if self.state != state:
                self.anim_time = 0
            self.state = state
            if watching:
                self.facing_right = self.caret_point.x() >= self.x() + self.width()/2
                self.last_motion = now
                self.next_idle_action = now + 8
            if not watching and idle_for < 80 and now >= self.next_idle_action:
                last_motion = self.last_motion
                options = ["stretch", "look", "yawn", "shy", "wave"] if idle_for < 25 else ["sway", "yawn", "look"]
                self._play(random.choice(options), random.uniform(3, 4.2), automatic=True)
                self.last_motion = last_motion
                self.next_idle_action = now + random.uniform(7, 12)
        self._animate(dt)
        self.update()

    def _apply_float_position(self):
        rounded = QPoint(round(self.float_x), round(self.float_y))
        target = self._clamped_position(rounded)
        # Retain fractional position unless the desktop boundary actually clips it.
        if target.x() != rounded.x():
            self.motion.x = self.float_x = float(target.x())
            self.motion.vx = 0
        if target.y() != rounded.y():
            self.motion.y = self.float_y = float(target.y())
            self.motion.vy = 0
        self.move(target)

    def _clamped_position(self, point: QPoint) -> QPoint:
        center = point + QPoint(self.width() // 2, self.height() // 2)
        screen = QApplication.screenAt(center) or QApplication.primaryScreen()
        area = screen.availableGeometry()
        return QPoint(
            max(area.left(), min(point.x(), area.right() - self.width() + 1)),
            max(area.top(), min(point.y(), area.bottom() - self.height() + 1)),
        )

    def paintEvent(self, event) -> None:  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        pixmap = self.frames[self.frame_index]
        if (not self.facing_right and self.state == "running") or (self.facing_right and self.state == "watch"):
            pixmap = self.mirrored[self.frame_index]
        # Small breathing/suspension movements are rendered at floating precision.
        from PySide6.QtCore import QRectF
        t = self.anim_time
        bob = 0.0
        lean = 0.0
        if self.state in ("idle", "sit", "sleeping", "watch", "drowsy"):
            bob = math.sin(t * (2 if self.state == "sleeping" else 3)) * 1.1
        elif self.state == "running":
            lean = max(-4, min(4, self.motion.vx / 110))
        elif self.state == "jump":
            bob = -abs(math.sin(t * math.pi * 2)) * self.height() * 0.14
        elif self.state == "sway":
            lean = math.sin(t * 3) * 3
        painter.translate(self.width() / 2, self.height() * 0.94 + bob)
        painter.rotate(lean)
        target = QRectF(-self.width() * 0.46, -self.height() * 0.9, self.width() * 0.92, self.height() * 0.9)
        painter.drawPixmap(target, pixmap, QRectF(pixmap.rect()))

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self._play("drag", 0.8)
            event.accept()
        elif event.button() == Qt.RightButton:
            self.menu_open = True
            self.motion.stop()
            menu = self._build_menu()
            try:
                menu.exec(event.globalPosition().toPoint())
            finally:
                self.menu_open = False
                menu.deleteLater()

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            position = event.globalPosition().toPoint() - self.drag_offset
            self.move(self._clamped_position(position))
            self.float_x = float(self.x())
            self.float_y = float(self.y())
            self.motion.x, self.motion.y = self.float_x, self.float_y
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.drag_offset = None
            self._play("jump", 0.5)
            self.last_motion = time.monotonic()
            self.settings.setValue("position", self.pos())
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._play("dance", 2.5)

    def _react(self, frame: int, duration: float) -> None:
        self.frame_index = frame
        self.reaction_until = time.monotonic() + duration
        self.update()

    def _sleep(self) -> None:
        self.motion.stop()
        self.manual_sleep = True
        self.frame_index = 9
        self.state = "sleeping"
        self.anim_time = 0
        self.update()

    def _toggle_following(self, enabled: bool) -> None:
        self.following = enabled
        self.manual_sleep = False
        self.motion.stop()
        self.reaction_until = 0.0
        self.last_motion = time.monotonic()
        self.next_idle_action = self.last_motion + 12
        self.settings.setValue("following", enabled)

    def _set_size(self, size: int) -> None:
        center = self.geometry().center()
        self.pet_size = size
        self.setFixedSize(size, size)
        self.move(self._clamped_position(center - QPoint(size // 2, size // 2)))
        self.float_x = float(self.x())
        self.float_y = float(self.y())
        self.settings.setValue("size", size)
        self.motion.x, self.motion.y = self.float_x, self.float_y
        self.motion.stop()

    def _set_speed(self, speed: float) -> None:
        self.speed = speed
        self.settings.setValue("speed", speed)

    @staticmethod
    def _startup_command() -> str:
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'
        return f'"{sys.executable}" "{Path(__file__).resolve()}"'

    def _autostart_enabled(self) -> bool:
        if sys.platform != "win32":
            return False
        import winreg

        try:
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
            ) as key:
                value, _ = winreg.QueryValueEx(key, APP_NAME)
                return value == self._startup_command()
        except OSError:
            return False

    def _set_autostart(self, enabled: bool) -> None:
        if sys.platform != "win32":
            return
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE,
        ) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, self._startup_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.settings.setValue("position", self.pos())
        self.tray.hide()
        event.accept()


def main() -> int:
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setQuitOnLastWindowClosed(False)
    pet = CursorWaifu()
    pet.show()
    pet.raise_()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
