import sys
import re
import json
import os
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QLabel, QPushButton, QTableWidget,
                             QTableWidgetItem, QDateTimeEdit, QMessageBox,
                             QProgressBar, QLineEdit, QDialog, QDialogButtonBox,
                             QSpinBox, QFormLayout, QGroupBox, QScrollArea)
from PyQt5.QtCore import (QObject, QDateTime, Qt, QThread, pyqtSignal, QTimer,
                          QMutex, QMutexLocker, QWaitCondition, QPropertyAnimation,
                          QEasingCurve, QPoint, QRect)
from PyQt5.QtGui import QFont, QIntValidator, QColor, QPalette

try:
    import pandas as pd
except ImportError:
    print("警告：未安装 pandas/openpyxl，Excel 保存功能将不可用")
    pd = None

# -------------------------- 1. 关键词定义 --------------------------
# 买卖相关关键词
TRADE_KEYWORDS = [
    r'收',
    r'求',
    r'带价',
    r'实验',
    r'出\b',
    r'物理',
    r'出\s?[东西|闲置|物品|资料|文件]',
    r'卖|出售|转让|转卖',
    r'价格|多少钱|¥|元|出\s?[0-9]+[元|块]',
    r'交易|面交|包邮|转账|付款|收款',
    r'实验报告',
    r'实验\s?[报告|数据|记录|指导]',
    r'课设|课程设计',
    r'大作业|课程作业|作业',
    r'代写|代做|代笔|代抄|代完成',
    r'抄作业|写作业|作业代写',
]
TRADE_PATTERN = re.compile('|'.join(TRADE_KEYWORDS), re.IGNORECASE)

# 配置文件路径
CONFIG_FILE = "./data/crawler_config.json"


