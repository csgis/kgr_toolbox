def classFactory(iface):
    """Load KgrToolbox class from file kgr_toolbox.
    
    Args:
        iface: A QGIS interface instance.
    """
    from .kgr_toolbox import KgrToolbox
    return KgrToolbox(iface)