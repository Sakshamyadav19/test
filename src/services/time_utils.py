"""Timezone and time conversion utilities."""

from datetime import datetime, timedelta
from typing import List
import pytz
from timezonefinder import TimezoneFinder

from src.utils.logger import warning


def get_timezone_from_coords(lat: float, lon: float) -> str:
    """
    Get timezone string from coordinates.
    
    Args:
        lat: Latitude
        lon: Longitude
    
    Returns:
        Timezone string (e.g., "America/Los_Angeles")
    """
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    
    if not tz_name:
        warning(f"Could not determine timezone for {lat}, {lon}, defaulting to UTC")
        return "UTC"
    
    return tz_name


def iso_to_local_hhmm(iso_str: str, tz_name: str) -> str:
    """
    Convert ISO8601 datetime to local HH:MM string.
    
    Args:
        iso_str: ISO8601 datetime string
        tz_name: Target timezone name
    
    Returns:
        HH:MM format string
    """
    try:
        # Parse ISO string (may or may not have timezone info)
        if 'T' in iso_str:
            dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        else:
            dt = datetime.fromisoformat(iso_str)
        
        # If datetime is naive, assume UTC
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        # Convert to target timezone
        target_tz = pytz.timezone(tz_name)
        local_dt = dt.astimezone(target_tz)
        
        # Format as HH:MM
        return local_dt.strftime("%H:%M")
    
    except Exception as e:
        warning(f"Failed to convert ISO to local time: {str(e)}")
        return "00:00"


def generate_time_bins(start_iso: str, end_iso: str, interval_min: int = 30) -> List[str]:
    """
    Generate time bins from start to end time.
    
    Args:
        start_iso: Start time ISO8601 string
        end_iso: End time ISO8601 string
        interval_min: Interval in minutes (default 30)
    
    Returns:
        List of time strings in HH:MM format
    """
    # Parse start and end times
    start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
    if start_dt.tzinfo is None:
        start_dt = pytz.UTC.localize(start_dt)
    
    end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
    if end_dt.tzinfo is None:
        end_dt = pytz.UTC.localize(end_dt)
    
    # Generate bins
    bins = []
    current = start_dt
    
    while current <= end_dt:
        bins.append(current.strftime("%H:%M"))
        current += timedelta(minutes=interval_min)
    
    return bins


def parse_time_range(time_range_str: str) -> tuple[str, str]:
    """
    Parse time range string (e.g., "17:00–19:00") into start and end times.
    
    Args:
        time_range_str: Time range string
    
    Returns:
        Tuple of (start_time, end_time)
    """
    # Handle various separators
    for sep in ['–', '-', '—', 'to']:
        if sep in time_range_str:
            parts = time_range_str.split(sep)
            if len(parts) == 2:
                return parts[0].strip(), parts[1].strip()
    
    # If no separator, assume single time
    return time_range_str.strip(), time_range_str.strip()


def calculate_trip_duration_minutes(start_iso: str, end_iso: str) -> int:
    """
    Calculate trip duration in minutes.
    
    Args:
        start_iso: Start time ISO8601 string
        end_iso: End time ISO8601 string
    
    Returns:
        Duration in minutes
    """
    start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
    if start_dt.tzinfo is None:
        start_dt = pytz.UTC.localize(start_dt)
    
    end_dt = datetime.fromisoformat(end_iso.replace('Z', '+00:00'))
    if end_dt.tzinfo is None:
        end_dt = pytz.UTC.localize(end_dt)
    
    duration = end_dt - start_dt
    return int(duration.total_seconds() / 60)

