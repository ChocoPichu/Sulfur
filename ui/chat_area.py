import re
from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QFrame, QPushButton, QApplication,
    QSizePolicy, QGraphicsOpacityEffect,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPropertyAnimation, QEasingCurve,
)
from PyQt6.QtGui import QFont, QCursor

import src.modules.configurations as cfg
from src.modules.more_modules.memory_ops import get_memory
from ui.stream_formatter import StreamFormatter


class SmoothScrollArea(QScrollArea):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._v_anim = QPropertyAnimation(
            self.verticalScrollBar(), b"value"
        )
        self._v_anim.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )
        self._v_anim.setDuration(250)
        self.verticalScrollBar().valueChanged.connect(
            self._on_scroll
        )
        self._auto_scroll_enabled = True

    def scroll_to_bottom(self, smooth: bool = True):
        vbar = self.verticalScrollBar()
        target = vbar.maximum()
        self._auto_scroll_enabled = True
        if not smooth:
            vbar.setValue(target)
            return
        self._v_anim.stop()
        self._v_anim.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )
        self._v_anim.setDuration(220)
        self._v_anim.setEndValue(target)
        self._v_anim.start()

    def wheelEvent(self, event):
        vbar = self.verticalScrollBar()
        delta = event.angleDelta().y()
        if delta == 0:
            super().wheelEvent(event)
            return

        step = vbar.singleStep() * 6
        direction = -1 if delta > 0 else 1

        if (
            self._v_anim.state()
            == QPropertyAnimation.State.Running
        ):
            current_target = self._v_anim.endValue()
        else:
            current_target = vbar.value()

        new_target = current_target + (direction * step)
        new_target = max(
            vbar.minimum(),
            min(new_target, vbar.maximum()),
        )

        self._auto_scroll_enabled = (
            new_target >= vbar.maximum() - 80
        )

        self._v_anim.stop()
        self._v_anim.setEasingCurve(
            QEasingCurve.Type.OutCubic
        )
        self._v_anim.setDuration(250)
        self._v_anim.setEndValue(new_target)
        self._v_anim.start()

        self._on_scroll()

    def _on_scroll(self):
        if not hasattr(self, 'cull_timer'):
            self.cull_timer = QTimer(self)
            self.cull_timer.setSingleShot(True)
            self.cull_timer.timeout.connect(
                self.update_culling
            )
        self.cull_timer.start(50)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_scroll()

    def update_culling(self):
        scroll_content = self.widget()
        if not scroll_content:
            return

        layout = scroll_content.layout()
        if not layout:
            return

        scroll_y = self.verticalScrollBar().value()
        viewport_height = self.viewport().height()
        visible_top = scroll_y - (viewport_height * 2.5)
        visible_bottom = scroll_y + (
            viewport_height * 2.5
        )

        count = layout.count()
        last_chat_idx = -1
        for i in range(count - 1, -1, -1):
            w = layout.itemAt(i).widget()
            if w and w.property("is_chat_message"):
                last_chat_idx = i
                break

        for i in range(count):
            w = layout.itemAt(i).widget()
            if w and w.property("is_chat_message"):
                if i == last_chat_idx:
                    self._uncull_widget(w)
                    continue

                geo = w.geometry()
                if (
                    geo.bottom() < visible_top
                    or geo.top() > visible_bottom
                ):
                    self._cull_widget(w)
                else:
                    self._uncull_widget(w)

    def _cull_widget(self, w):
        if w.property("is_culled"):
            return
        if w.height() < 10:
            return

        w.setProperty("is_culled", True)
        w.setFixedHeight(w.height())

        for child in w.children():
            if (
                child.isWidgetType()
                and child.isVisible()
            ):
                child.setProperty(
                    "was_visible", True
                )
                child.setVisible(False)

    def _uncull_widget(self, w):
        if not w.property("is_culled"):
            return

        w.setProperty("is_culled", False)
        w.setMinimumHeight(0)
        w.setMaximumHeight(16777215)

        for child in w.children():
            if (
                child.isWidgetType()
                and child.property("was_visible")
            ):
                child.setVisible(True)
                child.setProperty(
                    "was_visible", False
                )


