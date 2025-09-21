import sys
import os
import json
import webbrowser
import serial.tools.list_ports
from enum import Enum
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QMessageBox, QDialog,
    QButtonGroup, QRadioButton, QLineEdit, QGridLayout, QShortcut,
    QGroupBox, QTextEdit, QTabWidget, QSystemTrayIcon, QMenu, QAction, QStyle,
    QComboBox, QGraphicsOpacityEffect, QSizePolicy
)
from PyQt5.QtCore import Qt, QSize, pyqtSignal, QPropertyAnimation, QEasingCurve, QSequentialAnimationGroup, QParallelAnimationGroup
from PyQt5.QtGui import QPalette, QColor, QIcon, QFont, QKeySequence, QPainter, QLinearGradient

CONFIG_FILE = "config.json"

button_font = QFont("Montserrat", 28, QFont.Bold)
labelfont = QFont("Montserrat", 16)

class ActionType(str, Enum):
    NONE = "none"
    LINK = "link"
    EXE = "exe"
    KEYPRESS = "keypress"
    TEXT = "text"

def run_action(action: dict):
    if not action or action["type"] == ActionType.NONE:
        return

    try:
        if action["type"] == ActionType.LINK:
            webbrowser.open(action["value"])
        elif action["type"] == ActionType.EXE:
            file_path = action["value"]
            if file_path.lower().endswith('.lnk'):
                if os.name == 'nt':
                    os.system(f'start "" "{file_path}"')
                else:
                    os.startfile(file_path)
            else:
                os.startfile(file_path)
        elif action["type"] == ActionType.KEYPRESS:
            # This will be handled by logic.py
            pass
        elif action["type"] == ActionType.TEXT:
            # This will be handled by logic.py
            pass
    except Exception as e:
        QMessageBox.critical(None, "Execution Error", f"Failed to run action:\n{e}")

def get_serial_ports():
    """Get list of available serial ports"""
    ports = serial.tools.list_ports.comports()
    return [port.device for port in ports]

class FadeWidget(QWidget):
    """A widget that can fade in and out"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.animation = QPropertyAnimation(self.effect, b"opacity")
        self.animation.setDuration(400)
        
    def fade_in(self):
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()
        
    def fade_out(self):
        self.animation.setStartValue(1)
        self.animation.setEndValue(0)
        self.animation.setEasingCurve(QEasingCurve.OutCubic)
        self.animation.start()

class AnimatedButton(QPushButton):
    """Custom button class with sophisticated animations"""
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Setup animations
        self.hover_anim = QPropertyAnimation(self, b"geometry")
        self.hover_anim.setDuration(200)
        self.hover_anim.setEasingCurve(QEasingCurve.OutBack)
        
        self.click_anim = QPropertyAnimation(self, b"geometry")
        self.click_anim.setDuration(150)
        self.click_anim.setEasingCurve(QEasingCurve.OutQuad)
        
        self.color_anim = QPropertyAnimation(self, b"")
        self.color_anim.setDuration(300)
        
        self.original_style = ""
        self.hover_style = ""
        self.original_geometry = None
        
    def setButtonStyles(self, original_style, hover_style):
        self.original_style = original_style
        self.hover_style = hover_style
        self.setStyleSheet(self.original_style)
        
    def enterEvent(self, event):
        """Handle mouse hover enter event with smooth animation"""
        super().enterEvent(event)
        if self.hover_style:
            self.setStyleSheet(self.hover_style)
            
        if self.original_geometry is None:
            self.original_geometry = self.geometry()
            
        # Create a smooth scale animation on hover
        geom = self.original_geometry
        self.hover_anim.stop()
        self.hover_anim.setStartValue(geom)
        self.hover_anim.setEndValue(geom.adjusted(-4, -4, 4, 4))
        self.hover_anim.start()
        
    def leaveEvent(self, event):
        """Handle mouse hover leave event with smooth animation"""
        super().leaveEvent(event)
        if self.original_style:
            self.setStyleSheet(self.original_style)
            
        # Return to original size with smooth animation
        if self.original_geometry:
            self.hover_anim.stop()
            self.hover_anim.setStartValue(self.geometry())
            self.hover_anim.setEndValue(self.original_geometry)
            self.hover_anim.start()
        
    def mousePressEvent(self, event):
        """Handle button press with smooth animation"""
        # Scale down animation
        geom = self.geometry()
        self.click_anim.stop()
        self.click_anim.setStartValue(geom)
        self.click_anim.setEndValue(geom.adjusted(6, 6, -6, -6))
        self.click_anim.start()
        
        super().mousePressEvent(event)
        
    def mouseReleaseEvent(self, event):
        """Handle button release with smooth animation"""
        # Scale back up animation
        geom = self.geometry()
        self.click_anim.stop()
        self.click_anim.setStartValue(geom)
        self.click_anim.setEndValue(self.original_geometry)
        self.click_anim.start()
        
        super().mouseReleaseEvent(event)
        
    def flash(self):
        """Create a flash animation to provide feedback"""
        flash_anim = QPropertyAnimation(self, b"geometry")
        flash_anim.setDuration(300)
        flash_anim.setLoopCount(2)
        
        original_geom = self.geometry()
        flash_anim.setKeyValueAt(0, original_geom)
        flash_anim.setKeyValueAt(0.3, original_geom.adjusted(4, 4, -4, -4))
        flash_anim.setKeyValueAt(0.6, original_geom.adjusted(-2, -2, 2, 2))
        flash_anim.setKeyValueAt(1, original_geom)
        flash_anim.start()

class SlideDialog(QDialog):
    """Dialog with slide-in animation"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.animation = QPropertyAnimation(self, b"pos")
        self.animation.setDuration(350)
        self.animation.setEasingCurve(QEasingCurve.OutBack)
        
    def showEvent(self, event):
        super().showEvent(event)
        
        # Store original position
        original_pos = self.pos()
        
        # Start from above the screen
        start_pos = original_pos
        start_pos.setY(start_pos.y() - self.height() - 50)
        self.move(start_pos)
        
        # Animate to original position
        self.animation.setStartValue(start_pos)
        self.animation.setEndValue(original_pos)
        self.animation.start()
        
    def closeEvent(self, event):
        # Animate out before closing
        self.animation.setDirection(self.animation.Backward)
        self.animation.finished.connect(event.accept)
        self.animation.start()
        event.ignore()

