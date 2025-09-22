# coding: utf-8
from typing import List, Dict, Optional
import logging

from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem

from qfluentwidgets import (
    SubtitleLabel,
    BodyLabel,
    PushButton,
    PrimaryPushButton,
    InfoBar,
    InfoBarPosition,
    TableWidget,
)

logger = logging.getLogger(__name__)

try:
    from ..core.speedtest_client import SpeedtestClient
    from ..core.settings import get_settings
except ImportError:  # запуск как скрипт в папке
    from core.speedtest_client import SpeedtestClient  # type: ignore
    from core.settings import get_settings  # type: ignore


class _ServersLoader(QObject):
    started = pyqtSignal()
    error = pyqtSignal(str)
    finished = pyqtSignal(list)

    def __init__(self, limit: int = 200):
        super().__init__()
        self.limit = limit

    def run(self):
        try:
            self.started.emit()
            client = SpeedtestClient()
            servers = client.list_servers(limit=self.limit)
            self.finished.emit(servers)
        except Exception as e:
            logger.exception("Не удалось получить список серверов")
            self.error.emit(str(e))


class ServersInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('servers-interface')

        self.settings = get_settings()

        # Интерфейс
        self.vBox = QVBoxLayout(self)
        self.vBox.setContentsMargins(24, 24, 24, 24)
        self.vBox.setSpacing(12)

        self.title = SubtitleLabel('Доступные сервера', self)
        self.title.setAlignment(Qt.AlignHCenter)

        self.currentLabel = BodyLabel(self)
        self._update_current_label()

        self.table = TableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(['ID', 'Провайдер', 'Город', 'Страна', 'Хост'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)

        self.buttonsRow = QHBoxLayout()
        self.refreshBtn = PushButton('Обновить', self)
        self.selectBtn = PrimaryPushButton('Выбрать сервер', self)
        self.clearBtn = PushButton('Сбросить выбор', self)
        self.buttonsRow.addStretch(1)
        self.buttonsRow.addWidget(self.refreshBtn)
        self.buttonsRow.addWidget(self.selectBtn)
        self.buttonsRow.addWidget(self.clearBtn)
        self.buttonsRow.addStretch(1)

        self.vBox.addWidget(self.title)
        self.vBox.addWidget(self.currentLabel)
        self.vBox.addLayout(self.buttonsRow)
        self.vBox.addWidget(self.table)

        # фоновый загрузчик
        self._thread: Optional[QThread] = None
        self._loader: Optional[_ServersLoader] = None

        # события
        self.refreshBtn.clicked.connect(self.refresh)
        self.selectBtn.clicked.connect(self.select_server)
        self.clearBtn.clicked.connect(self.clear_selection)

        # начальный загрузчик
        self.refresh()

    # Помощники
    def _info(self, text: str):
        InfoBar.success(title='Готово', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _warn(self, text: str):
        InfoBar.warning(title='Внимание', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _error(self, text: str):
        InfoBar.error(title='Ошибка', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _update_current_label(self):
        sid = self.settings.get('server_id', None)
        if sid:
            self.currentLabel.setText(f"Текущий сервер: ID={sid}")
        else:
            self.currentLabel.setText('Текущий сервер: автоматически (лучший)')

    # Загрузка данных
    def refresh(self):
        if self._thread is not None:
            self._warn('Идёт обновление списка...')
            return

        self.table.setRowCount(0)

        self._thread = QThread(self)
        self._loader = _ServersLoader(limit=300)
        self._loader.moveToThread(self._thread)

        self._thread.started.connect(self._loader.run)
        self._loader.started.connect(lambda: self.refreshBtn.setDisabled(True))
        self._loader.error.connect(lambda msg: self._error(msg))
        self._loader.finished.connect(self._on_servers_loaded)
        self._loader.finished.connect(lambda _s: self.refreshBtn.setEnabled(True))
        self._loader.finished.connect(self._cleanup_thread)

        self._thread.start()

    def _cleanup_thread(self):
        try:
            if self._thread:
                self._thread.quit()
                self._thread.wait(1000)
        finally:
            self._thread = None
            self._loader = None

    def _on_servers_loaded(self, servers: List[Dict]):
        self.table.setRowCount(len(servers))
        sid_selected = self.settings.get('server_id', None)

        selected_row = -1
        for row, sv in enumerate(servers):
            items = [
                QTableWidgetItem(str(sv.get('id') or '')),
                QTableWidgetItem(str(sv.get('sponsor') or '')),
                QTableWidgetItem(str(sv.get('name') or '')),
                QTableWidgetItem(str(sv.get('country') or '')),
                QTableWidgetItem(str(sv.get('host') or '')),
            ]
            for col, item in enumerate(items):
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

            # Попытка выбора текущего сервера
            try:
                if sid_selected and int(sv.get('id')) == int(sid_selected):
                    selected_row = row
            except Exception:
                pass

        self.table.resizeColumnsToContents()
        if selected_row >= 0:
            self.table.selectRow(selected_row)

    # Действия
    def select_server(self):
        row = self.table.currentRow()
        if row < 0:
            self._warn('Выберите строку в таблице')
            return
        item = self.table.item(row, 0)
        if not item:
            self._error('Не удалось прочитать ID сервера')
            return
        try:
            sid = int(item.text())
        except Exception:
            self._error('Некорректный ID сервера')
            return
        self.settings.set('server_id', sid)
        self._update_current_label()
        self._info(f'Сервер выбран: ID={sid}')

    def clear_selection(self):
        self.settings.set('server_id', None)
        self._update_current_label()
        self._info('Выбор сервера сброшен — будет использоваться лучший сервер')
