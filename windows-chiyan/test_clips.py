import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import shutil
import tempfile
import unittest
from PyQt5.QtWidgets import QApplication
from clips import load_clips


class ClipAssetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        shutil.copyfile(Path(__file__).parent / 'assets/spritesheet.png', self.root / 'spritesheet.png')

    def tearDown(self):
        self.temp.cleanup()

    def manifest(self, value):
        (self.root / 'actions').mkdir(exist_ok=True)
        (self.root / 'actions/clips.json').write_text(json.dumps(value), encoding='utf-8')

    def test_optional_pack_missing_leaves_core_usable(self):
        frames, timings, looks, warnings = load_clips(self.root, 133, 144)
        self.assertEqual(len(frames['idle']), 6)
        self.assertEqual(len(looks), 16)
        self.assertEqual(warnings, [])

    def test_corrupt_manifest_does_not_break_pet(self):
        (self.root / 'actions').mkdir()
        (self.root / 'actions/clips.json').write_text('{', encoding='utf-8')
        frames, _, _, warnings = load_clips(self.root, 133, 144)
        self.assertIn('idle', frames)
        self.assertEqual(len(warnings), 1)

    def test_missing_frame_is_not_partially_installed(self):
        self.manifest({'hair': {'frames': ['missing.png'], 'durations_ms': [300]}})
        frames, _, _, warnings = load_clips(self.root, 133, 144)
        self.assertNotIn('hair', frames)
        self.assertEqual(len(warnings), 1)

    def test_traversal_and_builtin_override_are_rejected(self):
        self.manifest({'custom': {'frames': ['../spritesheet.png'], 'durations_ms': [100]},
                       'idle': {'frames': [], 'durations_ms': []}})
        frames, _, _, warnings = load_clips(self.root, 133, 144)
        self.assertNotIn('custom', frames)
        self.assertEqual(len(frames['idle']), 6)
        self.assertEqual(len(warnings), 2)

    def test_bad_frame_timings_are_rejected(self):
        self.manifest({'hair': {'frames': ['x.png'], 'durations_ms': [0]}})
        frames, _, _, warnings = load_clips(self.root, 133, 144)
        self.assertNotIn('hair', frames)
        self.assertTrue(warnings)

    def test_overflowing_optional_timing_preserves_core_clips(self):
        self.manifest({'hair': {'frames': ['x.png'], 'durations_ms': [10 ** 400]}})
        frames, _, _, warnings = load_clips(self.root, 133, 144)
        self.assertIn('idle', frames)
        self.assertNotIn('hair', frames)
        self.assertEqual(len(warnings), 1)


if __name__ == '__main__':
    unittest.main()
