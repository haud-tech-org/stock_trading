"""
Unit tests for environment type constants and functionality.
"""

import pytest
from src.stockreports.alert.common.environment import EnvironmentType


class TestEnvironmentType:
    """Test cases for EnvironmentType class."""
    
    def test_constants_defined(self):
        """Test that all environment type constants are defined."""
        assert EnvironmentType.AZURE == "AZURE"
        assert EnvironmentType.GCP == "GCP"
        assert EnvironmentType.KUBERNETES == "KUBERNETES"
        assert EnvironmentType.DOCKER == "DOCKER"
        assert EnvironmentType.LOCAL == "LOCAL"
    
    def test_get_display_name(self):
        """Test display name retrieval for environment types."""
        assert EnvironmentType.get_display_name(EnvironmentType.AZURE) == "Azure"
        assert EnvironmentType.get_display_name(EnvironmentType.GCP) == "Google Cloud"
        assert EnvironmentType.get_display_name(EnvironmentType.KUBERNETES) == "Kubernetes"
        assert EnvironmentType.get_display_name(EnvironmentType.DOCKER) == "Docker"
        assert EnvironmentType.get_display_name(EnvironmentType.LOCAL) == "Local"
    
    def test_get_display_name_invalid(self):
        """Test display name for invalid environment type."""
        assert EnvironmentType.get_display_name("INVALID") == "Unknown"
    
    def test_all_types(self):
        """Test retrieval of all environment types."""
        all_types = EnvironmentType.all_types()
        assert len(all_types) == 5
        assert EnvironmentType.AZURE in all_types
        assert EnvironmentType.GCP in all_types
        assert EnvironmentType.KUBERNETES in all_types
        assert EnvironmentType.DOCKER in all_types
        assert EnvironmentType.LOCAL in all_types
    
    def test_is_cloud_environment(self):
        """Test cloud environment detection."""
        assert EnvironmentType.is_cloud_environment(EnvironmentType.AZURE) is True
        assert EnvironmentType.is_cloud_environment(EnvironmentType.GCP) is True
        assert EnvironmentType.is_cloud_environment(EnvironmentType.KUBERNETES) is True
        assert EnvironmentType.is_cloud_environment(EnvironmentType.DOCKER) is False
        assert EnvironmentType.is_cloud_environment(EnvironmentType.LOCAL) is False
    
    def test_is_containerized(self):
        """Test containerized environment detection."""
        assert EnvironmentType.is_containerized(EnvironmentType.DOCKER) is True
        assert EnvironmentType.is_containerized(EnvironmentType.KUBERNETES) is True
        assert EnvironmentType.is_containerized(EnvironmentType.AZURE) is False
        assert EnvironmentType.is_containerized(EnvironmentType.GCP) is False
        assert EnvironmentType.is_containerized(EnvironmentType.LOCAL) is False
    
    def test_is_production(self):
        """Test production environment detection."""
        assert EnvironmentType.is_production(EnvironmentType.AZURE) is True
        assert EnvironmentType.is_production(EnvironmentType.GCP) is True
        assert EnvironmentType.is_production(EnvironmentType.KUBERNETES) is True
        assert EnvironmentType.is_production(EnvironmentType.DOCKER) is False
        assert EnvironmentType.is_production(EnvironmentType.LOCAL) is False
    
    def test_validate(self):
        """Test environment type validation."""
        assert EnvironmentType.validate(EnvironmentType.AZURE) is True
        assert EnvironmentType.validate(EnvironmentType.GCP) is True
        assert EnvironmentType.validate(EnvironmentType.KUBERNETES) is True
        assert EnvironmentType.validate(EnvironmentType.DOCKER) is True
        assert EnvironmentType.validate(EnvironmentType.LOCAL) is True
        assert EnvironmentType.validate("INVALID") is False
        assert EnvironmentType.validate("") is False
    
    def test_environment_characteristics(self):
        """Test environment characteristic sets."""
        assert EnvironmentType.CLOUD_ENVIRONMENTS == {EnvironmentType.AZURE, EnvironmentType.GCP, EnvironmentType.KUBERNETES}
        assert EnvironmentType.CONTAINERIZED_ENVIRONMENTS == {EnvironmentType.KUBERNETES, EnvironmentType.DOCKER}
        assert EnvironmentType.PRODUCTION_ENVIRONMENTS == {EnvironmentType.AZURE, EnvironmentType.GCP, EnvironmentType.KUBERNETES}
    
    def test_display_names_mapping(self):
        """Test that all constants have corresponding display names."""
        for env_type in EnvironmentType.all_types():
            display_name = EnvironmentType.get_display_name(env_type)
            assert display_name != "Unknown"
            assert display_name is not None
            assert len(display_name) > 0
