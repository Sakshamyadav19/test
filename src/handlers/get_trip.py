"""Get saved trip handler."""

import os
import boto3
from src.models.dynamo import Trip
from src.utils.auth import lambda_response, get_auth_service, lambda_handler_decorator, validate_trip_ownership
from src.utils.errors import NotFoundError
from src.utils.logger import info, error


dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-west-2"))
trips_table = dynamodb.Table(os.getenv("TRIPS_TABLE_NAME", "Trips"))


@lambda_handler_decorator
def handler(event, context):
    """
    Get a saved itinerary.
    
    GET /trip/{tripId}
    
    Returns:
        PlanResponse with saved itinerary
    """
    try:
        trip_id = event.get("pathParameters", {}).get("tripId")
        
        if not trip_id:
            return lambda_response(400, {"error": "tripId is required", "code": "VALIDATION_ERROR"})
        
        # Extract user ID
        auth_service = get_auth_service()
        user_id = auth_service.extract_user_from_event(event)
        
        if not user_id:
            return lambda_response(401, {"error": "Unauthorized", "code": "UNAUTHORIZED"})
        
        # Fetch from Trips table
        response = trips_table.get_item(Key={"tripId": trip_id})
        
        if "Item" not in response:
            return lambda_response(404, {"error": "Trip not found", "code": "NOT_FOUND"})
        
        trip = Trip.from_item(response["Item"])
        
        # Validate ownership
        validate_trip_ownership(trip.userId, user_id)
        
        info(f"Retrieved trip: {trip_id}")
        
        return lambda_response(200, {
            "tripId": trip.tripId,
            "order": trip.order,
            "itinerary": trip.itinerary,
            "totalTravelMinutes": trip.totalTravelMinutes,
            "confidence": trip.confidence,
            "finishBy": trip.finishBy
        })
    
    except NotFoundError as e:
        return lambda_response(404, {"error": e.message, "code": e.code})
    except Exception as e:
        error(f"Get trip error: {str(e)}")
        return lambda_response(500, {"error": "Failed to retrieve trip", "code": "INTERNAL_ERROR"})

