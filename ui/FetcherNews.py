import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QTabWidget, QTableWidget, QTableWidgetItem,
                             QPushButton, QHeaderView, QLabel, QAbstractItemView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QColor, QFont, QDesktopServices

# 引入我们分离好的爬虫逻辑
from utils.fetcher_news import fetch_bilibili, fetch_weibo, fetch_zhihu

# ================= 强力爬虫线程 =================
class FetchDataThread(QThread):
    data_fetched = pyqtSignal(str, list)
    error_occurred = pyqtSignal(str, str)

    def __init__(self, platform):
        super().__init__()
        self.platform = platform

    def run(self):
        try:
            data = []
            if self.platform == "Bilibili (B站)":
                data = fetch_bilibili()
            elif self.platform == "Weibo (微博)":
                data = fetch_weibo()
            elif self.platform == "Zhihu (知乎)":
                data = fetch_zhihu()

            self.data_fetched.emit(self.platform, data)
        except Exception as e:
            self.error_occurred.emit(self.platform, str(e))

# ================= UI 主窗口类 =================
class HotBoardApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🔥 全网热榜数据终端 (防反爬增强版)")
        self.resize(1050, 700)
        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(25, 25, 25, 25)
        main_layout.setSpacing(20)

        top_layout = QHBoxLayout()
        title_label = QLabel("全网热点风向标")
        title_label.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
        title_label.setObjectName("mainTitle")

        self.refresh_btn = QPushButton(" 🔄 一键抓取最新数据 ")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.clicked.connect(self.refresh_all)

        top_layout.addWidget(title_label)
        top_layout.addStretch()
        top_layout.addWidget(self.refresh_btn)
        main_layout.addLayout(top_layout)

        self.tabs = QTabWidget()
        self.tabs.setCursor(Qt.ArrowCursor)
        main_layout.addWidget(self.tabs)

        # 移除了 Douyin
        self.platforms = ["Bilibili (B站)", "Weibo (微博)", "Zhihu (知乎)"]
        self.tables = {}

        for platform in self.platforms:
            table = QTableWidget(0, 5)
            table.setHorizontalHeaderLabels(["排 名", "标 题 / 热 词", "内 容 来 源", "热 度", "快 捷 操 作"])
            table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
            table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
            table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)

            table.setEditTriggers(QAbstractItemView.NoEditTriggers)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setFocusPolicy(Qt.NoFocus)
            table.setShowGrid(False)
            table.verticalHeader().setVisible(False)

            table.cellDoubleClicked.connect(self.open_link)
            self.tabs.addTab(table, platform)
            self.tables[platform] = table

        self.refresh_all()

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #F2F5F8; }
            #mainTitle { color: #1E293B; }
            QPushButton {
                background-color: #3B82F6;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 15px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
            }
            QPushButton:hover { background-color: #2563EB; }
            QPushButton:disabled { background-color: #93C5FD; }
            QTabWidget::pane { border: none; background: white; border-radius: 12px; }
            QTabBar::tab {
                background: transparent;
                color: #64748B;
                padding: 15px 30px;
                font-size: 16px;
                font-weight: bold;
                font-family: "Microsoft YaHei";
                border-bottom: 3px solid transparent;
            }
            QTabBar::tab:hover { color: #3B82F6; }
            QTabBar::tab:selected { color: #3B82F6; border-bottom: 3px solid #3B82F6; }
            QTableWidget {
                background-color: white;
                border-radius: 12px;
                font-family: "Microsoft YaHei";
                font-size: 15px;
                color: #334155;
            }
            QTableWidget::item { border-bottom: 1px solid #E2E8F0; padding: 8px; }
            QTableWidget::item:selected { background-color: #EFF6FF; color: #1D4ED8; }
            QHeaderView::section {
                background-color: #F8FAFC;
                color: #475569;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #E2E8F0;
                font-weight: bold;
                font-size: 15px;
            }
        """)

    def refresh_all(self):
        self.refresh_btn.setEnabled(False)
        self.refresh_btn.setText(" ⏳ 极速抓取中... ")
        self.active_threads = []

        for platform in self.platforms:
            self.tables[platform].setRowCount(0)
            thread = FetchDataThread(platform)
            thread.data_fetched.connect(self.update_table)
            thread.error_occurred.connect(self.handle_error)
            thread.finished.connect(self.thread_finished)
            self.active_threads.append(thread)
            thread.start()

    def update_table(self, platform, data):
        table = self.tables[platform]
        table.setRowCount(len(data))

        for row, item in enumerate(data):
            rank_cell = QTableWidgetItem(item['rank'])
            rank_cell.setTextAlignment(Qt.AlignCenter)
            font = QFont("Microsoft YaHei", 13, QFont.Bold)
            if int(item['rank']) == 1:
                rank_cell.setForeground(QColor("#EF4444"))
            elif int(item['rank']) == 2:
                rank_cell.setForeground(QColor("#F97316"))
            elif int(item['rank']) == 3:
                rank_cell.setForeground(QColor("#F59E0B"))
            else:
                rank_cell.setForeground(QColor("#94A3B8"))
                font = QFont("Microsoft YaHei", 12)
            rank_cell.setFont(font)

            title_cell = QTableWidgetItem(item['title'])
            title_cell.setToolTip(item['title'])

            author_cell = QTableWidgetItem(item['author'])
            author_cell.setForeground(QColor("#64748B"))

            hotness_cell = QTableWidgetItem(item['hotness'])
            hotness_cell.setForeground(QColor("#F97316"))

            link_cell = QTableWidgetItem("🖱️ 双击直达")
            link_cell.setData(Qt.UserRole, item['link'])
            link_cell.setTextAlignment(Qt.AlignCenter)
            link_cell.setForeground(QColor("#3B82F6"))
            font_link = QFont("Microsoft YaHei", 11)
            font_link.setUnderline(True)
            link_cell.setFont(font_link)

            table.setItem(row, 0, rank_cell)
            table.setItem(row, 1, title_cell)
            table.setItem(row, 2, author_cell)
            table.setItem(row, 3, hotness_cell)
            table.setItem(row, 4, link_cell)

            table.setRowHeight(row, 50)

    def handle_error(self, platform, error_msg):
        table = self.tables[platform]
        table.setRowCount(1)
        error_item = QTableWidgetItem(f"❌ {error_msg}")
        error_item.setForeground(QColor("red"))

        font = QFont("Microsoft YaHei", 12, QFont.Bold)
        error_item.setFont(font)
        table.setItem(0, 1, error_item)
        table.setRowHeight(0, 80)

    def thread_finished(self):
        all_done = all(not t.isRunning() for t in self.active_threads)
        if all_done:
            self.refresh_btn.setEnabled(True)
            self.refresh_btn.setText(" 🔄 一键抓取最新数据 ")

    def open_link(self, row, column):
        link_item = self.sender().item(row, 4)
        if link_item:
            url = link_item.data(Qt.UserRole)
            if url:
                QDesktopServices.openUrl(QUrl(url))

    def closeEvent(self, event):
         event.ignore()  # 忽略默认的关闭事件
         self.hide()  # 隐藏当前窗口，而不是关闭


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication(sys.argv)
    window = HotBoardApp()
    window.show()
    sys.exit(app.exec_())