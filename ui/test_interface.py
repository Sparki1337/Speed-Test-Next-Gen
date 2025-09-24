# coding: utf-8
import logging
from datetime import datetime

from PyQt5.QtCore import Qt, QThread
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel

try:
    from qfluentwidgets import (
        PrimaryPushButton,
        PushButton,
        IndeterminateProgressRing,
        SubtitleLabel,
        TextBrowser,
        InfoBar,
        InfoBarPosition,
        FluentIcon as FIF,
    )
    LogViewClass = TextBrowser
except ImportError:
    # На некоторых версиях QFluentWidgets компонента TextBrowser нет — используем TextEdit,
    # если и его нет, то откатываемся на стандартный QTextBrowser из PyQt5
    try:
        from qfluentwidgets import (
            PrimaryPushButton,
            PushButton,
            IndeterminateProgressRing,
            SubtitleLabel,
            TextEdit,
            InfoBar,
            InfoBarPosition,
            FluentIcon as FIF,
        )
        LogViewClass = TextEdit
    except ImportError:
        from qfluentwidgets import (
            PrimaryPushButton,
            PushButton,
            IndeterminateProgressRing,
            SubtitleLabel,
            BodyLabel,
            InfoBar,
            InfoBarPosition,
            FluentIcon as FIF,
        )
        from PyQt5.QtWidgets import QTextBrowser as LogViewClass

try:
    from ..core.worker import SpeedtestWorker, PreciseSpeedtestWorker
    from ..core.storage import append_result
    from ..core.settings import get_settings
except ImportError:
    # Запуск без пакета: импорт из локальной папки
    from core.worker import SpeedtestWorker, PreciseSpeedtestWorker  # type: ignore
    from core.storage import append_result  # type: ignore
    from core.settings import get_settings  # type: ignore

logger = logging.getLogger(__name__)


