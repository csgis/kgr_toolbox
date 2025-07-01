def classFactory(iface):
    """Load PostgreSQLTemplateManager class from file postgresql_template_manager.
    
    Args:
        iface: A QGIS interface instance.
    """
    from .postgresql_template_manager import PostgreSQLTemplateManager
    return PostgreSQLTemplateManager(iface)