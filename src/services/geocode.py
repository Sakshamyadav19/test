"""Amazon Location Service wrapper for geocoding."""

import os
import boto3
from typing import Dict, Optional

from src.utils.errors import GeocodeError
from src.utils.logger import info, error


class GeocodeService:
    """Service for geocoding addresses."""
    
    def __init__(self, region: str = None):
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.place_index_name = os.getenv("LOCATION_PLACE_INDEX_NAME")
        self.location_client = boto3.client("location", region_name=self.region)
    
    def geocode_address(self, address: str) -> Dict[str, any]:
        """
        Geocode an address to latitude/longitude.
        
        Args:
            address: Address string or location name
        
        Returns:
            Dictionary with name, lat, lon
        
        Raises:
            GeocodeError: If geocoding fails
        """
        if not self.place_index_name:
            raise GeocodeError("LOCATION_PLACE_INDEX_NAME not configured")
        
        # Handle special case
        if address.lower() == "usecurrent":
            raise GeocodeError("Please provide an actual location, not 'useCurrent'")
        
        try:
            response = self.location_client.search_place_index_for_text(
                IndexName=self.place_index_name,
                Text=address,
                MaxResults=1
            )
            
            if not response.get("Results"):
                raise GeocodeError(f"Could not geocode address: {address}")
            
            result = response["Results"][0]
            place = result["Place"]
            geometry = place["Geometry"]
            
            coords = {
                "name": place.get("Label", address),
                "lat": geometry["Point"][1],  # Latitude is index 1
                "lon": geometry["Point"][0]  # Longitude is index 0
            }
            
            info(f"Geocoded: {address} -> {coords['lat']}, {coords['lon']}")
            return coords
        
        except self.location_client.exceptions.ValidationException as e:
            error(f"Invalid geocoding request: {str(e)}")
            raise GeocodeError(f"Invalid address format: {address}")
        except self.location_client.exceptions.AccessDeniedException as e:
            error(f"Access denied to Location Service: {str(e)}")
            raise GeocodeError("Insufficient permissions for geocoding")
        except Exception as e:
            error(f"Geocoding failed for '{address}': {str(e)}")
            raise GeocodeError(f"Failed to geocode address: {address}")


# Global instance
_geocode_service = None


def get_geocode_service() -> GeocodeService:
    """Get global GeocodeService instance."""
    global _geocode_service
    if _geocode_service is None:
        _geocode_service = GeocodeService()
    return _geocode_service

