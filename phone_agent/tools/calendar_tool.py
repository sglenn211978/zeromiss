"""Calendar availability checking tool for JobLatch AI Voice Dispatch."""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from phone_agent.database import DB


def parse_relative_date(date_str: Optional[str]) -> str:
    """Parses relative human date strings ('today', 'tomorrow', day names) or returns ISO date."""
    if not date_str or date_str.lower().strip() in ["today", "now", "asap", "immediate"]:
        return datetime.now().strftime("%Y-%m-%d")

    clean = date_str.lower().strip()
    today = datetime.now().date()

    if clean == "tomorrow":
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")

    weekdays = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }
    for day_name, day_num in weekdays.items():
        if day_name in clean:
            days_ahead = (day_num - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next week's instance
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")

    # If already YYYY-MM-DD or standard parseable
    try:
        dt = datetime.strptime(clean, "%Y-%m-%d")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        pass

    # Default to tomorrow if not parseable
    return (today + timedelta(days=1)).strftime("%Y-%m-%d")


def check_calendar_availability(
    target_date: Optional[str] = "today",
    time_window: Optional[str] = "any",
    service_category: Optional[str] = "general",
    urgency: Optional[str] = "standard",
) -> Dict[str, Any]:
    """
    Checks calendar availability for electrical service technicians.

    Parameters:
        target_date: Date to check (e.g. 'today', 'tomorrow', 'next Wednesday', or 'YYYY-MM-DD').
        time_window: Desired timeframe ('morning', 'afternoon', 'evening', 'emergency_asap', or 'any').
        service_category: Specialty ('residential', 'commercial', 'panel_upgrade', 'ev_charger', 'lighting', 'inspection', 'emergency').
        urgency: Level of urgency ('standard', 'urgent', 'emergency').

    Returns:
        Structured dictionary of available slots and recommended appointment window.
    """
    is_emergency = urgency.lower().strip() in ["emergency", "critical", "code_red"] or time_window == "emergency_asap"
    resolved_date = parse_relative_date(target_date)

    if is_emergency:
        # Emergency slots bypass standard windows and return immediate on-call technician
        emergency_slots = DB.get_available_slots(
            target_date=resolved_date,
            time_window_key="emergency_asap",
            limit=2,
        )
        if emergency_slots:
            slot = emergency_slots[0]
            return {
                "status": "EMERGENCY_SLOT_AVAILABLE",
                "resolved_date": resolved_date,
                "urgency": "EMERGENCY_CRITICAL",
                "recommended_slot": {
                    "slot_id": slot.slot_id,
                    "date": slot.date,
                    "time_window": slot.time_window,
                    "technician": slot.technician_name,
                    "dispatch_window": "30-60 minutes on-site arrival",
                },
                "dispatch_fee": 199.0,
                "available_slots_count": len(emergency_slots),
                "voice_summary": f"We have emergency on-call Master Electrician {slot.technician_name} ready to dispatch within 45 to 60 minutes today.",
            }

    # Standard / Urgent matching
    mapped_window = time_window.lower().strip() if time_window else "any"
    if mapped_window in ["am", "early"]:
        mapped_window = "morning"
    elif mapped_window in ["pm", "midday"]:
        mapped_window = "afternoon"
    elif mapped_window in ["late", "night"]:
        mapped_window = "evening"

    slots = DB.get_available_slots(
        target_date=resolved_date,
        time_window_key=mapped_window,
        service_category=service_category,
        limit=4,
    )

    if not slots:
        # Fallback to next day if requested date has no slots
        next_day = (datetime.strptime(resolved_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
        slots = DB.get_available_slots(target_date=next_day, limit=3)
        resolved_date = next_day

    formatted_slots = [
        {
            "slot_id": s.slot_id,
            "date": s.date,
            "time_window": s.time_window,
            "technician": s.technician_name,
        }
        for s in slots
    ]

    slot_descriptions = ", ".join([f"{s['date']} during {s['time_window']} with {s['technician']}" for s in formatted_slots[:2]])

    return {
        "status": "AVAILABLE",
        "resolved_date": resolved_date,
        "urgency": urgency.upper(),
        "available_slots": formatted_slots,
        "recommended_slot": formatted_slots[0] if formatted_slots else None,
        "voice_summary": f"I have openings for {resolved_date}: {slot_descriptions}.",
    }
