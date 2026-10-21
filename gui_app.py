# -*- coding: utf-8 -*-
"""
学习助手 GUI（题库由 config.ini 决定 · 丝滑悬停动画）
运行: python gui_app.py
打包: pyinstaller --noconfirm --clean --name "学习助手" --windowed --add-data "resource;resource" gui_app.py
"""
import sys, os

_IS_FROZEN = getattr(sys, "frozen", False)
if _IS_FROZEN:
    if sys.stdout is None:
        sys.stdout = open(os.devnull, "w", encoding="utf-8")
    if sys.stderr is None:
        sys.stderr = open(os.devnull, "w", encoding="utf-8")
    SCRIPT_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(SCRIPT_DIR)

import configparser, json, subprocess, tempfile, traceback

from PySide6.QtCore import (
    Qt, QThread, Signal, QObject, QByteArray, QSize,
    QPropertyAnimation, QEasingCurve, QPoint, QEvent,
)
from PySide6.QtGui import QIcon, QPixmap, QColor, QPainter, QPen
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QCheckBox, QComboBox, QSpinBox,
    QDoubleSpinBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QStackedWidget, QFrame, QScrollArea, QPlainTextEdit, QMessageBox,
    QFormLayout, QAbstractItemView, QGraphicsDropShadowEffect,
    QGraphicsOpacityEffect,
)

sys.path.insert(0, SCRIPT_DIR)
import main as engine
from api.answer import Tiku, DummyTiku
from api.base import Chaoxing, Account
from api.exceptions import LoginError
from api.logger import logger

CONFIG_INI_PATH = os.path.join(SCRIPT_DIR, "config.ini")
GUI_CONFIG_PATH = os.path.join(SCRIPT_DIR, "gui_config.json")

DEFAULT_CFG = {
    "username": "", "password": "", "use_cookies": False,
    "speed": 1.0, "jobs": 4, "retry_interval": 1.0,
    "notopen_action": "retry", "work_max_retries": 3,
    "work_redo_enabled": False,
}

_FEATHER = {
    "配置": '<line x1="4" y1="21" x2="4" y2="14"/><line x1="4" y1="10" x2="4" y2="3"/>'
            '<line x1="12" y1="21" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="3"/>'
            '<line x1="20" y1="21" x2="20" y2="16"/><line x1="20" y1="12" x2="20" y2="3"/>'
            '<line x1="1" y1="14" x2="7" y2="14"/><line x1="9" y1="8" x2="15" y2="8"/>'
            '<line x1="17" y1="16" x2="23" y2="16"/>',
    "课程": '<path d="M4 19.5A2.5 2.5 0 0 1 6.5 17H20"/>'
            '<path d="M6.5 2H20v20H6.5A2.5 2.5 0 0 1 4 19.5v-15A2.5 2.5 0 0 1 6.5 2z"/>',
    "运行": '<circle cx="12" cy="12" r="10"/><polygon points="10 8 16 12 10 16 10 8"/>',
    "日志": '<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>'
            '<polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>'
            '<line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>',
}


def svg_icon(name, color="#94A3B8", size=20):
    body = _FEATHER[name]
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}" '
           f'viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="2" '
           f'stroke-linecap="round" stroke-linejoin="round">{body}</svg>')
    renderer = QSvgRenderer(QByteArray(svg.encode()))
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    p = QPainter(pix)
    renderer.render(p)
    p.end()
    return QIcon(pix)


