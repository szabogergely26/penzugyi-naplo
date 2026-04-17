# pénzügyi_napló/ui/dialogs/log_viewer_dialog.py
# -----------------------------------------------




from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QVBoxLayout,
)

from penzugyi_naplo.core.logging_utils import get_log_file_path
from penzugyi_naplo.core.utils import open_with_default_app


class LogViewerDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Alkalmazásnapló")
        self.resize(900, 600)

        self.log_path = Path(get_log_file_path())

        self.path_label = QLabel()
        self.path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.path_label.setWordWrap(True)

        self.editor = QPlainTextEdit()
        self.editor.setReadOnly(True)
        self.editor.setLineWrapMode(QPlainTextEdit.NoWrap)

        self.refresh_button = QPushButton("Frissítés")
        self.open_button = QPushButton("Log fájl megnyitása")
        self.copy_button = QPushButton("Másolás")
        self.close_button = QPushButton("Bezárás")

        self.refresh_button.clicked.connect(self.load_log)
        self.open_button.clicked.connect(self.open_log_file)
        self.copy_button.clicked.connect(self.copy_all_text)
        self.close_button.clicked.connect(self.accept)

        button_row = QHBoxLayout()
        button_row.addWidget(self.refresh_button)
        button_row.addWidget(self.open_button)
        button_row.addWidget(self.copy_button)
        button_row.addStretch(1)
        button_row.addWidget(self.close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.path_label)
        layout.addWidget(self.editor, 1)
        layout.addLayout(button_row)

        self.load_log()

    def load_log(self) -> None:
        self.path_label.setText(f"Log fájl: {self.log_path}")

        if not self.log_path.exists():
            self.editor.setPlainText("A log fájl még nem jött létre.")
            self.open_button.setEnabled(False)
            self.copy_button.setEnabled(False)
            return

        try:
            text = self.log_path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = self.log_path.read_text(encoding="utf-8", errors="replace")
            except Exception as exc:
                self.editor.setPlainText(f"A log fájl nem olvasható.\n\nHiba:\n{exc}")
                self.open_button.setEnabled(True)
                self.copy_button.setEnabled(False)
                return
        except Exception as exc:
            self.editor.setPlainText(f"A log fájl nem olvasható.\n\nHiba:\n{exc}")
            self.open_button.setEnabled(True)
            self.copy_button.setEnabled(False)
            return

        if not text.strip():
            text = "A log fájl üres."

        self.editor.setPlainText(text)
        self.editor.verticalScrollBar().setValue(
            self.editor.verticalScrollBar().maximum()
        )
        self.open_button.setEnabled(True)
        self.copy_button.setEnabled(True)

    def open_log_file(self) -> None:
        if not self.log_path.exists():
            QMessageBox.information(
                self,
                "Log megnyitása",
                "A log fájl még nem jött létre.",
            )
            return

        try:
            open_with_default_app(str(self.log_path))
        except Exception as exc:
            QMessageBox.warning(
                self,
                "Log megnyitása",
                f"Nem sikerült megnyitni a log fájlt.\n\n{exc}",
            )

    def copy_all_text(self) -> None:
        text = self.editor.toPlainText()
        if not text:
            return

        clipboard = QGuiApplication.clipboard()
        clipboard.setText(text)

        QMessageBox.information(
            self,
            "Másolás",
            "A log tartalma a vágólapra került.",
        )