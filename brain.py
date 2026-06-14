"""Sulfur entry point. Run this"""

import sys
from PyQt6.QtWidgets import QApplication
from ui.app import App


if sys.platform == 'win32' and hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')


def launch_app():
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    launch_app()
