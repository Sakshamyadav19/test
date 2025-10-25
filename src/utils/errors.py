"""Custom exceptions for the application."""


class BaseAppError(Exception):
    """Base exception for all application errors."""
    
    def __init__(self, message: str, code: str = "ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(self.message)


class ValidationError(BaseAppError):
    """Raised when request validation fails."""
    
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, "VALIDATION_ERROR", 400)
        self.details = details or {}


class NotFoundError(BaseAppError):
    """Raised when a resource is not found."""
    
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message, "NOT_FOUND", 404)


class UnauthorizedError(BaseAppError):
    """Raised when authentication/authorization fails."""
    
    def __init__(self, message: str = "Unauthorized"):
        super().__init__(message, "UNAUTHORIZED", 401)


class ExternalServiceError(BaseAppError):
    """Raised when external service call fails."""
    
    def __init__(self, message: str, service: str = "EXTERNAL_SERVICE"):
        super().__init__(message, f"{service}_ERROR", 502)


class GeocodeError(ExternalServiceError):
    """Raised when geocoding fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "GEOCODE")


class LLMError(ExternalServiceError):
    """Raised when LLM invocation fails."""
    
    def __init__(self, message: str):
        super().__init__(message, "LLM")


