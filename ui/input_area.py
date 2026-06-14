import os
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QComboBox,
    QLabel, QPushButton, QWidget, QCheckBox, QTextEdit,
    QGraphicsDropShadowEffect, QFileDialog, QMenu,
    QToolButton, QDialog, QScrollArea,
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QCursor, QKeyEvent, QColor

import src.modules.configurations as cfg
import src.modules.target_path as target_path
import src.modules.session_manager as session_manager
import src.modules.preferences_manager as prefs_mgr
from src.modules.more_modules.target_path_ops import set_target
from src.modules.preferences_manager import load_prefs


class ExpandingTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Type your message...")
        self.setFont(
            QFont(cfg.FONT_MAIN[0], cfg.FONT_MAIN[1])
        )
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent
                color: {cfg.TEXT_PRIMARY};
                border: none
                padding: 8px 12px;
            }}
            QTextEdit:focus {{
                outline: none;
            }}
        """)
        self.textChanged.connect(self.resize_to_fit)
        self.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.resize_to_fit()

    def resize_to_fit(self):
        doc = self.document()
        if doc is not None:
            doc_height = int(doc.size().height())
            target_height = min(max(40, doc_height + 16), 200)
            self.setFixedHeight(target_height)


def _add_folder(app, folder_path: str):
    if not folder_path:
        return

    skip_dirs = {
        ".git", ".venv", "venv", "__pycache__",
        "node_modules", "dist", "build",
        ".mypy_cache", ".pytest_cache",
    }
    allowed_exts = set(
        cfg.SUPPORTED_LANGUAGES.values()
    ) | {
        ".md", ".txt", ".json", ".csv",
        ".pdf", ".png", ".jpg", ".jpeg", ".webp",
    }

    added = 0
    cap = 200
    for root, dirs, files in os.walk(folder_path):
        dirs[:] = [
            d for d in dirs
            if d not in skip_dirs and not d.startswith(".")
        ]
        for name in files:
            ext = os.path.splitext(name)[1].lower()
            if ext not in allowed_exts:
                continue
            full = os.path.abspath(os.path.join(root, name))
            result = set_target(full)
            if result.get("success"):
                added += 1
                if added >= cap:
                    break
        if added >= cap:
            break

    files_now = target_path.get_workspace_files()
    count = len(files_now)
    if hasattr(app, "target_label"):
        _refresh_workspace_label(app)
    try:
        session_manager.update_active_session(
            workspace_files=files_now
        )
    except Exception:
        pass


def open_attachment_manager(app):
    if (
        hasattr(app, "attachment_window")
        and app.attachment_window is not None
    ):
        try:
            if app.attachment_window.isVisible():
                app.attachment_window.raise_()
                app.attachment_window.activateWindow()
                return
        except RuntimeError:
            pass

    app.attachment_window = QDialog(app)
    app.attachment_window.setWindowTitle(
        "Manage Workspace Files"
    )
    app.attachment_window.resize(450, 300)
    app.attachment_window.setStyleSheet(
        f"background-color: {cfg.BG_BASE};"
    )
    app.attachment_window.setModal(False)
    app.attachment_window.setAttribute(
        Qt.WidgetAttribute.WA_DeleteOnClose
    )

    def on_close():
        app.attachment_window = None

    app.attachment_window.finished.connect(on_close)

    main_layout = QVBoxLayout(app.attachment_window)

    files = target_path.get_workspace_files()

    if not files:
        lbl = QLabel(
            "No files are currently attached."
        )
        lbl.setFont(
            QFont(cfg.FONT_MAIN[0], cfg.FONT_MAIN[1])
        )
        lbl.setStyleSheet(f"color: {cfg.TEXT_PRIMARY};")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(lbl)
        app.attachment_window.show()
        return

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll_content = QWidget()
    scroll_content.setStyleSheet(
        "background: transparent;"
    )
    scroll_layout = QVBoxLayout(scroll_content)
    scroll_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    scroll.setWidget(scroll_content)
    main_layout.addWidget(scroll)

    def remove_file(path_to_remove, row_widget):
        target_path.remove_workspace_file(path_to_remove)
        row_widget.hide()
        row_widget.deleteLater()

        current_files = target_path.get_workspace_files()
        _refresh_workspace_label(app)

        session_manager.update_active_session(
            workspace_files=current_files
        )

        scroll_content.adjustSize()

    for fpath in files:
        row = QFrame()
        row.setStyleSheet(
            f"background-color: {cfg.BG_SURFACE}; "
            "border-radius: 4px;"
        )
        row_layout = QHBoxLayout(row)

        lbl = QLabel(os.path.basename(fpath))
        lbl.setFont(
            QFont(cfg.FONT_MAIN[0], cfg.FONT_MAIN[1])
        )
        lbl.setStyleSheet(f"color: {cfg.TEXT_PRIMARY};")
        row_layout.addWidget(lbl)

        row_layout.addStretch(1)

        btn = QPushButton("Remove")
        btn.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cfg.TAG_REMOVE};
                color: {cfg.TEXT_PRIMARY};
                border: none;
                border-radius: 4px;
                padding: 4px 10px;
            }}
            QPushButton:hover {{
                background-color: #a83232;
            }}
        """)
        btn.clicked.connect(
            lambda checked, p=fpath, r=row: remove_file(p, r)
        )
        row_layout.addWidget(btn)

        scroll_layout.addWidget(row)

    app.attachment_window.show()


