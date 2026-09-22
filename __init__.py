def classFactory(iface):
    from .plugin import ChangeDetectorPlugin
    return ChangeDetectorPlugin(iface)