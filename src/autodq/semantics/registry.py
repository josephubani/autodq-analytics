from autodq.plugins.manager import PluginManager
from autodq.plugins.types import PluginType
from autodq.semantics.detectors.identifier import IdentifierDetector
from autodq.semantics.detectors.datetime import DateTimeDetector
from autodq.semantics.detectors.numeric import (
    ContinuousNumericDetector,
    DiscreteNumericDetector,
)
from autodq.semantics.detectors.categorical import CategoricalDetector


def get_default_semantic_plugin_manager() -> PluginManager:
    manager = PluginManager()

    manager.register(PluginType.SEMANTIC_DETECTOR, IdentifierDetector())
    manager.register(PluginType.SEMANTIC_DETECTOR, DateTimeDetector())
    manager.register(PluginType.SEMANTIC_DETECTOR, ContinuousNumericDetector())
    manager.register(PluginType.SEMANTIC_DETECTOR, DiscreteNumericDetector())
    manager.register(PluginType.SEMANTIC_DETECTOR, CategoricalDetector())

    return manager


def get_default_detectors():
    """
    Backward-compatible helper.
    """
    manager = get_default_semantic_plugin_manager()
    return manager.get_plugins(PluginType.SEMANTIC_DETECTOR)