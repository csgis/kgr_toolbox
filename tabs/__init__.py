"""
KGR Toolbox Tabs Module
"""
from .connection_tab import ConnectionTab
from .templates_tab import TemplatesTab
from .databases_tab import DatabasesTab
from .truncate_tab import TruncateTablesTab
from .qgis_projects_tab import QGISProjectsTab
from .archive_project_tab import ArchiveProjectTab
from .clean_qgs_tab import CleanQGSTab

__all__ = ['ConnectionTab', 'TemplatesTab', 'DatabasesTab', 'TruncateTablesTab', 'QGISProjectsTab', 'ArchiveProjectTab', 'CleanQGSTab']