def build_chat_area(app):
    app.chat_scroll = SmoothScrollArea()
    app.chat_scroll.setWidgetResizable(True)
    app.chat_scroll.setFrameShape(QFrame.Shape.NoFrame)
    app.chat_scroll.setStyleSheet(
        "background: transparent;"
    )

    app.chat_scroll_content = QWidget()
    app.chat_scroll_content.setStyleSheet(
        "background: transparent;"
    )
    app.chat_scroll_layout = QVBoxLayout(
        app.chat_scroll_content
    )
    app.chat_scroll_layout.setAlignment(
        Qt.AlignmentFlag.AlignTop
    )
    app.chat_scroll_layout.setContentsMargins(
        cfg.PAD_LG, cfg.PAD_MD,
        cfg.PAD_LG, cfg.PAD_MD,
    )
    app.chat_scroll_layout.setSpacing(cfg.PAD_MD)

    app.chat_scroll.setWidget(app.chat_scroll_content)

    app.right_layout.addWidget(
        app.chat_scroll, stretch=1
    )


def maybe_scroll_to_bottom(
    app, smooth: bool = True, threshold_px: int = 80
):
    if not hasattr(app, "chat_scroll"):
        return
    vbar = app.chat_scroll.verticalScrollBar()
    if getattr(
        app.chat_scroll, "_auto_scroll_enabled", True
    ) and (vbar.maximum() - vbar.value() <= threshold_px):
        app.chat_scroll.scroll_to_bottom(smooth=smooth)


def _fade_in(widget: QWidget, duration_ms: int = 180):
    eff = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(eff)
    anim = QPropertyAnimation(eff, b"opacity", widget)
    anim.setStartValue(0.0)
    anim.setEndValue(1.0)
    anim.setEasingCurve(QEasingCurve.Type.OutCubic)
    anim.setDuration(duration_ms)
    widget._fade_anim = anim

    def _cleanup():
        try:
            widget.setGraphicsEffect(None)
        except Exception:
            pass
        try:
            delattr(widget, "_fade_anim")
        except Exception:
            pass

    anim.finished.connect(_cleanup)
    anim.start()


def insert_welcome_message(app):
    if getattr(app, "_history_loaded", False):
        return

    app.welcome_frame = QFrame()
    welcome_layout = QVBoxLayout(app.welcome_frame)
    welcome_layout.setAlignment(
        Qt.AlignmentFlag.AlignCenter
    )
    welcome_layout.addSpacing(100)

    title = QLabel("Sulfur")
    title.setFont(
        QFont(
            cfg.FONT_STARTING_TITLE[0],
            cfg.FONT_STARTING_TITLE[1],
            QFont.Weight.Bold,
        )
    )
    title.setStyleSheet(f"color: {cfg.ACCENT};")
    title.setAlignment(Qt.AlignmentFlag.AlignCenter)
    welcome_layout.addWidget(title)

    subtitle = QLabel(
        "Set a target file and start coding together"
    )
    subtitle.setFont(
        QFont(
            cfg.FONT_SUBTITLE[0], cfg.FONT_SUBTITLE[1]
        )
    )
    subtitle.setStyleSheet(f"color: {cfg.TEXT_MUTED};")
    subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
    welcome_layout.addWidget(subtitle)

    app.chat_scroll_layout.addWidget(app.welcome_frame)


def _dismiss_welcome(app):
    if (
        hasattr(app, "welcome_frame")
        and app.welcome_frame
    ):
        app.welcome_frame.deleteLater()
        app.welcome_frame = None


def clear_chat(app):
    while app.chat_scroll_layout.count():
        item = app.chat_scroll_layout.takeAt(0)
        widget = item.widget()
        if widget:
            widget.deleteLater()

    app.welcome_frame = None
    app._history_loaded = False


def reset_chat_area(app):
    clear_chat(app)


