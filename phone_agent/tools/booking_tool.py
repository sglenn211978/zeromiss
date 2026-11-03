"""Booking tool for scheduling and dispatching electrical service calls."""

import re
from typing import Any, Dict, Optional
from phone_agent.config import DEFAULT_CONFIG
from phone_agent.database import DB
from phone_agent.models import UrgencyLevel


def normalize_phone(phone: str) -> str:
    """Normalizes phone numbers to standard format or returns cleaned string."""
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    elif len(digits) == 11 and digits.startswith("1"):
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return phone or "(555) 000-0000"


def book_service_call(
    customer_name: str,
    phone_number: str,
    service_address: str,
    slot_date: str,
    slot_time: str,
    issue_description: str,
    service_type: Optional[str] = "repair",
    urgency_level: Optional[str] = "STANDARD",
    assigned_technician: Optional[str] = None,
    notes: Optional[str] = None,
    customer_email: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Books an electrical service appointment or creates an emergency code-red dispatch ticket.

    Parameters:
        customer_name: Full name of the customer or property manager.
        phone_number: Best callback phone number for arrival SMS notifications.
        service_address: Complete physical service address including street and city.
        slot_date: Appointment date (YYYY-MM-DD or 'today'/'tomorrow').
        slot_time: Scheduled arrival window (e.g., '08:00 AM - 12:00 PM' or 'Within 45-60 Minutes').
        issue_description: Specific description of the electrical issue or project scope.
        service_type: Category ('repair', 'panel_upgrade', 'ev_charger', 'lighting', 'inspection', 'emergency').
        urgency_level: 'STANDARD', 'URGENT', or 'EMERGENCY_CRITICAL'.
        assigned_technician: Name of the assigned electrician if already selected.
        notes: Access details (e.g. gate code, dog on premises, main panel location).
        customer_email: Customer email address for calendar invite (.ics) and Google Calendar sync.

    Returns:
        Booking confirmation details with confirmation ID, fee schedule, and voice confirmation statement.
    """
    # Normalize urgency
    urgency_clean = (urgency_level or "STANDARD").upper().strip()
    if "EMERG" in urgency_clean or "CRITICAL" in urgency_clean:
        resolved_urgency = UrgencyLevel.EMERGENCY_CRITICAL
        fee = DEFAULT_CONFIG.emergency_dispatch_fee
    elif "URGENT" in urgency_clean:
        resolved_urgency = UrgencyLevel.URGENT
        fee = DEFAULT_CONFIG.standard_diagnostic_fee
    else:
        resolved_urgency = UrgencyLevel.STANDARD
        # Check if consultation / quote is free
        st_clean = (service_type or "").lower()
        if any(free_svc in st_clean for free_svc in DEFAULT_CONFIG.free_quote_services):
            fee = 0.0
        else:
            fee = DEFAULT_CONFIG.standard_diagnostic_fee

    clean_phone = normalize_phone(phone_number)

    # Normalize slot_date to standard YYYY-MM-DD
    from phone_agent.tools.calendar_tool import parse_relative_date
    resolved_date = parse_relative_date(slot_date)

    # Normalize slot_time: routine bookings must always use an actual time frame
    clean_slot_time = slot_time
    if resolved_urgency != UrgencyLevel.EMERGENCY_CRITICAL:
        lower_time = (slot_time or "").lower()
        if "minute" in lower_time or "priority" in lower_time or "emergency" in lower_time or not slot_time:
            clean_slot_time = "08:00 AM - 12:00 PM"

    booking = DB.book_slot(
        customer_name=customer_name.strip(),
        phone_number=clean_phone,
        service_address=service_address.strip(),
        slot_date=resolved_date,
        slot_time=clean_slot_time,
        issue_description=issue_description.strip(),
        service_type=service_type or "repair",
        urgency_level=resolved_urgency,
        assigned_technician=assigned_technician,
        dispatch_fee=fee,
        notes=notes,
        customer_email=customer_email,
    )

    fee_text = "free on-site estimate" if fee == 0.0 else f"${fee:.0f} diagnostic dispatch fee"

    email_note = f" and sent a calendar invite to {customer_email}" if customer_email else ""

    if resolved_urgency == UrgencyLevel.EMERGENCY_CRITICAL:
        voice_summary = (
            f"I have dispatched our on-call Master Electrician {booking.assigned_technician} to {booking.service_address}. "
            f"Your emergency confirmation number is {booking.confirmation_id}. "
            f"Estimated arrival is {booking.slot_time}. Please ensure everyone remains in a safe location."
        )
    else:
        voice_summary = (
            f"You are all set, {booking.customer_name}. I have booked {booking.assigned_technician} for "
            f"{booking.slot_date} during our {booking.slot_time} window at {booking.service_address}. "
            f"Your confirmation code is {booking.confirmation_id}, and we've sent a text to {clean_phone}{email_note}."
        )

    return {
        "status": "SUCCESS",
        "confirmation_id": booking.confirmation_id,
        "booking_status": booking.status,
        "customer_name": booking.customer_name,
        "customer_email": booking.customer_email,
        "phone_number": booking.phone_number,
        "service_address": booking.service_address,
        "appointment_date": booking.slot_date,
        "arrival_window": booking.slot_time,
        "technician": booking.assigned_technician,
        "dispatch_fee": fee,
        "fee_structure": fee_text,
        "google_calendar_link": booking.google_calendar_link,
        "calendar_ics_path": booking.calendar_ics_path,
        "contractor_name": booking.contractor_name,
        "contractor_email": booking.contractor_email,
        "contractor_calendar_link": booking.contractor_calendar_link,
        "contractor_ics_path": booking.contractor_ics_path,
        "contractor_alert_sent": booking.contractor_alert_sent,
        "sms_sent": True,
        "voice_summary": voice_summary,
    }
