"""Authentication handlers."""

import json
import boto3
import os
from src.models.dto import SignupRequest, LoginRequest, AuthResponse
from src.models.dynamo import User
from src.utils.auth import get_auth_service, lambda_response, lambda_handler_decorator
from src.utils.errors import UnauthorizedError, ValidationError
from src.utils.logger import info, error


dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-2"))
users_table = dynamodb.Table(os.getenv("USERS_TABLE_NAME", "Users"))


def lambda_handler(event, context):
    """
    Route requests to appropriate auth handler based on path.
    """
    path = event.get("path", "")
    
    if path == "/auth/signup":
        return signup_handler(event, context)
    elif path == "/auth/login":
        return login_handler(event, context)
    else:
        return lambda_response(404, {"error": "Not found", "code": "NOT_FOUND"})


@lambda_handler_decorator
def signup_handler(event, context):
    """
    Handle user signup.
    
    POST /auth/signup
    Body: {email, password}
    
    Returns:
        AuthResponse with tokens and user ID
    """
    try:
        body = json.loads(event.get("body", "{}"))
        
        # Validate request
        signup_req = SignupRequest(**body)
        
        # Create user in Cognito
        auth_service = get_auth_service()
        cognito_user = auth_service.signup_user(signup_req.email, signup_req.password)
        
        # Store in DynamoDB
        user = User(
            userId=cognito_user["userId"],
            email=signup_req.email
        )
        users_table.put_item(Item=user.to_item())
        
        info(f"User signed up: {signup_req.email}")
        
        return lambda_response(200, {
            "userId": cognito_user["userId"],
            "message": "User signed up successfully"
        })
    
    except ValidationError as e:
        return lambda_response(400, {"error": e.message, "code": e.code})
    except UnauthorizedError as e:
        return lambda_response(401, {"error": e.message, "code": e.code})
    except Exception as e:
        error(f"Signup error: {str(e)}")
        return lambda_response(500, {"error": "Failed to sign up user", "code": "INTERNAL_ERROR"})


@lambda_handler_decorator
def login_handler(event, context):
    """
    Handle user login.
    
    POST /auth/login
    Body: {email, password}
    
    Returns:
        AuthResponse with tokens and user ID
    """
    try:
        body = json.loads(event.get("body", "{}"))
        
        # Validate request
        login_req = LoginRequest(**body)
        
        # Authenticate with Cognito
        auth_service = get_auth_service()
        auth_result = auth_service.login_user(login_req.email, login_req.password)
        
        # Get user from DynamoDB
        response = users_table.scan(
            FilterExpression="email = :email",
            ExpressionAttributeValues={":email": login_req.email}
        )
        
        items = response.get("Items", [])
        if not items:
            raise UnauthorizedError("User not found")
        
        user_id = items[0]["userId"]
        
        info(f"User logged in: {login_req.email}")
        
        return lambda_response(200, {
            "accessToken": auth_result.get("accessToken"),
            "refreshToken": auth_result.get("refreshToken"),
            "userId": user_id,
            "message": "Logged in successfully"
        })
    
    except ValidationError as e:
        return lambda_response(400, {"error": e.message, "code": e.code})
    except UnauthorizedError as e:
        return lambda_response(401, {"error": e.message, "code": e.code})
    except Exception as e:
        error(f"Login error: {str(e)}")
        return lambda_response(500, {"error": "Failed to log in user", "code": "INTERNAL_ERROR"})
