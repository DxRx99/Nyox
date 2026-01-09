import sys
from PyQt6.QtWidgets import QApplication, QToolTip
from PyQt6.QtGui import QFont
from src.ui import MainWindow
from src.agent import AgentWorker
from src.updater import UPM # Import the UPM

def main():
    app = QApplication(sys.argv)
    
    # --- UPM CHECK ---
    # Check for updates silently on startup
    if UPM.check_for_updates():
        print("Update available. In a real app, prompt user here.")
        # UPM.apply_update() 

    app.setStyle("Fusion")
    
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    QToolTip.setFont(default_font)
    
    window = MainWindow()
    window.show()
    
    agent = AgentWorker()
    agent.start()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