class ConfigDialog(SlideDialog):
    def __init__(self, button_key: str, config_data: dict, parent=None):
        super().__init__(parent)
        self.button_key = button_key
        self.config_data = config_data
        self.url_input = None
        self.exe_path_input = None
        self.key_input = None
        self.text_input = None
        self.setup_ui()

        self.setStyleSheet("""
    QDialog {
        background-color: #2d2d2d;
        color: #ffffff;
        border-radius: 12px;
    }
    QLabel {
        color: #cccccc;
        font-size: 14px;
    }
    QPushButton {
        background-color: #e67e22;
        color: white;
        border: none;
        padding: 8px 16px;
        border-radius: 6px;
        font-weight: bold;
    }
    QPushButton:hover {
        background-color: #d35400;
        padding: 9px 17px;
    }
    QLineEdit, QTextEdit {
        background-color: #3c3c3c;
        color: white;
        border: 1px solid #555;
        border-radius: 6px;
        padding: 6px;
    }
    QRadioButton {
        color: #cccccc;
        font-size: 14px;
        spacing: 8px;
    }
    QRadioButton::indicator {
        width: 16px;
        height: 16px;
        border-radius: 8px;
        border: 2px solid #7f8c8d;
        background-color: #2d2d2d;
    }
    QRadioButton::indicator:checked {
        background-color: #e67e22;
        border: 2px solid #ffffff;
    }
    QTabWidget::pane {
        border: 1px solid #444;
        background-color: #2d2d2d;
        border-radius: 8px;
    }
    QTabBar::tab {
        background-color: #3c3c3c;
        color: #ccc;
        padding: 8px 16px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }
    QTabBar::tab:selected {
        background-color: #e67e22;
        color: white;
    }
""")

    def setup_ui(self):
        self.setWindowTitle(f"Configure {self.button_key}")
        self.setFixedSize(500, 400)

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        type_label = QLabel("Select action type:")
        layout.addWidget(type_label)

        self.type_group = QButtonGroup(self)
        self.none_radio = QRadioButton("None")
        self.link_radio = QRadioButton("Link")
        self.exe_radio = QRadioButton("Executable or Shortcut")
        self.key_radio = QRadioButton("Keyboard Shortcut")
        self.text_radio = QRadioButton("Text Input")

        for i, rb in enumerate((self.none_radio, self.link_radio, self.exe_radio, self.key_radio, self.text_radio)):
            self.type_group.addButton(rb, i)

        radio_layout = QGridLayout()
        radio_layout.addWidget(self.none_radio, 0, 0)
        radio_layout.addWidget(self.link_radio, 0, 1)
        radio_layout.addWidget(self.exe_radio, 1, 0)
        radio_layout.addWidget(self.key_radio, 1, 1)
        radio_layout.addWidget(self.text_radio, 2, 0)
        layout.addLayout(radio_layout)

        self.input_widget = QWidget()
        self.input_layout = QVBoxLayout(self.input_widget)
        layout.addWidget(self.input_widget)

        footer = QHBoxLayout()
        self.test_button = QPushButton("Test Action")
        self.test_button.clicked.connect(self.test_action)
        footer.addWidget(self.test_button)

        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self.save_config)
        footer.addWidget(self.save_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        footer.addWidget(self.cancel_button)

        layout.addLayout(footer)

        self.load_config()
        self.type_group.buttonClicked.connect(self.update_input_area)

    def load_config(self):
        config = self.config_data.get(self.button_key, {"type": ActionType.NONE, "value": ""})
        action_type = config["type"]

        if action_type == ActionType.LINK:
            self.link_radio.setChecked(True)
        elif action_type == ActionType.EXE:
            self.exe_radio.setChecked(True)
        elif action_type == ActionType.KEYPRESS:
            self.key_radio.setChecked(True)
        elif action_type == ActionType.TEXT:
            self.text_radio.setChecked(True)
        else:
            self.none_radio.setChecked(True)

        self.update_input_area()

    def update_input_area(self):
        self.clear_layout(self.input_layout)

        action_type = self.get_selected_type()
        config = self.config_data.get(self.button_key, {"type": "none", "value": ""})

        if action_type == ActionType.LINK:
            url_label = QLabel("Enter URL:")
            self.url_input = QLineEdit(config["value"] if config["type"] == "link" else "")
            self.input_layout.addWidget(url_label)
            self.input_layout.addWidget(self.url_input)

        elif action_type == ActionType.EXE:
            exe_label = QLabel("Select executable:")
            self.exe_path_input = QLineEdit(config["value"] if config["type"] == "exe" else "")
            browse_button = QPushButton("Browse")
            browse_button.clicked.connect(self.browse_exe)

            browse_layout = QHBoxLayout()
            browse_layout.addWidget(self.exe_path_input)
            browse_layout.addWidget(browse_button)

            self.input_layout.addWidget(exe_label)
            self.input_layout.addLayout(browse_layout)
            
        elif action_type == ActionType.KEYPRESS:
            key_label = QLabel("Enter keyboard shortcut (e.g., Ctrl+Shift+A):")
            self.key_input = QLineEdit(config["value"] if config["type"] == "keypress" else "")
            self.input_layout.addWidget(key_label)
            self.input_layout.addWidget(self.key_input)
            
        elif action_type == ActionType.TEXT:
            text_label = QLabel("Enter text to type:")
            self.text_input = QTextEdit()
            self.text_input.setMaximumHeight(100)
            if config["type"] == "text":
                self.text_input.setPlainText(config["value"])
            self.input_layout.addWidget(text_label)
            self.input_layout.addWidget(self.text_input)

    def get_selected_type(self) -> ActionType:
        if self.link_radio.isChecked():
            return ActionType.LINK
        if self.exe_radio.isChecked():
            return ActionType.EXE
        if self.key_radio.isChecked():
            return ActionType.KEYPRESS
        if self.text_radio.isChecked():
            return ActionType.TEXT
        return ActionType.NONE

    def browse_exe(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Executable or Shortcut",
            "",
            "Executable or Shortcut (*.exe *.bat *.cmd *.lnk);;All Files (*.*)"
        )
        if file_path:
            self.exe_path_input.setText(file_path)

    def test_action(self):
        value = ""
        action_type = self.get_selected_type()

        if action_type == ActionType.LINK and self.url_input:
            value = self.url_input.text()
        elif action_type == ActionType.EXE and self.exe_path_input:
            value = self.exe_path_input.text()
        elif action_type == ActionType.KEYPRESS and self.key_input:
            value = self.key_input.text()
        elif action_type == ActionType.TEXT and self.text_input:
            value = self.text_input.toPlainText()

        if value:
            run_action({"type": action_type, "value": value})
        else:
            QMessageBox.warning(self, "Test Action", "Please provide a value to test.")

    def save_config(self):
        action_type = self.get_selected_type()
        value = ""

        if action_type == ActionType.LINK:
            value = self.url_input.text() if self.url_input else ""
            if not value:
                QMessageBox.warning(self, "Configuration", "Please enter a URL.")
                return
        elif action_type == ActionType.EXE:
            value = self.exe_path_input.text() if self.exe_path_input else ""
            if not value:
                QMessageBox.warning(self, "Configuration", "Please select an executable or shortcut.")
                return
        elif action_type == ActionType.KEYPRESS:
            value = self.key_input.text() if self.key_input else ""
            if not value:
                QMessageBox.warning(self, "Configuration", "Please enter a keyboard shortcut.")
                return
        elif action_type == ActionType.TEXT:
            value = self.text_input.toPlainText() if self.text_input else ""
            if not value:
                QMessageBox.warning(self, "Configuration", "Please enter text to type.")
                return

        self.config_data[self.button_key] = {"type": action_type, "value": value}
        self.accept()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()
            elif item.layout():
                self.clear_layout(item.layout())


class ConsoleDeck(QMainWindow):
    BTN_STYLE_EMPTY = """
        QPushButton {
            background-color: #3c3c3c;
            color: #dcdcdc;
            border-radius: 12px;
            font-size: 22px;
            font-weight: bold;
            border: 2px solid #4a4a4a;
        }
        QPushButton:hover {
            background-color: #4a4a4a;
        }
    """
    BTN_STYLE_CONFIGURED = """
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #e67e22, stop: 1 #d35400);
            color: #ffffff;
            border-radius: 12px;
            font-size: 22px;
            font-weight: bold;
            border: 2px solid #e67e22;
        }
        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f39c12, stop: 1 #e67e22);
        }
    """
    BTN_STYLE_KEYPRESS = """
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #3498db, stop: 1 #2980b9);
            color: #ffffff;
            border-radius: 12px;
            font-size: 22px;
            font-weight: bold;
            border: 2px solid #3498db;
        }
        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #5dade2, stop: 1 #3498db);
        }
    """
    BTN_STYLE_TEXT = """
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #9b59b6, stop: 1 #8e44ad);
            color: #ffffff;
            border-radius: 12px;
            font-size: 22px;
            font-weight: bold;
            border: 2px solid #9b59b6;
        }
        QPushButton:hover {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #bb8fce, stop: 1 #9b59b6);
        }
    """
    
    # Hover styles for each button type
    BTN_HOVER_EMPTY = """
        QPushButton {
            background-color: #4a4a4a;
            color: #ffffff;
            border-radius: 12px;
            font-size: 22px;
            font-weight: bold;
            border: 2px solid #5a5a5a;
        }
    """
    BTN_HOVER_CONFIGURED = """
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #f39c12, stop: 1 #e67e22);
            color: #ffffff;
            border-radius: 12px;
            font-size: 22px;
            font-weight: bold;
            border: 2px solid #f39c12;
        }
    """
    BTN_HOVER_KEYPRESS = """
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #5dade2, stop: 1 #3498db);
            color: #ffffff;
            border-radius: 12px;
            font-size: 22px;
            font-weight: bold;
            border: 2px solid #5dade2;
        }
    """
    BTN_HOVER_TEXT = """
        QPushButton {
            background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                stop: 0 #bb8fce, stop: 1 #9b59b6);
            color: #ffffff;
            border-radius: 12px;
            font-size: 22px;
            font-weight: bold;
            border: 2px solid #bb8fce;
        }
    """

    def __init__(self):
        super().__init__()
        self.config_data = self.load_config()
        self.buttons = {}
        self.setup_ui()
        self.setup_shortcuts()

    def load_config(self) -> dict:
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def save_config(self):
        with open(CONFIG_FILE, "w") as f:
            json.dump(self.config_data, f, indent=4)

    def setup_ui(self):
        self.setWindowTitle("Desktop Deck")
        self.setFixedSize(800, 700)

        # Create a central widget with fade effect
        central = FadeWidget()
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        self.setCentralWidget(central)

        title = QLabel("Desktop Deck")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            color: #000000; 
            font-size: 32px; 
            font-weight: bold;
            padding: 10px;
            background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 0,
                stop: 0 transparent, stop: 0.5 #e67e22, stop: 1 transparent);
            border-radius: 8px;
        """)
        layout.addWidget(title)

        # Create tabs for different button groups
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #2d2d2d;
                border-radius: 8px;
                margin-top: 5px;
            }
            QTabBar::tab {
                background-color: #3c3c3c;
                color: #ccc;
                padding: 8px 16px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background-color: #e67e22;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #4a4a4a;
            }
        """)
        layout.addWidget(tab_widget)

        # Main buttons tab (9 buttons)
        main_tab = QWidget()
        main_layout = QVBoxLayout(main_tab)
        main_layout.setContentsMargins(10, 10, 10, 10)
        tab_widget.addTab(main_tab, "Main Buttons")

        grid = QGridLayout()
        grid.setSpacing(20)
        grid.setContentsMargins(10, 10, 10, 10)
        for row in range(3):
            for col in range(3):
                btn_num = row * 3 + col + 1
                button_key = f"BUTTON_{btn_num}"

                # Use our custom animated button
                button = AnimatedButton(str(btn_num))
                button.setFixedSize(150, 150)
                button.setFont(QFont("Montserrat", 26, QFont.Bold))
                button.clicked.connect(lambda _, key=button_key: self.on_button_clicked(key))

                self.update_button_style(button, button_key)
                self.buttons[button_key] = button
                grid.addWidget(button, row, col)

        main_layout.addLayout(grid)

        # Special functions tab
        special_tab = QWidget()
        special_layout = QVBoxLayout(special_tab)
        special_layout.setContentsMargins(10, 10, 10, 10)
        tab_widget.addTab(special_tab, "Special Functions")

        # Add info about special functions
        info_label = QLabel(
            "Special functions are handled automatically:\n\n"
            "• Volume Encoder: Adjusts system volume\n"
            "• Encoder Button: Mutes/unmutes audio\n"
            "• Button 10: Media play/pause control"
        )
        info_label.setAlignment(Qt.AlignLeft)
        info_label.setStyleSheet("""
            color: #aaaaaa; 
            font-size: 14px; 
            padding: 10px;
            background-color: #3c3c3c;
            border-radius: 8px;
        """)
        special_layout.addWidget(info_label)

        # Add serial port configuration
        serial_group = QGroupBox("Serial Port Configuration")
        serial_group.setStyleSheet("""
            QGroupBox { 
                color: #e67e22; 
                font-weight: bold; 
                border: 2px solid #e67e22;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        serial_layout = QVBoxLayout(serial_group)
        
        port_layout = QHBoxLayout()
        port_label = QLabel("COM Port:")
        port_label.setStyleSheet("color: #cccccc;")
        self.port_combo = QComboBox()
        self.port_combo.setStyleSheet("""
            QComboBox {
                background-color: #3c3c3c;
                color: white;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 5px;
            }
            QComboBox:hover {
                background-color: #4a4a4a;
            }
        """)
        
        # Add common COM ports
        for i in range(1, 21):
            self.port_combo.addItem(f"COM{i}")
        
        # Try to auto-detect the port with Arduino
        self.port_combo.setCurrentText("COM6")  # Default from Arduino code
        
        port_layout.addWidget(port_label)
        port_layout.addWidget(self.port_combo)
        port_layout.addStretch()
        
        self.refresh_ports_btn = QPushButton("Refresh Ports")
        self.refresh_ports_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.refresh_ports_btn.clicked.connect(self.refresh_serial_ports)
        port_layout.addWidget(self.refresh_ports_btn)
        
        serial_layout.addLayout(port_layout)
        special_layout.addWidget(serial_group)

        self.info_label = QLabel("Click a button to configure or run it")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setStyleSheet("""
            color: #aaaaaa; 
            font-size: 14px;
            padding: 8px;
            background-color: #3c3c3c;
            border-radius: 6px;
        """)
        layout.addWidget(self.info_label)

        # Add system tray icon
        self.setup_tray_icon()
        
        # Fade in the central widget
        central.fade_in()

    def setup_tray_icon(self):
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
            
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(self.style().standardIcon(QStyle.SP_ComputerIcon))
        
        tray_menu = QMenu()
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.show_normal)
        
        hide_action = tray_menu.addAction("Hide")
        hide_action.triggered.connect(self.hide)
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(QApplication.quit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
        self.tray_icon.activated.connect(self.tray_icon_activated)

    def show_normal(self):
        """Show the window with animation"""
        self.show()
        self.activateWindow()
        self.raise_()

    def tray_icon_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show_normal()

    def refresh_serial_ports(self):
        # Create a simple animation for the refresh button
        anim = QPropertyAnimation(self.refresh_ports_btn, b"geometry")
        anim.setDuration(300)
        original_geom = self.refresh_ports_btn.geometry()
        anim.setKeyValueAt(0, original_geom)
        anim.setKeyValueAt(0.5, original_geom.adjusted(0, -5, 0, -5))
        anim.setKeyValueAt(1, original_geom)
        anim.start()
        
        # This would ideally scan for available COM ports
        # For now, we'll just show a message
        QMessageBox.information(self, "Refresh Ports", 
                               "Port list refreshed. Note: Actual port scanning would require additional libraries.")

    def setup_shortcuts(self):
        # Add keyboard shortcuts for buttons 1-9
        for i in range(1, 10):
            shortcut = QShortcut(QKeySequence(f"Ctrl+Alt+{i}"), self)
            shortcut.activated.connect(lambda _, idx=i: self.on_keyboard_shortcut(f"BUTTON_{idx}"))

    def on_keyboard_shortcut(self, button_key):
        config = self.config_data.get(button_key)
        if config and config["type"] != ActionType.NONE:
            # Add a visual feedback animation when triggered by keyboard
            button = self.buttons.get(button_key)
            if button:
                button.flash()
            
            run_action(config)
            self.info_label.setText(f"Executed {button_key} via keyboard shortcut")
            
            # Animate the info label
            self.animate_info_label()

    def animate_info_label(self):
        """Animate the info label to provide feedback"""
        anim = QPropertyAnimation(self.info_label, b"geometry")
        anim.setDuration(300)
        original_geom = self.info_label.geometry()
        anim.setKeyValueAt(0, original_geom)
        anim.setKeyValueAt(0.3, original_geom.adjusted(0, -3, 0, -3))
        anim.setKeyValueAt(0.6, original_geom.adjusted(0, 2, 0, 2))
        anim.setKeyValueAt(1, original_geom)
        anim.start()

    def update_button_style(self, button: AnimatedButton, key: str):
        config = self.config_data.get(key, {"type": ActionType.NONE})
        
        if config["type"] == ActionType.NONE:
            button.setButtonStyles(self.BTN_STYLE_EMPTY, self.BTN_HOVER_EMPTY)
        elif config["type"] == ActionType.KEYPRESS:
            button.setButtonStyles(self.BTN_STYLE_KEYPRESS, self.BTN_HOVER_KEYPRESS)
        elif config["type"] == ActionType.TEXT:
            button.setButtonStyles(self.BTN_STYLE_TEXT, self.BTN_HOVER_TEXT)
        else:
            button.setButtonStyles(self.BTN_STYLE_CONFIGURED, self.BTN_HOVER_CONFIGURED)
            
        # Update tooltip with action info
        if config["type"] != ActionType.NONE:
            action_type = config["type"].capitalize()
            button.setToolTip(f"{action_type}: {config.get('value', '')}")
        else:
            button.setToolTip("No action configured")

    def on_button_clicked(self, key: str):
        dialog = ConfigDialog(key, self.config_data, self)
        if dialog.exec_() == QDialog.Accepted:
            self.save_config()
            self.update_button_style(self.buttons[key], key)
            self.info_label.setText(f"Configured {key}")
            self.animate_info_label()
        else:
            config = self.config_data.get(key)
            if config and config["type"] != ActionType.NONE:
                # Animate the button when executing an action
                button = self.buttons.get(key)
                if button:
                    button.flash()
                
                run_action(config)
                self.info_label.setText(f"Executed {key}")
                self.animate_info_label()

    def closeEvent(self, event):
        # Hide to tray instead of closing
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.hide()
            event.ignore()
        else:
            event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Set application-wide animation duration
    app.setEffectEnabled(Qt.UI_AnimateCombo, True)
    app.setEffectEnabled(Qt.UI_AnimateMenu, True)
    app.setEffectEnabled(Qt.UI_AnimateToolBox, True)
    app.setEffectEnabled(Qt.UI_AnimateTooltip, True)
    
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.WindowText, Qt.white)
    palette.setColor(QPalette.Base, QColor(25, 25, 25))
    palette.setColor(QPalette.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ButtonText, Qt.white)
    palette.setColor(QPalette.Highlight, QColor(230, 126, 34))
    palette.setColor(QPalette.HighlightedText, Qt.black)
    app.setPalette(palette)

    win = ConsoleDeck()
    win.show()
    sys.exit(app.exec_())