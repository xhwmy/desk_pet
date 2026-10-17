import unittest

from physics import Body, clamp_position, release_velocity, spring_follow, step_throw


class PhysicsTests(unittest.TestCase):
    def test_spring_moves_toward_pointer_without_overshooting(self):
        body = Body(0, 0)
        for _ in range(120):
            body = spring_follow(body, (100, 50), 1 / 60)
            self.assertLessEqual(body.x, 100.001)
        self.assertAlmostEqual(body.x, 100, places=2)
        self.assertAlmostEqual(body.y, 50, places=2)

    def test_fresh_fast_release_throws(self):
        vx, vy = release_velocity([(1, 0, 0), (1.05, 50, -25), (1.1, 100, -50)], 1.1)
        self.assertGreater(vx, 800)
        self.assertLess(vy, -400)

    def test_stale_or_slow_release_is_a_gentle_drop(self):
        self.assertEqual(release_velocity([(1, 0, 0), (1.1, 100, 0)], 1.4), (0, 0))
        self.assertEqual(release_velocity([(1, 0, 0), (1.1, 10, 0)], 1.1), (0, 0))
        self.assertEqual(release_velocity([(1, 0, 0), (1, 100, 0)], 1), (0, 0))

    def test_throw_bounces_inside_negative_origin_screen(self):
        body, impact = step_throw(Body(-198, 50, -1000, 0), (-200, -100, -100, 100), .05)
        self.assertGreaterEqual(body.x, -200)
        self.assertLessEqual(body.x, -100)
        self.assertGreater(body.vx, 0)

    def test_ground_friction_eventually_settles(self):
        body = Body(50, 0, 700, 0)
        impacts = []
        for _ in range(1200):
            body, impact = step_throw(body, (0, 0, 400, 300), 1 / 120)
            impacts.append(impact)
        self.assertEqual((body.vx, body.vy), (0, 0))
        self.assertEqual(body.y, 300)
        self.assertGreater(max(impacts), 100)

    def test_frame_rates_produce_nearby_positions(self):
        def simulate(dt):
            body = Body(100, 20, 100, 0)
            for _ in range(round(1 / dt)):
                body, _ = step_throw(body, (0, 0, 1000, 2000), dt)
            return body
        slow, fast = simulate(1 / 30), simulate(1 / 120)
        self.assertAlmostEqual(slow.x, fast.x, places=5)
        self.assertAlmostEqual(slow.y, fast.y, places=5)

    def test_long_gap_is_bounded_and_tiny_screen_is_safe(self):
        body, _ = step_throw(Body(5, 5, 500, 0), (0, 0, 1000, 1000), 20)
        self.assertLess(body.x, 40)
        self.assertEqual(clamp_position((20, 30), (0, 0, -10, -10)), (0, 0))


if __name__ == '__main__':
    unittest.main()
