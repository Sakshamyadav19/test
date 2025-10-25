"""Itinerary validation logic."""

from datetime import datetime
from typing import Dict, List, Tuple
import pytz

from src.utils.logger import warning, error
from src.utils.errors import ValidationError


def validate_itinerary(
    itinerary: List[Dict],
    known_stops: List[Dict],
    start_time_iso: str,
    end_time_iso: str
) -> Tuple[bool, str]:
    """
    Validate itinerary against known stops and time constraints.
    
    Args:
        itinerary: Generated itinerary items
        known_stops: Known stops with coordinates
        start_time_iso: Start time ISO8601
        end_time_iso: End time ISO8601
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not itinerary:
        return False, "Itinerary is empty"
    
    if not known_stops:
        return False, "No known stops to validate against"
    
    # Parse time bounds
    try:
        start_dt = datetime.fromisoformat(start_time_iso.replace('Z', '+00:00'))
        if start_dt.tzinfo is None:
            start_dt = pytz.UTC.localize(start_dt)
        
        end_dt = datetime.fromisoformat(end_time_iso.replace('Z', '+00:00'))
        if end_dt.tzinfo is None:
            end_dt = pytz.UTC.localize(end_dt)
    except Exception as e:
        return False, f"Invalid time format: {str(e)}"
    
    # Create map of known stops by name
    known_map = {stop["name"]: stop for stop in known_stops}
    
    # Track visited stops
    visited_names = set()
    
    # Validate each itinerary item
    last_arrival_dt = None
    
    for i, item in enumerate(itinerary):
        # Check required fields
        if not all(k in item for k in ["spot", "lat", "lon", "arrival"]):
            return False, f"Itinerary item {i} missing required fields"
        
        # Validate coordinates match known stops
        spot_name = item["spot"]
        if spot_name not in known_map:
            warning(f"Spot '{spot_name}' not in known stops")
        
        known_stop = known_map.get(spot_name)
        if known_stop:
            expected_lat = known_stop["lat"]
            expected_lon = known_stop["lon"]
            
            # Allow small tolerance for floating point
            if abs(item["lat"] - expected_lat) > 0.0001:
                return False, f"Coordinates mismatch for '{spot_name}': lat {item['lat']} != {expected_lat}"
            if abs(item["lon"] - expected_lon) > 0.0001:
                return False, f"Coordinates mismatch for '{spot_name}': lon {item['lon']} != {expected_lon}"
        
        # Check for duplicates
        if spot_name in visited_names:
            return False, f"Duplicate stop in itinerary: '{spot_name}'"
        visited_names.add(spot_name)
        
        # Validate arrival time format and within bounds
        try:
            arrival_str = item["arrival"]
            arrival_dt = _parse_arrival_time(arrival_str, start_dt, end_dt)
            
            # Check if time is within window
            if arrival_dt < start_dt or arrival_dt > end_dt:
                return False, f"Arrival time {arrival_str} outside time window"
            
            # Check monotonic (arrival times should be increasing)
            if last_arrival_dt and arrival_dt < last_arrival_dt:
                return False, f"Arrival times not monotonic: {arrival_str} before previous"
            
            last_arrival_dt = arrival_dt
        
        except Exception as e:
            return False, f"Invalid arrival time '{item['arrival']}': {str(e)}"
    
    # Check all stops are visited
    known_names = set(known_map.keys())
    missing = known_names - visited_names
    if missing:
        warning(f"Not all stops visited: {missing}")
        # Note: This is a warning, not an error, as planner may skip some stops
    
    return True, ""


def _parse_arrival_time(arrival_str: str, start_dt: datetime, end_dt: datetime) -> datetime:
    """
    Parse arrival time string into datetime.
    
    Args:
        arrival_str: HH:MM format string
        start_dt: Start datetime for reference
        end_dt: End datetime for reference
    
    Returns:
        Parsed datetime
    """
    try:
        # Parse HH:MM
        hour, minute = map(int, arrival_str.split(":"))
        
        # Use same date/timezone as start
        arrival_dt = start_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return arrival_dt
    
    except Exception as e:
        raise ValueError(f"Failed to parse arrival time: {str(e)}")


def recompute_finish_by(itinerary: List[Dict], stay_minutes: int = 45) -> str:
    """
    Recompute finish time from itinerary.
    
    Args:
        itinerary: Itinerary items
        stay_minutes: Stay duration per stop (default 45 min)
    
    Returns:
        Finish time as HH:MM string
    """
    if not itinerary:
        return "00:00"
    
    last_item = itinerary[-1]
    
    try:
        # Parse last arrival time
        last_arrival_str = last_item["arrival"]
        hour, minute = map(int, last_arrival_str.split(":"))
        
        # Add stay duration
        total_minutes = hour * 60 + minute + stay_minutes
        finish_hour = (total_minutes // 60) % 24
        finish_minute = total_minutes % 60
        
        return f"{finish_hour:02d}:{finish_minute:02d}"
    
    except Exception as e:
        error(f"Failed to recompute finish time: {str(e)}")
        return last_item["arrival"]

