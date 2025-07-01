# PostgreSQL Template Manager

A QGIS plugin for managing PostgreSQL database templates. Create templates from existing databases without data and use them as blueprints for new databases.

## Features

- **Create templates**: Generate templates from existing databases (structure only, no data)
- **Create databases**: Create new databases based on existing templates
- **Manage templates**: List available templates and delete unused ones
- **Permission checking**: Automatic validation of PostgreSQL user privileges
- **QGIS integration**: Dockable sidebar interface within QGIS

## Requirements

- QGIS 3.0 or higher
- PostgreSQL user with `CREATEDB` privilege
- Network access to PostgreSQL server

## Installation

### Method 1: QGIS Plugin Repository

1. Open QGIS
2. Go to **Plugins** → **Manage and Install Plugins**
3. Search for "PostgreSQL Template Manager"
4. Click **Install Plugin**
5. Enable the plugin if not automatically enabled

### Method 2: Manual Installation (ZIP)

1. Download the plugin ZIP file from releases
2. Open QGIS
3. Go to **Plugins** → **Manage and Install Plugins**
4. Click **Install from ZIP**
5. Select the downloaded ZIP file
6. Click **Install Plugin**

### Method 3: Development Installation

1. Clone the repository:
```bash
git clone https://github.com/csgis/postgresql-template-manager.git
```

2. Copy to QGIS plugins directory:
```bash
# Linux
cp -r postgresql-template-manager ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/

# Windows
copy postgresql-template-manager %APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\

# macOS
cp -r postgresql-template-manager ~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/
```

3. Restart QGIS and enable the plugin

## Usage

### Opening the Plugin

1. In QGIS, go to **Database** → **PostgreSQL Template Manager**
2. Or click the plugin icon in the Database toolbar
3. The plugin opens as a dockable sidebar

### Plugin Interface

The plugin provides a tabbed interface with the following sections:

#### Connection Tab
- Configure PostgreSQL connection parameters
- Test database connectivity
- Connection status indicator

#### Templates Tab
- Create new templates from existing databases
- List all available templates
- Delete unused templates

#### Databases Tab
- Create new databases from templates
- List existing databases
- Refresh database lists

## Step-by-Step Guide

### 1. Configure Connection

1. Open the plugin sidebar
2. Go to **Connection** tab
3. Enter your PostgreSQL details:
   - Host (default: localhost)
   - Port (default: 5432)
   - Username
   - Password
4. Click **Test Connection**
5. Wait for connection confirmation

### 2. Create Template

1. Go to **Templates** tab
2. Click **Refresh** to load available databases
3. Select source database from dropdown
4. Enter template name
5. Click **Create Template**
6. Monitor progress in the log area

### 3. Create Database from Template

1. Go to **Databases** tab
2. Select template from dropdown
3. Enter new database name
4. Click **Create Database**
5. Monitor progress in the log area

### 4. Manage Templates

- Use **Refresh** button to update template lists
- Select template and click **Delete Selected** to remove
- View template details in the list

## What Happens During Template Creation?

1. **Structure copy**: Plugin creates a copy of the source database
2. **Template status**: Marks the new database as a template
3. **Data removal**: Empties all tables using TRUNCATE CASCADE
4. **Progress tracking**: Real-time feedback in the plugin interface
5. **Error handling**: Comprehensive error reporting and logging

## Permissions

Your PostgreSQL user needs at least:

```sql
ALTER USER your_username CREATEDB;
```

The plugin automatically checks permissions and provides helpful error messages if insufficient privileges are detected.

## SQL Commands Reference

For users who prefer direct SQL commands or want to understand what the plugin does behind the scenes, here are the equivalent PostgreSQL commands:

### Create Template from Existing Database
```sql
-- Create template database (structure + data)
CREATE DATABASE my_template WITH TEMPLATE my_source_db IS_TEMPLATE = true;

-- Connect to the template and remove all data
\c my_template

-- Get list of all user tables and truncate them
DO $ 
DECLARE
    r RECORD;
BEGIN
    FOR r IN (SELECT schemaname, tablename FROM pg_tables 
              WHERE schemaname NOT IN ('information_schema', 'pg_catalog', 'pg_toast'))
    LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(r.schemaname) || '.' || quote_ident(r.tablename) || ' CASCADE';
    END LOOP;
END $;
```

### Create Database from Template
```sql
-- Create new database from template
CREATE DATABASE my_db WITH TEMPLATE my_template;
```

### List Templates
```sql
-- Show all template databases
SELECT datname as template_name, 
       pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database 
WHERE datistemplate = true 
AND datname NOT IN ('template0', 'template1')
ORDER BY datname;
```

### List Regular Databases
```sql
-- Show all non-template databases
SELECT datname as database_name,
       pg_size_pretty(pg_database_size(datname)) as size
FROM pg_database 
WHERE datistemplate = false 
AND datname NOT IN ('postgres')
ORDER BY datname;
```

### Delete Template
```sql
-- First disable template status
UPDATE pg_database SET datistemplate = false WHERE datname = 'my_template';

-- Then drop the database
DROP DATABASE my_template;
```

