import os
import time
import re
import datetime 
import shutil 
from PyQt6.QtCore import QUrl
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import (QToolTip, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QFrame, QLabel, QListWidget, QLineEdit, 
                             QToolBar, QFileDialog, QDialog, QMenu, QToolButton, 
                             QStyle, QFormLayout, QDialogButtonBox, QTabWidget, QTableWidget, 
                             QTableWidgetItem, QHeaderView, QAbstractItemView, QComboBox, 
                             QApplication, QCheckBox, QListWidgetItem, QScrollBar, 
                             QPushButton, QInputDialog, QMessageBox,
                             QFontComboBox, QListView, QGraphicsDropShadowEffect, QGraphicsOpacityEffect)
from PyQt6.QtGui import (QAction, QFont, QKeySequence, QIcon, QColor, QPainter, QPen, 
                         QPixmap, QPolygon, QShortcut, QMouseEvent, QFontDatabase, QIntValidator)
from PyQt6.QtCore import (Qt, QSize, QPointF, QPropertyAnimation, QEasingCurve, QPoint, QRect, 
                          QEvent, QTimer, QObject, QModelIndex, QVariantAnimation, 
                          QParallelAnimationGroup, QThread, pyqtSignal)
from PyQt6.QtGui import QMouseEvent, QCursor
from .editor import ZenithEditor
from .core import BUS, CONFIG, save_config, THEME_PALETTES


# --- GLOBAL ICON CACHE ---
class GlobalIconCache:
    _cache = {}

    @classmethod
    def get_icon(cls, shape, color, size=24):
        key = (shape, color, size)
        if key not in cls._cache:
            cls._cache[key] = cls._create_icon_impl(shape, color, size)
        return cls._cache[key]

    @staticmethod
    def _create_icon_impl(shape="x", color="#6c7086", size=24):
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        pen_width = 2
        if "arrow" in shape: pen_width = 2.5
        if "search" in shape: pen_width = 2.0
            
        pen = QPen(QColor(color))
        pen.setWidthF(pen_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        
        m = int(size * 0.28)
        if m < 4: m = 4
        c = size // 2
        
        if shape == "x":
            painter.drawLine(m, m, size-m, size-m)
            painter.drawLine(size-m, m, m, size-m)
        elif shape == "plus":
            painter.drawLine(c, m, c, size-m)
            painter.drawLine(m, c, size-m, c) 
        elif shape == "minus":
            painter.drawLine(m, c, size-m, c)
        
        # --- SEARCH ICON FIX ---
        elif shape == "search":
            glass_size = int(size * 0.35)
            cx = int(size * 0.40)
            cy = int(size * 0.40)
            painter.drawEllipse(QPoint(cx, cy), glass_size, glass_size)
            
            # Handle math
            offset = int(glass_size * 0.7)
            handle_start_x = cx + offset
            handle_start_y = cy + offset
            handle_end_x = size - m + 1
            handle_end_y = size - m + 1
            painter.drawLine(handle_start_x, handle_start_y, handle_end_x, handle_end_y)

        elif shape == "rename_box":
            box_rect = QRect(3, 5, size - 7, size - 10)
            painter.drawRoundedRect(box_rect, 2, 2)
            
            cursor_pen = QPen(QColor(color))
            cursor_pen.setWidth(2)
            painter.setPen(cursor_pen)
            
            cx_cursor = size // 2
            top_y = 9
            bot_y = size - 9
            
            painter.drawLine(cx_cursor, top_y, cx_cursor, bot_y)
            cap_size = 2
            painter.drawLine(cx_cursor - cap_size, top_y, cx_cursor + cap_size, top_y)
            painter.drawLine(cx_cursor - cap_size, bot_y, cx_cursor + cap_size, bot_y)

        elif shape == "arrow_down":
             path = QPolygon([QPoint(m, c-3), QPoint(c, size-m-1), QPoint(size-m, c-3)])
             painter.drawPolyline(path)
        elif shape == "arrow_up":
             path = QPolygon([QPoint(m, c+3), QPoint(c, m+1), QPoint(size-m, c+3)])
             painter.drawPolyline(path)
             
        painter.end()
        return QIcon(pixmap)

def create_icon(shape="x", color="#6c7086", size=24):
    return GlobalIconCache.get_icon(shape, color, size)

class VideoPauseOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
            center = self.rect().center()
            radius = 35
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.drawEllipse(center, radius, radius)
            
            cx, cy = center.x(), center.y()
            p1 = QPoint(cx - 10, cy - 14)
            p2 = QPoint(cx - 10, cy + 14)
            p3 = QPoint(cx + 16, cy)
            
            path = QPolygon([p1, p2, p3])
            painter.setBrush(QColor(255, 255, 255, 240))
            painter.drawPolygon(path)
        finally:
            painter.end()
            
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.hide()

    def paintEvent(self, event):
        painter = QPainter(self)
        try:
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            painter.fillRect(self.rect(), QColor(0, 0, 0, 100))
            
            center = self.rect().center()
            radius = 35
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(0, 0, 0, 150))
            painter.drawEllipse(center, radius, radius)
            
            cx, cy = center.x(), center.y()
            p1 = QPoint(cx - 10, cy - 14)
            p2 = QPoint(cx - 10, cy + 14)
            p3 = QPoint(cx + 16, cy)
            
            path = QPolygon([p1, p2, p3])
            painter.setBrush(QColor(255, 255, 255, 240))
            painter.drawPolygon(path)
        finally:
            painter.end()
            
# --- FILE LOADER THREAD ---
class FileLoadWorker(QThread):
    finished_loading = pyqtSignal(str, str, bool) 

    def __init__(self, filepath, encoding):
        super().__init__()
        self.filepath = filepath
        self.encoding = encoding

    def run(self):
        try:
            with open(self.filepath, 'r', encoding=self.encoding) as f:
                content = f.read()
            self.finished_loading.emit(self.filepath, content, True)
        except Exception as e:
            self.finished_loading.emit(self.filepath, str(e), False)

# --- CUSTOM WIDGETS ---
class CleanHoverListView(QListView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setUniformItemSizes(True)
        self.setLayoutMode(QListView.LayoutMode.Batched)
        self.viewport().installEventFilter(self)

    def showEvent(self, event):
        if self.window(): self.window().installEventFilter(self)
        super().showEvent(event)

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.Leave:
            if source is self.viewport() or source is self.window():
                global_pos = QCursor.pos()
                if not self.geometry().contains(self.mapFromGlobal(global_pos)):
                    self.clearSelection()
                    if self.selectionModel(): self.selectionModel().clearCurrentIndex()
                    self.viewport().update()
        return super().eventFilter(source, event)
      
class SidebarListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
    def leaveEvent(self, event):
        self.viewport().update()
        super().leaveEvent(event)         

# --- ANIMATED OVERLAY BARS (FIND / GOTO) ---
class EditorOverlayBar(QFrame):
    """Base class for floating bars over the editor"""
    def __init__(self, parent_editor):
        super().__init__(parent_editor)
        self.editor = parent_editor
        self.setFixedHeight(50) 
        self.setFixedWidth(400)
        self.hide()
        
        # Style
        self.setObjectName("OverlayBar")
        bg = CONFIG['theme']['sidebar']
        border = CONFIG['theme']['selection']
        fg = CONFIG['theme']['fg']
        self.setStyleSheet(f"""
            #OverlayBar {{
                background-color: {bg};
                border: 1px solid {border};
                border-top: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QLabel {{ color: {fg}; font-weight: 500; font-size: 13px; border: none; background: transparent; }}
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {border};
                border-radius: 4px;
                color: {fg};
                padding: 4px 8px;
                selection-background-color: {CONFIG['theme']['function']};
            }}
            QLineEdit:focus {{ border: 1px solid {CONFIG['theme']['function']}; }}
        """)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 0, 0, 80))
        shadow.setOffset(0, 4)
        self.setGraphicsEffect(shadow)
        
        # Animation
        self.anim = QPropertyAnimation(self, b"pos")
        self.anim.setDuration(250)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        

    def update_position(self):
        parent_width = self.parent().width()
        if self.isVisible():
            self.move(parent_width - self.width() - 25, 0)

    def show_animated(self):
        if self.isVisible(): 
            self.update_limits_if_needed() 
            if hasattr(self, 'input'):
                self.input.setFocus() 
                self.input.selectAll()
            return
        
        parent_width = self.parent().width()
        
        start_x = parent_width - self.width() - 25
        start_y = -self.height() - 10
        self.move(start_x, start_y)
        
        self.update_limits_if_needed()
        self.show()
        self.raise_()
        
        end_pos = QPoint(start_x, 0)
        
        self.anim.stop() 
        self.anim.setStartValue(QPoint(start_x, start_y))
        self.anim.setEndValue(end_pos)
        
        try: self.anim.finished.disconnect()
        except: pass
        
        self.anim.start()
        if hasattr(self, 'input'):
            self.input.setFocus()
            self.input.selectAll()
            
    def update_theme(self):
        """Refreshes the look of the bar based on current CONFIG."""
        bg = CONFIG['theme']['sidebar']
        border = CONFIG['theme']['selection']
        fg = CONFIG['theme']['fg']
        func = CONFIG['theme']['function']
        
        self.setStyleSheet(f"""
            #OverlayBar {{
                background-color: {bg};
                border: 1px solid {border};
                border-top: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QLabel {{ color: {fg}; font-weight: 500; font-size: 13px; border: none; background: transparent; }}
            QLineEdit {{
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid {border};
                border-radius: 4px;
                color: {fg};
                padding: 4px 8px;
                selection-background-color: {func};
            }}
            QLineEdit:focus {{ border: 1px solid {func}; }}
            QPushButton {{ background: {bg}; border: 1px solid {border}; color: {fg}; border-radius: 4px; padding: 4px 10px; }}
            QPushButton:hover {{ background: {border}; border: 1px solid {func}; }}
        """)
        
        if hasattr(self, 'icon'):
            self.icon.setPixmap(create_icon("search", CONFIG['theme']['comment'], 16).pixmap(16, 16))
        
        for child in self.findChildren(QToolButton):
            if child is not getattr(self, 'btn_close', None):
                 pass
                 
        if hasattr(self, 'btn_close'):
             self.btn_close.setIcon(create_icon("x", CONFIG['theme']['fg'], 14))

        self.style().unpolish(self)
        self.style().polish(self)
        
    def hide_animated(self):
        if not self.isVisible(): return
        
        current_pos = self.pos()
        end_pos = QPoint(current_pos.x(), -self.height() - 10)
        
        self.anim.stop()
        self.anim.setStartValue(current_pos)
        self.anim.setEndValue(end_pos)
        
        try: self.anim.finished.disconnect()
        except: pass
        
        self.anim.finished.connect(self.hide)
        self.anim.start()
        self.editor.setFocus()

    def update_limits_if_needed(self):
        pass

class FindBar(EditorOverlayBar):
    def __init__(self, parent_editor):
        super().__init__(parent_editor)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(8)
        
        self.icon = QLabel()
        self.icon.setPixmap(create_icon("search", CONFIG['theme']['comment'], 16).pixmap(16, 16))
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Find...")
        self.input.textChanged.connect(self.find_text)
        self.input.returnPressed.connect(self.find_next)
        
        btn_style = f"""
            QToolButton {{ background: transparent; border: 1px solid transparent; border-radius: 4px; padding: 4px; }}
            QToolButton:hover {{ background: {CONFIG['theme']['selection']}; border: 1px solid {CONFIG['theme']['function']}; }}
            QToolButton:pressed {{ background: {CONFIG['theme']['function']}; }}
        """
        
        self.btn_prev = QToolButton()
        self.btn_prev.setIcon(create_icon("arrow_up", CONFIG['theme']['fg'], 16))
        self.btn_prev.setToolTip("Previous Match")
        self.btn_prev.setStyleSheet(btn_style)
        self.btn_prev.clicked.connect(self.find_prev)
        
        self.btn_next = QToolButton()
        self.btn_next.setIcon(create_icon("arrow_down", CONFIG['theme']['fg'], 16))
        self.btn_next.setToolTip("Next Match")
        self.btn_next.setStyleSheet(btn_style)
        self.btn_next.clicked.connect(self.find_next)
        
        self.btn_close = QToolButton()
        self.btn_close.setIcon(create_icon("x", CONFIG['theme']['fg'], 14))
        self.btn_close.setToolTip("Close")
        self.btn_close.setStyleSheet(btn_style)
        self.btn_close.clicked.connect(self.hide_animated)
        
        layout.addWidget(self.icon)
        layout.addWidget(self.input)
        layout.addWidget(self.btn_prev)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_close)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_animated()
            return
        super().keyPressEvent(event)
        
    def find_text(self):
        text = self.input.text()
        if not text: return
        self.editor.findFirst(text, False, False, False, True, True)
        
    def find_next(self):
        text = self.input.text()
        if not text: return
        self.editor.findFirst(text, False, False, False, True, True)
        
    def find_prev(self):
        text = self.input.text()
        if not text: return
        
        if self.editor.hasSelectedText():
            lf, if_, _, _ = self.editor.getSelection()
            if lf != -1:
                self.editor.setCursorPosition(lf, if_)
        
        self.editor.findFirst(text, False, False, False, True, False)

class GoToBar(EditorOverlayBar):
    def __init__(self, parent_editor):
        super().__init__(parent_editor)
        self.setFixedWidth(280)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 5, 15, 5)
        layout.setSpacing(10)
        
        lbl = QLabel("Go to Line:")
        
        self.input = QLineEdit()
        self.input.setValidator(QIntValidator(1, 999999))
        self.input.setPlaceholderText("Line #")
        self.input.returnPressed.connect(self.go_to_line)
        
        btn_style = f"""
            QPushButton {{ background: {CONFIG['theme']['sidebar']}; border: 1px solid {CONFIG['theme']['selection']}; color: {CONFIG['theme']['fg']}; border-radius: 4px; padding: 4px 10px; }}
            QPushButton:hover {{ background: {CONFIG['theme']['selection']}; border: 1px solid {CONFIG['theme']['function']}; }}
        """
        
        self.btn_go = QPushButton("Go")
        self.btn_go.setStyleSheet(btn_style)
        self.btn_go.clicked.connect(self.go_to_line)
        
        self.btn_close = QToolButton()
        self.btn_close.setIcon(create_icon("x", CONFIG['theme']['fg'], 14))
        self.btn_close.setStyleSheet(f"QToolButton {{ background: transparent; border: none; border-radius: 4px; }} QToolButton:hover {{ background: #ff5555; }}")
        self.btn_close.clicked.connect(self.hide_animated)
        
        layout.addWidget(lbl)
        layout.addWidget(self.input)
        layout.addWidget(self.btn_go)
        layout.addWidget(self.btn_close)

    def update_limits_if_needed(self):
        max_lines = self.editor.lines()
        self.input.setPlaceholderText(f"1 - {max_lines}")
        if self.input.validator():
            self.input.validator().setTop(max_lines)

    def show_animated(self):
        self.input.clear()
        super().show_animated()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_animated()
            return
        super().keyPressEvent(event)

    def go_to_line(self):
        try:
            line = int(self.input.text())
            self.editor.setCursorPosition(line - 1, 0)
            self.editor.setFocus()
            self.hide_animated()
        except ValueError:
            pass

