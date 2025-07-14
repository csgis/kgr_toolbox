"""
Clean QGS tab for removing database credentials from QGIS project files.
"""

import os
import re
import xml.etree.ElementTree as ET
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (QVBoxLayout, QHBoxLayout, QFormLayout, 
                                QPushButton, QGroupBox, QLabel, QLineEdit,
                                QFileDialog, QMessageBox, QTextEdit, QCheckBox,
                                QTableWidget, QTableWidgetItem, QHeaderView)
from qgis.PyQt.QtGui import QFont
from .base_tab import BaseTab


class CleanQGSTab(BaseTab):
    """Tab for cleaning database credentials from QGIS project files."""
    
    # Signals
    file_cleaned = pyqtSignal(str)  # Cleaned file path
    
    def __init__(self, db_manager, parent=None):
        super().__init__(db_manager, parent)
    
    def setup_ui(self):
        """Setup the clean QGS tab UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("QGS File Credential Cleaner")
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
        
        # File selection section
        file_section = QGroupBox("Select QGS File")
        file_layout = QVBoxLayout(file_section)
        
        file_select_layout = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setPlaceholderText("Select a QGIS project file (.qgs or .qgz)")
        self.file_path_edit.setReadOnly(True)
        
        self.browse_btn = QPushButton("Browse...")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_select_layout.addWidget(self.file_path_edit)
        file_select_layout.addWidget(self.browse_btn)
        file_layout.addLayout(file_select_layout)
        
        layout.addWidget(file_section)
        
        # Options section
        options_section = QGroupBox("Cleaning Options")
        options_layout = QVBoxLayout(options_section)
        
        self.remove_user_checkbox = QCheckBox("Remove user credentials")
        self.remove_user_checkbox.setChecked(True)
        self.remove_user_checkbox.setToolTip("Remove 'user' parameter from datasource connections")
        
        self.remove_password_checkbox = QCheckBox("Remove password credentials")
        self.remove_password_checkbox.setChecked(True)
        self.remove_password_checkbox.setToolTip("Remove 'password' parameter from datasource connections")
        
        options_layout.addWidget(self.remove_user_checkbox)
        options_layout.addWidget(self.remove_password_checkbox)
        
        layout.addWidget(options_section)
        
        # Action buttons
        action_layout = QHBoxLayout()
        
        self.preview_btn = QPushButton("Preview Changes")
        self.preview_btn.clicked.connect(self.preview_changes)
        self.preview_btn.setEnabled(False)
        
        self.clean_btn = QPushButton("Clean File")
        self.clean_btn.clicked.connect(self.clean_file)
        self.clean_btn.setEnabled(False)
        self.clean_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; "
            "color: white; "
            "font-weight: bold; "
            "padding: 8px 16px; "
            "border: none; "
            "border-radius: 4px; "
            "} "
            "QPushButton:hover { background-color: #45a049; } "
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        
        action_layout.addWidget(self.preview_btn)
        action_layout.addStretch()
        action_layout.addWidget(self.clean_btn)
        layout.addLayout(action_layout)
        
        # Preview section
        preview_section = QGroupBox("Preview Changes")
        preview_layout = QVBoxLayout(preview_section)
        
        self.preview_table = QTableWidget()
        self.preview_table.setColumnCount(3)
        self.preview_table.setHorizontalHeaderLabels(["#", "Original Datasource", "Cleaned Datasource"])
        
        # Configure table appearance
        self.preview_table.setAlternatingRowColors(True)
        self.preview_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.preview_table.verticalHeader().setVisible(False)
        
        # Set column widths
        header = self.preview_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # # column
        header.setSectionResizeMode(1, QHeaderView.Stretch)  # Original column
        header.setSectionResizeMode(2, QHeaderView.Stretch)  # Cleaned column
        
        # Set maximum height and word wrap
        self.preview_table.setMaximumHeight(250)
        self.preview_table.setWordWrap(True)
        self.preview_table.setTextElideMode(3)  # ElideNone - don't truncate
        
        # Add placeholder message
        self.preview_info_label = QLabel("Select a file and click 'Preview Changes' to see what will be modified...")
        self.preview_info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
        
        preview_layout.addWidget(self.preview_info_label)
        preview_layout.addWidget(self.preview_table)
        
        # Initially hide table and show info label
        self.preview_table.setVisible(False)
        
        layout.addWidget(preview_section)
        
        # Connect file path changes to enable/disable buttons
        self.file_path_edit.textChanged.connect(self._on_file_path_changed)
    
    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>QGS File Credential Cleaner</h3>"
            "<p>This tool removes database credentials (user/password) from QGIS project files.</p>"
            "<h4>How it works:</h4>"
            "<ul>"
            "<li>Scans the QGS/QGZ file for PostgreSQL datasource connections</li>"
            "<li>Shows a table preview of what will be changed</li>"
            "<li>Removes user and/or password parameters from connection strings</li>"
            "<li>Creates a cleaned version with '_cleaned' suffix</li>"
            "<li>Original file remains untouched</li>"
            "</ul>"
            "<h4>Example:</h4>"
            "<p><b>Before:</b> dbname='mydb' host=localhost user='admin' password='secret'</p>"
            "<p><b>After:</b> dbname='mydb' host=localhost</p>"
            "<h4>Supported file types:</h4>"
            "<ul>"
            "<li><b>.qgs files:</b> Direct XML processing</li>"
            "<li><b>.qgz files:</b> Extracts and processes the contained .qgs file</li>"
            "</ul>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - QGS File Credential Cleaner")
        msg.setTextFormat(1)  # Rich text format
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()
    
    def _on_file_path_changed(self, text):
        """Enable/disable buttons based on file path."""
        has_file = bool(text.strip())
        self.preview_btn.setEnabled(has_file)
        self.clean_btn.setEnabled(has_file)
        
        # Clear preview when file changes
        if not has_file:
            self.preview_table.setRowCount(0)
            self.preview_table.setVisible(False)
            self.preview_info_label.setVisible(True)
            self.preview_info_label.setText("Select a file and click 'Preview Changes' to see what will be modified...")
            self.preview_info_label.setStyleSheet("color: #666; font-style: italic; padding: 10px;")
    
    def browse_file(self):
        """Browse for QGS file."""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            self,
            "Select QGIS Project File",
            "",
            "QGIS Project Files (*.qgs *.qgz);;All Files (*)"
        )
        
        if file_path:
            self.file_path_edit.setText(file_path)
            self.emit_log(f"Selected file: {os.path.basename(file_path)}")
    
    def preview_changes(self):
        """Preview what changes will be made to the file."""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            return
        
        try:
            self.emit_progress_started()
            
            # Read and parse the file
            qgs_content = self._read_qgs_file(file_path)
            if not qgs_content:
                return
            
            # Find datasources that would be changed
            changes = self._find_datasource_changes(qgs_content)
            
            if changes:
                # Show table and hide info label
                self.preview_info_label.setVisible(False)
                self.preview_table.setVisible(True)
                
                # Populate table
                self.preview_table.setRowCount(len(changes))
                
                for i, (original, cleaned) in enumerate(changes):
                    # Datasource number
                    num_item = QTableWidgetItem(str(i + 1))
                    num_item.setFlags(num_item.flags() & ~2)  # Remove editable flag
                    self.preview_table.setItem(i, 0, num_item)
                    
                    # Original datasource
                    original_item = QTableWidgetItem(original)
                    original_item.setFlags(original_item.flags() & ~2)  # Remove editable flag
                    original_item.setToolTip(original)  # Full text in tooltip
                    self.preview_table.setItem(i, 1, original_item)
                    
                    # Cleaned datasource
                    cleaned_item = QTableWidgetItem(cleaned)
                    cleaned_item.setFlags(cleaned_item.flags() & ~2)  # Remove editable flag
                    cleaned_item.setToolTip(cleaned)  # Full text in tooltip
                    self.preview_table.setItem(i, 2, cleaned_item)
                
                # Auto-resize rows to content
                self.preview_table.resizeRowsToContents()
                
                self.emit_log(f"Preview completed: {len(changes)} datasource(s) with credentials found")
            else:
                # Hide table and show info message
                self.preview_table.setVisible(False)
                self.preview_info_label.setVisible(True)
                self.preview_info_label.setText("No datasources with credentials found in this file.")
                self.preview_info_label.setStyleSheet("color: #4CAF50; font-style: italic; padding: 10px;")
                
                self.emit_log("Preview completed: No datasources with credentials found")
            
        except Exception as e:
            self.show_error(f"Error previewing file: {str(e)}")
            self.emit_log(f"Error during preview: {str(e)}")
        finally:
            self.emit_progress_finished()
    
    def clean_file(self):
        """Clean the selected QGS file."""
        file_path = self.file_path_edit.text().strip()
        if not file_path:
            return
        
        if not os.path.exists(file_path):
            self.show_error("Selected file does not exist.")
            return
        
        try:
            self.emit_progress_started()
            
            # Read and parse the file
            qgs_content = self._read_qgs_file(file_path)
            if not qgs_content:
                return
            
            # Clean the content
            cleaned_content, changes_count = self._clean_datasources(qgs_content)
            
            if changes_count == 0:
                self.emit_log("No credentials found to clean in the file.")
                self.show_info("No credentials found to clean in the file.")
                return
            
            # Generate cleaned file path
            base_name, ext = os.path.splitext(file_path)
            cleaned_path = f"{base_name}_cleaned{ext}"
            
            # Write cleaned content
            self._write_qgs_file(cleaned_path, cleaned_content, file_path.endswith('.qgz'))
            
            # Emit success signal
            self.file_cleaned.emit(cleaned_path)
            
            success_msg = (f"✓ File cleaned successfully!\n"
                          f"• Cleaned {changes_count} datasource(s)\n"
                          f"• Original file preserved\n"
                          f"• Saved to: {os.path.basename(cleaned_path)}")
            
            self.emit_log(success_msg.replace('\n', ' '))
            self.show_info(success_msg)
            
        except Exception as e:
            self.show_error(f"Error cleaning file: {str(e)}")
            self.emit_log(f"Error during cleaning: {str(e)}")
        finally:
            self.emit_progress_finished()
    
    def _read_qgs_file(self, file_path):
        """Read QGS file content (handles both .qgs and .qgz files)."""
        try:
            if file_path.endswith('.qgz'):
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    # Find the .qgs file in the archive
                    qgs_files = [f for f in zip_file.namelist() if f.endswith('.qgs')]
                    if not qgs_files:
                        raise Exception("No .qgs file found in the .qgz archive")
                    
                    with zip_file.open(qgs_files[0]) as qgs_file:
                        return qgs_file.read().decode('utf-8')
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            self.show_error(f"Error reading file: {str(e)}")
            return None
    
    def _write_qgs_file(self, output_path, content, is_qgz=False):
        """Write QGS file content (handles both .qgs and .qgz files)."""
        if is_qgz:
            import zipfile
            import tempfile
            
            # Create a temporary .qgs file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.qgs', delete=False, encoding='utf-8') as temp_file:
                temp_file.write(content)
                temp_qgs_path = temp_file.name
            
            try:
                # Create the .qgz file
                with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                    zip_file.write(temp_qgs_path, os.path.basename(output_path).replace('.qgz', '.qgs'))
            finally:
                os.unlink(temp_qgs_path)
        else:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
    
    def _find_datasource_changes(self, content):
        """Find datasources that would be changed and return before/after pairs."""
        changes = []
        
        # Pattern to match datasource tags with PostgreSQL connections
        datasource_pattern = r'<datasource>(.*?)</datasource>'
        
        for match in re.finditer(datasource_pattern, content, re.DOTALL):
            original_datasource = match.group(1).strip()
            
            # Check if it's a PostgreSQL connection with credentials
            if self._has_postgres_credentials(original_datasource):
                cleaned_datasource = self._clean_single_datasource(original_datasource)
                if cleaned_datasource != original_datasource:
                    changes.append((original_datasource, cleaned_datasource))
        
        return changes
    
    def _clean_datasources(self, content):
        """Clean all datasources in the content and return cleaned content and count."""
        changes_count = 0
        
        def replace_datasource(match):
            nonlocal changes_count
            original_datasource = match.group(1).strip()
            
            if self._has_postgres_credentials(original_datasource):
                cleaned_datasource = self._clean_single_datasource(original_datasource)
                if cleaned_datasource != original_datasource:
                    changes_count += 1
                    return f'<datasource>{cleaned_datasource}</datasource>'
            
            return match.group(0)
        
        # Pattern to match datasource tags
        datasource_pattern = r'<datasource>(.*?)</datasource>'
        cleaned_content = re.sub(datasource_pattern, replace_datasource, content, flags=re.DOTALL)
        
        return cleaned_content, changes_count
    
    def _has_postgres_credentials(self, datasource):
        """Check if datasource has PostgreSQL credentials."""
        # Check for dbname parameter (indicates PostgreSQL) and credentials
        has_dbname = 'dbname=' in datasource
        has_user = 'user=' in datasource and self.remove_user_checkbox.isChecked()
        has_password = 'password=' in datasource and self.remove_password_checkbox.isChecked()
        
        return has_dbname and (has_user or has_password)
    
    def _clean_single_datasource(self, datasource):
        """Clean a single datasource string."""
        cleaned = datasource
        
        if self.remove_user_checkbox.isChecked():
            # Remove user='...' or user="..." 
            cleaned = re.sub(r"\s*user=['\"][^'\"]*['\"]", "", cleaned)
        
        if self.remove_password_checkbox.isChecked():
            # Remove password='...' or password="..."
            cleaned = re.sub(r"\s*password=['\"][^'\"]*['\"]", "", cleaned)
        
        # Clean up any double spaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned
    
    def connect_signals(self):
        """Connect signals."""
        super().connect_signals()
        # No database manager operations needed for this tab
        pass