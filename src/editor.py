import os
import re
import sys
import unicodedata
import ctypes
from PyQt6.QtGui import QColor, QFont, QKeySequence, QTextOption, QPainter, QPaintEvent, QWheelEvent
from PyQt6.QtWidgets import QApplication, QPlainTextEdit, QWidget
from PyQt6.QtCore import Qt, QTimer, QRect, QSize, QEasingCurve, QPropertyAnimation
from PyQt6.Qsci import (QsciScintilla, QsciLexerPython, QsciLexerHTML, 
                        QsciLexerJSON, QsciLexerCSS, QsciLexerMarkdown, 
                        QsciLexerBash, QsciLexerCPP, QsciLexerJavaScript, QsciAPIs)

try:
    from spellchecker import SpellChecker
    HAS_SPELLCHECK = True
except ImportError:
    HAS_SPELLCHECK = False
    print("Warning: pyspellchecker not found.")

from .core import BUS, CONFIG

# Dynamic Lexer Mapping
LEXER_MAP = {
    '.html': QsciLexerHTML, '.xml': QsciLexerHTML, '.php': QsciLexerHTML,
    '.json': QsciLexerJSON,
    '.css': QsciLexerCSS,
    '.js': QsciLexerJavaScript, '.ts': QsciLexerJavaScript, '.mjs': QsciLexerJavaScript,
    '.md': QsciLexerMarkdown, '.markdown': QsciLexerMarkdown,
    '.sh': QsciLexerBash, '.bash': QsciLexerBash, '.zsh': QsciLexerBash,
    '.cpp': QsciLexerCPP, '.c': QsciLexerCPP, '.h': QsciLexerCPP, '.java': QsciLexerCPP, '.cs': QsciLexerCPP,
    '.py': QsciLexerPython, '.pyw': QsciLexerPython
}

# Arabic = 0x01, Hebrew = 0x0D, Farsi/Persian = 0x29, Urdu = 0x20, Syriac = 0x5A
RTL_LANG_IDS = {0x01, 0x0D, 0x29, 0x20, 0x5A}


class _RTLLineNumberArea(QWidget):
    """Line number gutter for the RTL overlay, displayed on the right side."""
    def __init__(self, editor):
        super().__init__(editor)
        self._editor = editor
    
    def sizeHint(self):
        return QSize(self._editor.line_number_area_width(), 0)
    
    def paintEvent(self, event):
        self._editor.line_number_area_paint(event)


