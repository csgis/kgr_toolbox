import os
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QMessageBox
from qgis.core import QgsApplication
from .database_manager import DatabaseManager
from .dialog import PostgreSQLTemplateManagerDialog


class KgrToolbox:
    """Main plugin class."""

    def __init__(self, iface):
        """Constructor.
        
        Args:
            iface: An interface instance that will be passed to this class
                which provides the hook by which you can manipulate the QGIS
                application at run time.
        """
        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        
        # Initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'PostgreSQLTemplateManager_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&PostgreSQL Template Manager')
        self.toolbar = self.iface.addToolBar(u'PostgreSQL Template Manager')
        self.toolbar.setObjectName(u'PostgreSQL Template Manager')
        
        # Initialize dialog
        self.dialog = None
        self.db_manager = DatabaseManager()

    def tr(self, message):
        """Get the translation for a string using Qt translation API."""
        return QCoreApplication.translate('PostgreSQLTemplateManager', message)

    def add_action(self, icon_path, text, callback, enabled_flag=True,
                   add_to_menu=True, add_to_toolbar=True, status_tip=None,
                   whats_this=None, parent=None):
        """Add a toolbar icon to the toolbar."""
        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToDatabaseMenu(self.menu, action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        icon_path = os.path.join(self.plugin_dir, 'icon.png')
        self.add_action(
            icon_path,
            text=self.tr(u'PostgreSQL Template Manager'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def unload(self):
        """Remove the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginDatabaseMenu(
                self.tr(u'&PostgreSQL Template Manager'),
                action)
            self.iface.removeToolBarIcon(action)

        # Remove the toolbar
        del self.toolbar

        # Close dialog if open
        if self.dialog:
            self.dialog.close()

    def run(self):
        """Run method that performs all the real work."""
        if not self.dialog:
            self.dialog = PostgreSQLTemplateManagerDialog(self.db_manager, self.iface.mainWindow())
        
        # Show the dialog as a dock widget
        self.iface.addDockWidget(self.dialog.dock_area, self.dialog)
        self.dialog.show()