import os
from typing import Any, List, Set

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config import REDACTION_TOKEN
from worker import JobConfig, SingleFileRedactWorker, SingleFileScanWorker


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("PrivacyInspector")
        self.setMinimumSize(980, 680)

        self.file_path: str | None = None
        self.scan_worker: SingleFileScanWorker | None = None
        self.redact_worker: SingleFileRedactWorker | None = None

        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(10)

        header = QFrame()
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(2)

        self.title = QLabel("PrivacyInspector")
        self.title.setStyleSheet("font-size: 20px; font-weight: 700;")

        header_layout.addWidget(self.title)
        root_layout.addWidget(header)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, 1)

        self.page_upload = self._build_upload_page()
        self.page_select = self._build_select_page()
        self.page_done = self._build_done_page()

        self.stack.addWidget(self.page_upload)
        self.stack.addWidget(self.page_select)
        self.stack.addWidget(self.page_done)
        self.stack.setCurrentIndex(0)

        bottom = QFrame()
        bottom.setFrameShape(QFrame.StyledPanel)
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(10, 10, 10, 10)
        bottom_layout.setSpacing(8)

        status_row = QHBoxLayout()
        self.status_label = QLabel("Готово.")
        self.status_label.setStyleSheet("color: #444; font-weight: 600;")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)

        status_row.addWidget(self.status_label, 1)
        status_row.addWidget(self.progress, 2)
        bottom_layout.addLayout(status_row)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        self.log.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bottom_layout.addWidget(self.log)

        root_layout.addWidget(bottom)

        self.btn_upload.clicked.connect(self.on_upload)
        self.btn_out.clicked.connect(self.on_pick_outdir)
        self.btn_all.clicked.connect(self.on_remove_all)
        self.btn_none.clicked.connect(self.on_remove_none)
        self.btn_confirm.clicked.connect(self.on_confirm)
        self.btn_new.clicked.connect(self.on_new_file)

    def _build_upload_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        box = QGroupBox("Шаг 1 - Загрузите один файл")
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(10)

        self.btn_upload = QPushButton("Загрузить файл...")
        self.btn_upload.setStyleSheet(
            "font-size: 14px; font-weight: 600; padding: 10px 14px;"
        )
        box_layout.addWidget(self.btn_upload)

        self.file_label = QLabel("Файл не выбран.")
        self.file_label.setStyleSheet("color: #444;")
        box_layout.addWidget(self.file_label)

        out_row = QHBoxLayout()
        self.out_dir = QLineEdit(os.path.join(os.getcwd(), "redacted_out"))
        self.out_dir.setPlaceholderText(
            "Папка вывода (по умолчанию: redacted_out)"
        )
        self.btn_out = QPushButton("Обзор...")
        out_row.addWidget(QLabel("Вывод:"))
        out_row.addWidget(self.out_dir, 1)
        out_row.addWidget(self.btn_out)
        box_layout.addLayout(out_row)

        layout.addWidget(box)
        layout.addStretch(1)
        return widget

    def _build_select_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        box = QGroupBox("Шаг 2 - Выберите, что удалить")
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(8)

        hint = QLabel(
            "Снимите флажки с элементов, которые нужно СОХРАНИТЬ. "
            "Отмеченные элементы будут удалены."
        )
        hint.setStyleSheet("color: #444;")
        box_layout.addWidget(hint)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Удалить", "Тип", "Текст", "Количество", "Оценка"]
        )
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(
            3, QHeaderView.ResizeToContents
        )
        self.table.horizontalHeader().setSectionResizeMode(
            4, QHeaderView.ResizeToContents
        )
        self.table.setWordWrap(True)
        self.table.setSortingEnabled(False)
        box_layout.addWidget(self.table)

        buttons = QHBoxLayout()
        self.btn_all = QPushButton("Удалить все")
        self.btn_none = QPushButton("Не удалять")
        self.btn_confirm = QPushButton("Подтвердить и сохранить")
        self.btn_confirm.setStyleSheet(
            "font-size: 14px; font-weight: 700; padding: 10px 14px;"
        )
        buttons.addWidget(self.btn_all)
        buttons.addWidget(self.btn_none)
        buttons.addStretch(1)
        buttons.addWidget(self.btn_confirm)
        box_layout.addLayout(buttons)

        layout.addWidget(box)
        return widget

    def _build_done_page(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setSpacing(12)

        box = QGroupBox("Готово")
        box_layout = QVBoxLayout(box)
        box_layout.setSpacing(10)

        self.done_label = QLabel("")
        self.done_label.setStyleSheet("font-size: 14px; font-weight: 700;")
        box_layout.addWidget(self.done_label)

        self.btn_new = QPushButton("Обезличить другой файл")
        box_layout.addWidget(self.btn_new)

        layout.addWidget(box)
        layout.addStretch(1)
        return widget

    def append_log(self, msg: str):
        scrollbar = self.log.verticalScrollBar()
        at_bottom = scrollbar.value() >= scrollbar.maximum() - 2

        self.log.appendPlainText(msg)

        if at_bottom:
            scrollbar.setValue(scrollbar.maximum())

    def set_status(self, msg: str):
        self.status_label.setText(msg)
        self.append_log(msg)

    def set_busy(self, busy: bool):
        self.btn_upload.setEnabled(not busy)
        self.btn_out.setEnabled(not busy)
        self.out_dir.setEnabled(not busy)
        self.btn_all.setEnabled(not busy)
        self.btn_none.setEnabled(not busy)
        self.btn_confirm.setEnabled(not busy)
        self.btn_new.setEnabled(not busy)

    def on_pick_outdir(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения",
            self.out_dir.text() or os.getcwd(),
        )
        if directory:
            self.out_dir.setText(directory)

    def on_upload(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите один файл",
            os.getcwd(),
            "Документы (*.txt *.docx *.xlsx *.pdf);;Все файлы (*.*)",
        )
        if not file_path:
            return

        self.file_path = file_path
        self.file_label.setText(f"Выбран файл: {file_path}")

        self.progress.setValue(0)
        self.log.clear()
        self.set_status("Начинается анализ...")
        self.set_busy(True)

        self.scan_worker = SingleFileScanWorker(file_path)
        self.scan_worker.log.connect(self.append_log)
        self.scan_worker.progress.connect(self.progress.setValue)
        self.scan_worker.result.connect(self.on_scan_result)
        self.scan_worker.done.connect(self.on_scan_done)
        self.scan_worker.start()

    def on_scan_result(self, findings: List[Any]):
        self.table.setRowCount(0)
        self.table.setRowCount(len(findings))

        for row_index, finding in enumerate(findings):
            remove_item = QTableWidgetItem()
            remove_item.setFlags(remove_item.flags() | Qt.ItemIsUserCheckable)
            remove_item.setCheckState(Qt.Checked)

            type_item = QTableWidgetItem(str(finding.entity_type))
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)

            text_item = QTableWidgetItem(str(finding.text))
            text_item.setFlags(text_item.flags() & ~Qt.ItemIsEditable)

            count_item = QTableWidgetItem(str(finding.count))
            count_item.setTextAlignment(Qt.AlignCenter)
            count_item.setFlags(count_item.flags() & ~Qt.ItemIsEditable)

            score_item = QTableWidgetItem(f"{float(finding.max_score):.2f}")
            score_item.setTextAlignment(Qt.AlignCenter)
            score_item.setFlags(score_item.flags() & ~Qt.ItemIsEditable)

            self.table.setItem(row_index, 0, remove_item)
            self.table.setItem(row_index, 1, type_item)
            self.table.setItem(row_index, 2, text_item)
            self.table.setItem(row_index, 3, count_item)
            self.table.setItem(row_index, 4, score_item)

        self.stack.setCurrentIndex(1)

    def on_scan_done(self, ok: bool, msg: str):
        self.set_busy(False)
        if not ok:
            QMessageBox.critical(self, "Ошибка анализа", msg)
            self.set_status("Анализ не выполнен. Попробуйте выбрать другой файл.")
            self.stack.setCurrentIndex(0)
            return

        self.set_status(msg)

    def on_remove_all(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Checked)

    def on_remove_none(self):
        for row in range(self.table.rowCount()):
            item = self.table.item(row, 0)
            if item:
                item.setCheckState(Qt.Unchecked)

    def collect_exclusions(self) -> Set[str]:
        excluded: Set[str] = set()
        for row in range(self.table.rowCount()):
            remove_item = self.table.item(row, 0)
            text_item = self.table.item(row, 2)
            if not remove_item or not text_item:
                continue

            if remove_item.checkState() != Qt.Checked:
                excluded.add(text_item.text())
        return excluded

    def on_confirm(self):
        if not self.file_path:
            QMessageBox.warning(self, "Файл не выбран", "Сначала выберите файл.")
            self.stack.setCurrentIndex(0)
            return

        out_dir = self.out_dir.text().strip() or os.path.join(
            os.getcwd(), "redacted_out"
        )
        excluded = self.collect_exclusions()

        cfg = JobConfig(
            out_dir=out_dir,
            token=REDACTION_TOKEN,
            overwrite=True,
            excluded_texts=excluded,
        )

        self.progress.setValue(0)
        self.set_status("Начинается обезличивание...")
        self.append_log(f"Сохранено без изменений: {len(excluded)} элемент(ов).")
        self.set_busy(True)

        self.redact_worker = SingleFileRedactWorker(self.file_path, cfg)
        self.redact_worker.log.connect(self.append_log)
        self.redact_worker.progress.connect(self.progress.setValue)
        self.redact_worker.done.connect(self.on_redact_done)
        self.redact_worker.start()

    def on_redact_done(self, ok: bool, msg: str):
        self.set_busy(False)

        if not ok:
            QMessageBox.critical(self, "Ошибка", msg)
            self.set_status(
                "Не удалось выполнить обезличивание. "
                "Измените выбор и попробуйте снова."
            )
            self.stack.setCurrentIndex(1)
            return

        self.set_status(msg)
        self.done_label.setText(msg)
        self.stack.setCurrentIndex(2)
        QMessageBox.information(self, "Готово", msg)

    def on_new_file(self):
        self.file_path = None
        self.file_label.setText("Файл не выбран.")
        self.table.setRowCount(0)
        self.progress.setValue(0)
        self.log.clear()
        self.status_label.setText("Готово.")
        self.stack.setCurrentIndex(0)
