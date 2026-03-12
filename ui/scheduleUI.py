import sys
import csv
import os
from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *


def hex_to_rgba(hex_color, alpha):
    c = QColor(hex_color)
    return f"rgba({c.red()}, {c.green()}, {c.blue()}, {alpha})"


# ================= 🚀 强制置顶悬浮提醒卡片 (不点关闭绝对不消失) =================
class AlarmWindow(QWidget):
    closed_signal = pyqtSignal(object)

    def __init__(self, title, message, color_hex, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(320, 130)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(0)

        # 主卡片
        card = QFrame(self)
        card.setObjectName("alarmCard")
        card.setStyleSheet("""
            QFrame#alarmCard {
                background-color: white;
                border: 1px solid #e2e8f0;
                border-radius: 10px;
            }
        """)

        # 阴影
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(15, 23, 42, 40))
        card.setGraphicsEffect(shadow)

        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.setSpacing(0)

        # 左侧强调色条
        side_bar = QFrame()
        side_bar.setFixedWidth(6)
        side_bar.setStyleSheet(f"""
            background-color: {color_hex};
            border-top-left-radius: 10px;
            border-bottom-left-radius: 10px;
        """)

        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(16, 14, 16, 12)
        content_layout.setSpacing(8)

        # 标题行
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(6)

        dot = QLabel("●")
        dot.setStyleSheet(f"color: {color_hex}; font-size: 11px; border: none;")

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"font-size: 15px; font-weight: 700; color: {color_hex}; border: none;"
        )

        header_layout.addWidget(dot)
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        # 内容
        msg_lbl = QLabel(message)
        msg_lbl.setWordWrap(True)
        msg_lbl.setStyleSheet("""
            font-size: 13px;
            color: #475569;
            border: none;
            padding-left: 1px;
        """)

        content_layout.addLayout(header_layout)
        content_layout.addWidget(msg_lbl)
        content_layout.addStretch()

        # 按钮
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(0)

        self.close_btn = QPushButton("我知道了")
        self.close_btn.setCursor(Qt.PointingHandCursor)
        self.close_btn.setFixedSize(92, 34)
        self.close_btn.setFocusPolicy(Qt.NoFocus)

        btn_bg = hex_to_rgba(color_hex, 24)
        btn_hover = hex_to_rgba(color_hex, 38)
        btn_pressed = hex_to_rgba(color_hex, 55)
        btn_border = hex_to_rgba(color_hex, 90)

        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {btn_bg};
                color: {color_hex};
                border: 1px solid {btn_border};
                border-radius: 6px;
                padding: 0 14px;
                font-weight: bold;
                font-size: 13px;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
            QPushButton:pressed {{
                background-color: {btn_pressed};
            }}
        """)
        self.close_btn.clicked.connect(self.close_window)

        btn_layout.addStretch()
        btn_layout.addWidget(self.close_btn)

        content_layout.addLayout(btn_layout)

        card_layout.addWidget(side_bar)
        card_layout.addWidget(content_widget)

        root_layout.addWidget(card)

    def show_corner(self, offset_index=0):
        screen = QApplication.desktop().availableGeometry()
        x = screen.width() - self.width() - 20
        y = screen.height() - self.height() - 20 - (offset_index * (self.height() + 10))
        self.move(x, y)
        self.show()
        self.raise_()
        self.activateWindow()

    def close_window(self):
        self.closed_signal.emit(self)
        self.close()


# ================= 后台提醒服务：桌宠启动即自动运行 =================
class ScheduleReminderService(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.data_dir = './data/schedule/'
        self.todo_file = os.path.join(self.data_dir, 'todo.csv')
        os.makedirs(self.data_dir, exist_ok=True)

        self.active_alarms = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_due_tasks)

    def start(self):
        if not self.timer.isActive():
            self.timer.start(10000)  # 每10秒扫描一次
        self.check_due_tasks()       # 启动后立即检查一次

    def _load_todo_data(self):
        tasks = []
        if not os.path.exists(self.todo_file):
            return tasks

        try:
            with open(self.todo_file, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 4:
                        due_date_str = row[2]
                        if len(due_date_str) == 16:
                            due_date_str += ":00"

                        notify_state = row[4] if len(row) > 4 else "0"

                        tasks.append({
                            "title": row[0],
                            "description": row[1],
                            "due_date": due_date_str,
                            "priority": row[3],
                            "notify_state": notify_state
                        })
        except Exception:
            pass

        return tasks

    def _save_todo_data(self, tasks):
        try:
            with open(self.todo_file, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                for data in tasks:
                    writer.writerow([
                        data['title'],
                        data['description'],
                        data['due_date'],
                        data['priority'],
                        data.get('notify_state', '0')
                    ])
        except Exception:
            pass

    def check_due_tasks(self):
        now = QDateTime.currentDateTime()
        tasks = self._load_todo_data()
        changed = False

        for data in tasks:
            target = QDateTime.fromString(data['due_date'], "yyyy-MM-dd HH:mm:ss")
            if not target.isValid():
                continue

            secs_diff = now.secsTo(target)

            raw_state = str(data.get('notify_state', '0'))
            if raw_state == 'False':
                notify_state = 0
            elif raw_state == 'True':
                notify_state = 3
            else:
                try:
                    notify_state = int(raw_state)
                except Exception:
                    notify_state = 0

            trigger_alarm = False
            title = ""
            msg = ""
            color = ""

            # 策略 3: 已经到期了
            if secs_diff <= 0 and notify_state < 3:
                title = "🚨 任务已到期！"
                msg = f"【{data['title']}】时间已用尽，请立即确认处理状态！"
                color = "#ef4444"
                data['notify_state'] = "3"
                trigger_alarm = True
                changed = True

            # 策略 2: 剩下不到 15 分钟
            elif 0 < secs_diff <= 15 * 60 and notify_state < 2:
                title = "⏳ 冲刺预警（不足15分钟）"
                msg = f"【{data['title']}】即将到期，请抓紧最后时间收尾！"
                color = "#f59e0b"
                data['notify_state'] = "2"
                trigger_alarm = True
                changed = True

            # 策略 1: 剩下不到 1 小时
            elif 15 * 60 < secs_diff <= 60 * 60 and notify_state < 1:
                title = "⏰ 温馨提醒（不足1小时）"
                msg = f"【{data['title']}】还有不到1小时到期，请合理安排手头工作。"
                color = "#3b82f6"
                data['notify_state'] = "1"
                trigger_alarm = True
                changed = True

            if trigger_alarm:
                self.show_alarm_window(title, msg, color)

        if changed:
            self._save_todo_data(tasks)

    def show_alarm_window(self, title, msg, color):
        alarm = AlarmWindow(title, msg, color)
        alarm.closed_signal.connect(self.remove_alarm)
        self.active_alarms.append(alarm)
        alarm.show_corner(len(self.active_alarms) - 1)

    def remove_alarm(self, alarm_window):
        if alarm_window in self.active_alarms:
            self.active_alarms.remove(alarm_window)

        # 关闭一个后，其余弹窗重新排队
        for idx, alarm in enumerate(self.active_alarms):
            if alarm.isVisible():
                alarm.show_corner(idx)


_schedule_reminder_service = None


def ensure_schedule_reminder_service():
    global _schedule_reminder_service

    app = QApplication.instance()
    if app is None:
        return None

    if _schedule_reminder_service is None:
        _schedule_reminder_service = ScheduleReminderService(app)
        _schedule_reminder_service.start()

    return _schedule_reminder_service


def install_schedule_service_bootstrap():
    if getattr(QApplication, "_schedule_service_bootstrap_installed", False):
        return

    QApplication._schedule_service_bootstrap_installed = True
    original_init = QApplication.__init__

    def patched_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        QTimer.singleShot(0, ensure_schedule_reminder_service)

    QApplication.__init__ = patched_init


# 模块导入时就安装启动钩子
install_schedule_service_bootstrap()

# 如果 QApplication 已经存在，则直接补启动
if QApplication.instance() is not None:
    QTimer.singleShot(0, ensure_schedule_reminder_service)


# ================= 🚀 自定义高颜值删除确认框 (替代丑陋的 QMessageBox) =================
class ConfirmDialog(QDialog):
    def __init__(self, title, message, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedSize(320, 160)
        self.setStyleSheet("QDialog { background-color: #ffffff; font-family: 'Microsoft YaHei'; }")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 25, 25, 20)
        layout.setSpacing(15)

        # 提示文字
        msg_label = QLabel(message)
        msg_label.setWordWrap(True)
        msg_label.setStyleSheet("font-size: 15px; color: #334155; font-weight: bold;")
        layout.addWidget(msg_label)

        layout.addStretch()

        # 按钮布局
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        no_btn = QPushButton("取消")
        no_btn.setCursor(Qt.PointingHandCursor)
        no_btn.setStyleSheet(
            "QPushButton { background-color: #f1f5f9; color: #475569; padding: 8px 20px; border-radius: 6px; font-weight: bold; border:none; } QPushButton:hover { background-color: #e2e8f0; }"
        )
        no_btn.clicked.connect(self.reject)

        yes_btn = QPushButton("确定删除")
        yes_btn.setCursor(Qt.PointingHandCursor)
        yes_btn.setStyleSheet(
            "QPushButton { background-color: #ef4444; color: white; padding: 8px 20px; border-radius: 6px; font-weight: bold; border:none; } QPushButton:hover { background-color: #dc2626; }"
        )
        yes_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(no_btn)
        btn_layout.addWidget(yes_btn)

        layout.addLayout(btn_layout)


# ================= 数字滚轮组件 =================
class NumberWheel(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(self, max_val, current_val=0, parent=None):
        super().__init__(parent)
        self.max_val = max_val
        self.current_val = current_val
        self.item_height = 40
        self.scroll_y = current_val * self.item_height
        self.last_y = 0
        self.setFixedSize(60, self.item_height * 3)
        self.setCursor(Qt.SizeVerCursor)
        self.anim = QPropertyAnimation(self, b"scroll_y_prop")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.OutQuad)

    def setValue(self, val):
        self.current_val = max(0, min(self.max_val, val))
        self.scroll_y = self.current_val * self.item_height
        self.update()

    def mousePressEvent(self, e):
        self.anim.stop()
        self.last_y = e.pos().y()

    def mouseMoveEvent(self, e):
        dy = self.last_y - e.pos().y()
        self.scroll_y += dy
        self.scroll_y = max(
            -self.item_height / 2,
            min(self.scroll_y, self.max_val * self.item_height + self.item_height / 2)
        )
        self.last_y = e.pos().y()
        self.update()

    def mouseReleaseEvent(self, e):
        target_idx = round(self.scroll_y / self.item_height)
        target_idx = max(0, min(self.max_val, target_idx))
        self.anim.setStartValue(self.scroll_y)
        self.anim.setEndValue(target_idx * self.item_height)
        self.anim.start()
        if self.current_val != target_idx:
            self.current_val = target_idx
            self.valueChanged.emit(self.current_val)

    def wheelEvent(self, e):
        steps = -1 if e.angleDelta().y() > 0 else 1
        target_idx = max(0, min(self.max_val, self.current_val + steps))
        self.anim.stop()
        self.anim.setStartValue(self.scroll_y)
        self.anim.setEndValue(target_idx * self.item_height)
        self.anim.start()
        if self.current_val != target_idx:
            self.current_val = target_idx
            self.valueChanged.emit(self.current_val)

    @pyqtProperty(float)
    def scroll_y_prop(self):
        return self.scroll_y

    @scroll_y_prop.setter
    def scroll_y_prop(self, val):
        self.scroll_y = val
        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        center_rect = QRect(0, self.item_height, self.width(), self.item_height)
        painter.fillRect(center_rect, QColor("#e3f2fd"))
        painter.setPen(QPen(QColor("#bae6fd"), 1))
        painter.drawLine(0, self.item_height, self.width(), self.item_height)
        painter.drawLine(0, self.item_height * 2, self.width(), self.item_height * 2)

        float_idx = self.scroll_y / self.item_height
        for i in range(self.max_val + 1):
            y_pos = (i - float_idx) * self.item_height + self.item_height
            if -self.item_height <= y_pos <= self.height():
                rect = QRect(0, int(y_pos), self.width(), self.item_height)
                dist = abs(i - float_idx)
                if dist < 0.5:
                    painter.setPen(QPen(QColor("#0f172a")))
                    font = QFont("Microsoft YaHei", 15, QFont.Bold)
                else:
                    opacity = max(0, 255 - int(dist * 120))
                    painter.setPen(QPen(QColor(148, 163, 184, opacity)))
                    font = QFont("Microsoft YaHei", 12)
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignCenter, f"{i:02d}")


# ================= 触发器：点击弹出的时间按钮 =================
class SlideTimePicker(QPushButton):
    def __init__(self, time_val, parent=None):
        super().__init__(parent)
        self.time_val = time_val
        self.setText(self.time_val.toString("HH : mm : ss"))
        self.setCursor(Qt.PointingHandCursor)
        self.clicked.connect(self.show_popup)

    def set_time(self, new_time):
        self.time_val = new_time
        self.setText(self.time_val.toString("HH : mm : ss"))

    def show_popup(self):
        self.popup = QWidget(self.window(), Qt.Popup | Qt.FramelessWindowHint)
        self.popup.setAttribute(Qt.WA_TranslucentBackground)
        main_frame = QFrame(self.popup)
        main_frame.setStyleSheet(
            "QFrame { background-color: white; border: 1px solid #cbd5e1; border-radius: 12px; } "
            "QLabel#title { font-size: 13px; color: #64748b; font-weight: bold; background: transparent; border: none; }"
        )
        layout = QHBoxLayout(main_frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        def create_column(title_text, max_val, current_val, callback):
            col = QVBoxLayout()
            title = QLabel(title_text)
            title.setObjectName("title")
            title.setAlignment(Qt.AlignCenter)
            wheel = NumberWheel(max_val, current_val)
            wheel.valueChanged.connect(callback)
            col.addWidget(title)
            col.addWidget(wheel)
            return col

        layout.addLayout(create_column("时", 23, self.time_val.hour(), self.set_hour))
        layout.addLayout(create_column("分", 59, self.time_val.minute(), self.set_minute))
        layout.addLayout(create_column("秒", 59, self.time_val.second(), self.set_second))

        popup_layout = QVBoxLayout(self.popup)
        popup_layout.setContentsMargins(0, 0, 0, 0)
        popup_layout.addWidget(main_frame)

        pos = self.mapToGlobal(self.rect().bottomLeft())
        self.popup.setGeometry(pos.x(), pos.y() + 5, 260, 200)
        self.popup.show()

    def set_hour(self, h):
        self.time_val.setHMS(h, self.time_val.minute(), self.time_val.second())
        self.setText(self.time_val.toString("HH : mm : ss"))

    def set_minute(self, m):
        self.time_val.setHMS(self.time_val.hour(), m, self.time_val.second())
        self.setText(self.time_val.toString("HH : mm : ss"))

    def set_second(self, s):
        self.time_val.setHMS(self.time_val.hour(), self.time_val.minute(), s)
        self.setText(self.time_val.toString("HH : mm : ss"))


# ================= 自定义待办项 UI =================
class TaskItemWidget(QWidget):
    def __init__(self, title, description, due_date, priority, is_done=False, parent=None):
        super(TaskItemWidget, self).__init__(parent)
        self.title = title
        self.description = description
        self.due_date = due_date
        self.priority = priority
        self.is_done = is_done
        self.initUI()

    def initUI(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(15, 10, 15, 10)

        self.color_label = QLabel()
        self.color_label.setFixedSize(6, 40)
        self.color_label.setStyleSheet(f"background-color: {self.get_priority_color()}; border-radius: 3px;")

        text_layout = QVBoxLayout()
        self.title_label = QLabel(self.title)

        font = QFont("Microsoft YaHei", 12, QFont.Bold)
        time_text, time_color = self.parse_smart_time()

        if self.is_done:
            font.setStrikeOut(True)
            self.title_label.setStyleSheet("color: #95a5a6;")
            time_text = "已完成"
            time_color = "#95a5a6"

        self.title_label.setFont(font)

        self.date_label = QLabel(f"⏰ {time_text} ({self.due_date})")
        self.date_label.setStyleSheet(
            f"color: {time_color}; font-size: 12px; font-weight: bold; font-family: 'Microsoft YaHei';"
        )

        text_layout.addWidget(self.title_label)
        text_layout.addWidget(self.date_label)

        self.priority_label = QLabel(self.priority)
        self.priority_label.setAlignment(Qt.AlignCenter)
        self.priority_label.setFixedSize(36, 24)
        self.priority_label.setStyleSheet(
            f"background-color: {self.get_priority_color()}22; color: {self.get_priority_color()}; "
            f"border-radius: 4px; font-weight: bold; font-size: 12px;"
        )

        layout.addWidget(self.color_label)
        layout.addSpacing(10)
        layout.addLayout(text_layout)
        layout.addStretch()
        layout.addWidget(self.priority_label)
        self.setLayout(layout)

    def parse_smart_time(self):
        now = QDateTime.currentDateTime()
        target = QDateTime.fromString(self.due_date, "yyyy-MM-dd HH:mm:ss")
        secs_diff = now.secsTo(target)
        days_diff = now.daysTo(target)
        if secs_diff < 0:
            return "🔥 已超期", "#ef4444"
        elif days_diff == 0:
            return "⚠️ 今天截止", "#f59e0b"
        elif days_diff == 1:
            return "🚀 明天截止", "#3b82f6"
        else:
            return f"还剩 {days_diff} 天", "#64748b"

    def get_priority_color(self):
        colors = {"高": "#ef4444", "中": "#f59e0b", "低": "#10b981"}
        return colors.get(self.priority, "#94a3b8")


# ================= 编辑弹窗 =================
class ItemDialog(QDialog):
    def __init__(self, title="", description="", due_date=None, priority="中", parent=None):
        super(ItemDialog, self).__init__(parent)
        self.setWindowTitle('✨ 任务详情')
        self.setFixedSize(460, 520)
        self.title_val = title
        self.desc_val = description
        self.date_val = due_date if due_date else QDateTime.currentDateTime()
        self.priority_val = priority
        self.initUI()
        self.apply_styles()

    def initUI(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(18)

        self.titleEdit = QLineEdit(self.title_val)
        self.titleEdit.setPlaceholderText("📝 请输入任务标题...")
        layout.addWidget(self.titleEdit)

        self.describeEdit = QTextEdit(self.desc_val)
        self.describeEdit.setPlaceholderText("补充详细描述（可选）...")
        layout.addWidget(self.describeEdit)

        layout.addWidget(QLabel('快捷设定截止时间:'))

        quick_date_layout = QHBoxLayout()
        btn_today = QPushButton("今天")
        btn_tomorrow = QPushButton("明天")
        btn_nextweek = QPushButton("下周")

        for btn in [btn_today, btn_tomorrow, btn_nextweek]:
            btn.setObjectName("quickBtn")
            btn.setCursor(Qt.PointingHandCursor)
            quick_date_layout.addWidget(btn)

        btn_today.clicked.connect(lambda: self.set_quick_date(0))
        btn_tomorrow.clicked.connect(lambda: self.set_quick_date(1))
        btn_nextweek.clicked.connect(lambda: self.set_quick_date(7))
        layout.addLayout(quick_date_layout)

        picker_layout = QHBoxLayout()
        self.datePicker = QDateEdit(self.date_val.date())
        self.datePicker.setCalendarPopup(True)
        self.datePicker.setDisplayFormat("yyyy年 MM月 dd日")
        self.timePicker = SlideTimePicker(self.date_val.time())
        picker_layout.addWidget(self.datePicker, 3)
        picker_layout.addWidget(self.timePicker, 2)
        layout.addLayout(picker_layout)

        layout.addWidget(QLabel('任务优先级:'))

        priority_layout = QHBoxLayout()
        self.priority_group = QButtonGroup(self)
        self.btn_high = QPushButton("高")
        self.btn_mid = QPushButton("中")
        self.btn_low = QPushButton("低")

        for p_name, btn in {"高": self.btn_high, "中": self.btn_mid, "低": self.btn_low}.items():
            btn.setCheckable(True)
            btn.setObjectName("priorityBtn")
            btn.setCursor(Qt.PointingHandCursor)
            self.priority_group.addButton(btn)
            priority_layout.addWidget(btn)
            if p_name == self.priority_val:
                btn.setChecked(True)

        layout.addLayout(priority_layout)
        layout.addStretch()

        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton('取消')
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton('💾 保存任务')
        save_btn.setObjectName("saveBtn")
        save_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def apply_styles(self):
        self.setStyleSheet("""
            QDialog { background-color: #ffffff; font-family: 'Microsoft YaHei'; }
            QLabel { color: #475569; font-weight: bold; font-size: 13px; }
            QLineEdit, QTextEdit, QDateEdit, SlideTimePicker {
                border: 1px solid #cbd5e1;
                border-radius: 8px;
                padding: 10px;
                background-color: #f8fafc;
                font-size: 14px;
                color: #334155;
            }
            QLineEdit:focus, QTextEdit:focus, QDateEdit:focus, SlideTimePicker:hover {
                border: 2px solid #3b82f6;
                background-color: #ffffff;
            }
            QDateEdit::drop-down { border: none; padding-right: 10px; }
            #quickBtn {
                background-color: #f1f5f9;
                border: none;
                border-radius: 6px;
                padding: 10px;
                color: #475569;
                font-weight: bold;
            }
            #quickBtn:hover { background-color: #e2e8f0; }
            #priorityBtn {
                background-color: #f8fafc;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 8px;
                font-weight: bold;
                color: #475569;
            }
            #priorityBtn:checked {
                background-color: #eff6ff;
                border: 2px solid #3b82f6;
                color: #2563eb;
            }
            #cancelBtn {
                background-color: transparent;
                border: 1px solid #cbd5e1;
                color: #64748b;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
            }
            #cancelBtn:hover { background-color: #f1f5f9; }
            #saveBtn {
                background-color: #3b82f6;
                color: white;
                border: none;
                padding: 10px 25px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }
            #saveBtn:hover { background-color: #2563eb; }
        """)

    def set_quick_date(self, days_added):
        new_date = QDate.currentDate().addDays(days_added)
        self.datePicker.setDate(new_date)
        self.timePicker.set_time(QTime(23, 59, 59))

    def get_data(self):
        selected_priority = "中"
        if self.btn_high.isChecked():
            selected_priority = "高"
        elif self.btn_low.isChecked():
            selected_priority = "低"

        final_datetime = QDateTime(self.datePicker.date(), self.timePicker.time_val)

        return {
            "title": self.titleEdit.text().strip(),
            "description": self.describeEdit.toPlainText().strip(),
            "due_date": final_datetime.toString("yyyy-MM-dd HH:mm:ss"),
            "priority": selected_priority,
            "notify_state": "0"
        }


# ================= 主控制台 =================
class TodoApp(QMainWindow):
    def __init__(self):
        super(TodoApp, self).__init__()
        self.data_dir = './data/schedule/'
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

        self.initUI()
        self.apply_stylesheet()
        self.load_data()

        # 确保后台提醒服务存在，但不在窗口里重复启动一套定时器
        self.reminder_service = ensure_schedule_reminder_service()

    def initUI(self):
        self.resize(850, 650)
        self.setWindowTitle('⚡ 极速日程管理枢纽')

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)

        quick_add_layout = QHBoxLayout()
        self.quick_input = QLineEdit()
        self.quick_input.setPlaceholderText("✍️ 输入任务标题，按回车弹出详情设定...")
        self.quick_input.setMinimumHeight(45)
        self.quick_input.returnPressed.connect(self.open_add_dialog)

        add_btn = QPushButton("添加任务")
        add_btn.setMinimumHeight(45)
        add_btn.setFixedWidth(100)
        add_btn.setCursor(Qt.PointingHandCursor)
        add_btn.clicked.connect(self.open_add_dialog)

        quick_add_layout.addWidget(self.quick_input)
        quick_add_layout.addWidget(add_btn)
        main_layout.addLayout(quick_add_layout)
        main_layout.addSpacing(15)

        lists_layout = QHBoxLayout()

        todo_layout = QVBoxLayout()
        todo_layout.addWidget(QLabel("🎯 待办事项"))
        self.todoList = QListWidget()
        self.todoList.itemDoubleClicked.connect(self.edit_task)
        todo_layout.addWidget(self.todoList)

        self.complete_btn = QPushButton('✔️ 标记为已完成')
        self.complete_btn.setStyleSheet("background-color: #10b981; color: white; padding: 10px; border-radius: 5px;")
        self.complete_btn.clicked.connect(self.move_to_done)
        todo_layout.addWidget(self.complete_btn)

        done_layout = QVBoxLayout()
        done_layout.addWidget(QLabel("✅ 已完成归档"))
        self.doneList = QListWidget()
        self.doneList.itemDoubleClicked.connect(self.edit_task)
        done_layout.addWidget(self.doneList)

        self.delete_btn = QPushButton('🗑️ 彻底删除')
        self.delete_btn.setStyleSheet("background-color: #ef4444; color: white; padding: 10px; border-radius: 5px;")
        self.delete_btn.clicked.connect(self.delete_task)
        done_layout.addWidget(self.delete_btn)

        lists_layout.addLayout(todo_layout)
        lists_layout.addLayout(done_layout)
        main_layout.addLayout(lists_layout)

    def apply_stylesheet(self):
        self.setStyleSheet("""
            TodoApp { font-family: 'Microsoft YaHei'; background-color: #f8fafc; }
            QLineEdit {
                border: 2px solid #e2e8f0;
                border-radius: 8px;
                font-size: 15px;
                padding-left: 15px;
                background: white;
            }
            QLineEdit:focus { border: 2px solid #3b82f6; }
            TodoApp > QWidget > QVBoxLayout > QHBoxLayout > QPushButton {
                font-weight: bold;
                border: none;
                background-color: #3b82f6;
                color: white;
                border-radius: 8px;
            }
            TodoApp > QWidget > QVBoxLayout > QHBoxLayout > QPushButton:hover {
                background-color: #2563eb;
            }
            QListWidget {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 10px;
                outline: none;
            }
            QListWidget::item { border-bottom: 1px solid #f1f5f9; }
            QListWidget::item:selected {
                background-color: #eff6ff;
                border-radius: 4px;
            }
            QLabel { color: #334155; font-weight: bold; font-size: 14px; }
        """)

    # ================= 业务逻辑 =================
    def open_add_dialog(self):
        title = self.quick_input.text().strip()
        dialog = ItemDialog(title=title, parent=self)
        if dialog.exec_() == QDialog.Accepted:
            data = dialog.get_data()
            if not data['title']:
                QMessageBox.warning(self, "提示", "任务标题不能为空！")
                return
            self.add_task_to_list(self.todoList, data)
            self.quick_input.clear()
            self.save_data()

    def add_task_to_list(self, list_widget, data, is_done=False):
        item = QListWidgetItem(list_widget)
        item.setSizeHint(QSize(0, 85))
        item.setData(Qt.UserRole, data)
        widget = TaskItemWidget(data['title'], data['description'], data['due_date'], data['priority'], is_done)
        list_widget.setItemWidget(item, widget)

    def edit_task(self, item):
        list_widget = item.listWidget()
        is_done = (list_widget == self.doneList)

        data = item.data(Qt.UserRole)
        due_date = QDateTime.fromString(data['due_date'], "yyyy-MM-dd HH:mm:ss")
        dialog = ItemDialog(data['title'], data['description'], due_date, data['priority'], self)

        if dialog.exec_() == QDialog.Accepted:
            new_data = dialog.get_data()
            if new_data['due_date'] != data['due_date']:
                new_data['notify_state'] = "0"
            else:
                new_data['notify_state'] = data.get('notify_state', "0")

            item.setData(Qt.UserRole, new_data)
            widget = TaskItemWidget(
                new_data['title'],
                new_data['description'],
                new_data['due_date'],
                new_data['priority'],
                is_done
            )
            list_widget.setItemWidget(item, widget)
            self.save_data()

    def move_to_done(self):
        item = self.todoList.currentItem()
        if item:
            data = item.data(Qt.UserRole)
            self.todoList.takeItem(self.todoList.row(item))
            self.add_task_to_list(self.doneList, data, is_done=True)
            self.save_data()

    def delete_task(self):
        item = self.doneList.currentItem() or self.todoList.currentItem()
        if item:
            dialog = ConfirmDialog("⚠️ 确认删除", "确定要彻底删除该任务吗？此操作不可恢复。")
            if dialog.exec_() == QDialog.Accepted:
                item.listWidget().takeItem(item.listWidget().row(item))
                self.save_data()

    def save_data(self):
        self._save_list(self.todoList, os.path.join(self.data_dir, 'todo.csv'))
        self._save_list(self.doneList, os.path.join(self.data_dir, 'done.csv'))

    def _save_list(self, list_widget, filepath):
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            for i in range(list_widget.count()):
                data = list_widget.item(i).data(Qt.UserRole)
                writer.writerow([
                    data['title'],
                    data['description'],
                    data['due_date'],
                    data['priority'],
                    data.get('notify_state', '0')
                ])

    def load_data(self):
        self._load_list(self.todoList, os.path.join(self.data_dir, 'todo.csv'), is_done=False)
        self._load_list(self.doneList, os.path.join(self.data_dir, 'done.csv'), is_done=True)

    def _load_list(self, list_widget, filepath, is_done):
        if not os.path.exists(filepath):
            return

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                for row in reader:
                    if len(row) >= 4:
                        notify_state = row[4] if len(row) > 4 else "0"
                        due_date_str = row[2]
                        if len(due_date_str) == 16:
                            due_date_str += ":00"
                        data = {
                            "title": row[0],
                            "description": row[1],
                            "due_date": due_date_str,
                            "priority": row[3],
                            "notify_state": notify_state
                        }
                        self.add_task_to_list(list_widget, data, is_done)
        except Exception:
            pass

    def closeEvent(self, event):
         event.ignore()  # 忽略默认的关闭事件
         self.hide()  # 隐藏当前窗口，而不是关闭

if __name__ == '__main__':
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    app = QApplication(sys.argv)
    window = TodoApp()
    window.show()
    sys.exit(app.exec_())