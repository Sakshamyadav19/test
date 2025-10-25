# API Gateway Route Configuration Guide

This guide explains how to configure API Gateway routes to connect with Lambda functions.

## Prerequisites

- All Lambda functions deployed (use `deploy_lambda.sh`)
- API Gateway created (see MANUAL_SETUP_GUIDE.md)
- Lambda functions accessible

## Route Configuration

### 1. Health Check Route
- **Method**: GET
- **Path**: `/health`
- **Lambda Function**: `odessey-health`
- **Authorization**: None (public)

### 2. Authentication Routes
- **Method**: POST
- **Path**: `/auth/signup`
- **Lambda Function**: `odessey-auth`
- **Authorization**: None (public)

- **Method**: POST
- **Path**: `/auth/login`
- **Lambda Function**: `odessey-auth`
- **Authorization**: None (public)

### 3. Trip Management Routes (Protected)
- **Method**: POST
- **Path**: `/trip/init`
- **Lambda Function**: `odessey-init`
- **Authorization**: Cognito JWT (optional for MVP)

- **Method**: POST
- **Path**: `/trip/classify`
- **Lambda Function**: `odessey-classify`
- **Authorization**: Cognito JWT (optional for MVP)

- **Method**: POST
- **Path**: `/trip/eta`
- **Lambda Function**: `odessey-eta`
- **Authorization**: Cognito JWT (optional for MVP)

- **Method**: POST
- **Path**: `/trip/plan`
- **Lambda Function**: `odessey-plan`
- **Authorization**: Cognito JWT (optional for MVP)

- **Method**: POST
- **Path**: `/trip/save`
- **Lambda Function**: `odessey-save`
- **Authorization**: Cognito JWT (optional for MVP)

- **Method**: GET
- **Path**: `/trip/{tripId}`
- **Lambda Function**: `odessey-get-trip`
- **Authorization**: Cognito JWT (optional for MVP)

## Step-by-Step Configuration

### 1. Open API Gateway Console
1. Go to **API Gateway** in AWS Console
2. Select your API: `odessey-api`
3. Click **Routes** in the left sidebar

### 2. Create Routes

For each route:

1. Click **Create**
2. Select **Lambda** integration
3. Choose the appropriate Lambda function
4. Configure path parameters if needed (e.g., `{tripId}`)
5. Click **Create**

### 3. Configure CORS (if needed)
1. Select a route
2. Click **Actions** → **Enable CORS**
3. Configure:
   - **Access-Control-Allow-Origin**: `*`
   - **Access-Control-Allow-Headers**: `Content-Type,X-Amz-Date,Authorization,X-Api-Key`
   - **Access-Control-Allow-Methods**: `GET,POST,PUT,DELETE,OPTIONS`

### 4. Deploy API
1. Click **Actions** → **Deploy API**
2. Select **New Stage**: `prod`
3. Click **Deploy**

## Testing Routes

### 1. Get API URL
After deployment, note the **Invoke URL** from the API Gateway console.

### 2. Test Health Endpoint
```bash
curl -X GET https://your-api-id.execute-api.us-east-2.amazonaws.com/prod/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "odessey-backend"
}
```

### 3. Test Authentication
```bash
# Signup
curl -X POST https://your-api-id.execute-api.us-east-2.amazonaws.com/prod/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123"}'

# Login
curl -X POST https://your-api-id.execute-api.us-east-2.amazonaws.com/prod/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "TestPass123"}'
```

### 4. Test Trip Flow
```bash
# Initialize trip
curl -X POST https://your-api-id.execute-api.us-east-2.amazonaws.com/prod/trip/init \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "startLocation": "Times Square, New York",
    "startTime": "2024-01-15T09:00:00Z",
    "endTime": "2024-01-15T18:00:00Z",
    "mode": "driving",
    "stops": ["Central Park", "Brooklyn Bridge", "Statue of Liberty"]
  }'
```

## Environment Variables for Lambda Functions

Make sure each Lambda function has these environment variables set:

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

## Troubleshooting

### Common Issues

1. **Lambda function not found**
   - Ensure Lambda functions are deployed
   - Check function names match exactly

2. **CORS errors**
   - Enable CORS on API Gateway
   - Check preflight OPTIONS requests

3. **Authorization errors**
   - Verify JWT tokens are valid
   - Check Cognito configuration

4. **Environment variable errors**
   - Verify all required env vars are set
   - Check AWS region consistency

### Monitoring

1. **CloudWatch Logs**
   - Each Lambda function creates log groups
   - Check `/aws/lambda/odessey-*` log groups

2. **API Gateway Logs**
   - Enable execution logging
   - Monitor request/response patterns

3. **X-Ray Tracing** (Optional)
   - Enable for detailed request tracing
   - Helps debug performance issues

## Next Steps

1. Test all endpoints individually
2. Implement proper error handling
3. Add rate limiting if needed
4. Set up monitoring and alerting
5. Configure custom domain (optional)
