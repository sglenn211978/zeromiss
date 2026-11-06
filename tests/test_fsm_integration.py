"""Unit tests for FSM & External Invoicing Integration (ServiceTitan, Housecall Pro, Jobber, QuickBooks)."""

import unittest
from phone_agent.database import DB, format_fsm_ticket_id, format_fsm_metadata
from phone_agent.models import UrgencyLevel


class TestFsmIntegration(unittest.TestCase):

    def setUp(self):
        DB.reset()

    def test_format_fsm_ticket_id(self):
        self.assertEqual(format_fsm_ticket_id("SERVICETITAN", "ZM-BOOK-1001"), "ST-1001")
        self.assertEqual(format_fsm_ticket_id("HOUSECALL_PRO", "ZM-BOOK-1001"), "HCP-1001")
        self.assertEqual(format_fsm_ticket_id("JOBBER", "ZM-BOOK-1001"), "JOB-1001")
        self.assertEqual(format_fsm_ticket_id("QUICKBOOKS", "ZM-BOOK-1001"), "QBO-1001")

    def test_format_fsm_metadata(self):
        meta_hcp = format_fsm_metadata("HOUSECALL_PRO", "ZM-BOOK-1005")
        self.assertEqual(meta_hcp["name"], "Housecall Pro")
        self.assertEqual(meta_hcp["ticket_id"], "HCP-1005")
        self.assertIn("HCP-1005", meta_hcp["url"])

        meta_st = format_fsm_metadata("SERVICETITAN", "ZM-BOOK-1005")
        self.assertEqual(meta_st["name"], "ServiceTitan")
        self.assertEqual(meta_st["ticket_id"], "ST-1005")

    def test_set_active_fsm_platform(self):
        res = DB.set_active_fsm_platform("SERVICETITAN")
        self.assertEqual(res, "SERVICETITAN")
        self.assertEqual(DB.active_fsm_platform, "SERVICETITAN")

        # All existing bookings should now have ServiceTitan IDs
        for b in DB.bookings.values():
            self.assertEqual(b.connected_fsm, "SERVICETITAN")
            self.assertTrue(b.fsm_ticket_id.startswith("ST-"))
            self.assertIn("servicetitan", b.fsm_external_url)

    def test_generate_payload_servicetitan(self):
        booking = list(DB.bookings.values())[0]
        payload = DB.generate_fsm_webhook_payload(booking.confirmation_id, "SERVICETITAN")

        self.assertEqual(payload["fsm_platform"], "ServiceTitan")
        self.assertIn("servicetitan.io", payload["api_endpoint"])
        self.assertIn("customer", payload)
        self.assertIn("accounting_ledger", payload)
        self.assertEqual(payload["accounting_ledger"]["diagnostic_deposit_credit"], -float(booking.dispatch_fee))

    def test_generate_payload_housecall_pro(self):
        booking = list(DB.bookings.values())[0]
        payload = DB.generate_fsm_webhook_payload(booking.confirmation_id, "HOUSECALL_PRO")

        self.assertEqual(payload["fsm_platform"], "Housecall Pro")
        self.assertIn("housecallpro.com", payload["api_endpoint"])
        self.assertEqual(payload["customer"]["name"], booking.customer_name)
        self.assertTrue(len(payload["line_items"]) > 0)
        self.assertEqual(payload["line_items"][0]["unit_cost"], -float(booking.dispatch_fee))

    def test_generate_payload_jobber(self):
        booking = list(DB.bookings.values())[0]
        payload = DB.generate_fsm_webhook_payload(booking.confirmation_id, "JOBBER")

        self.assertEqual(payload["fsm_platform"], "Jobber")
        self.assertEqual(payload["job"]["depositApplied"], float(booking.dispatch_fee))

    def test_generate_payload_quickbooks(self):
        booking = list(DB.bookings.values())[0]
        payload = DB.generate_fsm_webhook_payload(booking.confirmation_id, "QUICKBOOKS")

        self.assertEqual(payload["fsm_platform"], "QuickBooks Online")
        self.assertEqual(payload["Deposit"], float(booking.dispatch_fee))
        self.assertTrue(any(line["Amount"] == -float(booking.dispatch_fee) for line in payload["Line"]))


if __name__ == "__main__":
    unittest.main()
