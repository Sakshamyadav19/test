"""Amazon Bedrock client for LLM invocations."""

import json
import os
import boto3
from typing import Dict, List, Optional

from src.utils.logger import info, error, warning
from src.utils.errors import LLMError


class BedrockService:
    """Service for invoking Bedrock LLM models."""
    
    def __init__(self, region: str = None):
        self.region = region or os.getenv("AWS_REGION", "us-west-2")
        self.model_id = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")
        self.bedrock_runtime = boto3.client("bedrock-runtime", region_name=self.region)
    
    def classify_poi(self, name: str, lat: float, lon: float, city: str = None) -> Dict:
        """
        Classify a POI using Bedrock LLM.
        
        Args:
            name: POI name
            lat: Latitude
            lon: Longitude
            city: Optional city name
        
        Returns:
            Dictionary with category, bestTimeWindow, reason
        
        Raises:
            LLMError: If LLM invocation fails
        """
        # Build prompt from spec (section 5.1)
        system_prompt = """You classify real-world places. Use the provided name and coordinates only.
Return structured JSON with: category, bestTimeWindow, reason, and do not include extra fields.
Categories to choose from (pick one): pier, museum, viewpoint, cafe, park, landmark, beach, restaurant, other.
bestTimeWindow must be a local time range like "17:00–19:00".
Be decisive. If unsure, pick the closest category based on typical tourist use."""
        
        user_prompt = f"""Name: "{name}"
Coordinates: {lat}, {lon}
Return JSON only."""
        
        if city:
            user_prompt += f"\nCity: {city}"
        
        # Try up to 2 times
        for attempt in range(2):
            try:
                response = self._invoke_claude(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=500
                )
                
                # Parse response
                result = self._parse_json_response(response)
                
                # Validate required fields
                required_fields = ["category", "bestTimeWindow", "reason"]
                for field in required_fields:
                    if field not in result:
                        raise LLMError(f"Missing required field in LLM response: {field}")
                
                # Set default stayMin if not provided
                result["stayMin"] = result.get("stayMin", 45)
                
                info(f"Classified POI: {name} -> {result['category']}")
                return result
            
            except Exception as e:
                if attempt == 0:
                    warning(f"LLM classification failed (attempt {attempt + 1}): {str(e)}, retrying...")
                    # Retry with stricter prompt
                    user_prompt += "\n\nReturn JSON only; no prose."
                else:
                    error(f"LLM classification failed after 2 attempts: {str(e)}")
                    raise LLMError(f"Failed to classify POI '{name}': {str(e)}")
        
        raise LLMError(f"Failed to classify POI after 2 attempts")
    
    def plan_itinerary(
        self,
        start_time_iso: str,
        end_time_iso: str,
        mode: str,
        start_point: Dict[str, float],
        classified_stops: List[Dict],
        eta_matrix: Dict,
        incidents: List[Dict],
        timezone: str = "UTC"
    ) -> Dict:
        """
        Plan itinerary using Bedrock LLM.
        
        Args:
            start_time_iso: Start time (ISO8601)
            end_time_iso: End time (ISO8601)
            mode: Transport mode
            start_point: Start coordinates {lat, lon}
            classified_stops: List of classified stops
            eta_matrix: ETA matrix
            incidents: List of incidents
            timezone: Timezone string
        
        Returns:
            Planned itinerary dictionary
        
        Raises:
            LLMError: If LLM invocation fails
        """
        # Build prompt from spec (section 5.2)
        system_prompt = """You are an expert itinerary planner. Use ONLY the data provided.
You must:
- Visit all spots exactly once.
- Start at startTime and finish by endTime.
- Minimize total travel minutes using the ETA matrix.
- Prefer scheduling spots near their bestTimeWindow.
- Avoid routes/times with incidents when reasonable.
- DO NOT invent coordinates or times not implied by ETA and the window.
- Return STRICT JSON in the schema provided."""
        
        # Format classified stops
        stops_json = json.dumps(classified_stops, indent=2)
        
        # Format ETA matrix
        eta_matrix_json = json.dumps(eta_matrix, indent=2)
        
        # Format incidents
        incidents_json = json.dumps(incidents, indent=2)
        
        user_prompt = f"""StartTime: {start_time_iso}
EndTime: {end_time_iso}
Mode: {mode}
StartPoint: {{ "lat": {start_point['lat']}, "lon": {start_point['lon']} }}

Spots (all must be visited):
{stops_json}

ETA Matrix (minutes):
{eta_matrix_json}

Incidents (if any):
{incidents_json}

Return JSON in this schema:
{{
  "order": ["<spotName>", "..."],
  "itinerary": [
    {{
      "spot": "<spotName>",
      "lat": <number>,
      "lon": <number>,
      "arrival": "HH:MM",
      "reason": "<= 20 words, grounded in provided ETA/best-time/incident data>"
    }}
  ],
  "totalTravelMinutes": <number>,
  "confidence": "High|Medium|Low",
  "finishBy": "HH:MM"
}}

Rules:
- "lat" and "lon" must match the input spots; do not create new coordinates.
- "arrival" must be local time and within [startTime, endTime].
- Sum of travel and minimum stay should fit within the window. If not, choose the best subset that fits and explicitly skip the least valuable spot(s) (closest duplicates, low desirability).
- Keep reasons short and factual (no fluff)."""
        
        # Try up to 2 times
        for attempt in range(2):
            try:
                response = self._invoke_claude(
                    system_prompt=system_prompt,
                    user_prompt=user_prompt,
                    max_tokens=2000
                )
                
                # Parse response
                result = self._parse_json_response(response)
                
                # Validate response
                if "order" not in result:
                    raise LLMError("Missing 'order' field in LLM response")
                if "itinerary" not in result:
                    raise LLMError("Missing 'itinerary' field in LLM response")
                
                # Set defaults for optional fields
                result["totalTravelMinutes"] = result.get("totalTravelMinutes", 0)
                result["confidence"] = result.get("confidence", "Medium")
                
                info(f"Generated itinerary with {len(result['itinerary'])} stops")
                return result
            
            except Exception as e:
                if attempt == 0:
                    warning(f"LLM planning failed (attempt {attempt + 1}): {str(e)}, retrying...")
                    # Retry with stricter prompt
                    user_prompt += "\n\nIMPORTANT: Return STRICT JSON only. No prose."
                else:
                    error(f"LLM planning failed after 2 attempts: {str(e)}")
                    raise LLMError(f"Failed to plan itinerary: {str(e)}")
        
        raise LLMError("Failed to plan itinerary after 2 attempts")
    
    def _invoke_claude(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 1000
    ) -> str:
        """Invoke Claude model via Bedrock."""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "system": system_prompt,
                "messages": [
                    {
                        "role": "user",
                        "content": user_prompt
                    }
                ]
            }
            
            response = self.bedrock_runtime.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response["body"].read())
            
            # Extract text from Claude response
            if "content" in response_body:
                text = ""
                for block in response_body["content"]:
                    if block["type"] == "text":
                        text += block["text"]
                return text
            else:
                raise LLMError("Invalid response format from Bedrock")
        
        except Exception as e:
            raise LLMError(f"Bedrock invocation failed: {str(e)}")
    
    def _parse_json_response(self, response: str) -> Dict:
        """Parse JSON response from LLM."""
        try:
            # Try to extract JSON from response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                # Find first and last ```
                start_idx = response.find("```")
                if start_idx != -1:
                    response = response[start_idx + 3:]
                    end_idx = response.find("```")
                    if end_idx != -1:
                        response = response[:end_idx]
            
            # Try to find JSON object
            start_brace = response.find("{")
            end_brace = response.rfind("}")
            
            if start_brace != -1 and end_brace != -1:
                json_str = response[start_brace:end_brace + 1]
                return json.loads(json_str)
            else:
                return json.loads(response)
        
        except json.JSONDecodeError as e:
            raise LLMError(f"Failed to parse JSON response: {str(e)}")


# Global instance
_bedrock_service = None


def get_bedrock_service() -> BedrockService:
    """Get global BedrockService instance."""
    global _bedrock_service
    if _bedrock_service is None:
        _bedrock_service = BedrockService()
    return _bedrock_service

