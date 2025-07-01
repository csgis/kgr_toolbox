import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from qgis.PyQt.QtCore import QObject, pyqtSignal
from qgis.core import QgsMessageLog, Qgis


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