import os
import json
import subprocess
import webbrowser
import serial
import time
import ctypes
import pyautogui
import keyboard as kb
from enum import Enum
import threading
import logging
from typing import Dict, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("desktop_deck.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("DesktopDeck")

# Default serial port settings
DEFAULT_PORT = "COM6"
BAUDRATE = 9600

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")

# Global state
pulsante_selezionato = None
last_volume_value = 0
is_muted = False
serial_connection = None
serial_thread = None
stop_serial = False

class ActionType(str, Enum):
    NONE = "none"
    LINK = "link"
    EXE = "exe"
    KEYPRESS = "keypress"
    TEXT = "text"

class SerialManager:
    def __init__(self, port: str = DEFAULT_PORT, baudrate: int = BAUDRATE):
        self.port = port
        self.baudrate = baudrate
        self.ser = None
        self.is_connected = False
        self.callback = None
        
    def set_callback(self, callback):
        """Set callback function for received data"""
        self.callback = callback
        
    def connect(self) -> bool:
        """Connect to serial port"""
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            self.is_connected = True
            logger.info(f"Connected to {self.port} at {self.baudrate} baud")
            return True
        except serial.SerialException as e:
            logger.error(f"Failed to connect to {self.port}: {e}")
            self.is_connected = False
            return False
            
    def disconnect(self):
        """Disconnect from serial port"""
        if self.ser and self.ser.is_open:
            self.ser.close()
            self.is_connected = False
            logger.info(f"Disconnected from {self.port}")
            
    def read_data(self):
        """Read data from serial port and call callback if set"""
        if not self.ser or not self.ser.is_open:
            return
            
        try:
            raw_data = self.ser.readline()
            if raw_data:
                try:
                    linea = raw_data.decode('utf-8', errors='ignore').strip()
                    if linea and self.callback:
                        self.callback(linea)
                except UnicodeDecodeError:
                    logger.warning(f"Could not decode: {raw_data}")
        except serial.SerialException as e:
            logger.error(f"Serial read error: {e}")
            self.disconnect()
            
    def write_data(self, data: str):
        """Write data to serial port"""
        if self.ser and self.ser.is_open:
            try:
                self.ser.write(data.encode())
                logger.debug(f"Sent to serial: {data}")
            except serial.SerialException as e:
                logger.error(f"Serial write error: {e}")

def load_config() -> Dict:
    """Load configuration from JSON file"""
    logger.info(f"Loading config from: {CONFIG_FILE}")
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
                logger.debug("Config loaded successfully")
                return config
        else:
            logger.warning("Config file not found, creating default config")
            config = {}
            for i in range(1, 10):
                config[f"BUTTON_{i}"] = {"type": "none", "value": ""}
            # Set a default action for button 1
            config["BUTTON_1"] = {"type": "link", "value": "https://www.youtube.com"}
            save_config(config)
            return config
    except Exception as e:
        logger.error(f"Error loading config: {e}")
        return {}

def save_config(config: Dict):
    """Save configuration to JSON file"""
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(config, f, indent=2)
        logger.info("Configuration saved successfully")
    except Exception as e:
        logger.error(f"Error saving config: {e}")

def esegui_azione(azione: Dict):
    """Execute an action based on its type"""
    if not azione or azione["type"] == ActionType.NONE:
        logger.info("No action to execute")
        return
        
    logger.info(f"Executing action: {azione}")
    
    try:
        if azione["type"] == ActionType.LINK and azione["value"]:
            logger.info(f"Opening URL: {azione['value']}")
            webbrowser.open(azione["value"])
            
        elif azione["type"] == ActionType.EXE and azione["value"]:
            logger.info(f"Opening EXE: {azione['value']}")
            # Use subprocess.Popen for better control
            if os.name == 'nt':  # Windows
                if azione["value"].lower().endswith('.lnk'):
                    subprocess.Popen(['cmd', '/c', 'start', '', azione["value"]], 
                                   shell=True)
                else:
                    subprocess.Popen(azione["value"], shell=True)
            else:  # macOS/Linux
                subprocess.Popen(['xdg-open', azione["value"]])
                
        elif azione["type"] == ActionType.KEYPRESS and azione["value"]:
            logger.info(f"Pressing keys: {azione['value']}")
            kb.press_and_release(azione["value"])
            
        elif azione["type"] == ActionType.TEXT and azione["value"]:
            logger.info(f"Typing text: {azione['value']}")
            pyautogui.write(azione["value"])
            
        logger.info("Action executed successfully")
    except Exception as e:
        logger.error(f"Error executing action: {e}")

def simulate_keypress(vk_code: int):
    """Simulate a key press using Windows API"""
    KEYEVENTF_EXTENDEDKEY = 0x0001
    KEYEVENTF_KEYUP = 0x0002
    try:
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY, 0)
        time.sleep(0.05)  # Short delay between press and release
        ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_EXTENDEDKEY | KEYEVENTF_KEYUP, 0)
    except Exception as e:
        logger.error(f"Error simulating keypress: {e}")

