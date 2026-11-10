"""Test script to evaluate call booking and calendar sync for sean.glenn21@gmail.com."""

import json
import os
import sys
from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.database import DB

try:
    from rich import print as rprint
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def test_user_calendar_booking():
    console = Console() if RICH_AVAILABLE else None

    print("\n" + "=" * 80)
    print("  JobLatch AI Voice Dispatch - Custom Email & Calendar Integration Test")
    print("  User Email: sean.glenn21@gmail.com")
    print("================================================================================\n")

    agent = VoiceDispatchAgent()
    session = agent.create_session(caller_phone="(555) 829-1044")

    # Step 1: Caller introduces need
    turn1_user = (
        "Hi Sarah, this is Sean Glenn. I need to book a licensed electrician to install "
        "a 50-amp Level 2 EV charging circuit in my garage next Wednesday."
    )
    print(f"📞 Caller: \"{turn1_user}\"\n")
    turn1_agent = agent.process_caller_turn(session, turn1_user)
    print(f"🤖 Sarah: \"{turn1_agent}\"\n")

    # Step 2: Caller provides credentials including email
    turn2_user = (
        "Tomorrow morning works well. My name is Sean Glenn, address is 45 Innovation Way in Cambridge, "
        "cell is 555-829-1044, and my email is sean.glenn21@gmail.com."
    )
    print(f"📞 Caller: \"{turn2_user}\"\n")
    turn2_agent = agent.process_caller_turn(session, turn2_user)
    print(f"🤖 Sarah: \"{turn2_agent}\"\n")

    # Step 3: Verify booking in DB
    assert len(DB.bookings) > 0, "No booking was recorded in database!"
    booking = list(DB.bookings.values())[-1]

    print("-" * 80)
    print("VERIFICATION CHECKS:")
    print(f"✓ Confirmation ID:       {booking.confirmation_id}")
    print(f"✓ Customer Name:         {booking.customer_name}")
    print(f"✓ Customer Email:        {booking.customer_email}")
    print(f"✓ Phone:                 {booking.phone_number}")
    print(f"✓ Service Address:       {booking.service_address}")
    print(f"✓ Appointment Date/Time: {booking.slot_date} ({booking.slot_time})")
    print(f"✓ Assigned Electrician:  {booking.assigned_technician}")
    print(f"✓ Booking Status:        {booking.status}")

    assert booking.customer_email == "sean.glenn21@gmail.com", f"Expected sean.glenn21@gmail.com, got {booking.customer_email}"

    # Step 4: Verify .ics file
    assert booking.calendar_ics_path and os.path.exists(booking.calendar_ics_path), "Calendar .ics file missing!"
    print(f"✓ iCalendar File (.ics): {booking.calendar_ics_path}")

    with open(booking.calendar_ics_path, "r", encoding="utf-8") as f:
        ics_text = f.read()

    assert "sean.glenn21@gmail.com" in ics_text, "Email missing from .ics content!"
    assert "JobLatch AI Electrical" in ics_text, "Brand missing from .ics!"

    # Step 5: Verify Google Calendar link
    assert booking.google_calendar_link, "Google Calendar URL not generated!"
    print(f"✓ Google Calendar Link:  {booking.google_calendar_link}")

    # Step 6: Verify Sent Email Record
    meta_path = f"sent_emails/{booking.confirmation_id}_meta.json"
    eml_path = f"sent_emails/{booking.confirmation_id}_email.eml"
    assert os.path.exists(meta_path), f"Email metadata file missing: {meta_path}"
    assert os.path.exists(eml_path), f"MIME email file missing: {eml_path}"

    with open(meta_path, "r", encoding="utf-8") as f:
        meta = json.load(f)

    print(f"✓ Email Confirmation:    Saved to {eml_path}")
    print(f"✓ Email Recipient:       {meta['recipient']}")
    print(f"✓ Email Subject:         {meta['subject']}")
    print(f"✓ Email Delivery Status: {meta['status']}")

    print("\n" + "=" * 80)
    print("  iCalendar (.ics) File Preview:")
    print("-" * 80)
    for line in ics_text.strip().split("\n")[:18]:
        print(f"  {line.strip()}")
    print("  ...")
    print("=" * 80)

    if console:
        panel = Panel(
            f"[bold green]CALENDAR INTEGRATION VERIFIED SUCCESSFULLY![/bold green]\n\n"
            f"[bold]Customer:[/bold] {booking.customer_name} <{booking.customer_email}>\n"
            f"[bold]Technician:[/bold] {booking.assigned_technician}\n"
            f"[bold]Slot:[/bold] {booking.slot_date} ({booking.slot_time})\n"
            f"[bold]Google Calendar Link:[/bold]\n[cyan]{booking.google_calendar_link}[/cyan]\n\n"
            f"[bold]Local .ics file:[/bold] {booking.calendar_ics_path}\n"
            f"[bold]Email artifact:[/bold] {eml_path}",
            title="[bold cyan]Google Calendar & Email Verification[/bold cyan]",
            border_style="green",
        )
        console.print(panel)

    return True


if __name__ == "__main__":
    success = test_user_calendar_booking()
    sys.exit(0 if success else 1)
