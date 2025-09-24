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
    CheckBox,
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
        self._servers: List[Dict] = []
        self._favorite_ids = set(int(x) for x in (self.settings.get('favorite_server_ids', []) or []) if x)

        # Интерфейс
        self.vBox = QVBoxLayout(self)
        self.vBox.setContentsMargins(24, 24, 24, 24)
        self.vBox.setSpacing(12)

        self.title = SubtitleLabel('Доступные сервера', self)
        self.title.setAlignment(Qt.AlignHCenter)

        self.currentLabel = BodyLabel(self)
        self._update_current_label()

        self.table = TableWidget(self)
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(['⭐', 'ID', 'Провайдер', 'Город', 'Страна', 'Хост'])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setSelectionMode(self.table.SingleSelection)

        self.buttonsRow = QHBoxLayout()
        self.onlyFav = CheckBox('Только избранные', self)
        self.refreshBtn = PushButton('Обновить', self)
        self.selectBtn = PrimaryPushButton('Выбрать сервер', self)
        self.clearBtn = PushButton('Сбросить выбор', self)
        self.addFavBtn = PushButton('В избранное ⭐', self)
        self.removeFavBtn = PushButton('Убрать из избранных', self)
        self.buttonsRow.addWidget(self.onlyFav)
        self.buttonsRow.addStretch(1)
        self.buttonsRow.addWidget(self.refreshBtn)
        self.buttonsRow.addWidget(self.selectBtn)
        self.buttonsRow.addWidget(self.clearBtn)
        self.buttonsRow.addWidget(self.addFavBtn)
        self.buttonsRow.addWidget(self.removeFavBtn)
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
        self.addFavBtn.clicked.connect(self.add_favorite)
        self.removeFavBtn.clicked.connect(self.remove_favorite)
        self.onlyFav.stateChanged.connect(lambda _v: self._populate_table())

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
        self._servers = servers
        self._populate_table()

    def _populate_table(self):
        servers = self._servers
        if self.onlyFav.isChecked():
            servers = [sv for sv in servers if self._is_favorite(sv.get('id'))]

        self.table.setRowCount(len(servers))
        sid_selected = self.settings.get('server_id', None)
        selected_row = -1

        for row, sv in enumerate(servers):
            sid = sv.get('id')
            star = '★' if self._is_favorite(sid) else ''
            items = [
                QTableWidgetItem(star),
                QTableWidgetItem(str(sid or '')),
                QTableWidgetItem(str(sv.get('sponsor') or '')),
                QTableWidgetItem(str(sv.get('name') or '')),
                QTableWidgetItem(str(sv.get('country') or '')),
                QTableWidgetItem(str(sv.get('host') or '')),
            ]
            for col, item in enumerate(items):
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

            try:
                if sid_selected and sid and int(sid) == int(sid_selected):
                    selected_row = row
            except Exception:
                pass

        self.table.resizeColumnsToContents()
        if selected_row >= 0:
            self.table.selectRow(selected_row)

    # избранное
    def _is_favorite(self, sid) -> bool:
        try:
            return int(sid) in self._favorite_ids
        except Exception:
            return False

    def _save_favorites(self):
        self.settings.set('favorite_server_ids', sorted(self._favorite_ids))

    def _get_selected_sid(self) -> Optional[int]:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 1)  # колонка ID
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def add_favorite(self):
        sid = self._get_selected_sid()
        if sid is None:
            self._warn('Выберите сервер')
            return
        if sid in self._favorite_ids:
            self._info('Сервер уже в избранных')
            return
        self._favorite_ids.add(sid)
        self._save_favorites()
        self._info(f'Добавлено в избранные: ID={sid}')
        self._populate_table()

    def remove_favorite(self):
        sid = self._get_selected_sid()
        if sid is None:
            self._warn('Выберите сервер')
            return
        if sid not in self._favorite_ids:
            self._warn('Сервера нет в избранных')
            return
        self._favorite_ids.discard(sid)
        self._save_favorites()
        self._info(f'Удалено из избранных: ID={sid}')
        self._populate_table()

    # Действия
    def select_server(self):
        sid = self._get_selected_sid()
        if sid is None:
            self._warn('Выберите строку в таблице')
            return
        self.settings.set('server_id', sid)
        self._update_current_label()
        self._info(f'Сервер выбран: ID={sid}')

    def clear_selection(self):
        self.settings.set('server_id', None)
        self._update_current_label()
        self._info('Выбор сервера сброшен — будет использоваться лучший сервер')
