from __future__ import annotations

import math
import os
import random
import sys
import time
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QCursor, QIcon, QPainter, QPixmap, QTransform
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

        self.setWindowTitle(APP_NAME)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setFixedSize(self.pet_size, self.pet_size)

        self.frames = self._load_frames()
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

        self.tray = self._create_tray()
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)
        self.timer.start(TICK_MS)

    def _load_frames(self) -> list[QPixmap]:
        sheet_path = resource_path("assets/waifu_sprites.webp")
        sheet = QPixmap(str(sheet_path))
        if sheet.isNull():
            raise FileNotFoundError(f"Nie znaleziono arkusza animacji: {sheet_path}")

        cell_w = sheet.width() // SPRITE_COLUMNS
        cell_h = sheet.height() // SPRITE_ROWS
        return [
            sheet.copy(col * cell_w, row * cell_h, cell_w, cell_h)
            for row in range(SPRITE_ROWS)
            for col in range(SPRITE_COLUMNS)
        ]

    def _create_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(QIcon(self.frames[0]), self)
        tray.setToolTip(APP_NAME)
        tray.setContextMenu(self._build_menu(include_quit=True))
        tray.activated.connect(self._tray_activated)
        tray.show()
        return tray

    def _build_menu(self, include_quit: bool = True) -> QMenu:
        menu = QMenu(self)

        follow_action = QAction("Biegaj za kursorem", menu)
        follow_action.setCheckable(True)
        follow_action.setChecked(self.following)
        follow_action.triggered.connect(self._toggle_following)
        menu.addAction(follow_action)

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
        wave = menu.addAction("Pomachaj 👋")
        wave.triggered.connect(lambda: self._react(3, 1.6))
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
            self.following = True

    def _tick(self) -> None:
        now = time.monotonic()
        if self.drag_offset is not None:
            return

        if self.reaction_until > now:
            self.update()
            return

        cursor = QCursor.pos()
        center_x = self.float_x + self.width() / 2
        center_y = self.float_y + self.height() / 2
        dx = cursor.x() - center_x
        dy = cursor.y() - center_y
        distance = math.hypot(dx, dy)

        if self.following and distance > self.pet_size * 0.48:
            self.state = "running"
            self.last_motion = now
            self.facing_right = dx >= 0

            acceleration = 0.48 * self.speed
            max_speed = 7.2 * self.speed
            self.velocity_x += (dx / distance) * acceleration
            self.velocity_y += (dy / distance) * acceleration
            velocity = math.hypot(self.velocity_x, self.velocity_y)
            if velocity > max_speed:
                scale = max_speed / velocity
                self.velocity_x *= scale
                self.velocity_y *= scale

            if distance < self.pet_size:
                slow = max(0.25, distance / self.pet_size)
                self.velocity_x *= slow
                self.velocity_y *= slow

            self.float_x += self.velocity_x
            self.float_y += self.velocity_y
            self._apply_float_position()

            if now - self.last_frame_change >= 0.09:
                self.frame_index = 4 + ((self.frame_index - 4 + 1) % 4)
                self.last_frame_change = now
        else:
            self.velocity_x *= 0.72
            self.velocity_y *= 0.72
            idle_for = now - self.last_motion
            if idle_for > 55:
                self.state = "sleeping"
                self.frame_index = 9
            else:
                self.state = "idle"
                interval = 2.2 if self.frame_index != 2 else 0.18
                if now - self.last_frame_change >= interval:
                    if random.random() < 0.22:
                        self.frame_index = 2
                    else:
                        self.frame_index = 1 if self.frame_index == 0 else 0
                    self.last_frame_change = now
        self.update()

    def _apply_float_position(self) -> None:
        target = self._clamped_position(QPoint(round(self.float_x), round(self.float_y)))
        self.float_x = float(target.x())
        self.float_y = float(target.y())
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
        if not self.facing_right and self.frame_index in range(4, 8):
            pixmap = pixmap.transformed(QTransform().scale(-1, 1))
        painter.drawPixmap(QRect(0, 0, self.width(), self.height()), pixmap)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPosition().toPoint() - self.pos()
            self._react(11, 0.8)
            event.accept()
        elif event.button() == Qt.RightButton:
            self._build_menu().exec(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event) -> None:  # type: ignore[override]
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            position = event.globalPosition().toPoint() - self.drag_offset
            self.move(self._clamped_position(position))
            self.float_x = float(self.x())
            self.float_y = float(self.y())
            event.accept()

    def mouseReleaseEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.drag_offset = None
            self.last_motion = time.monotonic()
            self.settings.setValue("position", self.pos())
            event.accept()

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self._react(10, 1.1)

    def _react(self, frame: int, duration: float) -> None:
        self.frame_index = frame
        self.reaction_until = time.monotonic() + duration
        self.update()

    def _sleep(self) -> None:
        self.following = False
        self.settings.setValue("following", False)
        self.frame_index = 9
        self.state = "sleeping"
        self.reaction_until = time.monotonic() + 3600
        self.update()

    def _toggle_following(self, enabled: bool) -> None:
        self.following = enabled
        self.reaction_until = 0.0
        self.last_motion = time.monotonic()
        self.settings.setValue("following", enabled)

    def _set_size(self, size: int) -> None:
        center = self.geometry().center()
        self.pet_size = size
        self.setFixedSize(size, size)
        self.move(self._clamped_position(center - QPoint(size // 2, size // 2)))
        self.float_x = float(self.x())
        self.float_y = float(self.y())
        self.settings.setValue("size", size)

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
