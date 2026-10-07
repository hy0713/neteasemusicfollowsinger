"""Light desktop layout: library rail, centered lyrics and transport bar."""

from PySide6.QtCore import Qt, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPixmap, QLinearGradient, QPen
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QPushButton, QSizePolicy, QSlider, QStackedWidget,
    QVBoxLayout, QWidget,
)

from .pronunciation import LANGUAGES
from .themes import THEMES, recolor


def artwork(size=320, theme="时尚绿"):
    image = QPixmap(size, size)
    image.fill(QColor("#e9eee8"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    gradient = QLinearGradient(0, 0, size, size)
    gradient.setColorAt(0, QColor(THEMES[theme][4]))
    gradient.setColorAt(1, QColor(THEMES[theme][3]))
    painter.fillRect(image.rect(), gradient)
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#e5dfbb"))
    painter.drawEllipse(int(size*.13), int(size*.13), int(size*.27), int(size*.27))
    painter.setBrush(QColor("#203e3c"))
    painter.drawEllipse(int(size*.35), int(size*.30), int(size*.67), int(size*.67))
    painter.setPen(QPen(QColor("#4b6860"), max(1, size/200)))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    for diameter in (.53, .43, .33):
        painter.drawEllipse(int(size*(.685-diameter/2)), int(size*(.635-diameter/2)),
                            int(size*diameter), int(size*diameter))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#dfcfab"))
    painter.drawEllipse(int(size*.59), int(size*.54), int(size*.19), int(size*.19))
    painter.setBrush(QColor("#203e3c"))
    painter.drawEllipse(int(size*.666), int(size*.616), int(size*.038), int(size*.038))
    painter.end()
    return image


def app_icon(size=256, theme="时尚绿"):
    image = QPixmap(size, size)
    image.fill(Qt.GlobalColor.transparent)
    painter = QPainter(image)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(THEMES[theme][3]))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(0, 0, size, size, size*.24, size*.24)
    painter.setPen(QPen(QColor("#eff3df"), size*.075, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    painter.drawLine(int(size*.57), int(size*.30), int(size*.57), int(size*.66))
    painter.drawLine(int(size*.57), int(size*.30), int(size*.78), int(size*.25))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor("#eff3df"))
    painter.drawEllipse(int(size*.36), int(size*.58), int(size*.22), int(size*.16))
    painter.setPen(QPen(QColor("#b3c8ac"), size*.035, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
    for y in (.39, .52, .65):
        painter.drawLine(int(size*.22), int(size*y), int(size*.36), int(size*y))
    painter.end()
    return image


class LyricRow(QFrame):
    def __init__(self, line, annotation, language="ja", font_size=30, show_reading=True, show_translation=True, beginner=""):
        super().__init__()
        self.setObjectName("lyricRow")
        outer = QHBoxLayout(self)
        outer.setContentsMargins(0, 8, 0, 8)
        outer.addStretch()
        self.content = QFrame()
        self.content.setObjectName("lyricContent")
        self.content.setProperty("active", False)
        layout = QVBoxLayout(self.content)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(7)
        self.annotation = QLabel(annotation)
        self.annotation.setObjectName("annotation")
        self.beginner = QLabel()
        self.beginner.setObjectName("beginnerReading")
        self.beginner.setToolTip("近似汉字谐音，不是翻译。按普通话读，忽略汉字声调；鼻音、收尾辅音、连读等仍需听原唱核对。")
        self.original = QLabel(line.text)
        self.original.setObjectName("lyricOriginal")
        family = "Yu Mincho" if language == "ja" else "Segoe UI"
        self.original.setFont(QFont(family, 1))
        self.original.setStyleSheet(f"font-family: '{family}'; font-size: {font_size}px;")
        self.annotation.setStyleSheet(f"font-size: {max(13, round(font_size*.48))}px;")
        self.translation = QLabel(line.translation)
        self.translation.setObjectName("translation")
        for label in (self.annotation, self.beginner, self.original, self.translation):
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setWordWrap(True)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.annotation.setVisible(show_reading and bool(annotation))
        self.translation.setVisible(show_translation and bool(line.translation))
        layout.addWidget(self.annotation)
        layout.addWidget(self.beginner)
        layout.addWidget(self.original)
        layout.addWidget(self.translation)
        outer.addWidget(self.content)
        outer.addStretch()
        self.update_display(line, annotation, language, font_size, show_reading, show_translation, beginner)
        self.set_available_width(800)

    def update_display(self, line, annotation, language, font_size, show_reading, show_translation, beginner):
        self.line_text = line.text
        family = "Yu Mincho" if language == "ja" else "Segoe UI"
        self.original.setText(line.text)
        self.original.setStyleSheet(f"font-family: '{family}'; font-size: {font_size}px;")
        self.annotation.setText(annotation)
        self.annotation.setStyleSheet(f"font-size: {max(13, round(font_size*.48))}px;")
        self.annotation.setVisible(show_reading and bool(annotation))
        self.translation.setText(line.translation)
        self.translation.setVisible(show_translation and bool(line.translation))
        self.beginner.setText(f"谐音参考：{beginner}" if beginner else "")
        self.beginner.setVisible(bool(beginner))
        self.beginner.setStyleSheet(f"font-size: {max(14, round(font_size*.55))}px;")

    def set_available_width(self, width):
        natural = max(label.fontMetrics().horizontalAdvance(label.text()) if not label.isHidden() else 0 for label in (self.original, self.annotation, self.beginner, self.translation))
        self.content.setFixedWidth(min(max(240, natural+48), max(220, width-56), 820))
        self.content.layout().activate()
        height = self.content.layout().heightForWidth(self.content.width())
        self.setMinimumHeight(max(85, height+16))

    def sizeHint(self):
        return QSize(self.content.width()+56, self.minimumHeight())

    def set_active(self, active):
        self.content.setProperty("active", active)
        self.content.style().unpolish(self.content)
        self.content.style().polish(self.content)


def _button(text, callback, name=""):
    button = QPushButton(text)
    if name:
        button.setObjectName(name)
    button.clicked.connect(callback)
    return button


def build_ui(w):
    central = QWidget()
    w.setCentralWidget(central)
    shell = QHBoxLayout(central)
    shell.setContentsMargins(0, 0, 0, 0)
    shell.setSpacing(0)

    rail = QFrame()
    rail.setObjectName("sidebar")
    rail.setFixedWidth(218)
    sidebar = QVBoxLayout(rail)
    sidebar.setContentsMargins(18, 24, 18, 20)
    sidebar.setSpacing(10)
    brand = QHBoxLayout()
    logo = w.brand_logo = QLabel()
    logo.setPixmap(app_icon(36, w.theme_name))
    logo.setFixedSize(36, 36)
    brand.addWidget(logo)
    name = QLabel('<b>跟唱伴学</b><br/><span style="font-size:7px; font-weight:400; color:#819285;">F O L L O W S I N G E R</span>')
    name.setObjectName("brand")
    brand.addWidget(name)
    brand.addStretch()
    sidebar.addLayout(brand)
    sidebar.addSpacing(18)
    w.follow_button = _button("网易云同步", w._follow_cloud, "navigation")
    w.follow_button.setCheckable(True)
    w.follow_button.setChecked(True)
    sidebar.addWidget(w.follow_button)
    w.local_button = _button("本地练唱", w._open_audio, "navigation")
    w.local_button.setCheckable(True)
    sidebar.addWidget(w.local_button)
    sidebar.addSpacing(16)
    w.cover = QLabel()
    w.cover.setObjectName("cover")
    w.cover.setPixmap(artwork(170, w.theme_name))
    w.cover.setFixedSize(180, 180)
    w.cover.setAlignment(Qt.AlignmentFlag.AlignCenter)
    sidebar.addWidget(w.cover)
    w.title = QLabel("尚未选择歌曲")
    w.title.setObjectName("songTitle")
    w.title.setWordWrap(True)
    sidebar.addSpacing(6)
    sidebar.addWidget(w.title)
    w.artist = QLabel("五种语言 · 逐句练习")
    w.artist.setObjectName("muted")
    w.artist.setWordWrap(True)
    sidebar.addWidget(w.artist)
    w.connection = QLabel("●  等待连接")
    w.connection.setObjectName("connection")
    sidebar.addSpacing(5)
    sidebar.addWidget(w.connection)
    w.direct_button = _button("连接网易云客户端", w._launch_direct, "primary")
    sidebar.addWidget(w.direct_button)
    w.open_audio = _button("打开本地音频", w._open_audio)
    sidebar.addWidget(w.open_audio)
    sidebar.addWidget(_button("体验五语示例", w._open_sample))
    sidebar.addStretch()
    sidebar.addWidget(QLabel("皮肤", objectName="railNote"))
    w.theme_picker = QComboBox()
    w.theme_picker.addItems(list(THEMES))
    w.theme_picker.setCurrentText(w.theme_name)
    w.theme_picker.currentTextChanged.connect(w._change_theme)
    sidebar.addWidget(w.theme_picker)
    sidebar.addWidget(QLabel("日语 / 英语 / 俄语 / 法语 / 韩语", objectName="railNote"))
    sidebar.addWidget(QLabel("FollowSinger  0.3.1", objectName="railNote"))
    shell.addWidget(rail)

    workspace = QVBoxLayout()
    workspace.setContentsMargins(0, 0, 0, 0)
    workspace.setSpacing(0)
    header = QFrame()
    header.setObjectName("header")
    top = QVBoxLayout(header)
    top.setContentsMargins(26, 18, 26, 14)
    top.setSpacing(12)
    options = QHBoxLayout()
    w.reading_check = QCheckBox("读音提示")
    w.reading_check.setChecked(True)
    w.reading_check.toggled.connect(w._render_lines)
    w.translation_check = QCheckBox("中文译文")
    w.translation_check.setChecked(True)
    w.translation_check.toggled.connect(w._render_lines)
    options.addWidget(w.reading_check)
    options.addWidget(w.translation_check)
    options.addSpacing(20)
    options.addWidget(QLabel("学习语言", objectName="muted"))
    w.language = QComboBox()
    w.language.addItem("自动识别", "auto")
    for code, (name, _) in LANGUAGES.items():
        w.language.addItem(name, code)
    w.language.currentIndexChanged.connect(w._render_lines)
    options.addWidget(w.language)
    w.japanese_mode = QComboBox()
    w.japanese_mode.addItems(["假名", "罗马音"])
    w.japanese_mode.currentIndexChanged.connect(w._render_lines)
    options.addWidget(w.japanese_mode)
    options.addStretch()
    source_toggle = QPushButton("歌词来源  ▾")
    source_toggle.setObjectName("textButton")
    source_toggle.setCheckable(True)
    options.addWidget(source_toggle)
    top.addLayout(options)
    w.source_panel = QWidget()
    sources = QHBoxLayout(w.source_panel)
    sources.setContentsMargins(0, 0, 0, 0)
    w.song_id = QLineEdit()
    w.song_id.setPlaceholderText("网易云歌曲 ID 或链接")
    w.song_id.returnPressed.connect(w._load_id)
    sources.addWidget(w.song_id, 1)
    sources.addWidget(_button("获取歌词", w._load_id))
    sources.addWidget(_button("导入原文", w._import_lrc))
    sources.addWidget(_button("导入译文", w._import_translation))
    w.source_panel.setVisible(False)
    source_toggle.toggled.connect(w.source_panel.setVisible)
    top.addWidget(w.source_panel)
    display = QHBoxLayout()
    w.auto_follow = QCheckBox("自动跟随")
    w.auto_follow.setChecked(True)
    display.addWidget(w.auto_follow)
    w.beginner_check = QCheckBox("新手模式")
    w.beginner_check.setToolTip("追加近似汉字谐音，帮助第一遍跟唱；不会替代原有读音和音标。")
    w.beginner_check.toggled.connect(w._render_lines)
    display.addWidget(w.beginner_check)
    w.reading_note = QLabel("")
    w.reading_note.setObjectName("muted")
    w.reading_note.setWordWrap(True)
    display.addWidget(w.reading_note, 1)
    display.addWidget(QLabel("字号", objectName="muted"))
    w.font_size = QSlider(Qt.Orientation.Horizontal)
    w.font_size.setRange(22, 44)
    w.font_size.setValue(30)
    w.font_size.setFixedWidth(110)
    w.font_size.valueChanged.connect(w._render_lines)
    display.addWidget(w.font_size)
    top.addLayout(display)
    workspace.addWidget(header)

    w.lyric_stack = QStackedWidget()
    empty = QWidget()
    empty_layout = QVBoxLayout(empty)
    empty_layout.addStretch()
    empty_art = w.empty_logo = QLabel()
    empty_art.setPixmap(app_icon(64, w.theme_name))
    empty_art.setAlignment(Qt.AlignmentFlag.AlignCenter)
    empty_layout.addWidget(empty_art)
    empty_layout.addSpacing(20)
    empty_title = QLabel("从一首歌开始")
    empty_title.setObjectName("emptyTitle")
    empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    empty_layout.addWidget(empty_title)
    description = QLabel("连接网易云音乐，或打开本地音频\n原文、读音与译文，在这里一起练习")
    description.setObjectName("emptyDescription")
    description.setAlignment(Qt.AlignmentFlag.AlignCenter)
    empty_layout.addWidget(description)
    empty_layout.addSpacing(18)
    empty_actions = QHBoxLayout()
    empty_actions.addStretch()
    empty_actions.addWidget(_button("体验五语示例", w._open_sample, "primary"))
    empty_actions.addStretch()
    empty_layout.addLayout(empty_actions)
    empty_layout.addStretch()
    w.lyric_stack.addWidget(empty)
    w.list = QListWidget()
    w.list.setObjectName("lyricList")
    w.list.setSpacing(9)
    w.list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
    w.list.setVerticalScrollMode(QListWidget.ScrollMode.ScrollPerPixel)
    w.list.itemClicked.connect(w._line_clicked)
    w.lyric_stack.addWidget(w.list)
    workspace.addWidget(w.lyric_stack, 1)

    bottom = QFrame()
    bottom.setObjectName("transport")
    transport = QVBoxLayout(bottom)
    transport.setContentsMargins(26, 12, 26, 14)
    transport.setSpacing(10)
    w.status = QLabel("")
    w.status.setObjectName("status")
    w.status.setWordWrap(True)
    transport.addWidget(w.status)
    timeline = QHBoxLayout()
    w.position = QLabel("00:00")
    w.position.setObjectName("muted")
    timeline.addWidget(w.position)
    w.slider = QSlider(Qt.Orientation.Horizontal)
    w.slider.setRange(0, 1000)
    w.slider.sliderPressed.connect(lambda: setattr(w, "dragging", True))
    w.slider.sliderReleased.connect(w._slider_released)
    timeline.addWidget(w.slider, 1)
    w.duration = QLabel("00:00")
    w.duration.setObjectName("muted")
    timeline.addWidget(w.duration)
    transport.addLayout(timeline)
    controls = QHBoxLayout()
    w.previous = _button("上一句", lambda: w._jump_relative(-1), "textButton")
    controls.addWidget(w.previous)
    w.play_button = _button("▶", w._toggle, "playButton")
    w.play_button.setFixedSize(40, 40)
    controls.addWidget(w.play_button)
    w.next = _button("下一句", lambda: w._jump_relative(1), "textButton")
    controls.addWidget(w.next)
    controls.addSpacing(16)
    w.loop = QCheckBox("一句循环")
    w.loop.toggled.connect(w._set_loop_target)
    controls.addWidget(w.loop)
    controls.addStretch()
    controls.addWidget(QLabel("速度", objectName="muted"))
    w.speed = QDoubleSpinBox()
    w.speed.setRange(.5, 1.5)
    w.speed.setSingleStep(.05)
    w.speed.setValue(1)
    w.speed.setSuffix(" ×")
    w.speed.setEnabled(False)
    w.speed.valueChanged.connect(w._change_speed)
    controls.addWidget(w.speed)
    controls.addSpacing(12)
    controls.addWidget(QLabel("歌词偏移", objectName="muted"))
    w.offset = QDoubleSpinBox()
    w.offset.setRange(-10, 10)
    w.offset.setSingleStep(.1)
    w.offset.setDecimals(2)
    w.offset.setSuffix(" 秒")
    controls.addWidget(w.offset)
    transport.addLayout(controls)
    workspace.addWidget(bottom)
    shell.addLayout(workspace, 1)


def apply_style(w):
    css = """
        QMainWindow { background: #fbfbf8; }
        QDialog, QMessageBox, QInputDialog { background: #fbfbf8; }
        QWidget { color: #35433e; font: 12px 'Microsoft YaHei UI'; }
        #sidebar { background: #f0f1e9; border-right: 1px solid #e3e6dc; }
        #brand { font-size: 16px; font-weight: 600; }
        #songTitle { font-size: 19px; font-weight: 600; }
        #muted, #railNote { color: #8b958e; font-size: 11px; }
        #connection { color: #6e8c7b; font-size: 11px; }
        #cover { background: #e6e9df; border-radius: 8px; }
        #header { border-bottom: 1px solid #edf0e8; }
        QPushButton { background: transparent; border: 1px solid #dce2d7;
            padding: 8px 12px; border-radius: 6px; }
        QPushButton:hover { background: #e9eee5; border-color: #c9d5c5; }
        QPushButton:disabled { color: #b1b8b0; }
        #navigation { text-align: left; border: none; padding: 11px 14px; }
        #navigation:checked { background: #dce7dc; color: #365e52; font-weight: 600; }
        #primary { background: #456c5d; border-color: #456c5d; color: white; }
        #primary:hover { background: #36584d; }
        #textButton { border: none; padding: 5px 9px; color: #78877c; }
        #playButton { background: #456c5d; color: white; border: none; border-radius: 20px; font-size: 18px; }
        QComboBox, QDoubleSpinBox, QLineEdit { background: #f9faf6; border: 1px solid #e0e5db;
            padding: 5px 8px; border-radius: 5px; selection-background-color: #bcd3bf; }
        QComboBox { min-width: 65px; }
        QDoubleSpinBox { max-width: 90px; }
        QCheckBox { spacing: 7px; }
        QCheckBox::indicator { width: 13px; height: 13px; border: 1px solid #b9c8b9; border-radius: 3px; background: #fbfbf8; }
        QCheckBox::indicator:checked { border-color: #6a8d75; image: url(__CHECK__); }
        #lyricList { background: #fbfbf8; border: none; padding: 22px 12px; outline: none; }
        #lyricList::item { background: transparent; border: none; }
        #lyricRow { background: transparent; }
        #lyricContent { background: transparent; border: 1px solid transparent; border-radius: 8px; }
        #lyricContent[active="true"] { background: #e6eddf; border-left: 3px solid #6c8b6a; }
        #lyricOriginal { color: #455348; }
        #annotation { color: #789078; }
        #beginnerReading { color: #456c5d; }
        #translation { color: #99a095; font-size: 12px; }
        #transport { background: #f3f5ee; border-top: 1px solid #e2e7dc; }
        #status { color: #939c90; font-size: 10px; }
        #emptyTitle { font-size: 27px; font-weight: 500; color: #556b5c; }
        #emptyDescription { color: #8d998c; font-size: 13px; line-height: 1.6; }
        QSlider::groove:horizontal { height: 3px; background: #dce5d6; border-radius: 1px; }
        QSlider::sub-page:horizontal { background: #789673; border-radius: 1px; }
        QSlider::handle:horizontal { background: #6b8868; width: 10px; margin: -4px 0; border-radius: 5px; }
        QScrollBar:vertical { background: transparent; width: 7px; margin: 0; }
        QScrollBar::handle:vertical { background: #dce3d6; min-height: 30px; border-radius: 3px; }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
        QComboBox QAbstractItemView { background: #fbfbf8; color: #35433e; selection-background-color: #dce7dc; }
        QToolTip { background: #f0f1e9; color: #35433e; border: 1px solid #dce2d7; }
        QDoubleSpinBox:disabled { color: #8b958e; }
        QCheckBox::indicator:checked { image: url(__CHECK__); background: #456c5d; }
    """.replace("__CHECK__", (w.root / "assets" / "check.svg").as_posix())
    w.setStyleSheet(recolor(css, w.theme_name))
