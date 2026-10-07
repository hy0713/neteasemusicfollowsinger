"""PySide6 desktop UI for local practice and NetEase following."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import subprocess
import sys
import time
import json

from PySide6.QtCore import QObject, Qt, QTimer, QUrl, Signal, QEvent
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFrame, QHBoxLayout,
    QLabel, QInputDialog, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QSlider, QVBoxLayout, QWidget, QApplication, QAbstractSpinBox, QTextEdit, QPlainTextEdit,
)

from .design import LyricRow, build_ui, apply_style, app_icon, artwork
from .lyrics import LyricLine, active_index, attach_translations, parse_lrc, read_text
from .media import CloudFollower
from .netease import NeteaseLyrics, song_id_from_input
from .pronunciation import LANGUAGES, detect_language, reading
from .themes import THEMES
from .beginner import beginner_reading
from .timeline import FollowClock


class BackgroundResults(QObject):
    finished = Signal(int, object, str, str)
    artwork_ready = Signal(int, bytes, str)




class MainWindow(QMainWindow):
    def __init__(self, start_follower=True, settings_path=None):
        super().__init__()
        self.setWindowTitle("跟唱伴学 · FollowSinger")
        self.resize(1280, 840)
        self.setMinimumSize(960, 700)
        self.root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
        self.settings_path = Path(settings_path) if settings_path else ((Path(sys.executable).parent if getattr(sys, "frozen", False) else self.root) / "data" / "preferences.json")
        try:
            saved = json.loads(self.settings_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            saved = {}
        self.theme_name = saved.get("theme", "经典白")
        if self.theme_name not in THEMES:
            self.theme_name = "经典白"
        self.local_rate = 1.0
        self.has_album_cover = False
        self.rate_pending = None
        self.problem_until = 0.0
        self.mode = "cloud"
        self.detected_language = "ja"
        self.local_path: Path | None = None
        self.lines: list[LyricLine] = []
        self.rows: list[LyricRow] = []
        self.active = -1
        self.snapshot: dict = {}
        self.cloud_clock = FollowClock()
        self.track_identity = ""
        self.generation = 0
        self.loop_last_seek = 0.0
        self.loop_index = -1
        self.dragging = False
        self.source = ""
        self.service = NeteaseLyrics()
        self.pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="lyric-search")
        self.background = BackgroundResults()
        self.background.finished.connect(self._lyrics_loaded)
        self.background.artwork_ready.connect(self._cover_loaded)

        self.audio = QAudioOutput()
        self.audio.setVolume(.75)
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio)
        self.player.positionChanged.connect(self._local_position)
        self.player.durationChanged.connect(lambda _: self._update_timeline())
        self.player.playbackStateChanged.connect(lambda _: self._update_play_button())
        self.player.errorOccurred.connect(lambda _error, message: self._set_status(f"本地播放失败：{message}"))

        self._build_ui()
        self._set_style()
        self.setWindowIcon(QIcon(app_icon()))
        self.follower = CloudFollower()
        self.follower.snapshot.connect(self._cloud_snapshot)
        self.follower.problem.connect(self._cloud_problem)
        if start_follower:
            self.follower.start()
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self._tick)
        self.timer.start()
        self._set_status("等待网易云播放；也可打开本地音频。")
        QApplication.instance().installEventFilter(self)
        self._update_play_button()

    def _change_theme(self, name):
        if name not in THEMES:
            return
        self.theme_name = name
        self._set_style()
        self.brand_logo.setPixmap(app_icon(36, name))
        self.empty_logo.setPixmap(app_icon(64, name))
        self.setWindowIcon(QIcon(app_icon(256, name)))
        if not self.has_album_cover:
            self.cover.setPixmap(artwork(170, name))
        try:
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix(".tmp")
            temporary.write_text(json.dumps({"theme": name}, ensure_ascii=False), encoding="utf-8")
            temporary.replace(self.settings_path)
        except OSError:
            self._set_status("皮肤已切换，但设置无法保存。")

    def eventFilter(self, obj, event):
        if event.type() in (QEvent.Type.ShortcutOverride, QEvent.Type.KeyPress, QEvent.Type.KeyRelease) and event.key() == Qt.Key.Key_Space and event.modifiers() == Qt.KeyboardModifier.NoModifier:
            if isinstance(obj, QWidget) and obj.window() is self and not QApplication.activeModalWidget() and not QApplication.activePopupWidget():
                focus = QApplication.focusWidget()
                if not isinstance(focus, (QLineEdit, QTextEdit, QPlainTextEdit, QAbstractSpinBox)):
                    event.accept()
                    if event.type() == QEvent.Type.KeyPress and not event.isAutoRepeat():
                        self._toggle()
                    return True
        return super().eventFilter(obj, event)

    def _change_speed(self, value):
        if self.mode == "local":
            self.local_rate = value
            self.player.setPlaybackRate(value)
        elif self.snapshot.get("connected") and self.snapshot.get("canRate"):
            self.rate_pending = (value, time.monotonic())
            self.follower.send("rate", value, self.snapshot.get("identity", ""))

    def _update_speed(self):
        local = self.mode == "local"
        capable = local or bool(self.snapshot.get("connected") and self.snapshot.get("canRate"))
        self.speed.setEnabled(capable)
        self.speed.setToolTip("本地音频倍速" if local else ("网易云客户端倍速" if capable else "当前网易云通道不支持倍速，请连接客户端直连或打开本地音频"))
        value = self.local_rate if local else float(self.snapshot.get("rate") or 1)
        if self.rate_pending and not local:
            requested, sent = self.rate_pending
            if abs(value - requested) < .01 or time.monotonic() - sent > 2:
                self.rate_pending = None
            else:
                return
        self.speed.blockSignals(True)
        self.speed.setValue(value)
        self.speed.blockSignals(False)

    def _build_ui(self):
        build_ui(self)

    def _set_style(self):
        apply_style(self)

    def _set_status(self, message: str):
        self.status.setText(message)
        self.status.setToolTip(message)

    def _cloud_problem(self, message: str):
        if self.mode == "cloud":
            self.cloud_clock.cancel_seek()
            self.rate_pending = None
            self.problem_until = time.monotonic() + 3
            self._update_speed()
            self._set_status(message)

    def _update_mode(self):
        self.rate_pending = None
        self._update_speed()
        self.follow_button.setChecked(self.mode == "cloud")
        self.local_button.setChecked(self.mode == "local")
        if self.mode == "local":
            self.has_album_cover = False
            self.cover.setPixmap(artwork(170, self.theme_name))
            self.connection.setText("●  本地音频 · 精细练唱")

    def _open_audio(self):
        path, _ = QFileDialog.getOpenFileName(self, "打开本地音频", str(self.root),
            "音频 (*.mp3 *.flac *.wav *.m4a *.ogg *.opus *.aac *.wma);;所有文件 (*)")
        if not path:
            return
        self.mode = "local"
        self._update_mode()
        self.local_path = Path(path)
        self.generation += 1
        self.track_identity = str(self.local_path)
        self.title.setText(self.local_path.stem)
        self.artist.setText("本地练唱")
        self.speed.setEnabled(True)
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.setPlaybackRate(self.speed.value())
        lyrics_path = self.local_path.with_suffix(".lrc")
        if lyrics_path.exists():
            self._read_local_lyrics(lyrics_path)
        else:
            self._set_lines([], "")
            self._set_status("音频已打开。请选择“导入 LRC”或输入网易云歌曲 ID。")
        self._update_timeline()
        self._update_play_button()

    def _open_sample(self):
        names = [name for name, _ in LANGUAGES.values()]
        selected, accepted = QInputDialog.getItem(self, "体验示例", "选择语言", names, 0, False)
        if not accepted:
            return
        code = list(LANGUAGES)[names.index(selected)]
        self._load_sample(code)

    def _load_sample(self, code: str):
        selected = LANGUAGES[code][0]
        sample_dir = self.root / "samples"
        audio_path = sample_dir / "practice.wav"
        self.mode = "local"
        self._update_mode()
        self.local_path = audio_path
        self.generation += 1
        self.track_identity = str(audio_path)
        self.title.setText(f"{selected}跟唱示例")
        self.artist.setText("原创短句 · 合成提示音（无人声）")
        self.speed.setEnabled(True)
        self.player.setSource(QUrl.fromLocalFile(str(audio_path)))
        self.player.setPlaybackRate(self.local_rate)
        self.language.blockSignals(True)
        self.language.setCurrentIndex(0)
        self.language.blockSignals(False)
        self._read_local_lyrics(sample_dir / f"{code}.lrc")
        self.detected_language = code
        self._render_lines()
        self._update_timeline()
        self._update_play_button()

    def _read_local_lyrics(self, path: Path):
        try:
            lines = parse_lrc(read_text(path))
            for suffix in (".zh.lrc", ".trans.lrc"):
                translated = path.with_name(path.stem + suffix)
                if translated.exists():
                    lines = attach_translations(lines, parse_lrc(read_text(translated)))
                    break
            if not lines:
                raise ValueError("LRC 没有可用的时间标签歌词")
            self._set_lines(lines, str(path))
            self._set_status(f"已加载本地歌词：{path.name}")
        except (OSError, ValueError) as exc:
            self._set_status(str(exc))

    def _import_lrc(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入原文 LRC", str(self.root), "LRC 歌词 (*.lrc)")
        if path:
            self._read_local_lyrics(Path(path))

    def _import_translation(self):
        if not self.lines:
            self._set_status("请先加载原文歌词。")
            return
        path, _ = QFileDialog.getOpenFileName(self, "导入中文译文 LRC", str(self.root), "LRC 歌词 (*.lrc)")
        if not path:
            return
        try:
            original = [LyricLine(line.time_ms, line.text) for line in self.lines]
            self.lines = attach_translations(original, parse_lrc(read_text(Path(path))))
            self._render_lines()
            self._set_status(f"已导入译文：{Path(path).name}")
        except (OSError, ValueError) as exc:
            self._set_status(str(exc))

    def _follow_cloud(self):
        self.mode = "cloud"
        self._update_mode()
        self.player.pause()
        self._update_speed()
        if self.snapshot.get("connected"):
            self._cloud_snapshot(self.snapshot, force=True)
        else:
            self._set_status("正在等待网易云播放会话。")
        self._update_timeline()

        self._update_play_button()

    def _launch_direct(self):
        answer = QMessageBox.question(self, "启动网易云直连",
            "请先从托盘完整退出网易云音乐。程序随后会用本机 127.0.0.1:9222 调试端口启动客户端。\n\n已退出并继续？")
        if answer != QMessageBox.StandardButton.Yes:
            return
        exe, _ = QFileDialog.getOpenFileName(self, "选择 cloudmusic.exe", "C:/Program Files/NetEase/CloudMusic",
                                             "网易云客户端 (cloudmusic.exe)")
        if not exe:
            return
        chosen = Path(exe)
        if chosen.name.lower() != "cloudmusic.exe":
            self._set_status("请选择 cloudmusic.exe。")
            return
        try:
            subprocess.Popen([str(chosen), "--remote-debugging-port=9222",
                              "--remote-debugging-address=127.0.0.1"], cwd=str(chosen.parent))
            self._set_status("网易云已启动；播放歌曲后等待显示“客户端直连”。")
        except OSError as exc:
            self._set_status(f"启动失败：{exc}")

    def _cloud_snapshot(self, data: dict, force: bool = False):
        if self.mode != "cloud":
            self.snapshot = data
            return
        if force:
            self.cloud_clock.reset()
        if not self.cloud_clock.update(data):
            return
        self.snapshot = data
        self._update_speed()
        if not data.get("connected"):
            self.connection.setText("●  等待网易云连接")
            self._set_status(data.get("message", "网易云未连接"))
            self._update_timeline()
            self._update_play_button()
            return
        identity = data.get("identity", "")
        if force or identity != self.track_identity:
            self.has_album_cover = False
            self.cover.setPixmap(artwork(170, self.theme_name))
            self.track_identity = identity
            self.generation += 1
            self.title.setText(data.get("title") or "未知歌曲")
            self.artist.setText(data.get("artist") or "未知歌手")
            self._set_lines([], "")
            if data.get("trackId"):
                self._fetch_lyrics(str(data["trackId"]), self.generation, self.track_identity)
            elif data.get("title"):
                self._identify_and_fetch(data, self.generation, self.track_identity)
        channel = "客户端直连" if data.get("transport") == "direct" else "Windows 媒体会话"
        self.connection.setText(f"●  {channel}")
        limit = "双向进度可用" if data.get("timeline") and data.get("canSeek") else "当前版本未提供可用时间轴"
        if time.monotonic() >= self.problem_until:
            self._set_status(f"{channel} · {limit}" + (f" · 歌词：{self.source}" if self.source else ""))
        self._update_timeline()
        self._update_play_button()

    def _identify_and_fetch(self, data: dict, generation: int, identity: str):
        def task():
            song_id = self.service.identify(data.get("title", ""), data.get("artist", ""),
                                            int(data.get("duration") or 0))
            if not song_id:
                raise ValueError("未能可靠匹配歌曲，请输入网易云歌曲 ID 或导入 LRC。")
            return song_id, self.service.lyrics(song_id)
        self._submit(task, generation, identity)

    def _fetch_lyrics(self, song_id: str, generation: int, identity: str):
        self._submit(lambda: (song_id, self.service.lyrics(song_id)), generation, identity)

    def _load_id(self):
        try:
            song_id = song_id_from_input(self.song_id.text())
        except ValueError as exc:
            self._set_status(str(exc))
            return
        self._fetch_lyrics(song_id, self.generation, self.track_identity)
        self._set_status(f"正在获取歌曲 {song_id} 的歌词…")

    def _submit(self, task, generation: int, identity: str):
        future = self.pool.submit(task)
        def done(result):
            try:
                song_id, lines = result.result()
                self.background.finished.emit(generation, lines, song_id, identity)
            except Exception as exc:
                self.background.finished.emit(generation, None, str(exc), identity)
        future.add_done_callback(done)

    def _lyrics_loaded(self, generation: int, lines, detail: str, identity: str):
        if generation != self.generation or identity != self.track_identity:
            return
        if lines is None:
            self._set_status(f"歌词获取失败：{detail}")
            return
        self.song_id.setText(detail)
        self._set_lines(lines, f"网易云 {detail}")
        self._set_status(f"已加载 {len(lines)} 行歌词 · 网易云 {detail}")
        if self.mode == "cloud":
            future = self.pool.submit(self.service.cover, detail)
            def done(result):
                try:
                    self.background.artwork_ready.emit(generation, result.result(), identity)
                except Exception:
                    pass
            future.add_done_callback(done)

    def _cover_loaded(self, generation: int, content: bytes, identity: str):
        if generation != self.generation or identity != self.track_identity:
            return
        pixmap = QPixmap()
        if pixmap.loadFromData(content):
            self.has_album_cover = True
            self.cover.setPixmap(pixmap.scaled(170, 170, Qt.AspectRatioMode.KeepAspectRatio,
                                               Qt.TransformationMode.SmoothTransformation))

    def _set_lines(self, lines: list[LyricLine], source: str):
        self.lines = lines
        self.source = source
        self.active = -1
        self.loop_index = 0 if lines and self.loop.isChecked() else -1
        if lines:
            self.detected_language = detect_language(" ".join(line.text for line in lines[:8]))
        self._render_lines()

    def _language_code(self):
        selected = self.language.currentData()
        return self.detected_language if selected == "auto" else selected

    def _render_lines(self, *_):
        if not hasattr(self, "list"):
            return
        code = self._language_code()
        self.language.setItemText(0, f"自动 · {LANGUAGES[self.detected_language][0]}")
        self.japanese_mode.setVisible(code == "ja")
        novice = self.beginner_check.isChecked()
        self.reading_note.setText(LANGUAGES[code][1] + (" · 汉字谐音仅供入门" if novice else ""))
        self.reading_note.setToolTip("读音只供练习参考，特殊唱法需自行核对。")
        self.lyric_stack.setCurrentIndex(1 if self.lines else 0)
        reuse = len(self.rows) == len(self.lines) and all(row.line_text == line.text for row, line in zip(self.rows, self.lines))
        scroll = self.list.verticalScrollBar().value()
        self.list.setUpdatesEnabled(False)
        try:
            if not reuse:
                self.list.clear()
                self.rows.clear()
                self.active = -1
            for index, line in enumerate(self.lines):
                try:
                    annotation = reading(line.text, code, self.japanese_mode.currentIndex() == 1)
                except Exception as exc:
                    annotation = f"音标／读音不可用：{exc}"
                try:
                    hint = beginner_reading(line.text, code) if novice else ""
                except Exception as exc:
                    hint = f"谐音生成失败：{exc}"
                args = (line, annotation, code, self.font_size.value(), self.reading_check.isChecked(), self.translation_check.isChecked(), hint)
                if reuse:
                    row = self.rows[index]
                    row.update_display(*args)
                    row.set_active(index == self.active)
                    item = self.list.item(index)
                else:
                    row = LyricRow(*args)
                    item = QListWidgetItem()
                    self.list.addItem(item)
                    self.list.setItemWidget(item, row)
                    self.rows.append(row)
                row.set_available_width(self.list.viewport().width())
                item.setSizeHint(row.sizeHint())
            if reuse:
                self.list.doItemsLayout()
                self.list.verticalScrollBar().setValue(scroll)
        finally:
            self.list.setUpdatesEnabled(True)
        self._highlight(self._current_position())

    def _resize_rows(self):
        for index, row in enumerate(self.rows):
            row.set_available_width(self.list.viewport().width())
            self.list.item(index).setSizeHint(row.sizeHint())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "list"):
            QTimer.singleShot(0, self._resize_rows)

    def _line_clicked(self, item: QListWidgetItem):
        index = self.list.row(item)
        if 0 <= index < len(self.lines):
            if self.loop.isChecked():
                self.loop_index = index
            self._seek(self.lines[index].time_ms)

    def _jump_relative(self, delta: int):
        if not self.lines:
            return
        index = max(0, min(len(self.lines) - 1, self.active + delta))
        if self.loop.isChecked():
            self.loop_index = index
        self._seek(self.lines[index].time_ms)

    def _seek(self, position_ms: int):
        if self.mode == "local":
            self.player.setPosition(position_ms)
            self.player.play()
        elif self.snapshot.get("connected") and self.snapshot.get("canSeek"):
            self.cloud_clock.expect_seek(position_ms)
            self.follower.send("seek", position_ms, self.snapshot.get("identity", ""))
        else:
            self._set_status("当前网易云会话不支持定位；请使用直连或本地音频。")

    def _toggle(self):
        if self.mode == "local":
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()
        elif self.snapshot.get("connected") and self.snapshot.get("canPlay"):
            self.follower.send("toggle", 0, self.snapshot.get("identity", ""))
        else:
            self._set_status("网易云播放控制不可用，请连接客户端直连。")

    def _slider_released(self):
        self.dragging = False
        duration = self._current_duration()
        if duration > 0:
            self._seek(round(self.slider.value() / 1000 * duration))

    def _local_position(self, *_):
        if self.mode == "local":
            self._update_timeline()

    def _current_duration(self) -> int:
        return self.player.duration() if self.mode == "local" else int(self.snapshot.get("duration") or 0)

    def _current_position(self) -> int:
        if self.mode == "local":
            return self.player.position()
        return self.cloud_clock.position()

    @staticmethod
    def _format_time(ms: int) -> str:
        seconds = max(0, ms // 1000)
        return f"{seconds // 60:02d}:{seconds % 60:02d}"

    def _update_timeline(self):
        duration = self._current_duration()
        position = self._current_position()
        self.position.setText(self._format_time(position))
        self.duration.setText(self._format_time(duration))
        if not self.dragging:
            self.slider.setValue(round(position / duration * 1000) if duration else 0)
        self.slider.setEnabled(duration > 0 and (self.mode == "local" or self.snapshot.get("canSeek", False)))
        self._highlight(position)

    def _highlight(self, position_ms: int):
        index = (-1 if self.mode == "cloud" and not self.snapshot.get("timeline") else
                 active_index(self.lines, position_ms, round(self.offset.value() * 1000)))
        if index == self.active:
            return
        if 0 <= self.active < len(self.rows):
            self.rows[self.active].set_active(False)
        self.active = index
        if 0 <= index < len(self.rows):
            self.rows[index].set_active(True)
            if self.auto_follow.isChecked():
                self.list.scrollToItem(self.list.item(index), QListWidget.ScrollHint.PositionAtCenter)

    def _update_play_button(self):
        playing = (self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                   if self.mode == "local" else bool(self.snapshot.get("playing")))
        self.play_button.setText("Ⅱ" if playing else "▶")
        self.play_button.setToolTip("暂停" if playing else "播放")
        self.play_button.setEnabled(self.mode == "local" and self.local_path is not None
                                    or self.mode == "cloud" and self.snapshot.get("connected", False) and self.snapshot.get("canPlay", False))

    def _tick(self):
        self._update_timeline()
        index = self.loop_index
        if not self.loop.isChecked() or index < 0 or index + 1 >= len(self.lines):
            return
        playing = (self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState
                   if self.mode == "local" else self.snapshot.get("playing", False))
        if not playing or (self.mode == "cloud" and not self.snapshot.get("canSeek")):
            return
        start = self.lines[index].time_ms
        end = self.lines[index + 1].time_ms
        if end - start < (100 if self.mode == "local" else 800):
            return
        if self._current_position() >= end - 40 and time.monotonic() - self.loop_last_seek > .7:
            self.loop_last_seek = time.monotonic()
            self._seek(start)

    def _set_loop_target(self, enabled: bool):
        self.loop_index = (max(0, self.active) if self.lines else -1) if enabled else -1

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        self.timer.stop()
        self.follower.stop()
        self.player.stop()
        self.pool.shutdown(wait=False, cancel_futures=True)
        super().closeEvent(event)
