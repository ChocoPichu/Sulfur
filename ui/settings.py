import sys
import os
from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStackedWidget, QWidget, QSlider,
    QCheckBox, QButtonGroup, QSizePolicy, QMessageBox,
    QLineEdit, QLayout, QScrollArea, QFileDialog,
    QDialog, QApplication, QTextEdit,
)
from PyQt6.QtCore import Qt, QRect, QPoint, QSize, QTimer
from PyQt6.QtGui import QFont, QCursor

import src.modules.configurations as cfg
import src.modules.session_manager as session_manager
import src.modules.preferences_manager as prefs_mgr


class FlowLayout(QLayout):
    def __init__(
        self, parent=None, h_gap: int = 6, v_gap: int = 6
    ):
        super().__init__(parent)
        self._items: list = []
        self._h_gap = h_gap
        self._v_gap = v_gap

    def addItem(self, item):
        self._items.append(item)

    def count(self) -> int:
        return len(self._items)

    def itemAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index: int):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self) -> bool:
        return True

    def heightForWidth(self, width: int) -> int:
        return self._arrange(
            QRect(0, 0, width, 0), dry_run=True
        )

    def setGeometry(self, rect: QRect):
        super().setGeometry(rect)
        self._arrange(rect, dry_run=False)

    def sizeHint(self) -> QSize:
        return self.minimumSize()

    def minimumSize(self) -> QSize:
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        m = self.contentsMargins()
        return size + QSize(
            m.left() + m.right(), m.top() + m.bottom()
        )

    def _arrange(self, rect: QRect, dry_run: bool) -> int:
        m = self.contentsMargins()
        x0 = rect.x() + m.left()
        right_lim = rect.right() - m.right()
        x, y, row_h = x0, rect.y() + m.top(), 0

        for item in self._items:
            hint = item.sizeHint()
            w, h = hint.width(), hint.height()
            if x + w > right_lim and row_h > 0:
                x = x0
                y += row_h + self._v_gap
                row_h = 0
            if not dry_run:
                item.setGeometry(
                    QRect(QPoint(x, y), hint)
                )
            x += w + self._h_gap
            row_h = max(row_h, h)

        return y + row_h - rect.y() + m.bottom()


def _section_card(
    parent_layout, title: str, subtitle: str = None
):
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{
            background-color: {cfg.BG_CARD};
            border-radius: 8px;
            border: 1px solid {cfg.BORDER_REST};
        }}
    """)
    inner = QVBoxLayout(card)
    inner.setContentsMargins(
        cfg.PAD_MD, cfg.PAD_MD,
        cfg.PAD_MD, cfg.PAD_MD,
    )
    inner.setSpacing(6)

    title_lbl = QLabel(title)
    title_lbl.setFont(
        QFont(
            cfg.FONT_TITLE[0], cfg.FONT_TITLE[1],
            QFont.Weight.Bold,
        )
    )
    title_lbl.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    inner.addWidget(title_lbl)

    if subtitle:
        sub = QLabel(subtitle)
        sub.setFont(
            QFont(
                cfg.FONT_MAIN[0], cfg.FONT_MAIN[1]
            )
        )
        sub.setStyleSheet(
            f"color: {cfg.TEXT_MUTED}; "
            "background: transparent; border: none;"
        )
        sub.setWordWrap(True)
        inner.addWidget(sub)

    parent_layout.addWidget(card)
    return inner


def _make_scrollable_page(
    stack: QStackedWidget,
) -> QWidget:
    outer = QFrame()
    outer.setStyleSheet(
        f"QFrame {{ "
        f"background-color: {cfg.BG_SURFACE}; "
        "border-radius: 12px; }"
    )
    outer_layout = QVBoxLayout(outer)
    outer_layout.setContentsMargins(0, 0, 0, 0)
    outer_layout.setSpacing(0)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )
    scroll.setVerticalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAsNeeded
    )
    scroll.setStyleSheet(f"""
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollBar:vertical {{
            background: transparent;
            width: 6px;
            margin: 6px 2px;
        }}
        QScrollBar::handle:vertical {{
            background: {cfg.BORDER_REST};
            border-radius: 3px;
            min-height: 24px;
        }}
        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0;
        }}
    """)
    scroll.viewport().setStyleSheet(
        f"background-color: {cfg.BG_SURFACE};"
    )

    page = QWidget()
    page.setStyleSheet(
        f"background-color: {cfg.BG_SURFACE};"
    )
    page_layout = QVBoxLayout(page)
    page_layout.setContentsMargins(
        cfg.PAD_LG, cfg.PAD_LG,
        cfg.PAD_LG, cfg.PAD_LG,
    )
    page_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
    page_layout.setSpacing(cfg.PAD_MD)

    scroll.setWidget(page)
    outer_layout.addWidget(scroll)
    stack.addWidget(outer)
    return page


class SettingsDialog(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("Sulfur Settings")
        self.setMinimumSize(600, 500)
        self.resize(680, 600)
        self.setStyleSheet(
            f"background-color: {cfg.BG_BASE};"
        )
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowTitleHint
        )

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(
            cfg.PAD_LG, cfg.PAD_LG,
            cfg.PAD_LG, cfg.PAD_LG,
        )
        main_layout.setSpacing(cfg.PAD_MD)

        header_frame = QFrame()
        header_frame.setStyleSheet(
            "background: transparent;"
        )
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(0, 0, 0, 0)

        title_lbl = QLabel("Settings")
        title_lbl.setFont(
            QFont(
                cfg.FONT_TITLE[0], cfg.FONT_TITLE[1],
                QFont.Weight.Bold,
            )
        )
        title_lbl.setStyleSheet(
            f"color: {cfg.TEXT_PRIMARY};"
        )
        header_layout.addWidget(title_lbl)

        self._nav_widget = QWidget()
        nav_layout = QHBoxLayout(self._nav_widget)
        nav_layout.setContentsMargins(40, 0, 0, 0)
        nav_layout.setSpacing(0)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        self._nav_buttons = {}

        tabs = [
            "General", "Model", "Advanced", "Permissions"
        ]
        for i, tab_name in enumerate(tabs):
            btn = QPushButton(tab_name)
            btn.setCheckable(True)
            btn.setCursor(
                QCursor(
                    Qt.CursorShape.PointingHandCursor
                )
            )
            btn.setFont(
                QFont(
                    cfg.FONT_MAIN[0], 14,
                    QFont.Weight.Bold,
                )
            )
            r = ""
            if i == 0:
                r = (
                    "border-top-left-radius: 6px; "
                    "border-bottom-left-radius: 6px;"
                )
            elif i == len(tabs) - 1:
                r = (
                    "border-top-right-radius: 6px; "
                    "border-bottom-right-radius: 6px;"
                )
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {cfg.BG_SURFACE};
                    color: {cfg.TEXT_PRIMARY};
                    border: 1px solid {cfg.BORDER_REST};
                    padding: 6px 20px;
                    {r}
                }}
                QPushButton:checked {{
                    background-color: {cfg.BG_ACTIVE};
                }}
                QPushButton:hover:!checked {{
                    background-color: {cfg.BG_CARD};
                }}
            """)
            self._nav_group.addButton(btn, i)
            nav_layout.addWidget(btn)
            self._nav_buttons[tab_name] = btn

        header_layout.addWidget(self._nav_widget)
        header_layout.addStretch(1)
        main_layout.addWidget(header_frame)

        self._content = QStackedWidget()
        self._content.setStyleSheet(
            "background: transparent;"
        )
        main_layout.addWidget(self._content, stretch=1)

        self._pages = {}
        for tab in tabs:
            self._pages[tab] = _make_scrollable_page(
                self._content
            )

        self._nav_group.idClicked.connect(
            self._content.setCurrentIndex
        )
        self._nav_buttons["General"].setChecked(True)
        self._content.setCurrentIndex(0)

        _build_general_tab(self)
        _build_model_tab(self)
        _build_advanced_tab(self)
        _build_permissions_tab(self)

    def page(self, name: str):
        return self._pages[name]


