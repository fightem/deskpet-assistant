import os
import sys
import json
import pickle
from pathlib import Path
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# ---------------- 先清理代理，避免 requests/AKShare 读到系统代理 ----------------
for k in [
    "HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
    "http_proxy", "https_proxy", "all_proxy",
    "NO_PROXY", "no_proxy"
]:
    os.environ.pop(k, None)

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

_old_session = requests.Session


class NoProxySession(_old_session):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trust_env = False

        retry = Retry(
            total=1,
            backoff_factor=0.2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(pool_connections=20, pool_maxsize=20, max_retries=retry)
        self.mount("http://", adapter)
        self.mount("https://", adapter)


requests.Session = NoProxySession

import akshare as ak
import pandas as pd
import numpy as np

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QLineEdit, QMessageBox, QFrame, QStatusBar, QAction, QInputDialog,
    QAbstractItemView, QGridLayout, QStackedWidget
)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QColor

import matplotlib
matplotlib.use('Qt5Agg')

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------------- Matplotlib 样式兼容处理 ----------------
available_styles = set(plt.style.available)
if 'seaborn-v0_8-whitegrid' in available_styles:
    plt.style.use('seaborn-v0_8-whitegrid')
elif 'seaborn-whitegrid' in available_styles:
    plt.style.use('seaborn-whitegrid')
else:
    plt.style.use('default')


# ---------------- 中文字体选择 ----------------
def pick_cjk_font():
    preferred_fonts = [
        "Microsoft YaHei",
        "SimHei",
        "Noto Sans CJK SC",
        "Source Han Sans CN",
        "WenQuanYi Zen Hei",
        "PingFang SC"
    ]
    installed_fonts = {f.name for f in font_manager.fontManager.ttflist}
    for font_name in preferred_fonts:
        if font_name in installed_fonts:
            return font_name
    return "DejaVu Sans"


UI_FONT_FAMILY = pick_cjk_font()

