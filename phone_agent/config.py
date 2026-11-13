"""Configuration and business settings for JobLatch AI Electrical Voice Dispatch."""

import os
from dataclasses import dataclass
from typing import Dict, List


@dataclass
class DispatchConfig:
    # Company & Contractor Profile
    company_name: str = "JobLatch AI Electrical & Emergency Services"
    dispatch_phone: str = "(800) 555-LATCH"
    license_number: str = "EC-994821-MA"
    operating_area: str = "Greater Metro & Tri-County Area"

    # Electrical Contractor / Owner Credentials
    contractor_name: str = "Sean Glenn"
    contractor_email: str = os.getenv("CONTRACTOR_EMAIL", "sean.glenn21@gmail.com")
    contractor_phone: str = "(555) 829-1044"

    # Model Configuration
    model_name: str = "gemini-2.0-flash"
    api_key: str = os.getenv("GEMINI_API_KEY", os.getenv("GOOGLE_API_KEY", ""))

    # Pricing & Fees
    standard_diagnostic_fee: float = 89.0
    emergency_dispatch_fee: float = 199.0
    free_quote_services: tuple = ("panel_upgrade", "ev_charger", "generator_transfer")

    # Time Windows
    time_windows: Dict[str, str] = None

    # Emergency Tiers
    level_1_label: str = "LEVEL_1_CRITICAL_LIFE_SAFETY"
    level_2_label: str = "LEVEL_2_HIGH_HAZARD"
    level_3_label: str = "LEVEL_3_MODERATE_RISK"

    # Service Area filter (opt-in). When set, routine work in a caller-named town outside this list is
    # politely declined; emergencies still get life-safety instructions. Empty = filter disabled.
    # Example: SERVICE_AREA_TOWNS="Cherry Hill,Moorestown,Haddonfield,Voorhees"
    service_area_towns: tuple = tuple(
        t.strip() for t in os.getenv("SERVICE_AREA_TOWNS", "").split(",") if t.strip()
    )

    def __post_init__(self):
        if self.time_windows is None:
            self.time_windows = {
                "morning": "08:00 AM - 12:00 PM",
                "afternoon": "12:00 PM - 04:00 PM",
                "evening": "04:00 PM - 07:00 PM",
                "emergency_asap": "Within 45-60 Minutes (Priority Code Red)",
            }


DEFAULT_CONFIG = DispatchConfig()
