import unittest

from sprite_model import CELL_HEIGHT, CELL_WIDTH, FRAME_ROWS, cell_rect, look_frame, step_toward


class SpriteModelTests(unittest.TestCase):
    def test_rows_match_built_in_v2_pet(self):
        self.assertEqual(FRAME_ROWS['idle'], (0, 6))
        self.assertEqual(FRAME_ROWS['running-right'], (1, 8))
        self.assertEqual(FRAME_ROWS['running-left'], (2, 8))
        self.assertEqual(FRAME_ROWS['jumping'], (4, 5))

    def test_cell_rect_for_last_running_frame(self):
        self.assertEqual(cell_rect('running-right', 7), (7 * CELL_WIDTH, CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT))

    def test_look_direction_follows_cursor(self):
        self.assertEqual(look_frame(0, -100), (9, 0))
        self.assertEqual(look_frame(100, 0), (9, 4))
        self.assertEqual(look_frame(0, 100), (10, 0))
        self.assertEqual(look_frame(-100, 0), (10, 4))

    def test_walk_does_not_stall_on_diagonal(self):
        self.assertEqual(step_toward((0, 0), (1, 100), 2), (1, 2))


if __name__ == '__main__':
    unittest.main()
