"""Starts the IDE and explains what to do when JadivCode itself is missing."""

import sys

INSTALL = "curl -fsSL https://raw.githubusercontent.com/JadivCode/jadivcode/main/install.sh | bash"


def launch(argv=None):
    try:
        from .app import main
    except ImportError as exc:
        if "PyQt5" in str(exc):
            print("The JadivCode IDE needs PyQt5. Install it with:\n"
                  "    sudo apt install python3-pyqt5", file=sys.stderr)
            return 1
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
            app = QApplication(sys.argv)  # noqa: F841 - must exist for the dialog
            QMessageBox.critical(
                None, "JadivCode is not installed",
                "The IDE needs the JadivCode interpreter.\n\n"
                f"Install it by running this in a terminal:\n\n{INSTALL}")
        except ImportError:
            pass
        print(f"JadivCode is not installed. Install it with:\n    {INSTALL}", file=sys.stderr)
        return 1
    return main(argv)