# -------------------------- 2. 右下角通知弹窗类 --------------------------
class NotificationWidget(QWidget):
    """
    右下角通知弹窗
    特点：无边框、置顶、不自动关闭（需手动点击×）
    """

    def __init__(self, posts, parent=None):
        super().__init__(parent)
        self.posts = posts
        # 设置窗口标志：无边框 | 总是置顶 | 工具窗口模式
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 350)  # 稍微调大高度以容纳更多内容

        # 初始化UI
        self.init_ui()
        # 初始化位置（屏幕右下角）
        self.init_position()
        # 入场动画
        self.show_animation()

    def init_ui(self):
        # 主背景容器（白色圆角背景）
        self.main_widget = QWidget(self)
        self.main_widget.setGeometry(0, 0, 400, 350)
        self.main_widget.setStyleSheet("""
            QWidget {
                background-color: #FFFFFF;
                border: 1px solid #CCCCCC;
                border-radius: 10px;
                box-shadow: 2px 2px 10px rgba(0,0,0,0.2);
            }
        """)

        layout = QVBoxLayout(self.main_widget)
        layout.setContentsMargins(15, 15, 15, 15)

        # --- 标题栏 ---
        header_layout = QHBoxLayout()

        # 标题文字
        title_label = QLabel(f"🔔 发现 {len(self.posts)} 条买卖相关帖子")
        title_label.setStyleSheet("font-weight: bold; font-size: 15px; color: #E53935; border: none;")

        # 关闭按钮
        close_btn = QPushButton("×")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self.close_animation)  # 点击关闭执行退场动画
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #999999;
                font-size: 22px;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #FF0000;
                background-color: #F0F0F0;
                border-radius: 15px;
            }
        """)

        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(close_btn)
        layout.addLayout(header_layout)

        # --- 分割线 ---
        line = QLabel()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: #EEEEEE; border: none;")
        layout.addWidget(line)

        # --- 滚动区域显示帖子列表 ---
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { width: 6px; background: transparent; }
            QScrollBar::handle:vertical { background: #CCCCCC; border-radius: 3px; }
        """)

        scroll_content = QWidget()
        scroll_content.setStyleSheet("background-color: transparent; border: none;")
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(0, 10, 0, 0)

        # 填充帖子内容
        for post in self.posts:
            # post结构: [时间, 标题, 内容, 评论数, 关键词]
            post_container = QWidget()
            post_container.setStyleSheet("""
                QWidget {
                    background-color: #F5F7FA;
                    border-radius: 6px;
                    border: 1px solid #E0E0E0;
                }
                QWidget:hover {
                    background-color: #EEF2F7;
                    border: 1px solid #BBDEFB;
                }
            """)
            post_inner_layout = QVBoxLayout(post_container)
            post_inner_layout.setContentsMargins(10, 10, 10, 10)
            post_inner_layout.setSpacing(5)

            # 标题
            lbl_title = QLabel(post[1])
            lbl_title.setWordWrap(True)
            lbl_title.setStyleSheet(
                "font-weight: bold; color: #1976D2; font-size: 13px; border: none; background: transparent;")

            # 时间
            lbl_time = QLabel(f"发布时间: {post[0]}")
            lbl_time.setStyleSheet("color: #757575; font-size: 11px; border: none; background: transparent;")

            # 内容摘要 (限制长度)
            content_text = post[2]
            if len(content_text) > 70:
                content_text = content_text[:70] + "..."
            lbl_content = QLabel(content_text)
            lbl_content.setWordWrap(True)
            lbl_content.setStyleSheet("color: #424242; font-size: 12px; border: none; background: transparent;")

            post_inner_layout.addWidget(lbl_title)
            post_inner_layout.addWidget(lbl_content)
            post_inner_layout.addWidget(lbl_time)

            scroll_layout.addWidget(post_container)

        scroll_layout.addStretch()
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # --- 底部提示 ---
        footer = QLabel("请前往主界面查看详情")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("color: #999; font-size: 10px; border: none; margin-top: 5px;")
        layout.addWidget(footer)

    def init_position(self):
        """计算并设置到右下角"""
        desktop = QApplication.desktop()
        # 获取可用桌面几何（不包含任务栏）
        screen_rect = desktop.availableGeometry()
        self.move(screen_rect.width() - self.width() - 20, screen_rect.height() - self.height() - 20)

    def show_animation(self):
        """从下往上升起的动画"""
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(600)
        self.anim.setEasingCurve(QEasingCurve.OutBack)  # 带有回弹效果
        start_pos = self.pos() + QPoint(0, self.height() + 50)
        end_pos = self.pos()
        self.anim.setStartValue(start_pos)
        self.anim.setEndValue(end_pos)
        self.anim.start()

    def close_animation(self):
        """关闭时的透明度淡出动画"""
        self.anim_fade = QPropertyAnimation(self, b"windowOpacity")
        self.anim_fade.setDuration(300)
        self.anim_fade.setStartValue(1.0)
        self.anim_fade.setEndValue(0.0)
        self.anim_fade.finished.connect(self.close)
        self.anim_fade.start()


# -------------------------- 3. 配置管理类 --------------------------
class ConfigManager:
    """管理配置参数"""

    @staticmethod
    def load_config():
        default_config = {
            "interval_minutes": 30,  # 默认30分钟
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    for key, val in default_config.items():
                        if key not in config:
                            config[key] = val
                    return config
            except Exception as e:
                print(f"[配置加载] 失败，使用默认配置：{e}")
        return default_config

    @staticmethod
    def save_config(config):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=4)
        except Exception as e:
            print(f"[配置保存] 失败：{e}")


