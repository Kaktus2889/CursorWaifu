import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
import tempfile
import time
import unittest
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
        self.pet = CursorWaifu()
        self.pet.timer.stop()

    def tearDown(self):
        self.pet.close()
        self.pet.deleteLater()
        self.app.processEvents()

    def test_frames_and_all_clips_render(self):
        p = self.pet
        self.assertEqual(len(p.frames), 28)
        self.assertTrue(all(not frame.isNull() for frame in p.frames))
        self.assertTrue(p.frames[12].hasAlphaChannel())
        p.show()
        for state in ("idle", "running", "dance", "stretch", "wave", "sit", "sleeping", "jump", "drag"):
            p._play(state, 2)
            for _ in range(12):
                p._animate(0.15)
                self.assertIn(p.frame_index, range(28))
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
        p.last_motion = time.monotonic() - 60
        p._tick()
        self.assertEqual(p.state, "sleeping")

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
