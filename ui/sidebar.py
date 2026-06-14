from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QWidget, QLineEdit,
    QStackedWidget,
)
from PyQt6.QtCore import (
    Qt, QPropertyAnimation, QEasingCurve,
    QParallelAnimationGroup, QTimer,
)
from PyQt6.QtGui import QFont, QCursor, QFontMetrics

import src.modules.configurations as cfg
import src.modules.session_manager as session_manager
import src.modules.target_path as target_path_module


def build_sidebar(app):
    app.sidebar_expanded = True

    app.EXPANDED_WIDTH = 300
    app.COLLAPSED_WIDTH = 45

    app.sidebar_frame = QFrame()
    app.sidebar_frame.setFixedWidth(app.EXPANDED_WIDTH)
    app.sidebar_frame.setStyleSheet(f"""
        QFrame {{
            background-color: {cfg.BG_SURFACE};
            border-right: 1px solid {cfg.BORDER_REST};
        }}
    """)
    app.sidebar_layout = QVBoxLayout(app.sidebar_frame)
    app.sidebar_layout.setContentsMargins(0, 0, 0, 0)

    app.main_layout.addWidget(app.sidebar_frame)

    app.sidebar_stack = QStackedWidget()
    app.sidebar_stack.setStyleSheet(
        "border: none; background: transparent;"
    )
    app.sidebar_layout.addWidget(app.sidebar_stack)

    app.sidebar_expanded_view = QWidget()
    expanded_layout = QVBoxLayout(
        app.sidebar_expanded_view
    )
    expanded_layout.setContentsMargins(0, 0, 0, 0)

    header_row = QWidget()
    header_layout = QHBoxLayout(header_row)
    header_layout.setContentsMargins(
        cfg.PAD_MD, cfg.PAD_MD, cfg.PAD_MD, cfg.PAD_SM
    )

    title_lbl = QLabel("Sessions")
    title_lbl.setFont(
        QFont(cfg.FONT_SMALL[0], cfg.FONT_SMALL[1])
    )
    title_lbl.setStyleSheet(
        f"color: {cfg.TEXT_SECONDARY};"
    )
    header_layout.addWidget(title_lbl)

    header_layout.addStretch(1)

    collapse_btn = QPushButton("\u25c0")
    collapse_btn.setFixedSize(24, 24)
    collapse_btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    collapse_btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {cfg.TEXT_MUTED};
            border: none;
        }}
        QPushButton:hover {{
            background-color: {cfg.BG_ACTIVE};
            border-radius: 4px;
        }}
    """)
    collapse_btn.clicked.connect(
        lambda: toggle_sidebar(app)
    )
    header_layout.addWidget(collapse_btn)

    expanded_layout.addWidget(header_row)

    new_btn_container = QWidget()
    new_btn_layout = QVBoxLayout(new_btn_container)
    new_btn_layout.setContentsMargins(
        cfg.PAD_MD, 0, cfg.PAD_MD, cfg.PAD_SM
    )

    new_btn = QPushButton("\uff0b  New Session")
    new_btn.setFixedHeight(32)
    new_btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    new_btn.setFont(
        QFont(
            cfg.FONT_SMALL[0], cfg.FONT_SMALL[1],
            QFont.Weight.Bold,
        )
    )
    new_btn.setStyleSheet(f"""
        QPushButton {{
            background-color: {cfg.ACCENT};
            color: {cfg.TEXT_PRIMARY};
            border-radius: {cfg.RADIUS_MD}px;
            border: none;
        }}
        QPushButton:hover {{
            background-color: {cfg.ACCENT_DARK};
        }}
    """)
    new_btn.clicked.connect(
        lambda: on_new_session(app)
    )
    new_btn_layout.addWidget(new_btn)
    expanded_layout.addWidget(new_btn_container)

    app.session_list_area = QScrollArea()
    app.session_list_area.setWidgetResizable(True)
    app.session_list_area.setStyleSheet(
        "QScrollArea { border: none; "
        "background: transparent; }"
    )
    app.session_list_area.setHorizontalScrollBarPolicy(
        Qt.ScrollBarPolicy.ScrollBarAlwaysOff
    )

    app.session_list_content = QWidget()
    app.session_list_content.setStyleSheet(
        "background: transparent;"
    )
    app.session_list_content_layout = QVBoxLayout(
        app.session_list_content
    )
    app.session_list_content_layout.setContentsMargins(
        cfg.PAD_SM, 0, cfg.PAD_SM, cfg.PAD_MD
    )
    app.session_list_content_layout.setAlignment(
        Qt.AlignmentFlag.AlignTop
    )

    app.session_list_area.setWidget(
        app.session_list_content
    )
    expanded_layout.addWidget(app.session_list_area)

    app.sidebar_stack.addWidget(
        app.sidebar_expanded_view
    )

    app.sidebar_collapsed_view = QWidget()
    collapsed_layout = QVBoxLayout(
        app.sidebar_collapsed_view
    )
    collapsed_layout.setContentsMargins(
        0, cfg.PAD_MD, 0, 0
    )
    collapsed_layout.setAlignment(
        Qt.AlignmentFlag.AlignTop
        | Qt.AlignmentFlag.AlignHCenter
    )

    expand_btn = QPushButton("\u25b6")
    expand_btn.setFixedSize(24, 24)
    expand_btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    expand_btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            color: {cfg.TEXT_MUTED};
            border: none;
        }}
        QPushButton:hover {{
            background-color: {cfg.BG_ACTIVE};
            border-radius: 4px;
        }}
    """)
    expand_btn.clicked.connect(
        lambda: toggle_sidebar(app)
    )
    collapsed_layout.addWidget(expand_btn)

    app.sidebar_stack.addWidget(
        app.sidebar_collapsed_view
    )

    app.sidebar_stack.setCurrentIndex(0)

    app.sidebar_anim = QPropertyAnimation(
        app.sidebar_frame, b"minimumWidth"
    )
    app.sidebar_anim.setEasingCurve(
        QEasingCurve.Type.InOutQuart
    )
    app.sidebar_anim.setDuration(350)

    app.sidebar_anim2 = QPropertyAnimation(
        app.sidebar_frame, b"maximumWidth"
    )
    app.sidebar_anim2.setEasingCurve(
        QEasingCurve.Type.InOutQuart
    )
    app.sidebar_anim2.setDuration(350)

    app.anim_group = QParallelAnimationGroup()
    app.anim_group.addAnimation(app.sidebar_anim)
    app.anim_group.addAnimation(app.sidebar_anim2)

    refresh_session_list(app)


