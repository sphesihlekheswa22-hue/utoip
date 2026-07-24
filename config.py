"""Compatibility shim — prefer uitop.config."""
from uitop.config import Config, DevelopmentConfig, ProductionConfig, TestingConfig, config_by_name

__all__ = [
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "ProductionConfig",
    "config_by_name",
]
