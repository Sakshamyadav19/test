"""Initialize trip draft handler."""

import json
import os
import boto3
from src.models.dto import InitRequest, InitResponse, TripIdOnly
from src.models.dynamo import TripState
from src.services.geocode import get_geocode_service
from src.services.time_utils import calculate_trip_duration_minutes
from src.utils.auth import lambda_response, get_auth_service, lambda_handler_decorator
from src.utils.errors import ValidationError
from src.utils.logger import info, error


dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-west-2"))
trip_states_table = dynamodb.Table(os.getenv("TRIP_STATES_TABLE_NAME", "TripStates"))


@lambda_handler_decorator
def handler(event, context):
    """
    Initialize a new trip draft.
    
    POST /trip/init
    Body: InitRequest
    
    Returns:
        InitResponse with tripId and duration
    """
    try:
        body = json.loads(event.get("body", "{}"))
        
        # Validate request
        init_req = InitRequest(**body)
        
        # Extract user ID from event
        auth_service = get_auth_service()
        user_id = auth_service.extract_user_from_event(event)
        
        if not user_id:
            return lambda_response(401, {"error": "Unauthorized", "code": "UNAUTHORIZED"})
        
        # Geocode start location
        geocode_service = get_geocode_service()
        start_coords = geocode_service.geocode_address(init_req.startLocation)
        
        # Geocode all stops in parallel
        geocoded_stops = []
        for stop_name in init_req.stops:
            try:
                coords = geocode_service.geocode_address(stop_name)
                geocoded_stops.append({
                    "name": stop_name,
                    "lat": coords["lat"],
                    "lon": coords["lon"]
                })
            except Exception as e:
                error(f"Failed to geocode stop '{stop_name}': {str(e)}")
                return lambda_response(400, {
                    "error": f"Could not geocode stop: {stop_name}",
                    "code": "GEOCODE_ERROR",
                    "badStopNames": [stop_name]
                })
        
        # Calculate trip duration
        duration_minutes = calculate_trip_duration_minutes(init_req.startTime, init_req.endTime)
        
        # Generate trip ID
        trip_id = TripState.generate_id()
        
        # Create trip state
        trip_state = TripState(
            tripId=trip_id,
            userId=user_id,
            startLocation=init_req.startLocation,
            startTime=init_req.startTime,
            endTime=init_req.endTime,
            mode=init_req.mode,
            rawStops=init_req.stops,
            geocodedStops=geocoded_stops
        )
        
        # Store in DynamoDB
        trip_states_table.put_item(Item=trip_state.to_item())
        
        info(f"Initialized trip: {trip_id}")
        
        return lambda_response(200, {
            "tripId": trip_id,
            "tripDurationMinutes": duration_minutes,
            "message": "Trip initialized successfully"
        })
    
    except ValidationError as e:
        return lambda_response(400, {"error": e.message, "code": e.code})
    except Exception as e:
        error(f"Init trip error: {str(e)}")
        return lambda_response(500, {"error": "Failed to initialize trip", "code": "INTERNAL_ERROR"})

