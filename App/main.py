import argparse
import sys
import os
import signal
from PyQt5.QtWidgets import QApplication, QMessageBox
from logic import load_config, start_serial_listener, stop_serial_listener, get_serial_ports
from gui import ConsoleDeck
import threading
import logging

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

def signal_handler(sig, frame):
    """Handle interrupt signals"""
    logger.info("Received interrupt signal, shutting down...")
    stop_serial_listener()
    sys.exit(0)

def run_serial_listener(config, port="COM6", baudrate=9600, callback=None):
    """Run the serial listener with error handling"""
    try:
        logger.info(f"Starting serial listener on {port}")
        thread = start_serial_listener(port, baudrate, config, callback)
        return thread
    except Exception as e:
        logger.error(f"Failed to start serial listener: {e}")
        return None

def main(gui_mode=True, port="COM6", baudrate=9600):
    """Main application function"""
    logger.info("Starting Desktop Deck application")
    
    # Set up signal handlers for clean shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Load configuration
    config = load_config()
    
    if gui_mode:
        # Create and run the PyQt5 application
        app = QApplication(sys.argv)
        app.setStyle("Fusion")
        
        # Set dark palette
        from PyQt5.QtGui import QPalette, QColor
        from PyQt5.QtCore import Qt
        
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(45, 45, 45))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
        palette.setColor(QPalette.ToolTipBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Highlight, QColor(230, 126, 34))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        app.setPalette(palette)
        
        # Create and show the main window
        win = ConsoleDeck()
        win.show()
        
        # Set up serial data callback to update GUI
        def serial_data_callback(data):
            """Callback for serial data to update GUI"""
            if hasattr(win, 'info_label'):
                win.info_label.setText(f"Serial: {data}")
                win.animate_info_label()
        
        # Start serial listener in a separate thread
        serial_thread = run_serial_listener(config, port, baudrate, serial_data_callback)
        
        if not serial_thread:
            QMessageBox.warning(win, "Serial Error", 
                               f"Could not connect to serial port {port}.\n"
                               "Please check your connection and try again.")
        
        # Start the application event loop
        try:
            result = app.exec_()
        finally:
            # Clean up on exit
            stop_serial_listener()
            logger.info("Application shutdown complete")
        
        sys.exit(result)
    else:
        # Run in console mode (non-GUI)
        logger.info("Running in console mode")
        
        # Start serial listener
        serial_thread = run_serial_listener(config, port, baudrate)
        
        if not serial_thread:
            logger.error("Failed to start serial listener in console mode")
            return 1
        
        print("Desktop Deck running in console mode...")
        print("Press Ctrl+C to exit")
        
        try:
            # Keep the main thread alive
            while True:
                if not serial_thread.is_alive():
                    logger.error("Serial listener thread died")
                    break
                # Check every second if we should exit
                serial_thread.join(1.0)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
        finally:
            # Clean up
            stop_serial_listener()
            logger.info("Console application shutdown complete")
        
        return 0

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Desktop Deck Application")
    parser.add_argument('--gui', action='store_true', 
                       help="Start with GUI (default)")
    parser.add_argument('--nogui', action='store_true', 
                       help="Start in console mode (no GUI)")
    parser.add_argument('--port', type=str, default="COM6",
                       help="Serial port to use (default: COM6)")
    parser.add_argument('--baudrate', type=int, default=9600,
                       help="Baud rate for serial communication (default: 9600)")
    parser.add_argument('--list-ports', action='store_true',
                       help="List available serial ports and exit")
    
    args = parser.parse_args()
    
    if args.list_ports:
        ports = get_serial_ports()
        print("Available serial ports:")
        for port in ports:
            print(f"  {port}")
        sys.exit(0)
    
    # Default to GUI mode if no arguments provided
    gui_mode = not args.nogui
    
    # Run the application
    sys.exit(main(gui_mode, args.port, args.baudrate))