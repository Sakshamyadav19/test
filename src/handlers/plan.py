"""Plan itinerary handler."""

import json
import os
import boto3
from src.models.dto import TripIdOnly, ItineraryItem, PlanResponse
from src.models.dynamo import TripState
from src.services.bedrock import get_bedrock_service
from src.services.time_utils import get_timezone_from_coords
from src.services.validate import validate_itinerary, recompute_finish_by
from src.utils.auth import lambda_response, get_auth_service, lambda_handler_decorator, validate_trip_ownership
from src.utils.errors import ValidationError, NotFoundError
from src.utils.logger import info, error


dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-west-2"))
trip_states_table = dynamodb.Table(os.getenv("TRIP_STATES_TABLE_NAME", "TripStates"))


@lambda_handler_decorator
def handler(event, context):
    """
    Generate final itinerary using LLM.
    
    POST /trip/plan
    Body: {tripId}
    
    Returns:
        PlanResponse with final itinerary
    """
    try:
        body = json.loads(event.get("body", "{}"))
        trip_req = TripIdOnly(**body)
        
        # Extract user ID
        auth_service = get_auth_service()
        user_id = auth_service.extract_user_from_event(event)
        
        if not user_id:
            return lambda_response(401, {"error": "Unauthorized", "code": "UNAUTHORIZED"})
        
        # Load trip state
        response = trip_states_table.get_item(Key={"tripId": trip_req.tripId})
        
        if "Item" not in response:
            return lambda_response(404, {"error": "Trip not found", "code": "NOT_FOUND"})
        
        trip_state = TripState.from_item(response["Item"])
        
        # Validate ownership
        validate_trip_ownership(trip_state.userId, user_id)
        
        if not trip_state.classifiedStops:
            return lambda_response(400, {"error": "Classified stops not found", "code": "VALIDATION_ERROR"})
        
        if not trip_state.etaMatrix:
            return lambda_response(400, {"error": "ETA matrix not found", "code": "VALIDATION_ERROR"})
        
        # Get timezone from start location
        start_coords = trip_state.start_coords
        if not start_coords:
            return lambda_response(400, {"error": "Start coordinates not found", "code": "VALIDATION_ERROR"})
        
        timezone = get_timezone_from_coords(start_coords["lat"], start_coords["lon"])
        
        # Call Bedrock to plan itinerary
        bedrock_service = get_bedrock_service()
        
        planned = bedrock_service.plan_itinerary(
            start_time_iso=trip_state.startTime,
            end_time_iso=trip_state.endTime,
            mode=trip_state.mode,
            start_point=start_coords,
            classified_stops=trip_state.classifiedStops,
            eta_matrix=trip_state.etaMatrix,
            incidents=trip_state.incidents,
            timezone=timezone
        )
        
        # Validate itinerary
        is_valid, error_msg = validate_itinerary(
            itinerary=planned.get("itinerary", []),
            known_stops=trip_state.classifiedStops,
            start_time_iso=trip_state.startTime,
            end_time_iso=trip_state.endTime
        )
        
        if not is_valid:
            error(f"Itinerary validation failed: {error_msg}")
            # Try to fix finish time anyway
            if "itinerary" in planned:
                planned["finishBy"] = recompute_finish_by(planned["itinerary"])
        
        # Recompute finishBy server-side
        if "itinerary" in planned:
            planned["finishBy"] = recompute_finish_by(planned["itinerary"])
        
        # Store final itinerary in trip state
        trip_state.finalItinerary = planned
        trip_states_table.put_item(Item=trip_state.to_item())
        
        info(f"Generated itinerary for trip: {trip_req.tripId}")
        
        return lambda_response(200, {
            "tripId": trip_req.tripId,
            "order": planned.get("order", []),
            "itinerary": planned.get("itinerary", []),
            "totalTravelMinutes": planned.get("totalTravelMinutes", 0),
            "confidence": planned.get("confidence", "Medium"),
            "finishBy": planned.get("finishBy", "00:00")
        })
    
    except ValidationError as e:
        return lambda_response(400, {"error": e.message, "code": e.code})
    except NotFoundError as e:
        return lambda_response(404, {"error": e.message, "code": e.code})
    except Exception as e:
        error(f"Plan error: {str(e)}")
        return lambda_response(500, {"error": "Failed to plan itinerary", "code": "INTERNAL_ERROR"})