def open_settings(app):
    dialog = SettingsDialog(app)
    dialog.exec()


def _build_general_tab(dialog):
    layout = dialog.page("General").layout()
    font_main = QFont(
        cfg.FONT_MAIN[0], cfg.FONT_MAIN[1]
    )
    app = dialog.app

    llm = _section_card(
        layout,
        "Local LLM Server",
        "Connect to a local inference server. "
        "Just set your endpoint and model.",
    )

    provider_row = QWidget()
    provider_row.setStyleSheet(
        "background: transparent; border: none;"
    )
    pr_layout = QHBoxLayout(provider_row)
    pr_layout.setContentsMargins(0, 0, 0, 0)
    pr_layout.setSpacing(8)

    prov_lbl = QLabel("Provider:")
    prov_lbl.setFont(font_main)
    prov_lbl.setStyleSheet(
        f"color: {cfg.TEXT_MUTED}; "
        "background: transparent; border: none;"
    )
    pr_layout.addWidget(prov_lbl)

    dialog._provider_group = QButtonGroup(dialog)
    dialog._provider_group.setExclusive(True)

    provider_labels = ["llama.cpp", "LM Studio", "Ollama"]
    provider_keys = ["llama_cpp", "lm_studio", "ollama"]
    default_urls = {
        "llama_cpp": "http://127.0.0.1:8080",
        "lm_studio": "http://127.0.0.1:1234",
        "ollama": "http://127.0.0.1:11434",
    }
    current_provider = getattr(
        cfg, "BACKEND_TYPE", "llama_cpp"
    )

    for i, label in enumerate(provider_labels):
        pb = QPushButton(label)
        pb.setCheckable(True)
        pb.setCursor(
            QCursor(
                Qt.CursorShape.PointingHandCursor
            )
        )
        pb.setFont(font_main)
        r = ""
        if i == 0:
            r = (
                "border-top-left-radius: 6px; "
                "border-bottom-left-radius: 6px;"
            )
        elif i == len(provider_labels) - 1:
            r = (
                "border-top-right-radius: 6px; "
                "border-bottom-right-radius: 6px;"
            )
        pb.setStyleSheet(f"""
            QPushButton {{
                background-color: {cfg.BG_SURFACE};
                color: {cfg.TEXT_PRIMARY};
                border: 1px solid {cfg.BORDER_REST};
                padding: 4px 12px;
                {r}
            }}
            QPushButton:checked {{
                background-color: {cfg.ACCENT};
                color: white;
                border-color: {cfg.ACCENT};
            }}
            QPushButton:hover:!checked {{
                background-color: {cfg.BG_BASE};
            }}
        """)
        if provider_keys[i] == current_provider:
            pb.setChecked(True)
        dialog._provider_group.addButton(pb, i)
        pr_layout.addWidget(pb)

    pr_layout.addStretch(1)
    llm.addWidget(provider_row)

    def _field_row(
        label_text: str, placeholder: str, attr: str
    ):
        row = QWidget()
        row.setStyleSheet(
            "background: transparent; border: none;"
        )
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(8)
        lbl = QLabel(label_text)
        lbl.setFont(font_main)
        lbl.setStyleSheet(
            f"color: {cfg.TEXT_MUTED}; "
            "background: transparent; border: none;"
        )
        lbl.setFixedWidth(88)
        rl.addWidget(lbl)
        inp = QLineEdit()
        inp.setPlaceholderText(placeholder)
        inp.setText(getattr(cfg, attr, ""))
        inp.setFont(font_main)
        inp.setStyleSheet(f"""
            QLineEdit {{
                background-color: {cfg.BG_BASE};
                color: {cfg.TEXT_PRIMARY};
                border: 1px solid {cfg.BORDER_REST};
                border-radius: 6px;
                padding: 5px 10px;
            }}
            QLineEdit:focus {{
                border-color: {cfg.ACCENT};
            }}
        """)
        rl.addWidget(inp, stretch=1)
        return row, inp

    url_row, dialog._url_input = _field_row(
        "Server URL:", "http://localhost:1234",
        "BACKEND_URL",
    )
    llm.addWidget(url_row)

    test_row = QWidget()
    test_row.setStyleSheet(
        "background: transparent; border: none;"
    )
    test_layout = QHBoxLayout(test_row)
    test_layout.setContentsMargins(0, 0, 0, 0)
    test_layout.setSpacing(8)
    test_layout.addStretch(1)

    dialog._test_btn = QPushButton("Test Connection")
    dialog._test_btn.setCursor(
        QCursor(
            Qt.CursorShape.PointingHandCursor
        )
    )
    dialog._test_btn.setFont(font_main)
    dialog._test_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {cfg.BG_SURFACE};
            color: {cfg.TEXT_PRIMARY};
            border: 1px solid {cfg.BORDER_REST};
            border-radius: 6px;
            padding: 4px 14px;
        }}
        QPushButton:hover {{
            background-color: {cfg.BG_ACTIVE};
            border-color: {cfg.ACCENT};
        }}
    """)

    dialog._test_status = QLabel("")
    dialog._test_status.setFont(
        QFont(
            cfg.FONT_SMALL[0], cfg.FONT_SMALL[1]
        )
    )
    dialog._test_status.setStyleSheet(
        f"color: {cfg.TEXT_MUTED}; "
        "background: transparent; border: none;"
    )

    test_layout.addWidget(dialog._test_btn)
    test_layout.addWidget(dialog._test_status)
    llm.addWidget(test_row)

    def _test_connection():
        dialog._test_btn.setEnabled(False)
        dialog._test_status.setText("Testing...")
        dialog._test_status.setStyleSheet(
            f"color: {cfg.TEXT_SECONDARY}; "
            "background: transparent; border: none;"
        )
        QApplication.processEvents()

        try:
            from src.modules.backend import (
                get_active_backend,
            )

            backend = get_active_backend()
            if backend.is_healthy():
                models = backend.list_models()
                if models:
                    dialog._test_status.setText(
                        "Connected "
                        f"{len(models)} model(s) found"
                    )
                    dialog._test_status.setStyleSheet(
                        f"color: {cfg.TAG_ADD}; "
                        "background: transparent; "
                        "border: none;"
                    )
                    from ui.input_area import (
                        refresh_model_selector,
                    )

                    refresh_model_selector(app)
                else:
                    dialog._test_status.setText(
                        "Connected no models listed"
                    )
                    dialog._test_status.setStyleSheet(
                        f"color: {cfg.ACCENT}; "
                        "background: transparent; "
                        "border: none;"
                    )
            else:
                dialog._test_status.setText(
                    "Connection failed "
                    "server unreachable"
                )
                dialog._test_status.setStyleSheet(
                    f"color: {cfg.TAG_REMOVE}; "
                    "background: transparent; "
                    "border: none;"
                )
        except Exception as e:
            dialog._test_status.setText(
                f"Error: {str(e)[:60]}"
            )
            dialog._test_status.setStyleSheet(
                f"color: {cfg.TAG_REMOVE}; "
                "background: transparent; "
                "border: none;"
            )
        finally:
            dialog._test_btn.setEnabled(True)

    dialog._test_btn.clicked.connect(_test_connection)

    def _on_provider_changed(btn_idx):
        key = provider_keys[btn_idx]
        cfg.set_backend_type(key)
        is_local = (key == "llama_cpp")
        dialog._url_input.setText(
            default_urls.get(key, "")
        )
        cfg.set_backend_url(default_urls.get(key, ""))
        dialog._url_input.setEnabled(not is_local)
        dialog._gguf_folder_row.setVisible(is_local)
        dialog._gguf_found_label.setVisible(is_local)
        dialog._test_btn.setVisible(not is_local)
        dialog._test_status.setVisible(not is_local)
        from ui.input_area import refresh_model_selector

        refresh_model_selector(app)

    dialog._provider_group.idClicked.connect(
        _on_provider_changed
    )

    def _on_url_changed(val):
        cfg.set_backend_url(val)

    dialog._url_input.textChanged.connect(
        _on_url_changed
    )

    is_local = (current_provider == "llama_cpp")
    dialog._url_input.setEnabled(not is_local)
    dialog._test_btn.setVisible(not is_local)
    dialog._test_status.setVisible(not is_local)

    model_type_lbl = QLabel("Model Type:")
    model_type_lbl.setFont(font_main)
    model_type_lbl.setStyleSheet(
        f"color: {cfg.TEXT_MUTED}; "
        "background: transparent; border: none;"
    )
    llm.addWidget(model_type_lbl)

    dialog._model_type_group = QButtonGroup(dialog)
    dialog._model_type_group.setExclusive(True)

    model_types = [
        ("qwen", "Qwen 3.5"),
        ("gemma", "Gemma 4"),
    ]
    mt_row = QWidget()
    mt_row.setStyleSheet(
        "background: transparent; border: none;"
    )
    mt_layout = QHBoxLayout(mt_row)
    mt_layout.setContentsMargins(0, 2, 0, 0)
    mt_layout.setSpacing(0)
    mt_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    for i, (key, label) in enumerate(model_types):
        btn = QPushButton(label)
        btn.setCheckable(True)
        btn.setCursor(
            QCursor(
                Qt.CursorShape.PointingHandCursor
            )
        )
        btn.setFont(font_main)
        r = ""
        if i == 0:
            r = (
                "border-top-left-radius: 6px; "
                "border-bottom-left-radius: 6px;"
            )
        elif i == len(model_types) - 1:
            r = (
                "border-top-right-radius: 6px; "
                "border-bottom-right-radius: 6px;"
            )
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cfg.BG_SURFACE};
                color: {cfg.TEXT_PRIMARY};
                border: 1px solid {cfg.BORDER_REST};
                padding: 4px 12px;
                {r}
            }}
            QPushButton:checked {{
                background-color: {cfg.ACCENT};
                color: white;
                border-color: {cfg.ACCENT};
            }}
            QPushButton:hover:!checked {{
                background-color: {cfg.BG_BASE};
            }}
        """)
        if key == getattr(cfg, "MODEL_TYPE", "qwen"):
            btn.setChecked(True)
        dialog._model_type_group.addButton(btn, i)
        mt_layout.addWidget(btn)

    llm.addWidget(mt_row)

    def _on_model_type_changed(btn_idx):
        key = model_types[btn_idx][0]
        cfg.set_model_type(key)
        from ui.input_area import refresh_model_selector

        refresh_model_selector(app)

    dialog._model_type_group.idClicked.connect(
        _on_model_type_changed
    )

    dialog._gguf_folder_row = QWidget()
    dialog._gguf_folder_row.setStyleSheet(
        "background: transparent; border: none;"
    )
    gf_layout = QHBoxLayout(dialog._gguf_folder_row)
    gf_layout.setContentsMargins(0, 4, 0, 0)
    gf_layout.setSpacing(8)

    gf_lbl = QLabel("GGUF Folder:")
    gf_lbl.setFont(font_main)
    gf_lbl.setStyleSheet(
        f"color: {cfg.TEXT_MUTED}; "
        "background: transparent; border: none;"
    )
    gf_layout.addWidget(gf_lbl)

    dialog._gguf_path_label = QLabel(
        getattr(cfg, "MODEL_FOLDER", "") or "(not set)"
    )
    dialog._gguf_path_label.setFont(font_main)
    dialog._gguf_path_label.setStyleSheet(
        f"color: {cfg.TEXT_SECONDARY}; "
        "background: transparent; border: none;"
    )
    dialog._gguf_path_label.setWordWrap(True)
    gf_layout.addWidget(
        dialog._gguf_path_label, stretch=1
    )

    browse_btn = QPushButton("Browse\u25cf")
    browse_btn.setCursor(
        QCursor(
            Qt.CursorShape.PointingHandCursor
        )
    )
    browse_btn.setFont(font_main)
    browse_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {cfg.ACCENT};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 4px 10px;
        }}
        QPushButton:hover {{
            background-color: {cfg.ACCENT_DARK};
        }}
    """)
    gf_layout.addWidget(browse_btn)
    llm.addWidget(dialog._gguf_folder_row)

    dialog._gguf_found_label = QLabel()
    dialog._gguf_found_label.setFont(
        QFont(
            cfg.FONT_SMALL[0], cfg.FONT_SMALL[1]
        )
    )
    dialog._gguf_found_label.setStyleSheet(
        f"color: {cfg.TEXT_MUTED}; "
        f"background-color: {cfg.BG_BASE}; "
        "border-radius: 4px; padding: 4px 8px;"
    )
    dialog._gguf_found_label.setWordWrap(True)
    llm.addWidget(dialog._gguf_found_label)

    def _update_gguf_label():
        models = cfg.AVAILABLE_MODELS
        count = len(models)
        if count:
            names = "  \n".join(
                [f"  {m}" for m in list(models.keys())[:5]]
            )
            more = (
                f"\n  ... and {count - 5} more"
                if count > 5
                else ""
            )
            dialog._gguf_found_label.setText(
                f"Found {count} model(s) in folder:"
                f"{names}{more}"
            )
        else:
            dialog._gguf_found_label.setText(
                "No .gguf files found in folder."
            )

    def _browse_gguf_folder():
        folder = QFileDialog.getExistingDirectory(
            dialog,
            "Select GGUF Model Folder",
            cfg.BASE_DIR,
        )
        if folder:
            cfg.set_model_folder(folder)
            dialog._gguf_path_label.setText(folder)
            _update_gguf_label()
            from ui.input_area import (
                refresh_model_selector,
            )

            refresh_model_selector(app)

    browse_btn.clicked.connect(_browse_gguf_folder)
    _update_gguf_label()

    is_local = (current_provider == "llama_cpp")
    dialog._gguf_folder_row.setVisible(is_local)
    dialog._gguf_found_label.setVisible(is_local)

    appear = _section_card(
        layout,
        "Color Palette",
        "The app restarts automatically "
        "to apply changes.",
    )

    palette_container = QWidget()
    palette_container.setStyleSheet(
        "background: transparent;"
    )
    palette_flow = FlowLayout(
        palette_container, h_gap=6, v_gap=6
    )

    current_palette = cfg._ACTIVE_PALETTE_NAME
    for name in cfg.PALETTES:
        p = cfg.PALETTES[name]
        swatch = p["SWATCH"]
        bg = p["BG_SURFACE"]
        text = p["TEXT_PRIMARY"]
        is_active = (name == current_palette)
        border = (
            f"2px solid {swatch}"
            if is_active
            else f"1px solid {p['BORDER_REST']}"
        )

        btn = QPushButton()
        btn.setCursor(
            QCursor(
                Qt.CursorShape.PointingHandCursor
            )
        )
        btn.setFixedSize(148, 36)
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg};
                border: {border};
                border-radius: 6px;
            }}
            QPushButton:hover {{
                border: 2px solid {swatch};
            }}
        """)

        bl = QHBoxLayout(btn)
        bl.setContentsMargins(10, 0, 10, 0)
        bl.setSpacing(6)
        bl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
            | Qt.AlignmentFlag.AlignLeft
        )

        dot = QLabel("\u25cf")
        dot.setFont(
            QFont(cfg.FONT_MAIN[0], 10)
        )
        dot.setStyleSheet(
            f"color: {swatch}; "
            "background: transparent; border: none;"
        )
        dot.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        bl.addWidget(dot)

        name_lbl = QLabel(
            name + ("  \u2714" if is_active else "")
        )
        name_lbl.setFont(
            QFont(
                cfg.FONT_SMALL[0], cfg.FONT_SMALL[1],
                QFont.Weight.Bold
                if is_active
                else QFont.Weight.Normal,
            )
        )
        name_lbl.setStyleSheet(
            f"color: {text}; "
            "background: transparent; border: none;"
        )
        name_lbl.setAlignment(
            Qt.AlignmentFlag.AlignVCenter
        )
        bl.addWidget(name_lbl)

        btn.clicked.connect(
            lambda _c, n=name: _apply_palette(app, n)
        )
        palette_flow.addWidget(btn)

    appear.addWidget(palette_container)

    identity = _section_card(
        layout,
        "Identity",
        "Customize how the AI sees itself. "
        "Edit the instructions below and hit save.",
    )

    identity_path = os.path.join(
        cfg.INSTRUCTIONS_DIR, "identity.md"
    )

    dialog._identity_edit = QTextEdit()
    dialog._identity_edit.setFont(font_main)
    dialog._identity_edit.setStyleSheet(f"""
        QTextEdit {{
            background-color: {cfg.BG_BASE};
            color: {cfg.TEXT_PRIMARY};
            border: 1px solid {cfg.BORDER_REST};
            border-radius: 6px;
            padding: 8px;
        }}
        QTextEdit:focus {{
            border-color: {cfg.ACCENT};
        }}
    """)
    dialog._identity_edit.setMinimumHeight(140)

    try:
        with open(
            identity_path, 'r', encoding='utf-8'
        ) as f:
            dialog._identity_edit.setPlainText(f.read())
    except Exception:
        dialog._identity_edit.setPlainText(
            "# MISSION\n"
            "You are an AI coding assistant."
        )

    identity.addWidget(dialog._identity_edit)

    save_row = QWidget()
    save_row.setStyleSheet(
        "background: transparent; border: none;"
    )
    sr_layout = QHBoxLayout(save_row)
    sr_layout.setContentsMargins(0, 4, 0, 0)
    sr_layout.setSpacing(8)

    save_btn = QPushButton("Save Identity")
    save_btn.setCursor(
        QCursor(
            Qt.CursorShape.PointingHandCursor
        )
    )
    save_btn.setFont(font_main)
    save_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {cfg.ACCENT};
            color: white;
            border: none;
            border-radius: 6px;
            padding: 6px 16px;
        }}
        QPushButton:hover {{
            background-color: {cfg.ACCENT_DARK};
        }}
    """)

    def _save_identity():
        try:
            with open(
                identity_path, 'w', encoding='utf-8'
            ) as f:
                f.write(
                    dialog._identity_edit.toPlainText()
                )
            QMessageBox.information(
                dialog,
                "Saved",
                "Identity saved "
                "to instructions/identity.md",
            )
        except Exception as e:
            QMessageBox.warning(
                dialog,
                "Error",
                f"Could not save identity:\n{e}",
            )

    save_btn.clicked.connect(_save_identity)
    sr_layout.addWidget(save_btn)
    sr_layout.addStretch(1)
    identity.addWidget(save_row)

    layout.addStretch(1)


def _build_model_tab(dialog):
    layout = dialog.page("Model").layout()
    font_main = QFont(
        cfg.FONT_MAIN[0], cfg.FONT_MAIN[1]
    )

    def _slider_card(
        parent, title, subtitle, attr, default,
        lo, hi, step, label_fn,
    ):
        card = _section_card(parent, title, subtitle)
        val = getattr(cfg, attr, default)
        lbl = QLabel(label_fn(val))
        lbl.setFont(font_main)
        lbl.setStyleSheet(
            f"color: {cfg.TEXT_PRIMARY}; "
            "background: transparent; border: none;"
        )
        card.addWidget(lbl)
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(lo, hi)
        sl.setSingleStep(step)
        sl.setValue(val)
        card.addWidget(sl)
        return lbl, sl

    dialog._ctx_label, dialog._ctx_slider = _slider_card(
        layout,
        "Context Window",
        "How many tokens the model can see at once. "
        "Higher = longer memory, more RAM.",
        "NUM_CTX", 16000, 2048, 262144, 2048,
        lambda v: f"Size: {v:,} tokens",
    )
    dialog._ctx_slider.valueChanged.connect(
        lambda v: _update_ctx_label(dialog, v)
    )

    (
        dialog._predict_label,
        dialog._predict_slider,
    ) = _slider_card(
        layout,
        "Max Output Tokens",
        "Maximum number of tokens the model "
        "can generate per reply.",
        "MAX_TOKENS", 8192, 1024, 32768, 1024,
        lambda v: f"Limit: {v:,} tokens",
    )
    dialog._predict_slider.valueChanged.connect(
        lambda v: _update_predict_label(dialog, v)
    )

    current_temp = getattr(cfg, 'TEMPERATURE', 0.6)
    temp_card = _section_card(
        layout,
        "Temperature",
        "Controls randomness. "
        "Lower = focused and deterministic. "
        "Higher = creative and unpredictable.",
    )
    dialog._temp_label = QLabel(
        f"Value: {current_temp:.1f}"
    )
    dialog._temp_label.setFont(font_main)
    dialog._temp_label.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    temp_card.addWidget(dialog._temp_label)
    dialog._temp_slider = QSlider(
        Qt.Orientation.Horizontal
    )
    dialog._temp_slider.setRange(0, 20)
    dialog._temp_slider.setValue(
        int(current_temp * 10)
    )
    dialog._temp_slider.valueChanged.connect(
        lambda v: _update_temp_label(dialog, v)
    )
    temp_card.addWidget(dialog._temp_slider)

    layout.addStretch(1)


def _build_advanced_tab(dialog):
    layout = dialog.page("Advanced").layout()
    font_main = QFont(
        cfg.FONT_MAIN[0], cfg.FONT_MAIN[1]
    )

    def _label_slider(
        card_layout, label_fn, attr, default,
        lo, hi, update_fn,
    ):
        val = getattr(cfg, attr, default)
        lbl = QLabel(label_fn(val))
        lbl.setFont(font_main)
        lbl.setStyleSheet(
            f"color: {cfg.TEXT_PRIMARY}; "
            "background: transparent; border: none;"
        )
        card_layout.addWidget(lbl)
        sl = QSlider(Qt.Orientation.Horizontal)
        sl.setRange(lo, hi)
        sl.setValue(val)
        sl.valueChanged.connect(update_fn)
        card_layout.addWidget(sl)
        card_layout.addSpacing(4)
        return lbl, sl

    hw = _section_card(
        layout,
        "Hardware",
        "Low-level engine settings. "
        "May require a model reload to take effect.",
    )

    (
        dialog._thread_label,
        dialog._thread_slider,
    ) = _label_slider(
        hw,
        lambda v: f"CPU Threads: {v}",
        "NUM_THREAD", 8, 1, 32,
        lambda v: _update_thread_label(dialog, v),
    )
    (
        dialog._gpu_label,
        dialog._gpu_slider,
    ) = _label_slider(
        hw,
        lambda v: (
            "GPU Layers Offload: "
            f"{'Auto / Max' if v == -1 else v}"
        ),
        "GPU_LAYERS", -1, -1, 80,
        lambda v: _update_gpu_label(dialog, v),
    )
    (
        dialog._cpu_label,
        dialog._cpu_slider,
    ) = _label_slider(
        hw,
        lambda v: (
            f"CPU MoE Layers: "
            f"{'Off' if v == 0 else v}"
        ),
        "CPU_MOE_LAYERS", 0, 0, 64,
        lambda v: _update_cpu_label(dialog, v),
    )

    mem = _section_card(layout, "Memory & Precision")
    kv_lbl = QLabel("KV Cache Precision")
    kv_lbl.setFont(font_main)
    kv_lbl.setStyleSheet(
        f"color: {cfg.TEXT_MUTED}; "
        "background: transparent; border: none;"
    )
    mem.addWidget(kv_lbl)

    dialog._kv_group = QButtonGroup(dialog)
    dialog._kv_group.setExclusive(True)

    kv_row = QWidget()
    kv_row.setStyleSheet(
        "background: transparent;"
    )
    kv_layout = QHBoxLayout(kv_row)
    kv_layout.setContentsMargins(0, 2, 0, 0)
    kv_layout.setSpacing(0)
    kv_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)

    kv_options = [
        ("f16", "f16  (Standard)"),
        ("q8_0", "q8_0  (8-bit)"),
        ("q4_0", "q4_0  (4-bit)"),
    ]
    current_kv = getattr(cfg, 'KV_CACHE_QUANT', "f16")

    for i, (val, name) in enumerate(kv_options):
        btn = QPushButton(name)
        btn.setCheckable(True)
        btn.setCursor(
            QCursor(
                Qt.CursorShape.PointingHandCursor
            )
        )
        btn.setFont(
            QFont(
                cfg.FONT_MAIN[0], 11,
                QFont.Weight.Bold,
            )
        )
        r = ""
        if i == 0:
            r = (
                "border-top-left-radius: 6px; "
                "border-bottom-left-radius: 6px;"
            )
        elif i == len(kv_options) - 1:
            r = (
                "border-top-right-radius: 6px; "
                "border-bottom-right-radius: 6px;"
            )
        btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cfg.BG_SURFACE};
                color: {cfg.TEXT_PRIMARY};
                border: 1px solid {cfg.BORDER_REST};
                padding: 6px 12px;
                {r}
            }}
            QPushButton:checked {{
                background-color: {cfg.ACCENT};
                color: white;
                border-color: {cfg.ACCENT};
            }}
            QPushButton:hover:!checked {{
                background-color: {cfg.BG_BASE};
            }}
        """)
        if val == current_kv:
            btn.setChecked(True)
        dialog._kv_group.addButton(btn, i)
        kv_layout.addWidget(btn)
        btn.clicked.connect(
            lambda _c, v=val: _update_kv_cache(v)
        )

    mem.addWidget(kv_row)
    mem.addSpacing(cfg.PAD_SM)

    dialog._cache_switch = QCheckBox(
        "Prompt Caching speeds up "
        "multi-turn conversations"
    )
    dialog._cache_switch.setFont(font_main)
    dialog._cache_switch.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    dialog._cache_switch.setChecked(
        getattr(cfg, 'PROMPT_CACHING', True)
    )
    dialog._cache_switch.toggled.connect(
        lambda v: (
            setattr(cfg, 'PROMPT_CACHING', v),
            prefs_mgr.update_pref(
                "PROMPT_CACHING", v
            ),
        )
    )
    mem.addWidget(dialog._cache_switch)

    flags = _section_card(
        layout,
        "Engine Flags",
        "Both options force a model reload "
        "when toggled.",
    )

    dialog._fa_switch = QCheckBox(
        "Flash Attention  (-fa)"
    )
    dialog._fa_switch.setFont(font_main)
    dialog._fa_switch.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    dialog._fa_switch.setChecked(
        getattr(cfg, 'FLASH_ATTENTION', True)
    )
    dialog._fa_switch.toggled.connect(
        lambda v: (
            setattr(cfg, 'FLASH_ATTENTION', v),
            prefs_mgr.update_pref(
                "FLASH_ATTENTION", v
            ),
        )
    )
    flags.addWidget(dialog._fa_switch)

    dialog._mlock_switch = QCheckBox(
        "Lock model in RAM  (--mlock)"
    )
    dialog._mlock_switch.setFont(font_main)
    dialog._mlock_switch.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    dialog._mlock_switch.setChecked(
        getattr(cfg, 'MLOCK', False)
    )
    dialog._mlock_switch.toggled.connect(
        lambda v: (
            setattr(cfg, 'MLOCK', v),
            prefs_mgr.update_pref("MLOCK", v),
        )
    )
    flags.addWidget(dialog._mlock_switch)

    debug_section = _section_card(
        layout,
        "Developer",
        "Debug prints show backend switching, "
        "request details, and connection status "
        "in the terminal. Useful for "
        "troubleshooting provider issues.",
    )
    dialog._debug_switch = QCheckBox(
        "Enable debug terminal output"
    )
    dialog._debug_switch.setFont(font_main)
    dialog._debug_switch.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    dialog._debug_switch.setChecked(
        getattr(cfg, "DEBUG", False)
    )
    dialog._debug_switch.toggled.connect(
        lambda v: cfg.set_debug(v)
    )
    debug_section.addWidget(dialog._debug_switch)

    tools_section = _section_card(
        layout,
        "Tool Calling",
        "Native JSON Schema tool calling. "
        "When OFF, Sulfur uses the legacy XML "
        "tag system (<file>, <add>, <remove>) "
        "which works with any local model. "
        "When ON, Sulfur sends structured tool "
        "definitions; this requires a model that "
        "supports native function calling "
        "(most small local models do NOT). "
        "Unstable on local models.",
    )

    dialog._json_tools_switch = QCheckBox(
        "Enable JSON Schema tools (experimental)"
    )
    dialog._json_tools_switch.setFont(font_main)
    dialog._json_tools_switch.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    dialog._json_tools_switch.setChecked(
        getattr(cfg, "JSON_TOOLS", False)
    )
    dialog._json_tools_switch.toggled.connect(
        lambda v: cfg.set_json_tools(v)
    )
    tools_section.addWidget(dialog._json_tools_switch)
    dialog.setStyleSheet(
        f"padding: 1px; "
        f"background: {cfg.BG_BASE};"
    )
    layout.addStretch(1)


