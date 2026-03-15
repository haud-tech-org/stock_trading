"""
Environment type constants and utilities.

This module defines deployment environment types and provides utilities
for identifying and working with different deployment environments
(Azure, Google Cloud, Kubernetes, Docker, Local).
"""


class EnvironmentType:
    """
    Deployment environment type constants.
    
    Defines constants for different deployment environments and provides
    utilities for environment identification and human-readable naming.
    
    Usage:
        >>> from src.stockreports.alert.common.environment import EnvironmentType
        >>> env_type = EnvironmentType.AZURE
        >>> display_name = EnvironmentType.get_display_name(env_type)
        >>> print(display_name)  # Output: "Azure"
    """
    
    # Environment type constants
    AZURE = "AZURE"
    GCP = "GCP"
    KUBERNETES = "KUBERNETES"
    DOCKER = "DOCKER"
    LOCAL = "LOCAL"
    
    # Human-readable display names mapping
    DISPLAY_NAMES = {
        AZURE: "Azure",
        GCP: "Google Cloud",
        KUBERNETES: "Kubernetes",
        DOCKER: "Docker",
        LOCAL: "Local"
    }
    
    # Environment characteristics
    CLOUD_ENVIRONMENTS = {AZURE, GCP, KUBERNETES}
    CONTAINERIZED_ENVIRONMENTS = {KUBERNETES, DOCKER}
    PRODUCTION_ENVIRONMENTS = {AZURE, GCP, KUBERNETES}
    
    @classmethod
    def get_display_name(cls, environment_type: str) -> str:
        """
        Get human-readable display name for environment type.
        
        Args:
            environment_type: Environment type constant (e.g., EnvironmentType.AZURE)
            
        Returns:
            Human-readable display name
            
        Example:
            >>> EnvironmentType.get_display_name(EnvironmentType.AZURE)
            'Azure'
        """
        return cls.DISPLAY_NAMES.get(environment_type, "Unknown")
    
    @classmethod
    def all_types(cls) -> list:
        """
        Get list of all environment types.
        
        Returns:
            List of all environment type constants
            
        Example:
            >>> EnvironmentType.all_types()
            ['AZURE', 'GCP', 'KUBERNETES', 'DOCKER', 'LOCAL']
        """
        return [cls.AZURE, cls.GCP, cls.KUBERNETES, cls.DOCKER, cls.LOCAL]
    
    @classmethod
    def is_cloud_environment(cls, environment_type: str) -> bool:
        """
        Check if the environment is a cloud environment.
        
        Cloud environments are those hosted on cloud platforms
        (Azure, Google Cloud, Kubernetes).
        
        Args:
            environment_type: Environment type constant
            
        Returns:
            True if environment is cloud-based, False otherwise
            
        Example:
            >>> EnvironmentType.is_cloud_environment(EnvironmentType.AZURE)
            True
            >>> EnvironmentType.is_cloud_environment(EnvironmentType.LOCAL)
            False
        """
        return environment_type in cls.CLOUD_ENVIRONMENTS
    
    @classmethod
    def is_containerized(cls, environment_type: str) -> bool:
        """
        Check if the environment uses containerization.
        
        Containerized environments are those using Docker or Kubernetes.
        
        Args:
            environment_type: Environment type constant
            
        Returns:
            True if environment is containerized, False otherwise
            
        Example:
            >>> EnvironmentType.is_containerized(EnvironmentType.DOCKER)
            True
            >>> EnvironmentType.is_containerized(EnvironmentType.AZURE)
            False
        """
        return environment_type in cls.CONTAINERIZED_ENVIRONMENTS
    
    @classmethod
    def is_production(cls, environment_type: str) -> bool:
        """
        Check if the environment is considered production.
        
        Production environments are cloud-based deployments.
        
        Args:
            environment_type: Environment type constant
            
        Returns:
            True if environment is production, False otherwise
            
        Example:
            >>> EnvironmentType.is_production(EnvironmentType.GCP)
            True
            >>> EnvironmentType.is_production(EnvironmentType.LOCAL)
            False
        """
        return environment_type in cls.PRODUCTION_ENVIRONMENTS
    
    @classmethod
    def validate(cls, environment_type: str) -> bool:
        """
        Validate if the given environment type is valid.
        
        Args:
            environment_type: Environment type constant to validate
            
        Returns:
            True if valid, False otherwise
            
        Example:
            >>> EnvironmentType.validate(EnvironmentType.AZURE)
            True
            >>> EnvironmentType.validate("INVALID")
            False
        """
        return environment_type in cls.all_types()
