"""
Archive Project tab for PostgreSQL Template Manager.
Custom portable QGIS project exporter (no libqfieldsync).
"""

import os
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path
from PIL import Image, ImageOps
from qgis.PyQt.QtCore import pyqtSignal
from qgis.PyQt.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QLabel, QFileDialog, QProgressBar, QMessageBox, QCheckBox, QSpinBox
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

        # Title and help button section
        title_layout = QHBoxLayout()
        title_label = QLabel("Portable Project Archiver")
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

        # Image resize options section
        image_group = QVBoxLayout()
        image_group.setSpacing(8)
        
        # Resize images checkbox
        self.resize_images_checkbox = QCheckBox("Resize images")
        self.resize_images_checkbox.setStyleSheet("font-weight: bold;")
        self.resize_images_checkbox.toggled.connect(self._on_resize_checkbox_toggled)
        image_group.addWidget(self.resize_images_checkbox)
        
        # Pixel size input
        pixel_layout = QHBoxLayout()
        pixel_layout.setSpacing(10)
        self.pixel_label = QLabel("Pixel of long side:")
        self.pixel_label.setEnabled(False)
        self.pixel_spinbox = QSpinBox()
        self.pixel_spinbox.setRange(100, 10000)
        self.pixel_spinbox.setValue(300)
        self.pixel_spinbox.setSuffix(" px")
        self.pixel_spinbox.setEnabled(False)
        pixel_layout.addWidget(self.pixel_label)
        pixel_layout.addWidget(self.pixel_spinbox)
        pixel_layout.addStretch()
        image_group.addLayout(pixel_layout)
        
        # Warning label
        self.resize_warning_label = QLabel("⚠️ Resizing many images can take considerable time")
        self.resize_warning_label.setStyleSheet("color: #FF9800; font-size: 11px; font-style: italic;")
        self.resize_warning_label.setVisible(False)
        image_group.addWidget(self.resize_warning_label)
        
        layout.addLayout(image_group)

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

    def _on_resize_checkbox_toggled(self, checked):
        """Handle resize checkbox toggle"""
        self.pixel_label.setEnabled(checked)
        self.pixel_spinbox.setEnabled(checked)
        self.resize_warning_label.setVisible(checked)

    def _show_help_popup(self):
        """Show help information in a popup dialog."""
        help_text = (
            "<h3>Portable Project Archiver</h3>"
            "<p>Creates a completely self-contained, portable version of your current QGIS project.</p>"
            "<h4>What happens during archiving:</h4>"
            "<ul>"
            "<li><b>PostgreSQL layers →</b> Converted to a single 'data.gpkg' GeoPackage file</li>"
            "<li><b>All project files →</b> Copied to output folder (including DCIM, photos, etc.)</li>"
            "<li><b>Project file →</b> Updated to reference local GeoPackage instead of database</li>"
            "<li><b>Folder structure →</b> Preserved exactly as in original project</li>"
            "</ul>"
            "<h4>Image Resizing (Optional):</h4>"
            "<ul>"
            "<li><b>Resize images →</b> If enabled, resizes all images in DCIM folders</li>"
            "<li><b>Long side limit →</b> Images are resized only if their long side exceeds the specified pixel limit</li>"
            "<li><b>Supported formats →</b> JPEG, PNG, TIFF, BMP, and other common image formats</li>"
            "<li><b>Quality preserved →</b> JPEG quality is maintained at 95% during resizing</li>"
            "</ul>"
            "<h4>Result:</h4>"
            "<p>A <b>'{project_name}_portable.qgs'</b> file that can be opened on any computer without needing PostgreSQL access.</p>"
            "<h4>⚠️ Important notes:</h4>"
            "<ul>"
            "<li><b>Large files:</b> DCIM folders and media files will be copied (may take time)</li>"
            "<li><b>Image resizing:</b> Processing many high-resolution images can take significant time</li>"
            "<li><b>Database snapshots:</b> Data reflects the current state at export time</li>"
            "<li><b>No live sync:</b> Archived data won't update from the original database</li>"
            "</ul>"
        )
        
        msg = QMessageBox(self)
        msg.setWindowTitle("Help - Portable Project Archiver")
        msg.setTextFormat(1)  # Rich text format
        msg.setText(help_text)
        msg.setIcon(QMessageBox.Information)
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

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

    def _resize_images_in_folder(self, folder_path, max_long_side):
        """Resize all images in a folder if their long side exceeds max_long_side"""
        supported_formats = ('.jpg', '.jpeg', '.png', '.tiff', '.tif', '.bmp', '.webp')
        resized_count = 0
        
        try:
            image_files = []
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    if file.lower().endswith(supported_formats):
                        image_files.append(os.path.join(root, file))
            
            if not image_files:
                return 0
                
            self.emit_log(f"Found {len(image_files)} images to potentially resize in {folder_path}")
            
            for i, image_path in enumerate(image_files):
                try:
                    # Update progress
                    self.progress_label.setText(f"Resizing image {i+1}/{len(image_files)}: {os.path.basename(image_path)}")
                    
                    with Image.open(image_path) as img:
                        # Apply EXIF orientation to ensure correct rotation
                        img = ImageOps.exif_transpose(img)
                        
                        # Get original dimensions
                        width, height = img.size
                        long_side = max(width, height)
                        
                        # Only resize if long side exceeds the limit
                        if long_side > max_long_side:
                            # Calculate new dimensions maintaining aspect ratio
                            if width > height:
                                new_width = max_long_side
                                new_height = int(height * max_long_side / width)
                            else:
                                new_height = max_long_side
                                new_width = int(width * max_long_side / height)
                            
                            # Resize the image
                            resized_img = img.resize((new_width, new_height), Image.LANCZOS)
                            
                            # Save with appropriate quality settings
                            if image_path.lower().endswith(('.jpg', '.jpeg')):
                                resized_img.save(image_path, 'JPEG', quality=95, optimize=True)
                            else:
                                resized_img.save(image_path, optimize=True)
                            
                            resized_count += 1
                            self.emit_log(f"Resized {os.path.basename(image_path)} from {width}x{height} to {new_width}x{new_height}")
                        else:
                            # Even if not resizing, save with correct orientation if it's a JPEG
                            if image_path.lower().endswith(('.jpg', '.jpeg')):
                                img.save(image_path, 'JPEG', quality=95, optimize=True)
                            else:
                                img.save(image_path, optimize=True)
                
                except Exception as e:
                    self.emit_log(f"Could not resize {os.path.basename(image_path)}: {str(e)}")
                    continue
            
            return resized_count
            
        except Exception as e:
            self.emit_log(f"Error during image resizing: {str(e)}")
            return 0

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

        # Build warning message
        warning_parts = [
            "This will copy ALL files and folders from the project directory to the output folder.",
            "",
            "This includes:",
            "• DCIM folder (which might be quite large)",
            "• All other project files and folders",
            "• PostgreSQL layers will be converted to Geopackage"
        ]
        
        # Add image resizing warning if enabled
        if self.resize_images_checkbox.isChecked():
            max_pixels = self.pixel_spinbox.value()
            warning_parts.extend([
                "",
                f"• Images will be resized to {max_pixels}px on the long side",
                "• This may take considerable time with many images"
            ])
        
        warning_parts.extend([
            "",
            "Do you want to continue?"
        ])
        
        warning_msg = "\n".join(warning_parts)
        
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
            dcim_folders = []  # Track DCIM folders for potential resizing
            
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
                        
                        # Track DCIM folders for potential resizing
                        if item.name.upper() == "DCIM":
                            dcim_folders.append(target_path)
                    
                    current_step += 1
                    self.progress_bar.setValue(current_step)
            else:
                self.emit_log("Source and target directories are the same, skipping file copy")
                # Still need to find DCIM folders in the current directory
                for item in project_dir.iterdir():
                    if item.is_dir() and item.name.upper() == "DCIM":
                        dcim_folders.append(item)
                current_step += total_files  # Skip file copy steps
                self.progress_bar.setValue(current_step)

            # 2. Resize images in DCIM folders if requested
            if self.resize_images_checkbox.isChecked() and dcim_folders:
                max_pixels = self.pixel_spinbox.value()
                self.emit_log(f"Resizing images in DCIM folders to {max_pixels}px long side...")
                
                total_resized = 0
                for dcim_folder in dcim_folders:
                    self.progress_label.setText(f"Processing images in {dcim_folder.name}...")
                    resized_count = self._resize_images_in_folder(str(dcim_folder), max_pixels)
                    total_resized += resized_count
                    self.emit_log(f"Resized {resized_count} images in {dcim_folder}")
                
                self.emit_log(f"Total images resized: {total_resized}")

            # 3. Copy the current project file to output folder
            self.progress_label.setText("Copying project file...")
            shutil.copy2(str(project_file), str(export_path))
            self.emit_log(f"Copied project file to: {export_path}")
            current_step += 1
            self.progress_bar.setValue(current_step)

            # 4. Convert all layers to a single geopackage
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

            # 5. Update the copied project file to point to geopackage
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