def _build_permissions_tab(dialog):
    layout = dialog.page("Permissions").layout()
    font_main = QFont(
        cfg.FONT_MAIN[0], cfg.FONT_MAIN[1]
    )

    read_card = _section_card(
        layout,
        "Read Access",
        "Controls whether Sulfur can see "
        "the contents of files in the workspace. "
        "When OFF, the AI sees file names.",
    )

    dialog._allow_read_cb = QCheckBox(
        "Allow AI to read file contents"
    )
    dialog._allow_read_cb.setFont(font_main)
    dialog._allow_read_cb.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    dialog._allow_read_cb.setChecked(
        getattr(cfg, "ALLOW_READ", True)
    )
    dialog._allow_read_cb.toggled.connect(
        lambda v: cfg.set_allow_read(v)
    )
    read_card.addWidget(dialog._allow_read_cb)

    write_card = _section_card(
        layout,
        "Write Access",
        "Controls whether Sulfur can write "
        "or edit files. When OFF, Sulfur "
        "operates in read-only mode and will "
        "not attempt to make changes.",
    )

    dialog._allow_write_cb = QCheckBox(
        "Allow AI to write/edit files"
    )
    dialog._allow_write_cb.setFont(font_main)
    dialog._allow_write_cb.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    dialog._allow_write_cb.setChecked(
        getattr(cfg, "ALLOW_WRITE", True)
    )
    dialog._allow_write_cb.toggled.connect(
        lambda v: cfg.set_allow_write(v)
    )
    write_card.addWidget(dialog._allow_write_cb)

    confirm_card = _section_card(
        layout,
        "Confirmation",
        "By default, Sulfur shows a review card "
        "for every proposed edit and waits for "
        "your approval. Enable this to skip the "
        "review step and apply edits immediately. "
        "This is convenient but removes the safety "
        "net; only enable if you fully trust "
        "your local LLM.",
    )

    dialog._auto_apply_cb = QCheckBox(
        "Auto-apply edits without confirmation"
    )
    dialog._auto_apply_cb.setFont(font_main)
    dialog._auto_apply_cb.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    dialog._auto_apply_cb.setChecked(
        getattr(cfg, "AUTO_APPLY_EDITS", False)
    )
    dialog._auto_apply_cb.toggled.connect(
        lambda v: _on_auto_apply_toggled(dialog, v)
    )
    confirm_card.addWidget(dialog._auto_apply_cb)

    layout.addStretch(1)


