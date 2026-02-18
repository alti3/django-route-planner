class RoutePlannerError(Exception):
    """Base exception for route planning errors."""


class ExternalServiceError(RoutePlannerError):
    """Raised when an upstream API call fails."""


class InvalidLocationError(RoutePlannerError):
    """Raised when an input location is invalid or outside USA."""


class NoRouteFoundError(RoutePlannerError):
    """Raised when a drivable route cannot be generated."""


class NoFeasibleFuelPlanError(RoutePlannerError):
    """Raised when the route cannot be traversed with fuel constraints."""
