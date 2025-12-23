import sys
from PyQt6.QtWidgets import QApplication, QToolTip
from PyQt6.QtGui import QFont
from src.ui import MainWindow
from src.agent import AgentWorker

def main():
    app = QApplication(sys.argv)
    
    # CRITICAL FIX 1: Use 'Fusion' style. 
    # Windows native style ignores custom scrollbar rounding (border-radius).
    # Fusion style respects all CSS styling.
    app.setStyle("Fusion")
    
    # CRITICAL FIX 2: Set global font + ToolTip font to stop terminal spam.
    # The "Point size <= 0" error often comes from uninitialized ToolTips or Popups.
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    QToolTip.setFont(default_font)
    
    # Start the UI
    window = MainWindow()
    window.show()
    
    # Start the Agent (Background Thread)
    agent = AgentWorker()
    agent.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
