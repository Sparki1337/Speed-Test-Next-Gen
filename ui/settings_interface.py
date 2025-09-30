# coding: utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFileDialog

from qfluentwidgets import (
    ComboBox,
    SubtitleLabel,
    BodyLabel,
    LineEdit,
    PushButton,
    InfoBar,
    InfoBarPosition,
    setTheme,
    Theme,
)

try:
    from ..core.settings import get_settings
except ImportError:
    from core.settings import get_settings  # type: ignore


class SettingsInterface(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('settings-interface')
        self.settings = get_settings()

        self.vBox = QVBoxLayout(self)
        self.vBox.setContentsMargins(24, 24, 24, 24)
        self.vBox.setSpacing(12)

        self.title = SubtitleLabel('Настройки', self)
        self.title.setAlignment(Qt.AlignHCenter)

        # Единицы скорости
        self.unitsRow = QHBoxLayout()
        self.unitsLabel = BodyLabel('Единицы скорости:')
        self.unitsBox = ComboBox(self)
        self.unitsBox.addItems(['Mbps', 'MB/s'])
        self.unitsRow.addWidget(self.unitsLabel)
        self.unitsRow.addWidget(self.unitsBox)

        # Тема
        self.themeRow = QHBoxLayout()
        self.themeLabel = BodyLabel('Тема:')
        self.themeBox = ComboBox(self)
        self.themeBox.addItems(['Dark', 'Light'])
        self.themeRow.addWidget(self.themeLabel)
        self.themeRow.addWidget(self.themeBox)

        # Движок
        self.engineRow = QHBoxLayout()
        self.engineLabel = BodyLabel('Движок теста:')
        self.engineBox = ComboBox(self)
        self.engineBox.addItem('Python (speedtest-cli)', userData='python')
        self.engineBox.addItem('Ookla CLI (speedtest.exe)', userData='ookla')
        self.engineRow.addWidget(self.engineLabel)
        self.engineRow.addWidget(self.engineBox)

        # Путь к speedtest.exe
        self.ooklaPathRow = QHBoxLayout()
        self.ooklaPathLabel = BodyLabel('Путь к speedtest.exe:')
        self.ooklaPathEdit = LineEdit(self)
        self.ooklaBrowseBtn = PushButton('Обзор', self)
        self.ooklaPathRow.addWidget(self.ooklaPathLabel)
        self.ooklaPathRow.addWidget(self.ooklaPathEdit, 1)
        self.ooklaPathRow.addWidget(self.ooklaBrowseBtn)

        # Таймаут для Ookla CLI
        self.ooklaTimeoutRow = QHBoxLayout()
        self.ooklaTimeoutLabel = BodyLabel('Таймаут Ookla (сек):')
        self.ooklaTimeoutBox = ComboBox(self)
        self.ooklaTimeoutBox.addItems(['30', '60', '90', '120'])
        self.ooklaTimeoutRow.addWidget(self.ooklaTimeoutLabel)
        self.ooklaTimeoutRow.addWidget(self.ooklaTimeoutBox)

        # Акцентный цвет
        self.accentColorRow = QHBoxLayout()
        self.accentColorLabel = BodyLabel('Акцентный цвет:')
        self.accentColorBox = ComboBox(self)
        self.accentColorBox.addItem('Синий', userData='blue')
        self.accentColorBox.addItem('Зелёный', userData='green')
        self.accentColorBox.addItem('Фиолетовый', userData='purple')
        self.accentColorBox.addItem('Красный', userData='red')
        self.accentColorBox.addItem('Оранжевый', userData='orange')
        self.accentColorBox.addItem('Розовый', userData='pink')
        self.accentColorRow.addWidget(self.accentColorLabel)
        self.accentColorRow.addWidget(self.accentColorBox)

        # Лимит записей истории
        self.maxRecordsRow = QHBoxLayout()
        self.maxRecordsLabel = BodyLabel('Макс. записей истории:')
        self.maxRecordsBox = ComboBox(self)
        self.maxRecordsBox.addItems(['100', '500', '1000', '2000', '5000', 'Без ограничений'])
        self.maxRecordsRow.addWidget(self.maxRecordsLabel)
        self.maxRecordsRow.addWidget(self.maxRecordsBox)

        self.vBox.addWidget(self.title)
        self.vBox.addLayout(self.unitsRow)
        self.vBox.addLayout(self.themeRow)
        self.vBox.addLayout(self.accentColorRow)
        self.vBox.addLayout(self.maxRecordsRow)
        self.vBox.addLayout(self.engineRow)
        self.vBox.addLayout(self.ooklaPathRow)
        self.vBox.addLayout(self.ooklaTimeoutRow)
        self.vBox.addStretch(1)

        # Загрузка сохранённых настроек
        units = self.settings.get('units', 'Mbps')
        self.unitsBox.setCurrentText(units)
        theme = self.settings.get('theme', 'Dark')
        self.themeBox.setCurrentText(theme)
        # engine
        engine = str(self.settings.get('engine', 'python'))
        idx = self.engineBox.findData(engine)
        if idx >= 0:
            self.engineBox.setCurrentIndex(idx)
        else:
            self.engineBox.setCurrentIndex(0)
        # ookla path
        self.ooklaPathEdit.setText(str(self.settings.get('ookla_path', '') or ''))
        # ookla timeout
        timeout_val = int(self.settings.get('ookla_timeout', 90) or 90)
        if str(timeout_val) in ['30', '60', '90', '120']:
            self.ooklaTimeoutBox.setCurrentText(str(timeout_val))
        else:
            self.ooklaTimeoutBox.setCurrentText('90')
        # accent color
        accent_color = str(self.settings.get('accent_color', 'blue'))
        accent_idx = self.accentColorBox.findData(accent_color)
        if accent_idx >= 0:
            self.accentColorBox.setCurrentIndex(accent_idx)
        else:
            self.accentColorBox.setCurrentIndex(0)
        # max records
        max_records = int(self.settings.get('max_history_records', 1000))
        if max_records >= 999999:
            self.maxRecordsBox.setCurrentText('Без ограничений')
        elif str(max_records) in ['100', '500', '1000', '2000', '5000']:
            self.maxRecordsBox.setCurrentText(str(max_records))
        else:
            self.maxRecordsBox.setCurrentText('1000')

        # первичная настройка видимости
        self._apply_engine_visibility()

        # События
        self.unitsBox.currentTextChanged.connect(self.on_units_changed)
        self.themeBox.currentTextChanged.connect(self.on_theme_changed)
        self.accentColorBox.currentIndexChanged.connect(self.on_accent_color_changed)
        self.maxRecordsBox.currentTextChanged.connect(self.on_max_records_changed)
        self.engineBox.currentIndexChanged.connect(self.on_engine_changed)
        self.ooklaBrowseBtn.clicked.connect(self.on_browse_ookla)
        # сохраняем путь по завершении редактирования
        try:
            self.ooklaPathEdit.editingFinished.connect(self.on_ookla_path_changed)
        except Exception:
            pass
        self.ooklaTimeoutBox.currentTextChanged.connect(self.on_ookla_timeout_changed)

    def _info(self, text: str):
        InfoBar.success(title='Готово', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def on_units_changed(self, v: str):
        self.settings.set('units', v)
        self._info('Единицы скорости сохранены')

    def on_theme_changed(self, v: str):
        self.settings.set('theme', v)
        if v == 'Dark':
            setTheme(Theme.DARK)
        else:
            setTheme(Theme.LIGHT)
        self._info('Тема применена')

    # Engine & Ookla
    def _apply_engine_visibility(self):
        engine = str(self.settings.get('engine', 'python')).lower()
        show = (engine == 'ookla')
        for w in (self.ooklaPathLabel, self.ooklaPathEdit, self.ooklaBrowseBtn,
                  self.ooklaTimeoutLabel, self.ooklaTimeoutBox):
            w.setVisible(show)

    def on_engine_changed(self, _idx: int):
        data = self.engineBox.currentData()
        engine = str(data or 'python')
        self.settings.set('engine', engine)
        self._apply_engine_visibility()
        self._info('Движок теста сохранён')

    def on_browse_ookla(self):
        path, _ = QFileDialog.getOpenFileName(self, 'Выбрать speedtest.exe', '', 'Executable (speedtest.exe);;All Files (*)')
        if path:
            self.ooklaPathEdit.setText(path)
            self.settings.set('ookla_path', path)
            self._info('Путь к speedtest.exe сохранён')

    def on_ookla_path_changed(self):
        path = self.ooklaPathEdit.text().strip()
        self.settings.set('ookla_path', path)
        self._info('Путь к speedtest.exe сохранён')

    def on_ookla_timeout_changed(self, v: str):
        try:
            val = int(v)
        except Exception:
            val = 90
        self.settings.set('ookla_timeout', val)
        self._info('Таймаут Ookla сохранён')

    def on_accent_color_changed(self, _idx: int):
        data = self.accentColorBox.currentData()
        color = str(data or 'blue')
        self.settings.set('accent_color', color)
        self._apply_accent_color(color)
        self._info('Акцентный цвет сохранён')

    def on_max_records_changed(self, v: str):
        if v == 'Без ограничений':
            val = 999999999
        else:
            try:
                val = int(v)
            except Exception:
                val = 1000
        self.settings.set('max_history_records', val)
        self._info('Лимит записей истории сохранён')

    def _apply_accent_color(self, color: str):
        """Применить акцентный цвет к элементам интерфейса."""
        # Цветовая палитра
        colors = {
            'blue': '#0078D4',
            'green': '#10893E',
            'purple': '#881798',
            'red': '#E81123',
            'orange': '#FF8C00',
            'pink': '#E3008C'
        }
        
        accent_hex = colors.get(color, '#0078D4')
        
        # Применяем стиль к кнопкам (можно расширить на другие элементы)
        try:
            from qfluentwidgets import setThemeColor
            from PyQt5.QtGui import QColor
            setThemeColor(QColor(accent_hex))
        except Exception:
            # Если не удалось применить через QFluentWidgets, игнорируем
            pass
