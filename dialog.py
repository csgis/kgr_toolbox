import os
import tempfile
import zipfile
import re
from qgis.PyQt.QtCore import Qt, QSettings
from qgis.PyQt.QtWidgets import (QDockWidget, QVBoxLayout, QHBoxLayout, QWidget, 
                                QLabel, QLineEdit, QSpinBox, QPushButton, QComboBox,
                                QTextEdit, QGroupBox, QTabWidget, QFormLayout,
                                QMessageBox, QProgressBar, QListWidget, QSplitter,
                                QCheckBox)
from qgis.PyQt.QtGui import QFont


class PostgreSQLTemplateManagerDialog(QDockWidget):
    """Main dialog for PostgreSQL Template Manager."""
    
    def __init__(self, db_manager, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.dock_area = Qt.LeftDockWidgetArea
        
        # Connect signals
        self.db_manager.operation_finished.connect(self.on_operation_finished)
        self.db_manager.progress_updated.connect(self.on_progress_updated)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """Setup the user interface."""
        self.setWindowTitle("PostgreSQL Template Manager")
        self.setObjectName("PostgreSQLTemplateManager")
        
        # Main widget
        main_widget = QWidget()
        self.setWidget(main_widget)
        
        # Main layout
        layout = QVBoxLayout(main_widget)
        
        # Title
        title = QLabel("PostgreSQL Template Manager")
        title.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        font.setPointSize(12)
        title.setFont(font)
        layout.addWidget(title)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # Connection tab
        self.setup_connection_tab()
        
        # Templates tab
        self.setup_templates_tab()
        
        # Databases tab
        self.setup_databases_tab()
        
        # QGIS Project Layers tab
        self.setup_qgis_projects_tab()
        
        # Progress section
        self.setup_progress_section(layout)
        
    def setup_connection_tab(self):
        """Setup connection tab."""
        conn_widget = QWidget()
        layout = QFormLayout(conn_widget)
        
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
        
        self.tab_widget.addTab(conn_widget, "Connection")
    
    def setup_templates_tab(self):
        """Setup templates tab."""
        template_widget = QWidget()
        layout = QVBoxLayout(template_widget)
        
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
        
        self.tab_widget.addTab(template_widget, "Templates")
    
    def setup_databases_tab(self):
        """Setup databases tab."""
        db_widget = QWidget()
        layout = QVBoxLayout(db_widget)
        
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
        
        self.tab_widget.addTab(db_widget, "Databases")
    
    def setup_qgis_projects_tab(self):
        """Setup QGIS projects tab."""
        qgis_widget = QWidget()
        layout = QVBoxLayout(qgis_widget)
        
        # Database selection section
        db_section = QGroupBox("Select Database")
        db_layout = QVBoxLayout(db_section)
        
        db_select_layout = QHBoxLayout()
        self.qgis_db_combo = QComboBox()
        self.refresh_qgis_db_btn = QPushButton("Refresh")
        self.refresh_qgis_db_btn.clicked.connect(self.refresh_qgis_databases)
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
        self.new_schema_edit = QLineEdit()
        
        params_layout.addRow("New DB Name:", self.new_dbname_edit)
        params_layout.addRow("New Host:", self.new_host_edit)
        params_layout.addRow("New User:", self.new_user_edit)
        params_layout.addRow("New Port:", self.new_port_edit)
        params_layout.addRow("New Password:", self.new_password_edit)
        params_layout.addRow("New Schema:", self.new_schema_edit)
        
        # Create backup checkbox
        self.create_backup_checkbox = QCheckBox("Create local backup")
        self.create_backup_checkbox.setChecked(True)
        params_layout.addWidget(self.create_backup_checkbox)
        
        # Fix project button
        self.fix_project_btn = QPushButton("Fix Project Layers")
        self.fix_project_btn.clicked.connect(self.fix_qgis_project)
        params_layout.addWidget(self.fix_project_btn)
        
        layout.addWidget(params_section)
        
        self.tab_widget.addTab(qgis_widget, "Fix QGIS Project Layers")
    
    def setup_progress_section(self, layout):
        """Setup progress section."""
        progress_group = QGroupBox("Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        progress_layout.addWidget(self.progress_bar)
        
        self.log_text = QTextEdit()
        self.log_text.setMaximumHeight(100)
        self.log_text.setReadOnly(True)
        progress_layout.addWidget(self.log_text)
        
        layout.addWidget(progress_group)
    
    def test_connection(self):
        """Test database connection."""
        self.db_manager.set_connection_params(
            self.host_edit.text(),
            self.port_edit.value(),
            'postgres',  # Connect to default postgres db for testing
            self.username_edit.text(),
            self.password_edit.text()
        )
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.db_manager.test_connection()
    
    def refresh_databases(self):
        """Refresh databases list."""
        if not self.check_connection():
            return
        
        databases = self.db_manager.get_databases()
        self.source_db_combo.clear()
        self.source_db_combo.addItems(databases)
        
        self.databases_list.clear()
        self.databases_list.addItems(databases)
        
        self.log_text.append(f"Refreshed databases: {len(databases)} found")
    
    def refresh_templates(self):
        """Refresh templates list."""
        if not self.check_connection():
            return
        
        templates = self.db_manager.get_templates()
        self.template_combo.clear()
        self.template_combo.addItems(templates)
        
        self.templates_list.clear()
        self.templates_list.addItems(templates)
        
        self.log_text.append(f"Refreshed templates: {len(templates)} found")
    
    def refresh_qgis_databases(self):
        """Refresh databases list for QGIS projects tab."""
        if not self.check_connection():
            return
        
        databases = self.db_manager.get_databases()
        self.qgis_db_combo.clear()
        self.qgis_db_combo.addItems(databases)
        
        self.log_text.append(f"Refreshed QGIS databases: {len(databases)} found")
    
    def search_qgis_projects(self):
        """Search for QGIS projects in selected database."""
        if not self.check_connection():
            return
        
        selected_db = self.qgis_db_combo.currentText()
        if not selected_db:
            QMessageBox.warning(self, "Warning", "Please select a database.")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        projects = self.db_manager.find_qgis_projects(selected_db)
        
        self.qgis_projects_combo.clear()
        if projects:
            project_items = [f"{p['schema']}.{p['table']} - {p['name']}" for p in projects]
            self.qgis_projects_combo.addItems(project_items)
            self.log_text.append(f"Found {len(projects)} QGIS projects in {selected_db}")
        else:
            self.log_text.append(f"No QGIS projects found in {selected_db}")
        
        self.progress_bar.setVisible(False)
    
    def fix_qgis_project(self):
        """Fix selected QGIS project layers."""
        if not self.check_connection():
            return
        
        selected_db = self.qgis_db_combo.currentText()
        selected_project = self.qgis_projects_combo.currentText()
        
        if not selected_db or not selected_project:
            QMessageBox.warning(self, "Warning", "Please select a database and project.")
            return
        
        # Parse project info
        try:
            schema_table, project_name = selected_project.split(" - ", 1)
            schema, table = schema_table.split(".", 1)
        except ValueError:
            QMessageBox.critical(self, "Error", "Invalid project selection format.")
            return
        
        # Collect new connection parameters
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
        if self.new_schema_edit.text().strip():
            new_params['schema'] = self.new_schema_edit.text().strip()
        
        if not new_params:
            QMessageBox.warning(self, "Warning", "Please specify at least one parameter to update.")
            return
        
        create_backup = self.create_backup_checkbox.isChecked()
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        
        self.db_manager.fix_qgis_project_layers(
            selected_db, schema, table, project_name, new_params, create_backup
        )
    
    def create_template(self):
        """Create template from selected database."""
        if not self.check_connection():
            return
        
        source_db = self.source_db_combo.currentText()
        template_name = self.template_name_edit.text().strip()
        
        if not source_db:
            QMessageBox.warning(self, "Warning", "Please select a source database.")
            return
        
        if not template_name:
            QMessageBox.warning(self, "Warning", "Please enter a template name.")
            return
        
        # Check privileges
        privileges = self.db_manager.check_user_privileges()
        if not privileges['can_create_db'] and not privileges['is_superuser']:
            QMessageBox.critical(self, "Error", 
                               "Insufficient privileges. CREATEDB permission required.")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.db_manager.create_template(source_db, template_name)
    
    def create_database(self):
        """Create database from selected template."""
        if not self.check_connection():
            return
        
        template_name = self.template_combo.currentText()
        new_db_name = self.new_db_name_edit.text().strip()
        
        if not template_name:
            QMessageBox.warning(self, "Warning", "Please select a template.")
            return
        
        if not new_db_name:
            QMessageBox.warning(self, "Warning", "Please enter a database name.")
            return
        
        # Check privileges
        privileges = self.db_manager.check_user_privileges()
        if not privileges['can_create_db'] and not privileges['is_superuser']:
            QMessageBox.critical(self, "Error", 
                               "Insufficient privileges. CREATEDB permission required.")
            return
        
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.db_manager.create_database_from_template(template_name, new_db_name)
    
    def delete_template(self):
        """Delete selected template."""
        if not self.check_connection():
            return
        
        current_item = self.templates_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Warning", "Please select a template to delete.")
            return
        
        template_name = current_item.text()
        
        reply = QMessageBox.question(self, "Confirm Delete", 
                                   f"Are you sure you want to delete template '{template_name}'?\n"
                                   "This action cannot be undone!",
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.db_manager.delete_template(template_name)
    
    def check_connection(self):
        """Check if connection is established."""
        if not self.db_manager.connection_params:
            QMessageBox.warning(self, "Warning", "Please test the connection first.")
            return False
        return True
    
    def on_operation_finished(self, success, message):
        """Handle operation finished signal."""
        self.progress_bar.setVisible(False)
        
        if success:
            self.log_text.append(f"✓ {message}")
            self.conn_status.setText("Connected")
            self.conn_status.setStyleSheet("color: green;")
            
            # Refresh lists after successful operations
            self.refresh_databases()
            self.refresh_templates()
            self.refresh_qgis_databases()
        else:
            self.log_text.append(f"✗ {message}")
            if "Connection failed" in message:
                self.conn_status.setText("Connection failed")
                self.conn_status.setStyleSheet("color: red;")
    
    def on_progress_updated(self, message):
        """Handle progress update signal."""
        self.log_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.log_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def save_settings(self):
        """Save dialog settings."""
        settings = QSettings()
        settings.beginGroup("PostgreSQLTemplateManager")
        settings.setValue("host", self.host_edit.text())
        settings.setValue("port", self.port_edit.value())
        settings.setValue("username", self.username_edit.text())
        settings.endGroup()
    
    def load_settings(self):
        """Load dialog settings."""
        settings = QSettings()
        settings.beginGroup("PostgreSQLTemplateManager")
        self.host_edit.setText(settings.value("host", "localhost"))
        self.port_edit.setValue(int(settings.value("port", 5432)))
        self.username_edit.setText(settings.value("username", ""))
        settings.endGroup()
    
    def closeEvent(self, event):
        """Handle close event."""
        self.save_settings()
        event.accept()