def _ensure_check_icons():
    icon_path = os.path.join(tempfile.gettempdir(), "cx_gui_check_v1.png")
    if not os.path.exists(icon_path):
        size = 18
        pix = QPixmap(size, size)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        pen = QPen(QColor("#FFFFFF"), 2.2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.drawLine(4, 10, 7, 13)
        p.drawLine(7, 13, 14, 6)
        p.end()
        pix.save(icon_path, "PNG")
    return icon_path.replace("\\", "/")


STYLE_TEMPLATE = """
* { font-family: "Microsoft YaHei UI", "Segoe UI", "PingFang SC", "Helvetica Neue", sans-serif;
    font-size: 13px; color: #1E293B; }
#Root { background: #F5F6FA; }
#Sidebar { background: #FFFFFF; border-right: 1px solid #EEF1F7; }
#LogoTitle { font-size: 15px; font-weight: 700; color: #1E293B; }
#LogoSub { font-size: 11px; color: #94A3B8; }
#NavBtn { text-align: left; padding: 9px 12px; border: none;
    border-radius: 9px; background: transparent; color: #64748B;
    font-size: 13px; icon-size: 18px; spacing: 10px; }
#NavBtn:hover { background: #F1F4FB; color: #334155; }
#NavBtn:checked { background: #EEF2FF; color: #4F46E5; font-weight: 600; }
#SidebarFooter { color: #B6BFCE; font-size: 11px; }
#LinkBtn { background: transparent; border: none; color: #64748B;
    font-size: 11px; padding: 0 2px; text-align: left; }
#LinkBtn:hover { color: #4F46E5; text-decoration: underline; }
#PageTitle { font-size: 22px; font-weight: 700; color: #0F172A; }
#PageSub { font-size: 12px; color: #94A3B8; }
#Card { background: #FFFFFF; border-radius: 14px; border: 1px solid #F1F4F9; }
#Card:hover { border: 1px solid #E6EAF2; }
#CardTitle { font-size: 13px; font-weight: 600; color: #334155; }
#CardHint { font-size: 11px; color: #94A3B8; }
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: #F8FAFC; border: 1px solid #E6EAF2; border-radius: 9px;
    padding: 7px 11px; min-height: 20px;
    selection-background-color: #4F46E5; selection-color: #FFFFFF; }
QLineEdit:hover, QSpinBox:hover, QDoubleSpinBox:hover, QComboBox:hover { border-color: #D6DDEC; }
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #4F46E5; background: #FFFFFF; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox QAbstractItemView { background: #FFFFFF; border: 1px solid #E6EAF2;
    border-radius: 8px; padding: 4px; selection-background-color: #EEF2FF;
    selection-color: #4F46E5; outline: none; }
QCheckBox { spacing: 8px; color: #475569; }
QCheckBox::indicator { width: 16px; height: 16px; border-radius: 5px;
    border: 1.5px solid #CBD5E1; background: #FFFFFF; }
QCheckBox::indicator:hover { border-color: #4F46E5; background: #F5F7FE; }
QCheckBox::indicator:checked { background: #4F46E5; border: 1.5px solid #4F46E5;
    image: url("{CHECK_ICON}"); }
QCheckBox::indicator:checked:hover { background: #4338CA; border-color: #4338CA;
    image: url("{CHECK_ICON}"); }
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {
    width: 18px; border: none; background: transparent; }
#PrimaryBtn { background: #4F46E5; color: #FFFFFF; border: none;
    border-radius: 10px; padding: 10px 22px; font-weight: 600; font-size: 13px; }
#PrimaryBtn:hover { background: #4338CA; }
#PrimaryBtn:pressed { background: #3730A3; }
#PrimaryBtn:disabled { background: #C7CBE8; color: #FFFFFF; }
#GhostBtn { background: #FFFFFF; border: 1px solid #E6EAF2;
    border-radius: 10px; padding: 9px 18px; color: #475569; font-weight: 500; }
#GhostBtn:hover { background: #F8FAFC; border-color: #D6DDEC; }
#GhostBtn:pressed { background: #EEF1F7; }
#GhostBtn:disabled { color: #B6BFCE; }
QTableWidget, QTableView { background: transparent; border: none;
    gridline-color: transparent; outline: none; }
QTableWidget::item, QTableView::item { padding: 10px 8px;
    border-bottom: 1px solid #F1F4F9; }
QTableWidget::item:hover, QTableView::item:hover { background: #F8FAFC; }
QTableWidget::item:selected, QTableView::item:selected {
    background: #F5F7FE; color: #1E293B; }
QHeaderView::section { background: transparent; border: none;
    border-bottom: 1px solid #EEF1F7; padding: 10px 8px;
    color: #94A3B8; font-weight: 600; font-size: 12px; }
QTableWidget::indicator, QTableView::indicator {
    width: 18px; height: 18px; border-radius: 5px;
    border: 1.5px solid #CBD5E1; background: #FFFFFF; }
QTableWidget::indicator:hover, QTableView::indicator:hover {
    border-color: #4F46E5; background: #F5F7FE; }
QTableWidget::indicator:checked, QTableView::indicator:checked {
    background: #4F46E5; border: 1.5px solid #4F46E5;
    image: url("{CHECK_ICON}"); }
QTableWidget::indicator:checked:hover, QTableView::indicator:checked:hover {
    background: #4338CA; border-color: #4338CA;
    image: url("{CHECK_ICON}"); }
#LogView { background: #0B1220; color: #C7D2FE;
    border: 1px solid #1E293B; border-radius: 12px;
    font-family: "Cascadia Mono", Consolas, "JetBrains Mono", monospace;
    font-size: 12px; padding: 12px; }
#TikuHint { color: #64748B; font-size: 12px; line-height: 160%; }
#TikuStatus { font-size: 12px; font-weight: 600; padding: 6px 10px;
    border-radius: 8px; }
QToolTip { background: #1E293B; color: #F1F5F9;
    border: 1px solid #334155; border-radius: 8px;
    padding: 8px 12px; font-size: 12px; }
QScrollArea { background: transparent; border: none; }
QScrollBar:vertical { background: transparent; width: 8px; margin: 4px; }
QScrollBar::handle:vertical { background: #D6DDEC; border-radius: 4px; min-height: 30px; }
QScrollBar::handle:vertical:hover { background: #B6BFCE; }
QScrollBar::add-line, QScrollBar::sub-line { height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: transparent; }
"""


def build_style():
    return STYLE_TEMPLATE.replace("{CHECK_ICON}", _ensure_check_icons())


class HoverLift(QObject):
    def __init__(self, widget, shadow, base_offset=(0, 6), hover_offset=(0, 2),
                 base_blur=28, hover_blur=48):
        super().__init__(widget)
        self.w = widget
        self.shadow = shadow
        self.base_offset = base_offset
        self.hover_offset = hover_offset
        self.base_blur = base_blur
        self.hover_blur = hover_blur
        widget.setMouseTracking(True)
        widget.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.w:
            if event.type() == QEvent.Enter:
                self._animate_to(True)
            elif event.type() == QEvent.Leave:
                self._animate_to(False)
        return super().eventFilter(obj, event)

    def _animate_to(self, hovered):
        duration = 380 if hovered else 300

        blur_anim = QPropertyAnimation(self.shadow, b"blurRadius")
        blur_anim.setDuration(duration)
        blur_anim.setEasingCurve(QEasingCurve.OutCubic)
        blur_anim.setStartValue(self.shadow.blurRadius())
        blur_anim.setEndValue(self.hover_blur if hovered else self.base_blur)
        blur_anim.start(QPropertyAnimation.DeleteWhenStopped)

        ox, oy = self.hover_offset if hovered else self.base_offset
        off_anim = QPropertyAnimation(self.shadow, b"offset")
        off_anim.setDuration(duration)
        off_anim.setEasingCurve(QEasingCurve.OutCubic)
        off_anim.setStartValue(self.shadow.offset())
        off_anim.setEndValue(QPoint(ox, oy))
        off_anim.start(QPropertyAnimation.DeleteWhenStopped)


class ButtonHover(QObject):
    def __init__(self, btn, base_scale=1.0, hover_scale=1.08):
        super().__init__(btn)
        self.btn = btn
        self.base_scale = base_scale
        self.hover_scale = hover_scale
        btn.setCursor(Qt.PointingHandCursor)
        btn.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj is self.btn:
            if event.type() == QEvent.Enter:
                self._scale_icon(self.hover_scale)
            elif event.type() == QEvent.Leave:
                self._scale_icon(self.base_scale)
        return super().eventFilter(obj, event)

    def _scale_icon(self, s):
        icon = self.btn.icon()
        if icon.isNull():
            return
        size = self.btn.iconSize()
        if size.isValid() and size.width() > 0:
            self.btn.setIconSize(QSize(int(size.width() * s), int(size.height() * s)))


def make_card(padding=20, spacing=12):
    card = QFrame(objectName="Card")
    shadow = QGraphicsDropShadowEffect(card)
    shadow.setBlurRadius(28)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(15, 23, 42, 20))
    card.setGraphicsEffect(shadow)
    lay = QVBoxLayout(card)
    lay.setContentsMargins(padding, padding, padding, padding)
    lay.setSpacing(spacing)
    HoverLift(card, shadow)
    return card, lay


