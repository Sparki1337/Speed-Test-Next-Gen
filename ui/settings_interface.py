# coding: utf-8
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from qfluentwidgets import (
    ComboBox,
    SubtitleLabel,
    BodyLabel,
    SwitchButton,
    InfoBar,
    InfoBarPosition,
    setTheme,
    Theme,
)

try:
    from fluent_speedtest.utils import import_attrs
except ImportError:
    from utils import import_attrs  # type: ignore

get_settings, = import_attrs("core.settings", "get_settings")


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

        # Включить логи
        self.logsRow = QHBoxLayout()
        self.logsLabel = BodyLabel('Логи:')
        self.logsSwitch = SwitchButton('Включить логи', self)
        self.logsRow.addWidget(self.logsLabel)
        self.logsRow.addWidget(self.logsSwitch)

        self.vBox.addWidget(self.title)
        self.vBox.addLayout(self.unitsRow)
        self.vBox.addLayout(self.themeRow)
        self.vBox.addLayout(self.logsRow)
        self.vBox.addStretch(1)

        # Загрузка сохранённых настроек
        units = self.settings.get('units', 'Mbps')
        self.unitsBox.setCurrentText(units)
        theme = self.settings.get('theme', 'Dark')
        self.themeBox.setCurrentText(theme)
        logs_enabled = bool(self.settings.get('logs_enabled', True))
        self.logsSwitch.setChecked(logs_enabled)
        self.logsSwitch.setText('Включить логи' if logs_enabled else 'Отключить логи')

        # События
        self.unitsBox.currentTextChanged.connect(self.on_units_changed)
        self.themeBox.currentTextChanged.connect(self.on_theme_changed)
        self.logsSwitch.checkedChanged.connect(self.on_logs_toggled)

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

    def on_logs_toggled(self, checked: bool):
        self.settings.set('logs_enabled', bool(checked))
        self.logsSwitch.setText('Включить логи' if checked else 'Отключить логи')
        # InfoBar покажет подтверждение, само включение/выключение обработчиков будет сделано в main через сигнал settings.changed
        self._info('Логи ' + ('включены' if checked else 'выключены'))
