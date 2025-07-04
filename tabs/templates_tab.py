"""
Templates tab for PostgreSQL Template Manager.
Enhanced with connection handling and user warnings.
"""

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, 
                                QComboBox, QLineEdit, QPushButton, QGroupBox,
                                QListWidget, QMessageBox, QDialog, QDialogButtonBox,
                                QLabel, QTextEdit)
from .base_tab import BaseTab


class ConnectionWarningDialog(QDialog):
    """Dialog to warn user about dropping connections."""
    
    def __init__(self, database_name, connection_count, connections_info, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Drop Database Connections")
        self.setModal(True)
        self.resize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Warning message
        warning_label = QLabel(
            f"<b>Warning:</b> Creating a template from database '<b>{database_name}</b>' "
            f"requires dropping all active connections.\n\n"
            f"<b>{connection_count}</b> active connection(s) found and will be terminated."
        )
        warning_label.setWordWrap(True)
        warning_label.setStyleSheet("QLabel { color: #d32f2f; margin: 10px; }")
        layout.addWidget(warning_label)
        
        # Connection details
        if connections_info:
            details_label = QLabel("Active connections that will be dropped:")
            details_label.setStyleSheet("font-weight: bold; margin: 10px;")
            layout.addWidget(details_label)
            
            details_text = QTextEdit()
            details_text.setReadOnly(True)
            details_text.setMaximumHeight(150)
            
            connection_details = []
            for conn_info in connections_info:
                pid, username, client_addr, client_hostname, client_port, backend_start, state, query = conn_info
                client_display = client_addr or client_hostname or "local"
                connection_details.append(
                    f"• PID: {pid}, User: {username}, Client: {client_display}, "
                    f"State: {state}, Started: {backend_start}"
                )
            
            details_text.setPlainText("\n".join(connection_details))
            layout.addWidget(details_text)
        
        # Confirmation message
        confirm_label = QLabel(
            "This action will:\n"
            "• Terminate all active connections to the database\n"
            "• Create a new template with the database structure\n"
            "• Remove all data from the template\n\n"
            "Do you want to continue?"
        )
        confirm_label.setWordWrap(True)
        confirm_label.setStyleSheet("margin: 10px;")
        layout.addWidget(confirm_label)
        
        # Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.Yes | QDialogButtonBox.No,
            parent=self
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Style the buttons
        yes_button = button_box.button(QDialogButtonBox.Yes)
        yes_button.setText("Yes, Drop Connections and Create Template")
        yes_button.setStyleSheet("QPushButton { background-color: #d32f2f; color: white; padding: 5px; }")
        
        no_button = button_box.button(QDialogButtonBox.No)
        no_button.setText("Cancel")
        no_button.setStyleSheet("QPushButton { padding: 5px; }")
        
        layout.addWidget(button_box)


class TemplatesTab(BaseTab):
    """Tab for managing database templates."""
    
    # Signals
    templates_refreshed = pyqtSignal(list)  # List of template names
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
    
    def setup_ui(self):
        """Setup the templates tab UI."""
        layout = QVBoxLayout(self)
        
        # Create template section
        create_group = QGroupBox("Create Template")
        create_layout = QFormLayout(create_group)
        
        self.source_db_combo = QComboBox()
        self.template_name_edit = QLineEdit()
        self.create_template_btn = QPushButton("Create Template")
        self.create_template_btn.clicked.connect(self.create_template)
        
        create_layout.addRow("Source Database:", self.source_db_combo)
        create_layout.addRow("Template Name:", self.template_name_edit)
        create_layout.addWidget(self.create_template_btn)
        
        layout.addWidget(create_group)
        
        # Templates list section
        list_group = QGroupBox("Existing Templates")
        list_layout = QVBoxLayout(list_group)
        
        # Refresh and delete buttons
        btn_layout = QHBoxLayout()
        self.refresh_templates_btn = QPushButton("Refresh")
        self.refresh_templates_btn.clicked.connect(self.refresh_templates)
        self.delete_template_btn = QPushButton("Delete Selected")
        self.delete_template_btn.clicked.connect(self.delete_template)
        
        btn_layout.addWidget(self.refresh_templates_btn)
        btn_layout.addWidget(self.delete_template_btn)
        list_layout.addLayout(btn_layout)
        
        # Templates list
        self.templates_list = QListWidget()
        list_layout.addWidget(self.templates_list)
        
        layout.addWidget(list_group)
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.db_manager.operation_finished.connect(self.on_operation_finished)
    
    def refresh_templates(self):
        """Refresh templates list."""
        if not self.check_connection():
            return
        
        try:
            templates = self.db_manager.get_templates()
            self.templates_list.clear()
            self.templates_list.addItems(templates)
            
            self.emit_log(f"Refreshed templates: {len(templates)} found")
            self.templates_refreshed.emit(templates)
        except Exception as e:
            self.emit_log(f"Error refreshing templates: {str(e)}")
    
    def refresh_source_databases(self, databases):
        """Refresh source databases combo box."""
        self.source_db_combo.clear()
        self.source_db_combo.addItems(databases)
    
    def create_template(self):
        """Create template from selected database."""
        if not self.check_connection():
            return
        
        source_db = self.source_db_combo.currentText()
        template_name = self.template_name_edit.text().strip()
        
        if not self.validate_selection(self.source_db_combo, "source database"):
            return
        
        if not self.validate_non_empty_field(template_name, "template name"):
            return
        
        # Check privileges
        if not self.check_user_privileges():
            return
        
        # Check for active connections
        try:
            connection_count = self.db_manager.get_connection_count(source_db)
            
            if connection_count > 0:
                # Get detailed connection information
                connections_info = self.db_manager.get_active_connections(source_db)
                
                # Show warning dialog
                dialog = ConnectionWarningDialog(
                    source_db, 
                    connection_count, 
                    connections_info, 
                    self
                )
                
                if dialog.exec_() != QDialog.Accepted:
                    self.emit_log("Template creation cancelled by user")
                    return
                
                self.emit_log(f"User confirmed dropping {connection_count} connections to '{source_db}'")
            else:
                # No active connections, but still show a confirmation
                reply = QMessageBox.question(
                    self,
                    "Create Template",
                    f"Create template '{template_name}' from database '{source_db}'?\n\n"
                    "This will create a copy of the database structure without data.",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )
                
                if reply != QMessageBox.Yes:
                    return
            
            # Proceed with template creation
            self.emit_progress_started()
            self.db_manager.create_template(source_db, template_name)
            
        except Exception as e:
            self.emit_log(f"Error checking connections: {str(e)}")
            self.show_warning(f"Error checking database connections: {str(e)}")
    
    def delete_template(self):
        """Delete selected template."""
        if not self.check_connection():
            return
        
        current_item = self.templates_list.currentItem()
        if not current_item:
            self.show_warning("Please select a template to delete.")
            return
        
        template_name = current_item.text()
        
        if self.confirm_action("Confirm Delete", 
                              f"Are you sure you want to delete template '{template_name}'?\n"
                              "This action cannot be undone!"):
            self.emit_progress_started()
            self.db_manager.delete_template(template_name)
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        if any(keyword in message for keyword in ["template", "Template"]):
            self.emit_progress_finished()
            
            if success:
                self.emit_log(f"✓ {message}")
                self.template_name_edit.clear()
                self.refresh_templates()
            else:
                self.emit_log(f"✗ {message}")
    
    def get_template_names(self):
        """Get list of current template names."""
        return [self.templates_list.item(i).text() 
                for i in range(self.templates_list.count())]
    