class TestInterface(QWidget):
    def __init__(self, emitter=None, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('test-interface')
        self.settings = get_settings()

        # UI
        self.vBox = QVBoxLayout(self)
        self.vBox.setContentsMargins(24, 24, 24, 24)
        self.vBox.setSpacing(16)

        self.ring = IndeterminateProgressRing(self)
        self.ring.setFixedSize(90, 90)
        self.ring.hide()

        self.cardContainer = QWidget(self)
        self.cardContainer.setVisible(False)
        self.cardContainerLayout = QHBoxLayout(self.cardContainer)
        self.cardContainerLayout.setContentsMargins(0, 0, 0, 0)
        self.cardContainerLayout.setSpacing(12)

        self.cardPing = ResultCard(icon=FIF.WIFI, title='Ping', suffix='ms', parent=self.cardContainer)
        self.cardDownload = ResultCard(icon=FIF.DOWNLOAD, title='Download', parent=self.cardContainer)
        self.cardUpload = ResultCard(icon=FIF.CLOUD_DOWNLOAD, title='Upload', parent=self.cardContainer)

        for card in (self.cardPing, self.cardDownload, self.cardUpload):
            self.cardContainerLayout.addWidget(card, 1)

        self.buttonsRow = QHBoxLayout()
        self.startBtn = PrimaryPushButton('Тест', self, icon=FIF.PLAY)
        self.preciseBtn = PrimaryPushButton('Точный тест', self, icon=FIF.PLAY)
        self.stopBtn = PushButton('Стоп', self, icon=FIF.STOP_WATCH)
        self.stopBtn.setDisabled(True)
        self.buttonsRow.addStretch(1)
        self.buttonsRow.addWidget(self.startBtn)
        self.buttonsRow.addWidget(self.preciseBtn)
        self.buttonsRow.addWidget(self.stopBtn)
        self.buttonsRow.addStretch(1)

        self.logView = LogViewClass(self)
        self.logView.setPlaceholderText('Логи выполнения будут отображаться здесь...')
        self.logView.setMinimumHeight(180)
        self.logView.setVisible(True)

        self.vBox.addWidget(self.ring, 0, Qt.AlignHCenter)
        self.vBox.addLayout(self.buttonsRow)
        self.vBox.addWidget(self.cardContainer)
        self.vBox.addWidget(self.logView)

        # worker/thread
        self.thread: QThread = None
        self.worker = None  # SpeedtestWorker | PreciseSpeedtestWorker

        # события
        self.startBtn.clicked.connect(self.start_test)
        self.preciseBtn.clicked.connect(self.start_precise_test)
        self.stopBtn.clicked.connect(self.stop_test)

        # подключение UI logger emitter
        if emitter is not None:
            emitter.message.connect(self._append_log)

        # подписаться на изменения настроек (переключатель логов)
        self.settings.changed.connect(self._on_setting_changed)

        self._apply_theme_to_cards()

    # Логика
    def _info(self, text: str):
        InfoBar.success(title='Инфо', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _warn(self, text: str):
        InfoBar.warning(title='Внимание', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _error(self, text: str):
        InfoBar.error(title='Ошибка', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _append_log(self, line: str):
        self.logView.append(line)

    def _format_speed(self, bps: float) -> str:
        units = self.settings.get('units', 'Mbps')
        if units == 'MB/s':
            return f"{bps / 8e6:.2f} MB/s"
        return f"{bps / 1e6:.2f} Mbps"

    def _on_setting_changed(self, key: str, value):
        if key == 'theme':
            self._apply_theme_to_cards(str(value))

    def _on_stage_changed(self, stage: str):
        if stage in {'init', 'servers', 'best', 'download', 'upload', 'saving'}:
            self.ring.show()
        elif stage in {'done', 'canceled', 'error'}:
            self.ring.hide()

    def start_test(self):
        if self.thread is not None:
            self._warn('Тест уже выполняется')
            return

        self.logView.clear()
        self.startBtn.setDisabled(True)
        self.preciseBtn.setDisabled(True)
        self.stopBtn.setEnabled(True)
        self.ring.show()
        self.cardContainer.setVisible(False)

        self.thread = QThread(self)
        self.worker = SpeedtestWorker()
        self.worker.moveToThread(self.thread)

        # подключаем сигналы (queued гарантирует вызов слота в потоке worker)
        self.thread.started.connect(self.worker.run, type=Qt.QueuedConnection)
        self.worker.stageChanged.connect(self._on_stage_changed)
        self.worker.log.connect(self._append_log)
        self.worker.resultReady.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)

        self.thread.start()

    def start_precise_test(self):
        if self.thread is not None:
            self._warn('Тест уже выполняется')
            return

        self.logView.clear()
        self.startBtn.setDisabled(True)
        self.preciseBtn.setDisabled(True)
        self.stopBtn.setEnabled(True)
        self.ring.show()
        self.cardContainer.setVisible(False)

        self.thread = QThread(self)
        self.worker = PreciseSpeedtestWorker()
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run, type=Qt.QueuedConnection)
        self.worker.stageChanged.connect(self._on_stage_changed)
        # лог сигнал может не использоваться, но подключим на будущее
        try:
            self.worker.log.connect(self._append_log)  # type: ignore[attr-defined]
        except Exception:
            pass
        self.worker.resultReady.connect(self._on_result)
        self.worker.error.connect(self._on_error)
        self.worker.finished.connect(self._on_finished)

        self.thread.start()

    def stop_test(self):
        if self.worker:
            self.worker.cancel()

    def _on_result(self, result: dict):
        # persist
        append_result(result)

        # update UI values
        ping = result.get('ping_ms', 0)
        d_bps = result.get('download_bps', 0.0)
        u_bps = result.get('upload_bps', 0.0)

        self.cardPing.update_value(f"{ping:.0f}")
        self.cardDownload.update_value(self._format_speed(d_bps))
        self.cardUpload.update_value(self._format_speed(u_bps))
        self.cardContainer.setVisible(True)

        self._info('Результат сохранён')

    def _apply_theme_to_cards(self, theme_name: str = None):
        theme = theme_name or str(self.settings.get('theme', 'Dark'))
        for card in (self.cardPing, self.cardDownload, self.cardUpload):
            card.set_theme(theme)

    def _on_error(self, msg: str):
        self._error(msg)
        self._append_log(f"Ошибка: {msg}")

    def _on_finished(self):
        try:
            if self.thread:
                self.thread.quit()
                self.thread.wait(1000)
        finally:
            self.thread = None
            self.worker = None
            self.startBtn.setEnabled(True)
            self.preciseBtn.setEnabled(True)
            self.stopBtn.setDisabled(True)
            self.ring.hide()


class ResultCard(QFrame):
    def __init__(self, icon: FIF, title: str, suffix: str = '', parent=None):
        super().__init__(parent)
        self._suffix = suffix
        self._icon = icon

        self.setObjectName('resultCard')
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)

        self.vLayout = QVBoxLayout(self)
        self.vLayout.setContentsMargins(12, 12, 12, 12)
        self.vLayout.setSpacing(8)

        self.iconLabel = QLabel(self)
        self.iconLabel.setAlignment(Qt.AlignHCenter)
        self.iconLabel.setObjectName('iconLabel')

        self.titleLabel = QLabel(title, self)
        self.titleLabel.setObjectName('titleLabel')
        self.titleLabel.setAlignment(Qt.AlignHCenter)

        self.valueLabel = QLabel('—', self)
        self.valueLabel.setObjectName('valueLabel')
        self.valueLabel.setAlignment(Qt.AlignHCenter)

        self.vLayout.addWidget(self.iconLabel)
        self.vLayout.addWidget(self.titleLabel)
        self.vLayout.addWidget(self.valueLabel)

        self.set_theme('Dark')

    def update_value(self, value: str):
        self.valueLabel.setText(value if not self._suffix else f"{value} {self._suffix}")

    def set_theme(self, theme: str):
        theme_name = (theme or 'Dark').lower()
        if theme_name == 'light':
            bg = 'rgba(0, 0, 0, 0.04)'
            title_color = 'rgba(0, 0, 0, 0.6)'
            value_color = '#111111'
            icon_color = QColor('#222222')
        else:
            bg = 'rgba(255, 255, 255, 0.06)'
            title_color = 'rgba(255, 255, 255, 0.70)'
            value_color = '#FFFFFF'
            icon_color = QColor('#F2F2F2')

        self.setStyleSheet(
            "#resultCard {"
            "border-radius: 12px;"
            "padding: 16px;"
            f"background-color: {bg};"
            "}"
            "#resultCard QLabel#titleLabel {"
            "font-size: 14px;"
            f"color: {title_color};"
            "}"
            "#resultCard QLabel#valueLabel {"
            "font-size: 20px;"
            "font-weight: 600;"
            f"color: {value_color};"
            "}"
        )

        pixmap = self._icon.icon(color=icon_color).pixmap(32, 32)
        self.iconLabel.setPixmap(pixmap)