# -------------------------- 4. 爬虫线程类 --------------------------
class CrawlerThread(QThread):
    """执行具体爬取任务的线程"""
    progress_update = pyqtSignal(int, str)
    result_signal = pyqtSignal(list)
    error_signal = pyqtSignal(str)
    finished_signal = pyqtSignal()

    def __init__(self, start_time_str, end_time_str):
        super().__init__()
        self.start_time_str = start_time_str
        self.end_time_str = end_time_str
        self.is_aborted = False
        self.mutex = QMutex()
        self.wait_condition = QWaitCondition()

    def abort(self):
        with QMutexLocker(self.mutex):
            self.is_aborted = True
        self.wait_condition.wakeAll()
        self.progress_update.emit(0, "正在中断爬取...")

    def run(self):
        try:
            with QMutexLocker(self.mutex):
                if self.is_aborted:
                    self.error_signal.emit("爬取已被中断")
                    self.finished_signal.emit()
                    return

            try:
                # 延迟导入，确保爬虫文件存在
                from utils.spider_jishi import ZanaoCrawler
            except ImportError as e:
                self.error_signal.emit(f"导入爬虫失败：{str(e)}\n请确保 spider_jishi.py 在同级目录下")
                self.finished_signal.emit()
                return

            self.progress_update.emit(20, f"正在抓取数据...\n时间范围: {self.start_time_str} -> {self.end_time_str}")

            # 这里的 test_time_bound 设置为起始时间，爬虫会从该时间点开始抓取
            crawler = ZanaoCrawler(test_time_bound=self.start_time_str)

            if self.is_aborted: return

            crawler.run()

            with QMutexLocker(self.mutex):
                if self.is_aborted:
                    self.error_signal.emit("爬取已被中断")
                    self.finished_signal.emit()
                    return

            self.progress_update.emit(90, "正在处理数据...")
            formatted_data = crawler.get_formatted_posts()

            # --- 核心逻辑：严格筛选时间段 ---
            # 确保返回的数据严格位于 [start_time, end_time] 之间
            filtered_data = []
            for post in formatted_data:
                if self.is_aborted: break
                post_time_str = post[0]  # 假设第一个元素是时间字符串
                try:
                    post_time = datetime.strptime(post_time_str, '%Y-%m-%d %H:%M:%S')
                    start_time = datetime.strptime(self.start_time_str, '%Y-%m-%d %H:%M:%S')
                    end_time = datetime.strptime(self.end_time_str, '%Y-%m-%d %H:%M:%S')

                    # 包含起始时间，包含结束时间
                    if start_time <= post_time <= end_time:
                        filtered_data.append(post)
                except Exception:
                    continue

            self.progress_update.emit(100, f"抓取完成！区间内有效数据: {len(filtered_data)} 条")
            self.result_signal.emit(filtered_data)

        except Exception as e:
            with QMutexLocker(self.mutex):
                if not self.is_aborted:
                    self.error_signal.emit(f"爬虫运行出错：{str(e)}")
        finally:
            self.finished_signal.emit()
            self.wait_condition.wakeAll()


