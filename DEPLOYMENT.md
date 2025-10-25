# Deployment Guide

This document provides step-by-step instructions for deploying the Odessey backend.

## Prerequisites

1. **AWS Account** with appropriate credentials configured
2. **Python 3.12+** installed
3. **AWS CDK** installed: `npm install -g aws-cdk`
4. **Dependencies** installed: `pip install -r requirements.txt`

## Environment Setup

1. **Copy environment template:**
```bash
cp .env.template .env
```

2. **Edit `.env` file** with your AWS credentials and configuration:
```bash
AWS_REGION=us-west-2
AWS_ACCOUNT_ID=123456789012
INRIX_API_KEY=your-inrix-key-here
```

## AWS Resources Setup

### 1. Create Amazon Location Place Index

You need to create a Place Index for geocoding:

```bash
aws location create-place-index \
  --region us-west-2 \
  --index-name odessey-place-index \
  --data-source Esri
```

### 2. Store INRIX API Key in Secrets Manager

The CDK will create a secret, but you need to populate it:

```bash
aws secretsmanager put-secret-value \
  --region us-west-2 \
  --secret-id odessey-inrix-api-key \
  --secret-string '{"INRIX_API_KEY":"your-key-here"}'
```

## Deploy Infrastructure

1. **Bootstrap CDK (first time only):**
```bash
cdk bootstrap
```

2. **Deploy all stacks:**
```bash
cdk deploy --all
```

This will create:
- DynamoDB tables (Users, Trips, TripStates)
- Cognito User Pool and Client
- API Gateway with all Lambda functions
- Secrets Manager secret for INRIX

3. **Get API Gateway URL:**
After deployment, note the API Gateway URL from the CDK outputs.

## Update Environment Variables

After deployment, update your `.env` with actual values:

```bash
COGNITO_USER_POOL_ID=us-west-2_xxxxx
COGNITO_CLIENT_ID=xxxxxxxxxxxxx
API_GATEWAY_URL=https://xxxxx.execute-api.us-west-2.amazonaws.com/prod
INRIX_SECRET_ARN=arn:aws:secretsmanager:us-west-2:xxxxx:secret:odessey-inrix-api-key-xxxxx
```

## Testing

### 1. Health Check

```bash
curl https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/health
```

### 2. Sign Up

```bash
curl -X POST https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'
```

### 3. Login

```bash
curl -X POST https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123!"}'
```

Save the `accessToken` from the response.

### 4. Initialize Trip

```bash
curl -X POST https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/trip/init \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{
    "startLocation":"Union Square, San Francisco",
    "startTime":"2025-10-25T11:00:00-07:00",
    "endTime":"2025-10-25T18:00:00-07:00",
    "mode":"drive",
    "stops":["SFMOMA", "Pier 39", "Golden Gate Bridge"]
  }'
```

Save the `tripId` from the response.

### 5. Classify Stops

```bash
curl -X POST https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/trip/classify \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"tripId":"t_xxxxx"}'
```

### 6. Build ETA Matrix

```bash
curl -X POST https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/trip/eta \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"tripId":"t_xxxxx"}'
```

### 7. Plan Itinerary

```bash
curl -X POST https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/trip/plan \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"tripId":"t_xxxxx"}'
```

### 8. Save Trip

```bash
curl -X POST https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/trip/save \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -d '{"tripId":"t_xxxxx","title":"SF Day Trip"}'
```

### 9. Get Saved Trip

```bash
curl https://your-api-id.execute-api.us-west-2.amazonaws.com/prod/trip/t_xxxxx \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Troubleshooting

### Lambda Timeout
- Increase timeout in `infra/stacks/api_stack.py`
- Check CloudWatch logs for specific errors

### Geocoding Failures
- Verify Amazon Location Place Index exists
- Check IAM permissions for Geo permissions

### INRIX API Errors
- Verify INRIX API key is set in Secrets Manager
- Check INRIX API quota/limits
- Fallback mechanism should use distance-based estimates

### Bedrock Access
- Ensure Bedrock model access is granted in your AWS account
- Check IAM permissions for Bedrock

## Cleanup

To remove all resources:

```bash
cdk destroy --all
```

Note: This will NOT delete the INRIX secret - you must delete it manually:

```bash
aws secretsmanager delete-secret --region us-west-2 --secret-id odessey-inrix-api-key
```

## Notes

- The `.env` file should not be committed to git (already in `.gitignore`)
- All secrets are stored in AWS Secrets Manager
- API Gateway uses Cognito authorizer for protected endpoints
- DynamoDB tables use PAY_PER_REQUEST billing mode

