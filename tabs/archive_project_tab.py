"""
Archive Project tab for PostgreSQL Template Manager.
Custom portable QGIS project exporter (no libqfieldsync).
"""

import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QFileDialog, QProgressBar
)
from qgis.PyQt.QtGui import QFont
from qgis.core import QgsProject, QgsVectorLayer, QgsVectorFileWriter

from .base_tab import BaseTab

class ArchiveProjectTab(BaseTab):
    project_archived = pyqtSignal(str)

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(15)  # Reduce spacing between elements
        layout.setContentsMargins(20, 20, 20, 20)  # Add margins around the whole layout

        # Instructions section
        instructions = QLabel(
            "Export the current project as a portable archive.\n"
            "All PostgreSQL layers will be converted to a single Geopackage."
        )
        instructions.setWordWrap(True)
        font = QFont()
        font.setItalic(True)
        instructions.setFont(font)
        instructions.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(instructions)

        # Output folder section
        folder_group = QVBoxLayout()
        folder_group.setSpacing(8)
        
        folder_label = QLabel("Output Folder:")
        folder_label.setStyleSheet("font-weight: bold;")
        folder_group.addWidget(folder_label)
        
        folder_layout = QHBoxLayout()
        folder_layout.setSpacing(10)
        self.output_folder_edit = QLineEdit()
        self.output_folder_edit.setPlaceholderText("Select output folder...")
        self.browse_folder_btn = QPushButton("Browse…")
        self.browse_folder_btn.setFixedWidth(80)
        folder_layout.addWidget(self.output_folder_edit)
        folder_layout.addWidget(self.browse_folder_btn)
        folder_group.addLayout(folder_layout)
        
        layout.addLayout(folder_group)

        # Archive button
        self.archive_btn = QPushButton("Create Portable Archive")
        self.archive_btn.setStyleSheet(
            "QPushButton { "
            "background-color: #4CAF50; "
            "color: white; "
            "font-weight: bold; "
            "padding: 10px 20px; "
            "border: none; "
            "border-radius: 5px; "
            "font-size: 14px; "
            "} "
            "QPushButton:hover { background-color: #45a049; } "
            "QPushButton:disabled { background-color: #cccccc; }"
        )
        self.archive_btn.setFixedHeight(45)
        layout.addWidget(self.archive_btn)

        # Progress section
        progress_group = QVBoxLayout()
        progress_group.setSpacing(5)
        
        self.progress_label = QLabel("Processing...")
        self.progress_label.setStyleSheet("font-weight: bold; color: #2196F3;")
        self.progress_label.setVisible(False)
        progress_group.addWidget(self.progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet(
            "QProgressBar { "
            "border: 2px solid #ddd; "
            "border-radius: 5px; "
            "text-align: center; "
            "font-weight: bold; "
            "} "
            "QProgressBar::chunk { "
            "background-color: #2196F3; "
            "border-radius: 3px; "
            "}"
        )
        self.progress_bar.setFixedHeight(25)
        progress_group.addWidget(self.progress_bar)
        
        layout.addLayout(progress_group)

        # Add stretch to push everything to the top
        layout.addStretch()
        
        # Set default output folder
        self._set_default_output_folder()
        
        self.setLayout(layout)

    def connect_signals(self):
        self.browse_folder_btn.clicked.connect(self._browse_output_folder)
        self.archive_btn.clicked.connect(self._on_archive_project)

    def _browse_output_folder(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder", self.output_folder_edit.text() or os.path.expanduser("~")
        )
        if folder:
            self.output_folder_edit.setText(folder)
            self.emit_log(f"Output folder set to: {folder}")

    def _on_archive_project(self):
        output_folder = self.output_folder_edit.text().strip()
        if not self.validate_non_empty_field(output_folder, "output folder"):
            return
        if not os.path.isdir(output_folder):
            self.emit_log("Please select a valid output folder.")
            return

        project = QgsProject.instance()
        project_file = Path(project.fileName())
        if not project_file.exists():
            self.emit_log("No QGIS project is currently open.")
            return

        # Show warning about copying all files including DCIM folder
        warning_msg = (
            "This will copy ALL files and folders from the project directory to the output folder.\n\n"
            "This includes:\n"
            "• DCIM folder (which might be quite large)\n"
            "• All other project files and folders\n"
            "• PostgreSQL layers will be converted to Geopackage\n\n"
            "Do you want to continue?"
        )
        
        if not self.confirm_action("Copy All Project Files", warning_msg):
            return

        # Start progress
        self.emit_progress_started()
        self.progress_label.setVisible(True)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        self.archive_btn.setEnabled(False)

        project_name = os.path.splitext(os.path.basename(project_file))[0]
        export_qgs_filename = f"{project_name}_portable.qgs"
        export_path = Path(output_folder) / export_qgs_filename
        gpkg_path = Path(output_folder) / "data.gpkg"

        try:
            # Count total steps for progress calculation
            total_layers = len([layer for layer in project.mapLayers().values() 
                              if layer.type() == QgsVectorLayer.VectorLayer])
            project_dir = project_file.parent
            total_files = len([item for item in project_dir.iterdir() if item.name != project_file.name])
            
            total_steps = total_files + total_layers + 2  # +2 for project copy and final update
            current_step = 0
            
            # Switch to determinate progress
            self.progress_bar.setRange(0, total_steps)
            self.progress_label.setText("Copying project files...")

            # 1. Copy all files and folders from project directory to output folder (except the QGS file)
            original_qgs_name = project_file.name
            
            # Only copy if source and target directories are different
            if str(project_dir) != str(Path(output_folder)):
                self.emit_log(f"Copying files from project directory: {project_dir}")
                
                for item in project_dir.iterdir():
                    if item.name == original_qgs_name:
                        # Skip the original QGS file as we'll create the portable version
                        continue
                    
                    target_path = Path(output_folder) / item.name
                    
                    if item.is_file():
                        self.progress_label.setText(f"Copying file: {item.name}")
                        shutil.copy2(item, target_path)
                        self.emit_log(f"Copied file: {item.name}")
                    elif item.is_dir():
                        self.progress_label.setText(f"Copying folder: {item.name}")
                        if target_path.exists():
                            shutil.rmtree(target_path)
                        shutil.copytree(item, target_path)
                        self.emit_log(f"Copied folder: {item.name}")
                    
                    current_step += 1
                    self.progress_bar.setValue(current_step)
            else:
                self.emit_log("Source and target directories are the same, skipping file copy")
                current_step += total_files  # Skip file copy steps
                self.progress_bar.setValue(current_step)

            # 2. Copy the current project file to output folder
            self.progress_label.setText("Copying project file...")
            shutil.copy2(str(project_file), str(export_path))
            self.emit_log(f"Copied project file to: {export_path}")
            current_step += 1
            self.progress_bar.setValue(current_step)

            # 3. Convert all layers to a single geopackage
            self.progress_label.setText("Converting layers to geopackage...")
            new_layer_sources = {}
            postgresql_layers = []
            first_layer = True
            
            for layer_id, layer in project.mapLayers().items():
                if layer.type() == QgsVectorLayer.VectorLayer:
                    # Check if it's a PostgreSQL layer
                    provider_type = layer.providerType()
                    source = layer.source()
                    
                    if provider_type == "postgres" or "postgresql" in source.lower():
                        postgresql_layers.append(layer)
                        self.emit_log(f"Found PostgreSQL layer: {layer.name()}")
                    
                    # Export layer to geopackage
                    layer_name = layer.name().replace(' ', '_').replace('/', '_')
                    self.progress_label.setText(f"Converting layer: {layer.name()}")
                    
                    # Create write options
                    options = QgsVectorFileWriter.SaveVectorOptions()
                    options.driverName = "GPKG"
                    options.fileEncoding = "utf-8"
                    options.layerName = layer_name
                    
                    # For the first layer, create/overwrite the geopackage
                    # For subsequent layers, append to existing geopackage
                    if first_layer:
                        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
                        first_layer = False
                    else:
                        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer
                    
                    # Export layer
                    error, error_message = QgsVectorFileWriter.writeAsVectorFormat(
                        layer, 
                        str(gpkg_path),
                        options
                    )
                    
                    if error == QgsVectorFileWriter.NoError:
                        new_source = f"{gpkg_path}|layername={layer_name}"
                        new_layer_sources[layer_id] = new_source
                        self.emit_log(f"Exported {layer.name()} to geopackage")
                    else:
                        self.emit_log(f"Failed to export {layer.name()}: {error_message}")
                    
                    current_step += 1
                    self.progress_bar.setValue(current_step)

            # 4. Update the copied project file to point to geopackage
            self.progress_label.setText("Updating project file...")
            if new_layer_sources:
                self._update_project_sources(export_path, new_layer_sources, postgresql_layers)
                self.emit_log("Updated project file to use geopackage sources")
            
            current_step += 1
            self.progress_bar.setValue(current_step)

            self.progress_label.setText("Complete!")
            self.emit_log(f"✓ Successfully archived project '{project_name}' to {export_path}")
            self.project_archived.emit(str(export_path))
            
        except Exception as e:
            self.emit_log(f"Error creating archive: {str(e)}")
        finally:
            self.emit_progress_finished()
            self.progress_label.setVisible(False)
            self.progress_bar.setVisible(False)
            self.archive_btn.setEnabled(True)

    def _update_project_sources(self, qgs_path, new_sources, postgresql_layers):
        """Update the project file to use geopackage sources instead of PostgreSQL"""
        try:
            # Parse the QGS file (XML)
            tree = ET.parse(str(qgs_path))
            root = tree.getroot()
            
            # Find all maplayer elements
            maplayers = root.findall(".//maplayer")
            
            for maplayer in maplayers:
                layer_id = maplayer.get("id") or maplayer.findtext("id")
                
                if layer_id in new_sources:
                    # Update datasource
                    datasource_elem = maplayer.find("datasource")
                    if datasource_elem is not None:
                        datasource_elem.text = new_sources[layer_id]
                    
                    # Update provider to 'ogr' for geopackage
                    provider_elem = maplayer.find("provider")
                    if provider_elem is not None:
                        provider_elem.text = "ogr"
                    
                    self.emit_log(f"Updated layer {layer_id} source in project file")
            
            # Write the updated XML back to file
            tree.write(str(qgs_path), encoding='utf-8', xml_declaration=True)
            
        except Exception as e:
            self.emit_log(f"Error updating project file: {str(e)}")

    def _set_default_output_folder(self):
        documents = os.path.expanduser("~/Documents")
        self.output_folder_edit.setText(documents if os.path.isdir(documents) else os.getcwd())

    def get_output_folder(self):
        return self.output_folder_edit.text().strip()

    def set_output_folder(self, folder_path):
        if os.path.exists(folder_path) and os.path.isdir(folder_path):
            self.output_folder_edit.setText(folder_path)
            return True
        return False