def make_title(text, sub=""):
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 0)
    lay.setSpacing(2)
    lay.addWidget(QLabel(text, objectName="PageTitle"))
    if sub:
        lay.addWidget(QLabel(sub, objectName="PageSub"))
    return w


def hline():
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet("background: #F1F4F9;")
    return line


def read_ini_section(section):
    if not os.path.exists(CONFIG_INI_PATH):
        return {}
    try:
        cp = configparser.ConfigParser()
        cp.read(CONFIG_INI_PATH, encoding="utf8")
        if cp.has_section(section):
            return dict(cp.items(section))
    except Exception as e:
        logger.debug(f"读取 config.ini[{section}] 失败: {e}")
    return {}


def check_tiku_status():
    if not os.path.exists(CONFIG_INI_PATH):
        return False, "未找到 config.ini，章节测验将被跳过", "#B45309"
    try:
        cp = configparser.ConfigParser()
        cp.read(CONFIG_INI_PATH, encoding="utf8")
        if not cp.has_section("tiku"):
            return False, "config.ini 缺少 [tiku] 节，章节测验将被跳过", "#B45309"
        provider = cp.get("tiku", "provider", fallback="").strip()
        if not provider:
            return False, "provider 为空，章节测验将被跳过", "#B45309"
        required = ["submit", "cover_rate", "true_list", "false_list"]
        missing = [k for k in required if not cp.get("tiku", k, fallback="").strip()]
        if missing:
            return False, f"缺少字段: {', '.join(missing)}（章节测验将被跳过）", "#B45309"
        valid = {"TikuYanxi", "TikuGo", "TikuLike", "TikuAdapter", "AI", "SiliconFlow", "TikuManual"}
        parts = [p.strip() for p in provider.split(",") if p.strip()]
        invalid = [p for p in parts if p not in valid]
        if invalid:
            return False, f"provider 无效: {', '.join(invalid)}", "#B91C1C"
        return True, f"题库已就绪: {provider}", "#047857"
    except Exception as e:
        return False, f"读取失败: {e}", "#B91C1C"


class LogBridge(QObject):
    message = Signal(str)


