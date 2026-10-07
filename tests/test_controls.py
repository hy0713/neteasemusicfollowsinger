import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from followsinger.window import MainWindow
from followsinger.themes import THEMES


class ControlsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])
        (Path(__file__).resolve().parents[1] / ".tmp").mkdir(exist_ok=True)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).resolve().parents[1] / ".tmp")
        self.settings = Path(self.temp.name) / "preferences.json"
        self.w = MainWindow(False, self.settings)
        self.w.timer.stop()
        self.w.follower.send = Mock()
        self.w._fetch_lyrics = Mock()
        self.w.show()
        self.app.processEvents()
        self.w._cloud_snapshot(dict(connected=True, canPlay=True, canRate=True, rate=1,
            identity="123", trackId="123", duration=12000, position=2000, timeline=True))

    def tearDown(self):
        self.w.close()
        self.temp.cleanup()

    def test_click_space_and_editor_space(self):
        QTest.mouseClick(self.w.play_button, Qt.MouseButton.LeftButton)
        self.w.follower.send.assert_called_once_with("toggle", 0, "123")
        for widget in (self.w.play_button, self.w.slider, self.w.reading_check):
            self.w.follower.send.reset_mock()
            widget.setFocus()
            QTest.keyClick(widget, Qt.Key.Key_Space)
            self.w.follower.send.assert_called_once_with("toggle", 0, "123")
        self.w.source_panel.show()
        self.w.song_id.setFocus()
        self.w.follower.send.reset_mock()
        QTest.keyClick(self.w.song_id, Qt.Key.Key_Space)
        self.assertEqual(self.w.song_id.text(), " ")
        self.w.follower.send.assert_not_called()

    def test_rate_modes_and_disconnect(self):
        self.w.speed.setValue(.75)
        self.w.follower.send.assert_called_once_with("rate", .75, "123")
        self.w._cloud_snapshot({"connected": False})
        self.assertFalse(self.w.speed.isEnabled())
        self.assertFalse(self.w.play_button.isEnabled())
        self.w._load_sample("ja")
        self.w.speed.setValue(1.25)
        self.assertAlmostEqual(self.w.player.playbackRate(), 1.25)
        self.w._load_sample("fr")
        self.assertAlmostEqual(self.w.player.playbackRate(), 1.25)

    def test_five_themes_persist(self):
        self.assertEqual(self.w.theme_picker.count(), 5)
        for name in THEMES:
            self.w.theme_picker.setCurrentText(name)
            self.assertEqual(self.w.theme_name, name)
        second = MainWindow(False, self.settings)
        self.assertEqual(second.theme_name, "夜间黑")
        second.close()


if __name__ == "__main__":
    unittest.main()
