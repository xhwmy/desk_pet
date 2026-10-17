import random
import unittest

from motion_model import ClipClock, choose_action


class PlaybackTests(unittest.TestCase):
    def test_uneven_timings_preserve_long_neutral_pose(self):
        clock = ClipClock([1.68, .66, .66, .84, .84, 1.92], loop=True)
        for _ in range(100):
            clock.advance(.016)
        self.assertEqual(clock.frame, 0)
        clock.advance(.1)
        self.assertEqual(clock.frame, 1)

    def test_action_holds_last_frame_then_signals_completion(self):
        clock = ClipClock([.1, .2, .3])
        clock.advance(.1)
        clock.advance(.2)
        self.assertEqual(clock.frame, 2)
        self.assertFalse(clock.finished)
        clock.advance(.25)
        self.assertFalse(clock.finished)
        clock.advance(.05)
        self.assertTrue(clock.finished)
        self.assertEqual(clock.frame, 2)

    def test_timer_gap_does_not_skip_entire_manual_action(self):
        clock = ClipClock([.2, .2, .2])
        clock.advance(10)
        self.assertFalse(clock.finished)
        self.assertEqual(clock.frame, 1)

    def test_loop_wraps_after_whole_cycle(self):
        clock = ClipClock([.1, .1], loop=True)
        clock.advance(.2)
        self.assertEqual(clock.frame, 0)
        self.assertFalse(clock.finished)

    def test_invalid_frame_duration_is_rejected(self):
        for timings in ([], [0], [-1], [float('nan')]):
            with self.subTest(timings=timings), self.assertRaises(ValueError):
                ClipClock(timings)

    def test_negative_elapsed_does_not_rewind(self):
        clock = ClipClock([.2, .2])
        clock.advance(-2)
        self.assertEqual(clock.frame, 0)


class SelectionTests(unittest.TestCase):
    def test_previous_action_is_not_selected_when_alternative_exists(self):
        rng = random.Random(7)
        previous = None
        for _ in range(100):
            selected = choose_action({'hair': 5, 'collar': 3, 'walk': 1}, previous, rng)
            self.assertNotEqual(selected, previous)
            previous = selected

    def test_empty_or_disabled_pool_returns_none(self):
        self.assertIsNone(choose_action({'walk': 0}, None, random.Random(1)))

    def test_single_action_can_repeat(self):
        self.assertEqual(choose_action({'hair': 1}, 'hair', random.Random(1)), 'hair')

    def test_weight_influences_choice(self):
        rng = random.Random(0)
        picks = [choose_action({'hair': 9, 'walk': 1}, None, rng) for _ in range(1000)]
        self.assertGreater(picks.count('hair'), 850)
        self.assertLess(picks.count('hair'), 950)


if __name__ == '__main__':
    unittest.main()