def add_user_message(app, text):
    _dismiss_welcome(app)
    row_widget = QWidget()
    row_widget.setProperty("is_chat_message", True)
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 4, 0, 12)

    row_layout.addStretch(1)

    bubble = QFrame()
    bubble.setObjectName("userBubble")
    bubble.setStyleSheet(f"""
        #userBubble {{
            background-color: {cfg.BG_ACTIVE};
            border-radius: 8px;
        }}
    """)
    bubble_layout = QVBoxLayout(bubble)
    bubble_layout.setContentsMargins(16, 10, 16, 10)

    label = QLabel(text)
    label.setFont(
        QFont(cfg.FONT_MAIN[0], cfg.FONT_MAIN[1])
    )
    label.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent;"
    )
    label.setWordWrap(True)
    label.setMaximumWidth(650)
    bubble_layout.addWidget(label)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch(1)
    copy_btn = QPushButton("\U0001f4c4")
    copy_btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    copy_btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: none;
            color: {cfg.TEXT_PRIMARY};
        }}
        QPushButton:hover {{
            background-color: {cfg.BG_BASE};
            border-radius: 4px;
        }}
    """)
    copy_btn.setFixedSize(25, 25)

    def copy_text():
        QApplication.clipboard().setText(text)

    copy_btn.clicked.connect(copy_text)
    btn_layout.addWidget(copy_btn)
    bubble_layout.addLayout(btn_layout)

    row_layout.addWidget(bubble)
    app.chat_scroll_layout.addWidget(row_widget)
    if not getattr(app, "_loading_history", False):
        _fade_in(row_widget)
        QTimer.singleShot(
            0,
            lambda: maybe_scroll_to_bottom(
                app, smooth=True
            ),
        )


def add_ai_message(app, text: str):
    answer_container, answer_label, _, typing_lbl = (
        create_ai_bubble(app, think_mode=False)
    )
    answer_container.setProperty("full_text", text)
    typing_lbl.hide()

    formatter = StreamFormatter()
    result = formatter.process(text, strip_think=False)
    layout = answer_container.layout()

    if result.get("tool_blocks"):
        for block in result["tool_blocks"]:
            card = create_tool_summary_card(
                block, layout
            )
            finalize_tool_summary_card(card)

    render_rich_text(app, answer_container, result["display"])


def create_ai_bubble(app, think_mode: bool):
    row_widget = QWidget()
    row_widget.setProperty("is_chat_message", True)
    row_layout = QHBoxLayout(row_widget)
    row_layout.setContentsMargins(0, 2, 0, cfg.PAD_SM)

    bubble = QFrame()
    bubble.setObjectName("aiBubble")
    bubble.setStyleSheet(f"""
        #aiBubble {{
            background-color: {cfg.BG_CARD};
            border-radius: {cfg.RADIUS_LG}px;
            border: 1px solid {cfg.BORDER_REST};
        }}
    """)
    bubble.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Maximum,
    )
    bubble.setMinimumSize(0, 0)
    bubble_layout = QVBoxLayout(bubble)
    bubble_layout.setContentsMargins(
        cfg.PAD_LG, cfg.PAD_SM,
        cfg.PAD_LG, cfg.PAD_SM,
    )

    think_label = None
    if think_mode:
        think_title = QLabel("Thinking\u2026")
        think_title.setFont(
            QFont(
                cfg.FONT_MONO[0], cfg.FONT_MONO[1]
            )
        )
        think_title.setStyleSheet(
            f"color: {cfg.TEXT_MUTED}; "
            "background: transparent;"
        )
        bubble_layout.addWidget(think_title)

        think_label = QLabel("")
        think_label.setFont(
            QFont(
                cfg.FONT_MONO[0], cfg.FONT_MONO[1]
            )
        )
        think_label.setStyleSheet(
            f"color: {cfg.TEXT_MUTED}; "
            "background: transparent;"
        )
        think_label.setWordWrap(True)
        bubble_layout.addWidget(think_label)

    answer_container = QFrame()
    answer_container.setStyleSheet(
        "background: transparent;"
    )
    answer_layout = QVBoxLayout(answer_container)
    answer_layout.setContentsMargins(0, 0, 0, 0)
    answer_layout.setSpacing(cfg.PAD_SM)
    bubble_layout.addWidget(answer_container)

    typing_lbl = QLabel("Sulfur is typing\u2026")
    typing_lbl.setFont(
        QFont(cfg.FONT_MONO[0], cfg.FONT_MONO[1])
    )
    typing_lbl.setStyleSheet(
        f"color: {cfg.TEXT_MUTED}; "
        "background: transparent;"
    )
    typing_lbl.setWordWrap(True)
    answer_layout.addWidget(typing_lbl)

    answer_label = QLabel("")
    answer_label.setFont(
        QFont(cfg.FONT_MAIN[0], cfg.FONT_MAIN[1])
    )
    answer_label.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent;"
    )
    answer_label.setWordWrap(True)
    answer_label.setSizePolicy(
        QSizePolicy.Policy.Expanding,
        QSizePolicy.Policy.Maximum,
    )
    answer_label.setMinimumSize(0, 0)
    answer_layout.addWidget(answer_label)

    btn_layout = QHBoxLayout()
    btn_layout.addStretch(1)
    copy_btn = QPushButton("\U0001f4c4")
    copy_btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    copy_btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: none;
            color: {cfg.TEXT_PRIMARY};
        }}
        QPushButton:hover {{
            background-color: {cfg.BG_ACTIVE};
            border-radius: 4px;
        }}
    """)
    copy_btn.setFixedSize(25, 25)

    def copy_text():
        text_to_copy = answer_container.property(
            "full_text"
        )
        if not text_to_copy:
            text_to_copy = answer_label.text()
        QApplication.clipboard().setText(
            text_to_copy or ""
        )

    copy_btn.clicked.connect(copy_text)
    btn_layout.addWidget(copy_btn)
    bubble_layout.addLayout(btn_layout)

    bubble.setMinimumWidth(450)
    row_layout.addWidget(bubble, stretch=5)

    row_layout.addStretch(1)

    app.chat_scroll_layout.addWidget(row_widget)
    if not getattr(app, "_loading_history", False):
        _fade_in(row_widget)
        QTimer.singleShot(
            0,
            lambda: maybe_scroll_to_bottom(
                app, smooth=True
            ),
        )

    return (
        answer_container,
        answer_label,
        think_label,
        typing_lbl,
    )


