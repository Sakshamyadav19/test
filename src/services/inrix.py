"""INRIX API client for ETA and incidents."""

import os
import time
import math
import requests
import pytz
from typing import Dict, List, Optional
from datetime import datetime

from src.utils.logger import info, error, warning
from src.utils.errors import ExternalServiceError
from src.utils.secrets import get_secrets_manager


class InrixClient:
    """Client for INRIX API."""
    
    def __init__(self):
        self.base_url = os.getenv("INRIX_BASE_URL", "https://api.inrix.com/v1")
        self.secrets_manager = get_secrets_manager()
        self._api_key = None
    
    @property
    def api_key(self) -> str:
        """Get INRIX API key from Secrets Manager."""
        if self._api_key is None:
            self._api_key = self.secrets_manager.get_inrix_api_key()
            if not self._api_key:
                # Fallback to environment variable
                self._api_key = os.getenv("INRIX_API_KEY")
        
        if not self._api_key:
            raise ExternalServiceError("INRIX_API_KEY not found in Secrets Manager or environment")
        
        return self._api_key
    
    def get_predicted_eta(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        departure_time_iso: str,
        mode: str = "drive"
    ) -> Dict[str, float]:
        """
        Get predicted ETA between two points.
        
        Args:
            origin_lat: Origin latitude
            origin_lon: Origin longitude
            dest_lat: Destination latitude
            dest_lon: Destination longitude
            departure_time_iso: Departure time (ISO8601)
            mode: Transport mode (drive/walk/mix)
        
        Returns:
            Dictionary with meanMinutes, p80Minutes, incidentsCount
        """
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Call INRIX route API
                url = f"{self.base_url}/routing/route"
                params = {
                    "origin": f"{origin_lat},{origin_lon}",
                    "destination": f"{dest_lat},{dest_lon}",
                    "departureTime": departure_time_iso,
                    "provider": "inrix" if mode == "drive" else "here",
                    "region": "us"
                }
                
                headers = {
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
                
                response = requests.get(url, params=params, headers=headers, timeout=10)
                response.raise_for_status()
                
                data = response.json()
                
                # Parse INRIX response
                route = data.get("routes", [{}])[0]
                legs = route.get("legs", [])
                
                if not legs:
                    raise ExternalServiceError("No route legs returned from INRIX")
                
                # Sum up durations from all legs
                total_duration = 0
                total_incidents = 0
                
                for leg in legs:
                    duration = leg.get("duration", {}).get("value", 0)
                    total_duration += duration
                    total_incidents += len(leg.get("incidents", []))
                
                # Convert seconds to minutes
                mean_minutes = total_duration / 60
                # Estimate p80 (assuming 20% buffer for traffic)
                p80_minutes = mean_minutes * 1.2
                
                return {
                    "meanMinutes": mean_minutes,
                    "p80Minutes": p80_minutes,
                    "incidentsCount": total_incidents
                }
            
            except requests.RequestException as e:
                if attempt < max_retries - 1:
                    warning(f"INRIX API call failed (attempt {attempt + 1}): {str(e)}, retrying...")
                    time.sleep(retry_delay)
                else:
                    error(f"INRIX API call failed after {max_retries} attempts: {str(e)}")
                    # Return fallback estimate
                    return self._fallback_eta(origin_lat, origin_lon, dest_lat, dest_lon, mode)
        
        return self._fallback_eta(origin_lat, origin_lon, dest_lat, dest_lon, mode)
    
    def get_incidents(self, bbox: tuple, time_window: tuple) -> List[Dict]:
        """
        Get incidents for a bounding box and time window.
        
        Args:
            bbox: Bounding box (min_lat, min_lon, max_lat, max_lon)
            time_window: Time window (start_iso, end_iso)
        
        Returns:
            List of incident dictionaries
        """
        try:
            url = f"{self.base_url}/incidents"
            params = {
                "boundingBox": f"{bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]}",
                "startTime": time_window[0],
                "endTime": time_window[1]
            }
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(url, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            incidents = []
            
            for incident in data.get("incidents", []):
                incidents.append({
                    "segmentId": incident.get("id", ""),
                    "type": incident.get("type", "unknown"),
                    "start": incident.get("startTime", ""),
                    "severity": incident.get("severity", "moderate")
                })
            
            return incidents
        
        except Exception as e:
            warning(f"Failed to fetch incidents: {str(e)}")
            return []
    
    def build_eta_matrix(
        self,
        start_coords: Dict[str, float],
        stops_coords: List[Dict[str, float]],
        start_time_iso: str,
        end_time_iso: str,
        mode: str = "drive",
        bin_interval_min: int = 30
    ) -> Dict:
        """
        Build ETA matrix for all pairs at multiple time bins.
        
        Args:
            start_coords: Start location {lat, lon}
            stops_coords: List of stop coordinates [{name, lat, lon}, ...]
            start_time_iso: Start time (ISO8601)
            end_time_iso: End time (ISO8601)
            mode: Transport mode
            bin_interval_min: Time bin interval in minutes
        
        Returns:
            Nested dictionary: {"A->B": {"11:00": {mean, p80, incidents}, ...}}
        """
        from src.services.time_utils import generate_time_bins
        
        # Generate time bins
        bins = generate_time_bins(start_time_iso, end_time_iso, bin_interval_min)
        
        matrix = {}
        
        # For each stop
        for stop in stops_coords:
            stop_name = stop["name"]
            route_key = f"Start->{stop_name}"
            
            matrix[route_key] = {}
            
            # For each time bin
            for bin_time in bins:
                try:
                    # Calculate departure time for this bin
                    departure_dt = self._parse_departure_time(start_time_iso, bin_time)
                    departure_iso = departure_dt.isoformat()
                    
                    # Get ETA
                    eta_data = self.get_predicted_eta(
                        origin_lat=start_coords["lat"],
                        origin_lon=start_coords["lon"],
                        dest_lat=stop["lat"],
                        dest_lon=stop["lon"],
                        departure_time_iso=departure_iso,
                        mode=mode
                    )
                    
                    matrix[route_key][bin_time] = eta_data
                
                except Exception as e:
                    warning(f"Failed to get ETA for {route_key} at {bin_time}: {str(e)}")
                    matrix[route_key][bin_time] = {
                        "meanMinutes": 0,
                        "p80Minutes": 0,
                        "incidentsCount": 0
                    }
        
        return matrix
    
    def _parse_departure_time(self, start_iso: str, bin_time: str) -> datetime:
        """Parse departure time from start ISO and bin time string."""
        start_dt = datetime.fromisoformat(start_iso.replace('Z', '+00:00'))
        if start_dt.tzinfo is None:
            start_dt = pytz.UTC.localize(start_dt)
        
        hour, minute = map(int, bin_time.split(":"))
        departure = start_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        return departure
    
    def _fallback_eta(
        self,
        origin_lat: float,
        origin_lon: float,
        dest_lat: float,
        dest_lon: float,
        mode: str
    ) -> Dict[str, float]:
        """
        Fallback ETA calculation using straight-line distance.
        This is used when INRIX API fails.
        """
        import math
        
        # Calculate distance (Haversine formula)
        R = 6371  # Earth radius in km
        
        dlat = math.radians(dest_lat - origin_lat)
        dlon = math.radians(dest_lon - origin_lon)
        
        a = math.sin(dlat/2)**2 + math.cos(math.radians(origin_lat)) * math.cos(math.radians(dest_lat)) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        distance_km = R * c
        
        # Estimate travel time based on mode (average speeds)
        if mode == "walk":
            avg_speed_kmh = 5
        elif mode == "drive":
            avg_speed_kmh = 40
        else:  # mix
            avg_speed_kmh = 25
        
        eta_minutes = (distance_km / avg_speed_kmh) * 60
        
        return {
            "meanMinutes": eta_minutes,
            "p80Minutes": eta_minutes * 1.2,
            "incidentsCount": 0
        }


# Global instance
_inrix_client = None


def get_inrix_client() -> InrixClient:
    """Get global InrixClient instance."""
    global _inrix_client
    if _inrix_client is None:
        _inrix_client = InrixClient()
    return _inrix_client

