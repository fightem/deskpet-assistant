import sys
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from datetime import datetime, timedelta
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLineEdit, QTableWidget, QTableWidgetItem,
                             QHeaderView, QPushButton, QLabel, QTabWidget, QMessageBox)
from PyQt5.QtCore import Qt, QUrl, QThread, pyqtSignal
from PyQt5.QtGui import QDesktopServices, QFont, QIcon


class ScraperThread(QThread):
    """后台抓取数据的线程，防止UI卡死"""
    progress_signal = pyqtSignal(str)
    data_signal = pyqtSignal(dict)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, cookies, headers):
        super().__init__()
        self.cookies = cookies
        self.headers = headers
        self.running = True

    def run(self):
        # 计算半年前的日期
        half_year_ago = datetime.now() - timedelta(days=180)

        # 分类存储数据
        scraped_data = {'本科生院': [], '研究生院': []}

        page_index = 0
        keep_fetching = True

        while keep_fetching and self.running and page_index < 20:  # 设个安全上限，最多抓20页
            if page_index == 0:
                url = 'http://i.whut.edu.cn/xxtg/gztz_9764.shtml'
            else:
                # 学校系统常见的分页命名规律
                url = f'http://i.whut.edu.cn/xxtg/gztz_9764_{page_index}.shtml'

            self.progress_signal.emit(f"正在抓取第 {page_index + 1} 页数据...")

            try:
                response = requests.get(url, cookies=self.cookies, headers=self.headers, timeout=10)
                if response.status_code == 404:
                    break  # 遇到404说明到底了
                response.raise_for_status()
                response.encoding = 'utf-8'

                soup = BeautifulSoup(response.text, 'html.parser')
                list_ul = soup.find('ul', class_='list_t')

                if not list_ul:
                    self.error_signal.emit("未能在网页中找到通知列表，可能需要重新登录更新 Cookie。")
                    break

                items = list_ul.find_all('li')
                if not items:
                    break

                for li in items:
                    tag_span = li.find('span', class_='list_tag')
                    if not tag_span:
                        continue

                    dept_name = tag_span.text.strip()
                    a_tag = li.find('a', class_='list_text')
                    date_span = li.find('span', class_='date')

                    if a_tag and date_span:
                        date_str = date_span.text.strip()
                        # 解析日期
                        try:
                            notice_date = datetime.strptime(date_str, "%Y-%m-%d")
                        except ValueError:
                            continue

                        # 如果当前通知的日期早于半年前，停止抓取
                        if notice_date < half_year_ago:
                            keep_fetching = False
                            break

                        title = a_tag.get('title') or a_tag.text.strip()
                        href = a_tag.get('href')
                        full_link = urljoin(url, href)

                        notice_info = {'date': date_str, 'title': title, 'link': full_link}

                        if '本科生院' in dept_name:
                            scraped_data['本科生院'].append(notice_info)
                        elif '研究生院' in dept_name:
                            scraped_data['研究生院'].append(notice_info)

                page_index += 1

            except Exception as e:
                self.error_signal.emit(f"抓取第 {page_index + 1} 页时发生网络错误: {e}")
                break

        self.data_signal.emit(scraped_data)
        self.finished_signal.emit("加载完成")

    def stop(self):
        self.running = False