def add_system_message(app, text: str):
    container = QWidget()
    layout = QVBoxLayout(container)
    layout.setContentsMargins(
        0, cfg.PAD_XS, 0, cfg.PAD_XS
    )

    lbl = QLabel(text)
    lbl.setFont(
        QFont(cfg.FONT_SMALL[0], cfg.FONT_SMALL[1])
    )
    lbl.setStyleSheet(
        f"color: {cfg.SYSTEM_MSG}; "
        "background: transparent;"
    )
    lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(lbl)

    app.chat_scroll_layout.addWidget(container)


def _clear_container(container: QFrame):
    layout = container.layout()
    if layout is not None:
        to_remove = []
        for i in range(layout.count()):
            item = layout.itemAt(i)
            widget = item.widget() if item else None
            if widget and not widget.property(
                "is_tool_card"
            ):
                to_remove.append(widget)
        for widget in to_remove:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()


def convert_latex_to_html(text: str) -> str:
    replacements = {
        r'\alpha': '\u03b1',
        r'\beta': '\u03b2',
        r'\gamma': '\u03b3',
        r'\Gamma': '\u0393',
        r'\delta': '\u03b4',
        r'\Delta': '\u0394',
        r'\epsilon': '\u03b5',
        r'\zeta': '\u03b6',
        r'\eta': '\u03b7',
        r'\theta': '\u03b8',
        r'\Theta': '\u0398',
        r'\iota': '\u03b9',
        r'\kappa': '\u03ba',
        r'\lambda': '\u03bb',
        r'\Lambda': '\u039b',
        r'\mu': '\u03bc',
        r'\nu': '\u03bd',
        r'\xi': '\u03be',
        r'\Xi': '\u039e',
        r'\pi': '\u03c0',
        r'\Pi': '\u03a0',
        r'\rho': '\u03c1',
        r'\sigma': '\u03c3',
        r'\Sigma': '\u03a3',
        r'\tau': '\u03c4',
        r'\upsilon': '\u03c5',
        r'\phi': '\u03c6',
        r'\Phi': '\u03a6',
        r'\chi': '\u03c7',
        r'\psi': '\u03c8',
        r'\Psi': '\u03a8',
        r'\omega': '\u03c9',
        r'\Omega': '\u03a9',
        r'\infty': '\u221e',
        r'\sum': '\u2211',
        r'\int': '\u222b',
        r'\approx': '\u2248',
        r'\neq': '\u2260',
        r'\leq': '\u2264',
        r'\geq': '\u2265',
        r'\pm': '\u00b1',
        r'\times': '\u00d7',
        r'\div': '\u00f7',
        r'\cdot': '\u00b7',
        r'\nabla': '\u2207',
        r'\partial': '\u2202',
        r'\propto': '\u221d',
        r'\equiv': '\u2261',
        r'\forall': '\u2200',
        r'\exists': '\u2203',
        r'\in': '\u2208',
        r'\notin': '\u2209',
        r'\subset': '\u2282',
        r'\supset': '\u2283',
        r'\cup': '\u222a',
        r'\cap': '\u2229',
        r'\emptyset': '\u2205',
        r'\rightarrow': '\u2192',
        r'\leftarrow': '\u2190',
        r'\Rightarrow': '\u21d2',
        r'\Leftarrow': '\u21d0',
        r'\{': '{',
        r'\}': '}',
        r'\\': '<br>',
    }

    text = text.replace('<', '&lt;').replace('>', '&gt;')

    for latex, unicode_char in replacements.items():
        text = text.replace(latex, unicode_char)

    text = re.sub(
        r'\^\{([^}]+)\}', r'<sup>\1</sup>', text
    )
    text = re.sub(
        r'\^([a-zA-Z0-9])', r'<sup>\1</sup>', text
    )
    text = re.sub(
        r'_\{([^}]+)\}', r'<sub>\1</sub>', text
    )
    text = re.sub(
        r'_([a-zA-Z0-9])', r'<sub>\1</sub>', text
    )

    return text


