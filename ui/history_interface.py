# coding: utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTableWidgetItem

from qfluentwidgets import PushButton, SubtitleLabel, InfoBar, InfoBarPosition, TableWidget

try:
    from ..core.storage import load_results, clear_results
    from ..core.settings import get_settings
except ImportError:
    # Запасной импорт при запуске из каталога
    from core.storage import load_results, clear_results  # type: ignore
    from core.settings import get_settings  # type: ignore


class HistoryInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('history-interface')
        self.settings = get_settings()

        self.vBox = QVBoxLayout(self)
        self.vBox.setContentsMargins(24, 24, 24, 24)
        self.vBox.setSpacing(12)

        self.title = SubtitleLabel('История результатов', self)
        self.title.setAlignment(Qt.AlignHCenter)

        self.table = TableWidget(self)
        self.table.setColumnCount(7)
        # Заголовки будут выставляться динамически в зависимости от единиц измерения
        self._update_headers()

        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(True)

        self.buttonsRow = QHBoxLayout()
        self.refreshBtn = PushButton('Обновить', self)
        self.clearBtn = PushButton('Очистить', self)
        self.buttonsRow.addStretch(1)
        self.buttonsRow.addWidget(self.refreshBtn)
        self.buttonsRow.addWidget(self.clearBtn)
        self.buttonsRow.addStretch(1)

        self.vBox.addWidget(self.title)
        self.vBox.addLayout(self.buttonsRow)
        self.vBox.addWidget(self.table)

        self.refreshBtn.clicked.connect(self.refresh)
        self.clearBtn.clicked.connect(self.clear)
        # Перестраиваем заголовки/значения при изменении настроек единиц
        self.settings.changed.connect(self._on_setting_changed)

        self.refresh()

    def _info(self, text: str):
        InfoBar.success(title='Готово', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _error(self, text: str):
        InfoBar.error(title='Ошибка', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _units(self) -> str:
        return self.settings.get('units', 'Mbps')

    def _update_headers(self):
        units = 'MB/s' if self._units() == 'MB/s' else 'Mbps'
        self.table.setHorizontalHeaderLabels([
            'Время',
            'Ping (ms)',
            f'Download ({units})',
            f'Upload ({units})',
            'Провайдер',
            'Город',
            'Хост',
        ])

    def _on_setting_changed(self, key: str, value):
        if key == 'units':
            self._update_headers()
            self.refresh()

    def refresh(self):
        results = load_results()
        self.table.setRowCount(len(results))
        for row, r in enumerate(results):
            s = r.get('server', {})

            # конвертация скоростей
            d_bps = (r.get('download_bps', 0.0) or 0.0)
            u_bps = (r.get('upload_bps', 0.0) or 0.0)
            if self._units() == 'MB/s':
                d_val = d_bps / 8e6
                u_val = u_bps / 8e6
            else:
                d_val = d_bps / 1e6
                u_val = u_bps / 1e6

            items = [
                QTableWidgetItem(str(r.get('timestamp', ''))),
                QTableWidgetItem(f"{r.get('ping_ms', 0):.0f}"),
                QTableWidgetItem(f"{d_val:.2f}"),
                QTableWidgetItem(f"{u_val:.2f}"),
                QTableWidgetItem(str(s.get('sponsor', ''))),
                QTableWidgetItem(str(s.get('name', ''))),
                QTableWidgetItem(str(s.get('host', ''))),
            ]
            for col, item in enumerate(items):
                item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                self.table.setItem(row, col, item)

        self.table.resizeColumnsToContents()

    def clear(self):
        try:
            clear_results()
            self.refresh()
            self._info('История очищена')
        except Exception as e:
            self._error(str(e))
