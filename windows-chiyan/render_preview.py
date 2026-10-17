"""Render the real Qt playback into local review images (requires Pillow)."""
import io
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
from PIL import Image
from PyQt5.QtCore import QBuffer, QIODevice, QSettings, Qt
from PyQt5.QtGui import QColor, QPainter, QPixmap
from PyQt5.QtWidgets import QApplication
from app import ACTION_LABELS, ChiyanPet


def pil_frame(pixmap):
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, 'PNG')
    return Image.open(io.BytesIO(bytes(buffer.data()))).convert('RGBA')


def main():
    app = QApplication([])
    root = Path(__file__).resolve().parent
    with tempfile.TemporaryDirectory() as temporary:
        settings = QSettings(str(Path(temporary) / 'preview.ini'), QSettings.IniFormat)
        settings.setValue('paused', True)
        settings.setValue('height', 190)
        pet = ChiyanPet(settings=settings, start_timers=False, show_tray=False)
        states = ('idle', 'hair', 'collar', 'sleep', 'stretch', 'typing', 'peek')
        contact = QPixmap(7 * (pet.width() + 12), pet.height() + 40)
        contact.fill(QColor('#e8e7ed'))
        painter = QPainter(contact)
        painter.setPen(QColor('#25312e'))
        animation = []
        for index, state in enumerate(states):
            pet.play(state)
            duration = 6.6 if state == 'idle' else sum(pet.timings[state]) + .25
            for step in range(round(duration * 15)):
                pet.advance(1 / 15)
                rendered = pet.grab()
                image = pil_frame(rendered)
                background = Image.new('RGBA', image.size, '#e8e7ed')
                background.alpha_composite(image)
                animation.append(background.convert('RGB'))
                if step == round(duration * 15 * .55):
                    painter.drawPixmap(index * (pet.width() + 12) + 6, 30, rendered)
            painter.drawText(index * (pet.width() + 12) + 6, 20, ACTION_LABELS.get(state, '呼吸待机'))
        painter.end()
        contact.save(str(root / 'preview.png'))
        animation[0].save(root / 'motion-preview.gif', save_all=True, append_images=animation[1:],
                          duration=67, loop=0, optimize=True)
        pet.close()
        print(f'Rendered {len(animation)} frames from the real Qt widget')


if __name__ == '__main__':
    main()
