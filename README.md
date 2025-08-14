# <img src="icon.png" height="25"> KGR Toolbox

A QGIS plugin for managing PostgreSQL database templates and creating portable project archives.

## Features

### PostgreSQL Template Management
- **Create Templates**: Generate database templates from existing PostgreSQL databases without data
- **Deploy Templates**: Create new databases from existing templates
- **Schema Preservation**: Maintain all database structure, constraints, and relationships

### Portable Project Archives
- **PostgreSQL to Geopackage**: Convert all PostgreSQL layers to a single portable geopackage
- **Complete Project Export**: Copy all project files including DCIM folders and media and updates source references

### Qgis Projects
- **Fix QGIS Project Layers**: Search and update database connection configuration in layers.
- **Clean QGS Files**: Remove username and password in case they have been saved within the project file
- 
### PostgreSQL Database
- **Truncate Tables**: Truncate tables, to have a fresh start with duplicated databases


## Installation

### From QGIS Plugin Repository
1. Open QGIS
2. Go to `Plugins` → `Manage and Install Plugins`
3. Search for "KGR Toolbox"
4. Click `Install Plugin`

### Manual Installation
1. Download the latest release from [GitHub Releases](https://github.com/csgis/postgresql-template-manager/releases)
2. Go to `Plugins` → `Manage and Install Plugins`
3. Upload the zip

## Usage


#### Most of the actions need a database connection. Use a highly priviliged user to work with templates and databases.
1. Open the KGR Toolbox plugin
2. Go to the **Database Connection** tab
3. Enter your PostgreSQL connection details
4. Click **Test Connection**

For all other actions click the help button in the upper right corner of each tab.


## Requirements

- QGIS 3.0 or higher
- PostgreSQL database with appropriate permissions
- Python 3.6+ (included with QGIS)


## Troubleshooting

### Common Issues

**Connection Failed**
- Verify PostgreSQL server is running
- Check host, port, and credentials
- Ensure user has appropriate permissions

**Template Creation Failed**
- Ensure user has CREATEDB privileges
- Check database name doesn't already exist
- Verify sufficient disk space

**Archive Export Failed**
- Check write permissions in output folder
- Ensure sufficient disk space
- Verify QGIS project is saved

### Getting Help
- Check the [Issues](https://github.com/csgis/kgr_toolbox/issues) page
- Create a new issue with detailed description
- Include QGIS version, PostgreSQL version, and error messages

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](https://opensource.org/license/mit) file for details.
