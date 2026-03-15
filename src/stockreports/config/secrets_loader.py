"""
Secure credentials loader supporting multiple sources.
Follows 12-Factor App methodology for configuration management.

Priority order for credential resolution:
1. Environment Variables (highest priority)
2. Secret Management Service (Azure KeyVault, Google Secret Manager)
3. .env File (local development)
4. Default values (non-sensitive only)
"""

import os
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from src.stockreports.alert.common.environment import EnvironmentType

logger = logging.getLogger(__name__)


class SecretsLoader:
    """
    Multi-layered secrets loader with priority-based resolution.
    
    Automatically detects deployment environment and loads credentials
    from appropriate sources without requiring code changes.
    """

    def __init__(self, env_file: Optional[str] = None):
        """
        Initialize SecretsLoader.
        
        Args:
            env_file: Path to .env file (defaults to project root)
        """
        self.env_file = env_file or self._find_env_file()
        self.secrets_cache: Dict[str, Any] = {}
        self._load_env_file()
        self._detect_environment()

    @property
    def env_type(self) -> str:
        """
        Get the detected environment type (EnvironmentType constant).
        
        Returns:
            EnvironmentType constant
        """
        return self.environment_type

    def _find_env_file(self) -> Optional[Path]:
        """
        Locate .env file in project root or parent directories.
        
        Returns:
            Path to .env file if found, None otherwise
        """
        current = Path.cwd()
        for _ in range(4):  # Check up to 4 levels
            env_file = current / ".env"
            if env_file.exists():
                logger.info(f"Found .env file at: {env_file}")
                return env_file
            current = current.parent
        return None

    def _load_env_file(self) -> None:
        """
        Load environment variables from .env file.
        Only loads variables that are not already in OS environment.
        """
        if not self.env_file:
            logger.debug("No .env file found; using environment variables only")
            return

        try:
            with open(self.env_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    
                    # Skip empty lines and comments
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' not in line:
                        logger.warning(f"Invalid line in .env file (line {line_num}): {line}")
                        continue
                    
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    
                    # Validate key format
                    if not key or not key.replace('_', '').isalnum():
                        logger.warning(f"Invalid environment variable name in .env: {key}")
                        continue
                    
                    # Remove quotes if present
                    if value.startswith('"') and value.endswith('"'):
                        value = value[1:-1]
                    elif value.startswith("'") and value.endswith("'"):
                        value = value[1:-1]
                    
                    # Only load if not already in OS environment
                    if key not in os.environ:
                        os.environ[key] = value
                    
            logger.info(f"Loaded environment variables from {self.env_file}")
        except IOError as e:
            logger.warning(f"Failed to read .env file: {e}")
        except Exception as e:
            logger.warning(f"Error loading .env file: {e}")

    def _detect_environment(self) -> None:
        """
        Detect deployment environment.
        Sets flags for Azure, GCP, Kubernetes, Docker, or Local.
        Also sets environment_type using EnvironmentType constants.
        """
        self.is_azure = bool(os.getenv("AZURE_KEYVAULT_URL"))
        self.is_gcp = bool(os.getenv("GOOGLE_CLOUD_PROJECT"))
        self.is_kubernetes = bool(os.getenv("KUBERNETES_SERVICE_HOST"))
        self.is_docker = self._check_docker_environment()
        self.is_local = not any([self.is_azure, self.is_gcp, self.is_kubernetes, self.is_docker])

        # Set environment_type using EnvironmentType constants
        self.environment_type = self._get_environment_type()
        logger.debug(f"Detected deployment environment: {EnvironmentType.get_display_name(self.environment_type)}")

    def _check_docker_environment(self) -> bool:
        """Check if running in Docker container."""
        return Path("/.dockerenv").exists() or os.getenv("DOCKER_CONTAINER") == "true"

    def _get_environment_type(self) -> str:
        """
        Return EnvironmentType constant for detected environment.
        
        Returns:
            EnvironmentType constant (AZURE, GCP, KUBERNETES, DOCKER, or LOCAL)
        """
        if self.is_azure:
            return EnvironmentType.AZURE
        elif self.is_gcp:
            return EnvironmentType.GCP
        elif self.is_kubernetes:
            return EnvironmentType.KUBERNETES
        elif self.is_docker:
            return EnvironmentType.DOCKER
        else:
            return EnvironmentType.LOCAL

    def get_secret(
        self,
        key: str,
        default: Optional[str] = None,
        required: bool = False,
        is_sensitive: bool = False
    ) -> Optional[str]:
        """
        Retrieve a secret from priority-ordered sources.
        
        Priority:
        1. Environment Variables
        2. Secret Management Service
        3. .env File (already loaded into os.environ)
        4. Default Value
        
        Args:
            key: Secret key name (e.g., 'EMAIL_APP_PASSWORD')
            default: Default value if not found
            required: Raise exception if not found and required=True
            is_sensitive: Whether this is a sensitive value (for logging)
        
        Returns:
            Secret value or default
        
        Raises:
            ValueError: If required=True and secret not found
        """
        # Check cache first
        if key in self.secrets_cache:
            return self.secrets_cache[key]

        # Layer 1: Environment Variables (includes loaded .env)
        value = os.getenv(key)
        if value:
            logger.debug(f"Loaded '{key}' from environment variables")
            self.secrets_cache[key] = value
            return value

        # Layer 2: Secret Management Service (platform-specific)
        value = self._get_from_secret_manager(key)
        if value:
            logger.debug(f"Loaded '{key}' from secret management service")
            self.secrets_cache[key] = value
            return value

        # Layer 3: Default value
        if default is not None:
            logger.debug(f"Using default value for '{key}'")
            self.secrets_cache[key] = default
            return default

        # Not found
        if required:
            raise ValueError(
                f"Required secret '{key}' not found in any configuration source "
                f"(environment variables, secret manager, or defaults)"
            )

        logger.debug(f"Secret '{key}' not found and not required; returning None")
        return None

    def _get_from_secret_manager(self, key: str) -> Optional[str]:
        """
        Retrieve secret from platform-specific secret management service.
        Automatically detects environment and calls appropriate method.
        
        Args:
            key: Secret key name
            
        Returns:
            Secret value or None if not found
        """
        if self.is_azure:
            return self._get_from_azure_keyvault(key)
        elif self.is_gcp:
            return self._get_from_google_secret_manager(key)
        # Add more as needed: AWS Secrets Manager, HashiCorp Vault, etc.
        return None

    def _get_from_azure_keyvault(self, key: str) -> Optional[str]:
        """
        Retrieve secret from Azure Key Vault.
        
        Requires:
        - AZURE_KEYVAULT_URL environment variable
        - Azure credentials (DefaultAzureCredential)
        - azure-identity and azure-keyvault-secrets packages
        
        Args:
            key: Secret key name (converted to Azure format with hyphens)
            
        Returns:
            Secret value or None if not found
        """
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            keyvault_url = os.getenv("AZURE_KEYVAULT_URL")
            if not keyvault_url:
                logger.debug("AZURE_KEYVAULT_URL not set; skipping Azure Key Vault lookup")
                return None

            credential = DefaultAzureCredential()
            client = SecretClient(vault_url=keyvault_url, credential=credential)
            
            # Azure Key Vault uses hyphens instead of underscores
            azure_key = key.lower().replace("_", "-")
            
            try:
                secret = client.get_secret(azure_key)
                logger.debug(f"Retrieved '{key}' from Azure Key Vault")
                return secret.value
            except Exception as e:
                logger.debug(f"Secret '{azure_key}' not found in Azure Key Vault: {e}")
                return None
                
        except ImportError:
            logger.debug("Azure SDK not installed (azure-identity, azure-keyvault-secrets); "
                        "skipping Azure Key Vault")
            return None
        except Exception as e:
            logger.warning(f"Error accessing Azure Key Vault: {e}")
            return None

    def _get_from_google_secret_manager(self, key: str) -> Optional[str]:
        """
        Retrieve secret from Google Secret Manager.
        
        Requires:
        - GOOGLE_CLOUD_PROJECT environment variable
        - Google Cloud credentials (ADC or GOOGLE_APPLICATION_CREDENTIALS)
        - google-cloud-secret-manager package
        
        Args:
            key: Secret key name
            
        Returns:
            Secret value or None if not found
        """
        try:
            from google.cloud import secretmanager

            project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
            if not project_id:
                logger.debug("GOOGLE_CLOUD_PROJECT not set; skipping Google Secret Manager")
                return None

            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{project_id}/secrets/{key}/versions/latest"
            
            try:
                response = client.access_secret_version(request={"name": name})
                secret_value = response.payload.data.decode("UTF-8")
                logger.debug(f"Retrieved '{key}' from Google Secret Manager")
                return secret_value
            except Exception as e:
                logger.debug(f"Secret '{key}' not found in Google Secret Manager: {e}")
                return None
                
        except ImportError:
            logger.debug("Google Cloud SDK not installed (google-cloud-secret-manager); "
                        "skipping Google Secret Manager")
            return None
        except Exception as e:
            logger.warning(f"Error accessing Google Secret Manager: {e}")
            return None

    def get_all_secrets(self) -> Dict[str, str]:
        """
        Get all environment variables as a dictionary.
        WARNING: Do not log this in production (contains secrets).
        
        Returns:
            Dictionary of all environment variables
        """
        return dict(os.environ)

    def log_environment_info(self) -> None:
        """
        Log detected environment and configuration sources.
        Only logs non-sensitive information.
        """
        display_name = EnvironmentType.get_display_name(self.environment_type)
        logger.warning(f"Credentials Manager initialized for {display_name} environment")
        logger.warning(f"Environment flags - Azure: {self.is_azure}, GCP: {self.is_gcp}, "
                    f"Kubernetes: {self.is_kubernetes}, Docker: {self.is_docker}, "
                    f"Local: {self.is_local}")
        if self.env_file:
            logger.warning(f"Using .env file from: {self.env_file}")
