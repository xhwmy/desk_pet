"""Exercise the real Qt widget with isolated preferences and event input."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import tempfile
import unittest

from PyQt5.QtCore import QPoint, QPointF, QSettings, Qt
from PyQt5.QtGui import QMouseEvent
from PyQt5.QtTest import QTest
from PyQt5.QtWidgets import QApplication

from app import ChiyanPet
from physics import Body


class PetInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        cls.app.setQuitOnLastWindowClosed(False)
        cls.temp = tempfile.TemporaryDirectory()

    def setUp(self):
        self.settings = QSettings(os.path.join(self.temp.name, self.id() + '.ini'), QSettings.IniFormat)
        self.pet = ChiyanPet(settings=self.settings, start_timers=False, show_tray=False)

    def tearDown(self):
        self.pet.close()
        self.app.processEvents()

    def advance(self, seconds):
        for _ in range(round(seconds / .02)):
            self.pet.advance(.02)

    def test_all_six_actions_load_and_play_to_completion(self):
        for action in ('hair', 'collar', 'sleep', 'stretch', 'typing', 'peek'):
            with self.subTest(action=action):
                self.pet.play(action)
                self.assertEqual(self.pet.state, action)
                self.assertGreaterEqual(len(self.pet.frames[action]), 6)
                self.advance(10)
                self.assertEqual(self.pet.state, 'idle')

    def test_click_waits_for_double_click_window(self):
        QTest.mouseClick(self.pet, Qt.LeftButton, pos=QPoint(50, 60))
        self.assertEqual(self.pet.state, 'idle')
        QTest.qWait(QApplication.doubleClickInterval() + 30)
        self.assertEqual(self.pet.state, 'waving')

    def test_double_click_jumps_without_delayed_wave(self):
        QTest.mouseClick(self.pet, Qt.LeftButton, pos=QPoint(50, 60))
        QTest.mouseDClick(self.pet, Qt.LeftButton, pos=QPoint(50, 60))
        QTest.qWait(QApplication.doubleClickInterval() + 30)
        self.assertEqual(self.pet.state, 'jumping')

    def test_drag_interrupts_action_and_does_not_queue_wave(self):
        self.pet.play('typing')
        QTest.mousePress(self.pet, Qt.LeftButton, pos=QPoint(40, 60))
        local = QPointF(70, 60)
        event = QMouseEvent(QMouseEvent.MouseMove, local, QPointF(self.pet.mapToGlobal(QPoint(70, 60))),
                            Qt.NoButton, Qt.LeftButton, Qt.NoModifier)
        QApplication.sendEvent(self.pet, event)
        self.assertTrue(self.pet.dragging)
        QTest.mouseRelease(self.pet, Qt.LeftButton, pos=QPoint(70, 60))
        self.assertFalse(self.pet.click_timer.isActive())
        self.assertIsNone(self.pet.drag_offset)

    def test_pausing_freezes_flight_and_keeps_manual_actions(self):
        self.pet.flight = Body(self.pet.x(), self.pet.y(), 600, -300)
        self.pet.set_paused(True)
        position = self.pet.pos()
        self.advance(1)
        self.assertEqual(self.pet.pos(), position)
        self.assertIsNone(self.pet.flight)
        self.pet.play('hair')
        self.assertEqual(self.pet.state, 'hair')

    def test_pause_during_offscreen_drag_keeps_pet_reachable(self):
        self.pet.move(-10000, -10000)
        self.pet.dragging = True
        self.pet.drag_offset = QPoint(40, 60)
        self.pet.set_paused(True)
        bounds = self.pet.motion_bounds()
        self.assertGreaterEqual(self.pet.x(), bounds[0])
        self.assertGreaterEqual(self.pet.y(), bounds[1])

    def test_custom_loaded_action_appears_in_menu(self):
        self.pet.frames['custom-action'] = self.pet.frames['hair']
        self.pet.timings['custom-action'] = self.pet.timings['hair']
        menu = self.pet.make_menu()
        actions = menu.actions()[0].menu().actions()
        self.assertIn('custom-action', [action.text() for action in actions])
        menu.deleteLater()

    def test_native_window_has_a_discoverable_title(self):
        self.assertTrue(self.pet.windowTitle())

    def test_resize_and_reset_cancel_flight_and_pending_click(self):
        self.pet.flight = Body(self.pet.x(), self.pet.y(), 600, -300)
        self.pet.click_timer.start(100)
        self.pet.set_size(190)
        self.assertIsNone(self.pet.flight)
        self.assertFalse(self.pet.click_timer.isActive())
        self.pet.flight = Body(self.pet.x(), self.pet.y(), 600, -300)
        self.pet.reset_position()
        self.assertIsNone(self.pet.flight)

    def test_short_roaming_is_horizontal_and_remains_on_screen(self):
        start = self.pet.pos()
        self.pet.start_roam()
        if self.pet.walk_target:
            self.assertEqual(self.pet.walk_target[1], start.y())
            self.assertLessEqual(abs(self.pet.walk_target[0] - start.x()), 180)
        self.advance(8)
        self.assertIsNone(self.pet.walk_target)
        bounds = self.pet.motion_bounds()
        self.assertGreaterEqual(self.pet.x(), bounds[0])
        self.assertLessEqual(self.pet.x(), bounds[2])

    def test_rapid_switches_render_without_blank_frames(self):
        for action in ('hair', 'sleep', 'stretch', 'typing', 'idle'):
            self.pet.play(action)
            self.pet.advance(.016)
            image = self.pet.grab().toImage()
            self.assertFalse(image.isNull())
            self.assertTrue(any(image.pixelColor(x, image.height() // 2).alpha() for x in range(image.width())))

    def test_reduced_motion_disables_fade_and_throw(self):
        self.pet.set_reduced_motion(True)
        self.pet.play('hair')
        self.assertIsNone(self.pet.previous_frame)
        self.assertTrue(self.settings.value('reduced_motion', type=bool))

    def test_gentle_drop_uses_pointer_target_instead_of_spring_lag(self):
        self.pet.move(50, 50)
        QTest.mousePress(self.pet, Qt.LeftButton, pos=QPoint(40, 60))
        self.pet.dragging = True
        self.pet.drag_target = (150, 150)
        self.pet.drag_body = Body(60, 60)
        self.pet.trail.clear()
        QTest.mouseRelease(self.pet, Qt.LeftButton, pos=QPoint(40, 60))
        self.assertEqual(self.pet.pos(), QPoint(150, 150))
        self.assertIsNone(self.pet.flight)

    def test_flight_settles_then_resumes_idle_activity(self):
        self.pet.flight = Body(self.pet.x(), self.pet.y(), 600, -300)
        self.advance(15)
        self.assertIsNone(self.pet.flight)
        self.assertEqual(self.pet.state, 'idle')

    def test_repeated_interruption_keeps_pet_opaque(self):
        self.pet.set_paused(True)
        for _ in range(50):
            self.pet.play('hair')
            self.pet.advance(.016)
        image = self.pet.render_frame().toImage()
        self.assertGreater(image.pixelColor(image.width() // 2, image.height() // 2).alpha(), 230)


if __name__ == '__main__':
    unittest.main()
