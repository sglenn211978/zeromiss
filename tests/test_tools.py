"""Unit tests for individual dispatch tools and database state."""

import unittest
from phone_agent.agent.audio_sim import AudioStreamSimulator
from phone_agent.database import DB
from phone_agent.models import EmergencySeverity, UrgencyLevel
from phone_agent.tools.booking_tool import book_service_call, normalize_phone
from phone_agent.tools.calendar_tool import check_calendar_availability, parse_relative_date
from phone_agent.tools.emergency_tool import triage_fire_shock_emergency
from phone_agent.tools.registry import execute_tool


class TestDispatchTools(unittest.TestCase):

    def setUp(self):
        DB.reset()

    def test_calendar_availability_standard(self):
        result = check_calendar_availability(target_date="tomorrow", time_window="morning")
        self.assertEqual(result["status"], "AVAILABLE")
        self.assertGreater(len(result["available_slots"]), 0)
        self.assertIn("voice_summary", result)

    def test_calendar_availability_emergency(self):
        result = check_calendar_availability(target_date="today", urgency="emergency")
        self.assertEqual(result["status"], "EMERGENCY_SLOT_AVAILABLE")
        self.assertEqual(result["urgency"], "EMERGENCY_CRITICAL")
        self.assertIn("Marcus Vance", result["voice_summary"])

    def test_booking_tool_standard(self):
        res = book_service_call(
            customer_name="Alice Cooper",
            phone_number="5551234567",
            service_address="100 Main St, Boston",
            slot_date="2026-11-05",
            slot_time="08:00 AM - 12:00 PM",
            issue_description="Ceiling fan replacement",
            service_type="lighting",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["confirmation_id"].startswith("ZM-BOOK-"))
        self.assertEqual(res["phone_number"], "(555) 123-4567")
        self.assertEqual(res["dispatch_fee"], 89.0)

    def test_booking_tool_emergency(self):
        res = book_service_call(
            customer_name="Bob Danger",
            phone_number="5559876543",
            service_address="99 Fire Lane, Cambridge",
            slot_date="today",
            slot_time="Within 45-60 Minutes",
            issue_description="Main breaker arcing",
            urgency_level="EMERGENCY_CRITICAL",
        )
        self.assertEqual(res["status"], "SUCCESS")
        self.assertTrue(res["confirmation_id"].startswith("ZM-EMERG-"))
        self.assertEqual(res["booking_status"], "DISPATCHED_CODE_RED")
        self.assertEqual(res["dispatch_fee"], 199.0)

    def test_emergency_triage_level_1_fire(self):
        res = triage_fire_shock_emergency(
            hazard_type="active_sparking",
            location_in_property="breaker_panel",
            is_fire_visible=True,
        )
        self.assertEqual(res["severity_level"], EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY.value)
        self.assertTrue(res["emergency_dispatch_recommended"])
        # Check evacuation instruction present
        self.assertTrue(any("evacuate" in act.lower() for act in res["immediate_life_safety_actions"]))

    def test_emergency_triage_level_1_water_panel(self):
        res = triage_fire_shock_emergency(
            hazard_type="water_electrical_contact",
            location_in_property="basement",
            is_water_present=True,
        )
        self.assertEqual(res["severity_level"], EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY.value)
        self.assertTrue(res["utility_shutoff_required"])
        self.assertTrue(any("standing water" in act.lower() for act in res["immediate_life_safety_actions"]))

    def test_emergency_triage_level_1_shock(self):
        res = triage_fire_shock_emergency(
            hazard_type="electric_shock_injury",
            location_in_property="appliance",
            is_person_injured=True,
        )
        self.assertEqual(res["severity_level"], EmergencySeverity.LEVEL_1_CRITICAL_LIFE_SAFETY.value)
        self.assertTrue(any("911" in act.lower() or "medical" in act.lower() for act in res["immediate_life_safety_actions"]))

    def test_emergency_triage_level_2_burning_smell(self):
        res = triage_fire_shock_emergency(
            hazard_type="burning_smell_smoke",
            location_in_property="outlet",
            is_fire_visible=False,
        )
        self.assertEqual(res["severity_level"], EmergencySeverity.LEVEL_2_HIGH_HAZARD.value)
        self.assertTrue(any("breaker" in act.lower() for act in res["immediate_life_safety_actions"]))

    def test_audio_stream_simulator(self):
        tone = AudioStreamSimulator.generate_tone_pcm(frequency=440, duration_seconds=0.1)
        self.assertGreater(len(tone), 0)
        ring = AudioStreamSimulator.generate_phone_ring()
        self.assertGreater(len(ring), 0)
        speech = AudioStreamSimulator.simulate_speech_pcm("Hello this is Sarah at JobLatch AI")
        self.assertGreater(len(speech), 0)


if __name__ == "__main__":
    unittest.main()
