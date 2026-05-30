import sys
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout
from PyQt5.QtCore import QTimer, QTime, Qt, QDateTime
from PyQt5.QtGui import QFont, QPalette, QColor

class FashionClock(QWidget):
    def __init__(self):
        super().__init__()
        self.color_angle = 0
        self.initUI()

    def initUI(self):
        # Background: Pure Black
        palette = self.palette()
        palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.setPalette(palette)
        self.setAutoFillBackground(True)

        self.layout = QVBoxLayout()
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Main Clock Label
        self.timeLabel = QLabel(self)
        self.timeLabel.setAlignment(Qt.AlignCenter)
        
        # Secondary Countdown Label
        self.countdownLabel = QLabel(self)
        self.countdownLabel.setAlignment(Qt.AlignCenter)
        self.countdownLabel.hide() # Hidden by default
        
        self.layout.addWidget(self.timeLabel)
        self.layout.addWidget(self.countdownLabel)
        self.setLayout(self.layout)
        
        # Timer for updates
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_display)
        self.timer.start(100)

        self.update_display()
        self.showFullScreen()

    def update_display(self):
        now = QDateTime.currentDateTime().time()
        hour = now.hour()
        
        # 1. Update Time Text
        time_text = now.toString('hh:mm:ss')
        self.timeLabel.setText(time_text)
        
        # 2. Logic for Modes
        is_night = hour >= 22 or hour < 6
        is_countdown = hour == 21 # 21:00 to 22:00
        
        if is_night:
            # Red Mode
            self.timeLabel.setStyleSheet("color: #ff3333; font-family: 'Manrope'; font-weight: bold; font-size: 300pt;")
            self.countdownLabel.hide()
        else:
            # Day Mode & Countdown Mode both use Colorful Clock
            self.color_angle = (self.color_angle + 2) % 360
            color = QColor.fromHsv(self.color_angle, 200, 255)
            hex_color = color.name()
            self.timeLabel.setStyleSheet(f"color: {hex_color}; font-family: 'Manrope'; font-weight: bold; font-size: 300pt;")
            
            if is_countdown:
                # Add the 22:00 countdown label
                target = QTime(22, 0, 0)
                diff = now.secsTo(target)
                mins = diff // 60
                secs = diff % 60
                countdown_text = f"22:00 IN {mins:02}:{secs:02}"
                self.countdownLabel.setText(countdown_text)
                self.countdownLabel.setStyleSheet("color: #ffffff; font-family: 'Manrope'; font-weight: bold; font-size: 40pt; opacity: 0.7;")
                self.countdownLabel.show()
            else:
                self.countdownLabel.hide()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FashionClock()
    sys.exit(app.exec_())
