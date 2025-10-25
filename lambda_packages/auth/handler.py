"""Authentication handlers."""

import json
import boto3
import os
import time
import hmac
import hashlib
import base64


def lambda_handler(event, context):
    """
    Route requests to appropriate auth handler based on path.
    """
    try:
        # Extract path from event - API Gateway includes stage in path like /prod/auth/signup
        full_path = event.get("path", "")
        # Remove stage prefix if present (e.g., "/prod/auth/signup" -> "/auth/signup")
        path = full_path.replace("/prod", "").replace("/$default", "")
        print(f"Received request for path: {full_path} (normalized: {path})")
        
        if path == "/auth/signup":
            return signup_handler(event, context)
        elif path == "/auth/login":
            return login_handler(event, context)
        else:
            return create_response(404, {"error": "Not found", "code": "NOT_FOUND"})
    except Exception as e:
        print(f"Lambda handler error: {str(e)}")
        return create_response(500, {"error": "Internal server error", "code": "INTERNAL_ERROR"})


def create_response(status_code, body):
    """Create API Gateway response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
        },
        "body": json.dumps(body)
    }


def compute_secret_hash(username, client_id, client_secret):
    """Compute SECRET_HASH for Cognito operations."""
    message = username + client_id
    dig = hmac.new(
        client_secret.encode('utf-8'),
        message.encode('utf-8'),
        hashlib.sha256
    ).digest()
    return base64.b64encode(dig).decode()


def signup_handler(event, context):
    """
    Handle user signup.
    
    POST /auth/signup
    Body: {email, password}
    """
    try:
        print("Starting signup process")
        
        # Parse body
        body_str = event.get("body", "{}")
        print(f"Request body: {body_str}")
        
        if not body_str:
            return create_response(400, {"error": "Request body is required", "code": "MISSING_BODY"})
        
        body = json.loads(body_str)
        print(f"Parsed body: {body}")
        
        # Validate required fields
        email = body.get("email")
        password = body.get("password")
        
        if not email:
            return create_response(400, {"error": "Email is required", "code": "MISSING_EMAIL"})
        
        if not password:
            return create_response(400, {"error": "Password is required", "code": "MISSING_PASSWORD"})
        
        # Basic email validation
        if "@" not in email:
            return create_response(400, {"error": "Invalid email format", "code": "INVALID_EMAIL"})
        
        # Basic password validation
        if len(password) < 8:
            return create_response(400, {"error": "Password must be at least 8 characters", "code": "WEAK_PASSWORD"})
        
        print(f"Attempting to create user: {email}")
        
        # Initialize Cognito client
        cognito_client = boto3.client("cognito-idp", region_name=os.getenv("AWS_REGION", "us-east-2"))
        user_pool_id = os.getenv("COGNITO_USER_POOL_ID")
        client_id = os.getenv("COGNITO_CLIENT_ID")
        client_secret = os.getenv("COGNITO_CLIENT_SECRET")
        
        print(f"User Pool ID: {user_pool_id}")
        print(f"Client ID: {client_id}")
        
        if not user_pool_id or not client_id:
            return create_response(500, {"error": "Cognito configuration missing", "code": "CONFIG_ERROR"})
        
        # Compute SECRET_HASH if client secret is provided
        secret_hash = None
        if client_secret:
            secret_hash = compute_secret_hash(email, client_id, client_secret)
        
        # Create user in Cognito
        try:
            signup_params = {
                "ClientId": client_id,
                "Username": email,
                "Password": password,
                "UserAttributes": [
                    {
                        'Name': 'email',
                        'Value': email
                    }
                ]
            }
            
            if secret_hash:
                signup_params["SecretHash"] = secret_hash
            
            response = cognito_client.sign_up(**signup_params)
            print(f"Cognito signup response: {response}")
            
            user_id = response.get('UserSub')
            if not user_id:
                return create_response(500, {"error": "Failed to get user ID from Cognito", "code": "COGNITO_ERROR"})
            
            # Admin confirm the user immediately so they can log in
            try:
                cognito_client.admin_confirm_sign_up(
                    UserPoolId=user_pool_id,
                    Username=email
                )
                print(f"User {email} admin-confirmed successfully")
            except Exception as e:
                print(f"Warning: Failed to admin-confirm user {email}: {str(e)}")
                # Don't fail signup if confirmation fails, user is still created
            
        except cognito_client.exceptions.UsernameExistsException:
            return create_response(409, {"error": "User already exists", "code": "USER_EXISTS"})
        except cognito_client.exceptions.InvalidPasswordException as e:
            error_msg = str(e)
            print(f"Cognito signup error: {error_msg}")
            # Extract the specific password requirement
            if "Password did not conform with policy" in error_msg:
                # Try to extract the specific requirement
                if "symbol" in error_msg.lower():
                    return create_response(400, {"error": "Password must contain at least one symbol character", "code": "INVALID_PASSWORD"})
                elif "uppercase" in error_msg.lower():
                    return create_response(400, {"error": "Password must contain at least one uppercase letter", "code": "INVALID_PASSWORD"})
                elif "lowercase" in error_msg.lower():
                    return create_response(400, {"error": "Password must contain at least one lowercase letter", "code": "INVALID_PASSWORD"})
                elif "number" in error_msg.lower() or "digit" in error_msg.lower():
                    return create_response(400, {"error": "Password must contain at least one number", "code": "INVALID_PASSWORD"})
                elif "length" in error_msg.lower():
                    return create_response(400, {"error": "Password does not meet minimum length requirement (8 characters)", "code": "INVALID_PASSWORD"})
                else:
                    return create_response(400, {"error": "Password does not meet requirements: must contain uppercase, lowercase, numbers, and symbols", "code": "INVALID_PASSWORD"})
            return create_response(400, {"error": error_msg, "code": "INVALID_PASSWORD"})
        except cognito_client.exceptions.InvalidParameterException as e:
            error_msg = str(e)
            print(f"Cognito signup error: {error_msg}")
            return create_response(400, {"error": error_msg, "code": "INVALID_PARAMETER"})
        except Exception as e:
            print(f"Cognito signup error: {str(e)}")
            return create_response(500, {"error": f"Signup failed: {str(e)}", "code": "COGNITO_ERROR"})
        
        # Store in DynamoDB
        try:
            dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-2"))
            users_table = dynamodb.Table(os.getenv("USERS_TABLE_NAME", "Users"))
            
            user_item = {
                "userId": user_id,
                "email": email,
                "createdAt": str(int(time.time()))
            }
            
            users_table.put_item(Item=user_item)
            print(f"User stored in DynamoDB: {user_id}")
            
        except Exception as e:
            print(f"DynamoDB error: {str(e)}")
            # Don't fail signup if DynamoDB fails, user is already created in Cognito
        
        print(f"User signed up successfully: {email}")
        
        return create_response(200, {
            "userId": user_id,
            "email": email,
            "message": "User signed up successfully"
        })
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return create_response(400, {"error": "Invalid JSON in request body", "code": "INVALID_JSON"})
    except Exception as e:
        print(f"Signup error: {str(e)}")
        return create_response(500, {"error": f"Failed to sign up user: {str(e)}", "code": "INTERNAL_ERROR"})


def login_handler(event, context):
    """
    Handle user login.
    
    POST /auth/login
    Body: {email, password}
    """
    try:
        print("Starting login process")
        
        # Parse body
        body_str = event.get("body", "{}")
        print(f"Request body: {body_str}")
        
        if not body_str:
            return create_response(400, {"error": "Request body is required", "code": "MISSING_BODY"})
        
        body = json.loads(body_str)
        print(f"Parsed body: {body}")
        
        # Validate required fields
        email = body.get("email")
        password = body.get("password")
        
        if not email:
            return create_response(400, {"error": "Email is required", "code": "MISSING_EMAIL"})
        
        if not password:
            return create_response(400, {"error": "Password is required", "code": "MISSING_PASSWORD"})
        
        print(f"Attempting to login user: {email}")
        
        # Initialize Cognito client
        cognito_client = boto3.client("cognito-idp", region_name=os.getenv("AWS_REGION", "us-east-2"))
        client_id = os.getenv("COGNITO_CLIENT_ID")
        client_secret = os.getenv("COGNITO_CLIENT_SECRET")
        
        print(f"Client ID: {client_id}")
        
        if not client_id:
            return create_response(500, {"error": "Cognito configuration missing", "code": "CONFIG_ERROR"})
        
        # Compute SECRET_HASH if client secret is provided
        secret_hash = None
        if client_secret:
            secret_hash = compute_secret_hash(email, client_id, client_secret)
        
        # Authenticate with Cognito
        try:
            auth_params = {
                "ClientId": client_id,
                "AuthFlow": 'USER_PASSWORD_AUTH',
                "AuthParameters": {
                    'USERNAME': email,
                    'PASSWORD': password
                }
            }
            
            if secret_hash:
                auth_params["AuthParameters"]["SECRET_HASH"] = secret_hash
            
            response = cognito_client.initiate_auth(**auth_params)
            print(f"Cognito login response: {response}")
            
            auth_result = response.get('AuthenticationResult', {})
            access_token = auth_result.get('AccessToken')
            refresh_token = auth_result.get('RefreshToken')
            
            if not access_token:
                return create_response(401, {"error": "Authentication failed", "code": "AUTH_FAILED"})
            
        except cognito_client.exceptions.NotAuthorizedException:
            return create_response(401, {"error": "Invalid email or password", "code": "INVALID_CREDENTIALS"})
        except cognito_client.exceptions.UserNotFoundException:
            return create_response(401, {"error": "User not found", "code": "USER_NOT_FOUND"})
        except Exception as e:
            print(f"Cognito login error: {str(e)}")
            return create_response(500, {"error": f"Cognito login failed: {str(e)}", "code": "COGNITO_ERROR"})
        
        # Get user ID from DynamoDB
        try:
            dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-east-2"))
            users_table = dynamodb.Table(os.getenv("USERS_TABLE_NAME", "Users"))
            
            response = users_table.scan(
                FilterExpression="email = :email",
                ExpressionAttributeValues={":email": email}
            )
            
            items = response.get("Items", [])
            if not items:
                return create_response(404, {"error": "User not found in database", "code": "USER_NOT_FOUND"})
            
            user_id = items[0]["userId"]
            print(f"User found in DynamoDB: {user_id}")
            
        except Exception as e:
            print(f"DynamoDB error: {str(e)}")
            return create_response(500, {"error": f"Database error: {str(e)}", "code": "DATABASE_ERROR"})
        
        print(f"User logged in successfully: {email}")
        
        return create_response(200, {
            "accessToken": access_token,
            "refreshToken": refresh_token,
            "userId": user_id,
            "email": email,
            "message": "Logged in successfully"
        })
    
    except json.JSONDecodeError as e:
        print(f"JSON decode error: {str(e)}")
        return create_response(400, {"error": "Invalid JSON in request body", "code": "INVALID_JSON"})
    except Exception as e:
        print(f"Login error: {str(e)}")
        return create_response(500, {"error": f"Failed to log in user: {str(e)}", "code": "INTERNAL_ERROR"})