def toggle_sidebar(app):
    if (
        app.anim_group.state()
        == QPropertyAnimation.State.Running
    ):
        return

    start_w = app.sidebar_frame.width()

    if app.sidebar_expanded:
        end_w = app.COLLAPSED_WIDTH
        app.sidebar_stack.setCurrentIndex(1)
        app.sidebar_expanded = False
    else:
        end_w = app.EXPANDED_WIDTH
        app.sidebar_expanded = True

    app.sidebar_anim.setStartValue(start_w)
    app.sidebar_anim.setEndValue(end_w)
    app.sidebar_anim2.setStartValue(start_w)
    app.sidebar_anim2.setEndValue(end_w)

    if app.sidebar_expanded:
        app.anim_group.finished.connect(
            lambda: _on_expand_finished(app)
        )
    else:
        try:
            app.anim_group.finished.disconnect()
        except Exception:
            pass

    app.anim_group.start()


def _on_expand_finished(app):
    if app.sidebar_expanded:
        app.sidebar_stack.setCurrentIndex(0)
    try:
        app.anim_group.finished.disconnect()
    except Exception:
        pass


class SessionCard(QFrame):
    def __init__(self, app, session, active):
        super().__init__()
        self.app = app
        self.session_id = session["id"]
        self.current_name = session.get("name", "Untitled")

        self.setMaximumWidth(250)

        files = session.get("workspace_files", [])
        if not files:
            target_name = "Chat"
        elif len(files) == 1:
            target_name = (
                files[0]
                .replace("\\", "/")
                .split("/")[-1]
            )
        else:
            target_name = f"{len(files)} files attached"

        model = session.get("model_name", "\u2014")

        bg_color = (
            cfg.ACCENT_TINT if active else cfg.BG_CARD
        )
        border_color = (
            cfg.BORDER_ACTIVE
            if active
            else cfg.BORDER_REST
        )
        name_color = (
            cfg.TEXT_PRIMARY
            if active
            else cfg.TEXT_SECONDARY
        )

        self.setStyleSheet(f"""
            SessionCard {{
                background-color: {bg_color};
                border-radius: {cfg.RADIUS_MD}px;
                border: 1px solid {border_color};
            }}
            SessionCard:hover {{
                border: 1px solid {cfg.ACCENT};
            }}
        """)

        self.setCursor(
            QCursor(Qt.CursorShape.PointingHandCursor)
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            cfg.PAD_SM, cfg.PAD_SM,
            cfg.PAD_SM, cfg.PAD_SM,
        )
        layout.setSpacing(2)

        top_row = QWidget()
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)

        font = QFont(
            cfg.FONT_SMALL[0], cfg.FONT_SMALL[1],
            QFont.Weight.Bold,
        )
        metrics = QFontMetrics(font)
        elided_name = metrics.elidedText(
            self.current_name,
            Qt.TextElideMode.ElideRight,
            140,
        )

        self.name_label = QLabel(elided_name)
        self.name_label.setFont(font)
        self.name_label.setToolTip(self.current_name)
        self.name_label.setStyleSheet(
            f"color: {name_color}; "
            "border: none; background: transparent;"
        )
        top_layout.addWidget(
            self.name_label, stretch=1
        )

        del_btn = QPushButton("\u2715")
        del_btn.setFixedSize(20, 20)
        del_btn.setFont(
            QFont(cfg.FONT_MONO[0], 10)
        )
        del_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                color: {cfg.TEXT_MUTED};
                border: none;
            }}
            QPushButton:hover {{
                background-color: {cfg.BG_ACTIVE};
                border-radius: {cfg.RADIUS_SM}px;
            }}
        """)
        del_btn.clicked.connect(
            lambda: on_delete_session(
                self.app, self.session_id
            )
        )
        top_layout.addWidget(del_btn)

        layout.addWidget(top_row)

        target_lbl = QLabel(f"  {target_name}")
        target_lbl.setFont(
            QFont(
                cfg.FONT_MONO[0], cfg.FONT_MONO[1]
            )
        )
        target_lbl.setStyleSheet(
            f"color: {cfg.TEXT_MUTED}; "
            "border: none; background: transparent;"
        )
        layout.addWidget(target_lbl)

        model_lbl = QLabel(f"  {model}")
        model_lbl.setFont(
            QFont(
                cfg.FONT_MONO[0], cfg.FONT_MONO[1]
            )
        )
        model_lbl.setStyleSheet(
            f"color: {cfg.TEXT_MUTED}; "
            "border: none; background: transparent;"
        )
        layout.addWidget(model_lbl)

        self.edit_mode = False
        self.rename_input = QLineEdit()
        self.rename_input.setFont(
            QFont(
                cfg.FONT_SMALL[0], cfg.FONT_SMALL[1]
            )
        )
        self.rename_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {cfg.BG_BASE};
                color: {cfg.TEXT_PRIMARY};
                border: 1px solid {cfg.ACCENT};
                border-radius: {cfg.RADIUS_SM}px;
                padding: 2px 4px;
            }}
        """)
        self.rename_input.hide()
        self.rename_input.returnPressed.connect(
            self.commit_rename
        )
        self.rename_input.editingFinished.connect(
            self.commit_rename
        )
        top_layout.insertWidget(
            0, self.rename_input, stretch=1
        )

    def mousePressEvent(self, event):
        if (
            event.button() == Qt.MouseButton.LeftButton
            and not self.edit_mode
        ):
            on_switch_session(
                self.app, self.session_id
            )
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.edit_mode = True
            self.name_label.hide()
            self.rename_input.setText(
                self.current_name
            )
            self.rename_input.show()
            self.rename_input.setFocus()
            self.rename_input.selectAll()
        super().mouseDoubleClickEvent(event)

    def commit_rename(self):
        if not self.edit_mode:
            return
        self.edit_mode = False

        new_name = (
            self.rename_input.text().strip()
            or self.current_name
        )
        session_manager.rename_session(
            self.session_id, new_name
        )

        self.current_name = new_name

        metrics = QFontMetrics(self.name_label.font())
        elided_name = metrics.elidedText(
            self.current_name,
            Qt.TextElideMode.ElideRight,
            140,
        )

        self.name_label.setText(elided_name)
        self.name_label.setToolTip(self.current_name)

        self.rename_input.hide()
        self.name_label.show()


