import sys
import os
import threading
import queue
from typing import Any

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QFrame, QPushButton,
)
from PyQt6.QtCore import QTimer, Qt, QPropertyAnimation, QEvent, QPoint
from PyQt6.QtGui import QFontDatabase, QFont, QIcon, QCursor

from src.modules.more_modules.token_counter import (
    get_current_context_usage,
)
from src.modules.more_modules.chat_stream import chat_stream
from src.modules.more_modules.edits import check_edits, apply_edits
from src.modules.profiles import get_profile, get_think_regex
import src.modules.configurations as cfg
import src.modules.session_manager as session_manager

from ui.title_bar import build_title_bar
from ui.chat_area import (
    build_chat_area,
    insert_welcome_message,
    load_chat_history,
    add_user_message,
    create_ai_bubble,
    add_system_message,
    render_rich_text,
    maybe_scroll_to_bottom,
    create_tool_summary_card,
    update_tool_summary_card,
    finalize_tool_summary_card,
)
from ui.input_area import build_input_area
from ui.sidebar import build_sidebar, refresh_session_list
from ui.settings import open_settings
from ui.stream_formatter import StreamFormatter
import ui.chat_area as chat_area


class App(QMainWindow):
    def __init__(self):
        super().__init__()

        for font_file in cfg.CUSTOM_FONT_PATH:
            font_path = os.path.join(cfg.BASE_DIR, font_file)
            if os.path.exists(font_path):
                QFontDatabase.addApplicationFont(font_path)

        self.setWindowTitle("Sulfur")
        self.resize(1200, 750)
        self.setWindowFlag(
            Qt.WindowType.FramelessWindowHint, True
        )

        self.setWindowOpacity(0.0)
        self._opacity_anim = QPropertyAnimation(
            self, b"windowOpacity"
        )
        self._opacity_anim.setDuration(250)

        icon_path = os.path.join(
            cfg.BASE_DIR, "ui/images/logo.png"
        )
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {cfg.BG_BASE};
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 12px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {cfg.SCROLLBAR_BTN};
                min-height: 30px;
                border-radius: 6px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {cfg.SCROLLBAR_BTN_HOVER};
            }}
            QScrollBar::add-line:vertical,
            QScrollBar::sub-line:vertical {{
                height: 0px;
                background: none;
            }}
            QScrollBar::add-page:vertical,
            QScrollBar::sub-page:vertical {{
                background: none;
            }}
        """)

        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.root_layout = QVBoxLayout(self.central_widget)
        self.root_layout.setContentsMargins(0, 0, 0, 0)
        self.root_layout.setSpacing(0)

        self.content_widget = QWidget()
        self.content_widget.setStyleSheet(
            "background: transparent;"
        )
        self.root_layout.addWidget(
            self.content_widget, stretch=1
        )

        self.main_layout = QHBoxLayout(self.content_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.right_panel = QWidget()
        self.right_panel.setStyleSheet(
            f"background-color: {cfg.BG_BASE};"
        )
        self.right_layout = QVBoxLayout(self.right_panel)
        self.right_layout.setContentsMargins(0, 0, 0, 0)
        self.right_layout.setSpacing(0)
        self.main_layout.addWidget(
            self.right_panel, stretch=1
        )

        self._stream_queue = queue.Queue()
        self._is_streaming = False
        self._current_answer_box = None
        self._current_think_box = None
        self._current_answer_text = ""
        self._current_think_text = ""
        profile = get_profile("generic")
        self._formatter = StreamFormatter(
            think_regex=get_think_regex(profile)
        )
        self._tool_cards: list = []
        self._json_tool_cards: list = []

        build_title_bar(self)
        build_sidebar(self)
        build_chat_area(self)
        build_input_area(self)

        self.add_system_message = lambda text: (
            add_system_message(self, text)
        )

        self.queue_timer = QTimer(self)
        self.queue_timer.timeout.connect(self._poll_queue)

        self.context_timer = QTimer(self)
        self.context_timer.timeout.connect(
            self._update_context_label
        )
        self.context_timer.start(1000)

        QTimer.singleShot(100, self._init_sessions)

    def _update_context_label(self):
        if not hasattr(self, 'ctx_usage_label'):
            return

        total_ctx = cfg.NUM_CTX
        used_ctx = get_current_context_usage()

        self.ctx_usage_label.setText(
            f"Context: {used_ctx}/{total_ctx}"
        )

    def _fade_to(
        self, target_opacity, finished_callback=None
    ):
        self._opacity_anim.stop()
        try:
            self._opacity_anim.finished.disconnect()
        except Exception:
            pass
        if finished_callback:
            self._opacity_anim.finished.connect(
                finished_callback
            )
        self._opacity_anim.setStartValue(
            self.windowOpacity()
        )
        self._opacity_anim.setEndValue(target_opacity)
        self._opacity_anim.start()

    def showMinimized(self):
        self._fade_to(0.0, super().showMinimized)

    def showEvent(self, event):
        super().showEvent(event)
        self._fade_to(0.95)

    def changeEvent(self, event):
        if event.type() == QEvent.Type.WindowStateChange:
            if not self.isMinimized():
                self._fade_to(0.95)
        super().changeEvent(event)

    def _init_sessions(self):
        sessions = session_manager.list_sessions()
        if sessions:
            most_recent = sessions[0]
            session_manager.set_active_session_id(
                most_recent["id"]
            )
            from ui.sidebar import _apply_session_to_ui

            _apply_session_to_ui(self, most_recent)
        else:
            s = session_manager.create_session(
                name="Session 1"
            )
            session_manager.set_active_session_id(s["id"])
            insert_welcome_message(self)
        refresh_session_list(self)

    def on_send(self):
        if self._is_streaming:
            return

        user_text = (
            self.message_input.text().strip()
            if hasattr(self.message_input, 'text')
            else self.message_input.toPlainText().strip()
        )
        if not user_text:
            return

        self.message_input.clear()
        self._set_ui_locked(True)

        add_user_message(self, user_text)

        profile = get_profile(cfg.MODEL_TYPE)
        self._formatter = StreamFormatter(
            think_regex=get_think_regex(profile)
        )
        self._current_profile = profile
        self._tool_cards = []
        self._json_tool_cards = []

        think_mode = (
            self.think_mode_cb.isChecked()
            if hasattr(self, 'think_mode_cb')
            else False
        )

        (
            answer_container,
            answer_box,
            think_box,
            typing_lbl,
        ) = create_ai_bubble(self, think_mode)
        self._current_answer_container = answer_container
        self._current_answer_box = answer_box
        self._current_think_box = think_box
        self._current_typing_lbl = typing_lbl
        self._current_answer_text = ""
        self._current_think_text = ""
        self._got_first_token = False

        def stream_worker():
            try:
                for event in chat_stream(
                    user_text, think_mode=think_mode
                ):
                    self._stream_queue.put(event)
            except ValueError as exc:
                self._stream_queue.put({
                    'type': 'error',
                    'content': str(exc),
                })
            except Exception as exc:
                self._stream_queue.put({
                    'type': 'error',
                    'content': (
                        f'Unexpected error: {exc}'
                    ),
                })

        threading.Thread(
            target=stream_worker, daemon=True
        ).start()

        self.queue_timer.start(50)

    def _poll_queue(self):
        try:
            while True:
                event = self._stream_queue.get_nowait()
                etype = event.get('type')

                if etype == 'think':
                    self._current_think_text += (
                        event.get('content', '')
                    )
                    if self._current_think_box:
                        self._current_think_box.setText(
                            self._current_think_text
                        )
                        self._current_think_box.adjustSize(
                        )
                    maybe_scroll_to_bottom(
                        self, smooth=True
                    )

                elif etype == 'answer':
                    self._current_answer_text += (
                        event.get('content', '')
                    )
                    if self._current_answer_box:
                        if not self._got_first_token:
                            self._got_first_token = True
                            if getattr(
                                self,
                                "_current_typing_lbl",
                                None,
                            ):
                                self._current_typing_lbl.hide(
                                )

                        result = self._formatter.process(
                            self._current_answer_text
                        )
                        self._current_answer_box.setText(
                            result['display']
                        )
                        self._current_answer_box.adjustSize(
                        )

                        self._sync_tool_cards(
                            result['tool_blocks']
                        )
                    maybe_scroll_to_bottom(
                        self, smooth=True
                    )

                elif etype == 'error':
                    self._current_answer_text += (
                        "\n[Error: "
                        f"{event.get('content', '')}]"
                    )
                    if self._current_answer_box:
                        self._current_answer_box.setText(
                            self._current_answer_text
                        )
                    self._set_ui_locked(False)
                    self.queue_timer.stop()
                    return

                elif etype == 'tool_result':
                    block = event.get('content', {})
                    if block:
                        self._add_json_tool_card(block)

                elif etype == 'done':
                    if hasattr(self, 'tps_label'):
                        self.tps_label.setText(
                            "TPS: "
                            f"{event.get('tps', 0.0):.1f}"
                        )

                    self._set_ui_locked(False)

                    if getattr(
                        self, "_current_think_box", None
                    ):
                        self._current_think_box.hide()
                        self._current_think_box.setParent(
                            None
                        )
                        self._current_think_box.deleteLater(
                        )
                        self._current_think_box = None
                    if getattr(
                        self, "_current_answer_box", None
                    ):
                        self._current_answer_box.hide()
                        self._current_answer_box.setParent(
                            None
                        )
                        self._current_answer_box.deleteLater(
                        )
                        self._current_answer_box = None
                    if getattr(
                        self, "_current_typing_lbl", None
                    ):
                        self._current_typing_lbl.hide()
                        self._current_typing_lbl.setParent(
                            None
                        )
                        self._current_typing_lbl.deleteLater(
                        )
                        self._current_typing_lbl = None

                    profile = getattr(
                        self, "_current_profile", None
                    )
                    if (
                        profile
                        and profile.supports_think_mode
                    ):
                        clean_think = (
                            self._current_think_text
                            .replace(
                                profile.think_open, ""
                            )
                            .replace(
                                profile.think_close, ""
                            )
                            .strip()
                        )
                    else:
                        clean_think = (
                            self._current_think_text.strip()
                        )

                    if clean_think:
                        result = self._formatter.process(
                            self._current_answer_text,
                            strip_think=False,
                        )
                        clean_answer = result['display']
                        if (
                            profile
                            and profile.supports_think_mode
                        ):
                            final_combined_text = (
                                f"{profile.think_open}\n"
                                f"{clean_think}\n"
                                f"{profile.think_close}\n\n"
                                f"{clean_answer}"
                            )
                        else:
                            final_combined_text = (
                                clean_answer
                            )
                    else:
                        result = self._formatter.process(
                            self._current_answer_text,
                            strip_think=False,
                        )
                        final_combined_text = (
                            result['display']
                        )

                    if getattr(
                        self,
                        "_current_answer_container",
                        None,
                    ):
                        render_rich_text(
                            self,
                            self._current_answer_container,
                            final_combined_text,
                        )

                    self._sync_tool_cards(
                        result['tool_blocks']
                    )
                    for card in self._tool_cards:
                        finalize_tool_summary_card(card)

                    for card in self._json_tool_cards:
                        finalize_tool_summary_card(card)

                    json_tool_blocks = event.get(
                        'tool_blocks', []
                    )
                    if json_tool_blocks:
                        edited_files = set()
                        for b in json_tool_blocks:
                            p = b.get("path", "")
                            if p and os.path.exists(p):
                                edited_files.add(
                                    os.path.basename(p)
                                )
                        if edited_files:
                            add_system_message(
                                self,
                                "Automatically changed: "
                                f"{', '.join(
                                    sorted(edited_files)
                                )}",
                            )

                    if hasattr(
                        self, "chat_scroll_content"
                    ):
                        self.chat_scroll_content.adjustSize(
                        )
                    maybe_scroll_to_bottom(
                        self, smooth=False
                    )

                    self._apply_edits_if_any()
                    self.queue_timer.stop()
                    return

        except queue.Empty:
            pass

    def _apply_edits_if_any(self):
        if not self._current_answer_text:
            return

        result = check_edits(self._current_answer_text)
        if not result.get('has_edits'):
            return

        proposals = result.get('proposals', [])

        auto_apply = getattr(
            cfg, "AUTO_APPLY_EDITS", False
        )
        if auto_apply:
            outcome = apply_edits(proposals)
            if outcome.get('success'):
                add_system_message(
                    self,
                    "Auto-applied "
                    f"{len(proposals)} edit(s) -- "
                    f"{outcome.get('message', 'done')}",
                )
            else:
                add_system_message(
                    self,
                    "Auto-apply failed: "
                    f"{outcome.get(
                        'error', 'Unknown error'
                    )}",
                )
            return

        add_system_message(
            self,
            f"{len(proposals)} edit(s) detected "
            "review below:",
        )

        for i, proposal in enumerate(proposals):
            self._render_proposal_card(
                i + 1, len(proposals), proposal
            )

    def _render_proposal_card(
        self,
        index: int,
        total: int,
        proposal: dict[str, Any],
    ):
        ptype = proposal.get('type', '')

        if ptype == 'edit':
            preview = (
                "FIND:\n"
                f"{proposal.get('find', '')}\n"
                "REPLACE WITH:\n"
                f"{proposal.get('replace', '')}"
            )
        elif ptype == 'remove':
            preview = (
                "REMOVE:\n"
                f"{proposal.get('remove', '')}"
            )
        elif ptype == 'add':
            line_info = ""
            if proposal.get('before'):
                line_info = (
                    "  (before: "
                    f"{proposal['before'][:60]})"
                )
            elif proposal.get('after'):
                line_info = (
                    "  (after: "
                    f"{proposal['after'][:60]})"
                )
            preview = (
                f"ADD{line_info}:\n"
                f"{proposal.get('add', '')}"
            )
        elif ptype == 'full_rewrite':
            code = proposal.get('code', '')
            preview = (
                "FULL REWRITE -- first 300 chars:\n"
                f"{code[:300]}"
                f"{'...' if len(code) > 300 else ''}"
            )
        else:
            preview = str(proposal)

        card = QFrame()
        card.setObjectName("proposalCard")

        card.setStyleSheet(f"""
            QFrame#proposalCard {{
                background-color: {cfg.BG_CARD};
                border: 1px solid {cfg.ACCENT};
                border-radius: {cfg.RADIUS_MD}px;
                margin: 5px;
            }}
        """)
        card_layout = QVBoxLayout(card)

        if hasattr(self, 'chat_scroll_layout'):
            self.chat_scroll_layout.addWidget(card)

        header_label = QLabel(
            f"Edit {index}/{total}  .  "
            f"{ptype.upper().replace('_', ' ')}"
        )
        header_label.setFont(
            QFont(
                cfg.FONT_MAIN[0], cfg.FONT_MAIN[1],
                QFont.Weight.Bold,
            )
        )
        header_label.setStyleSheet(
            f"color: {cfg.TEXT_PRIMARY};"
        )
        card_layout.addWidget(header_label)

        preview_label = QLabel(preview)
        preview_label.setFont(
            QFont(
                cfg.FONT_MONO[0], cfg.FONT_MONO[1]
            )
        )
        preview_label.setStyleSheet(
            f"color: {cfg.TEXT_SECONDARY};"
        )
        preview_label.setWordWrap(True)
        card_layout.addWidget(preview_label)

        btn_row = QWidget()
        btn_layout = QHBoxLayout(btn_row)
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setAlignment(Qt.AlignmentFlag.AlignLeft)
        card_layout.addWidget(btn_row)

        apply_btn = QPushButton("\u2714  Apply")
        apply_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {cfg.ACCENT};
                color: {cfg.TEXT_PRIMARY};
                border-radius: 4px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {cfg.ACCENT_DARK};
            }}
        """)

        skip_btn = QPushButton("\u2716  Skip")
        skip_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {cfg.TEXT_MUTED};
                border: 1px solid {cfg.BORDER_REST};
                border-radius: 4px;
                padding: 4px 12px;
            }}
            QPushButton:hover {{
                background-color: {cfg.BG_ACTIVE};
            }}
        """)

        btn_layout.addWidget(apply_btn)
        btn_layout.addWidget(skip_btn)

        def on_apply():
            outcome = apply_edits([proposal])
            card.deleteLater()

            if hasattr(chat_area, 'refresh_chat_layout'):
                chat_area.refresh_chat_layout(self)

            if outcome.get('success'):
                fname = os.path.basename(
                    proposal.get('path', 'target file')
                )
                add_system_message(
                    self,
                    "Applied: "
                    f"{ptype.upper().replace('_', ' ')} "
                    f"in {fname}",
                )
            else:
                add_system_message(
                    self,
                    "Failed: "
                    f"{outcome.get(
                        'error', 'Unknown error'
                    )}",
                )

            QApplication.processEvents()

        def on_skip():
            card.deleteLater()
            if hasattr(chat_area, 'refresh_chat_layout'):
                chat_area.refresh_chat_layout(self)

        apply_btn.clicked.connect(on_apply)
        skip_btn.clicked.connect(on_skip)

    def _sync_tool_cards(self, tool_blocks: list):
        container = getattr(
            self, "_current_answer_container", None
        )
        if not container:
            return
        layout = container.layout()
        if not layout:
            return

        while len(self._tool_cards) < len(tool_blocks):
            block = tool_blocks[len(self._tool_cards)]
            card = create_tool_summary_card(
                block, layout
            )
            self._tool_cards.append(card)

        for i, block in enumerate(tool_blocks):
            if i < len(self._tool_cards):
                update_tool_summary_card(
                    self._tool_cards[i], block
                )

    def _add_json_tool_card(self, block: dict):
        container = getattr(
            self, "_current_answer_container", None
        )
        if not container:
            return
        layout = container.layout()
        if not layout:
            return
        card = create_tool_summary_card(block, layout)
        self._json_tool_cards.append(card)

    def _set_ui_locked(self, locked: bool):
        self._is_streaming = locked
        state = not locked

        if hasattr(self, 'send_btn'):
            self.send_btn.setEnabled(state)
        if hasattr(self, 'message_input'):
            self.message_input.setEnabled(state)
        if hasattr(self, 'settings_btn'):
            self.settings_btn.setEnabled(state)

    _RESIZE_MARGIN = 6

    def _resize_edge(self, pos: QPoint):
        r = self.rect()
        edge = 0
        if pos.x() <= r.left() + self._RESIZE_MARGIN:
            edge |= 1
        elif pos.x() >= r.right() - self._RESIZE_MARGIN:
            edge |= 2
        if pos.y() <= r.top() + self._RESIZE_MARGIN:
            edge |= 4
        elif pos.y() >= r.bottom() - self._RESIZE_MARGIN:
            edge |= 8
        return edge

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            edge = self._resize_edge(event.pos())
            if edge:
                self._resize_edge_flags = edge
                self._resize_start_geo = self.geometry()
                self._resize_start_pos = (
                    event.globalPosition().toPoint()
                )
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if hasattr(self, '_resize_edge_flags'):
            if self._resize_edge_flags:
                delta = (
                    event.globalPosition().toPoint()
                    - self._resize_start_pos
                )
                geo = self._resize_start_geo
                x, y, w, h = (
                    geo.x(), geo.y(),
                    geo.width(), geo.height(),
                )
                edge = self._resize_edge_flags

                if edge & 1:
                    x += delta.x()
                    w -= delta.x()
                elif edge & 2:
                    w += delta.x()
                if edge & 4:
                    y += delta.y()
                    h -= delta.y()
                elif edge & 8:
                    h += delta.y()

                w = max(400, w)
                h = max(300, h)
                self.setGeometry(x, y, w, h)
                event.accept()
                return

        edge = self._resize_edge(event.pos())
        if edge == 1 or edge == 2:
            self.setCursor(
                QCursor(Qt.CursorShape.SizeHorCursor)
            )
        elif edge == 4 or edge == 8:
            self.setCursor(
                QCursor(Qt.CursorShape.SizeVerCursor)
            )
        elif edge == (1 | 4) or edge == (2 | 8):
            self.setCursor(
                QCursor(Qt.CursorShape.SizeFDiagCursor)
            )
        elif edge == (2 | 4) or edge == (1 | 8):
            self.setCursor(
                QCursor(Qt.CursorShape.SizeBDiagCursor)
            )
        else:
            self.setCursor(
                QCursor(Qt.CursorShape.ArrowCursor)
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if hasattr(self, '_resize_edge_flags'):
            del self._resize_edge_flags
        super().mouseReleaseEvent(event)

    def closeEvent(self, event):
        from src.modules.model_inference import cleanup

        cleanup()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = App()
    window.show()
    sys.exit(app.exec())
