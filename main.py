"""
每日一言
每天分享一句话，激励大家学习。
"""

import time
from datetime import datetime, timedelta
from pathlib import Path

import requests
from ClassWidgets.SDK import CW2Plugin, PluginAPI
from PySide6.QtCore import QTimer, Signal, QThread, Slot
from loguru import logger

WIDGET_ID = 'widget_yiyan'
WIDGET_NAME = '每日一言 | LaoShui'
API_URL = "https://api.codelife.cc/yiyan/info?lang=cn"

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/91.0.4472.124 Safari/537.36 Edge/91.0.864.64'
    )
}


class FetchThread(QThread):
    """网络请求线程"""
    fetch_finished = Signal(dict)  # 成功信号
    fetch_failed = Signal()  # 失败信号

    def __init__(self):
        super().__init__()
        self.max_retries = 3

    def run(self):
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                response = requests.get(API_URL, headers=HEADERS, proxies={'http': None, 'https': None})
                response.raise_for_status()
                data = response.json().get("data", {})
                if data:
                    self.fetch_finished.emit(data)
                    return
            except Exception as e:
                logger.error(f"请求失败: {e}")

            retry_count += 1
            time.sleep(2)

        self.fetch_failed.emit()


class Plugin(CW2Plugin):
    # 定义信号，用于通知QML更新内容
    contentUpdated = Signal(str, str)

    def __init__(self, api: PluginAPI):
        super().__init__(api)
        # 初始化插件
        self.api = api
        self.content = "加载中，请稍后..."
        self.author = "LaoShui"

        # 注册小组件
        widget_qml_path = Path(__file__).parent / "widget_yiyan.qml"
        self.api.widgets.register(
            widget_id=WIDGET_ID,
            name=WIDGET_NAME,
            qml_path=widget_qml_path,
            backend_obj=self  # 将自身作为后端对象传递给QML
        )

        # 新增定时器用于延迟重试
        self.retry_timer = QTimer()
        self.retry_timer.timeout.connect(self.update_yiyan)

        # 新增每日定时更新定时器
        self.daily_timer = QTimer()
        self.daily_timer.timeout.connect(self.daily_update)

        # 添加每日更新状态跟踪
        self.last_update_date = None

        self.setup_daily_update()

    def setup_daily_update(self):
        """设置每日1点自动更新"""
        now = datetime.now()
        # 计算下一个1点的时间
        next_update = now.replace(hour=1, minute=0, second=0, microsecond=0)

        # 如果当前时间已经过了今天的1点，则设置为明天1点
        if now >= next_update:
            next_update += timedelta(days=1)

        # 计算距离下次更新的毫秒数
        time_until_update = (next_update - now).total_seconds() * 1000

        # 设置单次定时器，到时间后触发更新并重新设置下一次
        self.daily_timer.setSingleShot(True)
        self.daily_timer.start(int(time_until_update))

        logger.info(f"下次自动更新时间: {next_update.strftime('%Y-%m-%d %H:%M:%S')}")

    def daily_update(self):
        """每日定时更新"""
        today = datetime.now().date()

        # 检查今天是否已经更新过
        if self.last_update_date == today:
            logger.info("今日已更新过，跳过本次更新")
            self.setup_daily_update()  # 重新设置下一次更新
            return

        # 执行更新
        self.update_yiyan()

        # 重新设置下一次更新
        self.setup_daily_update()

    def update_yiyan(self):
        """启动异步更新每日一言"""
        self.contentUpdated.emit("加载中，请稍后...", "LaoShui")
        self.retry_timer.stop()

        self.worker_thread = FetchThread()
        self.worker_thread.fetch_finished.connect(self.handle_success)
        self.worker_thread.fetch_failed.connect(self.handle_failure)
        self.worker_thread.start()

    @Slot()
    def init_content(self):
        """QML初始化时调用，获取当前内容"""
        logger.info("QML requested content initialization")
        self.contentUpdated.emit(self.content, self.author)

    def handle_success(self, data):
        """处理成功响应"""
        content = data.get("content", "无法获取一言信息。")
        author = data.get("author", "未知作者")

        self.content = content
        self.author = author
        self.contentUpdated.emit(content, author)

        # 记录更新日期
        self.last_update_date = datetime.now().date()
        logger.info(f"一言更新成功，更新日期: {self.last_update_date}")

    def handle_failure(self):
        """处理失败情况"""
        logger.warning("重试3次失败，5分钟后自动重试")
        self.contentUpdated.emit("网络连接异常，5分钟后自动重试", "LaoShui")
        self.retry_timer.start(5 * 60 * 1000)  # 5分钟重试

    def on_load(self):
        """插件加载时执行"""
        super().on_load()
        logger.info("每日一言插件加载成功！")
        # 延迟一小段时间执行更新，确保初始化完成
        QTimer.singleShot(100, self.update_yiyan)

    def on_unload(self):
        """插件卸载时执行"""
        logger.info("每日一言插件卸载成功！")
        self.retry_timer.stop()
        self.daily_timer.stop()
