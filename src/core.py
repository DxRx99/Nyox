# src/core.py
import json
import os
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """ Central communication hub. """
    editor_text_changed = pyqtSignal(str)
    ai_ghost_text_ready = pyqtSignal(str)
    
BUS = EventBus()

# Default Configuration
DEFAULT_CONFIG = {
    "theme": {
        "bg": "#1e1e2e",  
        "fg": "#cdd6f4",
        "sidebar": "#181825", 
        "selection": "#45475a",
        "comment": "#6c7086",
        "keyword": "#cba6f7",
        "string": "#a6e3a1",
        "function": "#89b4fa"
    },
    "editor": {
        "font_family": "Consolas",
        "font_size": 13,
        "show_line_numbers": True,
        "cursor_blinking": True,
        "encoding": "utf-8",
        "enable_autocomplete": True,
        "enable_syntax_highlighting": True
    },
    "app": {
        "auto_save": False,
        "theme_name": "Default Dark"
    },
    "keybinds": {
        "sidebar_toggle": "Ctrl+B",
        "command_palette": "Ctrl+K, Ctrl+Space",
        "save": "Ctrl+S",
        "open": "Ctrl+O",
        "new_tab": "Ctrl+T",
        "close_tab": "Ctrl+W",
        "rename_tab": "Ctrl+R"
    },
    "behavior": {
        "enable_command_undo": False
    }
}

CONFIG_FILE = "config.json"

def get_scrollbar_css(bg, sel, func):
    return f"""
    QScrollBar:vertical {{ border: none; background: {bg}; width: 14px; margin: 0px; border-left: 1px solid {sel}; }}
    QScrollBar::handle:vertical {{ background: {func}; min-height: 20px; border-radius: 4px; margin: 2px 3px 2px 3px; }}
    QScrollBar::handle:vertical:hover {{ background: #8caaee; }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
    """

def load_config():
    """Loads config from JSON file, or returns defaults if missing."""
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
                # Merge saved config with defaults
                for key, val in DEFAULT_CONFIG.items():
                    if key not in saved_config:
                        saved_config[key] = val
                    elif isinstance(val, dict):
                        for subkey, subval in val.items():
                            if subkey not in saved_config[key]:
                                saved_config[key][subkey] = subval
                return saved_config
        except:
            print("Failed to load config, using defaults.")
    return DEFAULT_CONFIG.copy()

def save_config():
    """Saves current CONFIG to JSON file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(CONFIG, f, indent=4)
    except Exception as e:
        print(f"Failed to save config: {e}")

CONFIG = load_config()
STYLES = {
    "scrollbar": get_scrollbar_css(CONFIG['theme']['sidebar'], CONFIG['theme']['selection'], CONFIG['theme']['function'])
}