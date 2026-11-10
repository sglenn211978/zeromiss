"""Command Line Interface for JobLatch AI Electrical Gemini 2.0 Flash Voice Dispatch."""

import argparse
import os
import sys
import time
from phone_agent.agent.audio_sim import AudioStreamSimulator
from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.config import DEFAULT_CONFIG
from phone_agent.database import DB
from tests.scenarios import SCENARIOS
from tests.test_runner import DispatchScenarioTestRunner

try:
    from rich import print as rprint
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def interactive_call(agent: VoiceDispatchAgent, save_audio: bool = False):
    """Simulates an interactive telephone call with Sarah, the JobLatch AI Voice Dispatcher."""
    console = Console() if RICH_AVAILABLE else None

    print("\n" + "=" * 70)
    print("  DIALING: JobLatch AI Electrical 24/7 Voice Dispatch (800-555-LATCH)")
    print("  Connected to: Sarah (Master Electrician Voice Dispatcher)")
    print("  Engine: Gemini 2.0 Flash")
    print(f"  Dispatches Routed to Contractor: {DEFAULT_CONFIG.contractor_name} ({DEFAULT_CONFIG.contractor_email})")
    print("  (Type 'exit' or 'hang up' to end the call)")
    print("=" * 70 + "\n")

    # Simulate phone ringing
    print("📞 [Ring... Ring... Connected]\n")

    session = agent.create_session()
    opening_greeting = "Thank you for calling JobLatch AI Electrical 24/7 Dispatch. My name is Sarah. Are you reporting an electrical emergency, or calling to schedule service?"

    if console:
        console.print(f"[bold cyan]Sarah:[/bold cyan] {opening_greeting}\n")
    else:
        print(f"Sarah: {opening_greeting}\n")

    audio_chunks = []
    if save_audio:
        audio_chunks.append(AudioStreamSimulator.simulate_speech_pcm(opening_greeting))

    booking_announced = False
    while True:
        try:
            if console:
                user_input = Prompt.ask("[bold green]You[/bold green]").strip()
            else:
                user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ["exit", "quit", "hang up", "bye", "goodbye"]:
                closing = "Thank you for calling JobLatch AI Electrical. Stay safe, and have a great day!"
                if console:
                    console.print(f"\n[bold cyan]Sarah:[/bold cyan] {closing}")
                    console.print("[dim]📞 [Call Disconnected][/dim]\n")
                else:
                    print(f"\nSarah: {closing}")
                    print("📞 [Call Disconnected]\n")
                if save_audio:
                    audio_chunks.append(AudioStreamSimulator.simulate_speech_pcm(closing))
                break

            response = agent.process_caller_turn(session, user_input)

            if console:
                console.print(f"\n[bold cyan]Sarah:[/bold cyan] {response}\n")
            else:
                print(f"\nSarah: {response}\n")

            # Announce live contractor dispatch sync if a booking occurred
            if session.active_booking and not booking_announced:
                b = session.active_booking
                booking_announced = True
                if console:
                    console.print(
                        Panel(
                            f"[bold yellow]⚡ LIVE CONTRACTOR DISPATCH RECORDED[/bold yellow]\n\n"
                            f"[bold]Contractor:[/bold] {b.contractor_name} <{b.contractor_email}>\n"
                            f"[bold]Customer:[/bold] {b.customer_name} ({b.phone_number})\n"
                            f"[bold]Address:[/bold] {b.service_address}\n"
                            f"[bold]Assigned Electrician:[/bold] {b.assigned_technician}\n"
                            f"[bold]Arrival Window:[/bold] {b.slot_date} ({b.slot_time})\n\n"
                            f"[bold green]📅 Click to Add to Sean Glenn's Google Calendar:[/bold green]\n"
                            f"[cyan underline]{b.contractor_calendar_link}[/cyan underline]\n\n"
                            f"[dim]📁 Local .ics: {b.contractor_ics_path} | Email: {b.contractor_eml_path}[/dim]",
                            title="[bold cyan]Contractor Sync Notification[/bold cyan]",
                            border_style="yellow",
                        )
                    )
                else:
                    print(f"\n⚡ CONTRACTOR DISPATCH: {b.contractor_name} ({b.contractor_email})")
                    print(f"📅 Google Calendar Link: {b.contractor_calendar_link}\n")

            if save_audio:
                audio_chunks.append(AudioStreamSimulator.simulate_speech_pcm(user_input))
                audio_chunks.append(AudioStreamSimulator.simulate_speech_pcm(response))

        except (KeyboardInterrupt, EOFError):
            print("\n📞 [Call Disconnected by Caller]\n")
            break

    if save_audio and audio_chunks:
        os.makedirs("audio_recordings", exist_ok=True)
        filename = f"audio_recordings/call_{session.session_id}.wav"
        combined = b"".join(audio_chunks)
        AudioStreamSimulator.save_to_wav(combined, filename)
        print(f"🎙️  Call audio recording saved to: {filename}")


