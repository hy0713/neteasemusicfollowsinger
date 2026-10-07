from __future__ import annotations

import sys
from pathlib import Path
import logging
from logging.handlers import RotatingFileHandler

from PySide6.QtWidgets import QApplication

from followsinger.window import MainWindow


def main() -> int:
    location = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
    logs = location / "data" / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, handlers=[RotatingFileHandler(
        logs / "followsinger.log", maxBytes=1_000_000, backupCount=2, encoding="utf-8")])
    app = QApplication(sys.argv)
    smoke = "--smoke-test" in sys.argv
    window = MainWindow(start_follower=not smoke)
    window.show()
    if smoke:
        from followsinger.smoke import run
        run(app, window)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
