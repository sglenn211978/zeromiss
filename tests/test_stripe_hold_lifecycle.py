"""
Unit and Integration Tests for Stripe 2-Step Authorization Hold & On-Site Capture Lifecycle.

Verifies:
1. Authorization hold placement with capture_method="manual" (7-day window without settlement).
2. Automated capture trigger when technician arrives on-site (Stage 2: ON_SITE_DIAGNOSTIC).
3. Automated capture trigger when saving on-site diagnostic readings.
4. Pre-arrival cancellation release (drops hold without processing fees or charge).
5. Stripe Connect destination charges (transfer_data.destination = contractor_account_id).
6. Card-brand compliant SMS disclosure copy formatting.
7. Final balance settlement and completion.
"""

import unittest
from datetime import datetime, timedelta
from phone_agent.database import DB
from phone_agent.integrations.stripe_payments import STRIPE_PAYMENTS, format_hold_sms_disclosure
from phone_agent.models import UrgencyLevel


class TestStripeHoldLifecycle(unittest.TestCase):

    def setUp(self):
        # Create a fresh test booking
        self.booking = DB.book_slot(
            customer_name="Marcus Vance",
            phone_number="(555) 721-9944",
            service_address="44 Ocean Ave, Atlantic City, NJ",
            slot_date="Tomorrow",
            slot_time="08:00 AM - 12:00 PM",
            issue_description="Subpanel buzzing with tripped AFCI breaker",
            service_type="Diagnostic & Subpanel Repair",
            urgency_level=UrgencyLevel.URGENT,
            assigned_technician="Sarah Chen (EV & Commercial Specialist)",
            dispatch_fee=89.0,
            is_demo_seed=False,
        )
        self.cid = self.booking.confirmation_id

    def test_01_place_authorization_hold(self):
        """Verifies placing an authorization hold creates a manual-capture PaymentIntent."""
        booking = DB.place_authorization_hold(self.cid)
        self.assertIsNotNone(booking)
        self.assertEqual(booking.payment_status, "AUTHORIZED_HOLD")
        self.assertEqual(booking.stripe_capture_method, "manual")
        self.assertTrue(booking.stripe_payment_intent_id.startswith("pi_hold_"))
        self.assertIsNotNone(booking.hold_placed_at)
        self.assertIsNotNone(booking.hold_expires_at)

        # Verify underlying payment intent object
        intent = STRIPE_PAYMENTS.get_payment_intent(booking.stripe_payment_intent_id)
        self.assertIsNotNone(intent)
        self.assertEqual(intent["status"], "requires_capture")
        self.assertEqual(intent["amount"], 8900)
        self.assertEqual(intent["amount_capturable"], 8900)
        self.assertEqual(intent["amount_received"], 0)
        self.assertEqual(intent["transfer_data"]["destination"], "acct_apex_electric_101")

    def test_02_auto_capture_on_tech_arrival(self):
        """Verifies that advancing the tech workflow stage to ON_SITE_DIAGNOSTIC auto-captures the hold."""
        DB.place_authorization_hold(self.cid)
        self.assertEqual(DB.bookings[self.cid].payment_status, "AUTHORIZED_HOLD")

        # Technician arrives on site
        updated = DB.update_tech_workflow_stage(self.cid, "ON_SITE_DIAGNOSTIC")
        self.assertEqual(updated.tech_workflow_stage, "ON_SITE_DIAGNOSTIC")
        self.assertEqual(updated.payment_status, "CAPTURED_ON_SITE")
        self.assertIsNotNone(updated.captured_at)
        self.assertEqual(updated.captured_amount_cents, 8900)

        # Verify payment intent updated to succeeded
        intent = STRIPE_PAYMENTS.get_payment_intent(updated.stripe_payment_intent_id)
        self.assertEqual(intent["status"], "succeeded")
        self.assertEqual(intent["amount_received"], 8900)
        self.assertEqual(intent["amount_capturable"], 0)

    def test_03_auto_capture_on_save_diagnostic_readings(self):
        """Verifies that recording panel diagnostic readings on-site auto-captures held funds."""
        DB.place_authorization_hold(self.cid)
        self.assertEqual(DB.bookings[self.cid].payment_status, "AUTHORIZED_HOLD")

        updated = DB.save_diagnostic_readings(self.cid, {
            "main_voltage_l1_l2": "241.8V",
            "neutral_ground_impedance": "0.14 Ohms",
            "fault_finding": "Arcing terminal screw on breaker #12 tightened to 35 in-lbs",
        })
        self.assertEqual(updated.payment_status, "CAPTURED_ON_SITE")
        self.assertIsNotNone(updated.captured_at)
        self.assertEqual(updated.captured_amount_cents, 8900)

    def test_04_release_dispatch_hold_on_cancellation(self):
        """Verifies that cancelling a booking prior to technician arrival releases the hold immediately."""
        DB.place_authorization_hold(self.cid)
        self.assertEqual(DB.bookings[self.cid].payment_status, "AUTHORIZED_HOLD")

        released = DB.release_dispatch_hold(self.cid, reason="customer_cancellation")
        self.assertEqual(released.payment_status, "RELEASED_CANCELED")
        self.assertIsNotNone(released.released_at)

        # Verify payment intent updated to canceled
        intent = STRIPE_PAYMENTS.get_payment_intent(released.stripe_payment_intent_id)
        self.assertEqual(intent["status"], "canceled")
        self.assertEqual(intent["amount_received"], 0)
        self.assertEqual(intent["amount_capturable"], 0)

    def test_05_stripe_connect_destination_charges(self):
        """Verifies that payments are routed directly to contractor merchant account with connector fee."""
        intent = STRIPE_PAYMENTS.create_dispatch_hold(
            customer_id="cus_test_99",
            payment_method_id="pm_card_visa",
            amount_cents=18900,
            booking_id="ZM-TEST-CONNECT",
            contractor_account_id="acct_apex_electric_101",
        )
        self.assertEqual(intent["transfer_data"]["destination"], "acct_apex_electric_101")
        self.assertEqual(intent["application_fee_amount"], 500)
        self.assertEqual(intent["capture_method"], "manual")

    def test_06_sms_hold_disclosure_compliance(self):
        """Verifies card-brand compliant SMS disclosure copy."""
        disclosure = format_hold_sms_disclosure(89.0, "Apex Electrical")
        self.assertIn("authorization hold of $89", disclosure)
        self.assertIn("will not be charged until the technician arrives", disclosure)
        self.assertIn("Apex Electrical", disclosure)

    def test_07_mark_final_balance_paid_from_hold(self):
        """Verifies settling remaining final balance when starting from an active hold."""
        DB.place_authorization_hold(self.cid)
        final = DB.mark_final_balance_paid(self.cid)
        self.assertEqual(final.payment_status, "PAID_VERIFIED")
        self.assertTrue(final.final_balance_paid)
        self.assertEqual(final.tech_workflow_stage, "COMPLETED")
        self.assertIsNotNone(final.captured_at)


if __name__ == "__main__":
    unittest.main()