def show_dispatch_board():
    """Displays the active dispatch board with technicians, slots, and bookings."""
    console = Console() if RICH_AVAILABLE else None

    print("\n--- ELECTRICAL CONTRACTOR PROFILE ---")
    print(f"• Contractor Name: {DEFAULT_CONFIG.contractor_name} (JobLatch AI Owner / Dispatch Channel)")
    print(f"• Contractor Email: {DEFAULT_CONFIG.contractor_email}")
    print(f"• Direct Phone: {DEFAULT_CONFIG.contractor_phone}")

    print("\n--- ACTIVE TECHNICIAN ROSTER ---")
    for tech in DB.technicians.values():
        on_call_str = "ON-CALL (24/7)" if tech.is_on_call else "Standard Shift"
        specs = ", ".join(tech.specialties)
        print(f"• {tech.name} [{tech.license_type}] - {on_call_str} | Rating: {tech.rating}★ | Specialties: {specs}")

    print("\n--- RECENT SERVICE BOOKINGS ---")
    if not DB.bookings:
        print("  No active bookings recorded in this session.")
    else:
        for b in DB.bookings.values():
            email_info = f" | Email: {b.customer_email}" if b.customer_email else ""
            cal_info = " | 📅 Synced to Sean Glenn's Google Calendar" if b.contractor_calendar_link else ""
            print(f"• [{b.confirmation_id}] {b.customer_name}{email_info} | {b.slot_date} ({b.slot_time}) | Tech: {b.assigned_technician} | Status: {b.status}{cal_info}")
            if b.contractor_calendar_link:
                print(f"    📅 Contractor Calendar Link: {b.contractor_calendar_link}")

    print("\n--- EMERGENCY TRIAGE LOGS ---")
    if not DB.emergency_reports:
        print("  No emergency incidents logged.")
    else:
        for e in DB.emergency_reports.values():
            print(f"• [{e.triage_case_id}] {e.severity_level.value} - {e.hazard_type} ({e.location_in_property}) | {e.recommended_action_plan}")
    print()


def main():
    parser = argparse.ArgumentParser(description="JobLatch AI Gemini 2.0 Flash Voice Dispatch System")
    subparsers = parser.add_subparsers(dest="command")

    # Command: call
    call_parser = subparsers.add_parser("call", help="Start an interactive telephone call with the dispatch agent")
    call_parser.add_argument("--record-wav", action="store_true", help="Record call audio to WAV file")

    # Command: test
    test_parser = subparsers.add_parser("test", help="Run the 20 customer calling scenario test runner")
    test_parser.add_argument("--scenario", type=str, default=None, help="Filter to specific scenario ID (e.g. SCENARIO_01)")

    # Command: board
    subparsers.add_parser("board", help="Display dispatch board, technician roster, and active tickets")

    # Command: test-contractor
    subparsers.add_parser("test-contractor", help="Run live contractor dispatch simulation for Sean Glenn (sean.glenn21@gmail.com)")

    args = parser.parse_args()

    agent = VoiceDispatchAgent()

    if args.command == "call" or args.command is None:
        if args.command is None and len(sys.argv) > 1:
            parser.print_help()
            sys.exit(1)
        interactive_call(agent, save_audio=getattr(args, "record_wav", False))

    elif args.command == "test":
        runner = DispatchScenarioTestRunner()
        if args.scenario:
            matching = [s for s in SCENARIOS if s.scenario_id.upper() == args.scenario.upper()]
            if not matching:
                print(f"Error: Scenario '{args.scenario}' not found. Available IDs: {[s.scenario_id for s in SCENARIOS]}")
                sys.exit(1)
            res = runner.run_scenario(matching[0])
            status = "PASS" if res.passed else "FAIL"
            print(f"\nScenario {res.scenario_id}: {status}")
            if not res.passed:
                print("Failure reasons:", res.failure_reasons)
            sys.exit(0 if res.passed else 1)
        else:
            success = runner.run_all(export_reports=True)
            sys.exit(0 if success else 1)

    elif args.command == "board":
        show_dispatch_board()

    elif args.command == "test-contractor":
        from tests.test_contractor_dispatch import test_contractor_live_dispatch
        success = test_contractor_live_dispatch()
        sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

