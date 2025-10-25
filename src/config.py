"""
Centralized configuration for environment variables.
"""
import os

# AWS Configuration
AWS_REGION = os.getenv('AWS_REGION', 'us-east-2')
AWS_ACCOUNT_ID = os.getenv('AWS_ACCOUNT_ID', '391163822329')

# DynamoDB Table Names
USERS_TABLE_NAME = os.getenv('USERS_TABLE_NAME', 'Users')
TRIPS_TABLE_NAME = os.getenv('TRIPS_TABLE_NAME', 'Trips')
TRIP_STATES_TABLE_NAME = os.getenv('TRIP_STATES_TABLE_NAME', 'TripStates')

# Cognito Configuration
COGNITO_USER_POOL_ID = os.getenv('COGNITO_USER_POOL_ID')
COGNITO_CLIENT_ID = os.getenv('COGNITO_CLIENT_ID')

# AWS Services
INRIX_SECRET_ARN = os.getenv('INRIX_SECRET_ARN')
LOCATION_PLACE_INDEX_NAME = os.getenv('LOCATION_PLACE_INDEX_NAME', 'odessey-place-index')
BEDROCK_MODEL_ID = os.getenv('BEDROCK_MODEL_ID', 'anthropic.claude-3-sonnet-20240229-v1:0')

# INRIX Configuration
INRIX_BASE_URL = os.getenv('INRIX_BASE_URL', 'https://api.inrix.com/v1')

# API Gateway
API_GATEWAY_URL = os.getenv('API_GATEWAY_URL')

# Validation
def validate_config():
    """Validate that required environment variables are set."""
    required_vars = [
        'COGNITO_USER_POOL_ID',
        'COGNITO_CLIENT_ID',
        'INRIX_SECRET_ARN'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
    
    return True
