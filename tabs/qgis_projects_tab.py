"""
QGIS Projects tab for PostgreSQL Template Manager.
"""

from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, 
                                QComboBox, QLineEdit, QSpinBox, QPushButton, 
                                QGroupBox, QLabel, QCheckBox, QMessageBox)
from qgis.PyQt.QtGui import QFont
from .base_tab import BaseTab


class QGISProjectsTab(BaseTab):
    """Tab for fixing QGIS project layers."""
    
    # Signals
    projects_found = pyqtSignal(list)  # List of projects found
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
    
    def setup_ui(self):
        """Setup the QGIS projects tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("QGIS Project Layer Updater")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        
        self.help_btn = QPushButton("Help")
        self.help_btn.setFixedWidth(80)
        self.help_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #2196F3; "
            "color: white; "
            "font-weight: bold; "
            "padding: 5px 10px; "
            "border: none; "
            "border-radius: 4px; "
            "font-size: 12px; "
            "} "
            "QPushButton:hover { background-color: #1976D2; }"
        )
        self.help_btn.clicked.connect(self._show_help_popup)
        
        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(self.help_btn)
        layout.addLayout(title_layout)
        
        # Database selection section
        db_section = QGroupBox("Select Database")
        db_layout = QVBoxLayout(db_section)
        
        db_select_layout = QHBoxLayout()
        self.qgis_db_combo = QComboBox()
        self.refresh_qgis_db_btn = QPushButton("Refresh")

        self.refresh_qgis_db_btn.clicked.connect(lambda: self.refresh_qgis_databases())
        self.search_projects_btn = QPushButton("Search Projects")
        self.search_projects_btn.clicked.connect(self.search_qgis_projects)
        
        db_select_layout.addWidget(QLabel("Database:"))
        db_select_layout.addWidget(self.qgis_db_combo)
        db_select_layout.addWidget(self.refresh_qgis_db_btn)
        db_select_layout.addWidget(self.search_projects_btn)
        db_layout.addLayout(db_select_layout)
        
        layout.addWidget(db_section)
        
        # Project selection section
        project_section = QGroupBox("Select Project")
        project_layout = QVBoxLayout(project_section)
        
        self.qgis_projects_combo = QComboBox()
        project_layout.addWidget(self.qgis_projects_combo)
        
        layout.addWidget(project_section)
        
        # Connection parameters section
        params_section = QGroupBox("New Connection Parameters")
        params_layout = QFormLayout(params_section)
        
        self.new_dbname_edit = QLineEdit()
        self.new_host_edit = QLineEdit()
        self.new_user_edit = QLineEdit()
        self.new_port_edit = QSpinBox()
        self.new_port_edit.setRange(1, 65535)
        self.new_port_edit.setValue(5432)
        self.new_password_edit = QLineEdit()
        self.new_password_edit.setEchoMode(QLineEdit.Password)
        
        # Schema remapping fields
        self.source_schema_edit = QLineEdit()
        self.target_schema_edit = QLineEdit()
        
        params_layout.addRow("New DB Name:", self.new_dbname_edit)
        params_layout.addRow("New Host:", self.new_host_edit)
        params_layout.addRow("New User:", self.new_user_edit)
        params_layout.addRow("New Port:", self.new_port_edit)
        params_layout.addRow("New Password:", self.new_password_edit)
        params_layout.addRow("<b>Schema Remapping:</b>", None)
        params_layout.addRow("Source Schema (old):", self.source_schema_edit)
        params_layout.addRow("Target Schema (new):", self.target_schema_edit)
        
        # Add tooltips for schema fields
        self.source_schema_edit.setToolTip("Original schema name to replace (e.g., 'dogs')")
        self.target_schema_edit.setToolTip("New schema name to use (e.g., 'cats')")
        
        # Create backup checkbox
        self.create_backup_checkbox = QCheckBox("Create local backup")
        self.create_backup_checkbox.setChecked(True)
        params_layout.addWidget(self.create_backup_checkbox)
        
        # Fix project button
        self.fix_project_btn = QPushButton("Fix Project Layers")
        self.fix_project_btn.clicked.connect(self.fix_qgis_project)
        params_layout.addWidget(self.fix_project_btn)
        
        layout.addWidget(params_section)

    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>QGIS Project Layer Updater</h3>"
            "<p>This tool updates PostgreSQL connection parameters in QGIS project files.</p>"
            "<h4>How it works:</h4>"
            "<ul>"
            "<li><b>Empty fields are ignored</b> and won't be changed</li>"
            "<li><b>Schema remapping:</b> specify 'Source Schema' (old) and 'Target Schema' (new)</li>"
            "<li><b>Both schema fields filled:</b> only layers using the source schema will be updated</li>"
            "<li><b>Only 'Target Schema' filled:</b> ALL layers will use this schema</li>"
            "<li><b>Other parameters</b> (host, user, etc.) apply to all matching layers</li>"
            "</ul>"
            "<h4>Examples:</h4>"
            "<p><b>Schema remapping:</b> Source='dogs', Target='cats' → only 'dogs' schema layers become 'cats'</p>"
            "<p><b>Global schema change:</b> Target='production' → all layers use 'production' schema</p>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - QGIS Project Layer Updater")
        msg.setTextFormat(1)  # Rich text format
        msg.setText(help_text)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        self.db_manager.operation_finished.connect(self.on_operation_finished)
    
    def refresh_qgis_databases(self, databases=None):
        """Refresh databases list for QGIS projects tab."""
        if databases is None:
            if not self.check_connection():
                return
            
            try:
                databases = self.db_manager.get_databases()
            except Exception as e:
                self.emit_log(f"Error refreshing QGIS databases: {str(e)}")
                return
        
        self.qgis_db_combo.clear()
        self.qgis_db_combo.addItems(databases)
        self.emit_log(f"Refreshed QGIS databases: {len(databases)} found")
    
    def search_qgis_projects(self):
        """Search for QGIS projects in selected database."""
        if not self.check_connection():
            return
        
        selected_db = self.qgis_db_combo.currentText()
        if not self.validate_selection(self.qgis_db_combo, "database"):
            return
        
        self.emit_progress_started()
        
        try:
            projects = self.db_manager.find_qgis_projects(selected_db)
            
            self.qgis_projects_combo.clear()
            if projects:
                project_items = [f"{p['schema']}.{p['table']} - {p['name']}" for p in projects]
                self.qgis_projects_combo.addItems(project_items)
                self.emit_log(f"Found {len(projects)} QGIS projects in {selected_db}")
                self.projects_found.emit(projects)
            else:
                self.emit_log(f"No QGIS projects found in {selected_db}")
                self.projects_found.emit([])
        except Exception as e:
            self.emit_log(f"Error searching for QGIS projects: {str(e)}")
        
        self.emit_progress_finished()
    
    def fix_qgis_project(self):
        """Fix selected QGIS project layers."""
        if not self.check_connection():
            return
        
        selected_db = self.qgis_db_combo.currentText()
        selected_project = self.qgis_projects_combo.currentText()
        
        if not self.validate_selection(self.qgis_db_combo, "database"):
            return
        if not self.validate_selection(self.qgis_projects_combo, "project"):
            return
        
        # Parse project info
        try:
            schema_table, project_name = selected_project.split(" - ", 1)
            schema, table = schema_table.split(".", 1)
        except ValueError:
            self.show_error("Invalid project selection format.")
            return
        
        # Collect new connection parameters
        new_params = self._collect_new_parameters()
        
        if not new_params:
            self.show_warning("Please specify at least one parameter to update.")
            return
        
        create_backup = self.create_backup_checkbox.isChecked()
        
        self.emit_progress_started()
        self.db_manager.fix_qgis_project_layers(
            selected_db, schema, table, project_name, new_params, create_backup
        )
    
    def _collect_new_parameters(self):
        """Collect new connection parameters from form fields."""
        new_params = {}
        
        if self.new_dbname_edit.text().strip():
            new_params['dbname'] = self.new_dbname_edit.text().strip()
        if self.new_host_edit.text().strip():
            new_params['host'] = self.new_host_edit.text().strip()
        if self.new_user_edit.text().strip():
            new_params['user'] = self.new_user_edit.text().strip()
        if self.new_port_edit.value() != 5432:
            new_params['port'] = str(self.new_port_edit.value())
        if self.new_password_edit.text().strip():
            new_params['password'] = self.new_password_edit.text().strip()
        
        # Handle schema remapping logic
        source_schema = self.source_schema_edit.text().strip()
        target_schema = self.target_schema_edit.text().strip()
        
        if source_schema and target_schema:
            # Both schemas specified - remap from source to target
            new_params['schema_remapping'] = {
                'source': source_schema,
                'target': target_schema
            }
            self.emit_log(f"Schema remapping: '{source_schema}' → '{target_schema}'")
        elif target_schema:
            # Only target schema specified - apply to all layers
            new_params['schema'] = target_schema
            self.emit_log(f"Setting schema to '{target_schema}' for all layers")
        elif source_schema:
            # Only source schema specified - this is not a valid configuration
            self.show_warning("Target schema is required when source schema is specified.")
            return {}
        
        return new_params
    
    def clear_parameters(self):
        """Clear all parameter fields."""
        self.new_dbname_edit.clear()
        self.new_host_edit.clear()
        self.new_user_edit.clear()
        self.new_port_edit.setValue(5432)
        self.new_password_edit.clear()
        self.source_schema_edit.clear()
        self.target_schema_edit.clear()
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        if any(keyword in message for keyword in ["project", "Project", "layers", "Layers"]):
            self.emit_progress_finished()
            
            if success:
                self.emit_log(f"✓ {message}")
                self.clear_parameters()
            else:
                self.emit_log(f"✗ {message}")