class RTLPlainTextEdit(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.setWordWrapMode(QTextOption.WrapMode.NoWrap)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._show_line_numbers = True
        self._zoom_size = 12
        
        opt = QTextOption()
        opt.setAlignment(Qt.AlignmentFlag.AlignLeading)
        opt.setTextDirection(Qt.LayoutDirection.RightToLeft)
        opt.setWrapMode(QTextOption.WrapMode.NoWrap)
        self.document().setDefaultTextOption(opt)
        
        self._line_number_area = _RTLLineNumberArea(self)
        self.blockCountChanged.connect(self._update_line_number_area_width)
        self.updateRequest.connect(self._update_line_number_area)
        self._update_line_number_area_width()
        
        self._scroll_animation = QPropertyAnimation(self.verticalScrollBar(), b"value")
        self._scroll_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._scroll_animation.setDuration(300)
        self._target_scroll_value = 0
        
        self.textChanged.connect(self._scroll_to_cursor_rtl)
    
    # --- Line numbers (RIGHT side) ---
    
    def set_show_line_numbers(self, show):
        """Toggle line number visibility."""
        self._show_line_numbers = show
        self._line_number_area.setVisible(show)
        self._update_line_number_area_width()
    
    def line_number_area_width(self):
        if not self._show_line_numbers:
            return 0
        digits = max(1, len(str(self.blockCount())))
        return 10 + self.fontMetrics().horizontalAdvance('9') * digits + 10
    
    def _update_line_number_area_width(self, _=0):
        w = self.line_number_area_width()
        self.setViewportMargins(w, 0, 0, 0)
    
    def _update_line_number_area(self, rect, dy):
        if not self._show_line_numbers:
            return
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_number_area_width()
    
    def resizeEvent(self, event):
        super().resizeEvent(event)
        if not self._show_line_numbers:
            return
        cr = self.contentsRect()
        w = self.line_number_area_width()
        self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), w, cr.height()))
    
    def _sync_line_number_font(self):
        """Update line number area font to match the main editor font."""
        self._line_number_area.setFont(self.font())
    
    def line_number_area_paint(self, event):
        if not self._show_line_numbers:
            return
        theme = CONFIG["theme"]
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor(theme["sidebar"]))
        painter.setFont(self.font())
        painter.setPen(QColor(theme["comment"]))
        
        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    5, top, self._line_number_area.width() - 10, 
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignCenter, number
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1
        painter.end()
    
    # --- Zoom + Scroll ---
    
    def wheelEvent(self, event):
        """Handle Ctrl+Scroll to zoom, otherwise smooth scroll."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            self._zoom_size += (1 if delta > 0 else -1)
            self._zoom_size = max(6, min(72, self._zoom_size))
            font = self.font()
            font.setPixelSize(self._zoom_size)
            self.setFont(font)
            self._sync_line_number_font()
            self._update_line_number_area_width()
            if self._show_line_numbers:
                cr = self.contentsRect()
                w = self.line_number_area_width()
                self._line_number_area.setGeometry(QRect(cr.left(), cr.top(), w, cr.height()))
                self._line_number_area.update()
            
            parent_editor = self.parent()
            if parent_editor and hasattr(parent_editor, 'zoomTo'):
                default_size = max(10, CONFIG["editor"].get("font_size", 12))
                zoom_delta = self._zoom_size - default_size
                parent_editor.zoomTo(zoom_delta)
            event.accept()
            return
        
        delta = event.angleDelta().y()
        if delta != 0:
            sb = self.verticalScrollBar()
            if self._scroll_animation.state() == QPropertyAnimation.State.Running:
                current = self._target_scroll_value
            else:
                current = sb.value()
            
            step = int(delta * 0.8)
            self._target_scroll_value = max(sb.minimum(), min(sb.maximum(), current - step))
            
            self._scroll_animation.stop()
            self._scroll_animation.setStartValue(sb.value())
            self._scroll_animation.setEndValue(self._target_scroll_value)
            self._scroll_animation.start()
            event.accept()
            return
        
        super().wheelEvent(event)
    
    def _scroll_to_cursor_rtl(self):
        """Auto-scroll to keep cursor visible."""
        QTimer.singleShot(0, self._do_rtl_scroll)
    
    def _do_rtl_scroll(self):
        """Let Qt handle cursor tracking natively with RTL scrollbar."""
        self.ensureCursorVisible()

class ZenithEditor(QsciScintilla):
    SPELLCHECK_INDICATOR = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.setAttribute(Qt.WidgetAttribute.WA_InputMethodEnabled, True)
        
        # --- CORE ENGINE SETTINGS ---
        self.setUtf8(True)
        self.setEolMode(QsciScintilla.EolMode.EolUnix)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # --- ENABLE DRAG AND DROP ---
        self.setAcceptDrops(True)

        # --- FIX: CLEAR SHORTCUT ---
        self.SendScintilla(QsciScintilla.SCI_CLEARCMDKEY, ord('T') | (QsciScintilla.SCMOD_CTRL << 16))
        self.SendScintilla(QsciScintilla.SCI_CLEARCMDKEY, ord('F') | (QsciScintilla.SCMOD_CTRL << 16))
        self.SendScintilla(QsciScintilla.SCI_CLEARCMDKEY, ord('G') | (QsciScintilla.SCMOD_CTRL << 16))

        # --- HORIZONTAL SCROLLBAR ---
        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 1) 
        self.SendScintilla(QsciScintilla.SCI_SETSCROLLWIDTH, 1)
        self.SendScintilla(QsciScintilla.SCI_SETSCROLLWIDTHTRACKING, 1)

        self.current_lexer = None
        
        # --- SPELLCHECK SETUP ---
        if HAS_SPELLCHECK:
            self.spell_checker = SpellChecker()
            self.spell_timer = QTimer()
            self.spell_timer.setSingleShot(True)
            self.spell_timer.setInterval(500) 
            self.spell_timer.timeout.connect(self.run_realtime_spellcheck)

        self.SendScintilla(QsciScintilla.SCI_INDICSETSTYLE, self.SPELLCHECK_INDICATOR, QsciScintilla.INDIC_SQUIGGLE)
        self.SendScintilla(QsciScintilla.SCI_INDICSETFORE, self.SPELLCHECK_INDICATOR, QColor("#ff5555")) 

        # Initial Setup
        self.update_appearance() 
        self.set_lexer_from_filename("untitled.txt") 

        # --- AUTO COMPLETE SETUP ---
        if CONFIG["editor"].get("enable_autocomplete", True):
            self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsAll)
            self.setAutoCompletionThreshold(1)
            self.setAutoCompletionCaseSensitivity(False)
            self.setAutoCompletionReplaceWord(True)
            self.setAutoCompletionUseSingle(QsciScintilla.AutoCompletionUseSingle.AcusExplicit)
            self.SendScintilla(QsciScintilla.SCI_STYLESETBACK, 32, 0x2e1e1e) 
            self.SendScintilla(QsciScintilla.SCI_STYLESETFORE, 32, 0xf4d6cd) 
        else:
            self.setAutoCompletionSource(QsciScintilla.AutoCompletionSource.AcsNone)

        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        
        # Signals
        self.textChanged.connect(self.emit_change)
        if HAS_SPELLCHECK:
            self.textChanged.connect(self.trigger_spellcheck)
        self.linesChanged.connect(self.update_margin_width)
        self.textChanged.connect(self._detect_text_direction)
        
        # Track current layout direction
        self._is_rtl = False
        
        # --- RTL OVERLAY (Qt's native BiDi text engine) ---
        self._rtl_overlay = RTLPlainTextEdit(self)
        self._rtl_overlay.hide()
        self._syncing = False  # Prevent sync loops
        self._rtl_overlay.textChanged.connect(self._on_rtl_overlay_changed)
        self._update_rtl_overlay_style()

    # --- DRAG & DROP SUPPORT (FIXED FOR VIDEOS) ---
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            valid_exts = [
                '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', # Images
                '.mp4', '.mov', '.avi', '.mkv', '.webm'                   # Videos
            ]
            for url in urls:
                file_path = url.toLocalFile()
                if any(file_path.lower().endswith(ext) for ext in valid_exts):
                    event.accept()
                    return
        super().dragEnterEvent(event)

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            valid_exts = [
                '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp',
                '.mp4', '.mov', '.avi', '.mkv', '.webm'
            ]
            for url in urls:
                file_path = url.toLocalFile()
                if any(file_path.lower().endswith(ext) for ext in valid_exts):
                    import os
                    filename = os.path.basename(file_path)
                    self.insert(f'![{filename}]({file_path})')
                    event.accept()
                    return
        super().dropEvent(event)

    def keyPressEvent(self, event):
        self._check_keyboard_layout()
        
        if self._is_rtl and self._rtl_overlay.isVisible():
            return  
        
        if event.matches(QKeySequence.StandardKey.Paste):
            clipboard = QApplication.clipboard()
            mime_data = clipboard.mimeData()
            if mime_data.hasUrls():
                urls = mime_data.urls()
                valid_exts = [
                    '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp',
                    '.mp4', '.mov', '.avi', '.mkv', '.webm'
                ]
                for url in urls:
                    file_path = url.toLocalFile()
                    if any(file_path.lower().endswith(ext) for ext in valid_exts):
                        import os
                        filename = os.path.basename(file_path)
                        self.insert(f'![{filename}]({file_path})')
                        return

        if event.key() == Qt.Key.Key_T and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            win = self.window()
            if hasattr(win, "create_new_explorer_item"):
                win.create_new_explorer_item()
            return

        if self.isListActive():
            if event.key() == Qt.Key.Key_Tab:
                self.SendScintilla(QsciScintilla.SCI_AUTOCCOMPLETE)
                return
            elif event.key() in [Qt.Key.Key_Return, Qt.Key.Key_Enter]:
                self.cancelList()
                self.SendScintilla(QsciScintilla.SCI_NEWLINE)
                return

        mapping = {'(': ')', '{': '}', '[': ']', '"': '"', "'": "'"}
        if event.text() in mapping:
            self.insert(mapping[event.text()])
            super().keyPressEvent(event)
            return

        super().keyPressEvent(event)

    def set_lexer_from_filename(self, filename):
        if not CONFIG["editor"].get("enable_syntax_highlighting", True):
            self.setLexer(None)
            self.current_lexer = None
            return

        ext = os.path.splitext(filename)[1].lower()
        LexerClass = LEXER_MAP.get(ext)
        theme = CONFIG["theme"]
        font = self.font()

        if not LexerClass:
            self.setLexer(None)
            self.current_lexer = None
            self.setPaper(QColor(theme["bg"]))
            self.setColor(QColor(theme["fg"]))
            return

        self.current_lexer = LexerClass()
        self.current_lexer.setDefaultFont(font)
        self.setLexer(self.current_lexer)
        self.apply_lexer_styles(theme)
        self.setup_apis()

    def apply_lexer_styles(self, theme):
        if not self.current_lexer: return
        colors = {
            "bg": QColor(theme["bg"]), "fg": QColor(theme["fg"]),
            "kw": QColor(theme["keyword"]), "fn": QColor(theme["function"]),
            "str": QColor(theme["string"]), "cmt": QColor(theme["comment"])
        }
        
        l = self.current_lexer
        l.setPaper(colors["bg"])
        l.setColor(colors["fg"], -1)

        if isinstance(l, QsciLexerJSON):
            l.setColor(colors["fg"], 0); l.setColor(colors["kw"], 1); l.setColor(colors["str"], 2)
            l.setColor(colors["fn"], 4); l.setColor(colors["cmt"], 6); l.setColor(colors["kw"], 11)
        elif isinstance(l, QsciLexerPython):
            l.setColor(colors["fg"], 0); l.setColor(colors["cmt"], 1); l.setColor(colors["kw"], 5)
            l.setColor(colors["str"], 4); l.setColor(colors["str"], 3); l.setColor(colors["fn"], 8); l.setColor(colors["fn"], 9)

    def setup_apis(self):
        if not self.current_lexer or not CONFIG["editor"].get("enable_autocomplete", True): return
        self.api = QsciAPIs(self.current_lexer)
        for kw in ["def", "class", "import", "return", "print", "true", "false", "function", "var", "let", "const"]: 
            self.api.add(kw)
        self.api.prepare()

    def emit_change(self):
        BUS.editor_text_changed.emit("changed")
        self.SendScintilla(QsciScintilla.SCI_SETSCROLLWIDTH, 1)

    def update_margin_width(self):
        if not CONFIG["editor"]["show_line_numbers"]:
            self.setMarginWidth(0, 0); return
        digits = len(str(self.lines()))
        self.setMarginWidth(0, "8" * digits + "88") 

    def update_appearance(self):
        safe_size = max(10, CONFIG["editor"].get("font_size", 12))
        font_family = CONFIG["editor"]["font_family"]
        font = QFont(font_family, safe_size)
        self.setFont(font)
        
        if self.current_lexer and CONFIG["editor"].get("enable_syntax_highlighting", True):
            self.current_lexer.setDefaultFont(font)
            self.apply_lexer_styles(CONFIG["theme"])
        else:
            self.setPaper(QColor(CONFIG["theme"]["bg"]))
            self.setColor(QColor(CONFIG["theme"]["fg"]))
        
        margin_font = QFont(font_family, safe_size - 2) 
        self.setMarginsFont(margin_font)
        
        is_blinking = CONFIG["editor"].get("cursor_blinking", True)
        self.SendScintilla(QsciScintilla.SCI_SETCARETPERIOD, 500 if is_blinking else 0)

        theme = CONFIG["theme"]
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginsBackgroundColor(QColor(theme["sidebar"]))
        self.setMarginsForegroundColor(QColor(theme["comment"]))
        self.setCaretForegroundColor(QColor(theme["fg"]))
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor(theme["selection"]))
        self.setMatchedBraceBackgroundColor(QColor(theme["selection"]))
        self.setMatchedBraceForegroundColor(QColor(theme["function"]))
        
        self.setCallTipsBackgroundColor(QColor(theme["sidebar"]))
        self.setCallTipsForegroundColor(QColor(theme["fg"]))
        self.update_margin_width()
        
        if hasattr(self, '_rtl_overlay'):
            self._update_rtl_overlay_style()

    def _check_keyboard_layout(self):
        """Detect the current Windows keyboard layout and switch to RTL if needed."""
        try:
            hwnd = ctypes.windll.user32.GetForegroundWindow()
            thread_id = ctypes.windll.user32.GetWindowThreadProcessId(hwnd, None)
            layout_id = ctypes.windll.user32.GetKeyboardLayout(thread_id)
            lang_id = layout_id & 0xFF
            is_rtl_keyboard = lang_id in RTL_LANG_IDS
            
            if is_rtl_keyboard and not self._is_rtl:
                self._activate_rtl_overlay()
            elif not is_rtl_keyboard and self._is_rtl:
                self._deactivate_rtl_overlay()
        except Exception:
            pass
    
    def _update_rtl_overlay_style(self):
        """Style the RTL overlay to match the editor theme."""
        theme = CONFIG["theme"]
        safe_size = max(10, CONFIG["editor"].get("font_size", 12))
        font_family = CONFIG["editor"].get("font_family", "Consolas")
        self._rtl_overlay.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {theme['bg']};
                color: {theme['fg']};
                border: none;
                selection-background-color: {theme['selection']};
            }}
        """)
        font = QFont(font_family, safe_size)
        font.setPixelSize(safe_size)
        self._rtl_overlay.setFont(font)
        self._rtl_overlay._zoom_size = safe_size
        show_lines = CONFIG["editor"].get("show_line_numbers", True)
        self._rtl_overlay.set_show_line_numbers(show_lines)
    
    def _activate_rtl_overlay(self):
        """Switch to RTL mode: show Qt overlay on top of Scintilla."""
        self._is_rtl = True
        self._update_rtl_overlay_style()
        current_zoom = self.SendScintilla(QsciScintilla.SCI_GETZOOM)
        base_size = max(10, CONFIG["editor"].get("font_size", 12))
        synced_size = max(6, base_size + current_zoom)
        font = self._rtl_overlay.font()
        font.setPixelSize(synced_size)
        self._rtl_overlay.setFont(font)
        self._rtl_overlay._zoom_size = synced_size
        self._syncing = True
        self._rtl_overlay.setPlainText(self.text())
        self._syncing = False
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setMarginWidth(0, 0)
        self._rtl_overlay.setGeometry(0, 0, self.width(), self.height())
        self._rtl_overlay.show()
        self._rtl_overlay.setFocus()
        cursor = self._rtl_overlay.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        self._rtl_overlay.setTextCursor(cursor)
    
    def _deactivate_rtl_overlay(self):
        """Switch back to LTR mode: sync text back and hide overlay."""
        self._is_rtl = False
        base_size = max(10, CONFIG["editor"].get("font_size", 12))
        zoom_delta = self._rtl_overlay._zoom_size - base_size
        self.zoomTo(zoom_delta)
        self._syncing = True
        overlay_text = self._rtl_overlay.toPlainText()
        self.setText(overlay_text)
        self._syncing = False
        self._rtl_overlay.hide()
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.update_margin_width()
        self.setFocus()
        self.SendScintilla(QsciScintilla.SCI_DOCUMENTEND)
    
    def _on_rtl_overlay_changed(self):
        """Sync RTL overlay text back to Scintilla buffer (for save/status)."""
        if self._syncing:
            return
        self._syncing = True
        self.setText(self._rtl_overlay.toPlainText())
        self._syncing = False
    
    def resizeEvent(self, event):
        """Keep RTL overlay sized correctly."""
        super().resizeEvent(event)
        if self._rtl_overlay.isVisible():
            self._rtl_overlay.setGeometry(0, 0, self.width(), self.height())
    
    def _apply_rtl_layout(self):
        """Switch to RTL: mirror layout, move line numbers to right, scroll to caret."""
        self.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.SendScintilla(QsciScintilla.SCI_SETXOFFSET, 0)
        self.SendScintilla(QsciScintilla.SCI_SCROLLCARET)
        self.SendScintilla(QsciScintilla.SCI_COLOURISE, 0, -1)
        if hasattr(self, 'viewport'):
            self.viewport().update()
    
    def _apply_ltr_layout(self):
        """Switch to LTR: reset layout to default, scroll to caret."""
        self.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        self.SendScintilla(QsciScintilla.SCI_SETXOFFSET, 0)
        self.SendScintilla(QsciScintilla.SCI_SCROLLCARET)
        self.SendScintilla(QsciScintilla.SCI_COLOURISE, 0, -1)
        if hasattr(self, 'viewport'):
            self.viewport().update()
    
    def _detect_text_direction(self):
        """Detect if the current text is predominantly RTL and activate overlay."""
        if self._syncing:
            return
        text = self.text()
        if not text:
            if self._is_rtl:
                self._deactivate_rtl_overlay()
            return
        sample = text[:200]
        rtl_count = 0
        ltr_count = 0
        for ch in sample:
            bidi = unicodedata.bidirectional(ch)
            if bidi in ('R', 'AL', 'AN'):
                rtl_count += 1
            elif bidi == 'L':
                ltr_count += 1
        is_rtl = rtl_count > ltr_count and rtl_count > 0
        if is_rtl and not self._is_rtl:
            self._activate_rtl_overlay()
        elif not is_rtl and self._is_rtl:
            self._deactivate_rtl_overlay()

    def trigger_spellcheck(self):
        self.spell_timer.start()

    def run_realtime_spellcheck(self):
        if not HAS_SPELLCHECK: return
        self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, self.SPELLCHECK_INDICATOR)
        self.SendScintilla(QsciScintilla.SCI_INDICATORCLEARRANGE, 0, self.length())

        text_content = self.text()
        if not text_content: return
        text_bytes = text_content.encode('utf-8')
        words_iter = re.finditer(rb'\b[a-zA-Z]{3,}\b', text_bytes)
        
        for match in words_iter:
            word_bytes = match.group()
            try:
                word_str = word_bytes.decode('utf-8')
                if word_str.lower() not in self.spell_checker:
                    start_byte = match.start()
                    length_byte = match.end() - start_byte
                    self.SendScintilla(QsciScintilla.SCI_SETINDICATORCURRENT, self.SPELLCHECK_INDICATOR)
                    self.SendScintilla(QsciScintilla.SCI_INDICATORFILLRANGE, start_byte, length_byte)
            except: pass
