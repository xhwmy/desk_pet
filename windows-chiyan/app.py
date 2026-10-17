"""Complete keyframe actions and interactive motion for the independent Chiyan pet."""
import math
import os
import random
import sys
import time
from collections import deque
from PyQt5.QtCore import QPoint, QSettings, Qt, QTimer
from PyQt5.QtGui import QCursor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget
from clips import load_clips
from motion_model import ClipClock, choose_action
from physics import Body, clamp_position, release_velocity, spring_follow, step_throw
from sprite_model import CELL_HEIGHT, CELL_WIDTH, look_frame

ACTION_LABELS = {'hair': '理头发', 'collar': '整理衣领', 'sleep': '抱膝打盹',
                 'stretch': '伸懒腰', 'typing': '敲小键盘', 'peek': '左右探头',
                 'waving': '挥手', 'jumping': '跳跃', 'waiting': '等待', 'review': '认真思考'}
AUTO_WEIGHTS = {'hair': 4, 'collar': 4, 'peek': 4, 'stretch': 2, 'sleep': 1,
                'typing': 2, 'waving': 2, 'jumping': 1, 'walk': 2}


def asset_path(name):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'assets', name)


class ChiyanPet(QWidget):
    def __init__(self, settings=None, start_timers=True, show_tray=True):
        super().__init__()
        self.settings = settings if settings is not None else QSettings('DeskPet', 'ChiyanStandalone')
        self.pet_height = max(90, min(220, self.settings.value('height', 144, type=int)))
        self.paused = self.settings.value('paused', False, type=bool)
        self.reduced_motion = self.settings.value('reduced_motion', False, type=bool)
        self.state, self.previous_action = 'idle', None
        self.previous_frame, self.fade_age = None, .18
        self.squash_age, self.squash_depth = 1., .12
        self.walk_target = self.walk_position = self.flight = None
        self.drag_offset = self.press_position = self.drag_body = self.drag_target = None
        self.dragging = False
        self.trail = deque(maxlen=30)
        self.start_timers = start_timers
        self.load_sprites()
        self.clock = ClipClock(self.timings['idle'], loop=True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle('赤焰桌宠')
        self.resize(self.pet_width, self.pet_height)
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(self.settings.value('x', screen.right() - self.pet_width - 32, type=int),
                  self.settings.value('y', screen.bottom() - self.pet_height - 32, type=int))
        self.keep_on_screen()
        self.click_timer = QTimer(self)
        self.click_timer.setSingleShot(True)
        self.click_timer.timeout.connect(self.click_response)
        self.random_timer = QTimer(self)
        self.random_timer.setSingleShot(True)
        self.random_timer.timeout.connect(self.random_action)
        self.animation = QTimer(self)
        self.animation.setTimerType(Qt.PreciseTimer)
        self.animation.timeout.connect(self.tick)
        self.last_tick = time.monotonic()
        if start_timers:
            self.animation.start(16)
            self.schedule_random()
        self.tray = None
        if show_tray and QSystemTrayIcon.isSystemTrayAvailable():
            self.tray = QSystemTrayIcon(QIcon(self.frames['idle'][0]), self)
            self.tray.setToolTip('赤焰桌宠 · 双击找回')
            self.refresh_tray_menu()
            self.tray.activated.connect(self.tray_activated)
            self.tray.show()
        QApplication.instance().aboutToQuit.connect(self.save_position)
        self.show()

    @property
    def frame_no(self):
        return self.clock.frame

    def load_sprites(self):
        self.pet_width = round(self.pet_height * CELL_WIDTH / CELL_HEIGHT)
        self.frames, self.timings, self.look_frames, self.asset_warnings = load_clips(
            asset_path(''), self.pet_width, self.pet_height)

    def make_menu(self):
        menu = QMenu(self)
        actions = menu.addMenu('动作')
        for state, label in ACTION_LABELS.items():
            if state in self.frames:
                actions.addAction(label, lambda checked=False, name=state: self.play(name))
        builtins = {'idle', 'running-left', 'running-right', 'running', 'failed'}
        for state in self.frames.keys() - ACTION_LABELS.keys() - builtins:
            actions.addAction(state, lambda checked=False, name=state: self.play(name))
        menu.addAction('朝鼠标走来', self.walk_to_cursor)
        menu.addSeparator()
        for label, value, callback in [('暂停自动活动', self.paused, self.set_paused),
                                       ('减少动效', self.reduced_motion, self.set_reduced_motion)]:
            action = menu.addAction(label)
            action.setCheckable(True)
            action.setChecked(value)
            action.triggered.connect(callback)
        sizes = menu.addMenu('大小')
        for label, height in [('小', 110), ('中', 144), ('大', 190)]:
            action = sizes.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.pet_height == height)
            action.triggered.connect(lambda checked=False, value=height: self.set_size(value))
        if self.asset_warnings:
            menu.addAction('部分动作素材未加载', self.show_asset_warnings)
        menu.addAction('移到右下角', self.reset_position)
        menu.addAction('显示桌宠', self.restore)
        menu.addSeparator()
        menu.addAction('退出', QApplication.quit)
        return menu

    def show_asset_warnings(self):
        QMessageBox.warning(self, '赤焰桌宠', '\n'.join(self.asset_warnings))

    def refresh_tray_menu(self):
        if self.tray:
            self.tray.setContextMenu(self.make_menu())

    def cancel_motion(self):
        self.walk_target = self.walk_position = self.flight = None
        self.drag_offset = self.drag_body = None
        self.dragging = False
        self.trail.clear()
        self.click_timer.stop()
        self.keep_on_screen()

    def set_paused(self, paused):
        self.paused = bool(paused)
        self.settings.setValue('paused', self.paused)
        if self.paused:
            self.cancel_motion()
            self._set_clip('idle')
            self.random_timer.stop()
            self.save_position()
        else:
            self.schedule_random()
        self.refresh_tray_menu()

    def set_reduced_motion(self, enabled):
        self.reduced_motion = bool(enabled)
        self.settings.setValue('reduced_motion', self.reduced_motion)
        self.previous_frame, self.squash_age = None, 1.
        self.cancel_motion()
        self._set_clip('idle')
        self.schedule_random()
        self.refresh_tray_menu()

    def set_size(self, height):
        self.cancel_motion()
        feet, center = self.y() + self.height(), self.x() + self.width() / 2
        self.pet_height = max(90, min(220, int(height)))
        self.settings.setValue('height', self.pet_height)
        self.load_sprites()
        self.resize(self.pet_width, self.pet_height)
        self.previous_frame, self.state = None, 'idle'
        self.clock = ClipClock(self.timings['idle'], loop=True)
        self.move(round(center - self.width() / 2), feet - self.height())
        self.keep_on_screen()
        self.save_position()
        if self.tray:
            self.tray.setIcon(QIcon(self.frames['idle'][0]))
        self.refresh_tray_menu()
        self.schedule_random()
        self.update()

    def screen_geometry(self):
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        return screen.availableGeometry()

    def motion_bounds(self):
        rect = self.screen_geometry()
        return (rect.left(), rect.top(), max(rect.left(), rect.right() - self.width() + 1),
                max(rect.top(), rect.bottom() - self.height() + 1))

    def keep_on_screen(self):
        x, y = clamp_position((self.x(), self.y()), self.motion_bounds())
        self.move(round(x), round(y))

    def reset_position(self):
        self.cancel_motion()
        self._set_clip('idle')
        rect = QApplication.primaryScreen().availableGeometry()
        self.move(rect.right() - self.width() - 32, rect.bottom() - self.height() - 32)
        self.keep_on_screen()
        self.save_position()
        self.schedule_random()
        self.restore()

    def save_position(self):
        self.settings.setValue('x', self.x())
        self.settings.setValue('y', self.y())

    def restore(self):
        self.keep_on_screen()
        self.show()
        self.raise_()

    def tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.restore()

    def _set_clip(self, state):
        if state not in self.frames:
            return
        snapshot = self.render_frame() if hasattr(self, 'clock') else None
        self.state = state
        self.clock = ClipClock(self.timings[state], loop=state in ('idle', 'running-left', 'running-right'))
        self.previous_frame = None if self.reduced_motion else snapshot
        self.fade_age = 0.
        self.update()

    def play(self, state, duration_ms=0):
        # Old callers may pass a duration; clips now end at their own final pose.
        if state not in self.frames:
            return
        self.cancel_motion()
        self.random_timer.stop()
        self._set_clip(state)
        if state == 'idle':
            self.schedule_random()

    def start_walk(self, target):
        self.cancel_motion()
        self.random_timer.stop()
        destination = clamp_position((target.x() - self.width() / 2, target.y() - self.height() / 2),
                                     self.motion_bounds())
        self.walk_target = destination
        self.walk_position = (float(self.x()), float(self.y()))
        self._set_clip('running-right' if destination[0] >= self.x() else 'running-left')

    def start_roam(self):
        left, _, right, _ = self.motion_bounds()
        candidates = [x for x in (self.x() - random.randint(60, 180), self.x() + random.randint(60, 180))
                      if left <= x <= right]
        if not candidates:
            self.schedule_random()
            return
        self.start_walk(QPoint(round(random.choice(candidates) + self.width() / 2),
                               round(self.y() + self.height() / 2)))

    def walk_to_cursor(self):
        self.start_walk(QCursor.pos())

    def schedule_random(self):
        if self.start_timers and not self.paused:
            self.random_timer.start(random.randint(12000, 22000))

    def random_action(self):
        if self.paused or self.state != 'idle' or self.drag_offset is not None or self.flight:
            return
        weights = {name: weight for name, weight in AUTO_WEIGHTS.items() if name in self.frames or name == 'walk'}
        if self.reduced_motion:
            weights.pop('walk', None)
            weights.pop('jumping', None)
        selected = choose_action(weights, self.previous_action)
        self.previous_action = selected
        if selected == 'walk':
            self.start_roam()
        elif selected:
            self.play(selected)

    def tick(self):
        now = time.monotonic()
        self.advance(now - self.last_tick)
        self.last_tick = now

    def advance(self, dt):
        dt = max(0, dt)
        self.fade_age += min(.05, dt)
        self.squash_age += min(.05, dt)
        if self.previous_frame is not None and self.fade_age >= .18:
            self.previous_frame = None
        if self.dragging:
            self.drag_body = Body(*self.drag_target) if self.reduced_motion else spring_follow(self.drag_body, self.drag_target, dt)
            self.move(round(self.drag_body.x), round(self.drag_body.y))
        elif self.flight is not None:
            self.flight, impact = step_throw(self.flight, self.motion_bounds(), dt)
            self.move(round(self.flight.x), round(self.flight.y))
            if impact > 90:
                self.start_squash(min(.22, impact / 5000))
            if self.flight.vx == 0 and self.flight.vy == 0:
                self.flight = None
                self.save_position()
                self.schedule_random()
        elif self.walk_target is not None:
            x, y = self.walk_position
            dx, dy = self.walk_target[0] - x, self.walk_target[1] - y
            distance, step = math.hypot(dx, dy), 75 * min(.05, dt)
            if distance <= step:
                self.move(round(self.walk_target[0]), round(self.walk_target[1]))
                self.walk_target = self.walk_position = None
                self.save_position()
                self._set_clip('idle')
                self.schedule_random()
            else:
                self.walk_position = (x + dx / distance * step, y + dy / distance * step)
                self.move(round(self.walk_position[0]), round(self.walk_position[1]))
                before = self.pos()
                self.keep_on_screen()
                if before != self.pos():
                    self.walk_target = self.walk_position = None
                    self._set_clip('idle')
                    self.schedule_random()
        if self.drag_offset is None:
            self.clock.advance(dt)
            if self.clock.finished:
                self._set_clip('idle')
                self.schedule_random()
        self.update()

    def current_frame(self):
        if (self.state == 'idle' and self.previous_frame is None and not self.paused
                and self.drag_offset is None and self.flight is None):
            cursor, center = QCursor.pos(), self.frameGeometry().center()
            dx, dy = cursor.x() - center.x(), cursor.y() - center.y()
            if 30 * 30 < dx * dx + dy * dy < 200 * 200:
                row, col = look_frame(dx, dy)
                return self.look_frames[(row - 9) * 8 + col]
        return self.frames[self.state][self.clock.frame]

    def render_frame(self):
        result = QPixmap(self.size())
        result.fill(Qt.transparent)
        painter = QPainter(result)
        if self.previous_frame is not None:
            amount = min(1, self.fade_age / .18)
            painter.setOpacity(1 - amount)
            painter.drawPixmap(0, 0, self.previous_frame)
            # Preweight the incoming layer: Qt's Plus mode with global opacity
            # blends the destination too, causing repeated fades to lose alpha.
            incoming = QPixmap(self.size())
            incoming.fill(Qt.transparent)
            layer = QPainter(incoming)
            layer.setOpacity(amount)
            layer.drawPixmap(0, 0, self.current_frame())
            layer.end()
            painter.setCompositionMode(QPainter.CompositionMode_Plus)
            painter.setOpacity(1)
            painter.drawPixmap(0, 0, incoming)
        else:
            painter.drawPixmap(0, 0, self.current_frame())
        painter.end()
        return result

    def start_squash(self, depth=.12):
        if not self.reduced_motion:
            self.squash_age, self.squash_depth = 0., depth

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        if not self.reduced_motion and self.squash_age < .26:
            progress = self.squash_age / .26
            amount = self.squash_depth * (1 - progress) * math.sin(progress * 2 * math.pi)
            painter.translate(self.width() / 2, self.height() * 203 / 208)
            painter.scale(1 + amount * .4, 1 - amount)
            painter.translate(-self.width() / 2, -self.height() * 203 / 208)
        painter.drawPixmap(0, 0, self.render_frame())
        painter.end()

    def click_response(self):
        if self.drag_offset is None and self.flight is None:
            self.play('waving')
            self.start_squash()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.cancel_motion()
            self.random_timer.stop()
            self._set_clip('idle')
            self.drag_offset = event.globalPos() - self.pos()
            self.press_position = event.globalPos()
            self.trail.append((time.monotonic(), event.globalX(), event.globalY()))
            event.accept()
        elif event.button() == Qt.RightButton:
            self.click_timer.stop()
            menu = self.make_menu()
            menu.exec_(event.globalPos())
            menu.deleteLater()
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_offset is None or not event.buttons() & Qt.LeftButton:
            return
        self.trail.append((time.monotonic(), event.globalX(), event.globalY()))
        if not self.dragging and (event.globalPos() - self.press_position).manhattanLength() < QApplication.startDragDistance():
            return
        if not self.dragging:
            self.dragging = True
            self.drag_body = Body(self.x(), self.y())
            self.previous_frame = None
        target = event.globalPos() - self.drag_offset
        self.drag_target = (target.x(), target.y())
        event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.LeftButton or self.drag_offset is None:
            return
        dragged = self.dragging
        self.drag_offset, self.dragging = None, False
        if dragged:
            vx, vy = (0, 0) if self.reduced_motion or self.paused else release_velocity(self.trail, time.monotonic())
            if vx or vy:
                self.flight = Body(self.x(), self.y(), vx, vy)
            else:
                # A gentle drop must not stay behind at the spring's lagging position.
                self.move(round(self.drag_target[0]), round(self.drag_target[1]))
                self.keep_on_screen()
                self.save_position()
                self.start_squash(.06)
                self.schedule_random()
        else:
            self.click_timer.start(QApplication.doubleClickInterval())
            self.schedule_random()
        self.trail.clear()
        self.drag_body = None
        event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.play('jumping')
            event.accept()

    def closeEvent(self, event):
        self.animation.stop()
        self.random_timer.stop()
        self.click_timer.stop()
        self.save_position()
        if self.tray:
            self.tray.hide()
        super().closeEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    try:
        pet = ChiyanPet()
    except RuntimeError as error:
        QMessageBox.critical(None, '赤焰桌宠', str(error))
        return 1
    return app.exec_()


if __name__ == '__main__':
    sys.exit(main())
