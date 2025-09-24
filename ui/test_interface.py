# coding: utf-8
import logging
from datetime import datetime

from PyQt5.QtCore import Qt, QThread
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel
from PyQt5.QtGui import QColor

try:
    from qfluentwidgets import (
        PrimaryPushButton,
        PushButton,
        IndeterminateProgressRing,
        SubtitleLabel,
        BodyLabel,
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
            BodyLabel,
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
    from fluent_speedtest.utils import import_attrs
except ImportError:  # запуск из каталога
    from utils import import_attrs  # type: ignore

SpeedtestWorker, PreciseSpeedtestWorker = import_attrs("core.worker", "SpeedtestWorker", "PreciseSpeedtestWorker")
append_result, = import_attrs("core.storage", "append_result")
get_settings, = import_attrs("core.settings", "get_settings")

logger = logging.getLogger(__name__)


class TestInterface(QWidget):
    def __init__(self, emitter=None, parent=None):
        super().__init__(parent=parent)
        self.setObjectName('test-interface')
        self.settings = get_settings()
        self._logs_enabled = bool(self.settings.get('logs_enabled', True))
        self._emitter = emitter
        self._emitter_connected = False

        # UI
        self.vBox = QVBoxLayout(self)
        self.vBox.setContentsMargins(24, 24, 24, 24)
        self.vBox.setSpacing(16)

        self.title = SubtitleLabel('', self)
        self.title.setAlignment(Qt.AlignHCenter)
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
        self.startBtn = PrimaryPushButton('Старт', self, icon=FIF.PLAY)
        self.preciseBtn = PrimaryPushButton('Точный тест', self)
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
        # применить из настроек видимость панели логов
        self._apply_logs_enabled(self._logs_enabled)

        self.vBox.addWidget(self.title)
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

        # Подключение UI logger emitter (если разрешено)
        self._connect_emitter()

        # Подписка на изменения настроек (переключатель логов/темы)
        self.settings.changed.connect(self._on_setting_changed)

        self._apply_theme_to_cards()

    # ============== logic ==============
    def _info(self, text: str):
        InfoBar.success(title='Инфо', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _warn(self, text: str):
        InfoBar.warning(title='Внимание', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _error(self, text: str):
        InfoBar.error(title='Ошибка', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _append_log(self, line: str):
        # если логи выключены — игнорируем
        if not self._logs_enabled:
            return
        self.logView.append(line)

    def _format_speed(self, bps: float) -> str:
        units = self.settings.get('units', 'Mbps')
        if units == 'MB/s':
            return f"{bps / 8e6:.2f} MB/s"
        return f"{bps / 1e6:.2f} Mbps"

    def _connect_emitter(self):
        if not self._logs_enabled or self._emitter is None or self._emitter_connected:
            return
        try:
            self._emitter.message.connect(self._append_log)
        except Exception:
            return
        self._emitter_connected = True

    def _disconnect_emitter(self):
        if not self._emitter_connected or self._emitter is None:
            return
        try:
            self._emitter.message.disconnect(self._append_log)
        except TypeError:
            pass
        self._emitter_connected = False

    def _apply_logs_enabled(self, enabled: bool):
        enabled = bool(enabled)
        self._logs_enabled = enabled
        self.logView.setVisible(enabled)
        if enabled:
            self.logView.setMinimumHeight(180)
            self._connect_emitter()
        else:
            self.logView.setMinimumHeight(0)
            self.logView.clear()
            self._disconnect_emitter()

    def _on_setting_changed(self, key: str, value):
        if key == 'logs_enabled':
            self._apply_logs_enabled(bool(value))
        elif key == 'theme':
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
        # Сохранение результата
        append_result(result)

        # Обновление карточек
        ping = result.get('ping_ms', 0)
        d_bps = result.get('download_bps', 0.0)
        u_bps = result.get('upload_bps', 0.0)

        self.cardPing.update_value(f"{ping:.0f}")
        self.cardDownload.update_value(self._format_speed(d_bps))
        self.cardUpload.update_value(self._format_speed(u_bps))
        self.cardContainer.setVisible(True)

        self._info('Результат сохранён')

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

    def _apply_theme_to_cards(self, theme_name: str = None):
        theme = theme_name or str(self.settings.get('theme', 'Dark'))
        for card in (self.cardPing, self.cardDownload, self.cardUpload):
            card.set_theme(theme)


class ResultCard(QFrame):
    def __init__(self, icon: FIF, title: str, suffix: str = '', parent=None):
        super().__init__(parent)
        self._suffix = suffix
        self.setObjectName('resultCard')
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self._icon = icon

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
            f"#resultCard {{"
            f"border-radius: 12px;"
            f"padding: 16px;"
            f"background-color: {bg};"
            f"}}"
            f"#resultCard QLabel#titleLabel {{"
            f"font-size: 14px;"
            f"color: {title_color};"
            f"}}"
            f"#resultCard QLabel#valueLabel {{"
            f"font-size: 20px;"
            f"font-weight: 600;"
            f"color: {value_color};"
            f"}}"
        )

        pixmap = self._icon.icon(color=icon_color).pixmap(32, 32)
        self.iconLabel.setPixmap(pixmap)
