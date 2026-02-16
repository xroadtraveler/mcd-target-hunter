"""
MCD Target Hunter - GUI Frontend

Purpose:
    Provide a Windows-based graphical interface for scanning CNC/MCD output files
    to locate target strings (e.g. 'POST-GENERATED') and report their contextual
    parents such as operation names, operation numbers, and tool changes.

Input(s):
    - Variations of .txt file ('.nc', '.V11', etc)

Output(s):
    - CSV file

Key Features:
    - User-configurable Target and Parent search strings
    - File picker for CNC/MCD output files (extension-agnostic)
    - Config persistence across runs (per-user/-machine)
    - CSV report generation with one row per hit
    - Optional quick-open of generated reports

Design Notes:
    - Built with PyQt6
    - Backend scanning logic lives in mcd_hunter_core.py
    - GUI is intentionally thin; logic belongs in the backend

Audience:
    Manufacturing engineers, CNC programmers, and CNC troubleshooters working with
    CATIA / MCD-generated NC output

Author:
    Travis Rillos

Status:
    Stable (v1.0.0, initial public release)

Version:
    v1.0.0
"""

from .mcd_hunter_core import __version__

import os
import sys
import ctypes
from ctypes import wintypes

from PyQt6.QtCore import QUrl
from PyQt6.QtGui import QDesktopServices
from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QFileDialog, QHBoxLayout, QVBoxLayout, QMessageBox, QCheckBox
)

from .mcd_hunter_core import (
    APP_NAME,
    AppConfig,
    scan_file_for_hits,
    default_csv_report_path_in_dir,
    write_csv_report,
)


