"""Unit tests for service area filtering and hazard keyword word-boundary checks."""

import unittest
from phone_agent.agent.gemini_client import Gemini2FlashClient
from phone_agent.agent.prompts import DISPATCHER_SYSTEM_INSTRUCTION
from phone_agent.tools.service_area import check_service_area, extract_caller_town


class TestServiceAreaAndKeywordBoundaries(unittest.TestCase):
    def test_extract_caller_town(self):
        self.assertEqual(extract_caller_town("Hi, I'm calling from Princeton, New Jersey."), "Princeton")
        self.assertEqual(extract_caller_town("I'm in Cherry Hill and need electrical service."), "Cherry Hill")
        self.assertEqual(extract_caller_town("Address is 92 Maple St, Moorestown, NJ."), "Moorestown")
        self.assertIsNone(extract_caller_town("I need my electrical panel looked at."))

    def test_check_service_area(self):
        towns = ["Cherry Hill", "Moorestown", "Haddonfield", "Voorhees"]
        # Inside service area
        res1 = check_service_area("I live in Cherry Hill", towns=towns)
        self.assertEqual(res1["town"], "Cherry Hill")
        self.assertTrue(res1["in_service_area"])

        # Outside service area
        res2 = check_service_area("I'm calling from Princeton, NJ", towns=towns)
        self.assertEqual(res2["town"], "Princeton")
        self.assertFalse(res2["in_service_area"])

        # Unspecified town
        res3 = check_service_area("I need an electrician tomorrow", towns=towns)
        self.assertIsNone(res3["town"])
        self.assertIsNone(res3["in_service_area"])

    def test_no_false_positive_shock_on_word_number(self):
        """Verify that saying 'number' does not trigger the 'numb' electric shock triage."""
        client = Gemini2FlashClient()
        history = [
            {"role": "user", "content": "Hi, I have a question about my account number 12345."}
        ]
        res = client._simulate_gemini_2_flash_turn(history, DISPATCHER_SYSTEM_INSTRUCTION)
        # Should NOT invoke triage_fire_shock_emergency
        tool_names = [tc.get("name") for tc in res.get("tool_calls", [])]
        self.assertNotIn("triage_fire_shock_emergency", tool_names)

    def test_out_of_area_routine_call_declined_politely(self):
        """Verify out-of-area routine request receives polite referral without booking."""
        client = Gemini2FlashClient()
        history = [
            {"role": "user", "content": "I'm calling from Princeton, NJ. I need rewiring. My phone is 609-555-0199."}
        ]
        # Test with custom towns
        import os
        old = os.environ.get("SERVICE_AREA_TOWNS")
        os.environ["SERVICE_AREA_TOWNS"] = "Cherry Hill, Moorestown"
        try:
            res = client._simulate_gemini_2_flash_turn(history, DISPATCHER_SYSTEM_INSTRUCTION)
            self.assertEqual(res.get("tool_calls", []), [])
            self.assertIn("outside our service area", res.get("text", "").lower())
            self.assertIn("princeton", res.get("text", "").lower())
        finally:
            if old is not None:
                os.environ["SERVICE_AREA_TOWNS"] = old
            else:
                os.environ.pop("SERVICE_AREA_TOWNS", None)


if __name__ == "__main__":
    unittest.main()