class NoticeApp(QWidget):
    def __init__(self):
        super().__init__()
        self.all_data = {'本科生院': [], '研究生院': []}
        self.init_ui()
        self.start_scraping()

    def init_ui(self):
        self.setWindowTitle('综合信息抓取')
        self.resize(1000, 650)

        # --- 美化 QSS 样式 ---
        self.setStyleSheet("""
            QWidget {
                background-color: #F5F7FA;
                font-family: 'Microsoft YaHei', 'Segoe UI';
                font-size: 14px;
            }
            QLineEdit {
                border: 1px solid #DCDFE6;
                border-radius: 4px;
                padding: 8px;
                background-color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 1px solid #409EFF;
            }
            QLabel#statusLabel {
                color: #909399;
                font-size: 13px;
                font-style: italic;
            }
            QTabWidget::pane {
                border: 1px solid #E4E7ED;
                background: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background: #F5F7FA;
                border: 1px solid #E4E7ED;
                padding: 10px 20px;
                min-width: 100px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                border-bottom-color: #FFFFFF;
                color: #409EFF;
                font-weight: bold;
            }
            QTableWidget {
                background-color: #FFFFFF;
                border: none;
                gridline-color: #EBEEF5;
            }
            QHeaderView::section {
                background-color: #F5F7FA;
                color: #606266;
                padding: 8px;
                border: none;
                border-right: 1px solid #EBEEF5;
                border-bottom: 1px solid #EBEEF5;
                font-weight: bold;
            }
            QPushButton {
                color: #409EFF;
                background-color: transparent;
                border: none;
            }
            QPushButton:hover {
                color: #66B1FF;
                text-decoration: underline;
            }
        """)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # 1. 搜索区域
        search_layout = QHBoxLayout()
        search_label = QLabel("🔍 搜索标题:")
        search_label.setStyleSheet("font-weight: bold; color: #303133;")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText('在此输入关键词，直接输入即可实时筛选...')
        self.search_input.textChanged.connect(self.filter_data)
        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # 2. 状态标签
        self.status_label = QLabel("准备加载数据...")
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        # 3. 标签页与表格
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.update_status_text)

        self.tab_bks = QWidget()
        self.tab_yjs = QWidget()

        # 本科生表格
        self.table_bks = self.create_table()
        layout_bks = QVBoxLayout(self.tab_bks)
        layout_bks.setContentsMargins(0, 0, 0, 0)
        layout_bks.addWidget(self.table_bks)

        # 研究生表格
        self.table_yjs = self.create_table()
        layout_yjs = QVBoxLayout(self.tab_yjs)
        layout_yjs.setContentsMargins(0, 0, 0, 0)
        layout_yjs.addWidget(self.table_yjs)

        self.tabs.addTab(self.tab_bks, "本科生院")
        self.tabs.addTab(self.tab_yjs, "研究生院")
        layout.addWidget(self.tabs)

        self.setLayout(layout)

    def create_table(self):
        """创建并初始化标准表格"""
        table = QTableWidget(0, 3)
        table.setHorizontalHeaderLabels(['日期', '通知标题', '操作'])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        table.setAlternatingRowColors(True)  # 交替行颜色
        table.setSelectionBehavior(QTableWidget.SelectRows)  # 整行选中
        table.setEditTriggers(QTableWidget.NoEditTriggers)  # 不可编辑
        table.verticalHeader().setVisible(False)  # 隐藏左侧自带的行号
        return table

    def start_scraping(self):
        """启动后台线程抓取数据"""
        cookies = {
            'sajssdk_2015_cross_new_user': '1',
            # ---> 请确保这里的 Cookie 是你抓取到的最新 Cookie <---
            'sensorsdata2015jssdkcross': '%7B%22distinct_id%22%3A%2219cd0508450bff-01e7232fd42cab1-4c657b58-2073600-19cd050845114e8%22%2C%22first_id%22%3A%22%22%2C%22props%22%3A%7B%22%24latest_traffic_source_type%22%3A%22%E7%9B%B4%E6%8E%A5%E6%B5%81%E9%87%8F%22%2C%22%24latest_search_keyword%22%3A%22%E6%9C%AA%E5%8F%96%E5%88%B0%E5%80%BC_%E7%9B%B4%E6%8E%A5%E6%89%93%E5%BC%80%22%2C%22%24latest_referrer%22%3A%22%22%7D%2C%22identities%22%3A%22eyIkaWRlbnRpdHlfY29va2llX2lkIjoiMTljZDA1MDg0NTBiZmYtMDFlNzIzMmZkNDJjYWIxLTRjNjU3YjU4LTIwNzM2MDAtMTljZDA1MDg0NTExNGU4In0%3D%22%2C%22history_login_id%22%3A%7B%22name%22%3A%22%22%2C%22value%22%3A%22%22%7D%7D',
            'sensorsdata2015jssdksession': '%7B%22session_id%22%3A%2219cd050845edaa0b3e6b74f0329184c657b58207360019cd050845f1763%22%2C%22first_session_time%22%3A1773021463645%2C%22latest_session_time%22%3A1773021508841%7D',
        }
        headers = {
            'Host': 'i.whut.edu.cn',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36 Edg/146.0.0.0',
        }

        self.thread = ScraperThread(cookies, headers)
        self.thread.progress_signal.connect(lambda msg: self.status_label.setText(msg))
        self.thread.data_signal.connect(self.on_data_fetched)
        self.thread.error_signal.connect(self.on_error)
        self.thread.finished_signal.connect(self.on_finished)
        self.thread.start()

    def on_data_fetched(self, data):
        """数据抓取完毕，保存并渲染到表格"""
        self.all_data = data
        self.filter_data()  # 触发一次渲染

    def on_error(self, err_msg):
        QMessageBox.warning(self, "抓取异常", err_msg)

    def on_finished(self, msg):
        self.update_status_text()

    def update_status_text(self):
        """更新状态栏文字提示"""
        current_tab_name = self.tabs.tabText(self.tabs.currentIndex())
        # 获取当前表格的行数
        table = self.table_bks if current_tab_name == "本科生院" else self.table_yjs
        count = table.rowCount()
        self.status_label.setText(f"数据加载完毕，当前标签页【{current_tab_name}】共显示 {count} 条通知。")

    def filter_data(self):
        """处理搜索框的过滤逻辑"""
        keyword = self.search_input.text().strip().lower()

        # 过滤并渲染本科生院数据
        filtered_bks = [item for item in self.all_data['本科生院'] if keyword in item['title'].lower()]
        self.populate_table(self.table_bks, filtered_bks)

        # 过滤并渲染研究生院数据
        filtered_yjs = [item for item in self.all_data['研究生院'] if keyword in item['title'].lower()]
        self.populate_table(self.table_yjs, filtered_yjs)

        self.update_status_text()

    def populate_table(self, table_widget, data):
        """向指定表格中填入数据"""
        table_widget.setRowCount(0)
        for row_idx, item in enumerate(data):
            table_widget.insertRow(row_idx)

            # 日期
            date_item = QTableWidgetItem(item['date'])
            date_item.setTextAlignment(Qt.AlignCenter)

            # 标题
            title_item = QTableWidgetItem(item['title'])

            table_widget.setItem(row_idx, 0, date_item)
            table_widget.setItem(row_idx, 1, title_item)

            # 操作按钮
            btn_container = QWidget()
            btn_layout = QHBoxLayout(btn_container)
            btn_layout.setContentsMargins(0, 0, 0, 0)
            btn = QPushButton('查看详情')
            btn.setCursor(Qt.PointingHandCursor)
            # 点击调用浏览器打开
            btn.clicked.connect(lambda _, link=item['link']: QDesktopServices.openUrl(QUrl(link)))
            btn_layout.addWidget(btn)
            btn_layout.setAlignment(Qt.AlignCenter)

            table_widget.setCellWidget(row_idx, 2, btn_container)

    def closeEvent(self, event):
        event.ignore()  # 忽略默认的关闭事件
        self.hide()  # 隐藏当前窗口，而不是关闭


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setAttribute(Qt.AA_EnableHighDpiScaling)
    window = NoticeApp()
    window.show()
    sys.exit(app.exec_())