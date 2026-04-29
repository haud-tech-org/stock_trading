"""
Executor Configuration Service Exceptions

Defines custom exceptions for the Executor Configuration Service.
"""

class ExecutorConfigurationError(Exception):
    """Base exception for executor configuration errors."""
    pass

class ConfigurationNotFoundError(ExecutorConfigurationError):
    """Raised when a configuration is not found for the given parameters."""
    pass

class ConfigurationValidationError(ExecutorConfigurationError):
    """Raised when configuration validation fails."""
    pass

class ConfigurationFileError(ExecutorConfigurationError):
    """Raised when there is an error loading the configuration file."""
    pass