# Matplotlib 中文设置
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = [UI_FONT_FAMILY, 'DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


# ---------------- 数据目录 ----------------
DATA_DIR = Path("./data")
DATA_DIR.mkdir(exist_ok=True)

MARKET_CACHE_DIR = DATA_DIR / "market_cache"
MARKET_CACHE_DIR.mkdir(exist_ok=True)

HIST_CACHE_DIR = MARKET_CACHE_DIR / "histories"
HIST_CACHE_DIR.mkdir(exist_ok=True)

SNAPSHOT_FILE = MARKET_CACHE_DIR / "market_snapshot.pkl"
FAVORITES_FILE = DATA_DIR / "favorite_stocks.json"


class MarketDataFetcher:
    def __init__(self, stock_pool):
        self.stock_pool = stock_pool
        self.snapshot_file = SNAPSHOT_FILE
        self.hist_cache_dir = HIST_CACHE_DIR

    @staticmethod
    def to_tx_symbol(code: str) -> str:
        code = str(code).strip()
        if code.startswith(("sh", "sz", "bj")):
            return code

        if code.startswith(("600", "601", "603", "605", "688", "900")):
            return f"sh{code}"
        elif code.startswith(("000", "001", "002", "003", "300", "301", "200")):
            return f"sz{code}"
        elif code.startswith((
            "430", "830", "831", "832", "833", "835", "836", "837",
            "838", "839", "870", "871", "872", "873", "920"
        )):
            return f"bj{code}"
        else:
            return f"sz{code}"

    def hist_cache_path(self, code: str) -> Path:
        return self.hist_cache_dir / f"hist_{code}.pkl"

    def is_file_fresh_today(self, path: Path) -> bool:
        if not path.exists():
            return False
        mtime = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        return mtime == today

    def load_hist_cache(self, code: str):
        path = self.hist_cache_path(code)
        if not path.exists():
            return None
        try:
            return pd.read_pickle(path)
        except Exception:
            return None

    def save_hist_cache(self, code: str, hist: pd.DataFrame):
        try:
            hist.to_pickle(self.hist_cache_path(code))
        except Exception:
            pass

    def load_snapshot_cache(self):
        if not self.snapshot_file.exists():
            return None, None, None, None
        try:
            with open(self.snapshot_file, "rb") as f:
                obj = pickle.load(f)
            return (
                obj.get("df", pd.DataFrame()),
                obj.get("market_indices", {}),
                obj.get("market_changes", {}),
                obj.get("updated_at", "")
            )
        except Exception:
            return None, None, None, None

    def save_snapshot_cache(self, df, market_indices, market_changes, updated_at):
        try:
            with open(self.snapshot_file, "wb") as f:
                pickle.dump({
                    "df": df,
                    "market_indices": market_indices,
                    "market_changes": market_changes,
                    "updated_at": updated_at
                }, f)
        except Exception:
            pass

    def normalize_hist_df(self, hist: pd.DataFrame):
        if hist is None or hist.empty:
            return None

        df = hist.copy()
        df.columns = [str(c).strip() for c in df.columns]

        rename_map = {
            '日期': 'date',
            '开盘': 'open',
            '收盘': 'close',
            '最高': 'high',
            '最低': 'low',
            '成交量': 'volume',
            '成交额': 'amount',
            'date': 'date',
            'open': 'open',
            'close': 'close',
            'high': 'high',
            'low': 'low',
            'volume': 'volume',
            'amount': 'amount'
        }
        df = df.rename(columns=rename_map)

        required_cols = ['date', 'open', 'close', 'high', 'low']
        for col in required_cols:
            if col not in df.columns:
                return None

        for col in ['open', 'close', 'high', 'low', 'volume', 'amount']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=['close']).sort_values('date').reset_index(drop=True)
        return df

    def fetch_hist_online(self, code: str):
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=380)).strftime("%Y%m%d")

        hist = None

        try:
            hist = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )
        except Exception:
            hist = None

        if hist is None or len(hist) == 0:
            try:
                tx_symbol = self.to_tx_symbol(code)
                hist = ak.stock_zh_a_hist_tx(
                    symbol=tx_symbol,
                    start_date=start_date,
                    end_date=end_date,
                    adjust=""
                )
            except Exception:
                hist = None

        hist = self.normalize_hist_df(hist)
        return hist

    def build_stock_row_from_hist(self, name, code, industry, hist):
        latest = hist.iloc[-1]
        prev = hist.iloc[-2] if len(hist) >= 2 else latest

        close_now = float(latest['close'])
        close_prev = float(prev['close']) if pd.notna(prev['close']) else close_now
        change = close_now - close_prev
        change_pct = ((close_now / close_prev) - 1) * 100 if close_prev != 0 else 0.0

        amount = float(latest['amount']) if 'amount' in hist.columns and pd.notna(latest.get('amount', np.nan)) else np.nan
        volume = float(latest['volume']) if 'volume' in hist.columns and pd.notna(latest.get('volume', np.nan)) else np.nan

        close_series = hist['close'].dropna().reset_index(drop=True)

        def calc_return(days):
            if len(close_series) <= days:
                return np.nan
            base = float(close_series.iloc[-days - 1])
            now = float(close_series.iloc[-1])
            return (now / base - 1) * 100 if base != 0 else np.nan

        profit_3m = calc_return(60)
        profit_6m = calc_return(120)
        profit_1y = calc_return(240)

        ret20 = close_series.pct_change().tail(20).dropna()
        volatility_20d = float(ret20.std() * np.sqrt(252) * 100) if len(ret20) > 0 else np.nan

        ma20 = float(close_series.tail(20).mean()) if len(close_series) >= 20 else np.nan
        ma60 = float(close_series.tail(60).mean()) if len(close_series) >= 60 else np.nan

        popularity = 50
        if pd.notna(profit_3m):
            popularity += min(max(profit_3m, -20), 20) * 1.5
        if pd.notna(amount):
            popularity += min(amount / 1e8, 30)
        popularity = int(max(0, min(100, popularity)))

        return {
            'name': name,
            'code': code,
            'industry': industry,
            'price': round(close_now, 2),
            'change': round(change, 2),
            'change_pct': round(change_pct, 2),
            'volume': int(volume) if pd.notna(volume) else 0,
            'amount': round(amount / 1e8, 2) if pd.notna(amount) else 0.0,
            'profit_3m': round(profit_3m, 2) if pd.notna(profit_3m) else 0.0,
            'profit_6m': round(profit_6m, 2) if pd.notna(profit_6m) else 0.0,
            'profit_1y': round(profit_1y, 2) if pd.notna(profit_1y) else 0.0,
            'volatility_20d': round(volatility_20d, 2) if pd.notna(volatility_20d) else 0.0,
            'ma20': round(ma20, 2) if pd.notna(ma20) else 0.0,
            'ma60': round(ma60, 2) if pd.notna(ma60) else 0.0,
            'market_cap': 0.0,
            'popularity': popularity
        }

    def fetch_single_stock(self, name, code, industry):
        cache_path = self.hist_cache_path(code)
        cached_hist = self.load_hist_cache(code)

        if self.is_file_fresh_today(cache_path) and cached_hist is not None and len(cached_hist) >= 30:
            return self.build_stock_row_from_hist(name, code, industry, cached_hist)

        hist = self.fetch_hist_online(code)
        if hist is not None and len(hist) >= 30:
            self.save_hist_cache(code, hist)
            return self.build_stock_row_from_hist(name, code, industry, hist)

        if cached_hist is not None and len(cached_hist) >= 30:
            return self.build_stock_row_from_hist(name, code, industry, cached_hist)

        return None

    def load_index_data(self):
        index_map = {
            '上证指数': 'sh000001',
            '深证成指': 'sz399001',
            '创业板指': 'sz399006'
        }

        market_indices = {}
        market_changes = {}

        for name, symbol in index_map.items():
            try:
                idx_df = ak.stock_zh_index_daily_tx(symbol=symbol)
                idx_df.columns = [str(c).strip().lower() for c in idx_df.columns]
                idx_df = idx_df.sort_values('date').reset_index(drop=True)

                latest = idx_df.iloc[-1]
                prev = idx_df.iloc[-2] if len(idx_df) >= 2 else latest

                latest_close = float(latest['close'])
                prev_close = float(prev['close'])
                pct = ((latest_close / prev_close) - 1) * 100 if prev_close != 0 else 0.0

                market_indices[name] = round(latest_close, 2)
                market_changes[name] = round(pct, 2)
            except Exception:
                market_indices[name] = 0.0
                market_changes[name] = 0.0

        return market_indices, market_changes

    def load_all_remote_data(self):
        rows = []
        failed = []

        max_workers = min(8, max(1, len(self.stock_pool)))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(self.fetch_single_stock, name, code, industry): (name, code)
                for name, code, industry in self.stock_pool
            }

            for future in as_completed(futures):
                name, code = futures[future]
                try:
                    row = future.result()
                    if row is not None:
                        rows.append(row)
                    else:
                        failed.append(f"{name}({code})")
                except Exception:
                    failed.append(f"{name}({code})")

        df = pd.DataFrame(rows)
        if df.empty:
            raise RuntimeError("股票池数据为空，请检查网络或 AKShare 接口")

        df = df.sort_values(by=["industry", "name"]).reset_index(drop=True)

        market_indices, market_changes = self.load_index_data()
        updated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        self.save_snapshot_cache(df, market_indices, market_changes, updated_at)

        if failed:
            print("以下股票抓取失败：", "、".join(failed))

        return df, market_indices, market_changes, updated_at


class DataFetchWorker(QThread):
    data_ready = pyqtSignal(object, object, object, str)
    error = pyqtSignal(str)
    progress = pyqtSignal(str)

    def __init__(self, fetcher: MarketDataFetcher):
        super().__init__()
        self.fetcher = fetcher

    def run(self):
        try:
            self.progress.emit("正在后台并发抓取最新行情数据...")
            df, market_indices, market_changes, updated_at = self.fetcher.load_all_remote_data()
            self.data_ready.emit(df, market_indices, market_changes, updated_at)
        except Exception as e:
            self.error.emit(str(e))


class StockAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('股票分析专家 Pro')
        self.setGeometry(100, 100, 1366, 850)
        self.setMinimumSize(1100, 750)

        self.setStyleSheet(f'''
            QMainWindow {{
                background-color: #f0f2f5;
            }}
            QTabWidget::pane {{
                border: none;
                background: transparent;
            }}
            QTabBar::tab {{
                background: #e4e6eb;
                color: #606266;
                padding: 12px 24px;
                border-radius: 6px;
                margin-right: 4px;
                margin-bottom: 8px;
                font-family: "{UI_FONT_FAMILY}";
                font-weight: bold;
                font-size: 14px;
            }}
            QTabBar::tab:selected {{
                background: #1890ff;
                color: white;
            }}
            QTabBar::tab:hover:!selected {{
                background: #dcdfe6;
            }}
            QPushButton {{
                background-color: #1890ff;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-family: "{UI_FONT_FAMILY}";
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: #40a9ff;
            }}
            QPushButton:pressed {{
                background-color: #096dd9;
            }}
            QLabel {{
                font-family: "{UI_FONT_FAMILY}";
                color: #303133;
            }}
            QTableWidget {{
                background-color: white;
                border: 1px solid #ebeef5;
                border-radius: 8px;
                gridline-color: #ebeef5;
                selection-background-color: #e6f7ff;
                selection-color: #1890ff;
                font-family: "{UI_FONT_FAMILY}";
            }}
            QHeaderView::section {{
                background-color: #fafafa;
                padding: 10px;
                border: none;
                border-bottom: 1px solid #ebeef5;
                border-right: 1px solid #ebeef5;
                font-weight: bold;
                color: #606266;
                font-family: "{UI_FONT_FAMILY}";
            }}
            QLineEdit, QComboBox {{
                padding: 8px;
                border: 1px solid #dcdfe6;
                border-radius: 4px;
                background: white;
                min-width: 80px;
                font-family: "{UI_FONT_FAMILY}";
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid #1890ff;
            }}
            #CardFrame {{
                background: white;
                border-radius: 8px;
                border: 1px solid #ebeef5;
            }}
            #LoadingCard {{
                background: white;
                border-radius: 12px;
                border: 1px solid #ebeef5;
            }}
        ''')

        self.stock_pool = [
            ('贵州茅台', '600519', '消费'),
            ('中国平安', '601318', '金融'),
            ('招商银行', '600036', '金融'),
            ('宁德时代', '300750', '新能源'),
            ('比亚迪', '002594', '汽车'),
            ('五粮液', '000858', '消费'),
            ('泸州老窖', '000568', '消费'),
            ('中国中免', '601888', '消费'),
            ('隆基绿能', '601012', '新能源'),
            ('阳光电源', '300274', '新能源'),
            ('药明康德', '603259', '医药'),
            ('恒瑞医药', '600276', '医药'),
            ('迈瑞医疗', '300760', '医药'),
            ('中国建筑', '601668', '建筑'),
            ('中国中铁', '601390', '建筑'),
            ('中际旭创', '300308', '科技'),
            ('工业富联', '601138', '科技'),
            ('中兴通讯', '000063', '科技')
        ]

        self.fetcher = MarketDataFetcher(self.stock_pool)
        self.worker = None
        self.is_loading = False
        self.initial_data_loaded = False
        self.last_update_text = ""

        self.favorite_stocks = self.load_favorite_stocks()
        self.df = pd.DataFrame()
        self.market_indices = {}
        self.market_changes = {}

        self.menu_bar = self.menuBar()
        file_menu = self.menu_bar.addMenu('文件')

        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        self.refresh_action = QAction('刷新数据', self)
        self.refresh_action.triggered.connect(self.refresh_remote_data)
        file_menu.addAction(self.refresh_action)

        save_favorites_action = QAction('保存自选股', self)
        save_favorites_action.triggered.connect(self.manual_save_favorites)
        file_menu.addAction(save_favorites_action)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # 标题栏
        title_frame = QFrame()
        title_frame.setObjectName("CardFrame")
        title_frame.setStyleSheet("#CardFrame { background: #1890ff; }")
        title_layout = QHBoxLayout(title_frame)
        title_layout.setContentsMargins(20, 15, 20, 15)

        self.title_label = QLabel('股票分析专家 Pro')
        self.title_label.setFont(QFont(UI_FONT_FAMILY, 20, QFont.Bold))
        self.title_label.setStyleSheet('color: white;')
        title_layout.addWidget(self.title_label)

        self.market_status = QLabel('🟡 数据模式: 启动中...')
        self.market_status.setFont(QFont(UI_FONT_FAMILY, 12, QFont.Bold))
        self.market_status.setStyleSheet('color: white; margin-left: auto;')
        title_layout.addWidget(self.market_status)

        self.main_layout.addWidget(title_frame)

        # 堆叠页面：0=加载页，1=主内容页
        self.page_stack = QStackedWidget()
        self.main_layout.addWidget(self.page_stack)

        self.loading_page = self.build_loading_page()
        self.main_page = QWidget()

        self.page_stack.addWidget(self.loading_page)
        self.page_stack.addWidget(self.main_page)
        self.page_stack.setCurrentIndex(0)

        # 主内容页
        self.main_page_layout = QVBoxLayout(self.main_page)
        self.main_page_layout.setContentsMargins(0, 0, 0, 0)

        self.tab_widget = QTabWidget()
        self.main_page_layout.addWidget(self.tab_widget)

        self.overview_tab = QWidget()
        self.recommend_tab = QWidget()
        self.hot_tab = QWidget()
        self.profit_tab = QWidget()
        self.favorite_tab = QWidget()

        self.tab_widget.addTab(self.overview_tab, '📊 市场概览')
        self.tab_widget.addTab(self.recommend_tab, '🎯 股票筛选')
        self.tab_widget.addTab(self.hot_tab, '🔥 热门股票')
        self.tab_widget.addTab(self.profit_tab, '📈 收益排行')
        self.tab_widget.addTab(self.favorite_tab, '⭐ 自选股')

        self.setup_overview_tab()
        self.setup_recommend_tab()
        self.setup_hot_tab()
        self.setup_profit_tab()
        self.setup_favorite_tab()

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)

        self.load_cache_then_refresh()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_remote_data)
        self.timer.start(1800000)

    # ---------------- 自选股持久化 ----------------
    def load_favorite_stocks(self):
        if not FAVORITES_FILE.exists():
            return []
        try:
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                return [str(x).strip() for x in data if str(x).strip()]
            return []
        except Exception:
            return []

    def save_favorite_stocks(self):
        try:
            unique_stocks = []
            seen = set()
            for name in self.favorite_stocks:
                name = str(name).strip()
                if name and name not in seen:
                    unique_stocks.append(name)
                    seen.add(name)

            self.favorite_stocks = unique_stocks

            with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.favorite_stocks, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False

    def manual_save_favorites(self):
        ok = self.save_favorite_stocks()
        if ok:
            QMessageBox.information(self, '提示', f'自选股已保存到：\n{FAVORITES_FILE}')
        else:
            QMessageBox.warning(self, '错误', '自选股保存失败')

    def load_cache_then_refresh(self):
        df, market_indices, market_changes, updated_at = self.fetcher.load_snapshot_cache()

        if isinstance(df, pd.DataFrame) and not df.empty:
            self.df = df
            self.market_indices = market_indices or {}
            self.market_changes = market_changes or {}
            self.last_update_text = updated_at or ""
            self.initial_data_loaded = True

            self.update_all_tabs()
            self.page_stack.setCurrentIndex(1)
            self.market_status.setText(f'🟠 数据模式: 缓存数据 | {self.last_update_text}')
            self.status_bar.showMessage('已加载缓存数据，正在后台刷新最新数据...', 5000)
        else:
            self.page_stack.setCurrentIndex(0)
            self.market_status.setText('🟡 数据模式: 首次加载中...')
            self.set_loading_message("首次运行或暂无缓存，正在获取真实行情，请稍候。", show_retry=False)
            self.status_bar.showMessage('未找到缓存，正在加载真实数据...')

        self.refresh_remote_data(first_load=True)

    def build_loading_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setAlignment(Qt.AlignCenter)

        card = QFrame()
        card.setObjectName("LoadingCard")
        card.setFixedWidth(520)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(30, 30, 30, 30)
        card_layout.setSpacing(16)

        title = QLabel("正在加载股票数据...")
        title.setAlignment(Qt.AlignCenter)
        title.setFont(QFont(UI_FONT_FAMILY, 18, QFont.Bold))
        card_layout.addWidget(title)

        self.loading_label = QLabel("正在获取真实行情，请稍候。")
        self.loading_label.setAlignment(Qt.AlignCenter)
        self.loading_label.setWordWrap(True)
        self.loading_label.setFont(QFont(UI_FONT_FAMILY, 11))
        self.loading_label.setStyleSheet("color: #666666; line-height: 1.6;")
        card_layout.addWidget(self.loading_label)

        self.retry_button = QPushButton("重新加载")
        self.retry_button.setFixedWidth(140)
        self.retry_button.clicked.connect(self.refresh_remote_data)
        self.retry_button.hide()

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        btn_layout.addWidget(self.retry_button)
        btn_layout.addStretch()

        card_layout.addLayout(btn_layout)
        layout.addWidget(card)

        return page

    def set_loading_message(self, text, show_retry=False):
        self.loading_label.setText(text)
        self.retry_button.setVisible(show_retry)

    def create_table(self, columns):
        table = QTableWidget()
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        return table

    def create_card_frame(self):
        frame = QFrame()
        frame.setObjectName("CardFrame")
        return frame

    def _set_table_item(self, table, row_idx, col_idx, text, is_pct=False, val=0):
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignCenter)
        if is_pct:
            item.setForeground(QColor('#f5222d') if val >= 0 else QColor('#52c41a'))
        table.setItem(row_idx, col_idx, item)

    def set_loading_state(self, loading: bool):
        self.is_loading = loading
        self.refresh_action.setEnabled(not loading)
        self.recommend_btn.setEnabled(not loading)
        self.add_favorite_btn.setEnabled(not loading)
        self.remove_favorite_btn.setEnabled(not loading)

    def try_load_snapshot_as_fallback(self):
        df, market_indices, market_changes, updated_at = self.fetcher.load_snapshot_cache()
        if isinstance(df, pd.DataFrame) and not df.empty:
            self.df = df
            self.market_indices = market_indices or {}
            self.market_changes = market_changes or {}
            self.last_update_text = updated_at or ""
            self.update_all_tabs()
            self.page_stack.setCurrentIndex(1)
            self.initial_data_loaded = True
            self.market_status.setText(f'🟠 数据模式: 使用缓存数据 | {self.last_update_text}')
            return True
        return False

    def refresh_remote_data(self, first_load=False):
        if self.is_loading:
            return

        self.set_loading_state(True)

        if not self.initial_data_loaded:
            self.page_stack.setCurrentIndex(0)

        if self.initial_data_loaded:
            self.market_status.setText(f'🟡 数据模式: 正在刷新最新数据 | {self.last_update_text}')
        else:
            self.market_status.setText('🟡 数据模式: 加载中...')

        self.set_loading_message("正在获取最新行情数据，请稍候。", show_retry=False)
        self.status_bar.showMessage('正在后台刷新真实行情数据，请稍候...')

        self.worker = DataFetchWorker(self.fetcher)
        self.worker.progress.connect(self.status_bar.showMessage)
        self.worker.data_ready.connect(self.on_data_ready)
        self.worker.error.connect(self.on_data_error)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.start()

    def on_data_ready(self, df, market_indices, market_changes, updated_at):
        self.df = df
        self.market_indices = market_indices
        self.market_changes = market_changes
        self.last_update_text = updated_at

        self.update_all_tabs()
        self.page_stack.setCurrentIndex(1)
        self.initial_data_loaded = True
        self.market_status.setText(f'🟢 数据模式: 最新数据 | {updated_at}')
        self.status_bar.showMessage(f'✅ 数据刷新完成，已替换为最新数据，更新时间：{updated_at}', 6000)

    def on_data_error(self, msg):
        if self.initial_data_loaded:
            self.market_status.setText(f'🟠 数据模式: 缓存数据 | {self.last_update_text}')
            self.status_bar.showMessage(f'⚠️ 后台刷新失败，当前继续显示缓存/旧数据：{msg}', 8000)
            return

        ok = self.try_load_snapshot_as_fallback()
        if ok:
            self.status_bar.showMessage(f'⚠️ 实时加载失败，已切换到本地缓存：{msg}', 8000)
            return

        self.page_stack.setCurrentIndex(0)
        self.market_status.setText('🔴 数据模式: 加载失败')
        self.set_loading_message(
            f"数据加载失败：{msg}\n\n请检查网络或 AKShare 接口状态，然后点击“重新加载”。",
            show_retry=True
        )
        self.status_bar.showMessage(f'❌ 数据加载失败：{msg}', 8000)

    def on_worker_finished(self):
        self.set_loading_state(False)

    def setup_overview_tab(self):
        layout = QVBoxLayout(self.overview_tab)
        layout.setContentsMargins(0, 10, 0, 0)

        index_frame = self.create_card_frame()
        self.index_layout = QGridLayout(index_frame)
        self.index_layout.setContentsMargins(20, 20, 20, 20)
        layout.addWidget(index_frame)

        bottom_layout = QHBoxLayout()

        ind_frame = self.create_card_frame()
        ind_layout = QVBoxLayout(ind_frame)
        ind_layout.setContentsMargins(15, 15, 15, 15)
        ind_title = QLabel('📊 行业板块涨跌幅（基于股票池聚合）')
        ind_title.setFont(QFont(UI_FONT_FAMILY, 14, QFont.Bold))
        ind_layout.addWidget(ind_title)

        self.industry_table = self.create_table(['行业', '平均涨跌幅', '领涨股'])
        ind_layout.addWidget(self.industry_table)
        bottom_layout.addWidget(ind_frame, 2)

        hot_frame = self.create_card_frame()
        hot_layout = QVBoxLayout(hot_frame)
        hot_layout.setContentsMargins(20, 20, 20, 20)
        hot_layout.setAlignment(Qt.AlignTop)

        hot_title = QLabel('🔥 市场热点分析')
        hot_title.setFont(QFont(UI_FONT_FAMILY, 14, QFont.Bold))
        hot_layout.addWidget(hot_title)

        hot_text = (
            "1. 本页展示股票池的真实历史行情分析结果\n\n" "2. 行业涨跌幅基于当前股票池聚合计算\n\n" "3. 热门度基于近三个月收益与成交额构建\n\n" "4. 若联网失败，会自动尝试使用本地缓存\n\n" "5. 当前模式适合趋势观察与相对强弱比较")
        self.hot_topics = QLabel(hot_text)
        self.hot_topics.setFont(QFont(UI_FONT_FAMILY, 12))
        self.hot_topics.setWordWrap(True)
        self.hot_topics.setStyleSheet("line-height: 1.5; color: #555;")
        hot_layout.addWidget(self.hot_topics)
        bottom_layout.addWidget(hot_frame, 1)

        layout.addLayout(bottom_layout)

    def setup_recommend_tab(self):
        layout = QVBoxLayout(self.recommend_tab)
        layout.setContentsMargins(0, 10, 0, 0)

        filter_frame = self.create_card_frame()
        filter_layout = QHBoxLayout(filter_frame)
        filter_layout.setContentsMargins(15, 15, 15, 15)

        filter_layout.addWidget(QLabel('所属行业:'))
        self.industry_combo = QComboBox()
        self.industry_combo.addItem('全部')
        filter_layout.addWidget(self.industry_combo)

        filter_layout.addSpacing(20)
        filter_layout.addWidget(QLabel('3个月收益率(%):'))
        self.ret3m_min = QLineEdit('-100')
        self.ret3m_max = QLineEdit('200')
        filter_layout.addWidget(self.ret3m_min)
        filter_layout.addWidget(QLabel('-'))
        filter_layout.addWidget(self.ret3m_max)

        filter_layout.addSpacing(20)
        filter_layout.addWidget(QLabel('20日波动率(%):'))
        self.vol_min = QLineEdit('0')
        self.vol_max = QLineEdit('200')
        filter_layout.addWidget(self.vol_min)
        filter_layout.addWidget(QLabel('-'))
        filter_layout.addWidget(self.vol_max)

        filter_layout.addStretch()
        self.recommend_btn = QPushButton('🔍 开始筛选')
        self.recommend_btn.clicked.connect(self.recommend_stocks)
        filter_layout.addWidget(self.recommend_btn)

        layout.addWidget(filter_frame)

        content_layout = QHBoxLayout()

        table_frame = self.create_card_frame()
        t_layout = QVBoxLayout(table_frame)
        self.recommend_table = self.create_table(
            ['股票名称', '代码', '行业', '价格', '涨跌幅', '3个月收益', '6个月收益', '1年收益', '推荐理由']
        )
        t_layout.addWidget(self.recommend_table)
        content_layout.addWidget(table_frame, 3)

        chart_frame = self.create_card_frame()
        c_layout = QVBoxLayout(chart_frame)
        self.recommend_canvas = FigureCanvas(Figure(figsize=(5, 4)))
        c_layout.addWidget(self.recommend_canvas)
        content_layout.addWidget(chart_frame, 2)

        layout.addLayout(content_layout)

    def setup_hot_tab(self):
        layout = QVBoxLayout(self.hot_tab)
        layout.setContentsMargins(0, 10, 0, 0)

        chart_frame = self.create_card_frame()
        c_layout = QVBoxLayout(chart_frame)
        self.hot_canvas = FigureCanvas(Figure(figsize=(10, 3)))
        c_layout.addWidget(self.hot_canvas)
        layout.addWidget(chart_frame)

        table_frame = self.create_card_frame()
        t_layout = QVBoxLayout(table_frame)
        title = QLabel('🏆 热门股票排名榜')
        title.setFont(QFont(UI_FONT_FAMILY, 14, QFont.Bold))
        t_layout.addWidget(title)

        self.hot_table = self.create_table(
            ['排名', '名称', '代码', '行业', '价格', '涨跌幅', '成交额(亿)', '3个月收益', '热门度']
        )
        t_layout.addWidget(self.hot_table)
        layout.addWidget(table_frame)

    def setup_profit_tab(self):
        layout = QVBoxLayout(self.profit_tab)
        layout.setContentsMargins(0, 10, 0, 0)

        top_frame = self.create_card_frame()
        top_layout = QHBoxLayout(top_frame)
        top_layout.setContentsMargins(15, 15, 15, 15)

        top_layout.addWidget(QLabel('统计周期:'))
        self.time_combo = QComboBox()
        self.time_combo.addItems(['3个月', '6个月', '1年'])
        self.time_combo.currentIndexChanged.connect(self.update_profit_tab)
        top_layout.addWidget(self.time_combo)
        top_layout.addStretch()
        layout.addWidget(top_frame)

        content_layout = QHBoxLayout()

        table_frame = self.create_card_frame()
        t_layout = QVBoxLayout(table_frame)
        self.profit_table = self.create_table(['排名', '名称', '代码', '行业', '价格', '涨跌幅', '收益率', '20日波动率'])
        t_layout.addWidget(self.profit_table)
        content_layout.addWidget(table_frame, 1)

        chart_frame = self.create_card_frame()
        c_layout = QVBoxLayout(chart_frame)
        self.profit_canvas = FigureCanvas(Figure(figsize=(6, 4)))
        c_layout.addWidget(self.profit_canvas)
        content_layout.addWidget(chart_frame, 1)

        layout.addLayout(content_layout)

    def setup_favorite_tab(self):
        layout = QVBoxLayout(self.favorite_tab)
        layout.setContentsMargins(0, 10, 0, 0)

        action_frame = self.create_card_frame()
        action_layout = QHBoxLayout(action_frame)
        action_layout.setContentsMargins(15, 15, 15, 15)

        self.add_favorite_btn = QPushButton('➕ 添加自选')
        self.add_favorite_btn.clicked.connect(self.add_favorite)
        action_layout.addWidget(self.add_favorite_btn)

        self.remove_favorite_btn = QPushButton('➖ 移除自选')
        self.remove_favorite_btn.setStyleSheet("background-color: #ff4d4f;")
        self.remove_favorite_btn.clicked.connect(self.remove_favorite)
        action_layout.addWidget(self.remove_favorite_btn)

        self.save_favorite_btn = QPushButton('💾 保存自选')
        self.save_favorite_btn.setStyleSheet("background-color: #13c2c2;")
        self.save_favorite_btn.clicked.connect(self.manual_save_favorites)
        action_layout.addWidget(self.save_favorite_btn)

        action_layout.addStretch()
        layout.addWidget(action_frame)

        table_frame = self.create_card_frame()
        t_layout = QVBoxLayout(table_frame)
        self.favorite_table = self.create_table(
            ['股票名称', '代码', '行业', '当前价格', '涨跌幅', '3个月收益', '1年收益', '操作']
        )
        t_layout.addWidget(self.favorite_table)
        layout.addWidget(table_frame)

    def update_all_tabs(self):
        if not self.df.empty:
            self.industry_combo.blockSignals(True)
            current_text = self.industry_combo.currentText()
            self.industry_combo.clear()
            self.industry_combo.addItems(['全部'] + sorted(self.df['industry'].unique().tolist()))
            idx = self.industry_combo.findText(current_text)
            if idx >= 0:
                self.industry_combo.setCurrentIndex(idx)
            self.industry_combo.blockSignals(False)

        self.update_overview_tab()
        self.recommend_stocks()
        self.update_hot_tab()
        self.update_profit_tab()
        self.update_favorite_tab()

    def update_overview_tab(self):
        while self.index_layout.count():
            child = self.index_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        col = 0
        for index_name in self.market_indices:
            item_frame = QFrame()
            item_frame.setStyleSheet('background: #f8f9fa; border-radius: 8px; border: 1px solid #ebeef5;')
            item_layout = QVBoxLayout(item_frame)
            item_layout.setAlignment(Qt.AlignCenter)

            lbl_name = QLabel(index_name)
            lbl_name.setFont(QFont(UI_FONT_FAMILY, 14, QFont.Bold))
            lbl_name.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(lbl_name)

            lbl_price = QLabel(f"{self.market_indices[index_name]:.2f}")
            lbl_price.setFont(QFont(UI_FONT_FAMILY, 22, QFont.Bold))
            lbl_price.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(lbl_price)

            change = self.market_changes.get(index_name, 0.0)
            symbol = "+" if change >= 0 else ""
            color = "#f5222d" if change >= 0 else "#52c41a"

            lbl_change = QLabel(f"{symbol}{change:.2f}%")
            lbl_change.setFont(QFont(UI_FONT_FAMILY, 12, QFont.Bold))
            lbl_change.setStyleSheet(f'color: {color};')
            lbl_change.setAlignment(Qt.AlignCenter)
            item_layout.addWidget(lbl_change)

            self.index_layout.addWidget(item_frame, 0, col)
            col += 1

        if self.df.empty:
            return

        industry_data = self.df.groupby('industry', as_index=False).agg({'change_pct': 'mean'})
        industry_data = industry_data.sort_values(by='change_pct', ascending=False).reset_index(drop=True)

        self.industry_table.setUpdatesEnabled(False)
        self.industry_table.setRowCount(len(industry_data))

        for i, row in industry_data.iterrows():
            self._set_table_item(self.industry_table, i, 0, row['industry'])
            self._set_table_item(self.industry_table, i, 1, f"{row['change_pct']:.2f}%", True, row['change_pct'])

            top_stock = self.df[self.df['industry'] == row['industry']].sort_values(by='change_pct', ascending=False).iloc[0]
            self._set_table_item(self.industry_table, i, 2, top_stock['name'])

        self.industry_table.setUpdatesEnabled(True)

    def recommend_stocks(self):
        if self.df.empty:
            return

        try:
            ret_min, ret_max = float(self.ret3m_min.text()), float(self.ret3m_max.text())
            vol_min, vol_max = float(self.vol_min.text()), float(self.vol_max.text())
        except ValueError:
            QMessageBox.warning(self, '输入错误', '请输入有效的数值')
            return

        filtered = self.df[
            (self.df['profit_3m'] >= ret_min) & (self.df['profit_3m'] <= ret_max) &
            (self.df['volatility_20d'] >= vol_min) & (self.df['volatility_20d'] <= vol_max)
        ]

        industry = self.industry_combo.currentText()
        if industry != '全部':
            filtered = filtered[filtered['industry'] == industry]

        recommended = filtered.sort_values(by=['profit_3m', 'profit_6m'], ascending=[False, False]).head(15)

        self.recommend_table.setUpdatesEnabled(False)
        self.recommend_table.setRowCount(len(recommended))

        for i, (_, row) in enumerate(recommended.iterrows()):
            self._set_table_item(self.recommend_table, i, 0, row['name'])
            self._set_table_item(self.recommend_table, i, 1, row['code'])
            self._set_table_item(self.recommend_table, i, 2, row['industry'])
            self._set_table_item(self.recommend_table, i, 3, f"{row['price']:.2f}")
            self._set_table_item(self.recommend_table, i, 4, f"{row['change_pct']:.2f}%", True, row['change_pct'])
            self._set_table_item(self.recommend_table, i, 5, f"{row['profit_3m']:.2f}%")
            self._set_table_item(self.recommend_table, i, 6, f"{row['profit_6m']:.2f}%")
            self._set_table_item(self.recommend_table, i, 7, f"{row['profit_1y']:.2f}%")

            reasons = []
            if row['profit_3m'] > 10:
                reasons.append('近3月强势')
            if row['profit_6m'] > 20:
                reasons.append('中期趋势良好')
            if row['volatility_20d'] < 35:
                reasons.append('波动适中')
            if row['price'] > row['ma20'] > 0:
                reasons.append('站上MA20')

            self._set_table_item(self.recommend_table, i, 8, '，'.join(reasons) if reasons else '趋势观察')

        self.recommend_table.setUpdatesEnabled(True)
        self.update_recommend_chart(recommended)

    def update_recommend_chart(self, data):
        self.recommend_canvas.figure.clf()
        ax = self.recommend_canvas.figure.add_subplot(111)

        if not data.empty:
            x = data['name'].tolist()
            x = [name[:2] + '\n' + name[2:] if len(name) > 3 else name for name in x]
            ret3m = data['profit_3m'].tolist()
            vol = data['volatility_20d'].tolist()

            ax.bar(x, ret3m, label='3个月收益率(%)', color='#1890ff', alpha=0.8, width=0.4)
            ax.set_ylabel('3个月收益率(%)', fontweight='bold')

            ax2 = ax.twinx()
            ax2.plot(x, vol, label='20日波动率(%)', color='#f5222d', marker='o', linewidth=2)
            ax2.set_ylabel('20日波动率(%)', fontweight='bold')

            ax.set_title('收益与波动对比图', fontsize=12, fontweight='bold', pad=15)
            ax.tick_params(axis='x', rotation=0, labelsize=9)

        self.recommend_canvas.figure.tight_layout()
        self.recommend_canvas.draw_idle()

    def update_hot_tab(self):
        if self.df.empty:
            return

        hot_stocks = self.df.sort_values(by='popularity', ascending=False).head(10)

        self.hot_table.setUpdatesEnabled(False)
        self.hot_table.setRowCount(len(hot_stocks))

        for i, (_, row) in enumerate(hot_stocks.iterrows()):
            self._set_table_item(self.hot_table, i, 0, str(i + 1))
            self._set_table_item(self.hot_table, i, 1, row['name'])
            self._set_table_item(self.hot_table, i, 2, row['code'])
            self._set_table_item(self.hot_table, i, 3, row['industry'])
            self._set_table_item(self.hot_table, i, 4, f"{row['price']:.2f}")
            self._set_table_item(self.hot_table, i, 5, f"{row['change_pct']:.2f}%", True, row['change_pct'])
            self._set_table_item(self.hot_table, i, 6, f"{row['amount']:.2f}")
            self._set_table_item(self.hot_table, i, 7, f"{row['profit_3m']:.2f}%")
            self._set_table_item(self.hot_table, i, 8, f"🔥 {row['popularity']}")

        self.hot_table.setUpdatesEnabled(True)
        self.update_hot_chart(hot_stocks)

    def update_hot_chart(self, data):
        self.hot_canvas.figure.clf()
        ax = self.hot_canvas.figure.add_subplot(111)
        x = data['name'].tolist()
        pop = data['popularity'].tolist()

        ax.plot(x, pop, marker='s', color='#faad14', linewidth=2, markersize=8)
        ax.fill_between(x, pop, alpha=0.2, color='#faad14')
        ax.set_title('近期市场热门度趋势', fontsize=12, fontweight='bold', pad=10)
        ax.set_ylim(0, 110)

        self.hot_canvas.figure.tight_layout()
        self.hot_canvas.draw_idle()

    def update_profit_tab(self):
        if self.df.empty:
            return

        time_range = self.time_combo.currentText()
        col_map = {'3个月': 'profit_3m', '6个月': 'profit_6m', '1年': 'profit_1y'}
        profit_col = col_map[time_range]

        profit_stocks = self.df.sort_values(by=profit_col, ascending=False).head(15)

        self.profit_table.setUpdatesEnabled(False)
        self.profit_table.setRowCount(len(profit_stocks))

        for i, (_, row) in enumerate(profit_stocks.iterrows()):
            self._set_table_item(self.profit_table, i, 0, str(i + 1))
            self._set_table_item(self.profit_table, i, 1, row['name'])
            self._set_table_item(self.profit_table, i, 2, row['code'])
            self._set_table_item(self.profit_table, i, 3, row['industry'])
            self._set_table_item(self.profit_table, i, 4, f"{row['price']:.2f}")
            self._set_table_item(self.profit_table, i, 5, f"{row['change_pct']:.2f}%", True, row['change_pct'])
            self._set_table_item(self.profit_table, i, 6, f"{row[profit_col]:.2f}%", True, row[profit_col])
            self._set_table_item(self.profit_table, i, 7, f"{row['volatility_20d']:.2f}%")

        self.profit_table.setUpdatesEnabled(True)
        self.update_profit_chart(profit_stocks, profit_col, time_range)

    def update_profit_chart(self, data, profit_col, time_range):
        self.profit_canvas.figure.clf()
        ax = self.profit_canvas.figure.add_subplot(111)
        x = data['name'].tolist()
        profit = data[profit_col].tolist()

        colors = ['#f5222d' if p >= 0 else '#52c41a' for p in profit]
        ax.barh(x[::-1], profit[::-1], color=colors[::-1], alpha=0.8, height=0.6)
        ax.set_title(f'{time_range} 收益率排行', fontsize=12, fontweight='bold')

        self.profit_canvas.figure.tight_layout()
        self.profit_canvas.draw_idle()

    def update_favorite_tab(self):
        if self.df.empty:
            self.favorite_table.setRowCount(0)
            return

        fav_data = self.df[self.df['name'].isin(self.favorite_stocks)]

        self.favorite_table.setUpdatesEnabled(False)
        self.favorite_table.setRowCount(len(fav_data))

        for i, (_, row) in enumerate(fav_data.iterrows()):
            self._set_table_item(self.favorite_table, i, 0, row['name'])
            self._set_table_item(self.favorite_table, i, 1, row['code'])
            self._set_table_item(self.favorite_table, i, 2, row['industry'])
            self._set_table_item(self.favorite_table, i, 3, f"{row['price']:.2f}")
            self._set_table_item(self.favorite_table, i, 4, f"{row['change_pct']:.2f}%", True, row['change_pct'])
            self._set_table_item(self.favorite_table, i, 5, f"{row['profit_3m']:.2f}%", True, row['profit_3m'])
            self._set_table_item(self.favorite_table, i, 6, f"{row['profit_1y']:.2f}%", True, row['profit_1y'])

            view_btn = QPushButton('查看详情')
            view_btn.setStyleSheet("background-color: #52c41a; padding: 4px; border-radius: 2px;")
            view_btn.clicked.connect(lambda _, name=row['name']: self.show_stock_detail(name))

            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(view_btn)
            layout.setAlignment(Qt.AlignCenter)
            self.favorite_table.setCellWidget(i, 7, widget)

        self.favorite_table.setUpdatesEnabled(True)

    def add_favorite(self):
        if self.df.empty:
            QMessageBox.warning(self, '提示', '当前暂无真实数据')
            return

        stock_name, ok = QInputDialog.getText(self, '添加自选股', '请输入股票名称:')
        if ok and stock_name:
            stock_name = stock_name.strip()
            if not self.df[self.df['name'] == stock_name].empty:
                if stock_name not in self.favorite_stocks:
                    self.favorite_stocks.append(stock_name)
                    self.save_favorite_stocks()
                    self.update_favorite_tab()
                    self.status_bar.showMessage(f'已添加自选股：{stock_name}', 3000)
                else:
                    QMessageBox.warning(self, '提示', f'{stock_name} 已在列表中')
            else:
                QMessageBox.warning(self, '错误', '未找到该股票')

    def remove_favorite(self):
        if not self.favorite_stocks:
            return
        stock_name, ok = QInputDialog.getItem(self, '移除自选股', '请选择:', self.favorite_stocks, 0, False)
        if ok and stock_name:
            self.favorite_stocks.remove(stock_name)
            self.save_favorite_stocks()
            self.update_favorite_tab()
            self.status_bar.showMessage(f'已移除自选股：{stock_name}', 3000)

    def show_stock_detail(self, stock_name):
        if self.df.empty:
            return

        row = self.df[self.df['name'] == stock_name].iloc[0]
        msg = (
            f"<b>{row['name']}</b> ({row['code']})<br><br>"
            f"行业: {row['industry']}<br>"
            f"现价: <font color='{'red' if row['change_pct'] >= 0 else 'green'}'>{row['price']:.2f}</font><br>"
            f"涨跌幅: {row['change_pct']:.2f}%<br>"
            f"成交额: {row['amount']:.2f} 亿<br>"
            f"3个月收益: {row['profit_3m']:.2f}%<br>"
            f"6个月收益: {row['profit_6m']:.2f}%<br>"
            f"1年收益: {row['profit_1y']:.2f}%<br>"
            f"20日波动率: {row['volatility_20d']:.2f}%<br>"
            f"MA20: {row['ma20']:.2f}<br>"
            f"MA60: {row['ma60']:.2f}"
        )
        QMessageBox.information(self, '股票详情', msg)

    def closeEvent(self, event):
        self.save_favorite_stocks()
        event.ignore()
        self.hide()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    app.setFont(QFont(UI_FONT_FAMILY, 10))
    window = StockAnalyzer()
    window.show()
    sys.exit(app.exec_())