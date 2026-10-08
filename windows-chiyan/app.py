"""Independent Windows companion using the exact Chiyan sprite sheet from Codex."""

import os
import random
import sys
import time

from PyQt5.QtCore import QPoint, QRect, QSettings, Qt, QTimer
from PyQt5.QtGui import QCursor, QIcon, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication, QMenu, QMessageBox, QSystemTrayIcon, QWidget

from sprite_model import CELL_HEIGHT, CELL_WIDTH, COLUMNS, FRAME_ROWS, ROWS, cell_rect, look_frame, step_toward


def asset_path(name):
    base = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'assets', name)


class ChiyanPet(QWidget):
    def __init__(self):
        super().__init__()
        self.settings = QSettings('DeskPet', 'ChiyanStandalone')
        self.pet_height = max(90, min(220, self.settings.value('height', 144, type=int)))
        self.paused = self.settings.value('paused', False, type=bool)
        self.state = 'idle'
        self.frame_no = 0
        self.until = 0.0
        self.walk_target = None
        self.drag_offset = None
        self.load_sprites()
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool | Qt.NoDropShadowWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(self.pet_width, self.pet_height)
        screen = QApplication.primaryScreen().availableGeometry()
        x = self.settings.value('x', screen.right() - self.pet_width - 32, type=int)
        y = self.settings.value('y', screen.bottom() - self.pet_height - 32, type=int)
        self.move(x, y)
        self.keep_on_screen()

        self.tray = QSystemTrayIcon(QIcon(self.frames['idle'][0]), self)
        self.tray.setToolTip('赤焰桌宠 · 双击找回')
        self.tray.setContextMenu(self.make_menu())
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

        self.animation = QTimer(self)
        self.animation.timeout.connect(self.tick)
        self.animation.start(130)
        self.random_timer = QTimer(self)
        self.random_timer.setSingleShot(True)
        self.random_timer.timeout.connect(self.random_action)
        self.schedule_random()
        QApplication.instance().aboutToQuit.connect(self.save_position)
        self.show()

    def load_sprites(self):
        sheet = QPixmap(asset_path('spritesheet.png'))
        if sheet.isNull() or sheet.size().width() != COLUMNS * CELL_WIDTH or sheet.size().height() != ROWS * CELL_HEIGHT:
            raise RuntimeError('赤焰精灵图丢失或尺寸不正确')
        self.pet_width = round(self.pet_height * CELL_WIDTH / CELL_HEIGHT)
        self.frames = {}
        for state, (_, count) in FRAME_ROWS.items():
            self.frames[state] = []
            for index in range(count):
                x, y, w, h = cell_rect(state, index)
                frame = sheet.copy(QRect(x, y, w, h)).scaled(
                    self.pet_width, self.pet_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
                self.frames[state].append(frame)
        self.look_frames = []
        for index in range(16):
            row, col = 9 + index // COLUMNS, index % COLUMNS
            frame = sheet.copy(QRect(col * CELL_WIDTH, row * CELL_HEIGHT, CELL_WIDTH, CELL_HEIGHT)).scaled(
                self.pet_width, self.pet_height, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            self.look_frames.append(frame)

    def make_menu(self):
        menu = QMenu(self)
        menu.addAction('挥手', lambda: self.play('waving', 1100))
        menu.addAction('跳跃', lambda: self.play('jumping', 1100))
        menu.addAction('朝鼠标走来', self.walk_to_cursor)
        menu.addAction('等待', lambda: self.play('waiting', 2400))
        menu.addAction('认真思考', lambda: self.play('review', 2400))
        menu.addSeparator()
        pause = menu.addAction('暂停自动活动')
        pause.setCheckable(True)
        pause.setChecked(self.paused)
        pause.triggered.connect(self.set_paused)
        sizes = menu.addMenu('大小')
        for label, height in [('小', 110), ('中', 144), ('大', 190)]:
            action = sizes.addAction(label)
            action.setCheckable(True)
            action.setChecked(self.pet_height == height)
            action.triggered.connect(lambda checked=False, value=height: self.set_size(value))
        menu.addAction('移到右下角', self.reset_position)
        menu.addAction('显示桌宠', self.restore)
        menu.addSeparator()
        menu.addAction('退出', QApplication.quit)
        return menu

    def refresh_tray_menu(self):
        self.tray.setContextMenu(self.make_menu())

    def set_paused(self, paused):
        self.paused = bool(paused)
        self.settings.setValue('paused', self.paused)
        if self.paused:
            self.random_timer.stop()
            if self.walk_target is not None:
                self.walk_target = None
                self.play('idle')
        else:
            self.schedule_random()
        self.refresh_tray_menu()

    def set_size(self, height):
        self.pet_height = height
        self.settings.setValue('height', height)
        self.load_sprites()
        self.resize(self.pet_width, self.pet_height)
        self.keep_on_screen()
        self.tray.setIcon(QIcon(self.frames['idle'][0]))
        self.refresh_tray_menu()
        self.update()

    def screen_geometry(self):
        screen = QApplication.screenAt(self.frameGeometry().center()) or QApplication.primaryScreen()
        return screen.availableGeometry()

    def keep_on_screen(self):
        rect = self.screen_geometry()
        x = max(rect.left(), min(self.x(), rect.right() - self.width() + 1))
        y = max(rect.top(), min(self.y(), rect.bottom() - self.height() + 1))
        self.move(x, y)

    def reset_position(self):
        rect = QApplication.primaryScreen().availableGeometry()
        self.move(rect.right() - self.width() - 32, rect.bottom() - self.height() - 32)
        self.keep_on_screen()
        self.save_position()
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

    def play(self, state, duration_ms=0):
        self.walk_target = None
        self.state = state
        self.frame_no = 0
        self.until = time.monotonic() + duration_ms / 1000 if duration_ms else 0.0
        self.update()

    def start_walk(self, target):
        rect = self.screen_geometry()
        x = max(rect.left(), min(target.x() - self.width() // 2, rect.right() - self.width() + 1))
        y = max(rect.top(), min(target.y() - self.height() // 2, rect.bottom() - self.height() + 1))
        self.walk_target = (x, y)
        self.state = 'running-right' if x >= self.x() else 'running-left'
        self.frame_no = 0
        self.until = time.monotonic() + 12

    def walk_to_cursor(self):
        self.start_walk(QCursor.pos())

    def schedule_random(self):
        if not self.paused:
            self.random_timer.start(random.randint(8500, 15000))

    def random_action(self):
        if not self.paused and self.state == 'idle' and self.drag_offset is None:
            choice = random.choice(('waving', 'jumping', 'waiting', 'walk'))
            if choice == 'walk':
                rect = self.screen_geometry()
                self.start_walk(QPoint(random.randint(rect.left(), rect.right()),
                                       random.randint(rect.top(), rect.bottom())))
            else:
                self.play(choice, 1100 if choice != 'waiting' else 2400)
        self.schedule_random()

    def tick(self):
        if self.drag_offset is not None:
            return
        if self.walk_target is not None:
            new_position = step_toward((self.x(), self.y()), self.walk_target, 3)
            self.move(*new_position)
            if new_position == self.walk_target or time.monotonic() >= self.until:
                self.save_position()
                self.play('idle')
            else:
                self.frame_no = (self.frame_no + 1) % len(self.frames[self.state])
        elif self.until and time.monotonic() >= self.until:
            self.play('idle')
        elif self.state == 'idle':
            self.frame_no = (self.frame_no + 1) % len(self.frames['idle'])
        else:
            self.frame_no = (self.frame_no + 1) % len(self.frames[self.state])
        self.update()

    def current_frame(self):
        if self.state == 'idle' and not self.paused:
            cursor = QCursor.pos()
            center = self.frameGeometry().center()
            dx, dy = cursor.x() - center.x(), cursor.y() - center.y()
            if 30 < dx * dx + dy * dy < 280 * 280:
                row, col = look_frame(dx, dy)
                return self.look_frames[(row - 9) * COLUMNS + col]
        return self.frames[self.state][self.frame_no]

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        painter.drawPixmap(0, 0, self.current_frame())
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = event.globalPos() - self.pos()
            if self.walk_target is not None:
                self.play('idle')
            event.accept()
        elif event.button() == Qt.RightButton:
            self.make_menu().exec_(event.globalPos())
            event.accept()

    def mouseMoveEvent(self, event):
        if self.drag_offset is not None and event.buttons() & Qt.LeftButton:
            self.move(event.globalPos() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = None
            self.keep_on_screen()
            self.save_position()
            event.accept()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_offset = None
            self.play('jumping', 1100)
            event.accept()


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
