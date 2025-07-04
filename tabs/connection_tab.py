"""
Connection tab for PostgreSQL Template Manager.
"""

from qgis.PyQt.QtCore import QSettings, pyqtSignal
from qgis.PyQt.QtWidgets import (QFormLayout, QLineEdit, QSpinBox, QPushButton, 
                                QLabel)
from .base_tab import BaseTab


class ConnectionTab(BaseTab):
    """Tab for managing database connections."""
    
    # Signals
    connection_status_changed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
        self.load_settings()
    
    def setup_ui(self):
        """Setup the connection tab UI."""
        layout = QFormLayout(self)
        
        # Connection parameters
        self.host_edit = QLineEdit("localhost")
        self.port_edit = QSpinBox()
        self.port_edit.setRange(1, 65535)
        self.port_edit.setValue(5432)
        self.username_edit = QLineEdit()
        self.password_edit = QLineEdit()
        self.password_edit.setEchoMode(QLineEdit.Password)
        
        layout.addRow("Host:", self.host_edit)
        layout.addRow("Port:", self.port_edit)
        layout.addRow("Username:", self.username_edit)
        layout.addRow("Password:", self.password_edit)
        
        # Test connection button
        self.test_conn_btn = QPushButton("Test Connection")
        self.test_conn_btn.clicked.connect(self.test_connection)
        layout.addWidget(self.test_conn_btn)
        
        # Connection status
        self.conn_status = QLabel("Not connected")
        self.conn_status.setStyleSheet("color: red;")
        layout.addWidget(self.conn_status)
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.db_manager.operation_finished.connect(self.on_operation_finished)
    
    def test_connection(self):
        """Test database connection."""
        host = self.host_edit.text().strip()
        port = self.port_edit.value()
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        # Validate required fields
        if not self.validate_non_empty_field(host, "host"):
            return
        if not self.validate_non_empty_field(username, "username"):
            return
        
        self.db_manager.set_connection_params(
            host, port, 'postgres', username, password
        )
        
        self.emit_progress_started()
        self.db_manager.test_connection()
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        self.emit_progress_finished()
        
        if "Connection" in message:  # This is a connection test result
            if success:
                self.conn_status.setText("Connected")
                self.conn_status.setStyleSheet("color: green;")
                self.emit_log(f"✓ {message}")
                self.save_settings()
            else:
                self.conn_status.setText("Connection failed")
                self.conn_status.setStyleSheet("color: red;")
                self.emit_log(f"✗ {message}")
            
            self.connection_status_changed.emit(success, message)
    
    def get_connection_params(self):
        """Get current connection parameters."""
        return {
            'host': self.host_edit.text().strip(),
            'port': self.port_edit.value(),
            'username': self.username_edit.text().strip(),
            'password': self.password_edit.text().strip()
        }
    
    def is_connected(self):
        """Check if currently connected."""
        return bool(self.db_manager.connection_params)
    
    def save_settings(self):
        """Save connection settings."""
        settings = QSettings()
        settings.beginGroup("PostgreSQLTemplateManager")
        settings.setValue("host", self.host_edit.text())
        settings.setValue("port", self.port_edit.value())
        settings.setValue("username", self.username_edit.text())
        settings.endGroup()
    
    def load_settings(self):
        """Load connection settings."""
        settings = QSettings()
        settings.beginGroup("PostgreSQLTemplateManager")
        self.host_edit.setText(settings.value("host", "localhost"))
        self.port_edit.setValue(int(settings.value("port", 5432)))
        self.username_edit.setText(settings.value("username", ""))
        settings.endGroup()