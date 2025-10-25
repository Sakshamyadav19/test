"""DynamoDB entity models."""

import ulid
from datetime import datetime
from typing import Any, Dict, List, Optional
from decimal import Decimal


class User:
    """User entity."""
    
    def __init__(
        self,
        userId: str,
        email: str,
        createdAt: str = None
    ):
        self.userId = userId
        self.email = email
        self.createdAt = createdAt or datetime.utcnow().isoformat()
    
    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> "User":
        """Create User from DynamoDB item."""
        return cls(
            userId=item["userId"],
            email=item["email"],
            createdAt=item.get("createdAt")
        )
    
    def to_item(self) -> Dict[str, Any]:
        """Convert User to DynamoDB item."""
        return {
            "userId": self.userId,
            "email": self.email,
            "createdAt": self.createdAt
        }


class Trip:
    """Saved trip entity."""
    
    def __init__(
        self,
        tripId: str,
        userId: str,
        title: str,
        startTime: str,
        endTime: str,
        mode: str,
        startLocation: str,
        itinerary: List[Dict],
        order: List[str],
        finishBy: str,
        totalTravelMinutes: float,
        confidence: str,
        createdAt: str = None
    ):
        self.tripId = tripId
        self.userId = userId
        self.title = title
        self.startTime = startTime
        self.endTime = endTime
        self.mode = mode
        self.startLocation = startLocation
        self.itinerary = itinerary
        self.order = order
        self.finishBy = finishBy
        self.totalTravelMinutes = totalTravelMinutes
        self.confidence = confidence
        self.createdAt = createdAt or datetime.utcnow().isoformat()
    
    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> "Trip":
        """Create Trip from DynamoDB item."""
        return cls(
            tripId=item["tripId"],
            userId=item["userId"],
            title=item["title"],
            startTime=item["startTime"],
            endTime=item["endTime"],
            mode=item["mode"],
            startLocation=item["startLocation"],
            itinerary=item.get("itinerary", []),
            order=item.get("order", []),
            finishBy=item.get("finishBy"),
            totalTravelMinutes=float(item.get("totalTravelMinutes", 0)),
            confidence=item.get("confidence", "Medium"),
            createdAt=item.get("createdAt")
        )
    
    def to_item(self) -> Dict[str, Any]:
        """Convert Trip to DynamoDB item."""
        return {
            "tripId": self.tripId,
            "userId": self.userId,
            "GSI1PK": f"{self.userId}#{self.createdAt}",
            "GSI1SK": self.tripId,
            "title": self.title,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "mode": self.mode,
            "startLocation": self.startLocation,
            "itinerary": self.itinerary,
            "order": self.order,
            "finishBy": self.finishBy,
            "totalTravelMinutes": Decimal(str(self.totalTravelMinutes)),
            "confidence": self.confidence,
            "createdAt": self.createdAt
        }


class TripState:
    """Draft/intermediate trip state."""
    
    def __init__(
        self,
        tripId: str,
        userId: str,
        startLocation: str,
        startTime: str,
        endTime: str,
        mode: str,
        rawStops: List[str] = None,
        geocodedStops: List[Dict] = None,
        classifiedStops: List[Dict] = None,
        etaMatrix: Dict = None,
        incidents: List[Dict] = None,
        finalItinerary: Dict = None,
        lastUpdatedAt: str = None
    ):
        self.tripId = tripId
        self.userId = userId
        self.startLocation = startLocation
        self.startTime = startTime
        self.endTime = endTime
        self.mode = mode
        self.rawStops = rawStops or []
        self.geocodedStops = geocodedStops or []
        self.classifiedStops = classifiedStops or []
        self.etaMatrix = etaMatrix or {}
        self.incidents = incidents or []
        self.finalItinerary = finalItinerary
        self.lastUpdatedAt = lastUpdatedAt or datetime.utcnow().isoformat()
    
    @classmethod
    def generate_id(cls) -> str:
        """Generate a new trip ID."""
        return f"t_{ulid.new().str}"
    
    @classmethod
    def from_item(cls, item: Dict[str, Any]) -> "TripState":
        """Create TripState from DynamoDB item."""
        return cls(
            tripId=item["tripId"],
            userId=item["userId"],
            startLocation=item.get("startLocation", ""),
            startTime=item.get("startTime"),
            endTime=item.get("endTime"),
            mode=item.get("mode"),
            rawStops=item.get("rawStops", []),
            geocodedStops=item.get("geocodedStops", []),
            classifiedStops=item.get("classifiedStops", []),
            etaMatrix=item.get("etaMatrix", {}),
            incidents=item.get("incidents", []),
            finalItinerary=item.get("finalItinerary"),
            lastUpdatedAt=item.get("lastUpdatedAt")
        )
    
    def to_item(self) -> Dict[str, Any]:
        """Convert TripState to DynamoDB item."""
        item = {
            "tripId": self.tripId,
            "userId": self.userId,
            "startLocation": self.startLocation,
            "startTime": self.startTime,
            "endTime": self.endTime,
            "mode": self.mode,
            "lastUpdatedAt": self.lastUpdatedAt
        }
        
        if self.rawStops:
            item["rawStops"] = self.rawStops
        if self.geocodedStops:
            item["geocodedStops"] = self.geocodedStops
        if self.classifiedStops:
            item["classifiedStops"] = self.classifiedStops
        if self.etaMatrix:
            item["etaMatrix"] = self.etaMatrix
        if self.incidents:
            item["incidents"] = self.incidents
        if self.finalItinerary:
            item["finalItinerary"] = self.finalItinerary
        
        return item
    
    @property
    def start_coords(self) -> Optional[Dict[str, float]]:
        """Get start location coordinates."""
        if not self.geocodedStops:
            return None
        # First geocoded stop is assumed to be the start location
        first_stop = self.geocodedStops[0] if self.geocodedStops else None
        if first_stop:
            return {"lat": first_stop["lat"], "lon": first_stop["lon"]}
        return None