### Check User Privileges
```sql
-- Check if user has CREATEDB privilege
SELECT usename, usecreatedb, usesuper 
FROM pg_user 
WHERE usename = 'your_username';

-- Check if user can connect to specific database
SELECT has_database_privilege('your_username', 'my_source_db', 'CONNECT');
```

## Example Workflow

1. **Open QGIS** and activate the PostgreSQL Template Manager plugin
2. **Configure connection** in the Connection tab
3. **Test connection** to ensure connectivity
4. **Create template**: 
   - Templates tab → Select "production_db" → Name: "prod_schema_template"
5. **Create databases**:
   - Databases tab → Select "prod_schema_template" → Name: "project_alpha"
   - Databases tab → Select "prod_schema_template" → Name: "project_beta"
6. **Manage**: Use refresh and delete functions as needed

## Plugin Features

### User Interface
- **Dockable sidebar**: Integrates seamlessly with QGIS workspace
- **Tabbed interface**: Organized workflow with clear separation
- **Progress indicators**: Real-time feedback during operations
- **Error logging**: Detailed error messages and troubleshooting

### Database Operations
- **Connection management**: Secure credential handling
- **Template creation**: Automated structure-only copying
- **Database creation**: Fast deployment from templates
- **Privilege validation**: Automatic permission checking

### Integration
- **QGIS logging**: All operations logged to QGIS message log
- **Settings persistence**: Connection parameters saved between sessions
- **Toolbar integration**: Quick access via Database menu and toolbar

## Technical Details

### Dependencies
- **psycopg2**: Database connectivity (included with QGIS)
- **PyQt5**: User interface (included with QGIS)
- **QGIS Core**: Plugin framework and logging

### Database Operations
- Uses direct psycopg2 connections for all database operations
- Implements proper transaction handling and error recovery
- Supports PostgreSQL 9.5+ and all modern versions

### Security
- Passwords are not stored persistently
- Uses PostgreSQL's native authentication mechanisms
- Input validation prevents SQL injection

## Troubleshooting

### Plugin Not Visible
- Check if plugin is enabled in Plugin Manager
- Restart QGIS after installation
- Verify plugin files are in correct directory

### Connection Issues
- Verify PostgreSQL server is running
- Check network connectivity and firewall settings
- Validate connection parameters
- Review QGIS message log for detailed errors

### Permission Errors
```sql
-- Grant required permissions
ALTER USER your_username CREATEDB;

-- For connection to specific databases
GRANT CONNECT ON DATABASE source_database TO your_username;
```

### Plugin Errors
- Check QGIS message log (**View** → **Panels** → **Log Messages**)
- Look for "PostgreSQL Template Manager" entries
- Report issues with log details

## Use Cases

### Development Workflows
- **Feature development**: Isolated database per feature branch
- **Testing environments**: Clean database state for each test
- **Developer onboarding**: Standard schema for new team members

### Production Management
- **Staging environments**: Production schema without sensitive data
- **Client deployment**: Consistent database structure for new clients
- **Schema versioning**: Template-based database version control

### GIS Projects
- **Spatial database templates**: PostGIS-enabled schema templates
- **Project standardization**: Consistent spatial database structure
- **Multi-client GIS**: Separate spatial databases per client

## Integration with QGIS Workflows

The plugin complements QGIS database workflows:

- **DB Manager**: Use alongside QGIS DB Manager for comprehensive database administration
- **PostGIS**: Perfect for creating PostGIS-enabled database templates
- **Data sources**: Quickly create databases for new QGIS projects
- **Project templates**: Combine with QGIS project templates for complete workflow

## Configuration

Plugin settings are automatically managed:
- Connection parameters saved in QGIS settings
- Interface preferences persist between sessions
- Logging integrated with QGIS message system

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/new-feature`)
3. Follow QGIS plugin development guidelines
4. Test with multiple QGIS versions
5. Submit pull request with clear description

## Plugin Development

### Testing
```bash
# Test the plugin manually by installing in QGIS
# Copy plugin files to QGIS plugins directory and restart QGIS
```

### Building
```bash
# Create plugin ZIP excluding cache files and development artifacts
zip -r postgresql_template_manager.zip postgresql_template_manager/ \
    -x "postgresql_template_manager/__pycache__/*" \
    -x "postgresql_template_manager/.git/*" \
    -x "postgresql_template_manager/.gitignore" \
    -x "postgresql_template_manager/*.pyc" \
    -x "postgresql_template_manager/.DS_Store" \
    -x "postgresql_template_manager/Thumbs.db"
```

## License

MIT License - see [https://opensource.org/licenses/MIT](https://opensource.org/licenses/MIT) for details.

## Support

- **GitHub Issues**: [Report bugs and request features](https://github.com/csgis/postgresql-template-manager/issues)
- **QGIS Hub**: [Plugin page and reviews](https://plugins.qgis.org/plugins/postgresql_template_manager/)
- **Documentation**: [Wiki and guides](https://github.com/csgis/postgresql-template-manager/wiki)

## Changelog

### Version 1.0.0
- Initial release
- Template creation and management
- Database creation from templates
- QGIS integration with dockable interface
- PostgreSQL permission validation

---

**Note**: This plugin is designed for QGIS users who work with PostgreSQL databases and need efficient template management capabilities integrated into their GIS workflow.