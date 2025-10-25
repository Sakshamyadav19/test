"""Classify POIs handler."""

import json
import os
import boto3
from src.models.dto import TripIdOnly, ClassifiedStop, ClassifyResponse
from src.models.dynamo import TripState
from src.services.bedrock import get_bedrock_service
from src.utils.auth import lambda_response, get_auth_service, lambda_handler_decorator, validate_trip_ownership
from src.utils.errors import ValidationError, NotFoundError
from src.utils.logger import info, error


dynamodb = boto3.resource("dynamodb", region_name=os.getenv("AWS_REGION", "us-west-2"))
trip_states_table = dynamodb.Table(os.getenv("TRIP_STATES_TABLE_NAME", "TripStates"))


@lambda_handler_decorator
def handler(event, context):
    """
    Classify POIs with LLM.
    
    POST /trip/classify
    Body: {tripId}
    
    Returns:
        ClassifyResponse with classified stops
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
        
        # Classify each stop using Bedrock
        bedrock_service = get_bedrock_service()
        classified_stops = []
        
        for geocoded in trip_state.geocodedStops:
            try:
                classification = bedrock_service.classify_poi(
                    name=geocoded["name"],
                    lat=geocoded["lat"],
                    lon=geocoded["lon"]
                )
                
                classified_stop = {
                    "name": geocoded["name"],
                    "lat": geocoded["lat"],
                    "lon": geocoded["lon"],
                    "category": classification["category"],
                    "bestTimeWindow": classification["bestTimeWindow"],
                    "reason": classification["reason"],
                    "stayMin": classification.get("stayMin", 45)
                }
                classified_stops.append(classified_stop)
            
            except Exception as e:
                error(f"Failed to classify '{geocoded['name']}': {str(e)}")
                # Skip this stop
                continue
        
        # Update trip state
        trip_state.classifiedStops = classified_stops
        trip_states_table.put_item(Item=trip_state.to_item())
        
        info(f"Classified {len(classified_stops)} stops for trip: {trip_req.tripId}")
        
        return lambda_response(200, {
            "tripId": trip_req.tripId,
            "classifiedStops": classified_stops
        })
    
    except ValidationError as e:
        return lambda_response(400, {"error": e.message, "code": e.code})
    except NotFoundError as e:
        return lambda_response(404, {"error": e.message, "code": e.code})
    except Exception as e:
        error(f"Classify error: {str(e)}")
        return lambda_response(500, {"error": "Failed to classify stops", "code": "INTERNAL_ERROR"})

