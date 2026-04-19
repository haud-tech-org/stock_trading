"""
Executor Configuration Service Exceptions

Defines custom exceptions for the Executor Configuration Service.
"""

class ExecutorConfigurationError(Exception):
    """Base exception for executor configuration errors."""
    pass

class ExecutorConfigurationNotFoundError(ExecutorConfigurationError):
    """Raised when a configuration is not found for the given parameters."""
    pass

class ExecutorConfigurationValidationError(ExecutorConfigurationError):
    """Raised when configuration validation fails."""
    pass

class ExecutorConfigurationFileError(ExecutorConfigurationError):
    """Raised when there is an error loading the configuration file."""
    pass
