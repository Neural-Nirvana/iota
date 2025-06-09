#!/usr/bin/env python3
"""
PyQt AI OS Terminal - A modern GUI terminal for the AI OS system
Integrates termqt with the existing AI OS functionality
"""
import os
os.environ.setdefault("QT_API", "pyqt6")   # must be before qtpy is imported


import sys

import logging
import platform
import subprocess
import threading
from pathlib import Path

# PyQt imports
try:
    from qtpy.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
        QScrollBar, QMenuBar, QAction, QStatusBar, QSplitter, QTextEdit,
        QLabel, QPushButton, QComboBox, QGroupBox, QFormLayout, QLineEdit,
        QCheckBox, QSpinBox, QDoubleSpinBox, QTabWidget, QMessageBox,
        QSystemTrayIcon, QMenu, QFileDialog
    )
    from qtpy.QtCore import Qt, QCoreApplication, QTimer, QThread, pyqtSignal, QSettings
    from qtpy.QtGui import QFont, QIcon, QPixmap, QKeySequence
    from qtpy import QT_VERSION
except ImportError:
    print("Error: PyQt/PySide not found. Please install with:")
    print("pip install qtpy pyqt5  # or pyqt6, pyside2, pyside6")
    sys.exit(1)

# Terminal widget import
try:
    import termqt
    from termqt import Terminal
    if platform.system() in ["Linux", "Darwin"]:
        from termqt import TerminalPOSIXExecIO
    elif platform.system() == "Windows":
        from termqt import TerminalWinptyIO
    else:
        print(f"Unsupported platform: {platform.system()}")
        sys.exit(1)
except ImportError:
    print("Error: termqt not found. Please install with:")
    print("pip install termqt")
    sys.exit(1)

# Try to import the existing AI OS components
try:
    from config import load_config, save_config, Config
    AI_OS_AVAILABLE = True
except ImportError:
    print("Warning: AI OS components not found. Running in basic terminal mode.")
    AI_OS_AVAILABLE = False