class SessionWorker(QThread):
    finished_ok = Signal(object, list)
    failed = Signal(str)
    status = Signal(str)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg

    def run(self):
        try:
            self.status.emit("正在初始化题库…")
            tiku = None
            query_delay = 0.0
            try:
                tiku_ini = read_ini_section("tiku")
                try:
                    query_delay = float(tiku_ini.get("delay", "0") or 0)
                except ValueError:
                    query_delay = 0.0
                tiku = Tiku.get_tiku_from_config(None, config_path=CONFIG_INI_PATH)
                tiku.init_tiku()
                check_llm = str(tiku_ini.get("check_llm_connection", "true")).strip().lower() == "true"
                if check_llm and not tiku.DISABLE:
                    try:
                        if not tiku.check_llm_connection():
                            logger.warning("大模型连接检查失败，章节测验可能无法正确作答")
                    except Exception as e:
                        logger.debug(f"大模型连接检查异常: {e}")
            except Exception as e:
                logger.warning(f"题库初始化失败，将跳过章节测验: {e}")
                tiku = DummyTiku()
            if tiku is None:
                tiku = DummyTiku()

            account = Account(self.cfg["username"], self.cfg["password"])
            self.status.emit("正在创建客户端…")
            chaoxing = Chaoxing(
                account=account, tiku=tiku, query_delay=query_delay,
                work_max_retries=self.cfg.get("work_max_retries", 3),
                work_redo_enabled=self.cfg.get("work_redo_enabled", False),
            )
            self.status.emit("正在登录…")
            r = chaoxing.login(login_with_cookies=self.cfg.get("use_cookies", False))
            if not r.get("status"):
                raise LoginError(r.get("msg", "登录失败"))
            self.status.emit("正在获取课程列表…")
            courses = chaoxing.get_course_list()
            self.finished_ok.emit(chaoxing, courses)
        except Exception as e:
            logger.error(f"初始化失败: {e}")
            logger.error(traceback.format_exc())
            self.failed.emit(str(e))


