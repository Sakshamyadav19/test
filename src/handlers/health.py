"""Health check handler."""

from src.utils.auth import lambda_response


def handler(event, context):
    """
    Health check endpoint.
    
    Returns:
        API Gateway response with 200 status
    """
    return lambda_response(200, {
        "status": "healthy",
        "service": "odessey-backend"
    })

