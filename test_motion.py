import unittest
from math import hypot
from motion import Motion


class MotionTests(unittest.TestCase):
    def test_fps_independence(self):
        positions = []
        for fps in (30, 60, 144):
            m = Motion()
            for _ in range(fps * 2):
                m.step(2000, 0, 1 / fps)
            positions.append(m.x)
        self.assertLess(max(positions) - min(positions), 2)

    def test_arrival_and_no_jitter(self):
        m = Motion()
        for _ in range(1200):
            m.step(650, 0, 1 / 60)
        self.assertAlmostEqual(m.x, 650 - 190 * 0.56, delta=2)
        x = m.x
        for _ in range(120):
            m.step(650 + (_ % 3 - 1) * 3, 0, 1 / 60)
        self.assertAlmostEqual(m.x, x, places=5)
        self.assertEqual(m.vx, 0)

    def test_reverse_and_pause(self):
        m = Motion()
        for _ in range(120):
            m.step(1000, 0, 1 / 60)
        for _ in range(120):
            m.step(-1000, 0, 1 / 60)
        self.assertLess(m.vx, 0)
        for _ in range(60):
            m.step(-1000, 0, 1 / 60, enabled=False)
        self.assertEqual(hypot(m.vx, m.vy), 0)

    def test_tiny_steps_accumulate(self):
        m = Motion()
        for _ in range(100):
            m.step(1000, 0, 0.001)
        self.assertGreater(m.x, 5)

    def test_stall_and_zero_distance(self):
        m = Motion()
        m.step(0, 0, 0)
        m.step(10000, 10000, 30)
        self.assertLess(hypot(m.x, m.y), 50)


if __name__ == "__main__":
    unittest.main()
