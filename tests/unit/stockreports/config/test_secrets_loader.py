"""
Tests for SecretsLoader and environment type integration.
"""

import pytest
from src.stockreports.alert.common.environment import EnvironmentType
from src.stockreports.config.secrets_loader import SecretsLoader


class TestSecretsLoaderEnvironmentType:
    """Test SecretsLoader environment type detection."""

    def test_local_environment_detection(self, monkeypatch):
        """Test local environment detection."""
        # Unset all cloud environment variables
        monkeypatch.delenv("AZURE_KEYVAULT_URL", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
        monkeypatch.delenv("DOCKER_CONTAINER", raising=False)

        loader = SecretsLoader()
        assert loader.env_type == EnvironmentType.LOCAL
        assert loader.is_local is True
        assert loader.is_azure is False
        assert loader.is_gcp is False
        assert loader.is_kubernetes is False
        assert loader.is_docker is False

    def test_gcp_environment_detection(self, monkeypatch):
        """Test GCP environment detection."""
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
        monkeypatch.delenv("AZURE_KEYVAULT_URL", raising=False)
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
        monkeypatch.delenv("DOCKER_CONTAINER", raising=False)

        loader = SecretsLoader()
        assert loader.env_type == EnvironmentType.GCP
        assert loader.is_gcp is True
        assert loader.is_local is False

    def test_azure_environment_detection(self, monkeypatch):
        """Test Azure environment detection."""
        monkeypatch.setenv("AZURE_KEYVAULT_URL", "https://myvault.vault.azure.net/")
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
        monkeypatch.delenv("DOCKER_CONTAINER", raising=False)

        loader = SecretsLoader()
        assert loader.env_type == EnvironmentType.AZURE
        assert loader.is_azure is True
        assert loader.is_local is False

    def test_kubernetes_environment_detection(self, monkeypatch):
        """Test Kubernetes environment detection."""
        monkeypatch.setenv("KUBERNETES_SERVICE_HOST", "10.0.0.1")
        monkeypatch.delenv("AZURE_KEYVAULT_URL", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("DOCKER_CONTAINER", raising=False)

        loader = SecretsLoader()
        assert loader.env_type == EnvironmentType.KUBERNETES
        assert loader.is_kubernetes is True
        assert loader.is_local is False

    def test_docker_environment_detection(self, monkeypatch):
        """Test Docker environment detection."""
        monkeypatch.setenv("DOCKER_CONTAINER", "true")
        monkeypatch.delenv("AZURE_KEYVAULT_URL", raising=False)
        monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)

        loader = SecretsLoader()
        assert loader.env_type == EnvironmentType.DOCKER
        assert loader.is_docker is True
        assert loader.is_local is False

    def test_environment_type_property(self, monkeypatch):
        """Test env_type property access."""
        monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "my-project")
        monkeypatch.delenv("AZURE_KEYVAULT_URL", raising=False)
        monkeypatch.delenv("KUBERNETES_SERVICE_HOST", raising=False)
        monkeypatch.delenv("DOCKER_CONTAINER", raising=False)

        loader = SecretsLoader()
        # env_type should be accessible as a property
        assert loader.env_type == EnvironmentType.GCP
        assert isinstance(loader.env_type, str)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
