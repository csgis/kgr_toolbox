import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsMessageLog, Qgis
import tempfile
import os
import zipfile
import re
import shutil
from datetime import datetime


class DatabaseManager(QObject):
    """Handles all database operations using psycopg2."""
    
    # Signals
    operation_finished = pyqtSignal(bool, str)  # success, message
    progress_updated = pyqtSignal(str)  # progress message
    
    def __init__(self):
        super().__init__()
        self.connection_params = {}
        self.connection = None
    
    def log_message(self, message, level=Qgis.Info):
        """Log message to QGIS message log."""
        QgsMessageLog.logMessage(message, 'PostgreSQL Template Manager', level)
    
    def set_connection_params(self, host, port, database, username, password):
        """Set connection parameters."""
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': username,
            'password': password
        }
    
    def test_connection(self):
        """Test database connection."""
        try:
            self.progress_updated.emit("Testing connection...")
            
            conn = psycopg2.connect(**self.connection_params)
            conn.close()
            
            self.progress_updated.emit("Connection successful!")
            self.operation_finished.emit(True, "Connection successful!")
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Connection failed: {str(e)}"
            self.log_message(error_msg, Qgis.Critical)
            self.operation_finished.emit(False, error_msg)
            return False
    
    def get_databases(self):
        """Get list of non-template databases."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            query = """
                SELECT datname FROM pg_database 
                WHERE datistemplate = false 
                AND datname NOT IN ('postgres', 'template0', 'template1')
                ORDER BY datname;
            """
            
            cursor.execute(query)
            databases = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return databases
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting databases: {str(e)}", Qgis.Critical)
            return []
    
    def get_templates(self):
        """Get list of template databases."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            query = """
                SELECT datname FROM pg_database 
                WHERE datistemplate = true 
                AND datname NOT IN ('template0', 'template1')
                ORDER BY datname;
            """
            
            cursor.execute(query)
            templates = [row[0] for row in cursor.fetchall()]
            
            cursor.close()
            conn.close()
            
            return templates
            
        except psycopg2.Error as e:
            self.log_message(f"Error getting templates: {str(e)}", Qgis.Critical)
            return []
    
    def check_user_privileges(self):
        """Check user privileges."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            # Check if user is superuser
            cursor.execute(f"SELECT usesuper FROM pg_user WHERE usename = '{self.connection_params['user']}';")
            is_superuser = cursor.fetchone()[0] if cursor.rowcount > 0 else False
            
            # Check CREATEDB privilege
            cursor.execute(f"SELECT usecreatedb FROM pg_user WHERE usename = '{self.connection_params['user']}';")
            can_create_db = cursor.fetchone()[0] if cursor.rowcount > 0 else False
            
            cursor.close()
            conn.close()
            
            return {
                'is_superuser': is_superuser,
                'can_create_db': can_create_db
            }
            
        except psycopg2.Error as e:
            self.log_message(f"Error checking privileges: {str(e)}", Qgis.Critical)
            return {'is_superuser': False, 'can_create_db': False}
    
    def database_exists(self, db_name):
        """Check if database exists."""
        try:
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            cursor.execute("SELECT 1 FROM pg_database WHERE datname = %s;", (db_name,))
            exists = cursor.rowcount > 0
            
            cursor.close()
            conn.close()
            
            return exists
            
        except psycopg2.Error as e:
            self.log_message(f"Error checking database existence: {str(e)}", Qgis.Critical)
            return False
    
    def find_qgis_projects(self, database_name):
        """Find QGIS projects tables in all schemas of the specified database."""
        try:
            self.progress_updated.emit(f"Searching for QGIS projects in '{database_name}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            # Find all qgis_projects tables in all schemas
            query = """
                SELECT schemaname, tablename
                FROM pg_tables 
                WHERE tablename = 'qgis_projects'
                AND schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schemaname;
            """
            
            cursor.execute(query)
            tables = cursor.fetchall()
            
            projects = []
            for schema, table in tables:
                # Get projects from this table
                project_query = f"""
                    SELECT name, metadata 
                    FROM "{schema}"."{table}"
                    ORDER BY name;
                """
                
                try:
                    cursor.execute(project_query)
                    table_projects = cursor.fetchall()
                    
                    for name, metadata in table_projects:
                        projects.append({
                            'schema': schema,
                            'table': table,
                            'name': name,
                            'metadata': metadata
                        })
                        
                except psycopg2.Error as e:
                    self.log_message(f"Warning: Could not read projects from {schema}.{table}: {str(e)}", Qgis.Warning)
            
            cursor.close()
            conn.close()
            
            self.progress_updated.emit(f"Found {len(projects)} QGIS projects")
            return projects
            
        except psycopg2.Error as e:
            self.log_message(f"Error finding QGIS projects: {str(e)}", Qgis.Critical)
            return []
    
    def fix_qgis_project_layers(self, database_name, schema, table, project_name, new_params, create_backup=True):
        """Fix QGIS project layers with new connection parameters."""
        try:
            self.progress_updated.emit(f"Starting to fix project '{project_name}'...")
            
            # Step 1: Download project content
            content = self._download_project_content(database_name, schema, table, project_name)
            if not content:
                self.operation_finished.emit(False, "Failed to download project content")
                return
            
            # Step 2: Process the QGS file (will save both files for comparison)
            fixed_content = self._process_qgs_file(content, new_params, project_name, create_backup)
            if not fixed_content:
                self.operation_finished.emit(False, "Failed to process QGS file")
                return
            
            # Step 3: DISABLED - Upload fixed content back to database
            # Commenting out the upload for debugging purposes
            self.progress_updated.emit("SKIPPING UPLOAD - Debug mode enabled")
            self.progress_updated.emit("Both original and modified QGS files have been saved for comparison")
            
            # success = self._upload_project_content(database_name, schema, table, project_name, fixed_content)
            # if success:
            #     self.operation_finished.emit(True, f"Successfully fixed project '{project_name}'")
            # else:
            #     self.operation_finished.emit(False, "Failed to upload fixed project content")
            
            # Instead, just report success with debug info
            self.operation_finished.emit(True, f"Debug mode: Project '{project_name}' processed successfully. Files saved for comparison. Upload was SKIPPED.")
                
        except Exception as e:
            error_msg = f"Error fixing QGIS project: {str(e)}"
            self.log_message(error_msg, Qgis.Critical)
            self.operation_finished.emit(False, error_msg)
    
    def _download_project_content(self, database_name, schema, table, project_name):
        """Download project content from database."""
        try:
            self.progress_updated.emit(f"Downloading project content...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            query = f'SELECT content FROM "{schema}"."{table}" WHERE name = %s;'
            cursor.execute(query, (project_name,))
            
            result = cursor.fetchone()
            if not result:
                raise Exception(f"Project '{project_name}' not found")
            
            content = result[0]
            
            # Convert memoryview to bytes if necessary
            if isinstance(content, memoryview):
                content = content.tobytes()
            elif not isinstance(content, bytes):
                # Handle other types (like buffer objects)
                content = bytes(content)
            
            cursor.close()
            conn.close()
            
            self.progress_updated.emit(f"Downloaded {len(content)} bytes of project content")
            return content
            
        except psycopg2.Error as e:
            self.log_message(f"Error downloading project content: {str(e)}", Qgis.Critical)
            return None
    

    def _process_qgs_file(self, content, new_params, project_name, create_backup=True):
        """Process QGS file - unzip, modify, zip, and save both versions for comparison."""
        try:
            # Create temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Sanitize project name for filename (remove invalid characters)
                safe_project_name = re.sub(r'[<>:"/\\|?*]', '_', project_name)
                
                # Clean the content and preserve the prefix bytes
                clean_content, prefix_bytes = self._clean_and_preserve_zip_content(content)
                if not clean_content:
                    raise Exception("Invalid ZIP content - no ZIP magic bytes found")
                
                # Write cleaned content to temporary file
                qgz_path = os.path.join(temp_dir, f"{safe_project_name}.qgz")
                with open(qgz_path, 'wb') as f:
                    f.write(clean_content)
                
                self.progress_updated.emit("Extracting project file...")
                
                # Verify ZIP file is valid before extraction
                if not zipfile.is_zipfile(qgz_path):
                    raise Exception("Invalid ZIP file after cleaning")
                
                # Extract QGZ file
                extract_dir = os.path.join(temp_dir, "extracted")
                os.makedirs(extract_dir, exist_ok=True)
                
                with zipfile.ZipFile(qgz_path, 'r') as zip_ref:
                    zip_ref.extractall(extract_dir)
                
                # Find QGS and QLS file(s) (case-insensitive search for cross-platform compatibility)
                qgs_files = []
                qls_files = []
                for f in os.listdir(extract_dir):
                    if f.lower().endswith('.qgs'):
                        qgs_files.append(f)
                    if f.lower().endswith('.qls'):
                        qls_files.append(f)
                
                if not qgs_files:
                    raise Exception("No .qgs file found in project")
                
                qgs_path = os.path.join(extract_dir, qgs_files[0])
                
                # Create debug directory for saving files
                debug_locations = [
                    os.path.expanduser("~/qgis_debug_files"),
                    os.path.join(tempfile.gettempdir(), "qgis_debug_files"),
                    os.path.join(os.getcwd(), "qgis_debug_files")
                ]
                
                debug_dir = None
                for location in debug_locations:
                    try:
                        os.makedirs(location, exist_ok=True)
                        test_file = os.path.join(location, "test_write.tmp")
                        with open(test_file, 'w') as f:
                            f.write("test")
                        os.remove(test_file)
                        debug_dir = location
                        break
                    except (OSError, PermissionError):
                        continue
                
                if debug_dir:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    
                    # Save ORIGINAL QGS file (before modifications)
                    original_qgs_path = os.path.join(debug_dir, f"{safe_project_name}_ORIGINAL_{timestamp}.qgs")
                    shutil.copy2(qgs_path, original_qgs_path)
                    self.progress_updated.emit(f"Saved ORIGINAL QGS file: {original_qgs_path}")
                    
                    # Create backup if requested (using original content for authentic backup)
                    if create_backup:
                        self._create_backup_with_content(content, safe_project_name)
                    
                    # Modify QGS file
                    self.progress_updated.emit("Modifying datasource connections...")
                    modifications_made = self._modify_qgs_datasources(qgs_path, new_params)
                    
                    if not modifications_made:
                        self.progress_updated.emit("No datasource modifications were needed")
                    
                    # Save MODIFIED QGS file (after modifications)
                    modified_qgs_path = os.path.join(debug_dir, f"{safe_project_name}_MODIFIED_{timestamp}.qgs")
                    shutil.copy2(qgs_path, modified_qgs_path)
                    self.progress_updated.emit(f"Saved MODIFIED QGS file: {modified_qgs_path}")
                    
                    # Also save QLS files if present
                    for qls_file in qls_files:
                        qls_path = os.path.join(extract_dir, qls_file)
                        qls_debug_path = os.path.join(debug_dir, f"{safe_project_name}_{qls_file}_{timestamp}.qls")
                        shutil.copy2(qls_path, qls_debug_path)
                        self.progress_updated.emit(f"Saved QLS file: {qls_debug_path}")
                    
                    # Create comparison instructions file
                    diff_instructions_path = os.path.join(debug_dir, f"DIFF_INSTRUCTIONS_{safe_project_name}_{timestamp}.txt")
                    with open(diff_instructions_path, 'w') as f:
                        f.write(f"QGS Files Comparison Instructions\n")
                        f.write(f"====================================\n\n")
                        f.write(f"Project: {project_name}\n")
                        f.write(f"Timestamp: {timestamp}\n\n")
                        f.write(f"ORIGINAL file: {original_qgs_path}\n")
                        f.write(f"MODIFIED file: {modified_qgs_path}\n\n")
                        f.write(f"To compare using diff command:\n")
                        f.write(f"diff \"{original_qgs_path}\" \"{modified_qgs_path}\"\n\n")
                        f.write(f"To compare using git diff:\n")
                        f.write(f"git diff --no-index \"{original_qgs_path}\" \"{modified_qgs_path}\"\n\n")
                        f.write(f"Connection parameters used for modification:\n")
                        for key, value in new_params.items():
                            if value.strip():
                                f.write(f"  {key}: {value}\n")
                    
                    self.progress_updated.emit(f"Created diff instructions: {diff_instructions_path}")
                else:
                    self.log_message("No writable debug directory found for saving QGS files.", Qgis.Warning)

                # Create new QGZ file with only the files at the archive root (including .db, .qls, etc.)
                self.progress_updated.emit("Creating updated project file...")
                new_qgz_path = os.path.join(temp_dir, f"{safe_project_name}_fixed.qgz")
                
                with zipfile.ZipFile(new_qgz_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zip_ref:
                    for file in os.listdir(extract_dir):
                        file_path = os.path.join(extract_dir, file)
                        if os.path.isfile(file_path):
                            zip_ref.write(file_path, file)  # file is the name at root

                # Read fixed content
                with open(new_qgz_path, 'rb') as f:
                    fixed_zip_content = f.read()
                
                # Verify the new ZIP is valid
                if not zipfile.is_zipfile(new_qgz_path):
                    raise Exception("Created ZIP file is invalid")
                
                # DO NOT restore prefix_bytes! QGIS expects a standard ZIP starting with PK!
                final_content = fixed_zip_content
                
                return final_content
                
        except Exception as e:
            self.log_message(f"Error processing QGS file: {str(e)}", Qgis.Critical)
            return None
        
    def _clean_and_preserve_zip_content(self, content):
        """Remove extra bytes before ZIP magic and return clean ZIP content + prefix bytes."""
        if not content:
            return None, None
        
        # Ensure content is bytes
        if isinstance(content, memoryview):
            content = content.tobytes()
        elif not isinstance(content, bytes):
            content = bytes(content)
        
        # ZIP files start with 'PK' (0x504B)
        zip_magic = b'PK'
        
        # Find the first occurrence of ZIP magic bytes
        zip_start = content.find(zip_magic)
        
        if zip_start == -1:
            self.log_message("No ZIP magic bytes found in content", Qgis.Critical)
            return None, None
        
        # Extract prefix bytes (database metadata)
        prefix_bytes = content[:zip_start] if zip_start > 0 else None
        
        if zip_start > 0:
            self.progress_updated.emit(f"Found {zip_start} database header bytes (will be preserved)")
        
        # Return clean ZIP content and prefix bytes
        return content[zip_start:], prefix_bytes
    
    def _create_backup_with_content(self, content, project_name):
        """Create local backup with raw content."""
        try:
            # Convert memoryview to bytes if necessary
            if isinstance(content, memoryview):
                content = content.tobytes()
            elif not isinstance(content, bytes):
                content = bytes(content)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_locations = [
                os.path.expanduser("~/qgis_project_backups"),
                os.path.join(tempfile.gettempdir(), "qgis_project_backups"),
                os.path.join(os.getcwd(), "qgis_project_backups")
            ]
            
            backup_dir = None
            for location in backup_locations:
                try:
                    os.makedirs(location, exist_ok=True)
                    test_file = os.path.join(location, "test_write.tmp")
                    with open(test_file, 'w') as f:
                        f.write("test")
                    os.remove(test_file)
                    backup_dir = location
                    break
                except (OSError, PermissionError):
                    continue
            
            if not backup_dir:
                raise Exception("No writable backup directory found")
            
            # Save both raw and cleaned versions
            raw_backup_path = os.path.join(backup_dir, f"{project_name}_backup_raw_{timestamp}.qgz")
            clean_backup_path = os.path.join(backup_dir, f"{project_name}_backup_clean_{timestamp}.qgz")
            
            # Raw backup (original from database)
            with open(raw_backup_path, 'wb') as f:
                f.write(content)
            
            # Clean backup (ZIP-compatible)
            clean_content, _ = self._clean_and_preserve_zip_content(content)
            if clean_content:
                with open(clean_backup_path, 'wb') as f:
                    f.write(clean_content)
            
            self.progress_updated.emit(f"Backups created: {raw_backup_path}")
            
        except Exception as e:
            self.log_message(f"Warning: Could not create backup: {str(e)}", Qgis.Warning)
    
    def _modify_qgs_datasources(self, qgs_path, new_params):
        """Modify datasource connections in QGS file - manual parsing approach."""
        try:
            # Read QGS file
            with open(qgs_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            modifications_count = 0
            
            # Only process parameters that are actually provided and not empty
            params_to_change = {}
            for param_name, new_value in new_params.items():
                if new_value and new_value.strip():
                    params_to_change[param_name] = new_value.strip()
            
            if not params_to_change:
                self.progress_updated.emit("No parameters to change")
                return False
            
            self.progress_updated.emit(f"Will change these parameters: {list(params_to_change.keys())}")
            
            # Find all datasource tags and their positions
            datasource_pattern = r'<datasource>([^<]+)</datasource>'
            matches = list(re.finditer(datasource_pattern, content))
            
            # Process matches in reverse order to avoid position shifts
            for match in reversed(matches):
                full_match = match.group(0)
                datasource_content = match.group(1)
                start_pos = match.start()
                end_pos = match.end()
                
                # Parse the datasource content into key-value pairs
                original_params = self._parse_datasource_simple(datasource_content)
                new_params_dict = original_params.copy()
                datasource_changed = False
                
                # Apply only the requested changes
                if 'dbname' in params_to_change:
                    if 'dbname' in new_params_dict:
                        new_params_dict['dbname'] = params_to_change['dbname']
                        datasource_changed = True
                
                if 'host' in params_to_change:
                    if 'host' in new_params_dict:
                        new_params_dict['host'] = params_to_change['host']
                        datasource_changed = True
                
                if 'port' in params_to_change:
                    if 'port' in new_params_dict:
                        new_params_dict['port'] = params_to_change['port']
                        datasource_changed = True
                
                if 'user' in params_to_change:
                    if 'user' in new_params_dict:
                        new_params_dict['user'] = params_to_change['user']
                        datasource_changed = True
                
                if 'password' in params_to_change:
                    if 'password' in new_params_dict:
                        new_params_dict['password'] = params_to_change['password']
                        datasource_changed = True
                
                if 'schema' in params_to_change and 'table' in new_params_dict:
                    # Only change schema part of table parameter
                    table_value = new_params_dict['table']
                    if '.' in table_value:
                        # Handle quoted schema: "old_schema"."table" -> "new_schema"."table"
                        if table_value.startswith('"'):
                            parts = table_value.split('"."', 1)
                            if len(parts) == 2:
                                new_params_dict['table'] = f'"{params_to_change["schema"]}"."{parts[1]}'
                                datasource_changed = True
                        else:
                            # Handle unquoted schema: old_schema.table -> new_schema.table
                            parts = table_value.split('.', 1)
                            if len(parts) == 2:
                                new_params_dict['table'] = f'{params_to_change["schema"]}.{parts[1]}'
                                datasource_changed = True
                
                if datasource_changed:
                    modifications_count += 1
                    
                    # Rebuild the datasource string preserving original formatting
                    new_datasource_content = self._rebuild_datasource_simple(datasource_content, new_params_dict)
                    new_full_datasource = f'<datasource>{new_datasource_content}</datasource>'
                    
                    # Replace this specific datasource in the content
                    content = content[:start_pos] + new_full_datasource + content[end_pos:]
                    
                    # Extract table name for logging
                    table_name = original_params.get('table', 'unknown')
                    self.progress_updated.emit(f"Updated datasource {modifications_count}: {table_name}")
                    
                    # Debug output
                    self.progress_updated.emit(f"  Original: {datasource_content[:80]}...")
                    self.progress_updated.emit(f"  Modified: {new_datasource_content[:80]}...")
            
            # Write modified content back only if changes were made
            if content != original_content:
                with open(qgs_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.progress_updated.emit(f"Successfully updated {modifications_count} datasource connections")
                return True
            else:
                self.progress_updated.emit("No datasource connections were changed")
                return False
            
        except Exception as e:
            raise Exception(f"Error modifying QGS datasources: {str(e)}")
    
    def _parse_datasource_simple(self, datasource_content):
        """Simple parser to extract key=value pairs from datasource string."""
        params = {}
        
        # Use regex to find all key=value pairs, handling quoted and unquoted values
        patterns = [
            r"(\w+)='([^']*)'",     # key='value'
            r'(\w+)="([^"]*)"',     # key="value"  
            r"(\w+)=([^\s'\"]+)"    # key=value (no quotes, no spaces)
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, datasource_content)
            for key, value in matches:
                if key not in params:  # Don't overwrite already found values
                    params[key] = value
        
        return params
    
    def _rebuild_datasource_simple(self, original_datasource, new_params):
        """Rebuild datasource string by replacing only changed parameters."""
        result = original_datasource
        
        # Replace each parameter individually using precise regex
        for key, new_value in new_params.items():
            # Try different quote formats
            patterns_replacements = [
                (rf"{re.escape(key)}='[^']*'", f"{key}='{new_value}'"),
                (rf'{re.escape(key)}="[^"]*"', f'{key}="{new_value}"'),
                (rf"{re.escape(key)}=[^\s'\"]+", f"{key}={new_value}")
            ]
            
            for pattern, replacement in patterns_replacements:
                new_result = re.sub(pattern, replacement, result)
                if new_result != result:
                    result = new_result
                    break  # Found and replaced, move to next parameter
        
        return result
    
    def _upload_project_content(self, database_name, schema, table, project_name, content):
        """Upload fixed project content back to database."""
        try:
            self.progress_updated.emit("Uploading fixed project...")
            
            # Ensure content is bytes
            if not isinstance(content, bytes):
                if isinstance(content, memoryview):
                    content = content.tobytes()
                else:
                    content = bytes(content)
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = database_name
            
            conn = psycopg2.connect(**conn_params)
            cursor = conn.cursor()
            
            query = f'UPDATE "{schema}"."{table}" SET content = %s WHERE name = %s;'
            cursor.execute(query, (content, project_name))
            
            if cursor.rowcount == 0:
                raise Exception(f"No project named '{project_name}' was found to update")
            
            conn.commit()
            cursor.close()
            conn.close()
            
            self.progress_updated.emit(f"Project uploaded successfully ({len(content)} bytes)")
            return True
            
        except psycopg2.Error as e:
            self.log_message(f"Error uploading project content: {str(e)}", Qgis.Critical)
            return False
    
    def create_template(self, source_db, template_name):
        """Create a template from source database."""
        try:
            self.progress_updated.emit(f"Creating template '{template_name}' from '{source_db}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Drop existing template if it exists
            if self.database_exists(template_name):
                self.progress_updated.emit(f"Dropping existing template '{template_name}'...")
                cursor.execute(f'DROP DATABASE "{template_name}";')
            
            # Create template database
            cursor.execute(f'CREATE DATABASE "{template_name}" WITH TEMPLATE "{source_db}" IS_TEMPLATE = true;')
            
            self.progress_updated.emit("Removing data from template...")
            
            # Connect to template database to remove data
            cursor.close()
            conn.close()
            
            template_conn_params = self.connection_params.copy()
            template_conn_params['database'] = template_name
            
            template_conn = psycopg2.connect(**template_conn_params)
            template_conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            template_cursor = template_conn.cursor()
            
            # Get all user tables
            template_cursor.execute("""
                SELECT schemaname, tablename 
                FROM pg_tables 
                WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
                ORDER BY schemaname, tablename;
            """)
            
            tables = template_cursor.fetchall()
            
            # Truncate all tables
            for schema, table in tables:
                try:
                    template_cursor.execute(f'TRUNCATE TABLE "{schema}"."{table}" CASCADE;')
                    self.progress_updated.emit(f"Cleared data from {schema}.{table}")
                except psycopg2.Error as e:
                    self.log_message(f"Warning: Could not truncate {schema}.{table}: {str(e)}", Qgis.Warning)
            
            template_cursor.close()
            template_conn.close()
            
            success_msg = f"Template '{template_name}' created successfully!"
            self.progress_updated.emit(success_msg)
            self.operation_finished.emit(True, success_msg)
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Error creating template: {str(e)}"
            self.log_message(error_msg, Qgis.Critical)
            self.operation_finished.emit(False, error_msg)
            return False
    
    def create_database_from_template(self, template_name, new_db_name):
        """Create a new database from template."""
        try:
            self.progress_updated.emit(f"Creating database '{new_db_name}' from template '{template_name}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Drop existing database if it exists
            if self.database_exists(new_db_name):
                self.progress_updated.emit(f"Dropping existing database '{new_db_name}'...")
                cursor.execute(f'DROP DATABASE "{new_db_name}";')
            
            # Create database from template
            cursor.execute(f'CREATE DATABASE "{new_db_name}" WITH TEMPLATE "{template_name}";')
            
            cursor.close()
            conn.close()
            
            success_msg = f"Database '{new_db_name}' created successfully from template '{template_name}'!"
            self.progress_updated.emit(success_msg)
            self.operation_finished.emit(True, success_msg)
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Error creating database: {str(e)}"
            self.log_message(error_msg, Qgis.Critical)
            self.operation_finished.emit(False, error_msg)
            return False
    
    def delete_template(self, template_name):
        """Delete a template."""
        try:
            self.progress_updated.emit(f"Deleting template '{template_name}'...")
            
            conn_params = self.connection_params.copy()
            conn_params['database'] = 'postgres'
            
            conn = psycopg2.connect(**conn_params)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()
            
            # Deactivate template status
            cursor.execute(f"UPDATE pg_database SET datistemplate = false WHERE datname = '{template_name}';")
            
            # Drop database
            cursor.execute(f'DROP DATABASE "{template_name}";')
            
            cursor.close()
            conn.close()
            
            success_msg = f"Template '{template_name}' deleted successfully!"
            self.progress_updated.emit(success_msg)
            self.operation_finished.emit(True, success_msg)
            return True
            
        except psycopg2.Error as e:
            error_msg = f"Error deleting template: {str(e)}"
            self.log_message(error_msg, Qgis.Critical)
            self.operation_finished.emit(False, error_msg)
            return False