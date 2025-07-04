"""
Databases tab for PostgreSQL Template Manager.
"""

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QVBoxLayout, QFormLayout, QComboBox, 
                                QLineEdit, QPushButton, QGroupBox, QListWidget)
from .base_tab import BaseTab


class DatabasesTab(BaseTab):
    """Tab for managing databases created from templates."""
    
    # Signals
    databases_refreshed = pyqtSignal(list)  # List of database names
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
    
    def setup_ui(self):
        """Setup the databases tab UI."""
        layout = QVBoxLayout(self)
        
        # Create database section
        create_group = QGroupBox("Create Database from Template")
        create_layout = QFormLayout(create_group)
        
        self.template_combo = QComboBox()
        self.new_db_name_edit = QLineEdit()
        self.create_db_btn = QPushButton("Create Database")
        self.create_db_btn.clicked.connect(self.create_database)
        
        create_layout.addRow("Template:", self.template_combo)
        create_layout.addRow("New Database Name:", self.new_db_name_edit)
        create_layout.addWidget(self.create_db_btn)
        
        layout.addWidget(create_group)
        
        # Databases list section
        list_group = QGroupBox("Existing Databases")
        list_layout = QVBoxLayout(list_group)
        
        self.refresh_databases_btn = QPushButton("Refresh")
        self.refresh_databases_btn.clicked.connect(self.refresh_databases)
        list_layout.addWidget(self.refresh_databases_btn)
        
        self.databases_list = QListWidget()
        list_layout.addWidget(self.databases_list)
        
        layout.addWidget(list_group)
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.db_manager.operation_finished.connect(self.on_operation_finished)
    
    def refresh_databases(self):
        """Refresh databases list."""
        if not self.check_connection():
            return
        
        try:
            databases = self.db_manager.get_databases()
            self.databases_list.clear()
            self.databases_list.addItems(databases)
            
            self.emit_log(f"Refreshed databases: {len(databases)} found")
            self.databases_refreshed.emit(databases)
        except Exception as e:
            self.emit_log(f"Error refreshing databases: {str(e)}")
    
    def refresh_templates(self, templates):
        """Refresh templates combo box."""
        current_selection = self.template_combo.currentText()
        self.template_combo.clear()
        self.template_combo.addItems(templates)
        
        # Restore previous selection if it still exists
        if current_selection in templates:
            self.template_combo.setCurrentText(current_selection)
    
    def create_database(self):
        """Create database from selected template."""
        if not self.check_connection():
            return
        
        template_name = self.template_combo.currentText()
        new_db_name = self.new_db_name_edit.text().strip()
        
        if not self.validate_selection(self.template_combo, "template"):
            return
        
        if not self.validate_non_empty_field(new_db_name, "database name"):
            return
        
        # Check if database name is valid (basic validation)
        if not self._is_valid_database_name(new_db_name):
            self.show_warning("Invalid database name. Use only letters, numbers, and underscores.")
            return
        
        # Check privileges
        if not self.check_user_privileges():
            return
        
        self.emit_progress_started()
        self.db_manager.create_database_from_template(template_name, new_db_name)
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        if any(keyword in message for keyword in ["database", "Database"]):
            self.emit_progress_finished()
            
            if success:
                self.emit_log(f"✓ {message}")
                self.new_db_name_edit.clear()
                self.refresh_databases()
            else:
                self.emit_log(f"✗ {message}")
    
    def get_database_names(self):
        """Get list of current database names."""
        return [self.databases_list.item(i).text() 
                for i in range(self.databases_list.count())]
    
    def _is_valid_database_name(self, name):
        """Validate database name format."""
        import re
        # PostgreSQL database names: letters, numbers, underscores, start with letter/underscore
        pattern = r'^[a-zA-Z_][a-zA-Z0-9_]*$'
        return bool(re.match(pattern, name)) and len(name) <= 63