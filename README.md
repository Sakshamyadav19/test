# Odessey Backend - Serverless Itinerary Planner

A serverless AWS backend for an LLM-driven single-day itinerary planner.

## Architecture

- **API Gateway (HTTP)** → **Lambdas** per endpoint
- **DynamoDB**: Users, Trips, TripStates tables
- **Amazon Location Service**: Geocoding
- **INRIX APIs**: Future-aware ETAs + incidents
- **Amazon Bedrock**: LLM for POI classification and itinerary planning
- **Cognito**: Authentication
- **Secrets Manager**: API keys and credentials

## Project Structure

```
odessey_backend/
├── .env                          # AWS credentials, INRIX keys, config
├── requirements.txt              # Python dependencies
├── cdk.json                     # CDK configuration
├── app.py                       # CDK app entry point
├── infra/                       # Infrastructure (CDK)
│   └── stacks/
│       ├── dynamo_stack.py      # DynamoDB tables
│       ├── auth_stack.py        # Cognito User Pool
│       └── api_stack.py         # API Gateway + Lambda integrations
└── src/
    ├── handlers/                 # Lambda function handlers
    ├── services/                 # Business logic services
    ├── models/                   # Data models
    └── utils/                    # Utilities
```

## Setup

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Configure environment:**
```bash
cp .env.template .env
# Edit .env with your AWS credentials and configuration
```

3. **Bootstrap CDK (first time only):**
```bash
cdk bootstrap
```

4. **Deploy infrastructure:**
```bash
cdk deploy --all
```

## API Endpoints

- `GET /health` - Health check
- `POST /auth/signup` - User signup
- `POST /auth/login` - User login
- `POST /trip/init` - Initialize trip draft
- `POST /trip/classify` - Classify POIs
- `POST /trip/eta` - Build ETA matrix
- `POST /trip/plan` - Generate final itinerary
- `POST /trip/save` - Save itinerary
- `GET /trip/{tripId}` - Get saved itinerary

## Local Development

The API Gateway URL will be output after deployment. Use this URL to make API requests.

## Post-Deployment Configuration

1. Store INRIX_API_KEY in AWS Secrets Manager
2. Create Amazon Location Place Index
3. Update .env with actual ARNs and IDs

