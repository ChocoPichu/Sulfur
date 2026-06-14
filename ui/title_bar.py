import os
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QToolButton, QFrame,
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QFont, QCursor

import src.modules.configurations as cfg
from ui.settings import open_settings


class TitleBar(QFrame):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self._drag_pos: QPoint | None = None

        self.setFixedHeight(48)
        self.setObjectName("titleBar")
        self.setStyleSheet(f"""
            QFrame#titleBar {{
                background-color: {cfg.BG_SURFACE};
                border-bottom: 1px solid {cfg.BORDER_REST};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setSpacing(8)
        layout.addStretch()

        self.logo = QLabel()
        self.logo.setFixedSize(48, 48)
        self.logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.logo.setScaledContents(True)

        logo_path = os.path.join(
            cfg.RESOURCE_DIR, "ui/images/logo.png"
        )
        if os.path.exists(logo_path):
            pix = QPixmap(logo_path)
            self.logo.setPixmap(pix)
        else:
            self.logo.setText("S")
            self.logo.setFont(
                QFont(cfg.FONT_TITLE, 12, QFont.Weight.Bold)
            )
            self.logo.setStyleSheet(f"color: {cfg.ACCENT};")

        layout.addWidget(
            self.logo, alignment=Qt.AlignmentFlag.AlignCenter
        )

        layout.addStretch(1)

        self.title = QLabel("Sulfur")
        self.title.setFont(
            QFont(
                cfg.FONT_TITLE[0], 12, QFont.Weight.Bold
            )
        )
        self.title.setStyleSheet(f"color: {cfg.TEXT_PRIMARY};")
        layout.addWidget(self.title)

        app.ctx_usage_label = QLabel("Context: 0/0")
        app.ctx_usage_label.setFont(
            QFont(cfg.FONT_SUBTITLE[0], 10)
        )
        app.ctx_usage_label.setStyleSheet(
            f"color: {cfg.TEXT_MUTED};"
        )
        layout.addWidget(app.ctx_usage_label)

        layout.addStretch(1)

        app.settings_btn = QToolButton()
        app.settings_btn.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        app.settings_btn.setFixedSize(28, 28)
        app.settings_btn.setStyleSheet(f"""
            QToolButton {{
                background: transparent;
                border: none;
                color: {cfg.TEXT_SECONDARY};
                border-radius: 6px;
            }}
            QToolButton:hover {{
                background: {cfg.BG_ACTIVE};
            }}
        """)
        settings_icon = os.path.join(
            cfg.RESOURCE_DIR, "ui/images/settings.png"
        )
        if os.path.exists(settings_icon):
            app.settings_btn.setIcon(QIcon(settings_icon))
            app.settings_btn.setIconSize(
                app.settings_btn.size()
            )
        else:
            app.settings_btn.setText("\u2699")
            app.settings_btn.setFont(QFont("Segoe UI", 14))
        app.settings_btn.clicked.connect(
            lambda: open_settings(app)
        )
        layout.addWidget(app.settings_btn)

        self.min_btn = _win_btn(
            "\u2013", cfg, hover_bg=cfg.BG_ACTIVE
        )
        self.min_btn.clicked.connect(app.showMinimized)
        layout.addWidget(self.min_btn)

        self.max_btn = _win_btn(
            "\u25a1", cfg, hover_bg=cfg.BG_ACTIVE
        )
        self.max_btn.clicked.connect(
            self._toggle_max_restore
        )
        layout.addWidget(self.max_btn)

        self.close_btn = _win_btn(
            "\u2715", cfg, hover_bg=cfg.TAG_REMOVE
        )
        self.close_btn.clicked.connect(app.close)
        layout.addWidget(self.close_btn)

    def _toggle_max_restore(self):
        if self.app.isMaximized():
            self.app.showNormal()
        else:
            self.app.showMaximized()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = (
                event.globalPosition().toPoint()
            )
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self._drag_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            delta = (
                event.globalPosition().toPoint()
                - self._drag_pos
            )
            self.app.move(self.app.pos() + delta)
            self._drag_pos = (
                event.globalPosition().toPoint()
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_max_restore()
        super().mouseDoubleClickEvent(event)


def _win_btn(
    text: str, cfg_mod, hover_bg: str
) -> QToolButton:
    btn = QToolButton()
    btn.setText(text)
    btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    btn.setFixedSize(34, 28)
    btn.setFont(
        QFont("Segoe UI", 10, QFont.Weight.Bold)
    )
    btn.setStyleSheet(f"""
        QToolButton {{
            background: transparent;
            border: none;
            color: {cfg_mod.TEXT_PRIMARY};
            border-radius: 6px;
        }}
        QToolButton:hover {{
            background: {hover_bg};
        }}
    """)
    return btn


def build_title_bar(app):
    app.title_bar = TitleBar(app)
    try:
        app.root_layout.insertWidget(
            0, app.title_bar, stretch=0
        )
    except Exception:
        app.root_layout.addWidget(
            app.title_bar, stretch=0
        )