# -------------------------- 5. 定时爬取控制线程 --------------------------
class TimedCrawlerThread(QThread):
    """
    定时控制器
    负责计时，并周期性启动 CrawlerThread
    """
    new_posts_signal = pyqtSignal(list, str, str)  # 信号：数据列表, 开始时间, 结束时间
    status_signal = pyqtSignal(str)
    progress_update = pyqtSignal(int, str)

    def __init__(self, interval_minutes, parent=None):
        super().__init__(parent)
        self.interval_minutes = interval_minutes
        self.interval_seconds = interval_minutes * 60
        self.is_running = False
        self.is_crawling = False
        self.mutex = QMutex()
        self.crawler_thread = None
        self.timer = None

    def update_interval(self, new_interval_minutes):
        """动态更新时间间隔"""
        with QMutexLocker(self.mutex):
            self.interval_minutes = new_interval_minutes
            self.interval_seconds = new_interval_minutes * 60
            self.status_signal.emit(f"设置已更新：每 {new_interval_minutes} 分钟爬取一次")
            # 如果定时器正在运行，更新它的间隔
            if self.timer and self.is_running:
                self.timer.setInterval(self.interval_seconds * 1000)

    def stop(self):
        """停止定时任务"""
        with QMutexLocker(self.mutex):
            if not self.is_running: return
            self.is_running = False
            self.status_signal.emit("正在停止定时任务...")
            if self.timer:
                self.timer.stop()
                self.timer.deleteLater()
                self.timer = None
            if self.crawler_thread and self.crawler_thread.isRunning():
                self.crawler_thread.abort()

        if self.crawler_thread and self.crawler_thread.isRunning():
            self.crawler_thread.wait(3000)
        self.quit()
        self.wait(2000)

    def run(self):
        with QMutexLocker(self.mutex):
            self.is_running = True

        self.status_signal.emit(f"定时任务已启动 - 循环间隔: {self.interval_minutes} 分钟")

        # 创建定时器
        self.timer = QTimer()
        self.timer.setInterval(self.interval_seconds * 1000)  # 毫秒
        self.timer.setSingleShot(False)  # 循环触发
        self.timer.timeout.connect(self.do_crawl, Qt.QueuedConnection)
        self.timer.start()

        # 启动后立即执行第一次爬取
        self.do_crawl()

        # 进入事件循环，等待定时器触发
        self.exec_()

        # 清理工作
        with QMutexLocker(self.mutex):
            if self.timer:
                self.timer.stop()
                self.timer = None
            if self.crawler_thread:
                self.crawler_thread.deleteLater()
                self.crawler_thread = None
        self.status_signal.emit("定时任务已停止")

    def do_crawl(self):
        """
        核心定时逻辑：
        1. 计算时间窗口：当前时间 - 间隔时间 -> 当前时间
        2. 启动爬虫
        """
        with QMutexLocker(self.mutex):
            if not self.is_running or self.is_crawling: return
            self.is_crawling = True

        try:
            current_dt = datetime.now()
            # 关键逻辑：起始时间 = 当前时间 减去 设定的分钟数
            start_dt = current_dt - timedelta(minutes=self.interval_minutes)

            end_time_str = current_dt.strftime('%Y-%m-%d %H:%M:%S')
            start_time_str = start_dt.strftime('%Y-%m-%d %H:%M:%S')

            msg = f"开始本轮爬取... 范围: {start_time_str} 至 {end_time_str}"
            print(f"[定时任务] {msg}")
            self.status_signal.emit(msg)
            self.progress_update.emit(0, "正在初始化...")

            # 再次检查是否被停止
            if not self.is_running:
                self.is_crawling = False
                return

            # 启动实际的爬虫线程
            self.crawler_thread = CrawlerThread(start_time_str, end_time_str)

            # 连接信号
            self.crawler_thread.result_signal.connect(
                lambda data: self.on_crawler_result(data, start_time_str, end_time_str)
            )
            self.crawler_thread.error_signal.connect(self.on_crawler_error)
            self.crawler_thread.progress_update.connect(self.on_crawler_progress)
            self.crawler_thread.finished_signal.connect(self.on_crawler_finished)

            self.crawler_thread.start()

            # 等待爬虫线程结束（非阻塞等待，防止界面卡死，但要在本线程内监控）
            # 这里使用简单的循环检查，实际由信号驱动

        except Exception as e:
            self.status_signal.emit(f"定时调度异常：{str(e)}")
            with QMutexLocker(self.mutex):
                self.is_crawling = False

    def on_crawler_progress(self, value, desc):
        self.progress_update.emit(value, f"定时运行中: {desc}")

    def on_crawler_result(self, formatted_data, start_time_str, end_time_str):
        """爬取成功后的回调"""
        # 筛选买卖相关帖子
        new_trade_posts = []
        for post in formatted_data:
            title, content = post[1], post[2]
            if TRADE_PATTERN.search(title) or TRADE_PATTERN.search(content):
                new_trade_posts.append(post)

        if new_trade_posts:
            self.status_signal.emit(f"✅ 本轮发现 {len(new_trade_posts)} 条买卖相关帖子")
            # 发送信号给主界面，触发弹窗
            self.new_posts_signal.emit(new_trade_posts, start_time_str, end_time_str)
        else:
            self.status_signal.emit(f"本轮未发现相关帖子 ({start_time_str} - {end_time_str})")
            # 即使没有新帖子，也发送空列表以刷新界面状态
            self.new_posts_signal.emit([], start_time_str, end_time_str)

        self.progress_update.emit(100, "本轮结束，等待下一次周期...")

    def on_crawler_error(self, error_msg):
        self.status_signal.emit(f"❌ 本轮失败：{error_msg}")
        self.progress_update.emit(0, "失败")
        self.new_posts_signal.emit([], "", "")

    def on_crawler_finished(self):
        with QMutexLocker(self.mutex):
            self.is_crawling = False
            if self.crawler_thread:
                self.crawler_thread.deleteLater()
                self.crawler_thread = None