def refresh_session_list(app):
    layout = app.session_list_content_layout
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()

    sessions = session_manager.list_sessions()
    active_id = session_manager.get_active_session_id()

    if not sessions:
        empty_lbl = QLabel(
            "No sessions yet.\n"
            "Click \uff0b to start."
        )
        empty_lbl.setFont(
            QFont(
                cfg.FONT_SMALL[0], cfg.FONT_SMALL[1]
            )
        )
        empty_lbl.setStyleSheet(
            f"color: {cfg.TEXT_MUTED};"
        )
        empty_lbl.setAlignment(
            Qt.AlignmentFlag.AlignCenter
        )
        layout.addWidget(empty_lbl)
        layout.addSpacing(cfg.PAD_LG)
        return

    for s in sessions:
        card = SessionCard(
            app, s, active=(s["id"] == active_id)
        )
        layout.addWidget(card)


def on_new_session(app):
    s = session_manager.create_session()
    session_manager.set_active_session_id(s["id"])
    _apply_session_to_ui(app, s)
    refresh_session_list(app)


def on_switch_session(app, session_id: str):
    if session_id == session_manager.get_active_session_id():
        return
    session_manager.set_active_session_id(session_id)
    s = session_manager.load_session(session_id)
    if s:
        _apply_session_to_ui(app, s)
    refresh_session_list(app)


