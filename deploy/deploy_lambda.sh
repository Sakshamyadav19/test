#!/bin/bash

# deploy_lambda.sh
# Packages and uploads Lambda function to AWS

set -e

if [ $# -eq 0 ]; then
    echo "Usage: $0 <handler_name>"
    echo "Available handlers: health, auth, init, classify, eta, plan, save, get_trip"
    exit 1
fi

HANDLER_NAME=$1
FUNCTION_NAME="odessey-$HANDLER_NAME"
REGION=${AWS_REGION:-us-east-2}
ROLE_NAME="lambda-execution-role"
PACKAGE_FILE="deploy/packages/${HANDLER_NAME}-lambda.zip"

echo "Deploying Lambda function: $FUNCTION_NAME"

# Check if package exists
if [ ! -f "$PACKAGE_FILE" ]; then
    echo "Package not found: $PACKAGE_FILE"
    echo "Run package_lambda.sh first to create the package"
    exit 1
fi

# Get role ARN
ROLE_ARN=$(aws iam get-role --role-name "$ROLE_NAME" --query 'Role.Arn' --output text)
if [ $? -ne 0 ]; then
    echo "Error: IAM role '$ROLE_NAME' not found"
    echo "Run create_iam_role.sh first to create the role"
    exit 1
fi

echo "Using IAM role: $ROLE_ARN"

# Check if function exists
if aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" > /dev/null 2>&1; then
    echo "Function exists, updating code..."
    aws lambda update-function-code \
        --function-name "$FUNCTION_NAME" \
        --zip-file "fileb://$PACKAGE_FILE" \
        --region "$REGION"
    
    echo "Updating function configuration..."
    aws lambda update-function-configuration \
        --function-name "$FUNCTION_NAME" \
        --timeout 30 \
        --memory-size 512 \
        --region "$REGION"
else
    echo "Creating new function..."
    aws lambda create-function \
        --function-name "$FUNCTION_NAME" \
        --runtime python3.9 \
        --role "$ROLE_ARN" \
        --handler handler.lambda_handler \
        --zip-file "fileb://$PACKAGE_FILE" \
        --timeout 30 \
        --memory-size 512 \
        --region "$REGION"
fi

# Set environment variables
echo "Setting environment variables..."
aws lambda update-function-configuration \
    --function-name "$FUNCTION_NAME" \
    --environment Variables="{
        USERS_TABLE_NAME=Users,
        TRIPS_TABLE_NAME=Trips,
        TRIP_STATES_TABLE_NAME=TripStates,
        COGNITO_USER_POOL_ID=${COGNITO_USER_POOL_ID},
        COGNITO_CLIENT_ID=${COGNITO_CLIENT_ID},
        INRIX_SECRET_ARN=${INRIX_SECRET_ARN},
        LOCATION_PLACE_INDEX_NAME=odessey-place-index,
        BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0,
        AWS_REGION=${REGION}
    }" \
    --region "$REGION"

echo "Function deployed successfully: $FUNCTION_NAME"
echo "Function ARN: $(aws lambda get-function --function-name "$FUNCTION_NAME" --region "$REGION" --query 'Configuration.FunctionArn' --output text)"

echo "Done!"
