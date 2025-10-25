"""Request/Response DTOs matching OpenAPI spec."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


# Authentication
class SignupRequest(BaseModel):
    """User signup request."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., min_length=8, description="User password (min 8 chars)")


class LoginRequest(BaseModel):
    """User login request."""
    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class AuthResponse(BaseModel):
    """Authentication response."""
    accessToken: str = Field(..., description="JWT access token")
    refreshToken: Optional[str] = Field(None, description="JWT refresh token")
    userId: str = Field(..., description="User ID")
    message: str = Field(..., description="Success message")


# Trip initialization
class InitRequest(BaseModel):
    """Initialize trip draft request."""
    startLocation: str = Field(..., description="Free text or 'useCurrent'")
    startTime: str = Field(..., description="ISO8601 datetime")
    endTime: str = Field(..., description="ISO8601 datetime")
    mode: str = Field(..., pattern="^(walk|drive|mix)$", description="Transport mode")
    stops: List[str] = Field(..., min_length=1, description="POI names as user typed")
    
    @field_validator("stops")
    @classmethod
    def validate_stops(cls, v):
        if not v or len(v) == 0:
            raise ValueError("stops must have at least one item")
        return v


class InitResponse(BaseModel):
    """Initialize trip draft response."""
    tripId: str = Field(..., description="Generated trip ID")
    tripDurationMinutes: int = Field(..., description="Duration in minutes")
    message: str = Field(..., description="Success message")


class TripIdOnly(BaseModel):
    """Trip ID only request."""
    tripId: str = Field(..., description="Trip ID")


class ClassifiedStop(BaseModel):
    """Classified POI stop."""
    name: str = Field(..., description="POI name")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    category: str = Field(..., description="Category")
    bestTimeWindow: str = Field(..., description="Best time window (e.g., 17:00–19:00)")
    reason: str = Field(..., description="Classification reason")
    stayMin: int = Field(45, description="Stay duration in minutes")


class ClassifyResponse(BaseModel):
    """Classified stops response."""
    tripId: str = Field(..., description="Trip ID")
    classifiedStops: List[ClassifiedStop] = Field(..., description="Classified stops")


class EtaLeg(BaseModel):
    """ETA leg data."""
    mean: float = Field(..., description="Mean travel time in minutes")
    p80: float = Field(..., description="80th percentile in minutes")
    incidents: int = Field(0, description="Number of incidents")


class EtaResponse(BaseModel):
    """ETA matrix response."""
    tripId: str = Field(..., description="Trip ID")
    etaMatrix: dict = Field(..., description="ETA matrix keyed by 'A->B'")
    incidents: List[dict] = Field(default_factory=list, description="Incidents list")


class ItineraryItem(BaseModel):
    """Itinerary item."""
    spot: str = Field(..., description="Spot name")
    lat: float = Field(..., description="Latitude")
    lon: float = Field(..., description="Longitude")
    arrival: str = Field(..., description="Arrival time HH:MM local")
    reason: str = Field(..., max_length=120, description="Visit reason")


class PlanResponse(BaseModel):
    """Final itinerary response."""
    tripId: str = Field(..., description="Trip ID")
    order: List[str] = Field(..., description="Visit order")
    itinerary: List[ItineraryItem] = Field(..., description="Final itinerary")
    totalTravelMinutes: float = Field(..., description="Total travel time")
    confidence: str = Field(..., pattern="^(High|Medium|Low)$", description="Confidence level")
    finishBy: str = Field(..., description="Finish time HH:MM local")


class SaveRequest(BaseModel):
    """Save trip request."""
    tripId: str = Field(..., description="Trip ID")
    title: str = Field(..., min_length=1, description="Trip title")


class SaveResponse(BaseModel):
    """Save trip response."""
    tripId: str = Field(..., description="Trip ID")
    message: str = Field(..., description="Success message")

