"""Tool declarations and execution dispatcher for Gemini 2.0 Flash."""

from typing import Any, Dict, List
from phone_agent.models import ToolExecutionResult
from phone_agent.tools.booking_tool import book_service_call
from phone_agent.tools.calendar_tool import check_calendar_availability
from phone_agent.tools.emergency_tool import triage_fire_shock_emergency

# Official Gemini 2.0 Flash Function Declarations
GEMINI_FUNCTION_DECLARATIONS = [
    {
        "name": "check_calendar_availability",
        "description": (
            "Checks electrical service technician availability and schedule slots by date, timeframe, "
            "and service specialty (e.g. routine repairs, panel upgrades, EV chargers, or 24/7 emergency calls)."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "target_date": {
                    "type": "STRING",
                    "description": "Target date for the appointment. Can be 'today', 'tomorrow', 'next Monday', or 'YYYY-MM-DD'.",
                },
                "time_window": {
                    "type": "STRING",
                    "enum": ["morning", "afternoon", "evening", "emergency_asap", "any"],
                    "description": "Preferred time of day: morning (8am-12pm), afternoon (12pm-4pm), evening (4pm-7pm), emergency_asap, or any.",
                },
                "service_category": {
                    "type": "STRING",
                    "enum": ["residential", "commercial", "panel_upgrade", "ev_charger", "lighting", "inspection", "emergency", "general"],
                    "description": "Electrical specialty needed for proper technician dispatch.",
                },
                "urgency": {
                    "type": "STRING",
                    "enum": ["standard", "urgent", "emergency"],
                    "description": "Urgency classification: standard, urgent (same day priority), or emergency (code red immediate).",
                },
            },
            "required": ["target_date"],
        },
    },
    {
        "name": "book_service_call",
        "description": (
            "Books a confirmed electrical service call or dispatches an emergency technician to a customer's location. "
            "Generates a confirmation ID, assigns a licensed electrician, and schedules arrival."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "customer_name": {
                    "type": "STRING",
                    "description": "Full name of the caller or customer.",
                },
                "phone_number": {
                    "type": "STRING",
                    "description": "10-digit callback phone number for technician arrival updates.",
                },
                "service_address": {
                    "type": "STRING",
                    "description": "Full physical address where electrical service is needed.",
                },
                "slot_date": {
                    "type": "STRING",
                    "description": "Appointment date in YYYY-MM-DD format or 'today'/'tomorrow'.",
                },
                "slot_time": {
                    "type": "STRING",
                    "description": "Arrival window selected (e.g., '08:00 AM - 12:00 PM', '12:00 PM - 04:00 PM', or 'Within 45-60 Minutes').",
                },
                "issue_description": {
                    "type": "STRING",
                    "description": "Detailed summary of the electrical issue, equipment, or installation requested.",
                },
                "service_type": {
                    "type": "STRING",
                    "enum": ["repair", "panel_upgrade", "ev_charger", "lighting", "inspection", "emergency", "generator"],
                    "description": "Category of work to perform.",
                },
                "urgency_level": {
                    "type": "STRING",
                    "enum": ["STANDARD", "URGENT", "EMERGENCY_CRITICAL"],
                    "description": "Urgency rating for the service call.",
                },
                "assigned_technician": {
                    "type": "STRING",
                    "description": "Name of assigned electrician if obtained from calendar check (optional).",
                },
                "notes": {
                    "type": "STRING",
                    "description": "Special property access instructions, pet warnings, or panel locations (optional).",
                },
                "customer_email": {
                    "type": "STRING",
                    "description": "Customer email address for Google Calendar integration and confirmation email (optional).",
                },
            },
            "required": ["customer_name", "phone_number", "service_address", "slot_date", "slot_time", "issue_description"],
        },
    },
    {
        "name": "triage_fire_shock_emergency",
        "description": (
            "CRITICAL SAFETY TOOL: Triages urgent electrical hazards including active sparks, electrical fire/smoke, "
            "electric shock injuries, downed power lines, water near panels, or burning smells. Delivers immediate "
            "life-safety spoken instructions to protect the caller and triggers priority dispatch."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "hazard_type": {
                    "type": "STRING",
                    "enum": [
                        "active_sparking",
                        "burning_smell_smoke",
                        "water_electrical_contact",
                        "electric_shock_injury",
                        "exposed_live_wire",
                        "downed_power_line",
                        "hot_outlet_switch",
                        "breaker_buzzing",
                        "other_hazard",
                    ],
                    "description": "Specific hazardous electrical condition observed.",
                },
                "location_in_property": {
                    "type": "STRING",
                    "description": "Location of hazard: 'breaker_panel', 'basement', 'kitchen', 'bathroom', 'appliance', 'yard_exterior', etc.",
                },
                "is_fire_visible": {
                    "type": "BOOLEAN",
                    "description": "True if visible flames, glowing embers, or thick active smoke is present.",
                },
                "is_person_injured": {
                    "type": "BOOLEAN",
                    "description": "True if someone suffered an electric shock, burns, or requires medical attention.",
                },
                "is_water_present": {
                    "type": "BOOLEAN",
                    "description": "True if standing water, flooding, or dripping pipes are in contact with or near electrical equipment.",
                },
                "can_safely_access_panel": {
                    "type": "BOOLEAN",
                    "description": "True only if caller can safely and dryly reach the main breaker without touching water or approaching fire.",
                },
                "caller_description": {
                    "type": "STRING",
                    "description": "Raw description from the caller describing sounds, smells, or physical symptoms.",
                },
            },
            "required": ["hazard_type", "location_in_property"],
        },
    },
]


