"""JWT validation and Cognito helpers."""

import os
import json
import boto3
import bcrypt
from functools import wraps
from typing import Dict, Optional

from src.utils.errors import UnauthorizedError
from src.utils.logger import error, info


class AuthService:
    """Service for handling authentication."""
    
    def __init__(self):
        self.cognito_client = boto3.client("cognito-idp", region_name=os.getenv("AWS_REGION", "us-west-2"))
        self.user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
        self.client_id = os.getenv("COGNITO_CLIENT_ID")
    
    def extract_user_from_event(self, event: Dict) -> Optional[str]:
        """
        Extract user ID from API Gateway event (after Cognito authorizer.
        
        Args:
            event: Lambda event from API Gateway
        
        Returns:
            User ID (sub from JWT)
        """
        request_context = event.get("requestContext", {})
        authorizer = request_context.get("authorizer", {})
        
        # Extract from Cognito authorizer
        claims = authorizer.get("claims", {})
        if claims:
            return claims.get("sub")
        
        # Fallback: check JWT directly if available
        if "jwt" in authorizer:
            jwt_data = authorizer["jwt"]
            claims = jwt_data.get("claims", {})
            return claims.get("sub")
        
        return None
    
    def validate_token(self, token: str) -> Dict:
        """
        Validate JWT token with Cognito.
        
        Args:
            token: JWT token string
        
        Returns:
            Decoded token claims
        
        Raises:
            UnauthorizedError: If token is invalid
        """
        if not token:
            raise UnauthorizedError("No token provided")
        
        try:
            response = self.cognito_client.get_user(AccessToken=token)
            return response.get("UserAttributes", {})
        
        except self.cognito_client.exceptions.NotAuthorizedException:
            raise UnauthorizedError("Invalid or expired token")
        except Exception as e:
            error(f"Token validation failed: {str(e)}")
            raise UnauthorizedError("Token validation failed")
    
    def signup_user(self, email: str, password: str) -> Dict:
        """
        Sign up a new user in Cognito and DynamoDB.
        
        Args:
            email: User email
            password: User password
        
        Returns:
            Dictionary with userId
        """
        try:
            # Create user in Cognito
            response = self.cognito_client.sign_up(
                ClientId=self.client_id,
                Username=email,
                Password=password,
                UserAttributes=[
                    {"Name": "email", "Value": email}
                ]
            )
            
            user_id = response.get("UserSub")
            info(f"Created Cognito user: {user_id}")
            
            return {
                "userId": user_id,
                "email": email
            }
        
        except self.cognito_client.exceptions.UsernameExistsException:
            raise UnauthorizedError("User already exists")
        except Exception as e:
            error(f"Signup failed: {str(e)}")
            raise UnauthorizedError(f"Failed to sign up user: {str(e)}")
    
    def login_user(self, email: str, password: str) -> Dict:
        """
        Authenticate user and return tokens.
        
        Args:
            email: User email
            password: User password
        
        Returns:
            Dictionary with tokens and user info
        """
        try:
            # Authenticate with Cognito
            response = self.cognito_client.initiate_auth(
                ClientId=self.client_id,
                AuthFlow="USER_PASSWORD_AUTH",
                AuthParameters={
                    "USERNAME": email,
                    "PASSWORD": password
                }
            )
            
            authentication_result = response.get("AuthenticationResult", {})
            
            return {
                "accessToken": authentication_result.get("AccessToken"),
                "refreshToken": authentication_result.get("RefreshToken"),
                "idToken": authentication_result.get("IdToken")
            }
        
        except self.cognito_client.exceptions.NotAuthorizedException:
            raise UnauthorizedError("Invalid email or password")
        except Exception as e:
            error(f"Login failed: {str(e)}")
            raise UnauthorizedError(f"Failed to authenticate user: {str(e)}")


# Global instance
_auth_service = None


def get_auth_service() -> AuthService:
    """Get global AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def lambda_response(status_code: int, body: Dict, headers: Dict = None) -> Dict:
    """
    Create a Lambda API Gateway response.
    
    Args:
        status_code: HTTP status code
        body: Response body as dictionary
        headers: Optional custom headers
    
    Returns:
        API Gateway response dictionary
    """
    default_headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
        "Access-Control-Allow-Methods": "GET,POST,PUT,DELETE,OPTIONS"
    }
    
    if headers:
        default_headers.update(headers)
    
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body, default=str)
    }


def lambda_handler_decorator(func):
    """Decorator for Lambda handlers with error handling."""
    @wraps(func)
    def wrapper(event, context):
        try:
            # Call the handler
            return func(event, context)
        
        except UnauthorizedError as e:
            return lambda_response(401, {"error": e.message, "code": e.code})
        
        except Exception as e:
            error(f"Handler error in {func.__name__}: {str(e)}")
            return lambda_response(500, {"error": "Internal server error", "code": "INTERNAL_ERROR"})
    
    return wrapper


def validate_trip_ownership(trip_state_user_id: str, requesting_user_id: str):
    """
    Validate that the requesting user owns the trip.
    
    Args:
        trip_state_user_id: User ID from trip state
        requesting_user_id: User ID from request context
    
    Raises:
        UnauthorizedError: If ownership validation fails
    """
    if trip_state_user_id != requesting_user_id:
        raise UnauthorizedError("You do not have permission to access this trip")

