"""Build ETA matrix handler."""

import json
import os
import boto3
from src.models.dto import TripIdOnly
from src.models.dynamo import TripState
from src.services.inrix import get_inrix_client
from src.services.time_utils import get_timezone_from_coords
from src.utils.auth import lambda_response, get_auth_service, lambda_handler_decorator, validate_trip_ownership
from src.utils.errors import ValidationError, NotFoundError
from src.utils.logger import info, error


dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-west-2"))
trip_states_table = dynamodb.Table(os.getenv("TRIP_STATES_TABLE_NAME", "TripStates"))


@lambda_handler_decorator
def handler(event, context):
    """
    Build INRIX ETA matrix and incidents.
    
    POST /trip/eta
    Body: {tripId}
    
    Returns:
        EtaResponse with matrix and incidents
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
        
        # Build ETA matrix using INRIX
        inrix_client = get_inrix_client()
        
        # Extract start coords
        start_coords = trip_state.start_coords
        if not start_coords:
            return lambda_response(400, {"error": "Start coordinates not found", "code": "VALIDATION_ERROR"})
        
        # Extract stop coords
        stops_coords = [{"name": stop["name"], "lat": stop["lat"], "lon": stop["lon"]} 
                       for stop in trip_state.classifiedStops]
        
        # Build ETA matrix
        eta_matrix = inrix_client.build_eta_matrix(
            start_coords=start_coords,
            stops_coords=stops_coords,
            start_time_iso=trip_state.startTime,
            end_time_iso=trip_state.endTime,
            mode=trip_state.mode
        )
        
        # Get incidents (simplified - would need bbox)
        incidents = []
        try:
            # Calculate rough bbox from coordinates
            lats = [stop["lat"] for stop in stops_coords] + [start_coords["lat"]]
            lons = [stop["lon"] for stop in stops_coords] + [start_coords["lon"]]
            
            bbox = (min(lats), min(lons), max(lats), max(lons))
            time_window = (trip_state.startTime, trip_state.endTime)
            
            incidents = inrix_client.get_incidents(bbox, time_window)
        except Exception as e:
            error(f"Failed to fetch incidents: {str(e)}")
        
        # Update trip state
        trip_state.etaMatrix = eta_matrix
        trip_state.incidents = incidents
        trip_states_table.put_item(Item=trip_state.to_item())
        
        info(f"Built ETA matrix for trip: {trip_req.tripId}")
        
        return lambda_response(200, {
            "tripId": trip_req.tripId,
            "etaMatrix": eta_matrix,
            "incidents": incidents
        })
    
    except ValidationError as e:
        return lambda_response(400, {"error": e.message, "code": e.code})
    except NotFoundError as e:
        return lambda_response(404, {"error": e.message, "code": e.code})
    except Exception as e:
        error(f"ETA error: {str(e)}")
        return lambda_response(500, {"error": "Failed to build ETA matrix", "code": "INTERNAL_ERROR"})

