"""Test runner that executes and rigorously evaluates 20 customer calling scenarios."""

import json
import os
import sys
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional
from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.database import DB
from phone_agent.models import CallSession
from tests.scenarios import SCENARIOS, CallingScenario

try:
    from rich import print as rprint
    from rich.box import ROUNDED
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


@dataclass
class ScenarioEvaluationResult:
    scenario_id: str
    title: str
    category: str
    passed: bool
    duration_ms: float
    tools_called: List[str]
    expected_tools: List[str]
    emergency_level: Optional[str]
    booking_confirmation_id: Optional[str]
    assigned_technician: Optional[str]
    safety_phrases_matched: List[str]
    failure_reasons: List[str]
    transcript_summary: List[Dict[str, str]]


class DispatchScenarioTestRunner:
    """Evaluates the JobLatch AI Gemini 2.0 Flash Voice Dispatch Agent against 20 calling scenarios."""

    def __init__(self, api_key: Optional[str] = None):
        self.agent = VoiceDispatchAgent(api_key=api_key)
        self.results: List[ScenarioEvaluationResult] = []
        self.console = Console() if RICH_AVAILABLE else None

    def run_scenario(self, scenario: CallingScenario) -> ScenarioEvaluationResult:
        """Executes a single multi-turn scenario and evaluates compliance."""
        start_time = time.perf_counter()
        session = self.agent.create_session(caller_phone=scenario.caller_phone)

        # Clear DB state between scenarios to isolate bookings
        DB.reset()

        dialogue_transcript: List[Dict[str, str]] = []

        # Play through each caller utterance
        for turn_idx, caller_utterance in enumerate(scenario.turns):
            dialogue_transcript.append({"role": "Caller", "content": caller_utterance})
            agent_response = self.agent.process_caller_turn(session, caller_utterance)
            dialogue_transcript.append({"role": "Sarah (Dispatcher)", "content": agent_response})

        duration_ms = (time.perf_counter() - start_time) * 1000.0

        # Run evaluation criteria
        failure_reasons: List[str] = []
        tools_called_unique = list(dict.fromkeys(session.tools_invoked))

        # 1. Evaluate Tool Invocations
        for expected_tool in scenario.expected_tools:
            if expected_tool not in tools_called_unique:
                failure_reasons.append(f"Missing required tool call: '{expected_tool}'")

        # 2. Evaluate Emergency Triage Guardrails
        last_emergency_report = None
        if DB.emergency_reports:
            last_emergency_report = list(DB.emergency_reports.values())[-1]

        if scenario.is_emergency:
            if "triage_fire_shock_emergency" not in tools_called_unique:
                failure_reasons.append("Emergency scenario failed to invoke triage_fire_shock_emergency!")
            elif scenario.expected_emergency_level and last_emergency_report:
                if last_emergency_report.severity_level.value != scenario.expected_emergency_level:
                    failure_reasons.append(
                        f"Expected emergency severity '{scenario.expected_emergency_level}', "
                        f"got '{last_emergency_report.severity_level.value}'"
                    )
        else:
            if "triage_fire_shock_emergency" in tools_called_unique:
                failure_reasons.append("False positive: routine call triggered emergency triage!")

        # 3. Evaluate Mandatory Safety Spoken Directives
        combined_agent_speech = " ".join([
            turn["content"].lower()
            for turn in dialogue_transcript
            if turn["role"] == "Sarah (Dispatcher)"
        ])

        matched_safety_phrases: List[str] = []
        for phrase in scenario.mandatory_safety_phrases:
            if phrase.lower() in combined_agent_speech:
                matched_safety_phrases.append(phrase)
            else:
                failure_reasons.append(f"Agent failed to verbally state required safety instruction: '{phrase}'")

        # 4. Evaluate Booking Creation
        last_booking = None
        if DB.bookings:
            last_booking = list(DB.bookings.values())[-1]

        booking_conf = last_booking.confirmation_id if last_booking else None
        tech_assigned = last_booking.assigned_technician if last_booking else None

        if "book_service_call" in scenario.expected_tools:
            if not last_booking:
                failure_reasons.append("Expected service booking in database, but no booking was recorded!")
            else:
                # Check that customer details were captured
                if scenario.caller_name.lower() not in last_booking.customer_name.lower():
                    failure_reasons.append(
                        f"Customer name mismatch: expected '{scenario.caller_name}', got '{last_booking.customer_name}'"
                    )

        # 5. Check Voice Friendliness (no raw markdown asterisks, no code blocks)
        for turn in dialogue_transcript:
            if turn["role"] == "Sarah (Dispatcher)":
                content = turn["content"]
                if "```" in content or "**" in content or "##" in content:
                    failure_reasons.append("Agent response contained raw markdown syntax inappropriate for voice phone audio.")
                    break

        passed = len(failure_reasons) == 0

        return ScenarioEvaluationResult(
            scenario_id=scenario.scenario_id,
            title=scenario.title,
            category=scenario.category,
            passed=passed,
            duration_ms=duration_ms,
            tools_called=tools_called_unique,
            expected_tools=scenario.expected_tools,
            emergency_level=last_emergency_report.severity_level.value if last_emergency_report else None,
            booking_confirmation_id=booking_conf,
            assigned_technician=tech_assigned,
            safety_phrases_matched=matched_safety_phrases,
            failure_reasons=failure_reasons,
            transcript_summary=dialogue_transcript,
        )

    def run_all(self, export_reports: bool = True) -> bool:
        """Executes all 20 calling scenarios and outputs the evaluation report."""
        print(f"\n================================================================================")
        print(f"  JobLatch AI Voice Dispatch Agent - 20 Scenario Evaluation Test Suite")
        print(f"  Engine: Gemini 2.0 Flash Voice Dispatcher")
        print(f"  Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"================================================================================\n")

        self.results.clear()
        total_scenarios = len(SCENARIOS)

        for idx, scenario in enumerate(SCENARIOS, 1):
            res = self.run_scenario(scenario)
            self.results.append(res)
            status_symbol = "✓ PASS" if res.passed else "✗ FAIL"
            print(f"[{idx:02d}/{total_scenarios:02d}] {status_symbol} | {scenario.scenario_id}: {scenario.title[:45]:<45} ({res.duration_ms:.1f}ms)")
            if not res.passed:
                for f_err in res.failure_reasons:
                    print(f"       -> ERROR: {f_err}")

        # Summary statistics
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r.passed)
        failed_tests = total_tests - passed_tests
        pass_rate = (passed_tests / total_tests) * 100.0 if total_tests > 0 else 0.0
        avg_duration = sum(r.duration_ms for r in self.results) / total_tests if total_tests > 0 else 0.0

        if RICH_AVAILABLE:
            self._render_rich_table(passed_tests, failed_tests, pass_rate, avg_duration)
        else:
            self._render_plain_summary(passed_tests, failed_tests, pass_rate, avg_duration)

        if export_reports:
            self.export_reports()

        return failed_tests == 0

    def _render_rich_table(self, passed: int, failed: int, pass_rate: float, avg_duration: float):
        """Displays rich terminal table with detailed results."""
        table = Table(
            title="JobLatch AI Gemini 2.0 Flash Voice Dispatch - Evaluation Matrix",
            box=ROUNDED,
            show_header=True,
            header_style="bold cyan",
        )
        table.add_column("ID", style="dim", width=12)
        table.add_column("Scenario / Category", width=38)
        table.add_column("Tools Executed", width=34)
        table.add_column("Emergency Triage", width=24)
        table.add_column("Confirmation", width=16)
        table.add_column("Status", justify="center", width=10)

        for r in self.results:
            tools_str = "\n".join([f"• {t}" for t in r.tools_called])
            status_badge = "[bold green]PASS[/bold green]" if r.passed else "[bold red]FAIL[/bold red]"
            triage_badge = f"[yellow]{r.emergency_level}[/yellow]" if r.emergency_level else "[dim]None (Routine)[/dim]"
            conf_badge = f"[cyan]{r.booking_confirmation_id}[/cyan]" if r.booking_confirmation_id else "[dim]N/A[/dim]"

            table.add_row(
                r.scenario_id,
                f"[bold]{r.title}[/bold]\n[dim]{r.category}[/dim]",
                tools_str,
                triage_badge,
                conf_badge,
                status_badge,
            )

        self.console.print("\n")
        self.console.print(table)

        summary_panel = Panel(
            f"[bold]Total Scenarios Evaluated:[/bold] {len(self.results)}\n"
            f"[bold green]Passed:[/bold green] {passed} ({pass_rate:.1f}%)\n"
            f"[bold red]Failed:[/bold red] {failed}\n"
            f"[bold]Average Latency:[/bold] {avg_duration:.2f} ms per scenario\n"
            f"[bold cyan]Overall Result:[/bold cyan] {'[bold green]ALL TESTS PASSED[/bold green]' if failed == 0 else '[bold red]FAILURES DETECTED[/bold red]'}",
            title="[bold yellow]Evaluation Summary[/bold yellow]",
            border_style="green" if failed == 0 else "red",
        )
        self.console.print(summary_panel)

    def _render_plain_summary(self, passed: int, failed: int, pass_rate: float, avg_duration: float):
        """Displays plain text summary when rich is unavailable."""
        print("\n" + "=" * 80)
        print(f"EVALUATION SUMMARY:")
        print(f"  Total Scenarios: {len(self.results)}")
        print(f"  Passed:          {passed} ({pass_rate:.1f}%)")
        print(f"  Failed:          {failed}")
        print(f"  Average Time:    {avg_duration:.2f} ms")
        print(f"  Final Status:    {'ALL 20 SCENARIOS PASSED' if failed == 0 else 'TESTS FAILED'}")
        print("=" * 80 + "\n")

    def export_reports(self, output_dir: str = "reports"):
        """Exports JSON and Markdown evaluation reports."""
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 1. JSON Report
        json_path = os.path.join(output_dir, "scenario_eval_report.json")
        json_data = {
            "test_suite": "JobLatch AI Gemini 2.0 Flash Voice Dispatcher Evaluation",
            "model": "gemini-2.0-flash",
            "generated_at": datetime.now().isoformat(),
            "total_scenarios": len(self.results),
            "passed": sum(1 for r in self.results if r.passed),
            "failed": sum(1 for r in self.results if not r.passed),
            "pass_rate_percent": (sum(1 for r in self.results if r.passed) / len(self.results)) * 100.0,
            "results": [asdict(r) for r in self.results],
        }
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, indent=2)

        # 2. Markdown Report
        md_path = os.path.join(output_dir, "scenario_eval_report.md")
        passed_count = sum(1 for r in self.results if r.passed)
        failed_count = len(self.results) - passed_count
        with open(md_path, "w", encoding="utf-8") as f:
            f.write("# JobLatch AI Voice Dispatch Agent - 20 Scenario Evaluation Report\n\n")
            f.write(f"- **Model**: `gemini-2.0-flash`\n")
            f.write(f"- **Date**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"- **Total Scenarios**: {len(self.results)}\n")
            f.write(f"- **Passed**: {passed_count} / {len(self.results)} ({(passed_count / len(self.results)) * 100:.1f}%)\n")
            f.write(f"- **Failed**: {failed_count}\n\n")
            f.write("## Scenario Evaluation Breakdown\n\n")
            f.write("| ID | Scenario | Category | Emergency Level | Tools Invocations | Booking ID | Result |\n")
            f.write("|---|---|---|---|---|---|---|\n")
            for r in self.results:
                status_emoji = "✅ PASS" if r.passed else "❌ FAIL"
                em_level = r.emergency_level or "None"
                tools_str = ", ".join(r.tools_called)
                book_id = r.booking_confirmation_id or "N/A"
                f.write(f"| {r.scenario_id} | {r.title} | `{r.category}` | `{em_level}` | `{tools_str}` | `{book_id}` | {status_emoji} |\n")

            f.write("\n## Detailed Transcripts & Safety Verification\n\n")
            for r in self.results:
                f.write(f"### {r.scenario_id}: {r.title}\n")
                f.write(f"- **Category**: `{r.category}`\n")
                f.write(f"- **Result**: {'Passed' if r.passed else 'FAILED'}\n")
                if r.failure_reasons:
                    f.write(f"- **Failures**: {', '.join(r.failure_reasons)}\n")
                f.write(f"\n**Spoken Phone Transcript:**\n\n")
                for turn in r.transcript_summary:
                    f.write(f"- **{turn['role']}**: *\"{turn['content']}\"*\n")
                f.write("\n---\n\n")

        print(f"\n✓ Evaluation reports saved to:\n  • {json_path}\n  • {md_path}")


def main():
    runner = DispatchScenarioTestRunner()
    success = runner.run_all(export_reports=True)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
