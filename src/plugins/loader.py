"""Plugin loader - discovers and loads plugins from disk."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import yaml

from src.plugins.base import PluginBase


class PluginLoadError(Exception):
    """Raised when a plugin fails to load."""

    pass


class PluginLoader:
    """Discovers and loads plugins from a directory.

    Plugins are directories containing:
    - manifest.yaml: Plugin metadata and tool definitions
    - handler.py: Python module with Plugin class
    """

    def __init__(self, plugins_dir: Path) -> None:
        """Initialize the loader.

        Args:
            plugins_dir: Directory to scan for plugins.
        """
        self._plugins_dir = plugins_dir
        self._plugins: list[PluginBase] = []

    def register_plugin(self, plugin: PluginBase) -> None:
        """Register a plugin directly (for built-in plugins).

        Args:
            plugin: Plugin instance to register.
        """
        self._plugins.append(plugin)

    def get_all_plugins(self) -> list[PluginBase]:
        """Get all registered plugins.

        Returns:
            List of plugin instances.
        """
        return list(self._plugins)

    def discover_plugins(self) -> list[PluginBase]:
        """Discover and load plugins from the plugins directory.

        Returns:
            List of loaded plugin instances.
        """
        if not self._plugins_dir.exists():
            return self._plugins

        for item in self._plugins_dir.iterdir():
            if not item.is_dir():
                continue

            manifest_path = item / "manifest.yaml"
            handler_path = item / "handler.py"

            if not manifest_path.exists():
                continue

            try:
                plugin = self._load_plugin(item, manifest_path, handler_path)
                if plugin:
                    self._plugins.append(plugin)
            except Exception as e:
                # Log error but continue loading other plugins
                print(f"Failed to load plugin {item.name}: {e}", file=sys.stderr)

        return self._plugins

    # @todo: Mild SRP concern - this method handles both manifest loading and
    # dynamic module import. Consider extracting _import_plugin_module() if
    # manifest validation logic grows. Not urgent - method is ~40 lines and
    # easy to follow. (2024-11-27)
    def _load_plugin(
        self, plugin_dir: Path, manifest_path: Path, handler_path: Path
    ) -> PluginBase | None:
        """Load a single plugin.

        Args:
            plugin_dir: Plugin directory.
            manifest_path: Path to manifest.yaml.
            handler_path: Path to handler.py.

        Returns:
            Plugin instance or None if loading fails.

        Raises:
            PluginLoadError: If the plugin is invalid.
        """
        # Load manifest (for future validation)
        with open(manifest_path) as f:
            _manifest = yaml.safe_load(f)  # noqa: F841

        if not handler_path.exists():
            raise PluginLoadError(f"Missing handler.py in {plugin_dir}")

        # Dynamically import the handler module
        spec = importlib.util.spec_from_file_location(
            f"plugins.{plugin_dir.name}.handler", handler_path
        )
        if spec is None or spec.loader is None:
            raise PluginLoadError(f"Cannot load handler from {handler_path}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)

        # Get the Plugin class
        if not hasattr(module, "Plugin"):
            raise PluginLoadError(f"No Plugin class in {handler_path}")

        plugin_class = module.Plugin
        if not issubclass(plugin_class, PluginBase):
            raise PluginLoadError("Plugin class must inherit from PluginBase")

        return plugin_class()

    def reload_plugins(self) -> list[PluginBase]:
        """Reload all plugins.

        Returns:
            List of loaded plugin instances.
        """
        # Keep only manually registered plugins
        self._plugins = [p for p in self._plugins if not hasattr(p, "_from_disk")]
        return self.discover_plugins()