def render_rich_text(
    app, container: QFrame, full_text: str
):
    _clear_container(container)

    layout = container.layout()
    if layout is None:
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

    pattern = (
        r'(```.*?```|'
        r'<edit>.*?</edit>|'
        r'<add.*?>.*?</add>|'
        r'<remove>.*?</remove>|'
        r'<think>.*?</think>|'
        r'\$\$.*?\$\$|'
        r'\\\[.*?\\\])'
    )
    parts = re.split(
        pattern, full_text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    for part in parts:
        if not part:
            continue
        part = part.strip('\r\n')
        if not part:
            continue

        if part.startswith('```') and part.endswith('```'):
            code_content = part[3:-3].strip()
            if '\n' in code_content:
                first_line, rest = code_content.split(
                    '\n', 1
                )
                if len(first_line.split()) == 1:
                    code_content = rest

            code_frame = QFrame()
            code_frame.setStyleSheet(f"""
                QFrame {{
                    background-color: {cfg.BG_BASE};
                    border-radius: {cfg.RADIUS_MD}px;
                }}
            """)
            code_layout = QVBoxLayout(code_frame)
            code_layout.setContentsMargins(
                cfg.PAD_MD, cfg.PAD_MD,
                cfg.PAD_MD, cfg.PAD_MD,
            )

            code_lbl = QLabel(code_content)
            code_lbl.setFont(
                QFont(
                    cfg.FONT_CODE[0], cfg.FONT_CODE[1]
                )
            )
            code_lbl.setStyleSheet(
                f"color: {cfg.TEXT_PRIMARY}; "
                "background: transparent;"
            )
            code_lbl.setWordWrap(True)
            code_lbl.setTextInteractionFlags(
                Qt.TextInteractionFlag
                .TextSelectableByMouse
            )
            code_layout.addWidget(code_lbl)

            layout.addWidget(code_frame)

        elif (
            part.lower().startswith('<edit>')
            and part.lower().endswith('</edit>')
        ):
            _render_xml_card(
                layout, "EDIT", part[6:-7].strip(),
                cfg.TAG_EDIT,
            )

        elif (
            part.lower().startswith('<add')
            and part.lower().endswith('</add>')
        ):
            content = re.sub(
                r'^<add.*?>', '', part,
                flags=re.IGNORECASE,
            )
            content = content[:-6].strip()
            _render_xml_card(
                layout, "ADD", content, cfg.TAG_ADD,
            )

        elif (
            part.lower().startswith('<remove>')
            and part.lower().endswith('</remove>')
        ):
            _render_xml_card(
                layout, "REMOVE", part[8:-9].strip(),
                cfg.TAG_REMOVE,
            )

        elif (
            part.lower().startswith('<think>')
            and part.lower().endswith('</think>')
        ):
            think_content = part[7:-8].strip()

            think_frame = QFrame()
            think_frame.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border: 1px solid {cfg.TEXT_MUTED};
                    border-radius: {cfg.RADIUS_MD}px;
                }}
            """)
            think_layout = QVBoxLayout(think_frame)
            think_layout.setContentsMargins(
                cfg.PAD_MD, 6, cfg.PAD_MD, 6
            )

            title_lbl = QLabel(
                "Thinking process..."
            )
            title_lbl.setFont(
                QFont(
                    cfg.FONT_MAIN[0], 12,
                    QFont.Weight.Bold,
                )
            )
            title_lbl.setStyleSheet(
                f"color: {cfg.TEXT_MUTED}; "
                "border: none;"
            )
            think_layout.addWidget(title_lbl)

            content_lbl = QLabel(think_content)
            content_font = QFont(
                cfg.FONT_MAIN[0], 12
            )
            content_font.setItalic(True)
            content_lbl.setFont(content_font)
            content_lbl.setStyleSheet(
                f"color: {cfg.TEXT_MUTED}; "
                "border: none;"
            )
            content_lbl.setWordWrap(True)
            think_layout.addWidget(content_lbl)

            layout.addWidget(think_frame)

        elif (
            part.startswith('$$')
            and part.endswith('$$')
        ) or (
            part.startswith('\\[')
            and part.endswith('\\]')
        ):
            math_content = part[2:-2].strip()
            html_math = convert_latex_to_html(
                math_content
            )

            math_frame = QFrame()
            math_frame.setStyleSheet(f"""
                QFrame {{
                    background: transparent;
                    border-left: 3px solid {cfg.ACCENT};
                    padding-left: 10px;
                }}
            """)
            math_layout = QVBoxLayout(math_frame)
            math_layout.setContentsMargins(
                cfg.PAD_MD, cfg.PAD_SM,
                cfg.PAD_MD, cfg.PAD_SM,
            )

            math_lbl = QLabel(
                f"<div align='center'>"
                f"<i>{html_math}</i></div>"
            )
            math_font = QFont(
                "Georgia", cfg.FONT_MAIN[1] + 1
            )
            math_font.setItalic(True)
            math_lbl.setFont(math_font)
            math_lbl.setStyleSheet(
                f"color: {cfg.TEXT_PRIMARY}; "
                "background: transparent; "
                "border: none;"
            )
            math_lbl.setWordWrap(True)
            math_lbl.setTextInteractionFlags(
                Qt.TextInteractionFlag
                .TextSelectableByMouse
                | Qt.TextInteractionFlag
                .TextBrowserInteraction
            )
            math_layout.addWidget(math_lbl)

            layout.addWidget(math_frame)

        else:
            for line in part.split('\n'):
                line = line.strip()
                if not line:
                    continue

                lbl = QLabel()
                lbl.setWordWrap(True)
                lbl.setSizePolicy(
                    QSizePolicy.Policy.Expanding,
                    QSizePolicy.Policy.Maximum,
                )
                lbl.setMinimumSize(0, 0)
                lbl.setTextInteractionFlags(
                    Qt.TextInteractionFlag
                    .TextSelectableByMouse
                )

                if line.startswith('#'):
                    header_level = len(line) - len(
                        line.lstrip('#')
                    )
                    header_text = (
                        line[header_level:]
                        .strip()
                        .replace('**', '')
                    )
                    lbl.setText(header_text)
                    lbl.setFont(
                        QFont(
                            cfg.FONT_TITLE[0],
                            cfg.FONT_TITLE[1],
                            QFont.Weight.Bold,
                        )
                    )
                    lbl.setStyleSheet(
                        f"color: {cfg.TEXT_PRIMARY}; "
                        "background: transparent;"
                    )
                else:
                    is_bold = False
                    if '**' in line:
                        if (
                            line.startswith('**')
                            or line.startswith('- **')
                            or line.startswith('1. **')
                        ):
                            is_bold = True
                        line = line.replace('**', '')

                    line = re.sub(
                        r'\$(?!\s)([^\$]+?)'
                        r'(?<!\s)\$',
                        lambda m: (
                            "<i>"
                            f"{convert_latex_to_html(
                                m.group(1)
                            )}"
                            "</i>"
                        ),
                        line,
                    )
                    line = re.sub(
                        r'\\\((.*?)\\\)',
                        lambda m: (
                            "<i>"
                            f"{convert_latex_to_html(
                                m.group(1)
                            )}"
                            "</i>"
                        ),
                        line,
                    )

                    lbl.setText(line)
                    font_weight = (
                        QFont.Weight.Bold
                        if is_bold
                        else QFont.Weight.Normal
                    )
                    lbl.setFont(
                        QFont(
                            cfg.FONT_MAIN[0],
                            cfg.FONT_MAIN[1],
                            font_weight,
                        )
                    )
                    lbl.setStyleSheet(
                        f"color: {cfg.TEXT_PRIMARY}; "
                        "background: transparent;"
                    )

                layout.addWidget(lbl)


def _render_xml_card(
    parent_layout, tag_type, content, theme_color
):
    card = QFrame()
    card.setStyleSheet(f"""
        QFrame {{
            background-color: {cfg.BG_SURFACE};
            border-radius: {cfg.RADIUS_MD}px;
            border: 1px solid {theme_color};
        }}
    """)
    card_layout = QVBoxLayout(card)

    header_lbl = QLabel(f"Tool Used: {tag_type}")
    header_lbl.setFont(
        QFont(cfg.FONT_MONO[0], cfg.FONT_MONO[1])
    )
    header_lbl.setStyleSheet(
        f"color: {theme_color}; "
        "border: none; background: transparent;"
    )
    card_layout.addWidget(header_lbl)

    content_lbl = QLabel(content)
    content_lbl.setFont(
        QFont(cfg.FONT_CODE[0], cfg.FONT_CODE[1])
    )
    content_lbl.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "border: none; background: transparent;"
    )
    content_lbl.setWordWrap(True)
    card_layout.addWidget(content_lbl)

    parent_layout.addWidget(card)


def create_tool_summary_card(
    block: dict, parent_layout: QVBoxLayout
) -> QFrame:
    card = QFrame()
    card.setProperty("is_tool_card", True)
    card.setStyleSheet(f"""
        QFrame {{
            background-color: {cfg.BG_SURFACE};
            border: 1px solid {cfg.BORDER_REST};
            border-radius: {cfg.RADIUS_MD}px;
            margin: 2px 0px;
        }}
        QFrame:hover {{
            border-color: {cfg.ACCENT};
        }}
    """)
    card_layout = QVBoxLayout(card)
    card_layout.setContentsMargins(
        cfg.PAD_MD, cfg.PAD_SM,
        cfg.PAD_MD, cfg.PAD_SM,
    )
    card_layout.setSpacing(4)

    header_row = QWidget()
    header_row.setStyleSheet(
        "background: transparent; border: none;"
    )
    header_layout = QHBoxLayout(header_row)
    header_layout.setContentsMargins(0, 0, 0, 0)

    file_lbl = QLabel(
        f"{block.get('file', 'unknown')}"
    )
    file_lbl.setFont(
        QFont(
            cfg.FONT_MAIN[0], cfg.FONT_MAIN[1],
            QFont.Weight.Bold,
        )
    )
    file_lbl.setStyleSheet(
        f"color: {cfg.TEXT_PRIMARY}; "
        "background: transparent; border: none;"
    )
    header_layout.addWidget(file_lbl)
    header_layout.addStretch(1)

    stats_lbl = QLabel()
    stats_lbl.setObjectName("toolStats")
    stats_lbl.setFont(
        QFont(cfg.FONT_MONO[0], cfg.FONT_MONO[1])
    )
    stats_lbl.setStyleSheet(
        "background: transparent; border: none;"
    )
    header_layout.addWidget(stats_lbl)

    toggle_btn = QPushButton("\u25b6")
    toggle_btn.setObjectName("toolToggle")
    toggle_btn.setFixedSize(22, 22)
    toggle_btn.setCursor(
        QCursor(Qt.CursorShape.PointingHandCursor)
    )
    toggle_btn.setStyleSheet(f"""
        QPushButton {{
            background: transparent;
            border: none;
            color: {cfg.TEXT_MUTED};
            font-size: 12px;
        }}
        QPushButton:hover {{
            color: {cfg.ACCENT};
        }}
    """)
    header_layout.addWidget(toggle_btn)
    card_layout.addWidget(header_row)

    content_frame = QFrame()
    content_frame.setObjectName("toolContent")
    content_frame.setVisible(False)
    content_frame.setStyleSheet(f"""
        QFrame#toolContent {{
            background-color: {cfg.BG_BASE};
            border-radius: {cfg.RADIUS_SM}px;
            border: none;
        }}
    """)
    content_layout = QVBoxLayout(content_frame)
    content_layout.setContentsMargins(
        cfg.PAD_SM, cfg.PAD_SM,
        cfg.PAD_SM, cfg.PAD_SM,
    )

    code_lbl = QLabel()
    code_lbl.setObjectName("toolCode")
    code_lbl.setFont(
        QFont(cfg.FONT_CODE[0], cfg.FONT_CODE[1])
    )
    code_lbl.setStyleSheet(
        f"color: {cfg.TEXT_SECONDARY}; "
        "background: transparent; border: none;"
    )
    code_lbl.setWordWrap(True)
    code_lbl.setTextInteractionFlags(
        Qt.TextInteractionFlag.TextSelectableByMouse
    )
    content_layout.addWidget(code_lbl)
    card_layout.addWidget(content_frame)

    def _toggle():
        expanded = content_frame.isVisible()
        content_frame.setVisible(not expanded)
        toggle_btn.setText(
            "\u25bc" if expanded else "\u25b6"
        )

    toggle_btn.clicked.connect(_toggle)

    _refresh_card(card, block)

    parent_layout.insertWidget(0, card)
    return card


def update_tool_summary_card(card: QFrame, block: dict):
    _refresh_card(card, block)


def _refresh_card(card: QFrame, block: dict):
    add_lines = block.get("add_lines", 0)
    remove_lines = block.get("remove_lines", 0)

    stats_lbl = card.findChild(QLabel, "toolStats")
    if stats_lbl:
        parts = []
        if add_lines:
            parts.append(
                '<span style="color:'
                f'{cfg.TAG_ADD};">'
                f'+{add_lines}</span>'
            )
        if remove_lines:
            parts.append(
                '<span style="color:'
                f'{cfg.TAG_REMOVE};">'
                f'-{remove_lines}</span>'
            )
        if parts:
            stats_lbl.setText("  ".join(parts))
        else:
            stats_lbl.setText("")

    content_frame = card.findChild(QFrame, "toolContent")
    if content_frame:
        code_lbl = content_frame.findChild(
            QLabel, "toolCode"
        )
        if code_lbl:
            code_lbl.setText(
                block.get("content", "")
            )


def finalize_tool_summary_card(card: QFrame):
    card.setStyleSheet(f"""
        QFrame {{
            background-color: {cfg.BG_SURFACE};
            border: 1px solid {cfg.BORDER_ACTIVE};
            border-radius: {cfg.RADIUS_MD}px;
            margin: 2px 0px;
        }}
    """)


def load_chat_history(app):
    result = get_memory()
    messages = result.get("messages") or []
    if not messages:
        return

    app._history_loaded = True
    _dismiss_welcome(app)

    app._loading_history = True
    for msg in messages:
        role = (msg or {}).get("role")
        content = (msg or {}).get("content", "")
        if not content:
            continue

        if role == "user":
            add_user_message(app, content)
        elif role == "assistant":
            add_ai_message(app, content)
    app._loading_history = False

    try:
        QApplication.processEvents()
    except Exception:
        pass
    if hasattr(app, "chat_scroll_content"):
        app.chat_scroll_content.adjustSize()
    if hasattr(app, "chat_scroll"):
        app.chat_scroll.update_culling()


def refresh_chat_layout(app):
    QApplication.processEvents()
    if hasattr(app, "chat_scroll_content"):
        app.chat_scroll_content.adjustSize()
