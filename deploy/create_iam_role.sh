#!/bin/bash

# create_iam_role.sh
# Creates the IAM role and policy for Lambda functions

set -e

ACCOUNT_ID=${AWS_ACCOUNT_ID:-391163822329}
REGION=${AWS_REGION:-us-east-2}
ROLE_NAME="OdesseyLambdaRole"
POLICY_NAME="OdesseyLambdaPolicy"

echo "Creating IAM role and policy for Lambda functions..."
echo "Account ID: $ACCOUNT_ID"
echo "Region: $REGION"

# Create trust policy for Lambda
cat > trust-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": "lambda.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
        }
    ]
}
EOF

# Create IAM policy for Lambda permissions
cat > lambda-policy.json << EOF
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:GetItem",
                "dynamodb:PutItem",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:Query",
                "dynamodb:Scan"
            ],
            "Resource": [
                "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/Users",
                "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/Trips",
                "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/TripStates",
                "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/Trips/index/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "cognito-idp:GetUser",
                "cognito-idp:AdminGetUser",
                "cognito-idp:SignUp",
                "cognito-idp:InitiateAuth",
                "cognito-idp:AdminCreateUser"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "geo:SearchPlaceIndexForText"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "bedrock:InvokeModel"
            ],
            "Resource": "*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "secretsmanager:GetSecretValue"
            ],
            "Resource": "arn:aws:secretsmanager:${REGION}:${ACCOUNT_ID}:secret:odessey-inrix-api-key*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "*"
        }
    ]
}
EOF

# Create the IAM role
echo "Creating IAM role: $ROLE_NAME"
aws iam create-role \
    --role-name "$ROLE_NAME" \
    --assume-role-policy-document file://trust-policy.json \
    --description "Execution role for Odessey Lambda functions" \
    || echo "Role may already exist"

# Create the IAM policy
echo "Creating IAM policy: $POLICY_NAME"
aws iam create-policy \
    --policy-name "$POLICY_NAME" \
    --policy-document file://lambda-policy.json \
    --description "Policy for Odessey Lambda functions" \
    || echo "Policy may already exist"

# Attach the policy to the role
echo "Attaching policy to role..."
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::${ACCOUNT_ID}:policy/${POLICY_NAME}"

# Attach AWS managed policy for basic Lambda execution
aws iam attach-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-arn "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"

echo "IAM role and policy created successfully!"
echo "Role ARN: arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"

# Clean up temporary files
rm -f trust-policy.json lambda-policy.json

echo "Done!"
