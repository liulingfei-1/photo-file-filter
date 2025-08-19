#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# pyright: reportMissingImports=false

import sys
import os
import io
from typing import TextIO, cast
from contextlib import redirect_stdout, redirect_stderr

from PySide6.QtCore import QObject, QThread, Signal, Slot, Qt
from PySide6.QtGui import QTextCursor, QPalette, QColor
from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QFileDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QLabel,
    QTextEdit,
    QMessageBox,
    QProgressBar,
    QCheckBox,
    QStyleFactory,
)

from file_filter import process_files


class StreamProxy(io.TextIOBase):
    """A minimal text stream that forwards writes to a callback."""

    def __init__(self, callback):
        super().__init__()
        self._callback = callback

    def writable(self):
        return True

    def write(self, message: str):
        if message:
            self._callback(message)
        return len(message)

    def flush(self):
        return None


class Worker(QObject):
    log = Signal(str)
    finished = Signal()
    error = Signal(str)
    progress = Signal(int, int, int, str)  # processed, total, matched, current_filename

    def __init__(self, source_folder: str, target_folder: str, reference_file: str, cancel_flag_getter=None):
        super().__init__()
        self.source_folder = source_folder
        self.target_folder = target_folder
        self.reference_file = reference_file
        self._cancel_flag_getter = cancel_flag_getter or (lambda: False)

    @Slot()
    def run(self):
        try:
            stdout_proxy: io.TextIOBase = StreamProxy(lambda m: self.log.emit(m))
            stderr_proxy: io.TextIOBase = StreamProxy(lambda m: self.log.emit(m))
            def _progress_cb(processed, total, matched, current):
                try:
                    name = str(current) if current is not None else ""
                except Exception:
                    name = ""
                self.progress.emit(int(processed), int(total), int(matched), name)

            with redirect_stdout(cast(TextIO, stdout_proxy)), redirect_stderr(cast(TextIO, stderr_proxy)):
                process_files(
                    self.source_folder,
                    self.target_folder,
                    self.reference_file,
                    progress_callback=_progress_cb,
                    is_cancelled=self._cancel_flag_getter,
                )
        except Exception as exc:  # noqa: BLE001
            self.error.emit(str(exc))
        finally:
            self.finished.emit()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("照片筛选与重命名工具 (GUI)")
        self._build_ui()
        self._worker_thread = None

    def _build_ui(self):
        container = QWidget()
        layout = QVBoxLayout()

        # Source folder
        self.source_edit = QLineEdit()
        self.source_edit.setPlaceholderText("选择源文件夹，包含待筛选的照片")
        source_btn = QPushButton("浏览…")
        source_btn.clicked.connect(self._choose_source)
        row1 = QHBoxLayout()
        row1.addWidget(QLabel("源文件夹"))
        row1.addWidget(self.source_edit)
        row1.addWidget(source_btn)
        layout.addLayout(row1)

        # Target folder
        self.target_edit = QLineEdit()
        self.target_edit.setPlaceholderText("选择输出文件夹，结果会复制到此处")
        target_btn = QPushButton("浏览…")
        target_btn.clicked.connect(self._choose_target)
        row2 = QHBoxLayout()
        row2.addWidget(QLabel("目标文件夹"))
        row2.addWidget(self.target_edit)
        row2.addWidget(target_btn)
        layout.addLayout(row2)

        # Reference file
        self.reference_edit = QLineEdit()
        self.reference_edit.setPlaceholderText("选择参考表 (CSV / Excel)")
        reference_btn = QPushButton("浏览…")
        reference_btn.clicked.connect(self._choose_reference)
        row3 = QHBoxLayout()
        row3.addWidget(QLabel("参考表"))
        row3.addWidget(self.reference_edit)
        row3.addWidget(reference_btn)
        layout.addLayout(row3)

        # Run and control buttons
        self.run_btn = QPushButton("开始处理")
        self.run_btn.clicked.connect(self._on_run)
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.run_btn)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self.cancel_btn)
        self.clear_btn = QPushButton("清空日志")
        self.clear_btn.clicked.connect(lambda: self.log_view.clear())
        btn_row.addWidget(self.clear_btn)
        self.open_btn = QPushButton("打开输出目录")
        self.open_btn.clicked.connect(self._open_target_dir)
        btn_row.addWidget(self.open_btn)
        layout.addLayout(btn_row)

        # Log output
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        layout.addWidget(QLabel("输出日志："))
        layout.addWidget(self.log_view, stretch=1)

        # Progress bar and status
        progress_row = QHBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.status_label = QLabel("")
        self.status_label.setMinimumWidth(240)
        progress_row.addWidget(QLabel("进度"))
        progress_row.addWidget(self.progress_bar, stretch=1)
        progress_row.addWidget(self.status_label)
        layout.addLayout(progress_row)

        # Theme toggle
        theme_row = QHBoxLayout()
        self.dark_mode = QCheckBox("暗色主题")
        self.dark_mode.stateChanged.connect(self._toggle_theme)
        theme_row.addWidget(self.dark_mode)
        layout.addLayout(theme_row)

        container.setLayout(layout)
        self.setCentralWidget(container)
        self.resize(820, 520)

    def _choose_source(self):
        path = QFileDialog.getExistingDirectory(self, "选择源文件夹")
        if path:
            self.source_edit.setText(path)

    def _choose_target(self):
        path = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if path:
            self.target_edit.setText(path)

    def _choose_reference(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择参考表 (CSV / Excel)",
            os.getcwd(),
            "表格文件 (*.csv *.xlsx *.xls);;CSV (*.csv);;Excel (*.xlsx *.xls)"
        )
        if file_path:
            self.reference_edit.setText(file_path)

    def _append_log(self, message: str):
        # 统一换行，避免多次空白刷新
        if not message:
            return
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)
        self.log_view.insertPlainText(message)
        self.log_view.ensureCursorVisible()

    def _set_running(self, running: bool):
        self.run_btn.setEnabled(not running)
        self.source_edit.setEnabled(not running)
        self.target_edit.setEnabled(not running)
        self.reference_edit.setEnabled(not running)
        if hasattr(self, 'cancel_btn'):
            self.cancel_btn.setEnabled(running)
        if not running and hasattr(self, '_cancelled'):
            self._cancelled = False

    def _validate_inputs(self):
        source = self.source_edit.text().strip()
        target = self.target_edit.text().strip()
        reference = self.reference_edit.text().strip()

        if not source or not os.path.exists(source):
            QMessageBox.warning(self, "提示", "请提供有效的源文件夹路径")
            return None
        if not target:
            QMessageBox.warning(self, "提示", "请提供目标文件夹路径")
            return None
        target_parent = os.path.dirname(target.rstrip(os.sep))
        if target_parent and not os.path.exists(target_parent):
            QMessageBox.warning(self, "提示", f"目标文件夹的父目录不存在: {target_parent}")
            return None
        if not reference or not os.path.exists(reference):
            QMessageBox.warning(self, "提示", "请提供有效的参考表文件路径")
            return None
        return source, target, reference

    def _on_run(self):
        validated = self._validate_inputs()
        if not validated:
            return
        source, target, reference = validated
        self.log_view.clear()
        self._set_running(True)

        self._worker_thread = QThread()
        self._cancelled = False
        self._worker = Worker(source, target, reference, cancel_flag_getter=lambda: self._cancelled)
        self._worker.moveToThread(self._worker_thread)

        self._worker_thread.started.connect(self._worker.run)
        self._worker.log.connect(self._append_log)
        self._worker.error.connect(lambda e: QMessageBox.critical(self, "错误", e))
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)

        # 确保线程结束时释放资源
        self._worker.finished.connect(self._worker_thread.quit)
        self._worker.finished.connect(self._worker.deleteLater)
        self._worker_thread.finished.connect(self._worker_thread.deleteLater)

        self._worker_thread.start()

    def _on_finished(self):
        self._set_running(False)
        self._append_log("\n处理已结束\n")
        self.status_label.setText("完成")

    def _toggle_theme(self):
        if self.dark_mode.isChecked():
            self._apply_dark_theme()
        else:
            self._apply_light_theme()

    def _apply_dark_theme(self):
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
        palette.setColor(QPalette.ColorRole.Base, QColor(20, 20, 20))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 30, 30))
        palette.setColor(QPalette.ColorRole.Text, QColor(230, 230, 230))
        palette.setColor(QPalette.ColorRole.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ColorRole.ButtonText, QColor(230, 230, 230))
        palette.setColor(QPalette.ColorRole.Highlight, QColor(64, 128, 255))
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)

    def _apply_light_theme(self):
        QApplication.setStyle(QStyleFactory.create("Fusion"))
        self.setPalette(self.style().standardPalette())

    def _on_cancel(self):
        self._cancelled = True
        self.status_label.setText("正在取消…")
        self.cancel_btn.setEnabled(False)

    def _open_target_dir(self):
        target = self.target_edit.text().strip()
        if not target:
            return
        if sys.platform == "darwin":
            os.system(f'open "{target}"')
        elif sys.platform.startswith("win"):
            os.system(f'start "" "{target}"')
        else:
            os.system(f'xdg-open "{target}"')

    @Slot(int, int, int, str)
    def _on_progress(self, processed: int, total: int, matched: int, current: str):
        percent = 0 if total == 0 else int(processed * 100 / total)
        self.progress_bar.setValue(percent)
        if current:
            self.status_label.setText(f"{processed}/{total}，已匹配 {matched}：{current}")
        else:
            self.status_label.setText(f"{processed}/{total}，已匹配 {matched}")


def main():
    # macOS 下启用高分屏渲染优化
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()