class AITerminalWidget(QWidget):
    """Enhanced terminal widget with AI OS integration"""
    
    def __init__(self, parent=None, logger=None):
        super().__init__(parent)
        self.logger = logger or logging.getLogger(__name__)
        self.config = None
        if AI_OS_AVAILABLE:
            self.config = load_config()
        
        self.setup_ui()
        self.setup_terminal()
        self.setup_io()
        
    def setup_ui(self):
        """Setup the terminal widget UI"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create terminal with adaptive sizing
        self.terminal = Terminal(1000, 700, logger=self.logger)
        self.terminal.set_font(QFont("Consolas", 11))  # Modern monospace font
        self.terminal.maximum_line_history = 5000
        
        # Scrollbar
        self.scroll = QScrollBar(Qt.Vertical, self.terminal)
        self.terminal.connect_scroll_bar(self.scroll)
        
        layout.addWidget(self.terminal)
        layout.addWidget(self.scroll)
        
        self.setLayout(layout)
        
    def setup_terminal(self):
        """Configure terminal settings"""
        # Enable auto-wrap except on Windows with cmd
        auto_wrap = not (platform.system() == "Windows")
        self.terminal.enable_auto_wrap(auto_wrap)
        
    def setup_io(self):
        """Setup terminal I/O based on platform"""
        platform_name = platform.system()
        
        if platform_name in ["Linux", "Darwin"]:
            # Use bash for Unix-like systems
            shell = os.environ.get('SHELL', '/bin/bash')
            self.terminal_io = TerminalPOSIXExecIO(
                self.terminal.row_len,
                self.terminal.col_len,
                shell,
                logger=self.logger
            )
        elif platform_name == "Windows":
            # Use PowerShell on Windows for better experience
            powershell_path = r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
            if os.path.exists(powershell_path):
                shell = powershell_path
            else:
                shell = "cmd"
            
            self.terminal_io = TerminalWinptyIO(
                self.terminal.row_len,
                self.terminal.col_len,
                shell,
                logger=self.logger
            )
        
        # Connect callbacks
        self.terminal_io.stdout_callback = self.terminal.stdout
        self.terminal.stdin_callback = self.terminal_io.write
        self.terminal.resize_callback = self.terminal_io.resize
        
    def start_terminal(self):
        """Start the terminal process"""
        try:
            self.terminal_io.spawn()
            
            # If AI OS is available, auto-run it
            if AI_OS_AVAILABLE and self.config:
                self.auto_start_ai_os()
                
        except Exception as e:
            self.logger.error(f"Failed to start terminal: {e}")
            
    def auto_start_ai_os(self):
        """Automatically start the AI OS in the terminal"""
        QTimer.singleShot(1000, self._send_ai_os_command)
        
    def _send_ai_os_command(self):
        """Send command to start AI OS"""
        # Change to the directory containing app.py and run it
        command = "python app.py\n"
        if platform.system() == "Windows":
            command = "python app.py\r\n"
        
        self.terminal_io.write(command.encode())


class ConfigPanel(QWidget):
    """Configuration panel for AI OS settings"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = None
        if AI_OS_AVAILABLE:
            self.config = load_config()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup configuration UI"""
        layout = QVBoxLayout()
        
        # AI Provider Configuration
        provider_group = QGroupBox("AI Provider Settings")
        provider_layout = QFormLayout()
        
        # Provider selection
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["openai", "google", "openrouter", "together"])
        if self.config:
            self.provider_combo.setCurrentText(self.config.agent.provider)
        provider_layout.addRow("Provider:", self.provider_combo)
        
        # Model input
        self.model_input = QLineEdit()
        if self.config:
            self.model_input.setText(self.config.agent.model)
        provider_layout.addRow("Model:", self.model_input)
        
        # Temperature
        self.temperature_spin = QDoubleSpinBox()
        self.temperature_spin.setRange(0.0, 2.0)
        self.temperature_spin.setSingleStep(0.1)
        self.temperature_spin.setDecimals(1)
        if self.config:
            self.temperature_spin.setValue(self.config.agent.temperature)
        provider_layout.addRow("Temperature:", self.temperature_spin)
        
        # Max tokens
        self.max_tokens_spin = QSpinBox()
        self.max_tokens_spin.setRange(100, 8000)
        if self.config:
            self.max_tokens_spin.setValue(self.config.agent.max_tokens)
        provider_layout.addRow("Max Tokens:", self.max_tokens_spin)
        
        provider_group.setLayout(provider_layout)
        layout.addWidget(provider_group)
        
        # API Keys Configuration
        keys_group = QGroupBox("API Keys")
        keys_layout = QFormLayout()
        
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.Password)
        if self.config and self.config.agent.openai_api_key:
            self.openai_key.setText("••••" + self.config.agent.openai_api_key[-4:])
        keys_layout.addRow("OpenAI:", self.openai_key)
        
        self.google_key = QLineEdit()
        self.google_key.setEchoMode(QLineEdit.Password)
        if self.config and self.config.agent.google_api_key:
            self.google_key.setText("••••" + self.config.agent.google_api_key[-4:])
        keys_layout.addRow("Google:", self.google_key)
        
        self.openrouter_key = QLineEdit()
        self.openrouter_key.setEchoMode(QLineEdit.Password)
        if self.config and hasattr(self.config.agent, 'openrouter_api_key') and self.config.agent.openrouter_api_key:
            self.openrouter_key.setText("••••" + self.config.agent.openrouter_api_key[-4:])
        keys_layout.addRow("OpenRouter:", self.openrouter_key)
        
        self.together_key = QLineEdit()
        self.together_key.setEchoMode(QLineEdit.Password)
        if self.config and hasattr(self.config.agent, 'together_api_key') and self.config.agent.together_api_key:
            self.together_key.setText("••••" + self.config.agent.together_api_key[-4:])
        keys_layout.addRow("Together AI:", self.together_key)
        
        keys_group.setLayout(keys_layout)
        layout.addWidget(keys_group)
        
        # UI Settings
        ui_group = QGroupBox("Interface Settings")
        ui_layout = QFormLayout()
        
        self.show_tool_calls = QCheckBox()
        if self.config:
            self.show_tool_calls.setChecked(self.config.ui.show_tool_calls)
        ui_layout.addRow("Show Tool Calls:", self.show_tool_calls)
        
        self.markdown_enabled = QCheckBox()
        if self.config:
            self.markdown_enabled.setChecked(self.config.ui.markdown)
        ui_layout.addRow("Enable Markdown:", self.markdown_enabled)
        
        ui_group.setLayout(ui_layout)
        layout.addWidget(ui_group)
        
        # Save button
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.save_config)
        layout.addWidget(save_btn)
        
        layout.addStretch()
        self.setLayout(layout)
        
    def save_config(self):
        """Save configuration changes"""
        if not AI_OS_AVAILABLE or not self.config:
            QMessageBox.warning(self, "Warning", "AI OS configuration not available")
            return
            
        try:
            # Update config object
            self.config.agent.provider = self.provider_combo.currentText()
            self.config.agent.model = self.model_input.text()
            self.config.agent.temperature = self.temperature_spin.value()
            self.config.agent.max_tokens = self.max_tokens_spin.value()
            
            # Update API keys only if they don't contain bullet characters
            if "••••" not in self.openai_key.text():
                self.config.agent.openai_api_key = self.openai_key.text()
            if "••••" not in self.google_key.text():
                self.config.agent.google_api_key = self.google_key.text()
            if "••••" not in self.openrouter_key.text():
                if not hasattr(self.config.agent, 'openrouter_api_key'):
                    self.config.agent.openrouter_api_key = ""
                self.config.agent.openrouter_api_key = self.openrouter_key.text()
            if "••••" not in self.together_key.text():
                if not hasattr(self.config.agent, 'together_api_key'):
                    self.config.agent.together_api_key = ""
                self.config.agent.together_api_key = self.together_key.text()
            
            self.config.ui.show_tool_calls = self.show_tool_calls.isChecked()
            self.config.ui.markdown = self.markdown_enabled.isChecked()
            
            # Save to database
            if save_config(self.config):
                QMessageBox.information(self, "Success", "Configuration saved successfully!")
            else:
                QMessageBox.critical(self, "Error", "Failed to save configuration")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error saving configuration: {str(e)}")


class AITerminalMainWindow(QMainWindow):
    """Main window for the AI OS Terminal application"""
    
    def __init__(self):
        super().__init__()
        self.logger = self.setup_logging()
        self.settings = QSettings("AI-OS", "Terminal")
        
        self.setup_ui()
        self.setup_menubar()
        self.setup_statusbar()
        self.setup_system_tray()
        
        # Restore window state
        self.restore_window_state()
        
    def setup_logging(self):
        """Setup logging for the application"""
        logger = logging.getLogger("AITerminal")
        logger.setLevel(logging.DEBUG)
        
        # Console handler
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "[%(asctime)s] [%(name)s:%(levelname)s] %(message)s"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        # File handler
        log_dir = Path.home() / ".ai-os" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_dir / "gui.log")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
        
    def setup_ui(self):
        """Setup the main user interface"""
        self.setWindowTitle("AI OS Terminal - Enhanced Multi-Provider Assistant")
        self.setMinimumSize(1200, 800)
        
        # Create central widget with tabs
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QHBoxLayout(central_widget)
        
        # Main splitter
        splitter = QSplitter(Qt.Horizontal)
        
        # Terminal widget (main area)
        self.terminal_widget = AITerminalWidget(self, self.logger)
        splitter.addWidget(self.terminal_widget)
        
        # Configuration panel (sidebar)
        self.config_panel = ConfigPanel(self)
        splitter.addWidget(self.config_panel)
        
        # Set splitter proportions (terminal takes most space)
        splitter.setSizes([800, 400])
        
        layout.addWidget(splitter)
        
        # Start terminal after UI is ready
        QTimer.singleShot(500, self.terminal_widget.start_terminal)
        
    def setup_menubar(self):
        """Setup the application menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_action = QAction("&New Terminal", self)
        new_action.setShortcut(QKeySequence.New)
        new_action.triggered.connect(self.new_terminal)
        file_menu.addAction(new_action)
        
        file_menu.addSeparator()
        
        export_action = QAction("&Export Session", self)
        export_action.triggered.connect(self.export_session)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        toggle_config_action = QAction("Toggle &Configuration Panel", self)
        toggle_config_action.setShortcut("F9")
        toggle_config_action.triggered.connect(self.toggle_config_panel)
        view_menu.addAction(toggle_config_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_statusbar(self):
        """Setup the status bar"""
        self.statusbar = self.statusBar()
        
        # Provider status
        self.provider_label = QLabel("Provider: Not Connected")
        self.statusbar.addWidget(self.provider_label)
        
        if AI_OS_AVAILABLE:
            config = load_config()
            self.provider_label.setText(f"Provider: {config.agent.provider.title()}")
        
        self.statusbar.addPermanentWidget(QLabel(f"Platform: {platform.system()}"))
        
    def setup_system_tray(self):
        """Setup system tray icon"""
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = QSystemTrayIcon(self)
            
            # Create a simple icon (you can replace with a proper icon file)
            icon = self.style().standardIcon(self.style().SP_ComputerIcon)
            self.tray_icon.setIcon(icon)
            
            # Tray menu
            tray_menu = QMenu()
            
            show_action = tray_menu.addAction("Show")
            show_action.triggered.connect(self.show)
            
            tray_menu.addSeparator()
            
            quit_action = tray_menu.addAction("Quit")
            quit_action.triggered.connect(self.close)
            
            self.tray_icon.setContextMenu(tray_menu)
            self.tray_icon.activated.connect(self.tray_icon_activated)
            self.tray_icon.show()
            
    def tray_icon_activated(self, reason):
        """Handle system tray icon activation"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()
                self.activateWindow()
                
    def new_terminal(self):
        """Open a new terminal window"""
        new_window = AITerminalMainWindow()
        new_window.show()
        
    def export_session(self):
        """Export the current session"""
        filename, _ = QFileDialog.getSaveFileName(
            self, 
            "Export Session", 
            f"ai_os_session_{platform.system().lower()}.txt",
            "Text Files (*.txt);;All Files (*)"
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(f"AI OS Terminal Session Export\n")
                    f.write(f"Platform: {platform.system()}\n")
                    f.write(f"Export Time: {self.terminal_widget.terminal.current_time}\n")
                    f.write("\n" + "="*50 + "\n\n")
                    # Add terminal content here if available
                    
                QMessageBox.information(self, "Success", f"Session exported to {filename}")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export session: {str(e)}")
                
    def toggle_config_panel(self):
        """Toggle the configuration panel visibility"""
        self.config_panel.setVisible(not self.config_panel.isVisible())
        
    def show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>AI OS Terminal</h2>
        <p>Enhanced Multi-Provider AI Terminal Assistant</p>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Platform:</b> {platform}</p>
        <p><b>Qt Version:</b> {qt_version}</p>
        <br>
        <p>Supported AI Providers:</p>
        <ul>
        <li>OpenAI (GPT models)</li>
        <li>Google (Gemini models)</li>
        <li>OpenRouter (200+ models)</li>
        <li>Together AI (Open source models)</li>
        </ul>
        """.format(platform=platform.system(), qt_version=QT_VERSION)
        
        QMessageBox.about(self, "About AI OS Terminal", about_text)
        
    def restore_window_state(self):
        """Restore window geometry and state"""
        geometry = self.settings.value("geometry")
        if geometry:
            self.restoreGeometry(geometry)
            
        state = self.settings.value("windowState")
        if state:
            self.restoreState(state)
            
    def closeEvent(self, event):
        """Handle window close event"""
        # Save window state
        self.settings.setValue("geometry", self.saveGeometry())
        self.settings.setValue("windowState", self.saveState())
        
        # Hide to system tray instead of closing if available
        if hasattr(self, 'tray_icon') and self.tray_icon.isVisible():
            self.hide()
            event.ignore()
        else:
            event.accept()


def main():
    """Main application entry point"""
    # Enable high DPI scaling
    if QT_VERSION.startswith("5"):
        QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    
    app = QApplication(sys.argv)
    app.setApplicationName("AI OS Terminal")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("AI-OS")
    app.setOrganizationDomain("ai-os.dev")
    
    # Create and show main window
    window = AITerminalMainWindow()
    window.show()
    
    # Run the application
    sys.exit(app.exec())


if __name__ == "__main__":
    main()