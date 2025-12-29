# src/core.py
import json
import os
import copy  # Added for deepcopy
from PyQt6.QtCore import QObject, pyqtSignal

class EventBus(QObject):
    """ Central communication hub. """
    editor_text_changed = pyqtSignal(str)
    ai_ghost_text_ready = pyqtSignal(str)
    
BUS = EventBus()

# --- THEME DEFINITIONS ---
THEME_PALETTES = {
    "Default Dark": {
        "bg": "#1e1e2e", "fg": "#cdd6f4", "sidebar": "#181825", 
        "selection": "#45475a", "comment": "#6c7086", "keyword": "#cba6f7", 
        "string": "#a6e3a1", "function": "#89b4fa"
    },
    "Light": {
        "bg": "#ffffff", "fg": "#2c3e50", "sidebar": "#f0f0f0", 
        "selection": "#d6d6d6", "comment": "#95a5a6", "keyword": "#e74c3c", 
        "string": "#27ae60", "function": "#2980b9"
    },
    "High Contrast": {
        "bg": "#000000", "fg": "#ffffff", "sidebar": "#000000", 
        "selection": "#1a1a1a", "comment": "#00ff00", "keyword": "#ffff00", 
        "string": "#00ffff", "function": "#ff00ff"
    },
    "Dracula": {
        "bg": "#282a36", "fg": "#f8f8f2", "sidebar": "#21222c", 
        "selection": "#44475a", "comment": "#6272a4", "keyword": "#ff79c6", 
        "string": "#f1fa8c", "function": "#8be9fd"
    },
    "Monokai": {
        "bg": "#272822", "fg": "#f8f8f2", "sidebar": "#1e1f1c", 
        "selection": "#49483e", "comment": "#75715e", "keyword": "#f92672", 
        "string": "#e6db74", "function": "#66d9ef"
    },
    "Solarized": {
        "bg": "#002b36",       
        "fg": "#839496",       
        "sidebar": "#00212B",  
        "selection": "#073642",
        "comment": "#586e75",  
        "keyword": "#859900",  
        "string": "#2aa198",   
        "function": "#268bd2"  
    },
    "Nord": {
        "bg": "#2e3440", "fg": "#d8dee9", "sidebar": "#292e39", 
        "selection": "#434c5e", "comment": "#616e88", "keyword": "#81a1c1", 
        "string": "#a3be8c", "function": "#88c0d0"
    },
    "Gruvbox": {
        "bg": "#282828", "fg": "#ebdbb2", "sidebar": "#1d2021", 
        "selection": "#3c3836", "comment": "#928374", "keyword": "#fb4934", 
        "string": "#b8bb26", "function": "#83a598"
    }
}

# Default Configuration
DEFAULT_CONFIG = {
    "theme": THEME_PALETTES["Default Dark"].copy(),
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
        "rename_tab": "Ctrl+R",
        "find_text": "Ctrl+F",
        "global_find": "Ctrl+Shift+F",
        "goto_line": "Ctrl+G",
        "copy_path": "Ctrl+Shift+C",
        "undo": "Ctrl+Z",
        "redo": "Ctrl+Y",
        "cut": "Ctrl+X",
        "copy": "Ctrl+C",
        "paste": "Ctrl+V",
        "select_all": "Ctrl+A",
        "zoom_in": "Ctrl++",
        "zoom_out": "Ctrl+-"
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
    """Loads config from JSON file with safe merging."""
    # 1. Start with a pristine deep copy of defaults
    final_config = copy.deepcopy(DEFAULT_CONFIG)
    
    saved_config = {}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                saved_config = json.load(f)
        except Exception as e:
            print(f"Failed to load config file: {e}")
            saved_config = {}

    # 2. Recursive Merge Strategy
    # This ensures we keep user settings but add any new keys from defaults
    for section, default_val in DEFAULT_CONFIG.items():
        if section not in saved_config:
            continue # Use the default we already set in final_config
        
        user_val = saved_config[section]
        
        if isinstance(default_val, dict) and isinstance(user_val, dict):
            # Update dictionary keys individually
            for key, val in user_val.items():
                final_config[section][key] = val
        else:
            # Direct value update (strings, bools)
            final_config[section] = user_val

    # 3. ENFORCE THEME PALETTE
    # This is the critical fix. We trust the 'theme_name' and reload the palette 
    # from source to ensure colors are correct (and not stale or broken).
    theme_name = final_config.get("app", {}).get("theme_name", "Default Dark")
    
    if theme_name in THEME_PALETTES:
        final_config["theme"] = THEME_PALETTES[theme_name].copy()
    else:
        # Fallback if theme name is invalid
        final_config["app"]["theme_name"] = "Default Dark"
        final_config["theme"] = THEME_PALETTES["Default Dark"].copy()
        
    return final_config

def save_config():
    """Saves current CONFIG to JSON file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            json.dump(CONFIG, f, indent=4)
            f.flush() # Ensure it hits the disk
            os.fsync(f.fileno())
    except Exception as e:
        print(f"Failed to save config: {e}")

# Load immediately on module import
CONFIG = load_config()

# Helper styles based on loaded config
STYLES = {
    "scrollbar": get_scrollbar_css(CONFIG['theme']['sidebar'], CONFIG['theme']['selection'], CONFIG['theme']['function'])
}