def _refresh_workspace_label(app):
    files_now = target_path.get_workspace_files()
    count = len(files_now)
    if not hasattr(app, 'target_label'):
        return
    app.target_label.setText(
        f"{count} files in Workspace"
    )
    if count > 0:
        app.target_label.setStyleSheet(
            f"background: {cfg.SCROLLBAR_BTN}; "
            "border: none; "
            f"color: {cfg.TEXT_PRIMARY}; "
            "border-radius: 6px; "
            "padding: 4px 8px;"
        )
    else:
        app.target_label.setStyleSheet(
            "background: transparent; "
            "border: none; "
            f"color: {cfg.TEXT_MUTED};"
        )


def build_input_area(app):
    app.bottom_frame = QFrame()
    app.bottom_frame.setStyleSheet(f"""
        QFrame {{
            background-color: {cfg.BG_SURFACE};
            border-top: 1px solid {cfg.BORDER_REST};
            border-bottom: none;
            border-left: none;
            border-right: none;
        }}
    """)
    app.bottom_layout = QVBoxLayout(app.bottom_frame)
    app.bottom_layout.setContentsMargins(24, 10, 24, 16)
    app.bottom_layout.setSpacing(5)

    app.right_layout.addWidget(
        app.bottom_frame, stretch=0
    )

    context_widget = QWidget()
    context_widget.setStyleSheet(
        "border: none; background: transparent;"
    )
    context_layout = QHBoxLayout(context_widget)
    context_layout.setContentsMargins(0, 0, 0, 0)
    context_layout.setSpacing(cfg.PAD_SM)

    add_btn = QToolButton()
    add_btn.setText("\uff0b")
    add_btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    add_btn.setFixedSize(30, 30)
    add_btn.setFont(
        QFont(
            cfg.FONT_MAIN[0], 14, QFont.Weight.Bold
        )
    )
    add_btn.setPopupMode(
        QToolButton.ToolButtonPopupMode.InstantPopup
    )
    add_btn.setArrowType(Qt.ArrowType.NoArrow)
    add_btn.setStyleSheet(f"""
        QToolButton {{
            background-color: transparent;
            color: {cfg.TEXT_PRIMARY};
            border: 1px solid {cfg.BORDER_REST};
            border-radius: 15px;
            padding: 0px;
        }}
        QToolButton:hover {{
            background-color: {cfg.BG_ACTIVE};
            border: 1px solid {cfg.BORDER_ACTIVE};
        }}
        QToolButton::menu-indicator {{
            image: none;
            width: 0px;
        }}
    """)

    menu = QMenu(add_btn)
    menu.setStyleSheet(f"""
        QMenu {{
            background-color: {cfg.BG_CARD};
            color: {cfg.TEXT_PRIMARY};
            border: 1px solid {cfg.BORDER_REST};
            border-radius: {cfg.RADIUS_MD}px;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 6px 12px;
            border-radius: {cfg.RADIUS_SM}px;
        }}
        QMenu::item:selected {{
            background-color: {cfg.BG_ACTIVE};
        }}
    """)

    act_add_file = menu.addAction("Add file\u2026")
    act_add_folder = menu.addAction("Add folder\u2026")
    menu.addSeparator()
    act_clear = menu.addAction("Clear workspace")
    app.bottom_frame.setStyleSheet("padding: 1px;")

    def _sync_workspace_ui():
        files_now = target_path.get_workspace_files()
        count = len(files_now)
        app.target_label.setText(
            f"{count} files in Workspace"
        )
        if count > 0:
            app.target_label.setStyleSheet(
                f"background: {cfg.SCROLLBAR_BTN}; "
                "border: none; "
                f"color: {cfg.TEXT_PRIMARY}; "
                "border-radius: 6px; "
                "padding: 4px 8px;"
            )
        else:
            app.target_label.setStyleSheet(
                "background: transparent; "
                "border: none; "
                f"color: {cfg.TEXT_MUTED};"
            )
        session_manager.update_active_session(
            workspace_files=files_now
        )

    def pick_file():
        path, _ = QFileDialog.getOpenFileName(
            app, "Attach file", cfg.BASE_DIR,
            "All files (*.*)",
        )
        if path:
            set_target(path)
            _sync_workspace_ui()

    def pick_folder():
        folder = QFileDialog.getExistingDirectory(
            app, "Attach folder", cfg.BASE_DIR
        )
        if folder:
            _add_folder(app, folder)
            _sync_workspace_ui()

    def clear_workspace():
        set_target(None)
        _sync_workspace_ui()

    act_add_file.triggered.connect(pick_file)
    act_add_folder.triggered.connect(pick_folder)
    act_clear.triggered.connect(clear_workspace)

    add_btn.setMenu(menu)
    context_layout.addWidget(add_btn)

    app.target_label = QPushButton(
        "0 files in Workspace"
    )
    app.target_label.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    app.target_label.setFont(
        QFont(cfg.FONT_SMALL[0], cfg.FONT_SMALL[1])
    )
    app.target_label.setStyleSheet(
        "background: transparent; "
        "border: none; "
        f"color: {cfg.TEXT_MUTED};"
    )
    app.target_label.clicked.connect(
        lambda: open_attachment_manager(app)
    )
    context_layout.addWidget(app.target_label)

    count = len(target_path.get_workspace_files())
    if count > 0:
        app.target_label.setText(
            f"{count} files in Workspace"
        )
        app.target_label.setStyleSheet(
            f"background: {cfg.SCROLLBAR_BTN}; "
            "border: none; "
            f"color: {cfg.TEXT_PRIMARY}; "
            "border-radius: 6px; "
            "padding: 4px 8px;"
        )

    context_layout.addStretch(1)

    app.think_mode_cb = QCheckBox("Think")
    app.think_mode_cb.setFont(
        QFont(cfg.FONT_SMALL[0], cfg.FONT_SMALL[1])
    )
    app.think_mode_cb.setStyleSheet(
        f"color: {cfg.TEXT_SECONDARY}; "
        "margin-right: 10px;"
    )
    context_layout.addWidget(app.think_mode_cb)

    app.model_select = QComboBox()

    _populate_model_list(app)

    app.model_select.setCurrentText(cfg.MODEL_NAME)
    app.model_select.setFont(
        QFont(cfg.FONT_SMALL[0], cfg.FONT_SMALL[1])
    )
    app.model_select.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    app.model_select.setStyleSheet(f"""
        QComboBox {{
            background-color: {cfg.ACCENT_DARK};
            color: white;
            border-radius: 6px;
            padding: 4px 10px;
            border: none;
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background-color: {cfg.BG_CARD};
            color: {cfg.TEXT_PRIMARY};
            selection-background-color: {cfg.ACCENT};
            border: 1px solid {cfg.BORDER_REST};
        }}
    """)
    app.model_select.currentTextChanged.connect(
        on_model_change
    )
    context_layout.addWidget(app.model_select)

    app.tps_label = QLabel("TPS: --")
    app.tps_label.setFont(
        QFont(cfg.FONT_MONO[0], cfg.FONT_MONO[1])
    )
    app.tps_label.setStyleSheet(
        f"color: {cfg.TEXT_MUTED}; margin-left: 5px;"
    )
    context_layout.addWidget(app.tps_label)

    app.bottom_layout.addWidget(context_widget)

    input_widget = QWidget()
    input_widget.setStyleSheet(
        "border: none; background: transparent;"
    )
    input_layout = QHBoxLayout(input_widget)
    input_layout.setContentsMargins(0, 0, 0, 0)
    input_layout.setSpacing(0)
    input_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

    pill = QFrame()
    pill.setObjectName("pillInputFrame")
    pill.setProperty("focused", False)
    pill.setSizePolicy(
        pill.sizePolicy().horizontalPolicy(),
        pill.sizePolicy().verticalPolicy(),
    )
    pill.setStyleSheet(f"""
        QFrame#pillInputFrame {{
            background-color: {cfg.BG_SURFACE};
            border: 1px solid {cfg.BORDER_REST};
            border-radius: 20px;
        }}
        QFrame#pillInputFrame[focused="true"] {{
            border: 1px solid {cfg.BORDER_ACTIVE};
        }}
    """)

    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(18)
    shadow.setOffset(0, 6)
    shadow.setColor(QColor(0, 0, 0, 90))
    pill.setGraphicsEffect(shadow)

    pill_layout = QHBoxLayout(pill)
    pill_layout.setContentsMargins(10, 6, 6, 6)
    pill_layout.setSpacing(6)
    pill_layout.setAlignment(Qt.AlignmentFlag.AlignBottom)

    app.message_input = ExpandingTextEdit(pill)
    pill_layout.addWidget(app.message_input, stretch=1)

    app.send_btn = QPushButton("\u27a4")
    app.send_btn.setFixedSize(40, 40)
    app.send_btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    app.send_btn.setFont(
        QFont(cfg.FONT_MAIN[0], 18)
    )
    app.send_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {cfg.ACCENT};
            color: {cfg.TEXT_PRIMARY};
            border: none;
            border-radius: 14px;
        }}
        QPushButton:hover {{
            background-color: {cfg.ACCENT_DARK};
        }}
    """)
    app.send_btn.clicked.connect(app.on_send)
    pill_layout.addWidget(app.send_btn)

    input_layout.addWidget(pill, stretch=1)

    app.bottom_layout.addWidget(input_widget)


def on_model_change(choice: str):
    cfg.set_model_name(choice)
    if (
        cfg.BACKEND_TYPE != "llama_cpp"
        and choice
        and choice not in cfg.AVAILABLE_MODELS
    ):
        current = (
            dict(cfg.CUSTOM_MODELS)
            if cfg.CUSTOM_MODELS
            else {}
        )
        if choice not in current:
            current[choice] = {"model_id": choice}
            cfg.CUSTOM_MODELS = current
            prefs_mgr.update_pref(
                "CUSTOM_MODELS", current
            )


def _populate_model_list(app):
    prefs = load_prefs()

    app.model_select.clear()

    if cfg.BACKEND_TYPE == "llama_cpp":
        for name in cfg.AVAILABLE_MODELS:
            app.model_select.addItem(name)
    else:
        from src.modules.backend import get_active_backend

        backend = get_active_backend()
        if backend and backend.is_healthy():
            try:
                remote = backend.list_models()
                for m in remote:
                    app.model_select.addItem(m)
            except Exception:
                pass
        for name in cfg.CUSTOM_MODELS:
            items = [
                app.model_select.itemText(i)
                for i in range(app.model_select.count())
            ]
            if name not in items:
                app.model_select.addItem(name)

        provider_urls = prefs.get("provider", {})
        saved_model = (
            provider_urls.get(cfg.BACKEND_TYPE, {})
            .get("model", "")
        )
        items = [
            app.model_select.itemText(i)
            for i in range(app.model_select.count())
        ]
        if (
            saved_model
            and saved_model not in items
        ):
            app.model_select.addItem(saved_model)

    if cfg.MODEL_NAME and cfg.MODEL_NAME != "None":
        items = [
            app.model_select.itemText(i)
            for i in range(app.model_select.count())
        ]
        if cfg.MODEL_NAME not in items and items:
            cfg.set_model_name(items[0])
            app.model_select.setCurrentText(items[0])
        else:
            app.model_select.setCurrentText(
                cfg.MODEL_NAME
            )

    if (
        cfg.BACKEND_TYPE != "llama_cpp"
        and app.model_select.count() == 0
    ):
        app.model_select.setPlaceholderText(
            "No models detected"
        )


def refresh_model_selector(app):
    _populate_model_list(app)
