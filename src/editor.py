import os
import re
from PyQt6.QtGui import QColor, QFont
from PyQt6.QtCore import Qt, QTimer
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

class ZenithEditor(QsciScintilla):
    SPELLCHECK_INDICATOR = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        
        # --- CORE ENGINE SETTINGS ---
        self.setUtf8(True)
        self.setEolMode(QsciScintilla.EolMode.EolUnix)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setIndentationGuides(True)
        self.setWrapMode(QsciScintilla.WrapMode.WrapNone)

        # --- FIX: CLEAR SHORTCUT ---
        # Clear 'Ctrl+T' in Scintilla so our app can use it for "New Tab"
        self.SendScintilla(QsciScintilla.SCI_CLEARCMDKEY, ord('T') | (QsciScintilla.SCMOD_CTRL << 16))
        # Clear 'Ctrl+F' and 'Ctrl+G' so Main Window handles them
        self.SendScintilla(QsciScintilla.SCI_CLEARCMDKEY, ord('F') | (QsciScintilla.SCMOD_CTRL << 16))
        self.SendScintilla(QsciScintilla.SCI_CLEARCMDKEY, ord('G') | (QsciScintilla.SCMOD_CTRL << 16))

        # --- PERFORMANCE ---
        self.SendScintilla(QsciScintilla.SCI_SETHSCROLLBAR, 0)
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

    def keyPressEvent(self, event):
        # Direct Shortcut Injection for Tab Creation
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
        # Optimized: Do not send full text content
        BUS.editor_text_changed.emit("changed")

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