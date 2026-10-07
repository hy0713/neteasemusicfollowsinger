"""Validate source and frozen builds through the same QApplication."""

import json
from pathlib import Path
import sys

from PySide6.QtCore import QTimer
from PySide6.QtMultimedia import QMediaPlayer

from .pronunciation import LANGUAGES
from .themes import THEMES
from .timeline import FollowClock
from .lyrics import LyricLine, active_index


def run(app, window):
    output = ((Path(sys.executable).parent if getattr(sys, "frozen", False)
               else Path(__file__).resolve().parent.parent) / "output")
    output.mkdir(exist_ok=True)
    results = []
    window._load_sample("ja")
    window.audio.setVolume(0)
    window.player.play()

    def finish():
        failure = ""
        try:
            assert 11500 <= window.player.duration() <= 12500, "示例音频未解码"
            assert window.player.position() > 300, "本地音频未播放"
            results.append("本地音频解码与静音播放")
            clock = FollowClock()
            lines = [LyricLine(0, "Hi"), LyricLine(1000, "Hello")]
            state = dict(connected=True, timeline=True, identity="smoke", transport="direct",
                         position=950, duration=10000, playing=True, rate=1, sample=100)
            clock.update(state, 100)
            indices = [active_index(lines, clock.position(100.1))]
            clock.update({**state, "sample": 100.25}, 100.25)
            indices.append(active_index(lines, clock.position(100.25)))
            assert indices == [1, 1], "重复客户端进度导致歌词退回上一句"
            results.append("远端重复进度不回退歌词")
            window.player.pause()
            for code in LANGUAGES:
                window._load_sample(code)
                app.processEvents()
                assert len(window.rows) == 4
                assert all(row.annotation.text() and row.translation.text() for row in window.rows)
                assert window._language_code() == code
                results.append(f"{code} 读音、译文与界面")
                assert not window.beginner_check.isChecked()
                assert all(row.beginner.isHidden() for row in window.rows)
                window.beginner_check.setChecked(True)
                app.processEvents()
                assert all(row.beginner.text() and not row.beginner.isHidden() for row in window.rows)
                assert all("失败" not in row.beginner.text() for row in window.rows)
                if code == "fr":
                    window.grab().save(str(output / "preview-french-beginner.png"))
                window.beginner_check.setChecked(False)
            results.append("五语新手模式、默认关闭及原读音保留")
            window._load_sample("ja")
            window.resize(1280, 840)
            app.processEvents()
            window._resize_rows()
            window.grab().save(str(output / "preview-japanese.png"))
            window.reading_check.setChecked(False)
            assert all(row.annotation.isHidden() for row in window.rows)
            window.reading_check.setChecked(True)
            window.translation_check.setChecked(False)
            assert all(row.translation.isHidden() for row in window.rows)
            window.translation_check.setChecked(True)
            results.append("读音与译文显示开关")
            original_theme = window.theme_name
            for number, name in enumerate(THEMES):
                window.theme_picker.setCurrentText(name)
                app.processEvents()
                window.grab().save(str(output / f"theme-{number}.png"))
            window.theme_picker.setCurrentText(original_theme)
            results.append("五种皮肤切换与截图")
            window.speed.setValue(.75)
            assert abs(window.player.playbackRate() - .75) < .01
            window._load_sample("ja")
            assert abs(window.player.playbackRate() - .75) < .01
            results.append("本地倍速及切换音频后保持")
            window.resize(960, 700)
            app.processEvents()
            window._resize_rows()
            assert window.centralWidget().width() <= 960, "最小窗口溢出"
            window.grab().save(str(output / "preview-compact.png"))
            results.append("960×700 紧凑布局")
        except Exception as exc:
            failure = str(exc)
        (output / "smoke-result.json").write_text(json.dumps(
            {"passed": not failure, "checks": results, "error": failure,
             "frozen": bool(getattr(sys, "frozen", False))}, ensure_ascii=False, indent=2), encoding="utf-8")
        window.close()
        app.exit(1 if failure else 0)

    QTimer.singleShot(1800, finish)
