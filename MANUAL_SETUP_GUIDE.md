# Manual AWS Setup Guide

This guide walks you through setting up all AWS resources manually via the AWS Console.

## Prerequisites

- AWS Account with appropriate permissions
- AWS CLI configured with correct credentials
- Account ID: `391163822329`
- Region: `us-east-2`

## Step 1: Create DynamoDB Tables

### 1.1 Users Table

1. Go to **DynamoDB** in AWS Console
2. Click **Create table**
3. Configure:
   - **Table name**: `Users`
   - **Partition key**: `userId` (String)
   - **Billing mode**: On-demand
4. Click **Create table**

### 1.2 Trips Table

1. Click **Create table**
2. Configure:
   - **Table name**: `Trips`
   - **Partition key**: `tripId` (String)
   - **Billing mode**: On-demand
3. Click **Create table**
4. After creation, go to **Indexes** tab
5. Click **Create index**
6. Configure GSI:
   - **Index name**: `userId-createdAt-index`
   - **Partition key**: `GSI1PK` (String)
   - **Sort key**: `GSI1SK` (String)
7. Click **Create index**

### 1.3 TripStates Table

1. Click **Create table**
2. Configure:
   - **Table name**: `TripStates`
   - **Partition key**: `tripId` (String)
   - **Billing mode**: On-demand
3. Click **Create table**

## Step 2: Create Cognito User Pool

1. Go to **Cognito** in AWS Console
2. Click **Create user pool**
3. **Step 1 - Sign-in experience**:
   - **Cognito user pool sign-in options**: Email
   - **User name requirements**: Email
4. **Step 2 - Security requirements**:
   - **Password policy**: Custom
   - **Minimum length**: 8
   - **Require uppercase letters**: Yes
   - **Require lowercase letters**: Yes
   - **Require numbers**: Yes
   - **Require symbols**: No
5. **Step 3 - Sign-up experience**:
   - **Self-service sign-up**: Enable
   - **Cognito-assisted verification**: Email
6. **Step 4 - Message delivery**:
   - **Email**: Send email with Amazon SES
7. **Step 5 - Integrate your app**:
   - **User pool name**: `odessey-user-pool`
   - **App client name**: `odessey-client`
   - **Client secret**: Don't generate a client secret
8. **Step 6 - Review and create**:
   - Review settings and click **Create user pool**

## Step 3: Create Amazon Location Service

1. Go to **Amazon Location Service** in AWS Console
2. Click **Create resource**
3. Select **Place index**
4. Configure:
   - **Name**: `odessey-place-index`
   - **Data provider**: Esri
   - **Pricing plan**: Request-based pricing
5. Click **Create place index**

## Step 4: Create Secrets Manager Secret

1. Go to **Secrets Manager** in AWS Console
2. Click **Store a new secret**
3. Configure:
   - **Secret type**: Other type of secret
   - **Key/value pairs**:
     - Key: `INRIX_API_KEY`
     - Value: `your-actual-inrix-api-key-here`
4. **Secret name**: `odessey-inrix-api-key`
5. Click **Next** → **Next** → **Store**

## Step 5: Create IAM Role for Lambda

1. Go to **IAM** in AWS Console
2. Click **Roles** → **Create role**
3. **Trusted entity type**: AWS service
4. **Service**: Lambda
5. Click **Next**
6. **Permissions**: Create custom policy
7. **Policy name**: `OdesseyLambdaPolicy`
8. **Policy document**:
```json
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
                "arn:aws:dynamodb:us-east-2:391163822329:table/Users",
                "arn:aws:dynamodb:us-east-2:391163822329:table/Trips",
                "arn:aws:dynamodb:us-east-2:391163822329:table/TripStates",
                "arn:aws:dynamodb:us-east-2:391163822329:table/Trips/index/*"
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
            "Resource": "arn:aws:secretsmanager:us-east-2:391163822329:secret:odessey-inrix-api-key*"
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
```
9. Click **Next** → **Next**
10. **Role name**: `OdesseyLambdaRole`
11. Click **Create role**

## Step 6: Create API Gateway

1. Go to **API Gateway** in AWS Console
2. Click **Create API**
3. Select **HTTP API**
4. Click **Build**
5. Configure:
   - **API name**: `odessey-api`
   - **CORS**: Configure CORS
     - **Access-Control-Allow-Origin**: `*`
     - **Access-Control-Allow-Headers**: `Content-Type,X-Amz-Date,Authorization,X-Api-Key`
     - **Access-Control-Allow-Methods**: `GET,POST,PUT,DELETE,OPTIONS`
6. Click **Next** → **Create**

## Step 7: Environment Variables Reference

After creating Lambda functions, set these environment variables:

```bash
USERS_TABLE_NAME=Users
TRIPS_TABLE_NAME=Trips
TRIP_STATES_TABLE_NAME=TripStates
COGNITO_USER_POOL_ID=us-east-2_xxxxxxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxx
INRIX_SECRET_ARN=arn:aws:secretsmanager:us-east-2:391163822329:secret:odessey-inrix-api-key-xxxxx
LOCATION_PLACE_INDEX_NAME=odessey-place-index
BEDROCK_MODEL_ID=anthropic.claude-3-sonnet-20240229-v1:0
AWS_REGION=us-east-2
```

## Next Steps

1. Use the deployment scripts to create Lambda functions
2. Connect API Gateway routes to Lambda functions
3. Test the API endpoints

## Resource ARNs Reference

- **Users Table**: `arn:aws:dynamodb:us-east-2:391163822329:table/Users`
- **Trips Table**: `arn:aws:dynamodb:us-east-2:391163822329:table/Trips`
- **TripStates Table**: `arn:aws:dynamodb:us-east-2:391163822329:table/TripStates`
- **Cognito User Pool**: `arn:aws:cognito-idp:us-east-2:391163822329:userpool/us-east-2_xxxxxxxxx`
- **Location Place Index**: `arn:aws:geo:us-east-2:391163822329:place-index/odessey-place-index`
- **Secrets Manager**: `arn:aws:secretsmanager:us-east-2:391163822329:secret:odessey-inrix-api-key-xxxxx`
- **Lambda Role**: `arn:aws:iam::391163822329:role/OdesseyLambdaRole`
