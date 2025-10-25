"""Health check handler."""

import json


def lambda_handler(event, context):
    """
    Health check endpoint.
    
    Returns:
        API Gateway response with 200 status
    """
    return {
        "statusCode": 200,
        "headers": {
            "Content-Type": "application/json"
        },
        "body": json.dumps({
            "status": "healthy",
            "service": "odessey-backend"
        })
    }