def gestisci_volume(value: str):
    """Handle volume control from encoder"""
    global last_volume_value
    try:
        valore = int(value)
        delta = valore - last_volume_value
        
        if delta != 0:
            # VK_VOLUME_UP = 0xAF, VK_VOLUME_DOWN = 0xAE
            vk = 0xAF if delta > 0 else 0xAE
            for _ in range(abs(delta)):
                simulate_keypress(vk)
                time.sleep(0.01)  # Small delay between volume steps
                
            logger.info(f"Volume adjusted by {delta}")
        last_volume_value = valore
    except ValueError:
        logger.error(f"Invalid volume value: {value}")

def gestisci_mute():
    """Handle mute toggle"""
    global is_muted
    try:
        # VK_VOLUME_MUTE = 0xAD
        simulate_keypress(0xAD)
        is_muted = not is_muted
        logger.info(f"Mute toggled -> {'ON' if is_muted else 'OFF'}")
    except Exception as e:
        logger.error(f"Error toggling mute: {e}")

def gestisci_media():
    """Handle media play/pause"""
    try:
        # VK_MEDIA_PLAY_PAUSE = 0xB3
        simulate_keypress(0xB3)
        logger.info("Media play/pause triggered")
    except Exception as e:
        logger.error(f"Error triggering media control: {e}")

def handle_serial_data(data: str, config: Dict):
    """Handle incoming serial data"""
    logger.debug(f"Received serial data: '{data}'")
    
    if data.startswith("VOLUME_"):
        valore = data.replace("VOLUME_", "")
        gestisci_volume(valore)
    elif data == "MUTE":
        gestisci_mute()
    elif data == "MEDIA":
        gestisci_media()
    elif data in config:
        logger.info(f"Executing action for: {data}")
        action = config[data]
        esegui_azione(action)
    else:
        logger.warning(f"No action configured for: '{data}'")

def serial_listener_worker(port: str = DEFAULT_PORT, baudrate: int = BAUDRATE, 
                          config: Optional[Dict] = None, callback=None):
    """Worker function for serial listener thread"""
    global stop_serial
    
    if config is None:
        config = load_config()
        
    serial_mgr = SerialManager(port, baudrate)
    
    def data_callback(data):
        handle_serial_data(data, config)
        if callback:
            callback(data)
    
    serial_mgr.set_callback(data_callback)
    
    max_retries = 5
    retry_delay = 2
    
    while not stop_serial:
        if not serial_mgr.is_connected:
            if serial_mgr.connect():
                logger.info(f"Serial listener started on {port}")
            else:
                logger.warning(f"Failed to connect to {port}, retrying in {retry_delay}s...")
                time.sleep(retry_delay)
                continue
                
        try:
            serial_mgr.read_data()
            time.sleep(0.01)  # Small delay to prevent CPU overuse
        except Exception as e:
            logger.error(f"Error in serial listener: {e}")
            serial_mgr.disconnect()
            time.sleep(retry_delay)
            
    serial_mgr.disconnect()
    logger.info("Serial listener stopped")

def start_serial_listener(port: str = DEFAULT_PORT, baudrate: int = BAUDRATE, 
                         config: Optional[Dict] = None, callback=None) -> threading.Thread:
    """Start serial listener in a separate thread"""
    global stop_serial, serial_thread
    
    stop_serial = False
    serial_thread = threading.Thread(
        target=serial_listener_worker,
        args=(port, baudrate, config, callback),
        daemon=True,
        name="SerialListener"
    )
    serial_thread.start()
    return serial_thread

def stop_serial_listener():
    """Stop the serial listener thread"""
    global stop_serial
    stop_serial = True
    if serial_thread and serial_thread.is_alive():
        serial_thread.join(timeout=2.0)
        logger.info("Serial listener stopped")

def seleziona_pulsante(btn: int):
    """Select a button (for future use)"""
    global pulsante_selezionato
    pulsante_selezionato = btn
    logger.debug(f"Button selected: BUTTON_{btn}")

def deseleziona_pulsante():
    """Deselect button (for future use)"""
    global pulsante_selezionato
    pulsante_selezionato = None
    logger.debug("Button deselected")

def get_pulsante_selezionato() -> Optional[int]:
    """Get currently selected button (for future use)"""
    return pulsante_selezionato

def get_serial_ports():
    """Get list of available serial ports"""
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    except ImportError:
        logger.warning("pyserial not available for port scanning")
        return []
    except Exception as e:
        logger.error(f"Error getting serial ports: {e}")
        return []