class LearnWorker(QThread):
    finished_ok = Signal()
    failed = Signal(str)

    def __init__(self, chaoxing, courses, cfg):
        super().__init__()
        self.chaoxing = chaoxing
        self.courses = courses
        self.cfg = cfg

    def run(self):
        try:
            tasks = []
            for course in self.courses:
                logger.info(f"读取课程章节: {course['title']}")
                point_list = self.chaoxing.get_course_point(
                    course["courseId"], course["clazzId"], course["cpi"]
                )
                for i, point in enumerate(point_list["points"]):
                    tasks.append(engine.ChapterTask(point=point, index=i, course=course))
            logger.info(f"共 {len(tasks)} 个章节任务，开始执行…")
            engine.JobProcessor(self.chaoxing, tasks, self.cfg).run()
            logger.info("所有课程学习任务已完成")
            self.finished_ok.emit()
        except Exception as e:
            logger.error(f"运行失败: {e}")
            logger.error(traceback.format_exc())
            self.failed.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("学习助手")
        self.resize(1180, 760)
        self.setStyleSheet(build_style())

        self.cfg = self._load_cfg()
        self.chaoxing = None
        self.courses = []
        self.session_worker = None
        self.learn_worker = None
        self.log_bridge = LogBridge()
        self._page_anim = None
        self._config_inner = None

        self._build_ui()
        self._load_cfg_to_ui()
        self._refresh_tiku_status()
        self.log_bridge.message.connect(self._append_log)
        self._install_log_sink()

    def _load_cfg(self):
        if os.path.exists(GUI_CONFIG_PATH):
            try:
                with open(GUI_CONFIG_PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return {k: data.get(k, DEFAULT_CFG[k]) for k in DEFAULT_CFG}
            except Exception:
                pass
        return dict(DEFAULT_CFG)

    def _save_cfg(self):
        try:
            with open(GUI_CONFIG_PATH, "w", encoding="utf-8") as f:
                json.dump(self.cfg, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存配置失败: {e}")

    def _load_cfg_to_ui(self):
        c = self.cfg
        self.ed_username.setText(c.get("username", ""))
        self.ed_password.setText(c.get("password", ""))
        self.cb_cookies.setChecked(c.get("use_cookies", False))
        self.sp_speed.setValue(float(c.get("speed", 1.0)))
        self.sp_jobs.setValue(int(c.get("jobs", 4)))
        self.sp_retry.setValue(float(c.get("retry_interval", 1.0)))
        idx = self.cb_notopen.findText(c.get("notopen_action", "retry"))
        self.cb_notopen.setCurrentIndex(max(0, idx))
        self.sp_max_retries.setValue(int(c.get("work_max_retries", 3)))
        self.cb_redo.setChecked(c.get("work_redo_enabled", False))

    def _collect_cfg(self):
        return {
            "username": self.ed_username.text().strip(),
            "password": self.ed_password.text(),
            "use_cookies": self.cb_cookies.isChecked(),
            "speed": self.sp_speed.value(),
            "jobs": self.sp_jobs.value(),
            "retry_interval": self.sp_retry.value(),
            "notopen_action": self.cb_notopen.currentText(),
            "work_max_retries": self.sp_max_retries.value(),
            "work_redo_enabled": self.cb_redo.isChecked(),
        }

    def _build_ui(self):
        root = QWidget(objectName="Root")
        self.setCentralWidget(root)
        h = QHBoxLayout(root)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(0)
        h.addWidget(self._build_sidebar())
        self.stack = QStackedWidget()
        self.stack.addWidget(self._build_config_page())
        self.stack.addWidget(self._build_course_page())
        self.stack.addWidget(self._build_run_page())
        self.stack.addWidget(self._build_log_page())
        h.addWidget(self.stack, 1)
        self._switch_page(0, animate=False)

    def _build_sidebar(self):
        bar = QFrame(objectName="Sidebar")
        bar.setFixedWidth(216)
        lay = QVBoxLayout(bar)
        lay.setContentsMargins(16, 24, 16, 20)
        lay.setSpacing(4)

        logo_box = QWidget()
        lb = QVBoxLayout(logo_box)
        lb.setContentsMargins(6, 0, 6, 0)
        lb.setSpacing(2)
        lb.addWidget(QLabel("学习助手", objectName="LogoTitle"))
        lb.addWidget(QLabel("Study Helper", objectName="LogoSub"))
        lay.addWidget(logo_box)
        lay.addSpacing(22)

        self.nav_buttons = []
        self._nav_names = ["配置", "课程", "运行", "日志"]
        for i, name in enumerate(self._nav_names):
            b = QPushButton(name, objectName="NavBtn")
            b.setCheckable(True)
            b.setCursor(Qt.PointingHandCursor)
            b.setIcon(svg_icon(name, "#94A3B8"))
            b.setIconSize(QSize(18, 18))
            b.clicked.connect(lambda _=False, idx=i: self._switch_page(idx))
            lay.addWidget(b)
            self.nav_buttons.append(b)

        lay.addStretch()
        lay.addWidget(hline())
        lay.addSpacing(8)

        # 底部：版本号 + 关于按钮
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(6, 0, 6, 0)
        bottom_row.setSpacing(4)

        ver_label = QLabel("v1.0 · Beta测试版", objectName="SidebarFooter")
        bottom_row.addWidget(ver_label)
        bottom_row.addStretch()

        self.btn_about = QPushButton("关于", objectName="LinkBtn")
        self.btn_about.setCursor(Qt.PointingHandCursor)
        self.btn_about.clicked.connect(self._on_about)
        bottom_row.addWidget(self.btn_about)

        lay.addLayout(bottom_row)
        return bar

    def _on_about(self):
        QMessageBox.about(
            self,
            "关于 学习助手",
            "<h3>学习助手</h3>"
            "<p>基于 <a href='https://github.com/Samueli924/chaoxing'>Samueli924/chaoxing</a> "
            "修改而来。</p>"
            "<p>Copyright © 2024 原作者<br>"
            "修改者：zengjianxiong2017@163.com（2026 年）</p>"
            "<p>本程序是自由软件：可以根据自由软件基金会发布的 "
            "GNU 通用公共许可证第 3 版（或任何更新版本）的条款重新分发和/或修改它。</p>"
            "<p>本程序分发时希望它有用，但不提供任何担保，甚至不提供适销性或"
            "特定用途适用性的默示担保。</p>"
            "<p>完整许可证见安装目录下的 LICENSE 文件，"
            "访问 <a href='https://www.gnu.org/licenses/gpl-3.0.html'>"
            "https://www.gnu.org/licenses/gpl-3.0.html</a></p>"
        )

    def _switch_page(self, idx, animate=True):
        for i, b in enumerate(self.nav_buttons):
            b.setChecked(i == idx)
            color = "#4F46E5" if i == idx else "#94A3B8"
            b.setIcon(svg_icon(self._nav_names[i], color))

        if not animate:
            self.stack.setCurrentIndex(idx)
            return

        self.stack.setCurrentIndex(idx)

        page = self.stack.currentWidget()
        if idx == 0 and self._config_inner is not None:
            target = self._config_inner
        else:
            target = page

        if target.graphicsEffect() is not None:
            target.setGraphicsEffect(None)

        effect = QGraphicsOpacityEffect(target)
        target.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(320)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.OutCubic)

        def _cleanup():
            target.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        anim.start(QPropertyAnimation.DeleteWhenStopped)
        self._page_anim = anim

    def _build_config_page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        inner = QWidget()
        scroll.setWidget(inner)
        self._config_inner = inner
        lay = QVBoxLayout(inner)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(16)
        lay.addWidget(make_title("配置", "填写账号信息与学习参数"))

        card1, c1 = make_card()
        c1.addWidget(QLabel("账户", objectName="CardTitle"))
        f1 = QFormLayout()
        f1.setSpacing(12)
        f1.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.ed_username = QLineEdit()
        self.ed_username.setPlaceholderText("手机号")
        self.ed_username.setToolTip("超星账号的手机号")
        self.ed_password = QLineEdit()
        self.ed_password.setEchoMode(QLineEdit.Password)
        self.ed_password.setPlaceholderText("登录密码")
        self.ed_password.setToolTip("超星账号密码，仅保存在本地 gui_config.json")
        self.cb_cookies = QCheckBox("使用 Cookies 登录（无需密码）")
        self.cb_cookies.setToolTip("勾选后不验证密码，直接读取 cookies.txt")
        f1.addRow("手机号", self.ed_username)
        f1.addRow("密码", self.ed_password)
        f1.addRow("", self.cb_cookies)
        c1.addLayout(f1)
        lay.addWidget(card1)

        card2, c2 = make_card()
        c2.addWidget(QLabel("学习设置", objectName="CardTitle"))
        f2 = QFormLayout()
        f2.setSpacing(12)
        f2.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.sp_speed = QDoubleSpinBox(); self.sp_speed.setRange(1.0, 2.0)
        self.sp_speed.setSingleStep(0.1); self.sp_speed.setDecimals(1)
        self.sp_speed.setToolTip("视频播放倍速，1.0 原速，最大 2.0")
        self.sp_jobs = QSpinBox(); self.sp_jobs.setRange(1, 16)
        self.sp_jobs.setToolTip("同时并发的章节数，越大越快但越容易被风控")
        self.sp_retry = QDoubleSpinBox(); self.sp_retry.setRange(0.1, 10.0)
        self.sp_retry.setSingleStep(0.1); self.sp_retry.setDecimals(1)
        self.sp_retry.setToolTip("任务失败后等待多少秒再重试")
        self.cb_notopen = QComboBox(); self.cb_notopen.addItems(["retry", "continue"])
        self.cb_notopen.setToolTip("未开放章节：retry=反复重试，continue=直接跳过")
        self.sp_max_retries = QSpinBox(); self.sp_max_retries.setRange(1, 10)
        self.sp_max_retries.setToolTip("单个任务点最大重试次数")
        self.cb_redo = QCheckBox("允许章节检测自动重做（需题库支持错误反馈，推荐配合 AI 使用）")
        self.cb_redo.setToolTip("章节测验答错后让 AI 重新作答")
        f2.addRow("播放倍速", self.sp_speed)
        f2.addRow("并发章节数", self.sp_jobs)
        f2.addRow("重试间隔(秒)", self.sp_retry)
        f2.addRow("未开放章节", self.cb_notopen)
        f2.addRow("最大重试次数", self.sp_max_retries)
        f2.addRow("", self.cb_redo)
        c2.addLayout(f2)
        lay.addWidget(card2)

        card3, c3 = make_card()
        c3.addWidget(QLabel("题库", objectName="CardTitle"))
        hint = QLabel(
            "题库配置位于 exe 同目录下的 <b>config.ini</b> 的 <b>[tiku]</b> 节，"
            "本节内容由程序启动时自动读取，GUI 不需要填写。<br><br>"
            "<b>支持的 provider：</b> "
            "<code>TikuYanxi</code> · <code>TikuGo</code> · <code>TikuLike</code> · "
            "<code>TikuAdapter</code> · <code>AI</code> · <code>SiliconFlow</code> · "
            "<code>TikuManual</code>（多个用英文逗号分隔，按顺序回退）<br><br>"
            "<b>[tiku] 必需字段：</b> provider · submit · cover_rate · true_list · false_list<br>"
            "<b>不配置或配置不全</b>时，章节测验将被自动跳过，视频/文档/阅读学习不受影响。"
        )
        hint.setObjectName("TikuHint")
        hint.setWordWrap(True)
        hint.setTextFormat(Qt.RichText)
        c3.addWidget(hint)
        self.lbl_tiku_status = QLabel("")
        self.lbl_tiku_status.setObjectName("TikuStatus")
        self.lbl_tiku_status.setWordWrap(True)
        c3.addWidget(self.lbl_tiku_status)
        btn_row = QHBoxLayout()
        self.btn_open_ini = QPushButton("打开 config.ini", objectName="GhostBtn")
        ButtonHover(self.btn_open_ini)
        self.btn_open_ini.clicked.connect(self._on_open_ini)
        self.btn_recheck = QPushButton("重新检测", objectName="GhostBtn")
        ButtonHover(self.btn_recheck)
        self.btn_recheck.clicked.connect(self._refresh_tiku_status)
        btn_row.addWidget(self.btn_open_ini)
        btn_row.addWidget(self.btn_recheck)
        btn_row.addStretch()
        c3.addLayout(btn_row)
        lay.addWidget(card3)

        row = QHBoxLayout()
        self.btn_save = QPushButton("保存配置", objectName="GhostBtn")
        ButtonHover(self.btn_save)
        self.btn_save.clicked.connect(self._on_save_clicked)
        self.btn_connect = QPushButton("保存并登录", objectName="PrimaryBtn")
        ButtonHover(self.btn_connect)
        self.btn_connect.clicked.connect(self._on_connect)
        row.addWidget(self.btn_save)
        row.addStretch()
        row.addWidget(self.btn_connect)
        lay.addLayout(row)
        lay.addStretch()
        return scroll

    def _build_course_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(make_title("课程", "勾选需要学习的课程后开始"))
        top.addStretch()
        self.btn_refresh = QPushButton("刷新课程", objectName="GhostBtn")
        ButtonHover(self.btn_refresh)
        self.btn_refresh.clicked.connect(self._on_connect)
        self.btn_select_all = QPushButton("全选 / 反选", objectName="GhostBtn")
        ButtonHover(self.btn_select_all)
        self.btn_select_all.clicked.connect(self._toggle_select_all)
        top.addWidget(self.btn_refresh)
        top.addWidget(self.btn_select_all)
        lay.addLayout(top)

        card, c = make_card(padding=8)
        self.lbl_course_status = QLabel("尚未登录，请先在「配置」页登录")
        self.lbl_course_status.setStyleSheet("color: #94A3B8; font-size: 12px; padding: 6px 8px;")
        c.addWidget(self.lbl_course_status)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["", "课程 ID", "班级 ID", "课程名"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Fixed)
        self.table.setColumnWidth(0, 52)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setShowGrid(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setFocusPolicy(Qt.NoFocus)
        self.table.cellClicked.connect(self._on_cell_clicked)
        c.addWidget(self.table)
        lay.addWidget(card, 1)

        bottom = QHBoxLayout()
        bottom.addStretch()
        self.btn_start = QPushButton("开始学习", objectName="PrimaryBtn")
        ButtonHover(self.btn_start)
        self.btn_start.setEnabled(False)
        self.btn_start.clicked.connect(self._on_start_learning)
        bottom.addWidget(self.btn_start)
        lay.addLayout(bottom)
        return page

    def _build_run_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(16)
        lay.addWidget(make_title("运行", "任务状态与进度概览"))
        card, c = make_card(padding=36, spacing=10)
        c.addStretch()
        self.lbl_run_status = QLabel("空闲")
        self.lbl_run_status.setAlignment(Qt.AlignCenter)
        self.lbl_run_status.setStyleSheet("font-size: 26px; font-weight: 700; color: #4F46E5;")
        c.addWidget(self.lbl_run_status)
        self.lbl_run_summary = QLabel("尚未开始任务")
        self.lbl_run_summary.setAlignment(Qt.AlignCenter)
        self.lbl_run_summary.setStyleSheet("font-size: 13px; color: #94A3B8;")
        c.addWidget(self.lbl_run_summary)
        c.addStretch()
        lay.addWidget(card, 1)
        tip = QLabel("提示：运行中可切换到「日志」页查看实时输出。")
        tip.setStyleSheet("color: #94A3B8; font-size: 12px;")
        lay.addWidget(tip)
        return page

    def _build_log_page(self):
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setContentsMargins(36, 32, 36, 32)
        lay.setSpacing(16)
        top = QHBoxLayout()
        top.addWidget(make_title("日志", "运行过程中的实时输出"))
        top.addStretch()
        self.btn_clear_log = QPushButton("清空", objectName="GhostBtn")
        ButtonHover(self.btn_clear_log)
        self.btn_clear_log.clicked.connect(lambda: self.log_edit.clear())
        top.addWidget(self.btn_clear_log)
        lay.addLayout(top)
        card, c = make_card(padding=8)
        self.log_edit = QPlainTextEdit(objectName="LogView")
        self.log_edit.setReadOnly(True)
        c.addWidget(self.log_edit)
        lay.addWidget(card, 1)
        return page

    def _refresh_tiku_status(self):
        ok, text, color = check_tiku_status()
        bg = "#ECFDF5" if ok else "#FEF3C7" if color == "#B45309" else "#FEF2F2"
        prefix = "✓ " if ok else "⚠ "
        self.lbl_tiku_status.setText(prefix + text)
        self.lbl_tiku_status.setStyleSheet(
            f"color: {color}; background: {bg}; font-size: 12px; font-weight: 600;"
            f" padding: 8px 12px; border-radius: 8px;"
        )

    def _on_open_ini(self):
        if not os.path.exists(CONFIG_INI_PATH):
            QMessageBox.warning(
                self, "未找到 config.ini",
                f"未在以下位置找到配置文件：\n{CONFIG_INI_PATH}\n\n"
                f"请手动在该目录创建 config.ini，\n"
                f"并在 [tiku] 节填写 provider 等字段。\n\n"
                f"如果不需要章节测验，可以忽略此提示。"
            )
            return
        try:
            if sys.platform.startswith("win"):
                os.startfile(CONFIG_INI_PATH)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", CONFIG_INI_PATH])
            else:
                subprocess.Popen(["xdg-open", CONFIG_INI_PATH])
            from PySide6.QtCore import QTimer
            QTimer.singleShot(1200, self._refresh_tiku_status)
        except Exception as e:
            QMessageBox.warning(self, "无法打开", f"打开 config.ini 失败：{e}\n路径：{CONFIG_INI_PATH}")

    def _install_log_sink(self):
        def sink(message):
            self.log_bridge.message.emit(str(message).rstrip("\n"))
        try:
            logger.add(sink, level="INFO", format="{time:HH:mm:ss} | {level: <7} | {message}")
        except Exception as e:
            print(f"安装日志 sink 失败: {e}", file=sys.stderr)

    def _append_log(self, text):
        if not hasattr(self, "log_edit"):
            return
        self.log_edit.appendPlainText(text)
        sb = self.log_edit.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _on_save_clicked(self):
        self.cfg = self._collect_cfg()
        self._save_cfg()
        self._refresh_tiku_status()
        QMessageBox.information(self, "提示", "配置已保存")

    def _on_connect(self):
        cfg = self._collect_cfg()
        if not cfg["username"]:
            QMessageBox.warning(self, "提示", "请先填写手机号")
            return
        self.cfg = cfg
        self._save_cfg()
        self._refresh_tiku_status()
        self.btn_connect.setEnabled(False)
        self.btn_refresh.setEnabled(False)
        self.lbl_course_status.setText("正在连接…")
        self._switch_page(1)
        self.session_worker = SessionWorker(cfg)
        self.session_worker.status.connect(lambda s: self.lbl_course_status.setText(s))
        self.session_worker.finished_ok.connect(self._on_session_ok)
        self.session_worker.failed.connect(self._on_session_failed)
        self.session_worker.start()

    def _on_session_ok(self, chaoxing, courses):
        self.chaoxing = chaoxing
        self.courses = courses or []
        self._fill_courses(self.courses)
        self.lbl_course_status.setText(f"登录成功，共 {len(self.courses)} 门课程，请勾选后开始学习")
        self.btn_connect.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        self.btn_start.setEnabled(bool(self.courses))
        self._refresh_tiku_status()

    def _on_session_failed(self, msg):
        self.lbl_course_status.setText(f"登录失败: {msg}")
        self.btn_connect.setEnabled(True)
        self.btn_refresh.setEnabled(True)
        QMessageBox.critical(self, "登录失败", msg)

    def _fill_courses(self, courses):
        self.table.setRowCount(0)
        for c in courses:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setRowHeight(row, 46)
            chk = QTableWidgetItem()
            chk.setFlags(chk.flags() | Qt.ItemIsUserCheckable)
            chk.setCheckState(Qt.Checked)
            chk.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, chk)
            self.table.setItem(row, 1, QTableWidgetItem(str(c.get("courseId", ""))))
            self.table.setItem(row, 2, QTableWidgetItem(str(c.get("clazzId", ""))))
            name_item = QTableWidgetItem(c.get("title", "未命名课程"))
            name_item.setData(Qt.UserRole, c)
            self.table.setItem(row, 3, name_item)

    def _on_cell_clicked(self, row, col):
        if col == 0:
            return
        item = self.table.item(row, 0)
        if item:
            item.setCheckState(Qt.Unchecked if item.checkState() == Qt.Checked else Qt.Checked)

    def _toggle_select_all(self):
        rows = self.table.rowCount()
        if rows == 0:
            return
        all_checked = all(
            self.table.item(r, 0) and self.table.item(r, 0).checkState() == Qt.Checked
            for r in range(rows)
        )
        state = Qt.Unchecked if all_checked else Qt.Checked
        for r in range(rows):
            item = self.table.item(r, 0)
            if item:
                item.setCheckState(state)

    def _on_start_learning(self):
        if self.chaoxing is None:
            QMessageBox.warning(self, "提示", "请先在「配置」页登录")
            return
        selected = []
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item and item.checkState() == Qt.Checked:
                course = self.table.item(row, 3).data(Qt.UserRole)
                if course:
                    selected.append(course)
        if not selected:
            QMessageBox.warning(self, "提示", "请至少勾选一门课程")
            return
        self.cfg = self._collect_cfg()
        self._save_cfg()
        self.btn_start.setEnabled(False)
        self.lbl_run_status.setText("运行中…")
        self.lbl_run_status.setStyleSheet("font-size: 26px; font-weight: 700; color: #4F46E5;")
        self.lbl_run_summary.setText(
            f"课程数 {len(selected)}    ·    并发 {self.cfg['jobs']}    ·    倍速 {self.cfg['speed']}"
        )
        self._switch_page(2)
        self.learn_worker = LearnWorker(self.chaoxing, selected, self.cfg)
        self.learn_worker.finished_ok.connect(self._on_learn_ok)
        self.learn_worker.failed.connect(self._on_learn_failed)
        self.learn_worker.start()

    def _on_learn_ok(self):
        self.lbl_run_status.setText("已完成")
        self.lbl_run_status.setStyleSheet("font-size: 26px; font-weight: 700; color: #10B981;")
        self.btn_start.setEnabled(True)
        QMessageBox.information(self, "完成", "所有课程学习任务已完成")

    def _on_learn_failed(self, msg):
        self.lbl_run_status.setText("运行失败")
        self.lbl_run_status.setStyleSheet("font-size: 26px; font-weight: 700; color: #EF4444;")
        self.btn_start.setEnabled(True)
        QMessageBox.critical(self, "运行失败", msg)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()