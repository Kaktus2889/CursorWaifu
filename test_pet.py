import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import time
import unittest
from unittest.mock import patch
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication
from app import CursorWaifu


class PetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        QSettings.setDefaultFormat(QSettings.IniFormat)
        QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, cls.tmp.name)
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        checker = patch("app.UpdateChecker.start")
        checker.start()
        self.addCleanup(checker.stop)
        self.pet = CursorWaifu()
        self.pet._toggle_following(True)
        self.pet.timer.stop()

    def test_taskbar_switch_and_turnaround(self):
        p = self.pet
        p._toggle_taskbar(True)
        self.assertTrue(p.taskbar_walk)
        self.assertFalse(p.following)
        now = time.monotonic()
        target = p._patrol_destination(now)
        area = p.screen().availableGeometry()
        self.assertEqual(target.y(), area.bottom() + 1 - p.height())
        direction = p.patrol_right
        p.motion.x, p.motion.y = target.x(), target.y()
        next_target = p._patrol_destination(now)
        self.assertNotEqual(p.patrol_right, direction)
        self.assertGreater(p.patrol_pause_until, now)
        self.assertEqual(next_target.y(), target.y())
        self.assertNotEqual(next_target.x(), target.x())
        p._toggle_following(True)
        self.assertFalse(p.taskbar_walk)
        self.assertTrue(p.following)

    def test_taskbar_resize_recalculates_floor(self):
        p = self.pet
        p._toggle_taskbar(True)
        p._set_size(250)
        target = p._patrol_destination(time.monotonic())
        self.assertEqual(target.y(), p.screen().availableGeometry().bottom() + 1 - 250)

    def tearDown(self):
        self.pet.close()
        self.pet.deleteLater()
        self.app.processEvents()

    def test_frames_and_all_clips_render(self):
        p = self.pet
        self.assertEqual(len(p.frames), 44)
        self.assertTrue(all(not frame.isNull() for frame in p.frames))
        self.assertTrue(p.frames[12].hasAlphaChannel())
        p.show()
        for state in ("idle", "running", "dance", "stretch", "wave", "sit", "sleeping", "jump", "drag", "look", "yawn", "shy", "sway", "watch", "drowsy"):
            p._play(state, 2)
            for _ in range(12):
                p._animate(0.15)
                self.assertIn(p.frame_index, range(44))
                self.assertFalse(p.grab().isNull())

    def test_wake_cancels_manual_sleep(self):
        p = self.pet
        p._sleep()
        p._tick()
        self.assertTrue(p.manual_sleep)
        self.assertEqual(p.frame_index, 9)
        p._toggle_following(True)
        self.assertFalse(p.manual_sleep)
        self.assertEqual(p.reaction_until, 0)

    def test_fractional_position_preserved(self):
        p = self.pet
        p.float_x = p.motion.x = 100.25
        p.float_y = p.motion.y = 100.35
        p._apply_float_position()
        self.assertEqual(p.motion.x, 100.25)
        self.assertEqual(p.motion.y, 100.35)

    def test_sitting_and_sleeping_automatic(self):
        p = self.pet
        p.following = False
        p.last_motion = time.monotonic() - 30
        p._tick()
        self.assertEqual(p.state, "sit")
        p.last_motion = time.monotonic() - 120
        p._tick()
        self.assertEqual(p.state, "sleeping")

    def test_new_idle_frames_have_safe_transparent_margin(self):
        from PySide6.QtGui import QBitmap, QRegion
        for frame in self.pet.frames[28:]:
            box = QRegion(QBitmap.fromImage(frame.toImage().createAlphaMask())).boundingRect()
            self.assertGreaterEqual(box.top(), 15)
            self.assertLess(box.bottom(), frame.height()-9)
            self.assertGreater(box.left(), 0)
            self.assertLess(box.right(), frame.width()-1)

    def test_watch_mode_and_disable(self):
        from PySide6.QtCore import QPoint
        p = self.pet
        p.caret_point = QPoint(300, 200)
        p._poll_caret = lambda now: None
        p.following = True
        target = p._watch_destination(p.caret_point)
        p.motion.x, p.motion.y = target.x(), target.y()
        p.float_x, p.float_y = p.motion.x, p.motion.y
        p._tick()
        self.assertEqual(p.state, "watch")
        self.assertIn(p.frame_index, [32, 33])
        p._toggle_typing(False)
        self.assertIsNone(p.caret_point)

    def test_idle_action_keeps_inactivity_clock(self):
        p = self.pet
        p.following = False
        before = time.monotonic() - 35
        p.last_motion = before
        p.next_idle_action = 0
        p._tick()
        self.assertEqual(p.last_motion, before)
        self.assertTrue(p.auto_reaction)

    def test_resize_and_menu_refresh(self):
        p = self.pet
        p._set_size(250)
        self.assertEqual(p.motion.x, p.x())
        for _ in range(3):
            p._refresh_tray(p.tray.contextMenu())
            self.app.processEvents()
            submenus = [a.menu() for a in p.tray.contextMenu().actions() if a.menu()]
            self.assertEqual(len(submenus), 2)
            self.assertEqual(len(submenus[0].actions()), 3)


if __name__ == "__main__":
    unittest.main()
