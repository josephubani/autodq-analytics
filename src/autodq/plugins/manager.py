from collections import defaultdict

from autodq.plugins.types import PluginType


class PluginManager:
    """
    Central registry for AutoDQ plugins.
    """

    def __init__(self):
        self._plugins = defaultdict(list)

    def register(self, plugin_type: PluginType, plugin) -> None:
        """
        Register a plugin under a plugin type.
        """
        self._plugins[plugin_type].append(plugin)

    def get_plugins(self, plugin_type: PluginType) -> list:
        """
        Get all plugins registered under a plugin type.
        """
        return self._plugins.get(plugin_type, [])

    def clear(self) -> None:
        """
        Clear all registered plugins.
        """
        self._plugins.clear()