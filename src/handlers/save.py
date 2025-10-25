"""Save trip handler."""

import json
import os
import boto3
from src.models.dto import SaveRequest, SaveResponse
from src.models.dynamo import TripState, Trip
from src.utils.auth import lambda_response, get_auth_service, lambda_handler_decorator, validate_trip_ownership
from src.utils.errors import ValidationError, NotFoundError
from src.utils.logger import info, error


dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-west-2"))
trip_states_table = dynamodb.Table(os.getenv("TRIP_STATES_TABLE_NAME", "TripStates"))
trips_table = dynamodb.Table(os.getenv("TRIPS_TABLE_NAME", "Trips"))


@lambda_handler_decorator
def handler(event, context):
    """
    Save finalized itinerary.
    
    POST /trip/save
    Body: {tripId, title}
    
    Returns:
        SaveResponse with confirmation
    """
    try:
        body = json.loads(event.get("body", "{}"))
        save_req = SaveRequest(**body)
        
        # Extract user ID
        auth_service = get_auth_service()
        user_id = auth_service.extract_user_from_event(event)
        
        if not user_id:
            return lambda_response(401, {"error": "Unauthorized", "code": "UNAUTHORIZED"})
        
        # Load trip state
        response = trip_states_table.get_item(Key={"tripId": save_req.tripId})
        
        if "Item" not in response:
            return lambda_response(404, {"error": "Trip not found", "code": "NOT_FOUND"})
        
        trip_state = TripState.from_item(response["Item"])
        
        # Validate ownership
        validate_trip_ownership(trip_state.userId, user_id)
        
        # Get final itinerary
        if not trip_state.finalItinerary:
            return lambda_response(400, {"error": "Final itinerary not found. Please run /trip/plan first", "code": "VALIDATION_ERROR"})
        
        final_itinerary = trip_state.finalItinerary
        
        # Create trip entity
        trip = Trip(
            tripId=save_req.tripId,
            userId=user_id,
            title=save_req.title,
            startTime=trip_state.startTime,
            endTime=trip_state.endTime,
            mode=trip_state.mode,
            startLocation=trip_state.startLocation,
            itinerary=final_itinerary.get("itinerary", []),
            order=final_itinerary.get("order", []),
            finishBy=final_itinerary.get("finishBy", "00:00"),
            totalTravelMinutes=final_itinerary.get("totalTravelMinutes", 0),
            confidence=final_itinerary.get("confidence", "Medium")
        )
        
        # Save to Trips table
        trips_table.put_item(Item=trip.to_item())
        
        info(f"Saved trip: {save_req.tripId}")
        
        return lambda_response(200, {
            "tripId": save_req.tripId,
            "message": "Trip saved successfully"
        })
    
    except ValidationError as e:
        return lambda_response(400, {"error": e.message, "code": e.code})
    except NotFoundError as e:
        return lambda_response(404, {"error": e.message, "code": e.code})
    except Exception as e:
        error(f"Save error: {str(e)}")
        return lambda_response(500, {"error": "Failed to save trip", "code": "INTERNAL_ERROR"})