# -------------------------- 6. 参数设置窗口 --------------------------
class SettingsDialog(QDialog):
    config_saved_signal = pyqtSignal(dict)

    def __init__(self, current_config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("参数设置")
        self.setModal(True)
        self.setFixedSize(300, 150)
        self.current_config = current_config
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        group_box = QGroupBox("定时爬取设置")
        form_layout = QFormLayout()

        self.interval_edit = QLineEdit()
        self.interval_edit.setValidator(QIntValidator())
        self.interval_edit.setText(str(self.current_config["interval_minutes"]))
        self.interval_edit.setPlaceholderText("请输入1-1440之间的整数")
        form_layout.addRow("循环间隔（分钟）：", self.interval_edit)

        group_box.setLayout(form_layout)
        layout.addWidget(group_box)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel, Qt.Horizontal, self)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.setLayout(layout)

    def accept(self):
        interval_text = self.interval_edit.text().strip()
        if not interval_text: return
        try:
            interval_minutes = int(interval_text)
        except ValueError:
            return

        if interval_minutes < 1 or interval_minutes > 1440:
            QMessageBox.warning(self, "输入错误", "时间间隔必须在1-1440分钟之间！")
            return

        new_config = {"interval_minutes": interval_minutes}
        ConfigManager.save_config(new_config)
        self.config_saved_signal.emit(new_config)
        QMessageBox.information(self, "设置成功", f"已保存配置：\n每 {interval_minutes} 分钟爬取一次")
        super().accept()


