import sys
from PyQt6.QtWidgets import QApplication, QToolTip
from PyQt6.QtGui import QFont
from src.ui import MainWindow
from src.updater import UPM 

def main():
    app = QApplication(sys.argv)
    

    has_update, msg = UPM.check_for_updates()
    if has_update:
        print("Update Available Please Update Nyox")

    app.setStyle("Fusion")
    
    default_font = QFont("Segoe UI", 10)
    app.setFont(default_font)
    QToolTip.setFont(default_font)
    
    window = MainWindow()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
