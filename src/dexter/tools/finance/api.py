import os
import requests
import logging
from dexter.utils.api_security import get_financial_datasets_api_key, APIKeySecurityError
from dexter.utils.rate_limiter import rate_limit

####################################
# Secure API Configuration
####################################

logger = logging.getLogger(__name__)

@rate_limit(api_type="financial_datasets", cost=0.001)
def call_api(endpoint: str, params: dict) -> dict:
    """
    Helper function to call the Financial Datasets API with secure key management.

    Args:
        endpoint: API endpoint path
        params: Query parameters for the API call

    Returns:
        JSON response from the API

    Raises:
        APIKeySecurityError: If API key validation fails
        requests.exceptions.RequestException: If API call fails
    """
    try:
        # Get validated API key (not stored at module level)
        api_key = get_financial_datasets_api_key()

        base_url = "https://api.financialdatasets.ai"
        url = f"{base_url}{endpoint}"
        headers = {"x-api-key": api_key}

        logger.info(f"Making API call to Financial Datasets: {endpoint}")
        response = requests.get(url, params=params, headers=headers, timeout=(30, 60))
        response.raise_for_status()

        return response.json()

    except APIKeySecurityError as e:
        logger.error(f"API key validation failed: {e}")
        raise
    except requests.exceptions.RequestException as e:
        logger.error(f"API call failed for {endpoint}: {e}")
        raise

