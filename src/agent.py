# src/agent.py
import time
from PyQt6.QtCore import QThread, pyqtSignal
from .core import BUS

class AgentWorker(QThread):
    def run(self):
        # Placeholder for AI logic
        while True:
            time.sleep(10)
            # BUS.ai_ghost_text_ready.emit("print('Hello World')")