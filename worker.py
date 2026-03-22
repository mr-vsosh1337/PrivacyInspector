import os
import traceback
from dataclasses import dataclass
from typing import Set

from PySide6.QtCore import QThread, Signal

from core.analyzer import SUPPORTED_EXTS, build_analyzer
from core.handlers import (
    make_out_path,
    redact_docx,
    redact_pdf,
    redact_txt,
    redact_xlsx,
)
from core.scan import scan_file


@dataclass
class JobConfig:
    out_dir: str
    token: str
    overwrite: bool
    excluded_texts: Set[str]


class SingleFileScanWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    result = Signal(object)
    done = Signal(bool, str)

    def __init__(self, file_path: str):
        super().__init__()
        self.file_path = file_path

    def run(self):
        try:
            self.progress.emit(0)
            ext = os.path.splitext(self.file_path)[1].lower()
            if ext not in SUPPORTED_EXTS:
                self.done.emit(False, f"Неподдерживаемый тип файла: {ext}")
                return

            self.log.emit("Инициализация анализатора...")
            analyzer = build_analyzer()
            self.log.emit("Анализатор готов.")
            self.progress.emit(30)

            self.log.emit(f"Анализ файла: {self.file_path}")
            findings = scan_file(analyzer, self.file_path)
            self.progress.emit(100)

            self.result.emit(findings)
            self.done.emit(
                True,
                f"Анализ завершен. Найдено элементов: {len(findings)}",
            )

        except Exception as error:
            self.log.emit("ОШИБКА:\n" + traceback.format_exc())
            self.done.emit(False, str(error))


class SingleFileRedactWorker(QThread):
    progress = Signal(int)
    log = Signal(str)
    done = Signal(bool, str)

    def __init__(self, file_path: str, cfg: JobConfig):
        super().__init__()
        self.file_path = file_path
        self.cfg = cfg

    def run(self):
        try:
            self.progress.emit(0)

            ext = os.path.splitext(self.file_path)[1].lower()
            if ext not in SUPPORTED_EXTS:
                self.done.emit(False, f"Неподдерживаемый тип файла: {ext}")
                return

            os.makedirs(self.cfg.out_dir, exist_ok=True)
            out_path = make_out_path(self.file_path, self.cfg.out_dir)

            if os.path.exists(out_path) and not self.cfg.overwrite:
                self.done.emit(
                    False,
                    f"Выходной файл уже существует "
                    f"(включите перезапись): {out_path}",
                )
                return

            self.log.emit("Инициализация анализатора...")
            analyzer = build_analyzer()
            self.log.emit("Анализатор готов.")
            self.progress.emit(25)

            self.log.emit(f"Обезличивание файла: {self.file_path}")
            if ext == ".txt":
                redact_txt(
                    self.file_path,
                    out_path,
                    analyzer,
                    self.cfg.token,
                    self.cfg.excluded_texts,
                )
            elif ext == ".docx":
                redact_docx(
                    self.file_path,
                    out_path,
                    analyzer,
                    self.cfg.token,
                    self.cfg.excluded_texts,
                )
            elif ext == ".xlsx":
                redact_xlsx(
                    self.file_path,
                    out_path,
                    analyzer,
                    self.cfg.token,
                    self.cfg.excluded_texts,
                )
            elif ext == ".pdf":
                redact_pdf(
                    self.file_path,
                    out_path,
                    analyzer,
                    self.cfg.excluded_texts,
                )

            self.progress.emit(100)
            self.done.emit(True, f"Сохранено: {out_path}")

        except Exception as error:
            self.log.emit("ОШИБКА:\n" + traceback.format_exc())
            self.done.emit(False, str(error))
