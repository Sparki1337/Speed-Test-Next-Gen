# coding: utf-8
import logging
from datetime import datetime

from PyQt5.QtCore import Qt, QThread
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

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

        self.title = SubtitleLabel('Тест скорости', self)
        self.title.setAlignment(Qt.AlignHCenter)

        self.ring = IndeterminateProgressRing(self)
        self.ring.setFixedSize(90, 90)
        self.ring.hide()

        self.valuesRow = QHBoxLayout()
        self.pingLabel = BodyLabel('Ping: — ms', self)
        self.downLabel = BodyLabel('Download: —', self)
        self.upLabel = BodyLabel('Upload: —', self)
        for w in (self.pingLabel, self.downLabel, self.upLabel):
            w.setAlignment(Qt.AlignHCenter)
        self.valuesRow.addWidget(self.pingLabel, 1, Qt.AlignHCenter)
        self.valuesRow.addWidget(self.downLabel, 1, Qt.AlignHCenter)
        self.valuesRow.addWidget(self.upLabel, 1, Qt.AlignHCenter)

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
        self._apply_logs_enabled(bool(self.settings.get('logs_enabled', True)))

        self.vBox.addWidget(self.title)
        self.vBox.addWidget(self.ring, 0, Qt.AlignHCenter)
        self.vBox.addLayout(self.valuesRow)
        self.vBox.addLayout(self.buttonsRow)
        self.vBox.addWidget(self.logView)

        # worker/thread
        self.thread: QThread = None
        self.worker = None  # SpeedtestWorker | PreciseSpeedtestWorker

        # events
        self.startBtn.clicked.connect(self.start_test)
        self.preciseBtn.clicked.connect(self.start_precise_test)
        self.stopBtn.clicked.connect(self.stop_test)

        # connect UI logger emitter
        if emitter is not None:
            emitter.message.connect(self._append_log)

        # подписаться на изменения настроек (переключатель логов)
        self.settings.changed.connect(self._on_setting_changed)

    # ============== logic ==============
    def _info(self, text: str):
        InfoBar.success(title='Инфо', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _warn(self, text: str):
        InfoBar.warning(title='Внимание', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _error(self, text: str):
        InfoBar.error(title='Ошибка', content=text, orient=Qt.Horizontal, position=InfoBarPosition.TOP, parent=self)

    def _append_log(self, line: str):
        # если логи выключены — игнорируем
        if not bool(self.settings.get('logs_enabled', True)):
            return
        self.logView.append(line)

    def _format_speed(self, bps: float) -> str:
        units = self.settings.get('units', 'Mbps')
        if units == 'MB/s':
            return f"{bps / 8e6:.2f} MB/s"
        return f"{bps / 1e6:.2f} Mbps"

    def _apply_logs_enabled(self, enabled: bool):
        self.logView.setVisible(bool(enabled))
        if enabled:
            self.logView.setMinimumHeight(180)
        else:
            self.logView.setMinimumHeight(0)

    def _on_setting_changed(self, key: str, value):
        if key == 'logs_enabled':
            self._apply_logs_enabled(bool(value))

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
        self.pingLabel.setText(f"Ping: {ping:.0f} ms")
        self.downLabel.setText(f"Download: {self._format_speed(d_bps)}")
        self.upLabel.setText(f"Upload: {self._format_speed(u_bps)}")

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
