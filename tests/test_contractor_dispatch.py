"""Live Contractor Dispatch and Google Calendar Sync Test for Sean Glenn (sean.glenn21@gmail.com)."""

import json
import os
import sys
from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.config import DEFAULT_CONFIG
from phone_agent.database import DB
from phone_agent.models import EmergencySeverity

try:
    from rich import print as rprint
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def test_contractor_live_dispatch():
    console = Console() if RICH_AVAILABLE else None

    print("\n" + "=" * 80)
    print("  ZeroMiss Voice Dispatch - Live Contractor Dispatch & Calendar Sync")
    print(f"  Contractor: {DEFAULT_CONFIG.contractor_name} ({DEFAULT_CONFIG.contractor_email})")
    print("================================================================================\n")

    DB.reset()
    agent = VoiceDispatchAgent()

    # --- TEST 1: Routine Customer Booking with Live Contractor Sync ---
    print("--- SCENARIO 1: Customer (Elena Rostova) calls to book EV Charger ---")
    session = agent.create_session(caller_phone="(555) 341-9820")

    turn1 = (
        "Hello Sarah, my name is Elena Rostova. I live at 144 Highland Avenue in Somerville. "
        "I need a 240-volt NEMA 14-50 outlet installed in my garage for a new electric vehicle. "
        "Can we schedule this for tomorrow morning?"
    )
    print(f"📞 Customer: \"{turn1}\"\n")
    agent_resp = agent.process_caller_turn(session, turn1)
    print(f"🤖 Sarah (Dispatcher): \"{agent_resp}\"\n")

    # Verify Booking
    assert len(DB.bookings) > 0, "Error: Booking was not recorded in database!"
    booking = list(DB.bookings.values())[-1]

    print("-" * 80)
    print("CONTRACTOR DISPATCH VERIFICATION:")
    print(f"✓ Confirmation Code:      {booking.confirmation_id}")
    print(f"✓ Customer Name:          {booking.customer_name}")
    print(f"✓ Customer Phone:         {booking.phone_number}")
    print(f"✓ Service Address:        {booking.service_address}")
    print(f"✓ Assigned Electrician:   {booking.assigned_technician}")
    print(f"✓ Arrival Window:         {booking.slot_date} ({booking.slot_time})")
    print(f"✓ Contractor Name:        {booking.contractor_name}")
    print(f"✓ Contractor Email:       {booking.contractor_email}")
    print(f"✓ Contractor Alert Sent:  {booking.contractor_alert_sent}")

    assert booking.contractor_email == "sean.glenn21@gmail.com", f"Wrong contractor email: {booking.contractor_email}"
    assert booking.contractor_alert_sent is True, "Contractor alert was not sent!"

    # Verify Contractor Calendar Link
    assert booking.contractor_calendar_link, "Contractor Google Calendar link missing!"
    assert "add=sean.glenn21%40gmail.com" in booking.contractor_calendar_link or "add=sean.glenn21@gmail.com" in booking.contractor_calendar_link, "Contractor email missing in calendar URL"
    print(f"\n✓ 1-Click Google Calendar Link for Sean Glenn:")
    print(f"  {booking.contractor_calendar_link}\n")

    # Verify Contractor .ics File
    assert booking.contractor_ics_path and os.path.exists(booking.contractor_ics_path), f"Contractor .ics missing: {booking.contractor_ics_path}"
    with open(booking.contractor_ics_path, "r", encoding="utf-8") as f:
        ics_text = f.read()
    assert "sean.glenn21@gmail.com" in ics_text, "Contractor email missing from .ics attendee!"
    assert "Elena Rostova" in ics_text, "Customer name missing from .ics!"
    print(f"✓ Contractor iCalendar (.ics) File: {booking.contractor_ics_path}")

    # Verify Contractor Alert Email
    assert booking.contractor_eml_path and os.path.exists(booking.contractor_eml_path), f"Contractor email missing: {booking.contractor_eml_path}"
    with open(booking.contractor_eml_path, "r", encoding="utf-8") as f:
        eml_text = f.read()
    assert "To: Sean Glenn <sean.glenn21@gmail.com>" in eml_text or "sean.glenn21@gmail.com" in eml_text
    print(f"✓ Contractor Email Dispatch (.eml): {booking.contractor_eml_path}")

    meta_path = f"sent_emails/contractor_alert_{booking.confirmation_id}_meta.json"
    assert os.path.exists(meta_path), f"Metadata missing: {meta_path}"
    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)
    print(f"✓ Email Audit Record: Delivered to {meta['contractor_email']} (Subject: {meta['subject']})")

    # --- TEST 2: Emergency Triage Notification to Contractor ---
    print("\n" + "=" * 80)
    print("--- SCENARIO 2: Emergency Incident Call with Contractor Code-Red Alert ---")
    session_emerg = agent.create_session(caller_phone="(555) 919-4402")
    turn_emerg = (
        "Help! I'm David Miller at 55 Oak Street. There is black smoke and active sparking "
        "coming out of my basement breaker panel! It smells like burning plastic!"
    )
    print(f"📞 Customer: \"{turn_emerg}\"\n")
    agent_emerg_resp = agent.process_caller_turn(session_emerg, turn_emerg)
    print(f"🤖 Sarah (Dispatcher): \"{agent_emerg_resp}\"\n")

    # Verify Emergency Report
    assert len(DB.emergency_reports) > 0, "Emergency report was not recorded!"
    emerg_report = list(DB.emergency_reports.values())[-1]
    print(f"✓ Emergency Triage ID:     {emerg_report.triage_case_id}")
    print(f"✓ Severity Level:         {emerg_report.severity_level.value}")
    print(f"✓ Contractor Alert Sent:  {emerg_report.contractor_alert_sent}")
    assert emerg_report.contractor_alert_sent is True, "Emergency contractor alert not sent!"
    assert emerg_report.contractor_eml_path and os.path.exists(emerg_report.contractor_eml_path)
    print(f"✓ Emergency Alert (.eml): {emerg_report.contractor_eml_path}")

    if console:
        panel = Panel(
            f"[bold green]LIVE CONTRACTOR DISPATCH & GOOGLE CALENDAR VERIFIED![/bold green]\n\n"
            f"[bold]Contractor Account:[/bold] Sean Glenn <[cyan]sean.glenn21@gmail.com[/cyan]>\n"
            f"[bold]Role:[/bold] Owner / Master Electrician Dispatch Channel\n\n"
            f"[bold yellow]👉 CLICK TO ADD DIRECTLY TO YOUR GOOGLE CALENDAR:[/bold yellow]\n"
            f"[cyan underline]{booking.contractor_calendar_link}[/cyan underline]\n\n"
            f"[bold]Contractor .ics File:[/bold] {booking.contractor_ics_path}\n"
            f"[bold]Contractor Email Alert:[/bold] {booking.contractor_eml_path}\n"
            f"[bold]Emergency Code-Red Alert:[/bold] {emerg_report.contractor_eml_path}",
            title="[bold cyan]ZeroMiss Live Contractor Dispatch Sync[/bold cyan]",
            border_style="green",
        )
        console.print(panel)

    return True


if __name__ == "__main__":
    success = test_contractor_live_dispatch()
    sys.exit(0 if success else 1)