# -------------------------- 7. 主界面类 --------------------------
class PostQueryTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.all_data = []
        self.current_data = []
        self.is_filtered = False
        self.config = ConfigManager.load_config()
        self.timed_crawler = None
        self.is_manual_crawling = False
        self.notification_window = None  # 存储弹窗引用
        self.initUI()

    def initUI(self):
        self.setWindowTitle('校园集市买卖/学术相关帖子查询工具（武汉理工大学信研2506 胡肖安制作，未经允许请勿转载）')
        self.setGeometry(100, 100, 1200, 650)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        font = QFont("SimHei")
        self.setFont(font)

        # --- 顶部设置区域 ---
        top_layout = QVBoxLayout()
        settings_layout = QHBoxLayout()

        self.settings_btn = QPushButton("参数设置")
        self.settings_btn.setStyleSheet("background-color: #673AB7; color: white; padding: 5px 15px;")
        self.settings_btn.clicked.connect(self.open_settings)
        settings_layout.addWidget(self.settings_btn)
        settings_layout.addSpacing(20)

        self.start_time_edit = QDateTimeEdit()
        self.start_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.start_time_edit.setDateTime(QDateTime.currentDateTime().addDays(-1))
        settings_layout.addWidget(QLabel("起始时间(手动):"))
        settings_layout.addWidget(self.start_time_edit)
        settings_layout.addSpacing(20)

        self.end_time_edit = QDateTimeEdit()
        self.end_time_edit.setDisplayFormat("yyyy-MM-dd HH:mm:ss")
        self.end_time_edit.setDateTime(QDateTime.currentDateTime())
        self.end_time_edit.setReadOnly(True)
        settings_layout.addWidget(QLabel("结束时间:"))
        settings_layout.addWidget(self.end_time_edit)
        settings_layout.addSpacing(20)

        self.filter_switch_btn = QPushButton("筛选买卖相关（未开启）")
        self.filter_switch_btn.setStyleSheet("background-color: #9E9E9E; color: white; padding: 5px 15px;")
        self.filter_switch_btn.clicked.connect(self.toggle_trade_filter)
        self.filter_switch_btn.setEnabled(False)
        settings_layout.addWidget(self.filter_switch_btn)
        settings_layout.addStretch()
        top_layout.addLayout(settings_layout)

        # --- 搜索区域 ---
        search_layout = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("输入关键词搜索（匹配标题/内容）...")
        self.search_edit.setMinimumWidth(300)
        search_layout.addWidget(QLabel("搜索:"))
        search_layout.addWidget(self.search_edit)
        search_layout.addSpacing(10)

        self.search_btn = QPushButton("搜索")
        self.search_btn.setStyleSheet("background-color: #FFC107; color: black; padding: 5px 15px;")
        self.search_btn.clicked.connect(self.search_posts)
        search_layout.addWidget(self.search_btn)

        self.clear_search_btn = QPushButton("清空搜索")
        self.clear_search_btn.setStyleSheet("background-color: #9E9E9E; color: white; padding: 5px 15px;")
        self.clear_search_btn.clicked.connect(self.clear_search)
        search_layout.addWidget(self.clear_search_btn)
        search_layout.addStretch()
        top_layout.addLayout(search_layout)
        main_layout.addLayout(top_layout)

        # --- 按钮区域 ---
        control_layout = QHBoxLayout()
        self.query_btn = QPushButton("手动查询")
        self.query_btn.setStyleSheet("background-color: #4CAF50; color: white; padding: 5px 15px;")
        self.query_btn.clicked.connect(self.handle_manual_query)
        control_layout.addWidget(self.query_btn)
        control_layout.addSpacing(20)

        self.start_timed_btn = QPushButton("启动定时爬取")
        self.start_timed_btn.setStyleSheet(
            "background-color: #2196F3; color: white; padding: 5px 15px; font-weight: bold;")
        self.start_timed_btn.clicked.connect(self.start_timed_crawl)
        control_layout.addWidget(self.start_timed_btn)

        self.stop_timed_btn = QPushButton("停止定时爬取")
        self.stop_timed_btn.setStyleSheet("background-color: #f44336; color: white; padding: 5px 15px;")
        self.stop_timed_btn.clicked.connect(self.stop_timed_crawl)
        self.stop_timed_btn.setEnabled(False)
        control_layout.addWidget(self.stop_timed_btn)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setMinimumWidth(300)
        self.progress_bar.setVisible(False)
        control_layout.addSpacing(20)
        control_layout.addWidget(QLabel("进度:"))
        control_layout.addWidget(self.progress_bar)
        control_layout.addStretch()
        main_layout.addLayout(control_layout)

        self.timed_status_label = QLabel(
            f"定时任务状态：未启动（当前配置：每 {self.config['interval_minutes']} 分钟循环一次）")
        self.timed_status_label.setStyleSheet("color: #666; font-size: 12px;")
        main_layout.addWidget(self.timed_status_label)

        # --- 表格区域 ---
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["发布时间", "帖子标题", "帖子内容", "评论数目", "匹配关键词"])
        self.table.setColumnWidth(0, 180)
        self.table.setColumnWidth(1, 250)
        self.table.setColumnWidth(2, 400)
        self.table.setColumnWidth(3, 80)
        self.table.horizontalHeader().setStretchLastSection(True)
        main_layout.addWidget(self.table)

        # --- 底部 ---
        bottom_layout = QHBoxLayout()
        self.save_btn = QPushButton("保存为Excel")
        self.save_btn.clicked.connect(self.save_to_excel)
        self.save_btn.setEnabled(False)
        bottom_layout.addWidget(self.save_btn)
        self.status_label = QLabel("状态: 等待操作...")
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.status_label)
        main_layout.addLayout(bottom_layout)

        self.show()

    # --- 设置相关 ---
    def open_settings(self):
        dialog = SettingsDialog(self.config, self)
        dialog.config_saved_signal.connect(self.on_config_saved)
        dialog.exec_()

    def on_config_saved(self, new_config):
        self.config = new_config
        status_text = f"定时任务状态：{'运行中' if self.timed_crawler and self.timed_crawler.isRunning() else '未启动'}"
        status_text += f"（当前配置：每 {self.config['interval_minutes']} 分钟循环一次）"
        self.timed_status_label.setText(status_text)

        # 如果正在运行，实时更新时间间隔
        if self.timed_crawler and self.timed_crawler.isRunning():
            self.timed_crawler.update_interval(new_config["interval_minutes"])

    # --- 手动查询相关 ---
    def update_end_time(self):
        self.end_time_edit.setDateTime(QDateTime.currentDateTime())

    def handle_manual_query(self):
        if self.timed_crawler and self.timed_crawler.isRunning():
            QMessageBox.warning(self, "操作冲突", "定时爬取任务正在运行，请先停止！")
            return
        self.update_end_time()
        start_str = self.start_time_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")
        end_str = self.end_time_edit.dateTime().toString("yyyy-MM-dd HH:mm:ss")

        self.query_btn.setEnabled(False)
        self.start_timed_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"状态: 手动查询中...（{start_str} 至 {end_str}）")
        self.is_manual_crawling = True

        self.crawler_thread = CrawlerThread(start_str, end_str)
        self.crawler_thread.progress_update.connect(self.update_progress)
        self.crawler_thread.result_signal.connect(self.handle_manual_result)
        self.crawler_thread.error_signal.connect(self.handle_error)
        self.crawler_thread.finished_signal.connect(self.manual_finished)
        self.crawler_thread.start()

    def handle_manual_result(self, data):
        self.all_data = data
        self.apply_filter_search()
        self.status_label.setText(f"状态: 手动查询完成，共找到 {len(data)} 条记录")
        self.save_btn.setEnabled(len(data) > 0)
        self.filter_switch_btn.setEnabled(len(data) > 0)

    # --- 定时爬取核心逻辑 ---
    def start_timed_crawl(self):
        """启动定时任务"""
        if self.timed_crawler and self.timed_crawler.isRunning(): return
        if self.is_manual_crawling:
            QMessageBox.warning(self, "冲突", "手动查询正在进行中，请稍后")
            return

        # 清空之前的数据，准备开始监控
        self.clear_page_data()

        # 创建线程，传入当前的配置间隔
        interval = self.config["interval_minutes"]
        self.timed_crawler = TimedCrawlerThread(interval, self)

        # 连接信号
        self.timed_crawler.new_posts_signal.connect(self.handle_new_timed_posts)
        self.timed_crawler.status_signal.connect(lambda s: self.timed_status_label.setText(f"定时任务状态：{s}"))
        self.timed_crawler.progress_update.connect(self.update_progress)

        # 启动
        self.timed_crawler.start()

        # UI更新
        self.start_timed_btn.setEnabled(False)
        self.stop_timed_btn.setEnabled(True)
        self.query_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

    def stop_timed_crawl(self):
        """停止定时任务"""
        if not self.timed_crawler or not self.timed_crawler.isRunning(): return
        self.stop_timed_btn.setEnabled(False)
        self.status_label.setText("状态: 正在停止定时爬取任务...")

        # 使用工作线程优雅停止
        stop_thread = QThread()
        stop_worker = StopWorker(self.timed_crawler)
        stop_worker.moveToThread(stop_thread)
        stop_worker.finished_signal.connect(lambda: self.on_stop_finished(stop_thread, stop_worker))
        stop_thread.started.connect(stop_worker.run)
        stop_thread.start()

    def on_stop_finished(self, thread, worker):
        worker.deleteLater()
        thread.quit()
        thread.wait()
        self.timed_crawler = None
        self.start_timed_btn.setEnabled(True)
        self.stop_timed_btn.setEnabled(False)
        self.query_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("状态: 定时爬取任务已停止")

    def handle_new_timed_posts(self, new_posts, start_str, end_str):
        """
        接收定时爬取的结果
        1. 更新表格
        2. 如果有买卖相关帖子，弹出窗口
        """
        # 更新总数据（倒序，新的在前）
        self.all_data = new_posts + self.all_data
        self.apply_filter_search()

        count = len(new_posts)
        msg = f"状态: 监控刷新 ({start_str} - {end_str})，新增 {count} 条相关帖子"
        self.status_label.setText(msg)
        self.save_btn.setEnabled(len(self.all_data) > 0)
        self.filter_switch_btn.setEnabled(len(self.all_data) > 0)

        # --- 关键：如果有新帖子，弹出通知 ---
        if count > 0:
            # 如果之前的弹窗还开着，先关闭它
            if self.notification_window:
                self.notification_window.close()

            # 创建新弹窗
            self.notification_window = NotificationWidget(new_posts)
            self.notification_window.show()

    # --- 通用UI逻辑 ---
    def apply_filter_search(self):
        data = self.all_data
        if self.is_filtered:
            data = [p for p in data if TRADE_PATTERN.search(p[1]) or TRADE_PATTERN.search(p[2])]

        kw = self.search_edit.text().strip().lower()
        if kw:
            data = [p for p in data if kw in p[1].lower() or kw in p[2].lower()]

        self.current_data = data
        self.refresh_table()

    def update_progress(self, value, desc):
        self.progress_bar.setValue(value)
        self.status_label.setText(f"状态: {desc}")

    def handle_error(self, msg):
        self.status_label.setText(f"错误: {msg}")
        QMessageBox.warning(self, "错误", msg)
        self.progress_bar.setValue(0)

    def manual_finished(self):
        self.is_manual_crawling = False
        self.query_btn.setEnabled(True)
        self.start_timed_btn.setEnabled(True)
        self.progress_bar.setVisible(False)

    def clear_page_data(self):
        self.all_data.clear()
        self.current_data.clear()
        self.table.setRowCount(0)
        self.is_filtered = False
        self.filter_switch_btn.setText("筛选买卖相关（未开启）")
        self.filter_switch_btn.setStyleSheet("background-color: #9E9E9E; color: white; padding: 5px 15px;")
        self.save_btn.setEnabled(False)

    def refresh_table(self):
        self.table.setRowCount(0)
        for row, data in enumerate(self.current_data):
            self.table.insertRow(row)
            for col, txt in enumerate(data):
                item = QTableWidgetItem(txt)
                if col in [0, 3, 4]:
                    item.setTextAlignment(Qt.AlignCenter)
                else:
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                self.table.setItem(row, col, item)

    def toggle_trade_filter(self):
        self.is_filtered = not self.is_filtered
        if self.is_filtered:
            self.filter_switch_btn.setText("筛选买卖相关（已开启）")
            self.filter_switch_btn.setStyleSheet("background-color: #2196F3; color: white; padding: 5px 15px;")
        else:
            self.filter_switch_btn.setText("筛选买卖相关（未开启）")
            self.filter_switch_btn.setStyleSheet("background-color: #9E9E9E; color: white; padding: 5px 15px;")
        self.apply_filter_search()

    def search_posts(self):
        self.apply_filter_search()

    def clear_search(self):
        self.search_edit.clear()
        self.apply_filter_search()

    def save_to_excel(self):
        if not pd: return
        if not self.current_data: return
        df = pd.DataFrame(self.current_data, columns=["发布时间", "帖子标题", "帖子内容", "评论数目", "匹配关键词"])
        fname = f"帖子查询结果_{QDateTime.currentDateTime().toString('yyyyMMddHHmmss')}.xlsx"
        try:
            df.to_excel(fname, index=False, engine='openpyxl')
            QMessageBox.information(self, "成功", f"已保存至: {fname}")
        except Exception as e:
            QMessageBox.warning(self, "失败", str(e))

    def closeEvent(self, event):

        if self.timed_crawler and self.timed_crawler.isRunning():
            self.timed_crawler.stop()
        if self.is_manual_crawling and self.crawler_thread:
            self.crawler_thread.abort()
        if self.notification_window:
            self.notification_window.close()
        event.ignore()  # 忽略默认的关闭事件
        self.hide()  # 隐藏当前窗口，而不是关闭
        # event.accept()


# -------------------------- 停止任务工作线程 --------------------------
class StopWorker(QObject):
    finished_signal = pyqtSignal()

    def __init__(self, crawler):
        super().__init__()
        self.crawler = crawler

    def run(self):
        self.crawler.stop()
        self.finished_signal.emit()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = PostQueryTool()
    sys.exit(app.exec_())