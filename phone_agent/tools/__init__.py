"""ZeroMiss Dispatch Tools package."""

from phone_agent.tools.booking_tool import book_service_call
from phone_agent.tools.calendar_tool import check_calendar_availability
from phone_agent.tools.emergency_tool import triage_fire_shock_emergency
from phone_agent.tools.registry import GEMINI_FUNCTION_DECLARATIONS, execute_tool

__all__ = [
    "check_calendar_availability",
    "book_service_call",
    "triage_fire_shock_emergency",
    "GEMINI_FUNCTION_DECLARATIONS",
    "execute_tool",
]
