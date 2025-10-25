"""AWS Secrets Manager client."""

import json
import os
import boto3
from typing import Dict, Optional
from botocore.exceptions import ClientError

from src.utils.logger import error, info


class SecretsManager:
    """Client for retrieving secrets from AWS Secrets Manager."""
    
    def __init__(self, region: str = None):
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.client = boto3.client("secretsmanager", region_name=self.region)
        self._cache: Dict[str, str] = {}
    
    def get_secret(self, secret_name: str) -> Optional[str]:
        """
        Retrieve a secret from Secrets Manager with caching.
        
        Args:
            secret_name: Name or ARN of the secret
        
        Returns:
            Secret value or None if not found
        """
        if secret_name in self._cache:
            return self._cache[secret_name]
        
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            secret_value = response["SecretString"]
            
            # Cache for future use
            self._cache[secret_name] = secret_value
            info(f"Retrieved secret: {secret_name}")
            return secret_value
        
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code == "ResourceNotFoundException":
                error(f"Secret not found: {secret_name}")
            elif error_code == "InvalidRequestException":
                error(f"Invalid request for secret: {secret_name}")
            elif error_code == "InvalidParameterException":
                error(f"Invalid parameter for secret: {secret_name}")
            elif error_code == "DecryptionFailureException":
                error(f"Failed to decrypt secret: {secret_name}")
            elif error_code == "InternalServiceErrorException":
                error(f"Internal AWS error for secret: {secret_name}")
            else:
                error(f"Error retrieving secret {secret_name}: {str(e)}")
            return None
    
    def get_json_secret(self, secret_name: str) -> Dict:
        """
        Retrieve a JSON secret and parse it.
        
        Args:
            secret_name: Name or ARN of the secret
        
        Returns:
            Parsed JSON dictionary
        """
        secret_value = self.get_secret(secret_name)
        if not secret_value:
            return {}
        
        try:
            return json.loads(secret_value)
        except json.JSONDecodeError as e:
            error(f"Failed to parse JSON secret {secret_name}: {str(e)}")
            return {}
    
    def get_inrix_api_key(self) -> Optional[str]:
        """Get INRIX API key from Secrets Manager."""
        secret_arn = os.getenv("INRIX_SECRET_ARN")
        if not secret_arn:
            error("INRIX_SECRET_ARN not set in environment")
            return None
        
        secret_json = self.get_json_secret(secret_arn)
        return secret_json.get("INRIX_API_KEY") or os.getenv("INRIX_API_KEY")


# Global instance
_secrets_manager = None


def get_secrets_manager() -> SecretsManager:
    """Get global SecretsManager instance."""
    global _secrets_manager
    if _secrets_manager is None:
        _secrets_manager = SecretsManager()
    return _secrets_manager