def execute_tool(tool_name: str, arguments: Dict[str, Any]) -> ToolExecutionResult:
    """Executes the requested tool by name with provided arguments."""
    try:
        if tool_name == "check_calendar_availability":
            result = check_calendar_availability(
                target_date=arguments.get("target_date", "today"),
                time_window=arguments.get("time_window", "any"),
                service_category=arguments.get("service_category", "general"),
                urgency=arguments.get("urgency", "standard"),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                data=result,
                message=result.get("voice_summary", "Calendar checked successfully."),
            )

        elif tool_name == "book_service_call":
            result = book_service_call(
                customer_name=arguments.get("customer_name", "Valued Customer"),
                phone_number=arguments.get("phone_number", "(555) 000-0000"),
                service_address=arguments.get("service_address", "Customer Address"),
                slot_date=arguments.get("slot_date", "today"),
                slot_time=arguments.get("slot_time", "08:00 AM - 12:00 PM"),
                issue_description=arguments.get("issue_description", "Electrical service"),
                service_type=arguments.get("service_type", "repair"),
                urgency_level=arguments.get("urgency_level", "STANDARD"),
                assigned_technician=arguments.get("assigned_technician"),
                notes=arguments.get("notes"),
                customer_email=arguments.get("customer_email"),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                data=result,
                message=result.get("voice_summary", "Booking confirmed."),
            )

        elif tool_name == "triage_fire_shock_emergency":
            result = triage_fire_shock_emergency(
                hazard_type=arguments.get("hazard_type", "other_hazard"),
                location_in_property=arguments.get("location_in_property", "unknown"),
                is_fire_visible=bool(arguments.get("is_fire_visible", False)),
                is_person_injured=bool(arguments.get("is_person_injured", False)),
                is_water_present=bool(arguments.get("is_water_present", False)),
                can_safely_access_panel=bool(arguments.get("can_safely_access_panel", True)),
                caller_description=arguments.get("caller_description"),
            )
            return ToolExecutionResult(
                tool_name=tool_name,
                success=True,
                data=result,
                message=result.get("voice_directives", "Emergency triage evaluated."),
            )

        else:
            return ToolExecutionResult(
                tool_name=tool_name,
                success=False,
                data={},
                message=f"Unknown tool: '{tool_name}'",
            )
    except Exception as e:
        return ToolExecutionResult(
            tool_name=tool_name,
            success=False,
            data={"error": str(e)},
            message=f"Tool execution failed: {str(e)}",
        )