class GlobalSearchBar(EditorOverlayBar):
    def __init__(self, parent_editor, main_window_ref):
        super().__init__(parent_editor)
        self.main_window = main_window_ref
        
        self.setFixedHeight(50) 
        self.setFixedWidth(500) 
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # --- Top Section (Input) ---
        top_container = QWidget()
        top_container.setFixedHeight(50)
        
        top_container.setStyleSheet(f"""
            background-color: {CONFIG['theme']['sidebar']};
            border-bottom: 1px solid {CONFIG['theme']['selection']};
            border-top-left-radius: 8px;
            border-top-right-radius: 8px;
        """)
        
        top_layout = QHBoxLayout(top_container)
        top_layout.setContentsMargins(10, 0, 10, 0)
        top_layout.setSpacing(10)

        self.icon = QLabel()
        self.icon.setPixmap(create_icon("search", CONFIG['theme']['comment'], 16).pixmap(16, 16))
        
        self.input = QLineEdit()
        self.input.setPlaceholderText("Search all open files...")
        
        bg_color = "rgba(255, 255, 255, 0.05)"
        border_col = CONFIG['theme']['selection']
        fg_col = CONFIG['theme']['fg']
        focus_col = CONFIG['theme']['function']
        
        self.input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_color};
                color: {fg_col};
                border: 1px solid {border_col};
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 13px;
            }}
            QLineEdit:focus {{
                border: 1px solid {focus_col};
            }}
        """)
        
        self.input.textChanged.connect(self.perform_search)
        self.input.returnPressed.connect(self.activate_current_result)
        
        self.btn_close = QToolButton()
        self.btn_close.setIcon(create_icon("x", CONFIG['theme']['fg'], 14))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.setStyleSheet(f"QToolButton {{ background: transparent; border: none; border-radius: 4px; padding: 4px; }} QToolButton:hover {{ background: #ff5555; }}")
        self.btn_close.clicked.connect(self.hide_animated)
        
        top_layout.addWidget(self.icon)
        top_layout.addWidget(self.input)
        top_layout.addWidget(self.btn_close)
        
        layout.addWidget(top_container)
        
        # --- Bottom Section (Results List) ---
        self.results_list = QListWidget()
        self.results_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.results_list.itemClicked.connect(self.on_item_clicked)
        self.results_list.hide() 
        
        self.results_list.setStyleSheet(f"""
            QListWidget {{ 
                background-color: {CONFIG['theme']['bg']}; 
                border: none; 
                outline: none;
                border-bottom-left-radius: 8px;
                border-bottom-right-radius: 8px;
            }}
            QListWidget::item {{ 
                padding: 8px; 
                border-bottom: 1px solid {CONFIG['theme']['selection']};
                color: {CONFIG['theme']['fg']};
            }}
            QListWidget::item:selected {{ 
                background-color: {CONFIG['theme']['selection']}; 
                color: white;
                border-left: 3px solid {CONFIG['theme']['function']};
            }}
            QListWidget::item:hover:!selected {{
                background-color: {CONFIG['theme']['sidebar']};
            }}
            {SCROLLBAR_CSS}
        """)
        apply_smooth_scroll(self.results_list)
        
        layout.addWidget(self.results_list)

    def show_animated(self):
        self.input.clear()
        self.results_list.clear()
        self.results_list.hide()
        self.setFixedHeight(50)
        super().show_animated()

    def perform_search(self, text):
        self.results_list.clear()
        
        if not text: 
            self.animate_height(50) 
            self.results_list.hide()
            return
        
        search_term = text.lower()
        
        if self.main_window.last_active_filename:
            self.main_window.file_states[self.main_window.last_active_filename] = self.main_window.editor.text()
            
        found_count = 0
        for filename, content in self.main_window.file_states.items():
            if not content: continue
            if found_count >= 50: break

            lines = content.split('\n')
            for i, line in enumerate(lines):
                if search_term in line.lower():
                    stripped = line.strip()
                    if len(stripped) > 60: stripped = stripped[:60] + "..."
                    
                    display_text = f"{os.path.basename(filename)}:{i+1}  |  {stripped}"
                    item = QListWidgetItem(display_text)
                    item.setData(Qt.ItemDataRole.UserRole, (filename, i))
                    self.results_list.addItem(item)
                    
                    found_count += 1
                    if found_count >= 50: break 
        
        item_count = self.results_list.count()
        if item_count > 0:
            self.results_list.setCurrentRow(0)
            self.results_list.show()
            
            # --- FIX: Scrollbar Policy & Exact Height ---
            
            if item_count <= 6:
                self.results_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            else:
                self.results_list.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
            
            row_height = self.results_list.sizeHintForRow(0)
            if row_height <= 0: row_height = 36 
            
            visible_items = min(item_count, 6)
            list_height = visible_items * row_height
            
            total_height = 50 + list_height
            
            self.animate_height(total_height)
        else:
            self.animate_height(50)
            self.results_list.hide()

    def animate_height(self, target_h):
        if self.height() == target_h: return
        
        if hasattr(self, 'h_anim'): self.h_anim.stop()
        
        self.setMinimumHeight(0)
        self.setMaximumHeight(16777215) 
              
        self.h_anim = QPropertyAnimation(self, b"geometry")
        self.h_anim.setDuration(200)
        self.h_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        start_rect = self.geometry()
        end_rect = QRect(start_rect)
        end_rect.setHeight(target_h)
        
        self.h_anim.setStartValue(start_rect)
        self.h_anim.setEndValue(end_rect)
        self.h_anim.start()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.hide_animated()
            return
        if self.results_list.isVisible() and self.results_list.count() > 0:
            if event.key() == Qt.Key.Key_Down:
                idx = self.results_list.currentRow()
                if idx < self.results_list.count() - 1: self.results_list.setCurrentRow(idx + 1)
                return
            elif event.key() == Qt.Key.Key_Up:
                idx = self.results_list.currentRow()
                if idx > 0: self.results_list.setCurrentRow(idx - 1)
                return
        super().keyPressEvent(event)

    def activate_current_result(self):
        item = self.results_list.currentItem()
        if item: self.on_item_clicked(item)

    def on_item_clicked(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            filename, line_index = data
            self.main_window.open_file_at_line(filename, line_index)
            self.hide_animated()

# --- SMOOTH SCROLL DELEGATE (Helpers) ---
class SmoothScrollDelegate(QObject):
    def __init__(self, target_widget):
        super().__init__(target_widget)
        self.widget = target_widget
        self.scroll_bar = None
        if hasattr(target_widget, "verticalScrollBar"):
            self.scroll_bar = target_widget.verticalScrollBar()
        elif isinstance(target_widget, QAbstractItemView):
            self.scroll_bar = target_widget.verticalScrollBar()
        if self.scroll_bar:
            if hasattr(self.widget, 'viewport'):
                 self.widget.viewport().installEventFilter(self)
            else:
                 self.widget.installEventFilter(self)
        self.current_scroll = 0  
        self.target_scroll = 0
        self.timer = QTimer()
        self.timer.setInterval(12) 
        self.timer.timeout.connect(self.update_scroll)
        if isinstance(target_widget, ZenithEditor): self.step_size = 6 
        else: self.step_size = 60

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.Wheel and self.scroll_bar and self.scroll_bar.maximum() > 0:
            delta = event.angleDelta().y()
            if delta == 0: return False
            if not self.timer.isActive():
                self.current_scroll = self.scroll_bar.value()
                self.target_scroll = self.current_scroll
            steps = delta / 120.0
            self.target_scroll -= (steps * self.step_size)
            self.target_scroll = max(self.scroll_bar.minimum(), min(self.target_scroll, self.scroll_bar.maximum()))
            if not self.timer.isActive(): self.timer.start()
            return True
        elif event.type() == QEvent.Type.Leave:
             if self.timer.isActive(): self.timer.stop()
        return False

    def update_scroll(self):
        diff = self.target_scroll - self.current_scroll
        if abs(diff) < 1:
            self.current_scroll = self.target_scroll
            self.scroll_bar.setValue(int(self.current_scroll))
            self.timer.stop()
        else:
            self.current_scroll += diff * 0.15
            self.scroll_bar.setValue(int(self.current_scroll))
        if isinstance(self.widget, QAbstractItemView) and hasattr(self.widget, 'viewport'):
            viewport = self.widget.viewport()
            if viewport.underMouse():
                local_pos = viewport.mapFromGlobal(QCursor.pos())
                if viewport.rect().contains(local_pos):
                    mouse_event = QMouseEvent(QEvent.Type.MouseMove, QPointF(local_pos), Qt.MouseButton.NoButton, Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier)
                    QApplication.sendEvent(viewport, mouse_event)

def apply_smooth_scroll(widget):
    if isinstance(widget, QComboBox):
        widget.setMaxVisibleItems(100)
        widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        return
    target = widget
    if hasattr(widget, "view") and isinstance(widget.view(), QAbstractItemView): target = widget.view()
    target._scroller = SmoothScrollDelegate(target)

def colorize_icon(icon, color):
    pixmap = icon.pixmap(QSize(24, 24))
    painter = QPainter(pixmap)
    painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
    painter.fillRect(pixmap.rect(), color)
    painter.end()
    return QIcon(pixmap)

# --- SCROLLBAR CSS ---
SCROLLBAR_CSS = f"""
    QAbstractScrollArea::corner {{ background: transparent; border: none; }}
    QScrollBar:vertical {{
        border: none;
        background: {CONFIG['theme']['sidebar']};
        width: 14px;
        margin: 0px; 
        border-left: 1px solid {CONFIG['theme']['selection']};
    }}
    QScrollBar::handle:vertical {{
        background: {CONFIG['theme']['function']};
        min-height: 20px;
        border-radius: 4px; 
        margin: 2px 3px 2px 3px; 
    }}
    QScrollBar::handle:vertical:hover {{ background: #8caaee; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
    QScrollBar::up-arrow:vertical, QScrollBar::down-arrow:vertical {{
        height: 0px; width: 0px; background: none; border: none; image: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    QScrollBar:horizontal {{
        border: none;
        background: {CONFIG['theme']['sidebar']};
        height: 14px;
        margin: 0px;
        border-top: 1px solid {CONFIG['theme']['selection']};
    }}
    QScrollBar::handle:horizontal {{
        background: {CONFIG['theme']['function']};
        min-width: 20px;
        border-radius: 4px;
        margin: 3px 2px 3px 2px;
    }}
    QScrollBar::handle:horizontal:hover {{ background: #8caaee; }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
    QScrollBar::left-arrow:horizontal, QScrollBar::right-arrow:horizontal {{
        height: 0px; width: 0px; background: none; border: none; image: none;
    }}
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
"""

# --- EXPLORER SPECIFIC SCROLLBAR ---
EXPLORER_SCROLLBAR_CSS = f"""
    QScrollBar:vertical {{
        border: none;
        background: transparent;
        width: 14px; 
        margin: 16px 0 16px 0; 
    }}
    QScrollBar::handle:vertical {{
        background: {CONFIG['theme']['function']};
        min-height: 20px;
        border-radius: 4px;
        margin: 0px 4px 0px 4px; 
    }}
    QScrollBar::handle:vertical:hover {{ background: #8caaee; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px; background: none;
    }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
"""

COMBO_STYLE = f"""
    QComboBox {{
        background-color: {CONFIG['theme']['sidebar']};
        color: {CONFIG['theme']['fg']};
        border: 1px solid {CONFIG['theme']['selection']};
        border-radius: 6px;
        padding: 5px 12px;
        font-size: 13px;
    }}
    QComboBox:hover, QComboBox:on {{
        border: 1px solid {CONFIG['theme']['function']};
        background-color: {CONFIG['theme']['bg']};
    }}
    QComboBox::drop-down {{
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 25px;
        border: none;
        background: transparent;
    }}
    QComboBox::down-arrow {{ image: none; border: none; width: 0px; height: 0px; }}
    QComboBox QAbstractItemView {{
        background-color: {CONFIG['theme']['sidebar']};
        border: 1px solid {CONFIG['theme']['selection']};
        outline: none;
        padding: 2px;
        border-radius: 4px;
        color: {CONFIG['theme']['fg']};
    }}
    QComboBox QAbstractItemView::item {{
        height: 30px;
        color: {CONFIG['theme']['fg']};
        padding-left: 8px;
        border-radius: 4px;
    }}
    QComboBox QAbstractItemView::item:selected, 
    QComboBox QAbstractItemView::item:hover {{
        background-color: {CONFIG['theme']['function']};
        color: {CONFIG['theme']['bg']};
    }}
"""

class ThemedComboBox(QComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        view = CleanHoverListView(self)
        view.setStyleSheet(f"""
            QListView {{
                background-color: {CONFIG['theme']['sidebar']};
                border: 1px solid {CONFIG['theme']['selection']};
                outline: none;
            }}
            {SCROLLBAR_CSS}
        """)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setView(view)
        apply_smooth_scroll(view)
        self.setStyleSheet(COMBO_STYLE + "\nQComboBox { combobox-popup: 0; }")
        self._popup_anim = None
        self._is_closing = False

    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        if not popup: return
        popup.setObjectName("PopupWrapper")
        popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        popup.setStyleSheet(f"""
            #PopupWrapper {{ 
                background-color: {CONFIG['theme']['sidebar']}; 
                border: 1px solid {CONFIG['theme']['function']}; 
                border-radius: 4px; 
            }}
            {SCROLLBAR_CSS}
        """)
        gp = self.mapToGlobal(QPoint(0, self.height()))
        target_rect = popup.geometry()
        target_rect.moveTopLeft(gp)
        start_rect = QRect(target_rect); start_rect.setHeight(0)
        popup.setGeometry(start_rect)
        popup.show()
        if not self._popup_anim:
            self._popup_anim = QPropertyAnimation(popup, b"geometry", self)
            self._popup_anim.setDuration(150)
            self._popup_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        try: self._popup_anim.finished.disconnect()
        except: pass
        self._popup_anim.setStartValue(start_rect)
        self._popup_anim.setEndValue(target_rect)
        self._popup_anim.start()

    def hidePopup(self):
        if self._is_closing: return
        popup = self.view().window()
        if not popup: super().hidePopup(); return
        self._is_closing = True
        start_rect = popup.geometry()
        target_rect = QRect(start_rect)
        target_rect.setHeight(0)
        if not self._popup_anim: 
            self._popup_anim = QPropertyAnimation(popup, b"geometry", self)
            self._popup_anim.setDuration(150)
        self._popup_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._popup_anim.setStartValue(start_rect)
        self._popup_anim.setEndValue(target_rect)
        try: self._popup_anim.finished.disconnect()
        except: pass
        self._popup_anim.finished.connect(self._finish_close)
        self._popup_anim.start()

    def _finish_close(self): super().hidePopup(); self._is_closing = False

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        arrow_color = QColor(CONFIG['theme']['fg'])
        if self.underMouse(): arrow_color = QColor(CONFIG['theme']['function'])
        pen = QPen(arrow_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        rect = self.rect(); x = rect.width() - 20; y = rect.height() // 2
        path = QPolygon([QPoint(x - 5, y - 2), QPoint(x, y + 3), QPoint(x + 5, y - 2)])
        painter.drawPolyline(path)

class ThemedFontComboBox(QFontComboBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        view = CleanHoverListView(self)
        view.setStyleSheet(f"""
            QListView {{
                background-color: {CONFIG['theme']['sidebar']};
                border: 1px solid {CONFIG['theme']['selection']};
                outline: none;
            }}
            {SCROLLBAR_CSS}
        """)
        view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        view.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.setView(view)
        apply_smooth_scroll(view)
        self.setStyleSheet(COMBO_STYLE + """
            QFontComboBox::drop-down { border: none; background: transparent; }
            QFontComboBox::down-arrow { image: none; border: none; width: 0px; height: 0px; }
        """)
        self.setMaxVisibleItems(10)
        self._popup_anim = None
        self._is_closing = False
          
    def showPopup(self):
        super().showPopup()
        popup = self.view().window()
        if not popup: return
        popup.setObjectName("PopupWrapper")
        popup.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
        popup.setStyleSheet(f"""
            #PopupWrapper {{ 
                background-color: {CONFIG['theme']['sidebar']}; 
                border: 1px solid {CONFIG['theme']['function']}; 
                border-radius: 4px; 
            }}
            {SCROLLBAR_CSS}
        """)
        gp = self.mapToGlobal(QPoint(0, self.height()))
        target_rect = popup.geometry()
        target_rect.moveTopLeft(gp)
        start_rect = QRect(target_rect); start_rect.setHeight(0)
        popup.setGeometry(start_rect); popup.show()
        if not self._popup_anim:
            self._popup_anim = QPropertyAnimation(popup, b"geometry", self)
            self._popup_anim.setDuration(150)
            self._popup_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        try: self._popup_anim.finished.disconnect()
        except: pass
        self._popup_anim.setStartValue(start_rect)
        self._popup_anim.setEndValue(target_rect)
        self._popup_anim.start()

    def hidePopup(self):
        if self._is_closing: return
        popup = self.view().window()
        if not popup: super().hidePopup(); return
        self._is_closing = True
        start_rect = popup.geometry(); target_rect = QRect(start_rect); target_rect.setHeight(0)
        if not self._popup_anim: 
            self._popup_anim = QPropertyAnimation(popup, b"geometry", self)
            self._popup_anim.setDuration(150)
        self._popup_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        self._popup_anim.setStartValue(start_rect)
        self._popup_anim.setEndValue(target_rect)
        try: self._popup_anim.finished.disconnect()
        except: pass
        self._popup_anim.finished.connect(self._finish_close)
        self._popup_anim.start()

    def _finish_close(self): super().hidePopup(); self._is_closing = False

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        arrow_color = QColor(CONFIG['theme']['fg'])
        if self.underMouse(): arrow_color = QColor(CONFIG['theme']['function'])
        pen = QPen(arrow_color, 2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        rect = self.rect(); x = rect.width() - 20; y = rect.height() // 2
        path = QPolygon([QPoint(x - 5, y - 2), QPoint(x, y + 3), QPoint(x + 5, y - 2)])
        painter.drawPolyline(path)

class ModernSpinBox(QWidget):
    def __init__(self, value=12, min_val=8, max_val=72):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.setSpacing(2)
        self.min_val, self.max_val, self.current_value = min_val, max_val, value
        self.display = QLabel(str(self.current_value))
        self.display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.display.setStyleSheet(f"background: {CONFIG['theme']['sidebar']}; color: {CONFIG['theme']['fg']}; border: 1px solid {CONFIG['theme']['selection']}; border-radius: 4px; padding: 4px; min-width: 40px;")
        btn_style = f"QToolButton {{ background: {CONFIG['theme']['sidebar']}; border: 1px solid {CONFIG['theme']['selection']}; border-radius: 4px; }} QToolButton:hover {{ background: {CONFIG['theme']['selection']}; border: 1px solid {CONFIG['theme']['function']}; }} QToolButton:pressed {{ background: {CONFIG['theme']['function']}; color: {CONFIG['theme']['bg']}; }}"
        self.btn_minus = QToolButton()
        self.btn_minus.setIcon(create_icon("minus", CONFIG['theme']['fg']))
        self.btn_minus.setStyleSheet(btn_style)
        self.btn_minus.clicked.connect(self.decrement)
        self.btn_plus = QToolButton()
        self.btn_plus.setIcon(create_icon("plus", CONFIG['theme']['fg']))
        self.btn_plus.setStyleSheet(btn_style)
        self.btn_plus.clicked.connect(self.increment)
        layout.addWidget(self.btn_minus)
        layout.addWidget(self.display)
        layout.addWidget(self.btn_plus)
        layout.addStretch()
    def increment(self):
        if self.current_value < self.max_val: 
            self.current_value += 1
            self.display.setText(str(self.current_value))
    def decrement(self):
        if self.current_value > self.min_val: 
            self.current_value -= 1
            self.display.setText(str(self.current_value))
    def value(self): return self.current_value

# --- TAB SWITCHER POPUP (Ctrl+Tab overlay) ---
class TabSwitcherPopup(QWidget):
    """VS Code-style Ctrl+Tab popup showing all open tabs."""
    def __init__(self, parent):
        super().__init__(parent)
        self.main_window = parent
        self.selected_index = 0
        self.tab_names = []
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.hide()

    def show_switcher(self, direction=1):
        """Populate and show the switcher. direction: 1=next, -1=prev."""
        file_list = self.main_window.file_list
        count = file_list.count()
        if count <= 1:
            return
        
        self.tab_names = []
        for i in range(count):
            item = file_list.item(i)
            widget = file_list.itemWidget(item)
            if hasattr(widget, 'text'):
                self.tab_names.append(widget.text())
            else:
                self.tab_names.append(item.text())
        
        current_row = file_list.currentRow()
        self.selected_index = (current_row + direction) % count
        
        item_h = 36
        padding = 16
        w = 320
        h = len(self.tab_names) * item_h + padding * 2
        parent_rect = self.main_window.rect()
        x = (parent_rect.width() - w) // 2
        y = (parent_rect.height() - h) // 2
        self.setGeometry(x, y, w, h)
        
        self.show()
        self.raise_()
        self.setFocus()
        self.grabKeyboard()
        self.update()

    def cycle(self, direction=1):
        """Move selection up or down."""
        if not self.tab_names:
            return
        self.selected_index = (self.selected_index + direction) % len(self.tab_names)
        self.update()

    def _commit(self):
        """Switch to the selected tab and close."""
        self.releaseKeyboard()
        self.hide()
        if self.tab_names and 0 <= self.selected_index < len(self.tab_names):
            self.main_window.file_list.setCurrentRow(self.selected_index)

    def paintEvent(self, event):
        theme = CONFIG["theme"]
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background
        bg = QColor(theme["sidebar"])
        bg.setAlpha(240)
        p.setBrush(bg)
        border = QColor(theme["selection"])
        p.setPen(QPen(border, 1))
        p.drawRoundedRect(self.rect().adjusted(1, 1, -1, -1), 10, 10)
        
        item_h = 36
        padding = 16
        font = QFont(CONFIG["editor"].get("font_family", "Consolas"), 11)
        p.setFont(font)
        
        for i, name in enumerate(self.tab_names):
            y = padding + i * item_h
            item_rect = QRect(8, y, self.width() - 16, item_h)
            
            if i == self.selected_index:
                sel_bg = QColor(theme["function"])
                sel_bg.setAlpha(50)
                p.setBrush(sel_bg)
                p.setPen(Qt.PenStyle.NoPen)
                p.drawRoundedRect(item_rect, 6, 6)
                p.setPen(QColor(theme["function"]))
            else:
                p.setPen(QColor(theme["fg"]))
            
            text_rect = item_rect.adjusted(12, 0, -8, 0)
            p.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, name)
        
        p.end()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Tab:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.cycle(-1)
            else:
                self.cycle(1)
            event.accept()
        elif event.key() == Qt.Key.Key_Down:
            self.cycle(1)
            event.accept()
        elif event.key() == Qt.Key.Key_Up:
            self.cycle(-1)
            event.accept()
        elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._commit()
            event.accept()
        elif event.key() == Qt.Key.Key_Escape:
            self.releaseKeyboard()
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event):
        if event.key() == Qt.Key.Key_Control:
            self._commit()
            event.accept()
        else:
            super().keyReleaseEvent(event)

    def focusOutEvent(self, event):
        self.releaseKeyboard()
        self.hide()
        super().focusOutEvent(event)

    def _index_at(self, pos):
        padding = 16
        item_h = 36
        y = pos.y() - padding
        if y < 0:
            return -1
        idx = int(y // item_h)
        if 0 <= idx < len(self.tab_names):
            return idx
        return -1

    def mouseMoveEvent(self, event):
        idx = self._index_at(event.pos())
        if idx >= 0 and idx != self.selected_index:
            self.selected_index = idx
            self.update()

    def mousePressEvent(self, event):
        idx = self._index_at(event.pos())
        if idx >= 0:
            self.selected_index = idx
            self._commit()

class ExplorerItemWidget(QWidget):
    def __init__(self, text, item_ref, main_window, is_new=False):
        super().__init__()
        self.item_ref = item_ref
        self.main_window = main_window
        self.clean_text = text
        self.is_dirty = False
        self.is_new = is_new 
        self.is_active_selection = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 4, 2)
        layout.setSpacing(2)
        self.label = QLabel(text)
        default_col = CONFIG['theme']['fg']
        self.label.setStyleSheet(f"background: transparent; border: none; color: {default_col}; font-weight: 500;")
        self.label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents) 
        
        self.edit_line = QLineEdit(text)
        self.edit_line.setStyleSheet(f"background: {CONFIG['theme']['selection']}; border: 1px solid {CONFIG['theme']['function']}; color: {CONFIG['theme']['fg']}; border-radius: 4px; padding: 2px;")
        self.edit_line.hide()
        self.edit_line.returnPressed.connect(self.finish_rename)
        self.edit_line.editingFinished.connect(self.finish_rename)
        
        self.btn_rename = QToolButton()
        self.btn_rename.setFixedSize(26, 26)
        self.btn_rename.setIconSize(QSize(20, 20))
        self.btn_rename.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_rename.setToolTip("Rename Tab")
        self.btn_rename.clicked.connect(self.start_rename)
        self.btn_close = QToolButton()
        self.btn_close.setFixedSize(26, 26)
        self.btn_close.setIconSize(QSize(18, 18))
        self.btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close.clicked.connect(self.close_clicked)
        layout.addWidget(self.label)
        layout.addWidget(self.edit_line)
        layout.addStretch()
        layout.addWidget(self.btn_rename)
        layout.addWidget(self.btn_close)
          
        # FIX #7: Use cached icons initially
        default_icon_col = CONFIG['theme']['comment']
        self.btn_rename.setIcon(create_icon("rename_box", default_icon_col, size=24))
        self.btn_close.setIcon(create_icon("x", default_icon_col, size=18))
        self.set_selected_visuals(False)
        self.update_label_style() 

    def set_dirty(self, dirty): 
        self.is_dirty = dirty
        self.update_label_style()
        if dirty:
            suffix = " **" if self.is_new else " *"
            self.label.setText(f"{self.clean_text}{suffix}")
        else:
            self.label.setText(self.clean_text)

    def update_label_style(self):
        selected = self.is_selected()
        font_weight = "bold" if selected else "500"
        font_style = "italic" if self.is_dirty else "normal"
        if selected: color = CONFIG['theme']['bg'] 
        else: color = CONFIG['theme']['fg'] 
        self.label.setStyleSheet(f"background: transparent; border: none; color: {color}; font-weight: {font_weight}; font-style: {font_style};")

    def set_selected_visuals(self, selected):
        self.is_active_selection = selected
        self.update_label_style()
        icon_col = "#ffffff" if selected else CONFIG['theme']['comment']
        rename_hover = "rgba(0, 0, 0, 0.3)" if selected else "rgba(255, 255, 255, 0.15)"
        
        text_color = CONFIG['theme']['bg'] if selected else CONFIG['theme']['fg']
        selection_bg = CONFIG['theme']['fg'] if selected else CONFIG['theme']['selection']
        selection_fg = CONFIG['theme']['bg'] if selected else CONFIG['theme']['fg']
        border_col = 'rgba(0,0,0,0.3)' if selected else CONFIG['theme']['function']
        
        self.edit_line.setStyleSheet(f"""
            QLineEdit {{
                background: transparent; 
                border: 1px solid {border_col}; 
                color: {text_color}; 
                border-radius: 4px; 
                padding: 2px;
                selection-background-color: {selection_bg};
                selection-color: {selection_fg};
            }}
        """)
        
        self.btn_rename.setIcon(create_icon("rename_box", icon_col, size=24))
        self.btn_close.setIcon(create_icon("x", icon_col, size=18))
        
        self.btn_rename.setStyleSheet(f"QToolButton {{ border: none; background: transparent; border-radius: 4px; }} QToolButton:hover {{ background-color: {rename_hover}; }}")
        self.btn_close.setStyleSheet(f"QToolButton {{ border: none; background: transparent; border-radius: 4px; }} QToolButton:hover {{ background-color: #ff5555; }}")
        self.btn_rename.style().unpolish(self.btn_rename)
        self.btn_rename.style().polish(self.btn_rename)
        self.btn_close.style().unpolish(self.btn_close)
        self.btn_close.style().polish(self.btn_close)
        
    def is_selected(self): return hasattr(self, 'is_active_selection') and self.is_active_selection
    def close_clicked(self): self.main_window.close_explorer_tab(self.item_ref)
    
    def start_rename(self):
        self.label.hide()
        self.edit_line.setText(self.clean_text)
        self.edit_line.show()
        self.edit_line.selectAll()
        self.edit_line.setFocus()
        
    def finish_rename(self):
        if not self.edit_line.isVisible(): return
        self.edit_line.hide()
        self.label.show()
        new_name = self.edit_line.text().strip()
        if new_name and new_name != self.clean_text:
            base_name = new_name
            ext = ""
            
            if "." in base_name:
                parts = base_name.rsplit(".", 1)
                base_name = parts[0]
                ext = "." + parts[1]
                
            check_name = new_name
            counter = 1
            
            while check_name in self.main_window.file_states or os.path.exists(check_name):
                check_name = f"{base_name} ({counter}){ext}"
                counter += 1
                
            self.main_window.perform_tab_rename(self.clean_text, check_name)
    
    def text(self): return self.clean_text
    def set_text(self, text): 
        self.clean_text = text
        self.set_dirty(self.is_dirty) 

# --- MODERN INPUT DIALOG ---
class ModernInputDialog(QDialog):
    def __init__(self, parent=None, title="Input", label="Enter value:", text=""):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setFixedWidth(350)
        self.setStyleSheet(f"""
            QDialog {{ background-color: {CONFIG['theme']['bg']}; color: {CONFIG['theme']['fg']}; border: 1px solid {CONFIG['theme']['selection']}; border-radius: 8px; }}
            QLabel {{ color: {CONFIG['theme']['fg']}; font-size: 13px; font-weight: 500; margin-bottom: 5px; }}
            QLineEdit {{ background-color: {CONFIG['theme']['sidebar']}; color: {CONFIG['theme']['fg']}; border: 1px solid {CONFIG['theme']['selection']}; border-radius: 4px; padding: 6px; font-size: 13px; }}
            QLineEdit:focus {{ border: 1px solid {CONFIG['theme']['function']}; }}
            QPushButton {{ background-color: {CONFIG['theme']['sidebar']}; border: 1px solid {CONFIG['theme']['selection']}; color: {CONFIG['theme']['fg']}; border-radius: 4px; padding: 6px 15px; min-width: 60px; }}
            QPushButton:hover {{ background-color: {CONFIG['theme']['selection']}; border: 1px solid {CONFIG['theme']['function']}; }}
            QPushButton:pressed {{ background-color: {CONFIG['theme']['function']}; color: {CONFIG['theme']['bg']}; }}
        """)
        layout = QVBoxLayout(self)
        self.lbl = QLabel(label)
        layout.addWidget(self.lbl)
        
        self.input = QLineEdit()
        self.input.setText(text)
        self.input.selectAll()
        layout.addWidget(self.input)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_ok = QPushButton("OK")
        self.btn_ok.clicked.connect(self.accept)
        self.btn_ok.setDefault(True)
        
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_ok)
        layout.addLayout(btn_layout)

    def get_text(self):
        return self.input.text()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zenith Settings")
        self.resize(600, 600)
        self.parent_window = parent
        
        self.initial_theme = CONFIG["app"].get("theme_name", "Default Dark")
        self.ensure_default_keybinds()

        # --- STYLE ---
        self.setStyleSheet(f"""
            QDialog {{ background-color: {CONFIG['theme']['bg']}; color: {CONFIG['theme']['fg']}; }}
            QLabel {{ color: {CONFIG['theme']['fg']}; font-size: 14px; font-weight: 500; }}
            QTabWidget::pane {{ border: 1px solid {CONFIG['theme']['selection']}; border-radius: 6px; top: -1px; background: {CONFIG['theme']['bg']}; }}
            QTabWidget::tab-bar {{ alignment: left; }}
            QTabBar::tab {{ background: {CONFIG['theme']['sidebar']}; color: {CONFIG['theme']['comment']}; padding: 8px 25px; border: 1px solid transparent; border-top-left-radius: 6px; border-top-right-radius: 6px; margin-right: 2px; font-weight: bold; }}
            QTabBar::tab:selected {{ background: {CONFIG['theme']['bg']}; color: {CONFIG['theme']['fg']}; border: 1px solid {CONFIG['theme']['selection']}; border-bottom: 2px solid {CONFIG['theme']['function']}; }}
            QTabBar::tab:!selected:hover {{ background: {CONFIG['theme']['selection']}; }}
            QCheckBox {{ color: {CONFIG['theme']['fg']}; spacing: 8px; font-size: 14px; background: transparent; }}
            QCheckBox::indicator {{ width: 18px; height: 18px; border-radius: 4px; border: 1px solid {CONFIG['theme']['comment']}; background: {CONFIG['theme']['sidebar']}; }}
            QCheckBox::indicator:checked {{ background-color: {CONFIG['theme']['function']}; border: 1px solid {CONFIG['theme']['function']}; }}
            
            QTableWidget {{ 
                background: transparent; 
                border: 1px solid {CONFIG['theme']['selection']};
                border-radius: 6px;
                gridline-color: transparent; 
                outline: none;
                color: {CONFIG['theme']['fg']};
                alternate-background-color: rgba(255, 255, 255, 0.03); 
            }}
            QHeaderView::section {{ 
                background-color: {CONFIG['theme']['sidebar']}; 
                color: {CONFIG['theme']['comment']}; 
                padding: 10px; 
                border: none; 
                border-bottom: 2px solid {CONFIG['theme']['selection']}; 
                font-weight: bold;
                text-transform: uppercase;
                font-size: 11px;
            }}
            QTableWidget::item {{ padding: 8px 12px; border-bottom: 1px solid rgba(255, 255, 255, 0.05); color: {CONFIG['theme']['fg']}; }}
            QTableWidget::item:selected {{ background-color: {CONFIG['theme']['selection']}; border: none; color: {CONFIG['theme']['fg']}; }}
            QTableWidget:focus {{ outline: none; }}
            
            QPushButton {{ background-color: {CONFIG['theme']['sidebar']}; border: 1px solid {CONFIG['theme']['selection']}; color: {CONFIG['theme']['fg']}; border-radius: 4px; padding: 6px 15px; min-width: 60px; }}
            QPushButton:hover {{ background-color: {CONFIG['theme']['selection']}; border: 1px solid {CONFIG['theme']['function']}; }}
            QPushButton:pressed {{ background-color: {CONFIG['theme']['function']}; color: {CONFIG['theme']['bg']}; }}
            {SCROLLBAR_CSS}
        """)
        
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        
        # --- TAB: APPEARANCE ---
        self.tab_appearance = QWidget()
        form_layout = QFormLayout()
        form_layout.setSpacing(15)
        
        self.theme_box = ThemedComboBox()
        self.theme_box.addItems(["Default Dark", "Light", "High Contrast", "Dracula", "Monokai", "Solarized", "Nord", "Gruvbox"])
        self.theme_box.setCurrentText(CONFIG["app"].get("theme_name", "Default Dark"))
        
        self.font_box = ThemedFontComboBox()
        self.font_box.setCurrentFont(QFont(CONFIG["editor"]["font_family"]))
        
        self.size_box = ModernSpinBox(value=max(8, CONFIG["editor"].get("font_size", 12)))
        
        self.encoding_box = ThemedComboBox()
        self.encoding_box.addItems(["utf-8", "ascii", "cp1252", "iso-8859-1", "utf-16", "utf-32", "latin-1", "mac_roman", "windows-1250", "shift_jis"])
        self.encoding_box.setCurrentText(CONFIG["editor"].get("encoding", "utf-8"))
        
        self.line_num_box = QCheckBox("Show Line Numbers")
        self.line_num_box.setChecked(CONFIG["editor"].get("show_line_numbers", True))
        
        form_layout.addRow("Theme:", self.add_help(self.theme_box, "Controls the visual color scheme of the entire application."))
        form_layout.addRow("Font Family:", self.add_help(self.font_box, "The font used for the main text editor area."))
        form_layout.addRow("Font Size:", self.add_help(self.size_box, "The size of the text in the editor."))
        form_layout.addRow("Encoding:", self.add_help(self.encoding_box, "The character encoding used when reading and writing files."))
        form_layout.addRow("", self.add_help(self.line_num_box, "Toggles the visibility of line numbers in the editor margin."))
        
        self.tab_appearance.setLayout(form_layout)
        
        # --- TAB: BEHAVIOR ---
        self.tab_behavior = QWidget()
        behav_layout = QFormLayout()
        behav_layout.setSpacing(15)
        
        self.cursor_blink_box = QCheckBox("Cursor Blinking")
        self.cursor_blink_box.setChecked(CONFIG["editor"].get("cursor_blinking", True))
        
        self.autosave_box = QCheckBox("Auto-Save Files")
        self.autosave_box.setChecked(CONFIG["app"].get("auto_save", False))
        
        self.syntax_highlight_box = QCheckBox("Enable System Syntax")
        self.syntax_highlight_box.setChecked(CONFIG["editor"].get("enable_syntax_highlighting", True))
        
        self.cmd_undo_box = QCheckBox("Enable Command Undo/Redo")
        current_behavior = CONFIG.get("behavior", {})
        self.cmd_undo_box.setChecked(current_behavior.get("enable_command_undo", False))
        
        self.history_box = QCheckBox("Enable Local History (Time Machine)")
        self.history_box.setChecked(current_behavior.get("enable_local_history", True))

        behav_layout.addRow("", self.add_help(self.cursor_blink_box, "Toggles whether the text cursor blinks or stays solid."))
        behav_layout.addRow("", self.add_help(self.autosave_box, "Automatically saves changes to disk when you switch tabs or close the app."))
        behav_layout.addRow("", self.add_help(self.syntax_highlight_box, "Enables color highlighting for code based on file language."))
        behav_layout.addRow("", self.add_help(self.cmd_undo_box, "Allows 'Undo' (Ctrl+Z) to reverse app actions like closing tabs or renaming, not just text edits."))
        behav_layout.addRow("", self.add_help(self.history_box, "Automatically saves timestamped snapshots of your files to a hidden .zenith_history folder every 5 minutes."))
        
        self.tab_behavior.setLayout(behav_layout)
        
        # --- TAB: KEYBINDS ---
        self.tab_keys = QWidget()
        key_layout = QVBoxLayout()
        key_layout.setContentsMargins(0, 10, 0, 0)
        
        self.key_table = QTableWidget()
        self.key_table.setColumnCount(2)
        self.key_table.setHorizontalHeaderLabels(["COMMAND", "BINDING"])
        self.key_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.key_table.verticalHeader().hide()
        self.key_table.setShowGrid(False) 
        self.key_table.setAlternatingRowColors(True) 
        self.key_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.key_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows) 
        self.key_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers) 
        self.key_table.itemDoubleClicked.connect(self.edit_keybind)
        self.key_table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.key_table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        
        apply_smooth_scroll(self.key_table)
        self.populate_key_table()
        key_layout.addWidget(self.key_table)
        self.tab_keys.setLayout(key_layout)

        # --- TAB: DEVELOPER ---
        self.tab_developer = QWidget()
        dev_layout = QFormLayout()
        dev_layout.setSpacing(15)
        
        self.debug_notif_box = QCheckBox("Enable Debug Notifications")
        is_debug = CONFIG.get("developer", {}).get("debug_notifications", False)
        self.debug_notif_box.setChecked(is_debug)
        
        dev_layout.addRow("", self.add_help(self.debug_notif_box, "Shows popup notifications for internal actions like opening/closing tabs (Useful for debugging)."))
        self.tab_developer.setLayout(dev_layout)
        
        # --- FINALIZE ---
        self.tabs.addTab(self.tab_appearance, "Appearance")
        self.tabs.addTab(self.tab_behavior, "Behavior")
        self.tabs.addTab(self.tab_keys, "Keybinds")
        self.tabs.addTab(self.tab_developer, "Developer")
        layout.addWidget(self.tabs)
        
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.apply_settings)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def add_help(self, widget, text):
        """Wraps a widget in a layout and adds a clickable Help Button."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        layout.addWidget(widget)
        
        btn_help = QToolButton()
        btn_help.setText("?")
        btn_help.setFixedSize(18, 18)
        btn_help.setCursor(Qt.CursorShape.PointingHandCursor)
        
        btn_help.setToolTip(text)
        
        btn_help.clicked.connect(lambda: QToolTip.showText(QCursor.pos(), text, btn_help))
        
        # --- NEW SUBTLE THEMED STYLE ---
        btn_help.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                color: {CONFIG['theme']['comment']};
                border: 1px solid {CONFIG['theme']['comment']}; /* Subtle outline */
                border-radius: 9px; 
                font-weight: bold;
                font-family: 'Segoe UI', sans-serif;
                font-size: 11px;
                padding: 0px;
                padding-bottom: 2px;
            }}
            QToolButton:hover {{
                background-color: {CONFIG['theme']['function']}; /* Fill with accent on hover */
                border: 1px solid {CONFIG['theme']['function']};
                color: {CONFIG['theme']['bg']}; /* High contrast text */
            }}
            QToolButton:pressed {{
                background-color: {CONFIG['theme']['selection']};
                border-color: {CONFIG['theme']['fg']};
                color: {CONFIG['theme']['fg']};
            }}
        """)
        
        layout.addWidget(btn_help)
        return container

    def ensure_default_keybinds(self):
        defaults = {
            "new_tab": "Ctrl+T", "close_tab": "Ctrl+W", "rename_tab": "Ctrl+R",
            "open_file": "Ctrl+O", "save_file": "Ctrl+S", "save_as": "Ctrl+Shift+S",
            "sidebar_toggle": "Ctrl+B", "command_palette": "Ctrl+K, Ctrl+Space",
            "find_text": "Ctrl+F", "global_find": "Ctrl+Shift+F", "goto_line": "Ctrl+G",
            "copy_path": "Ctrl+Shift+C", "undo": "Ctrl+Z", "redo": "Ctrl+Y",
            "cut": "Ctrl+X", "copy": "Ctrl+C", "paste": "Ctrl+V",
            "select_all": "Ctrl+A", "zoom_in": "Ctrl++", "zoom_out": "Ctrl+-"
        }
        if "keybinds" not in CONFIG: CONFIG["keybinds"] = {}
        for key, val in defaults.items():
            if key not in CONFIG["keybinds"]: CONFIG["keybinds"][key] = val

    def populate_key_table(self):
        self.key_table.setRowCount(0)
        row = 0
        sorted_keys = sorted(CONFIG["keybinds"].keys())
        for action in sorted_keys:
            shortcut = CONFIG["keybinds"][action]
            self.key_table.insertRow(row)
            display_name = action.replace("_", " ").title()
            
            item_action = QTableWidgetItem(display_name)
            item_action.setData(Qt.ItemDataRole.UserRole, action) 
            self.key_table.setItem(row, 0, item_action)
            
            item_shortcut = QTableWidgetItem(shortcut)
            f = QFont("Consolas") if "Consolas" in QFontDatabase.families() else QFont("Monospace")
            f.setBold(True)
            item_shortcut.setFont(f)
            item_shortcut.setForeground(QColor(CONFIG['theme']['function'])) 
            item_shortcut.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.key_table.setItem(row, 1, item_shortcut)
            row += 1

    def edit_keybind(self, item):
        row = item.row()
        action_name = self.key_table.item(row, 0).text()
        current_bind = self.key_table.item(row, 1).text()
        dlg = ModernInputDialog(self, title=f"Edit {action_name}", label="Key Binding (separate multiple with comma):", text=current_bind)
        if dlg.exec():
            new_bind = dlg.get_text()
            if new_bind: self.key_table.item(row, 1).setText(new_bind)

    def apply_settings(self):
        CONFIG["editor"]["font_family"] = self.font_box.currentFont().family()
        CONFIG["editor"]["font_size"] = max(8, self.size_box.value())
        CONFIG["editor"]["show_line_numbers"] = self.line_num_box.isChecked()
        CONFIG["editor"]["encoding"] = self.encoding_box.currentText()
        
        new_theme_name = self.theme_box.currentText()
        CONFIG["app"]["theme_name"] = new_theme_name
        
        if new_theme_name in THEME_PALETTES:
            CONFIG["theme"] = THEME_PALETTES[new_theme_name].copy()

        CONFIG["editor"]["cursor_blinking"] = self.cursor_blink_box.isChecked()
        CONFIG["app"]["auto_save"] = self.autosave_box.isChecked()
        CONFIG["editor"]["enable_syntax_highlighting"] = self.syntax_highlight_box.isChecked()
        
        if "behavior" not in CONFIG: CONFIG["behavior"] = {}
        CONFIG["behavior"]["enable_command_undo"] = self.cmd_undo_box.isChecked()
        CONFIG["behavior"]["enable_local_history"] = self.history_box.isChecked()

        if "developer" not in CONFIG: CONFIG["developer"] = {}
        CONFIG["developer"]["debug_notifications"] = self.debug_notif_box.isChecked()
        
        for i in range(self.key_table.rowCount()):
            action_key = self.key_table.item(i, 0).data(Qt.ItemDataRole.UserRole)
            new_shortcut = self.key_table.item(i, 1).text()
            CONFIG["keybinds"][action_key] = new_shortcut
            
        save_config() 
        
        if new_theme_name != self.initial_theme:
            QMessageBox.information(self, "Restart Required", "Theme changes require a restart to fully apply to all UI elements.")

        if self.parent_window: 
            self.parent_window.apply_theme()
            self.parent_window.refresh_shortcuts()
            self.parent_window.update_status_encoding()
            self.parent_window.apply_editor_fixes() 
            self.parent_window.editor.set_lexer_from_filename(self.parent_window.last_active_filename or "untitled.txt")
            
        self.accept()
        
# --- REVISED COMMAND PALETTE ---
class CommandPalette(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowFlags(Qt.WindowType.Widget | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.hide()
        
        self._geo_anim = QPropertyAnimation(self, b"geometry")
        self._alpha_anim = QPropertyAnimation(self, b"windowOpacity")
        
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)
        self.opacity_anim = QPropertyAnimation(self.opacity_effect, b"opacity")

        self._group = QParallelAnimationGroup(self)
        self._group.addAnimation(self._geo_anim)
        self._group.addAnimation(self.opacity_anim)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0,0,0,0)
        
        self.body = QFrame()
        self.body.setObjectName("PaletteBody")
        self.body.setStyleSheet(f"""
            #PaletteBody {{
                background-color: {CONFIG['theme']['sidebar']}; 
                border: 1px solid {CONFIG['theme']['function']}; 
                border-radius: 12px;
                border-bottom: 3px solid {CONFIG['theme']['selection']};
            }}
            QLineEdit {{ 
                background: transparent; 
                color: {CONFIG['theme']['fg']}; 
                border: none; 
                font-size: 16px; 
                padding: 5px;
            }}
            QListWidget {{ background: transparent; color: {CONFIG['theme']['fg']}; border: none; outline: none; }}
            QListWidget::item {{ 
                padding: 8px 10px; 
                border-radius: 6px; 
                margin: 2px 8px; 
                border: 1px solid transparent; 
            }}
            QListWidget::item:hover {{ 
                background: {CONFIG['theme']['selection']}; 
                border: 1px solid {CONFIG['theme']['selection']};
            }}
            QListWidget::item:selected {{ 
                background: {CONFIG['theme']['selection']}; 
                border: 1px solid {CONFIG['theme']['function']};
                color: {CONFIG['theme']['fg']};
                font-weight: bold; 
            }}
        """)
        
        body_layout = QVBoxLayout(self.body)
        body_layout.setContentsMargins(0,0,0,0)
        body_layout.setSpacing(0)
        
        self.search_area = QFrame()
        self.search_area.setObjectName("SearchArea")
        self.search_area.setStyleSheet(f"""
            #SearchArea {{
                background-color: transparent;
                border: none;
                border-bottom: 1px solid {CONFIG['theme']['selection']};
            }}
        """)
        search_layout = QHBoxLayout(self.search_area)
        search_layout.setContentsMargins(15, 12, 15, 12)
        search_layout.setSpacing(10)
        
        lbl_icon = QLabel()
        lbl_icon.setPixmap(create_icon("search", CONFIG['theme']['comment'], size=18).pixmap(18, 18))
        search_layout.addWidget(lbl_icon)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a command...")
        self.input.setStyleSheet("border: none; background: transparent;")
        self.input.installEventFilter(self)
        search_layout.addWidget(self.input)
        
        self.results = QListWidget()
        self.results.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.results.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.results.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        apply_smooth_scroll(self.results)
        
        body_layout.addWidget(self.search_area)
        body_layout.addWidget(self.results)
        main_layout.addWidget(self.body)
        
        self.main_window = parent
        
        self.all_commands = [
            ("New Tab", "Ctrl+T", lambda: self.main_window.create_new_explorer_item(register_undo=True)),
            ("Close Tab", "Ctrl+W", lambda: self.main_window.close_current_tab(register_undo=True)),
            ("Rename Tab", "Ctrl+R", lambda: self.main_window.rename_current_tab(register_undo=True)),
            ("Open File", "Ctrl+O", self.main_window.open_file),
            ("Save File", "Ctrl+S", self.main_window.save_file),
            ("Save File As", "", self.main_window.save_as),
            ("Toggle Sidebar", "Ctrl+B", self.main_window.toggle_sidebar),
            ("Settings", "", self.main_window.open_settings),
            ("Find Text", "Ctrl+F", lambda: self.main_window.open_find_bar()),
            ("Global Find", "Ctrl+Shift+F", lambda: self.main_window.open_global_search()),
            ("Go to Line", "Ctrl+G", lambda: self.main_window.open_goto_bar()),
            ("Undo", "Ctrl+Z", self.main_window.global_undo),
            ("Redo", "Ctrl+Y", self.main_window.global_redo),
            ("Cut", "Ctrl+X", self.main_window.editor.cut),
            ("Copy", "Ctrl+C", self.main_window.editor.copy),
            ("Paste", "Ctrl+V", self.main_window.editor.paste),
            ("Select All", "Ctrl+A", self.main_window.editor.selectAll),
            ("Zoom In", "Ctrl++", self.main_window.editor.zoomIn),
            ("Zoom Out", "Ctrl+-", self.main_window.editor.zoomOut),
            ("Exit Zenith", "Alt+F4", QApplication.instance().quit),
        ]
        self.populate_list()
        
        self.input.textChanged.connect(self.filter_list)
        self.input.returnPressed.connect(self.trigger_selected)
        self.results.itemClicked.connect(self.execute_command)
        
        self.last_close_time = 0

    def calculate_geometry(self):
        parent = self.parent()
        if not parent: return QRect(0,0,600,350)
        
        main_w = parent.width()
        main_h = parent.height()
        
        target_w = int(main_w * 0.5)
        if target_w < 400: target_w = 400
        if target_w > 800: target_w = 800
        if target_w > main_w - 40: target_w = main_w - 40
        
        h = 380
        x = (main_w - target_w) // 2
        y = int(main_h * 0.15)
        
        return QRect(x, y, target_w, h)

    def update_overlay_position(self):
        if self.isVisible():
            new_rect = self.calculate_geometry()
            if self._group.state() != QParallelAnimationGroup.State.Running:
                self.setGeometry(new_rect)
            self.raise_() 

    def show_animated(self):
        if time.time() - self.last_close_time > 0.5:
            self.input.clear()
            self.results.clearSelection() 
            self.results.setCurrentRow(-1) 
            self.results.scrollToTop()
            
        QApplication.instance().installEventFilter(self)
            
        QApplication.instance().installEventFilter(self)
        
        end_rect = self.calculate_geometry()
        start_rect = QRect(end_rect)
        start_rect.setHeight(int(end_rect.height() * 0.9))
        start_rect.moveTop(end_rect.y() - 10) 
        
        self.opacity_effect.setOpacity(0.0)
        self.setGeometry(start_rect)
        self.show()
        self.raise_()
        self.input.setFocus()
        
        self._geo_anim.setDuration(200)
        self._geo_anim.setStartValue(start_rect)
        self._geo_anim.setEndValue(end_rect)
        self._geo_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self.opacity_anim.setDuration(150)
        self.opacity_anim.setStartValue(0.0)
        self.opacity_anim.setEndValue(1.0)
        self.opacity_anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        
        try: self._group.finished.disconnect()
        except: pass
        self._group.start()

    def hide_animated(self):
        QApplication.instance().removeEventFilter(self)
        self.last_close_time = time.time()
        
        if self._group.state() == QParallelAnimationGroup.State.Running:
            self._group.stop()
            
        current_rect = self.geometry()
        end_rect = QRect(current_rect)
        end_rect.setHeight(int(current_rect.height() * 0.9))
        
        self._geo_anim.setDuration(150)
        self._geo_anim.setStartValue(current_rect)
        self._geo_anim.setEndValue(end_rect)
        self._geo_anim.setEasingCurve(QEasingCurve.Type.InQuad)
        
        self.opacity_anim.setDuration(100)
        self.opacity_anim.setStartValue(self.opacity_effect.opacity())
        self.opacity_anim.setEndValue(0.0)
        
        try: self._group.finished.disconnect()
        except: pass
        self._group.finished.connect(self._on_hide_finished)
        self._group.start()
        
        if self.main_window: self.main_window.editor.setFocus()

    def _on_hide_finished(self):
        super(CommandPalette, self).hide()

    def eventFilter(self, source, event):
        if event.type() == QEvent.Type.MouseButtonPress:
            if self.isVisible() and not self.geometry().contains(self.mapFromGlobal(event.globalPosition().toPoint())):
                self.hide_animated()
                return True 
        if source == self.input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Escape:
                self.hide_animated()
                return True
            if event.key() == Qt.Key.Key_Down:
                idx = self.results.currentRow()
                if idx < self.results.count() - 1: self.results.setCurrentRow(idx + 1)
                return True
            elif event.key() == Qt.Key.Key_Up:
                idx = self.results.currentRow()
                if idx > 0: self.results.setCurrentRow(idx - 1)
                return True
            elif event.key() == Qt.Key.Key_Return:
                self.trigger_selected()
                return True
        return super().eventFilter(source, event)

    def populate_list(self):
        self.results.clear()
        for name, short, func in self.all_commands: self.add_item(name, short, func)
        self.results.setCurrentRow(0)

    def add_item(self, name, short, func):
        text = f"{name}    ({short})" if short else name
        item = QListWidgetItem(text)
        item.setData(Qt.ItemDataRole.UserRole, func)
        self.results.addItem(item)

    def filter_list(self, text):
        self.results.clear()
        search = text.lower()
        for name, short, func in self.all_commands:
            if search in name.lower(): self.add_item(name, short, func)
        
        if self.results.count() > 0 and text.strip(): 
            self.results.setCurrentRow(0)
        else:
            self.results.clearSelection()
            self.results.setCurrentRow(-1)

    def trigger_selected(self):
        item = self.results.currentItem()
        if item: self.execute_command(item)

    def execute_command(self, item):
        func = item.data(Qt.ItemDataRole.UserRole)
        if func: 
            self.hide_animated()
            func() 

    def update_theme(self):
        pass
    
    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape: self.hide_animated()
        else: super().keyPressEvent(event)

class SearchTriggerButton(QPushButton):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedWidth(280)
        self.setFixedHeight(32) 
        self.setStyleSheet(f"""
            QPushButton {{ 
                background: {CONFIG['theme']['bg']}; 
                border: 1px solid {CONFIG['theme']['selection']}; 
                border-radius: 6px; 
                text-align: left; 
            }} 
            QPushButton:hover {{ 
                /* Subtle background change (slightly brighter) */
                background: rgba(255, 255, 255, 0.08); 
                /* KEEP THE BLUE OUTLINE */
                border: 1px solid {CONFIG['theme']['function']}; 
            }}
            QPushButton:pressed {{ 
                background: {CONFIG['theme']['selection']}; 
            }}
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 10, 0)
        layout.setSpacing(8)
        
        self.lbl_icon = QLabel()
        self.lbl_icon.setPixmap(create_icon("search", CONFIG['theme']['comment'], size=14).pixmap(14, 14))
        self.lbl_icon.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        self.lbl_text = QLabel("Search commands...")
        self.lbl_text.setStyleSheet(f"color: {CONFIG['theme']['comment']}; font-size: 13px; border: none; background: transparent;")
        self.lbl_text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # TEXT ONLY SHORTCUT (NO BADGE)
        self.lbl_shortcut = QLabel("Ctrl+K")
        self.lbl_shortcut.setStyleSheet(f"""
            color: {CONFIG['theme']['comment']}; 
            background: transparent;
            border: none;
            font-family: Consolas, Monospace; 
            font-size: 12px;
            opacity: 0.7;
        """)
        self.lbl_shortcut.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        layout.addWidget(self.lbl_icon)
        layout.addWidget(self.lbl_text)
        layout.addStretch()
        layout.addWidget(self.lbl_shortcut)
        layout.setAlignment(self.lbl_shortcut, Qt.AlignmentFlag.AlignVCenter)