def get_windows_desktop_path() -> str:
    """
    Returns the real Desktop path using Windows Known Folder API.
    Handles OneDrive redirection / corporate folder policies.

    Falls back to %USERPROFILE%\\Desktop if the API fails.
    """
    # FOLDERID_Desktop GUID: {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", wintypes.BYTE * 8),
        ]

    FOLDERID_Desktop = GUID(
        0xB4BFCC3A,
        0xDB2C,
        0x424C,
        (wintypes.BYTE * 8)(0xB0, 0x29, 0x7F, 0xE9, 0x9A, 0x87, 0xC6, 0x41),
    )

    # SHGetKnownFolderPath signature:
    # HRESULT SHGetKnownFolderPath(REFKNOWNFOLDERID rfid, DWORD dwFlags, HANDLE hToken, PWSTR *ppszPath);
    SHGetKnownFolderPath = ctypes.windll.shell32.SHGetKnownFolderPath
    SHGetKnownFolderPath.argtypes = [
        ctypes.POINTER(GUID),
        wintypes.DWORD,
        wintypes.HANDLE,
        ctypes.POINTER(ctypes.c_wchar_p),
    ]
    # Don't rely on wintypes.HRESULT (not always present)
    SHGetKnownFolderPath.restype = ctypes.c_long

    path_ptr = ctypes.c_wchar_p()
    hr = SHGetKnownFolderPath(ctypes.byref(FOLDERID_Desktop), 0, None, ctypes.byref(path_ptr))

    if hr == 0 and path_ptr.value:
        desktop = path_ptr.value
        # Free memory allocated by the shell
        ctypes.windll.ole32.CoTaskMemFree(path_ptr)
        return desktop

    # Fallback
    return os.path.join(os.path.expanduser("~"), "Desktop")


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME + " - " + f"v{__version__}")
        self.setMinimumWidth(820)

        self.config = AppConfig.load()

        # Default output folder: real Desktop (handles OneDrive redirection)
        desktop_default = get_windows_desktop_path()
        if not self.config.output_dir_path:
            self.config.output_dir_path = desktop_default

        # Input file
        self.input_file_label = QLabel("Target file (MCD output):")
        self.input_file_box = QLineEdit(self.config.input_file_path)
        self.input_browse_btn = QPushButton("Browse")
        self.input_clear_btn = QPushButton("Clear")
        self.input_clear_btn.setStyleSheet("color: red; font-weight: bold;")

        # Output folder
        self.output_dir_label = QLabel("Output folder (CSV destination):")
        self.output_dir_box = QLineEdit(self.config.output_dir_path)
        self.output_browse_btn = QPushButton("Browse")
        self.output_clear_btn = QPushButton("Clear")
        self.output_clear_btn.setStyleSheet("color: red; font-weight: bold;")

        # Search options
        self.target_label = QLabel("Target (child) search text:")
        self.target_input = QLineEdit(self.config.target_text)

        self.parent_label = QLabel("Parent search text:")
        self.parent_input = QLineEdit(self.config.parent_text)

        self.use_parent_checkbox = QCheckBox("Use Parent lookup")
        self.use_parent_checkbox.setChecked(self.config.use_parent)

        self.opno_label = QLabel("Operation number search text:")
        self.opno_input = QLineEdit(self.config.op_no_text)

        self.toolchg_label = QLabel("Tool change search text:")
        self.toolchg_input = QLineEdit(self.config.tool_change_text)

        self.case_checkbox = QCheckBox("Case sensitive search")
        self.case_checkbox.setChecked(self.config.case_sensitive)

        self.run_button = QPushButton("Run")
        self.cancel_button = QPushButton("Cancel")
        self.about_button = QPushButton("About")

        # Layout
        root = QVBoxLayout()

        root.addWidget(self.input_file_label)
        in_row = QHBoxLayout()
        in_row.addWidget(self.input_file_box, 1)
        in_row.addWidget(self.input_browse_btn)
        in_row.addWidget(self.input_clear_btn)
        root.addLayout(in_row)

        root.addSpacing(10)

        root.addWidget(self.output_dir_label)
        out_row = QHBoxLayout()
        out_row.addWidget(self.output_dir_box, 1)
        out_row.addWidget(self.output_browse_btn)
        out_row.addWidget(self.output_clear_btn)
        root.addLayout(out_row)

        root.addSpacing(15)

        root.addWidget(self.target_label)
        root.addWidget(self.target_input)

        root.addWidget(self.parent_label)
        root.addWidget(self.parent_input)
        root.addWidget(self.use_parent_checkbox)

        root.addWidget(self.opno_label)
        root.addWidget(self.opno_input)

        root.addWidget(self.toolchg_label)
        root.addWidget(self.toolchg_input)

        root.addWidget(self.case_checkbox)

        root.addSpacing(15)

        self.about_button = QPushButton("About")
        btn_row = QHBoxLayout()
        btn_row.addWidget(self.about_button)
        btn_row.addStretch(1)
        btn_row.addWidget(self.run_button)
        btn_row.addWidget(self.cancel_button)
        root.addLayout(btn_row)

        self.setLayout(root)

        # Signals
        self.input_browse_btn.clicked.connect(self.pick_input_file)
        self.input_clear_btn.clicked.connect(lambda: self.input_file_box.setText(""))

        self.output_browse_btn.clicked.connect(self.pick_output_dir)
        self.output_clear_btn.clicked.connect(lambda: self.output_dir_box.setText(""))

        self.use_parent_checkbox.stateChanged.connect(
            lambda: self.parent_input.setEnabled(self.use_parent_checkbox.isChecked())
        )
        self.parent_input.setEnabled(self.use_parent_checkbox.isChecked())

        self.run_button.clicked.connect(self.on_run)
        self.cancel_button.clicked.connect(self.close)

        self.about_button.clicked.connect(self.show_about)

    # Add "About" button and message
    def show_about(self):
        about_text = (
            f"{APP_NAME}\n"
            f"Version: {__version__}\n\n"
            "Purpose:\n"
            "Scan CNC/MCD output files for a target string and report each hit\n"
            "with useful context (operation name/no., tool number, tool change line).\n\n"
            "Output:\n"
            "CSV report (one row per hit)\n\n"
            "Notes:\n"
            "Built for troubleshooting CNC programming workflows."
        )

        QMessageBox.about(self, f"About {APP_NAME}", about_text)

    # Choose input file from lcoation
    def pick_input_file(self):
        start_dir = self.input_file_box.text().strip()

        # If the box is empty or invalid, default to Desktop
        if not start_dir or not os.path.isfile(start_dir):
            start_dir = get_windows_desktop_path()

        path, _ = QFileDialog.getOpenFileName(self, "Select CNC/MCD output file", start_dir, "All Files (*.*)")
        if path:
            self.input_file_box.setText(path)

    # Choose location for output CSV file
    def pick_output_dir(self):
        start_dir = self.output_dir_box.text().strip() or os.path.expanduser("~")
        path = QFileDialog.getExistingDirectory(self, "Select folder", start_dir)
        if path:
            self.output_dir_box.setText(path)

    # Run
    def on_run(self):
        input_path = self.input_file_box.text().strip()
        output_dir = self.output_dir_box.text().strip()

        if not input_path or not os.path.isfile(input_path):
            QMessageBox.warning(self, "Error", "Valid input file required.")
            return

        if not output_dir or not os.path.isdir(output_dir):
            QMessageBox.warning(self, "Error", "Valid output folder required.")
            return

        target_text = self.target_input.text().strip()
        if not target_text:
            QMessageBox.warning(self, "Error", "Target search text cannot be blank.")
            return

        # Save config
        self.config.input_file_path = input_path
        self.config.output_dir_path = output_dir
        self.config.target_text = target_text
        self.config.parent_text = self.parent_input.text().strip()
        self.config.use_parent = self.use_parent_checkbox.isChecked()
        self.config.op_no_text = self.opno_input.text().strip()
        self.config.tool_change_text = self.toolchg_input.text().strip()
        self.config.case_sensitive = self.case_checkbox.isChecked()
        self.config.save()

        # Scan + write report
        try:
            rows, total_hits = scan_file_for_hits(
                input_path,
                self.config.target_text,
                self.config.parent_text,
                self.config.use_parent,
                self.config.op_no_text,
                self.config.tool_change_text,
                self.config.case_sensitive,
            )

            report_path = default_csv_report_path_in_dir(input_path, output_dir)
            write_csv_report(report_path, rows, total_hits)

            msg = QMessageBox(self)
            msg.setWindowTitle("Complete")
            msg.setIcon(QMessageBox.Icon.Information)
            msg.setText("Report created.")
            msg.setInformativeText(f"Report path:\n{report_path}\n\nTotal hits: {total_hits}")

            open_btn = msg.addButton("Open CSV Report", QMessageBox.ButtonRole.ActionRole)
            folder_btn = msg.addButton("Open Output Folder", QMessageBox.ButtonRole.ActionRole)
            msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)

            msg.exec()

            clicked = msg.clickedButton()
            if clicked == open_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(report_path))
            elif clicked == folder_btn:
                QDesktopServices.openUrl(QUrl.fromLocalFile(output_dir))

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Something went wrong:\n\n{e}")


def main():
    app = QApplication(sys.argv)
    w = MainWindow()
    w.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()