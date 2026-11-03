"""Test evaluating 'burning rubber' electrical hazard detection and triage."""

import sys
from phone_agent.agent.voice_agent import VoiceDispatchAgent
from phone_agent.database import DB
from phone_agent.models import EmergencySeverity


def test_burning_rubber_emergency():
    print("\n" + "=" * 80)
    print("  Testing 'Burning Rubber' Electrical Hazard Triage")
    print("================================================================================\n")

    DB.reset()
    agent = VoiceDispatchAgent()
    session = agent.create_session(caller_phone="(555) 789-2341")

    caller_turn = (
        "Hi Sarah, I'm calling because I notice a strong rubber burning smell coming from the wall "
        "behind my refrigerator, but I don't see any open flames yet. My name is Mark Sullivan at 72 Beacon Street."
    )
    print(f"📞 Caller: \"{caller_turn}\"\n")
    agent_response = agent.process_caller_turn(session, caller_turn)
    print(f"🤖 Sarah: \"{agent_response}\"\n")

    # 1. Verify that triage tool was executed
    assert "triage_fire_shock_emergency" in session.tools_invoked, "Emergency triage tool was NOT invoked for burning rubber!"
    print("✓ Emergency Triage Tool Invoked: SUCCESS")

    # 2. Verify emergency report was logged
    assert len(DB.emergency_reports) > 0, "No emergency report logged in DB!"
    report = list(DB.emergency_reports.values())[-1]
    print(f"✓ Triage Case ID: {report.triage_case_id}")
    print(f"✓ Hazard Type:    {report.hazard_type}")
    print(f"✓ Severity Level: {report.severity_level.value}")

    assert report.severity_level in (EmergencySeverity.LEVEL_2_HIGH_HAZARD, EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY)

    # 3. Verify contractor alert was sent to sean.glenn21@gmail.com
    assert report.contractor_alert_sent is True, "Contractor emergency alert was not sent!"
    print(f"✓ Emergency Alert Dispatched to Contractor: Sean Glenn (sean.glenn21@gmail.com)")

    # 4. Verify life safety instructions were spoken or provided
    instructions = " ".join(report.immediate_life_safety_actions).lower()
    assert "breaker" in instructions or "panel" in instructions, "Breaker shutoff instruction missing!"
    print("✓ Breaker Isolation Safety Directive Present: SUCCESS")

    print("\n" + "=" * 80)
    print("  TEST PASSED: 'Burning Rubber' is recognized as a high-severity emergency!")
    print("================================================================================\n")
    return True


if __name__ == "__main__":
    success = test_burning_rubber_emergency()
    sys.exit(0 if success else 1)
