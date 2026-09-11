import sys
import unittest
from PySide6.QtCore import QRect
from caret import CaretObserver, to_logical


class Screen:
    def name(self):
        return "DISPLAY2"
    def geometry(self):
        return QRect(-1280, 0, 1280, 720)


class CaretTests(unittest.TestCase):
    def test_negative_monitor_scaled(self):
        sample = (-1920+960, 540, -1920, 0, 1920, 1080, "display2")
        self.assertEqual(to_logical(sample, [Screen()]), (-640, 360))

    def test_unsupported_falls_back(self):
        self.assertIsNone(to_logical(None, [Screen()]))
        self.assertIsNone(to_logical((0,0,0,0,1920,1080,"unknown"), [Screen()]))
        if sys.platform != "win32":
            self.assertIsNone(CaretObserver().poll())

    def test_native_api_smoke(self):
        observer = CaretObserver()
        result = observer.poll()
        self.assertTrue(result is None or len(result) == 7)
        observer.reset()
        self.assertIsNone(observer.previous)


if __name__ == "__main__":
    unittest.main()
