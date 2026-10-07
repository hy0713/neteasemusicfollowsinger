"""Open the real Qt window with the bundled sample and save a screenshot."""

from pathlib import Path
import os
import sys

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtWidgets import QApplication

from followsinger.window import MainWindow


def main():
    app = QApplication([])
    window = MainWindow()
    sample = Path(__file__).resolve().parent.parent / "samples"
    window.mode = "local"
    window.local_path = sample / "practice.wav"
    window.player.setSource(QUrl.fromLocalFile(str(window.local_path)))
    window._read_local_lyrics(sample / "ko.lrc")
    window.audio.setVolume(0)
    window.player.play()
    window.show()

    def check():
        try:
            assert len(window.lines) == 4
            assert len(window.rows) == 4
            assert all(line.translation for line in window.lines)
            assert window.language.currentData() == "ko"
            assert window.player.duration() >= 11000, window.player.duration()
            assert window.player.position() > 300, window.player.position()
            output = Path(__file__).resolve().parent.parent / "output" / "smoke-ui.png"
            output.parent.mkdir(exist_ok=True)
            assert window.grab().save(str(output))
            print(f"Qt window, Korean aid, translations and sample playback: OK; {output}")
        finally:
            window.close()
            app.quit()

    QTimer.singleShot(1600, check)
    app.exec()


if __name__ == "__main__":
    main()