# --- MODERN OVERLAY BUTTON (Fixed Visibility) ---
class ModernOverlayButton(QToolButton):
    def __init__(self, parent, icon_type="close"):
        super().__init__(parent)
        self.icon_type = icon_type
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedSize(32, 32)
        self.setStyleSheet("border: none;") 
        self.hovered = False

    def enterEvent(self, event):
        self.hovered = True
        self.update()

    def leaveEvent(self, event):
        self.hovered = False
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        bg_color = QColor(0, 0, 0, 140) if self.hovered else QColor(0, 0, 0, 60)
        painter.setBrush(bg_color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(self.rect(), 4, 4)

        if self.hovered:
            fg_color = QColor("#ff5555") if self.icon_type == "close" else QColor("#89b4fa")
        else:
            fg_color = QColor(255, 255, 255, 230) 
            
        pen = QPen(fg_color)
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        rect = self.rect()
        c = rect.center()

        if self.icon_type == "close":
            s = 5
            painter.drawLine(c.x() - s, c.y() - s, c.x() + s, c.y() + s)
            painter.drawLine(c.x() + s, c.y() - s, c.x() - s, c.y() + s)
        elif self.icon_type == "fullscreen":
            s = 6
            painter.drawLine(c.x() - s, c.y() - s + 4, c.x() - s, c.y() - s)
            painter.drawLine(c.x() - s, c.y() - s, c.x() - s + 4, c.y() - s)
            painter.drawLine(c.x() + s, c.y() + s - 4, c.x() + s, c.y() + s)
            painter.drawLine(c.x() + s, c.y() + s, c.x() + s - 4, c.y() + s)
        elif self.icon_type == "restore":
            s = 6
            painter.drawLine(c.x() - s, c.y() - s + 4, c.x() - s, c.y() - s)
            painter.drawLine(c.x() - s, c.y() - s, c.x() - s + 4, c.y() - s)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(c.x()-3, c.y()-3, 6, 6)

# --- ZOOMABLE PREVIEW (Fixed Double Click Logic) ---
class ZoomablePreview(QFrame):
    def __init__(self, main_window_ref):
        super().__init__(None) 
        self.main_window = main_window_ref
        
        self.default_flags = Qt.WindowType.Tool | Qt.WindowType.FramelessWindowHint
        self.setWindowFlags(self.default_flags)
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, False)
        self.setAutoFillBackground(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        self.default_style = "QFrame { border: 2px solid #89b4fa; background-color: #1e1e2e; border-radius: 4px; }"
        self.fullscreen_style = "QFrame { background-color: rgba(0, 0, 0, 180); border: none; border-radius: 0px; }"
        self.setStyleSheet(self.default_style)
        
        self.is_video = False
        self.current_path = None
        self.saved_geometry = None 
        
        # --- Image Label ---
        self.image_label = QLabel(self)
        self.image_label.setStyleSheet("background: transparent; border: none;")
        self.image_label.setScaledContents(True)
        self.image_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        # --- Video Widget ---
        self.video_widget = QVideoWidget(self)
        self.video_widget.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.video_widget.setStyleSheet("background-color: #000000; border: none;")
        
        self.player = QMediaPlayer()
        self.audio = QAudioOutput()
        self.player.setAudioOutput(self.audio)
        self.player.setVideoOutput(self.video_widget)
        self.player.playbackStateChanged.connect(self.check_video_loop)

        # --- PAUSE OVERLAY ---
        self.pause_overlay = VideoPauseOverlay(self)

        # --- Buttons ---
        self.btn_close = ModernOverlayButton(self, "close")
        self.btn_close.clicked.connect(self.hide_preview)
        
        self.btn_expand = ModernOverlayButton(self, "fullscreen")
        self.btn_expand.clicked.connect(self.toggle_fullscreen)

        self.btn_close.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)
        self.btn_expand.setAttribute(Qt.WidgetAttribute.WA_NativeWindow, True)

        self.original_pixmap = QPixmap()
        self.is_fullscreen = False
        self.is_magnified = False 

        self.smooth_zoom = QPropertyAnimation()
        self.smooth_zoom.setDuration(150)
        self.smooth_zoom.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        # --- Click Logic ---
        self.click_timer = QTimer()
        self.click_timer.setSingleShot(True)
        self.click_timer.setInterval(250)
        self.click_timer.timeout.connect(self.handle_single_click_action)
        
        self.last_click_time = 0
        self.last_global_pos = QPoint()

        self.video_widget.setMouseTracking(True)
        self.video_widget.installEventFilter(self)
        self.setMouseTracking(True)

    def set_content(self, path):
        self.current_path = path
        video_exts = ['.mp4', '.webm', '.mkv', '.avi', '.mov']
        if any(path.lower().endswith(ext) for ext in video_exts):
            self.setup_video_mode(path)
        else:
            self.setup_image_mode(path)

    def setup_video_mode(self, path):
        self.is_video = True
        self.image_label.hide()
        self.video_widget.show()
        self.video_widget.lower() 
        self.pause_overlay.hide() 
        
        self.btn_close.setParent(self)
        self.btn_expand.setParent(self)
        
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()
        self.setFocus() 
        
        if self.is_fullscreen:
            self.fit_to_container()
        else:
            self.resize(484, 274)
            self.video_widget.setGeometry(2, 2, 480, 270)
            self.pause_overlay.setGeometry(2, 2, 480, 270)
        
        self.raise_buttons()
        QTimer.singleShot(50, self.raise_buttons)

    def setup_image_mode(self, path):
        self.is_video = False
        self.video_widget.hide()
        self.pause_overlay.hide()
        self.player.stop()
        self.image_label.show()
        self.image_label.lower() 
        
        loaded_pixmap = QPixmap(path)
        if loaded_pixmap.isNull(): return
        self.original_pixmap = loaded_pixmap
        self.is_magnified = False
        
        self.btn_close.setParent(self)
        self.btn_expand.setParent(self)
        
        if self.is_fullscreen:
            self.fit_to_container()
        else:
            w, h = self.original_pixmap.width(), self.original_pixmap.height()
            scale = min(400 / w, 400 / h) if w > 400 or h > 400 else 1.0
            new_w, new_h = int(w * scale), int(h * scale)
            self.resize(new_w + 4, new_h + 4)
            self.image_label.setGeometry(2, 2, new_w, new_h)
            self.refresh_view_quality()
        self.raise_buttons()

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_buttons()
        self.setFocus() 

    def keyPressEvent(self, event):
        if self.is_video and event.key() == Qt.Key.Key_Space:
            self.handle_single_click_action() 
        else:
            super().keyPressEvent(event)

    def wheelEvent(self, event):
        if not self.is_fullscreen or not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
            event.ignore()
            return

        delta = event.angleDelta().y()
        factor = 1.25 if delta > 0 else 0.8
        
        target_widget = self.video_widget if self.is_video else self.image_label
        curr_geo = target_widget.geometry()
        
        cursor_pos = event.position()
        rel_x = (cursor_pos.x() - curr_geo.x()) / curr_geo.width()
        rel_y = (cursor_pos.y() - curr_geo.y()) / curr_geo.height()
        
        new_w = int(curr_geo.width() * factor)
        new_h = int(curr_geo.height() * factor)
        new_x = int(cursor_pos.x() - (new_w * rel_x))
        new_y = int(cursor_pos.y() - (new_h * rel_y))
        
        self.smooth_zoom.stop()
        self.smooth_zoom.setTargetObject(target_widget)
        self.smooth_zoom.setPropertyName(b"geometry")
        self.smooth_zoom.setStartValue(curr_geo)
        self.smooth_zoom.setEndValue(QRect(new_x, new_y, new_w, new_h))
        self.smooth_zoom.start()
        
        self.is_magnified = True
        
        if self.is_video:
             self.pause_overlay.setGeometry(new_x, new_y, new_w, new_h)

        event.accept()

    def raise_buttons(self):
        if self.is_video and self.pause_overlay.isVisible():
            self.pause_overlay.raise_()
            
        self.btn_close.raise_()
        self.btn_expand.raise_()
        self.btn_close.show()
        self.btn_expand.show()
        self.btn_close.repaint()
        self.btn_expand.repaint()

    def toggle_fullscreen(self):
        QTimer.singleShot(0, self._do_toggle_fullscreen)

    def _do_toggle_fullscreen(self):
        self.hide()
        if not self.is_fullscreen:
            self.saved_geometry = self.geometry()
            self.is_fullscreen = True
            
            if self.main_window:
                self.setParent(self.main_window)
                self.setWindowFlags(Qt.WindowType.Widget)
                self.setGeometry(0, 0, self.main_window.width(), self.main_window.height())
            
            self.setStyleSheet(self.fullscreen_style)
            self.btn_expand.icon_type = "restore"
            self.show()
            self.fit_to_container()
            self.setFocus()
        else:
            self.is_fullscreen = False
            self.setParent(None)
            self.setWindowFlags(self.default_flags)
            self.setStyleSheet(self.default_style)
            self.btn_expand.icon_type = "fullscreen"
            
            if self.saved_geometry:
                self.setGeometry(self.saved_geometry)
            
            target = self.video_widget if self.is_video else self.image_label
            target.setGeometry(2, 2, self.width() - 4, self.height() - 4)
            if self.is_video: 
                self.pause_overlay.setGeometry(target.geometry())
                if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                    self.pause_overlay.show()
                    self.pause_overlay.raise_()
            
            self.style().unpolish(self)
            self.style().polish(self)
            self.show()
            self.setFocus()
        
        QTimer.singleShot(50, self.raise_buttons)

    def fit_to_container(self):
        w, h = self.width(), self.height()
        if self.is_video:
             pw, ph = 16, 9
        else:
             pw, ph = self.original_pixmap.width(), self.original_pixmap.height()
             
        scale = min((w * 0.95)/pw, (h * 0.95)/ph)
        nw, nh = int(pw*scale), int(ph*scale)
        target_rect = QRect((w-nw)//2, (h-nh)//2, nw, nh)
        
        target_widget = self.video_widget if self.is_video else self.image_label
        self.smooth_zoom.stop()
        target_widget.setGeometry(target_rect)
        
        if self.is_video: 
            self.pause_overlay.setGeometry(target_rect)
            if self.player.playbackState() != QMediaPlayer.PlaybackState.PlayingState:
                self.pause_overlay.raise_()
        
        self.is_magnified = False
        if not self.is_video: self.refresh_view_quality()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        padding = 10
        btn_w = self.btn_close.width()
        self.btn_close.move(self.width() - btn_w - padding, padding)
        self.btn_expand.move(self.width() - btn_w - padding, self.height() - btn_w - padding)
        
        if self.is_video:
            self.pause_overlay.setGeometry(self.video_widget.geometry())

        if not self.is_fullscreen:
            target = self.video_widget if self.is_video else self.image_label
            target.setGeometry(2, 2, self.width() - 4, self.height() - 4)
            if self.is_video: 
                self.pause_overlay.setGeometry(target.geometry())
        elif self.is_fullscreen and not self.is_magnified: 
            self.fit_to_container()
            
        self.raise_buttons()

    def check_video_loop(self, state):
        if state == QMediaPlayer.PlaybackState.StoppedState and self.isVisible():
            self.player.play()
            self.pause_overlay.hide()
    
    def refresh_view_quality(self):
        if self.original_pixmap.isNull(): return
        self.image_label.setPixmap(self.original_pixmap.scaled(self.image_label.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
    
    def hide_preview(self):
        self.player.stop()
        self.hide()
        if self.is_fullscreen: self.toggle_fullscreen()

    def handle_single_click_action(self):
        if self.is_video:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
                self.pause_overlay.setGeometry(self.video_widget.geometry())
                self.pause_overlay.show()
                self.pause_overlay.raise_()
                self.raise_buttons()
            else:
                self.player.play()
                self.pause_overlay.hide()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: 
            curr_time = time.time()
            if (curr_time - self.last_click_time) < 0.3:
                self.click_timer.stop() 
                self.toggle_fullscreen()
                self.last_click_time = 0 
                return
            
            self.last_click_time = curr_time
            self.last_global_pos = event.globalPosition().toPoint()
            
            child = self.childAt(event.pos())
            if child in [self.btn_close, self.btn_expand]:
                super().mousePressEvent(event)
                return
            
            if self.is_fullscreen:
                if not (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    content_widget = self.video_widget if self.is_video else self.image_label
                    if not content_widget.geometry().contains(event.pos()):
                         self.toggle_fullscreen()
                         return

            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_fullscreen and (event.buttons() & Qt.MouseButton.LeftButton) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
             self.smooth_zoom.stop()
             current_pos = event.globalPosition().toPoint()
             delta = current_pos - self.last_global_pos
             
             target = self.video_widget if self.is_video else self.image_label
             target.move(target.pos() + delta)
             
             if self.is_video:
                 self.pause_overlay.move(target.pos())

             self.last_global_pos = current_pos
             return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton: 
            self.click_timer.start()
            event.accept()
    
    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.click_timer.stop()
            self.toggle_fullscreen()
            event.accept()

    def eventFilter(self, source, event):
        if source == self.video_widget:
            if event.type() == QEvent.Type.MouseButtonPress: 
                self.mousePressEvent(event)
                return True
            
            if event.type() == QEvent.Type.MouseButtonRelease:
                self.mouseReleaseEvent(event)
                return True
            
            if event.type() == QEvent.Type.MouseMove: 
                self.raise_buttons()
                if (event.buttons() & Qt.MouseButton.LeftButton) and (event.modifiers() & Qt.KeyboardModifier.ControlModifier):
                    self.mouseMoveEvent(event)
        return super().eventFilter(source, event)
    
class NotificationPopup(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10) 
        
        self.card = QFrame()
        self.card.setObjectName("NotifyCard")
        
        card_layout = QHBoxLayout(self.card)
        card_layout.setContentsMargins(10, 10, 15, 10)
        card_layout.setSpacing(10)
        
        self.left_close_btn = QToolButton()
        self.left_close_btn.setFixedSize(26, 26)
        self.left_close_btn.setIconSize(QSize(18, 18))
        self.left_close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.left_close_btn.setToolTip("Close")
        self.left_close_btn.clicked.connect(self.hide_animated)
        
        self.text_label = QLabel()
        self.text_label.setWordWrap(False)
        self.text_label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        
        card_layout.addWidget(self.left_close_btn)
        card_layout.addWidget(self.text_label, 1)
        
        layout.addWidget(self.card)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.card.setGraphicsEffect(shadow)
        
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.hide_animated)
        
        self._active_anim_group = None

    def update_position(self):
        if not self.isVisible() or not self.parent(): return
        
        parent_geo = self.parent().geometry()
        target_x = parent_geo.x() + parent_geo.width() - self.width() - 25
        target_y = parent_geo.y() + parent_geo.height() - self.height() - 35
        
        self.move(target_x, target_y)

    def show_message(self, message, duration=3000, is_error=False):
        if self._active_anim_group:
            self._active_anim_group.stop()
            self._active_anim_group = None
        self.timer.stop()

        # --- THEME COLORS ---
        bg = CONFIG['theme']['sidebar']
        fg = CONFIG['theme']['fg']
        border = CONFIG['theme']['selection']
        accent_color = "#ff5555" if is_error else CONFIG['theme']['function']
        
        # --- STYLESHEET ---
        self.card.setStyleSheet(f"""
            #NotifyCard {{
                background-color: {bg};
                border: 1px solid {border};
                border-left: 4px solid {accent_color}; 
                border-radius: 6px;
            }}
            QLabel {{
                color: {fg};
                font-family: 'Segoe UI', sans-serif;
                font-size: 13px;
                font-weight: 600;
                border: none;
                background: transparent;
            }}
            QToolButton {{
                background: transparent;
                border: none;
                border-radius: 4px;
                padding: 2px;
            }}
            QToolButton:hover {{
                background-color: #ff5555; 
            }}
        """)
        
        self.text_label.setText(message)
        self.text_label.adjustSize()
        
        # --- ICON SETUP ---
        self.left_close_btn.setIcon(create_icon("x", fg, 18))
        
        # --- POSITIONING ---
        self.adjustSize() 
        
        if self.parent():
            parent_geo = self.parent().geometry()
            target_x = parent_geo.x() + parent_geo.width() - self.width() - 25
            target_y = parent_geo.y() + parent_geo.height() - self.height() - 35
            start_y = target_y + 20 
            
            self.move(target_x, start_y)
            self.setWindowOpacity(0.0)
            self.show()
            self.raise_()
            
            # --- ANIMATION ---
            anim_group = QParallelAnimationGroup(self)
            
            anim_pos = QPropertyAnimation(self, b"pos")
            anim_pos.setDuration(250)
            anim_pos.setStartValue(QPoint(target_x, start_y))
            anim_pos.setEndValue(QPoint(target_x, target_y))
            anim_pos.setEasingCurve(QEasingCurve.Type.OutCubic)
            
            anim_opacity = QPropertyAnimation(self, b"windowOpacity")
            anim_opacity.setDuration(200)
            anim_opacity.setStartValue(0.0)
            anim_opacity.setEndValue(1.0)
            
            anim_group.addAnimation(anim_pos)
            anim_group.addAnimation(anim_opacity)
            
            self._active_anim_group = anim_group
            anim_group.start()
            
        self.timer.start(duration)

    def hide_animated(self):
        if not self.isVisible(): return

        if self._active_anim_group:
            self._active_anim_group.stop()
            self._active_anim_group = None

        current_pos = self.pos()
        target_y = current_pos.y() + 20
        
        anim_group = QParallelAnimationGroup(self)
        
        anim_pos = QPropertyAnimation(self, b"pos")
        anim_pos.setDuration(200)
        anim_pos.setStartValue(current_pos)
        anim_pos.setEndValue(QPoint(current_pos.x(), target_y))
        anim_pos.setEasingCurve(QEasingCurve.Type.InQuad)
        
        anim_opacity = QPropertyAnimation(self, b"windowOpacity")
        anim_opacity.setDuration(150)
        anim_opacity.setStartValue(self.windowOpacity())
        anim_opacity.setEndValue(0.0)
        
        anim_group.addAnimation(anim_pos)
        anim_group.addAnimation(anim_opacity)
        
        anim_group.finished.connect(self.hide)
        
        self._active_anim_group = anim_group
        anim_group.start()
    
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        CONFIG["keybinds"]["command_palette"] = "Ctrl+K, Ctrl+Space"
        
        # 2. Unified Undo Stack
        self.action_stack = [] 
        self.redo_stack = []
        self._is_undoing = False 
        
        if QApplication.instance(): QApplication.instance().setStyle("Fusion")
        self.setWindowTitle("Zenith IDE")
        self.resize(1200, 800)
        self.file_states = {}
        self.saved_content = {} 
        self.untitled_count = 0
        self.current_file_path = None
        self.last_active_filename = None
        self.is_switching_internal = False
        self._window_actions = []
        self._extra_shortcuts = [] 
        border_col = CONFIG['theme']['selection']
        
        # --- NOTIFICATION SYSTEM ---
        self.notification_popup = NotificationPopup(self)
        
        # --- TAB SWITCHER ---
        self.tab_switcher_popup = TabSwitcherPopup(self)
    
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(20, 20))
        self.toolbar.setMovable(False)
        self.toolbar.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self.addToolBar(self.toolbar)
        
        self.btn_sidebar = QToolButton()
        self.btn_sidebar.setIcon(colorize_icon(self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowLeft), Qt.GlobalColor.white))
        self.btn_sidebar.clicked.connect(self.toggle_sidebar)
        self.toolbar.addWidget(self.btn_sidebar)
        
        spacer_l = QWidget()
        spacer_l.setSizePolicy(pd := QWidget().sizePolicy())
        pd.setHorizontalPolicy(pd.Policy.Expanding)
        spacer_l.setSizePolicy(pd)
        self.toolbar.addWidget(spacer_l)
        
        self.search_trigger = SearchTriggerButton()
        self.search_trigger.clicked.connect(self.toggle_palette)
        self.toolbar.addWidget(self.search_trigger)

        spacer_r = QWidget()
        spacer_r.setSizePolicy(pd)
        spacer_r.setSizePolicy(pd)
        self.toolbar.addWidget(spacer_r)
        
        self.btn_menu = QToolButton()
        self.btn_menu.setText("⋮")
        self.btn_menu.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        self.btn_menu.setStyleSheet("QToolButton { font-size: 22px; font-weight: bold; padding-bottom: 8px; color: white; } QToolButton::menu-indicator { image: none; }")
        self.main_menu = QMenu(self)
        self.main_menu.setObjectName("ThreeDotMenu")
        self.setup_menu()
        self.btn_menu.setMenu(self.main_menu)
        self.toolbar.addWidget(self.btn_menu)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Sidebar
        self.sidebar_container = QWidget()
        self.sidebar_container.setMaximumWidth(250)
        self.sidebar_container.setMinimumWidth(250)
        self.sidebar_container.setStyleSheet(f"background-color: {CONFIG['theme']['sidebar']}; border-right: 1px solid {border_col};")
        side_layout = QVBoxLayout(self.sidebar_container)
        side_layout.setContentsMargins(0,0,0,0)
        
        # Explorer Header
        explorer_header = QWidget()
        header_layout = QHBoxLayout(explorer_header)
        header_layout.setContentsMargins(15, 15, 15, 5)
        lbl_explorer = QLabel("EXPLORER")
        lbl_explorer.setStyleSheet("font-weight: bold; color: #7f849c; font-size: 12px; letter-spacing: 1px; border: none;")

        self.btn_new = QToolButton()
        self.btn_new.setText("+")
        self.btn_new.setToolTip("New Tab (Ctrl+T)")
        self.btn_new.setStyleSheet(f"QToolButton {{ color: white; font-weight: bold; font-size: 18px; border: none; background: transparent; border-radius: 4px; padding: 2px; }} QToolButton:hover {{ background: {CONFIG['theme']['selection']}; }} QToolButton:pressed {{ background: {CONFIG['theme']['function']}; color: #1e1e2e; }}")
        self.btn_new.clicked.connect(self.create_new_explorer_item)
        
        header_layout.addWidget(lbl_explorer)
        header_layout.addStretch()
        header_layout.addWidget(self.btn_new)
        side_layout.addWidget(explorer_header)

        # File List
        self.file_list = SidebarListWidget() 
        self.file_list.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.file_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.file_list.setTextElideMode(Qt.TextElideMode.ElideRight)
        apply_smooth_scroll(self.file_list)
        self.file_list.currentItemChanged.connect(self.switch_file_buffer)
        side_layout.addWidget(self.file_list)
        
        # Editor Area
        editor_area = QFrame()
        editor_layout = QVBoxLayout(editor_area)
        editor_layout.setContentsMargins(0,0,0,0)
        editor_layout.setSpacing(0)
        
        self.top_bar = QWidget()
        self.top_bar.setObjectName("TopBar")
        top_bar_layout = QHBoxLayout(self.top_bar)
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        
        self.breadcrumbs = QLabel("  [Untitled.txt]  ")
        
        self.btn_go_top = QToolButton()
        self.btn_go_top.setFixedSize(24, 24)
        self.btn_go_top.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_go_top.setToolTip("Go to Top")
        self.btn_go_top.setStyleSheet(f"QToolButton {{ border: none; background: transparent; border-radius: 4px; }} QToolButton:hover {{ background-color: {CONFIG['theme']['selection']}; }}")
        self.btn_go_top.clicked.connect(lambda: (self.editor.setCursorPosition(0, 0), self.editor.setFocus()))

        self.btn_close_tab_main = QToolButton()
        self.btn_close_tab_main.setObjectName("CloseBtn")
        self.btn_close_tab_main.setFixedSize(24, 24)
        self.btn_close_tab_main.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_close_tab_main.setToolTip("Close Tab (Ctrl+W)")
        self.btn_close_tab_main.setStyleSheet(f"#CloseBtn {{ border: none; background: transparent; border-radius: 4px; }} #CloseBtn:hover {{ background-color: #ff5555; }}")
        self.btn_close_tab_main.clicked.connect(self.close_current_tab)
        
        top_bar_layout.addWidget(self.breadcrumbs)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.btn_go_top)
        top_bar_layout.addWidget(self.btn_close_tab_main)
        spacer_margin = QWidget()
        spacer_margin.setFixedWidth(5)
        top_bar_layout.addWidget(spacer_margin)
        editor_layout.addWidget(self.top_bar)
        
        # --- EDITOR SETUP ---
        self.editor = ZenithEditor()
        self.editor.setStyleSheet(f"border: none; {SCROLLBAR_CSS}")
        
        # --- EDITOR LAYOUT ---
        editor_layout.addWidget(self.editor)
        apply_smooth_scroll(self.editor)
        self.editor.cursorPositionChanged.connect(self.update_cursor_stats)
        BUS.editor_text_changed.connect(self.on_editor_text_changed)

        # Image Viewer
        self.image_preview = ZoomablePreview(self)
        self.editor.cursorPositionChanged.connect(self.check_line_for_image)

        self.editor.installEventFilter(self)
        if hasattr(self.editor, 'viewport'):
            self.editor.viewport().installEventFilter(self)
        
        editor_layout.addWidget(self.editor)
        
        # Floating Bars
        self.find_bar = FindBar(self.editor)
        self.goto_bar = GoToBar(self.editor)
        self.global_search_bar = GlobalSearchBar(self.editor, self)
        
        # Status Bar
        status_container = QWidget()
        status_layout = QHBoxLayout(status_container)
        status_layout.setContentsMargins(10, 5, 10, 5)
        self.status_bar = QLabel(" Ln 1, Col 1")
        self.encoding_label = QLabel(CONFIG["editor"].get("encoding", "utf-8").upper())
        status_layout.addWidget(self.status_bar)
        status_layout.addStretch()
        status_layout.addWidget(self.encoding_label)
        editor_layout.addWidget(status_container)
        
        layout.addWidget(self.sidebar_container)
        layout.addWidget(editor_area)
        
        self.anim_side = QPropertyAnimation(self.sidebar_container, b"maximumWidth")
        self.anim_side.setDuration(250)
        self.anim_side.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self.palette = CommandPalette(self)
        BUS.ai_ghost_text_ready.connect(self.show_ghost_suggestion)
        
        self.refresh_shortcuts()
        QTimer.singleShot(0, self.delayed_startup)
        
        self.apply_theme()
        
        BUS.ai_ghost_text_ready.connect(self.show_ghost_suggestion)
        
        self.refresh_shortcuts()
        QTimer.singleShot(0, self.delayed_startup)
        self.apply_theme()

        self.history_timer = QTimer(self)
        self.history_timer.setInterval(300000)
        self.history_timer.timeout.connect(self.perform_auto_snapshot)
        self.history_timer.start()
        
    def perform_auto_snapshot(self):
        
        if self.current_file_path and os.path.exists(self.current_file_path):
            current_content = self.editor.text()
            self.create_snapshot(self.current_file_path, current_content)
            self.status_bar.setText(" Time Machine: Snapshot saved.")
        
        

    def resizeEvent(self, event):
        if self.palette.isVisible(): self.palette.update_overlay_position()

        self.find_bar.update_position()
        self.goto_bar.update_position()
        self.global_search_bar.update_position()

        if hasattr(self, 'notification_popup') and self.notification_popup.isVisible():
            pw = self.width()
            ph = self.height()
            self.notification_popup.move(pw - self.notification_popup.width() - 20, ph - self.notification_popup.height() - 40)
        super().resizeEvent(event)

    def check_line_for_image(self, line, index):

        if not self.isVisible():
            if hasattr(self, 'image_preview') and self.image_preview.isVisible() and not self.image_preview.is_fullscreen:
                self.image_preview.hide()
            return

        text = self.editor.text(line).strip()
        if not text:
            self.image_preview.hide_preview()
            return

        match = re.search(r'!\[.*?\]\((.*?)\)', text)
        clean_path = match.group(1) if match else None
        
        if not clean_path:
            match_obs = re.search(r'!\[\[(.*?)\]\]', text)
            if match_obs:
                clean_path = match_obs.group(1)

        if not clean_path:
            self.image_preview.hide_preview()
            return

        # 2. Check Extension
        valid_exts = [
            '.png', '.jpg', '.jpeg', '.gif', '.bmp', '.svg', '.webp', 
            '.mp4', '.webm', '.mkv', '.avi', '.mov'
        ]
        if not any(clean_path.lower().endswith(ext) for ext in valid_exts):
            self.image_preview.hide_preview()
            return


        potential_paths = []
        potential_paths.append(clean_path) 
        if self.current_file_path:
            base_dir = os.path.dirname(os.path.abspath(self.current_file_path))
            potential_paths.append(os.path.join(base_dir, clean_path))
        
        potential_paths.append(os.path.join(os.getcwd(), clean_path))
        potential_paths.append(os.path.join(os.path.expanduser("~"), clean_path))

        final_path = None
        for p in potential_paths:
            if os.path.exists(p) and os.path.isfile(p):
                final_path = p
                break

        if final_path:
            self.image_preview.set_content(final_path)
            
            if not self.image_preview.is_fullscreen:
                curr_pos = self.editor.SendScintilla(2008)
                y_pos = self.editor.SendScintilla(2247, 0, curr_pos)
                global_pos = self.editor.mapToGlobal(QPoint(50, y_pos + 25))
                self.image_preview.move(global_pos)
                self.image_preview.show()
            return

        self.image_preview.hide_preview()
        
    def notify(self, message, is_error=False):
        self.notification_popup.show_message(message, is_error=is_error)

    def debug_notify(self, action_name):
        if CONFIG.get("developer", {}).get("debug_notifications", False):
            self.notify(f"[Debug] {action_name}")

    def apply_theme(self):
        theme = CONFIG['theme']
        

        bg_col = QColor(theme['bg'])
        brightness = (bg_col.red() * 0.299 + bg_col.green() * 0.587 + bg_col.blue() * 0.114)
        is_light_theme = brightness > 128
        

        icon_color_qt = Qt.GlobalColor.black if is_light_theme else Qt.GlobalColor.white
        icon_css_color = "black" if is_light_theme else "white"
        
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {theme['bg']}; }}
            QLabel {{ color: {theme['fg']}; }}
            QSplitter::handle {{ background-color: {theme['sidebar']}; width: 2px; }}
            QToolBar {{ background: {theme['sidebar']}; border-bottom: 1px solid {theme['selection']}; spacing: 10px; }}
            QToolButton {{ color: {theme['fg']}; border-radius: 4px; padding: 6px; }}
            QToolButton:hover {{ background: {theme['selection']}; }}
            
            /* MENU STYLING FIX */
            QMenu {{
                background-color: {theme['sidebar']};
                color: {theme['fg']};
                border: 1px solid {theme['function']};
                border-radius: 6px;
                padding: 5px;
            }}
            QMenu::item {{ 
                padding: 5px 20px 5px 10px; 
                border-radius: 4px; 
                color: {theme['fg']}; /* Fixes invisible text in Light Mode */
            }}
            QMenu::item:selected {{ 
                background-color: {theme['selection']}; 
                color: {theme['fg']}; 
            }}
            QMenu::separator {{ background: {theme['selection']}; height: 1px; margin: 5px 0px; }}
            
            {SCROLLBAR_CSS.replace(CONFIG['theme']['sidebar'], theme['sidebar']).replace(CONFIG['theme']['selection'], theme['selection']).replace(CONFIG['theme']['function'], theme['function'])}
        """)

        self.sidebar_container.setStyleSheet(f"background-color: {theme['sidebar']}; border-right: 1px solid {theme['selection']};")
        self.top_bar.setStyleSheet(f"#TopBar {{ background: {theme['bg']}; border-bottom: 2px solid {theme['function']}; }}")

        width = self.sidebar_container.width()
        arrow_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight if width > 0 else QStyle.StandardPixmap.SP_ArrowLeft)
        self.btn_sidebar.setIcon(colorize_icon(arrow_icon, icon_color_qt))
        
        self.btn_menu.setStyleSheet(f"""
            QToolButton {{ 
                font-size: 22px; 
                font-weight: bold; 
                padding-bottom: 8px; 
                color: {icon_css_color}; /* Forces Black in Light Mode */
            }} 
            QToolButton::menu-indicator {{ image: none; }}
        """)
        
        if hasattr(self, 'btn_new'):
            self.btn_new.setStyleSheet(f"""
                QToolButton {{ 
                    color: {icon_css_color}; /* Forces Black in Light Mode */
                    font-weight: bold; 
                    font-size: 18px; 
                    border: none; 
                    background: transparent; 
                    border-radius: 4px; 
                    padding: 2px; 
                }} 
                QToolButton:hover {{ background: {theme['selection']}; }} 
                QToolButton:pressed {{ background: {theme['function']}; color: {theme['bg']}; }}
            """)

        self.breadcrumbs.setStyleSheet(f"color: {theme['comment']}; padding: 10px; font-family: Consolas; font-size: 12px; border: none;")

        btn_icon_col = theme['comment'] if not is_light_theme else "#555555"
        self.btn_go_top.setIcon(create_icon("arrow_up", btn_icon_col, size=16))
        self.btn_close_tab_main.setIcon(create_icon("x", btn_icon_col, size=16))

        self.file_list.setStyleSheet(f"""
            QListWidget {{ background: transparent; color: {theme['fg']}; border: none; padding: 10px 0px; outline: none; }} 
            QListWidget::item {{ padding: 2px; border-radius: 6px; margin: 2px 10px; border: none; color: {theme['fg']}; }} 
            QListWidget::item:hover {{ background: {theme['selection']}; }} 
            QListWidget::item:selected {{ background: {theme['function']}; color: {theme['bg']}; }}
            /* Explorer Scrollbar dynamic update */
            QScrollBar:vertical {{ border: none; background: transparent; width: 14px; margin: 16px 0 16px 0; }}
            QScrollBar::handle:vertical {{ background: {theme['function']}; min-height: 20px; border-radius: 4px; margin: 0px 4px 0px 4px; }}
            QScrollBar::handle:vertical:hover {{ background: #8caaee; }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; background: none; }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        """)

        self.status_bar.setStyleSheet(f"color: {theme['function']}; font-size: 12px; border: none;")
        self.encoding_label.setStyleSheet(f"color: {theme['comment']}; font-size: 12px; border: none;")
        self.status_bar.parent().setStyleSheet(f"background: {theme['sidebar']}; border-top: 1px solid {theme['selection']};")

        self.search_trigger.setStyleSheet(f"""
            QPushButton {{ 
                background: {theme['bg']}; 
                border: 1px solid {theme['selection']}; 
                border-radius: 6px; 
                text-align: left; 
                color: {theme['fg']};
            }} 
            QPushButton:hover {{ 
                background: {theme['selection']}; 
                border: 1px solid {theme['function']}; 
            }}
        """)
        self.search_trigger.lbl_icon.setPixmap(create_icon("search", theme['comment'], size=14).pixmap(14, 14))
        self.search_trigger.lbl_text.setStyleSheet(f"color: {theme['comment']}; font-size: 13px; border: none; background: transparent;")
        
        self.find_bar.update_theme()
        self.goto_bar.update_theme()
        self.palette.update_theme()
        
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            widget = self.file_list.itemWidget(item)
            if isinstance(widget, ExplorerItemWidget):
                widget.update_label_style()
                widget.btn_rename.setIcon(create_icon("rename_box", theme['comment'], size=24))
                widget.btn_close.setIcon(create_icon("x", theme['comment'], size=18))

        self.editor.update_appearance()
        self.apply_editor_fixes()
        
    def eventFilter(self, source, event):
        return super().eventFilter(source, event)

    def update_cursor_stats(self, line, index): 
        self.status_bar.setText(f" Ln {line + 1}, Col {index + 1}")

    def open_find_bar(self):
        if self.find_bar.isVisible():
            self.find_bar.hide_animated()
        else:
            if hasattr(self, 'goto_bar'): self.goto_bar.hide_animated()
            if hasattr(self, 'global_search_bar'): self.global_search_bar.hide_animated()
            self.find_bar.show_animated()

    def open_goto_bar(self):
        if self.goto_bar.isVisible():
            self.goto_bar.hide_animated()
        else:
            if hasattr(self, 'find_bar'): self.find_bar.hide_animated()
            if hasattr(self, 'global_search_bar'): self.global_search_bar.hide_animated()
            self.goto_bar.show_animated()

    def open_global_search(self):
        if self.global_search_bar.isVisible():
            self.global_search_bar.hide_animated()
        else:
            if hasattr(self, 'find_bar'): self.find_bar.hide_animated()
            if hasattr(self, 'goto_bar'): self.goto_bar.hide_animated()
            self.global_search_bar.show_animated()

    def open_file_at_line(self, filename, line_index):
        target_item = None
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if self.get_widget_text(item) == filename:
                target_item = item
                break
        
        if not target_item:
            return

        self.file_list.setCurrentItem(target_item)
        self.editor.setCursorPosition(line_index, 0)
        self.editor.setFocus()

    def copy_file_path(self):
        if self.current_file_path:
            QApplication.clipboard().setText(os.path.abspath(self.current_file_path))
            self.status_bar.setText(f" Copied path: {self.current_file_path}")
        else:
            self.status_bar.setText(" File not saved, cannot copy path.")

    def setup_menu(self):
        m = self.main_menu
        m.clear()
        for act in self._window_actions: self.removeAction(act)
        self._window_actions.clear()
        
        def add_action_to_window(text, slot, shortcut_key):
            act = QAction(text, self)
            seq = CONFIG["keybinds"].get(shortcut_key)
            if seq:
                keys = [QKeySequence(k.strip()) for k in seq.split(',') if k.strip()]
                if shortcut_key in ["command_palette", "new_tab"]: pass
                else: act.setShortcuts(keys)
            act.setShortcutContext(Qt.ShortcutContext.ApplicationShortcut)
            act.triggered.connect(slot)
            self.addAction(act)
            self._window_actions.append(act)
            return act
        
        m.addAction(add_action_to_window("Open...", self.open_file, "open"))
        m.addAction(add_action_to_window("Save", self.save_file, "save"))
        m.addAction(add_action_to_window("Save As...", self.save_as, ""))
        add_action_to_window("Close Tab", self.close_current_tab, "close_tab")
        add_action_to_window("Toggle Sidebar", self.toggle_sidebar, "sidebar_toggle")
        add_action_to_window("Palette", self.toggle_palette, "command_palette")
        m.addSeparator()
        
        if hasattr(self, 'find_bar') and hasattr(self, 'goto_bar'):
            act_find = QAction("Find Text", self)
            act_find.setShortcut("Ctrl+F")
            act_find.triggered.connect(self.open_find_bar)
            self.addAction(act_find)  
            self._window_actions.append(act_find)

            act_goto = QAction("Go to Line", self)
            act_goto.setShortcut("Ctrl+G")
            act_goto.triggered.connect(self.open_goto_bar)
            self.addAction(act_goto)
            self._window_actions.append(act_goto)

        # --- GLOBAL SEARCH (New) ---
        act_global = QAction("Global Find", self)
        act_global.setShortcut("Ctrl+Shift+F")
        act_global.triggered.connect(self.open_global_search)
        self.addAction(act_global)
        self._window_actions.append(act_global)

        # --- COPY PATH HOTKEY ---
        act_copy_path = QAction("Copy File Path", self)
        act_copy_path.setShortcut("Ctrl+Shift+C")
        act_copy_path.triggered.connect(self.copy_file_path)
        self.addAction(act_copy_path)
        self._window_actions.append(act_copy_path)
        
        m.addSeparator()
        act_set = QAction("Settings", self)
        act_set.triggered.connect(self.open_settings)
        m.addAction(act_set)

    def toggle_sidebar(self):
        width = self.sidebar_container.width()
        base_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_ArrowRight if width > 0 else QStyle.StandardPixmap.SP_ArrowLeft)
        self.btn_sidebar.setIcon(colorize_icon(base_icon, Qt.GlobalColor.white))
        if width > 0: 
            self.sidebar_container.setMinimumWidth(0)
            self.anim_side.setStartValue(width)
            self.anim_side.setEndValue(0)
        else: 
            self.anim_side.setStartValue(0)
            self.anim_side.setEndValue(250)
            self.sidebar_container.setMinimumWidth(0) 
        self.anim_side.start()

    def refresh_explorer(self): pass

    def open_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "All Files (*)")
        if path: 
            if self.last_active_filename: self.file_states[self.last_active_filename] = self.editor.text()
            fname = os.path.basename(path)
            found = False
            for i in range(self.file_list.count()):
                item = self.file_list.item(i)
                if self.get_widget_text(item) == fname: 
                    self.file_list.setCurrentItem(item)
                    found = True
                    break
            if not found: 
                item = self.add_sidebar_item(fname)
                self.file_list.setCurrentItem(item)


    def save_file(self):
        item = self.file_list.currentItem()
        if not item: return
        name = self.get_widget_text(item)
        content = self.editor.text()
        
        self.file_states[name] = content
        self.saved_content[name] = content
        
        widget = self.file_list.itemWidget(item)
        if isinstance(widget, ExplorerItemWidget): widget.set_dirty(False)
        self.editor.setModified(False)

        if os.path.exists(name):
             enc = CONFIG["editor"].get("encoding", "utf-8")
             try:
                with open(name, 'w', encoding=enc) as f: 
                    f.write(content)
                
                self.notify(f"Saved {os.path.basename(name)}")
                
                if CONFIG.get("behavior", {}).get("enable_local_history", True):
                    self.create_snapshot(name, content)

             except Exception as e:
                 QMessageBox.critical(self, "Save Error", str(e))
        else: self.save_as()

    def perform_auto_snapshot(self):
        if not CONFIG.get("behavior", {}).get("enable_local_history", True):
            return

        if self.current_file_path and os.path.exists(self.current_file_path):
            current_content = self.editor.text()
            self.create_snapshot(self.current_file_path, current_content)
            self.status_bar.setText(" Time Machine: Snapshot saved.")

    def save_as(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save As", "", "Text Files (*.txt);;All Files (*)")
        if path:
            if not os.path.splitext(path)[1]:
                path += ".txt"
            enc = CONFIG["editor"].get("encoding", "utf-8")
            with open(path, 'w', encoding=enc) as f: 
                f.write(self.editor.text())
            item = self.file_list.currentItem()
            if item:
                old_name = self.get_widget_text(item)
                new_name = os.path.basename(path)
                widget = self.file_list.itemWidget(item)
                if isinstance(widget, ExplorerItemWidget): 
                    widget.set_text(new_name)
                    widget.is_new = False
                    widget.set_dirty(False)
                    widget.set_selected_visuals(True)
                if old_name in self.file_states: 
                    self.file_states[new_name] = self.file_states.pop(old_name)
                    self.last_active_filename = new_name
                
                if old_name in self.saved_content:
                    self.saved_content.pop(old_name)
                self.saved_content[new_name] = self.editor.text()

                self.current_file_path = path
                self.editor.set_lexer_from_filename(new_name)
                self.editor.setModified(False)
                self.apply_editor_fixes()

    def open_settings(self): 
        SettingsDialog(self).exec()
        self.debug_notify("Settings Dialog Closed")

    def toggle_palette(self):
        if self.palette.isVisible(): 
            self.palette.hide_animated()
            self.editor.setFocus()
            self.debug_notify("Command Palette Closed")
        else: 
            self.palette.show_animated()
            self.debug_notify("Command Palette Opened")

    def changeEvent(self, event):
        if event.type() == QEvent.Type.ActivationChange:
            if not self.isActiveWindow():
                if hasattr(self, 'palette'): 
                    self.palette.hide_animated()
                
                if hasattr(self, 'image_preview') and self.image_preview.isVisible():
                    if not self.image_preview.is_fullscreen:
                        self.image_preview.hide_preview()

        super().changeEvent(event)

    def show_ghost_suggestion(self, text): 
        self.status_bar.setText(f" Agent Suggestion: [Tab] {text}")

    def closeEvent(self, event):
        if hasattr(self, 'image_preview'):
            self.image_preview.close()
            self.image_preview.deleteLater()
        super().closeEvent(event)

    def apply_editor_fixes(self):
        self.editor.SendScintilla(2516, 1) 
        sidebar_bg = QColor(CONFIG['theme']['sidebar'])
        text_fg = QColor(CONFIG['theme']['comment'])
        if hasattr(self.editor, "setMarginsBackgroundColor"):
            self.editor.setMarginsBackgroundColor(sidebar_bg)
        if hasattr(self.editor, "setMarginsForegroundColor"):
            self.editor.setMarginsForegroundColor(text_fg)

    def delayed_startup(self):
        if self.file_list.count() == 0:
            self.create_new_explorer_item(register_undo=False) 
        else:
            self.file_list.setCurrentRow(0)
        self.apply_editor_fixes()

    def refresh_shortcuts(self):
        self.setup_menu() 
        for sc in self._extra_shortcuts: sc.setEnabled(False)
        self._extra_shortcuts.clear()
        
        def create_shortcut(seq_str, callback):
            if not seq_str: return
            for part in seq_str.split(','):
                part = part.strip()
                if part:
                    sc = QShortcut(QKeySequence(part), self)
                    sc.setContext(Qt.ShortcutContext.WindowShortcut)
                    sc.activated.connect(callback)
                    self._extra_shortcuts.append(sc)

        create_shortcut(CONFIG["keybinds"].get("new_tab", "Ctrl+T"), self.create_new_explorer_item)
        create_shortcut(CONFIG["keybinds"].get("command_palette", "Ctrl+K, Ctrl+Space"), self.toggle_palette)
        create_shortcut("Ctrl+Z", self.global_undo)
        create_shortcut("Ctrl+Y", self.global_redo)
        create_shortcut("Ctrl+Tab", self.next_tab)
        create_shortcut("Ctrl+Shift+Tab", self.prev_tab)
        create_shortcut(CONFIG["keybinds"].get("rename_tab", "Ctrl+R"), self.rename_current_tab)
        
    def _handle_shortcut_feedback(self): pass

    def next_tab(self):
        """Show tab switcher popup moving to next tab (Ctrl+Tab)."""
        if self.tab_switcher_popup.isVisible():
            self.tab_switcher_popup.cycle(1)
        else:
            self.tab_switcher_popup.show_switcher(direction=1)

    def prev_tab(self):
        """Show tab switcher popup moving to previous tab (Ctrl+Shift+Tab)."""
        if self.tab_switcher_popup.isVisible():
            self.tab_switcher_popup.cycle(-1)
        else:
            self.tab_switcher_popup.show_switcher(direction=-1)

    def update_status_encoding(self): 
        self.encoding_label.setText(CONFIG["editor"].get("encoding", "utf-8").upper())

    def get_widget_text(self, item): 
        widget = self.file_list.itemWidget(item)
        return widget.text() if isinstance(widget, ExplorerItemWidget) else item.text()

    def switch_file_buffer(self, current, previous):
        if self.is_switching_internal: return
        if previous:
            prev_widget = self.file_list.itemWidget(previous)
            if isinstance(prev_widget, ExplorerItemWidget): prev_widget.set_selected_visuals(False)
            self.file_states[self.get_widget_text(previous)] = self.editor.text()
        elif self.last_active_filename: self.file_states[self.last_active_filename] = self.editor.text()
        
        if current:
            self.editor.setDisabled(False)
            self.editor.setVisible(True)
            self.top_bar.setVisible(True)
            curr_widget = self.file_list.itemWidget(current)
            if isinstance(curr_widget, ExplorerItemWidget): curr_widget.set_selected_visuals(True)
            curr_name = self.get_widget_text(current)
            self.last_active_filename = curr_name
            self.breadcrumbs.setText(f"  {curr_name}  ")
            
            if curr_name not in self.file_states:
                if os.path.exists(curr_name):
                    self.editor.setDisabled(True) 
                    enc = CONFIG["editor"].get("encoding", "utf-8")
                    self.loader = FileLoadWorker(curr_name, enc)
                    self.loader.finished_loading.connect(self.on_file_loaded)
                    self.loader.start()
                    return 
                else:
                    self.file_states[curr_name] = ""
                    self.current_file_path = None
            
            self._finalize_switch(curr_name)
        else: 
            self.editor.setDisabled(True)
            self.editor.setVisible(False)
            self.top_bar.setVisible(False)
            
    def create_snapshot(self, filepath, content):
       
        if not filepath or not content: return

        try:
            file_dir = os.path.dirname(filepath)
            history_dir = os.path.join(file_dir, ".zenith_history")
            
            if not os.path.exists(history_dir):
                os.makedirs(history_dir)
                if os.name == 'nt':
                    import ctypes
                    ctypes.windll.kernel32.SetFileAttributesW(history_dir, 2)

            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = os.path.basename(filepath)
            backup_name = f"{filename}_{timestamp}.bak"
            backup_path = os.path.join(history_dir, backup_name)

            enc = CONFIG["editor"].get("encoding", "utf-8")
            with open(backup_path, 'w', encoding=enc) as f:
                f.write(content)
            
            
        except Exception as e:
            print(f"Time Machine Error: {e}")

    def on_file_loaded(self, name, content, success):
        self.editor.setDisabled(False)
        if success:
            self.file_states[name] = content
            self.saved_content[name] = content
            self.current_file_path = name
        else:
            QMessageBox.critical(self, "Error", f"Could not read file: {content}")
            self.file_states[name] = ""
            
        if name == self.last_active_filename:
            self._finalize_switch(name)

    def _finalize_switch(self, curr_name):
        content = self.file_states.get(curr_name, "")
        self.is_switching_internal = True
        self.editor.setText(content)
        self.editor.set_lexer_from_filename(curr_name)
        self.editor.setModified(False)
        self.is_switching_internal = False
        self.apply_editor_fixes()
        
        # --- FIXED: UPDATE GOTO BAR LIMITS ON TAB SWITCH ---
        if hasattr(self, 'goto_bar') and self.goto_bar.isVisible():
            self.goto_bar.update_limits_if_needed()

    def on_editor_text_changed(self, text):
        if self.is_switching_internal: return
        
        if CONFIG.get("behavior", {}).get("enable_command_undo", False):
            self.record_editor_action()

        item = self.file_list.currentItem()
        if item:
            widget = self.file_list.itemWidget(item)
            if isinstance(widget, ExplorerItemWidget):
                curr_name = widget.text()
                clean = self.saved_content.get(curr_name, "")
                is_dirty = (self.editor.text() != clean)
                if widget.is_dirty != is_dirty:
                    widget.set_dirty(is_dirty)

        try:
            line, idx = self.editor.getCursorPosition()
            self.check_line_for_image(line, idx)
        except:
            pass

    def add_sidebar_item(self, name, is_new=False):
        item = QListWidgetItem()
        item.setSizeHint(QSize(0, 34))
        self.file_list.addItem(item)
        self.file_list.setItemWidget(item, ExplorerItemWidget(name, item, self, is_new))
        return item

    # --- UNIFIED PRIORITY UNDO SYSTEM ---
    def register_command_action(self, undo_func, redo_func):
        """Pushes a Command action onto the unified stack."""
        self.action_stack.append(('cmd', undo_func, redo_func))
        self.redo_stack.clear()

    def record_editor_action(self):
        """Marks the top of the stack as an editor session."""
        if self._is_undoing: return
        if not self.action_stack or self.action_stack[-1][0] != 'editor':
            self.action_stack.append(['editor', 1])
            self.redo_stack.clear()

    def global_undo(self):
        """Decides whether to undo Editor text or App Command based on stack order."""
        if not self.action_stack:
            return

        self._is_undoing = True
        top_item = self.action_stack[-1]
        action_type = top_item[0]

        if action_type == 'editor':
            self.editor.undo()
            
            if not self.editor.isUndoAvailable():
                self.action_stack.pop()
                
        elif action_type == 'cmd':
            undo_func = top_item[1]
            redo_func = top_item[2]
            undo_func()
            self.redo_stack.append(self.action_stack.pop())

        self._is_undoing = False

    def global_redo(self):
        if self.redo_stack:
            item = self.redo_stack.pop()
            if item[0] == 'cmd':
                redo_func = item[2]
                redo_func()
                self.action_stack.append(item)
        else:
            self.editor.redo()

    def restore_tab(self, name, content):
        item = self.create_new_explorer_item(name=name, register_undo=False)
        self.file_states[name] = content
        self.saved_content[name] = content 
        self.editor.setText(content)
        self.apply_editor_fixes()

    def close_tab_by_name(self, name):
        for i in range(self.file_list.count()):
            item = self.file_list.item(i)
            if self.get_widget_text(item) == name:
                self._do_close_tab(item, register_undo=False)
                break

    # --- ACTION PRIMITIVES ---
    
    def create_new_explorer_item(self, name=None, register_undo=False):
        if self.last_active_filename and self.last_active_filename in self.file_states:
             self.file_states[self.last_active_filename] = self.editor.text()
        
        if name:
            new_name = name
        else:
            existing_untitled = []
            for k in self.file_states.keys():
                match = re.match(r"Untitled (\d+)\.txt", k)
                if match:
                    existing_untitled.append(int(match.group(1)))
            
            check_num = 1
            while True:
                if check_num not in existing_untitled:
                    break
                check_num += 1
            
            new_name = f"Untitled {check_num}.txt"
            
        self.file_states[new_name] = ""
        self.saved_content[new_name] = "" 
        item = self.add_sidebar_item(new_name, is_new=True)
        self.file_list.takeItem(self.file_list.row(item))
        self.file_list.insertItem(0, item)
        self.file_list.setItemWidget(item, ExplorerItemWidget(new_name, item, self, is_new=True))
        self.file_list.setCurrentItem(item)
        self.editor.setFocus()
        self.editor.set_lexer_from_filename(new_name)
        
        self.editor.setModified(False) 
        
        self.apply_editor_fixes()
        self.debug_notify("New Tab Opened")
        
        if register_undo and CONFIG.get("behavior", {}).get("enable_command_undo", False):
            self.register_command_action(
                lambda: self.close_tab_by_name(new_name),
                lambda: self.create_new_explorer_item(name=new_name, register_undo=False)
            )
        return item 

    def close_current_tab(self, register_undo=False):
        item = self.file_list.currentItem()
        if item: 
            self._do_close_tab(item, register_undo=register_undo)

    def close_explorer_tab(self, item):
        self._do_close_tab(item, register_undo=False)
        self.debug_notify("Tab Closed")

    def _do_close_tab(self, item, register_undo=False):
        name = self.get_widget_text(item)
        content = self.file_states.get(name, self.editor.text() if name == self.last_active_filename else "")
        
        if name in self.file_states: del self.file_states[name]
        if name in self.saved_content: del self.saved_content[name]
        self.file_list.takeItem(self.file_list.row(item))
        
        if register_undo and CONFIG.get("behavior", {}).get("enable_command_undo", False):
            self.register_command_action(
                lambda: self.restore_tab(name, content),
                lambda: self.close_tab_by_name(name)
            )
            
        if self.file_list.count() == 0: QApplication.quit()

    def rename_current_tab(self, register_undo=False):
        item = self.file_list.currentItem()
        if not item: return
        widget = self.file_list.itemWidget(item)
        if isinstance(widget, ExplorerItemWidget):
            widget.start_rename()

    def perform_tab_rename(self, old_name, new_name, register_undo=False):
        if old_name in self.file_states:
            self.file_states[new_name] = self.file_states.pop(old_name)
        if old_name in self.saved_content:
            self.saved_content[new_name] = self.saved_content.pop(old_name)
            
        item_found = None
        for i in range(self.file_list.count()):
            it = self.file_list.item(i)
            if self.get_widget_text(it) == old_name:
                item_found = it
                break
        
        if item_found:
            widget = self.file_list.itemWidget(item_found)
            if isinstance(widget, ExplorerItemWidget): widget.set_text(new_name)
            
            if self.last_active_filename == old_name:
                self.last_active_filename = new_name
                self.breadcrumbs.setText(f"  {new_name}  ")
                self.editor.set_lexer_from_filename(new_name)
                self.apply_editor_fixes()

        if register_undo and CONFIG.get("behavior", {}).get("enable_command_undo", False):
            self.register_command_action(
                lambda: self.perform_tab_rename(new_name, old_name, register_undo=False),
                lambda: self.perform_tab_rename(old_name, new_name, register_undo=False)
            )

    def moveEvent(self, event):

        if self.palette.isVisible(): 
            self.palette.update_overlay_position()
            
        if hasattr(self, 'notification_popup'):
            self.notification_popup.update_position()
            
        super().moveEvent(event)
