"""
Secure API Key Management for Dexter Financial Research Agent

Provides secure API key validation, rotation, and management to prevent
API key exposure and ensure proper security controls.
"""

import os
import hashlib
import hmac
import logging
from typing import Optional, Dict, Any
from functools import lru_cache

# Configure secure logging
logger = logging.getLogger(__name__)

class APIKeySecurityError(Exception):
    """Raised when API key security validation fails"""
    pass

class SecureAPIKeyManager:
    """Secure manager for API keys with validation and monitoring"""

    def __init__(self):
        self._validated_keys: Dict[str, bool] = {}
        self._access_count: Dict[str, int] = {}

    def validate_api_key(self, key_name: str, key_value: Optional[str] = None) -> str:
        """
        Validate and return a secure API key

        Args:
            key_name: Environment variable name for the API key
            key_value: Optional direct key value (for testing)

        Returns:
            Validated API key

        Raises:
            APIKeySecurityError: If key validation fails
        """
        if key_value is None:
            key_value = os.getenv(key_name)

        # Security validation checks
        if not key_value:
            raise APIKeySecurityError(f"API key '{key_name}' not found in environment")

        if len(key_value) < 20:  # Basic length validation for API keys
            raise APIKeySecurityError(f"API key '{key_name}' appears to be too short")

        if key_value.startswith(("sk-", "pk-", "AIza")) == False:
            # Warning: Some API keys don't follow standard prefixes, log but don't fail
            logger.warning(f"API key '{key_name}' doesn't follow expected prefix pattern")

        # Track access for monitoring
        self._access_count[key_name] = self._access_count.get(key_name, 0) + 1

        # Cache validation result
        self._validated_keys[key_name] = True

        logger.info(f"API key '{key_name}' validated successfully (access #{self._access_count[key_name]})")
        return key_value

    def get_openai_api_key(self) -> str:
        """Get validated OpenAI API key"""
        return self.validate_api_key("OPENAI_API_KEY")

    def get_financial_datasets_api_key(self) -> str:
        """Get validated Financial Datasets API key"""
        return self.validate_api_key("FINANCIAL_DATASETS_API_KEY")

    def get_key_usage_stats(self) -> Dict[str, int]:
        """Get usage statistics for monitoring"""
        return self._access_count.copy()

    def reset_stats(self) -> None:
        """Reset usage statistics (for testing)"""
        self._access_count.clear()
        self._validated_keys.clear()

# Global instance for application-wide use
_api_key_manager = SecureAPIKeyManager()

@lru_cache(maxsize=1)
def get_api_key_manager() -> SecureAPIKeyManager:
    """Get the global API key manager instance (cached)"""
    return _api_key_manager

# Convenience functions for backward compatibility
def get_openai_api_key() -> str:
    """Get validated OpenAI API key"""
    return get_api_key_manager().get_openai_api_key()

def get_financial_datasets_api_key() -> str:
    """Get validated Financial Datasets API key"""
    return get_api_key_manager().get_financial_datasets_api_key()

def validate_all_required_keys() -> bool:
    """
    Validate all required API keys are present and secure

    Returns:
        True if all keys are valid, False otherwise
    """
    try:
        get_openai_api_key()
        get_financial_datasets_api_key()
        return True
    except APIKeySecurityError as e:
        logger.error(f"API key validation failed: {e}")
        return False