def on_delete_session(app, session_id: str):
    active_id = session_manager.get_active_session_id()
    session_manager.delete_session(session_id)
    remaining = session_manager.list_sessions()

    if session_id == active_id:
        if remaining:
            new_active = remaining[0]
            session_manager.set_active_session_id(
                new_active["id"]
            )
            _apply_session_to_ui(app, new_active)
        else:
            session_manager.set_active_session_id(None)
            _blank_ui(app)

    refresh_session_list(app)


def _apply_session_to_ui(app, session: dict):
    model = (
        session.get("model_name") or cfg.MODEL_NAME
    )
    cfg.set_model_name(model)
    if hasattr(app, "model_select"):
        QTimer.singleShot(
            0,
            lambda: app.model_select.setCurrentText(
                model
            ),
        )

    files = session.get("workspace_files", [])

    from src.modules.more_modules.target_path_ops import (
        set_target,
    )

    set_target(None)

    for f in files:
        set_target(f)

    from ui.input_area import _refresh_workspace_label

    _refresh_workspace_label(app)

    from ui.chat_area import (
        reset_chat_area,
        insert_welcome_message,
        load_chat_history,
    )

    reset_chat_area(app)
    messages = session.get("messages", [])
    if messages:
        QTimer.singleShot(
            50, lambda: load_chat_history(app)
        )
    else:
        insert_welcome_message(app)


def _reload_chat(
    app,
    session,
    reset_chat_area,
    insert_welcome_message,
    add_user_message,
    add_ai_message,
    _dismiss_welcome,
):
    reset_chat_area(app)
    messages = session.get("messages", [])
    if messages:
        app._history_loaded = True
        _dismiss_welcome(app)
        for msg in messages:
            role = (msg or {}).get("role")
            content = (msg or {}).get("content", "")
            if not content:
                continue
            if role == "user":
                add_user_message(app, content)
            elif role == "assistant":
                add_ai_message(app, content)
    else:
        insert_welcome_message(app)


def _blank_ui(app):
    from src.modules.more_modules.target_path_ops import (
        set_target,
    )

    set_target(None)

    from ui.chat_area import (
        reset_chat_area,
        insert_welcome_message,
    )

    reset_chat_area(app)
    insert_welcome_message(app)