def _on_auto_apply_toggled(dialog, enabled: bool):
    if enabled:
        msg = QMessageBox(dialog)
        msg.setWindowTitle("Safety Warning")
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setText(
            "Auto-apply edits "
            "without confirmation?"
        )
        msg.setInformativeText(
            "Edits will be applied immediately "
            "without review. "
            "This means the AI can modify "
            "workspace files automatically. "
            "Only enable this if you fully trust "
            "your local LLM."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(
            QMessageBox.StandardButton.No
        )
        if (
            msg.exec()
            == QMessageBox.StandardButton.No
        ):
            dialog._auto_apply_cb.blockSignals(True)
            dialog._auto_apply_cb.setChecked(False)
            dialog._auto_apply_cb.blockSignals(False)
            return
    cfg.set_auto_apply_edits(enabled)


def _update_ctx_label(dialog, val):
    dialog._ctx_label.setText(
        f"Size: {val:,} tokens"
    )
    cfg.NUM_CTX = val
    prefs_mgr.update_pref("NUM_CTX", val)


def _update_predict_label(dialog, val):
    dialog._predict_label.setText(
        f"Limit: {val:,} tokens"
    )
    cfg.MAX_TOKENS = val
    prefs_mgr.update_pref("MAX_TOKENS", val)


def _update_temp_label(dialog, val):
    real = val / 10.0
    dialog._temp_label.setText(
        f"Value: {real:.1f}"
    )
    cfg.TEMPERATURE = real
    prefs_mgr.update_pref("TEMPERATURE", real)


def _update_thread_label(dialog, val):
    dialog._thread_label.setText(
        f"CPU Threads: {val}"
    )
    cfg.NUM_THREAD = val
    prefs_mgr.update_pref("NUM_THREAD", val)


def _update_gpu_label(dialog, val):
    txt = "Auto / Max" if val == -1 else str(val)
    dialog._gpu_label.setText(
        f"GPU Layers Offload: {txt}"
    )
    cfg.GPU_LAYERS = val
    prefs_mgr.update_pref("GPU_LAYERS", val)


def _update_cpu_label(dialog, val):
    txt = "Off" if val == 0 else str(val)
    dialog._cpu_label.setText(
        f"CPU MoE Layers: {txt}"
    )
    cfg.CPU_MOE_LAYERS = val
    prefs_mgr.update_pref("CPU_MOE_LAYERS", val)


def _update_kv_cache(val):
    cfg.KV_CACHE_QUANT = val
    prefs_mgr.update_pref("KV_CACHE_QUANT", val)
    print(
        "[SETTINGS] KV Cache precision "
        f"{val}  (engine reloads on next prompt)"
    )


def _apply_palette(app, palette_name: str):
    prefs_mgr.update_pref("PALETTE", palette_name)
    msg = QMessageBox(app)
    msg.setWindowTitle("Palette changed")
    msg.setText(
        f"{palette_name} saved.\n\n"
        "The app needs to close to apply changes. "
        "Continue?"
    )
    msg.setStandardButtons(
        QMessageBox.StandardButton.Yes
        | QMessageBox.StandardButton.No
    )
    msg.setDefaultButton(
        QMessageBox.StandardButton.No
    )
    if msg.exec() == QMessageBox.StandardButton.Yes:
        sys.exit(0)
